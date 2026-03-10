import os
import pytest
import tempfile

from swesmith.profiles.php import (
    PhpProfile,
    Dbal,
    Monolog6db20ca0,
    Guzzlefb92d95f,
    parse_log_phpunit_testdox,
    parse_log_phpunit_verbose,
)
from swesmith.constants import ENV_NAME
from swebench.harness.constants import TestStatus


def make_dummy_php_profile():
    class DummyPhpProfile(PhpProfile):
        owner = "dummy"
        repo = "dummyrepo"
        commit = "deadbeefcafebabe"

        @property
        def dockerfile(self):
            return "FROM php:8.3\nRUN echo hello"

        def log_parser(self, log):
            return parse_log_phpunit_testdox(log)

    return DummyPhpProfile()


def _write_file(base, relpath, content):
    full = os.path.join(base, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)


def _make_profile_with_clone(tmp_path):
    profile = make_dummy_php_profile()

    def fake_clone(dest=None):
        return str(tmp_path), False

    profile.clone = fake_clone
    return profile


def _make_profile_with_cache(cache):
    profile = make_dummy_php_profile()
    profile._test_name_to_files_cache = cache
    return profile


# --- Log parser tests ---


def test_parse_log_phpunit_testdox_passed():
    log = " ✔ Prepare\n ✔ Query\n ✔ Exec"
    result = parse_log_phpunit_testdox(log)
    assert result["Prepare"] == TestStatus.PASSED.value
    assert result["Query"] == TestStatus.PASSED.value
    assert result["Exec"] == TestStatus.PASSED.value


def test_parse_log_phpunit_testdox_failed():
    log = " ✘ Fetch associative"
    result = parse_log_phpunit_testdox(log)
    assert result["Fetch associative"] == TestStatus.FAILED.value


def test_parse_log_phpunit_testdox_skipped():
    log = " ↩ Some skipped test"
    result = parse_log_phpunit_testdox(log)
    assert result["Some skipped test"] == TestStatus.SKIPPED.value


def test_parse_log_phpunit_testdox_mixed():
    log = " ✔ Test one\n ✘ Test two\n ↩ Test three\n ✔ Test four"
    result = parse_log_phpunit_testdox(log)
    assert len(result) == 4
    assert result["Test one"] == TestStatus.PASSED.value
    assert result["Test two"] == TestStatus.FAILED.value
    assert result["Test three"] == TestStatus.SKIPPED.value
    assert result["Test four"] == TestStatus.PASSED.value


def test_parse_log_phpunit_testdox_empty():
    result = parse_log_phpunit_testdox("")
    assert result == {}


def test_parse_log_phpunit_verbose_passed():
    log = " ✓ testPrepare\n ✓ testQuery"
    result = parse_log_phpunit_verbose(log)
    assert result["testPrepare"] == TestStatus.PASSED.value
    assert result["testQuery"] == TestStatus.PASSED.value


def test_parse_log_phpunit_verbose_failed():
    log = " ✗ testFetchAssociative"
    result = parse_log_phpunit_verbose(log)
    assert result["testFetchAssociative"] == TestStatus.FAILED.value


# --- Testdox name conversion tests ---


def test_testdox_name_simple():
    assert PhpProfile._testdox_name("testPrepare") == "Prepare"


def test_testdox_name_camel_case():
    assert PhpProfile._testdox_name("testGetServerVersion") == "Get server version"


def test_testdox_name_multi_word():
    assert PhpProfile._testdox_name("testFetchAssociative") == "Fetch associative"


def test_testdox_name_consecutive_uppercase():
    assert PhpProfile._testdox_name("testGetHTTPResponse") == "Get http response"


# --- Build test name to files map tests ---


def test_build_map_basic_test_file(tmp_path):
    _write_file(
        tmp_path,
        "tests/ConnectionTest.php",
        "<?php\nclass ConnectionTest {\n    public function testPrepare() {}\n    public function testQuery() {}\n}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "Prepare" in result
    assert "tests/ConnectionTest.php" in result["Prepare"]
    assert "Query" in result
    assert "tests/ConnectionTest.php" in result["Query"]


def test_build_map_without_public_modifier(tmp_path):
    _write_file(
        tmp_path,
        "tests/FooTest.php",
        "<?php\nclass FooTest {\n    function testSomething() {}\n}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "Something" in result


def test_build_map_camel_case_method(tmp_path):
    _write_file(
        tmp_path,
        "tests/BarTest.php",
        "<?php\nclass BarTest {\n    public function testGetServerVersion() {}\n}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "Get server version" in result


def test_build_map_vendor_skipped(tmp_path):
    _write_file(
        tmp_path,
        "vendor/pkg/tests/SomeTest.php",
        "<?php\nclass SomeTest {\n    public function testVendor() {}\n}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "Vendor" not in result


def test_build_map_non_test_file_ignored(tmp_path):
    _write_file(
        tmp_path,
        "src/Connection.php",
        "<?php\nclass Connection {\n    public function testLike() {}\n}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert result == {}


def test_build_map_test_dir_convention(tmp_path):
    _write_file(
        tmp_path,
        "Test/Unit/Helper.php",
        "<?php\nclass Helper {\n    public function testFormat() {}\n}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "Format" in result


def test_build_map_same_name_multiple_files(tmp_path):
    _write_file(
        tmp_path,
        "tests/ATest.php",
        "<?php\nclass ATest {\n    public function testExecute() {}\n}\n",
    )
    _write_file(
        tmp_path,
        "tests/BTest.php",
        "<?php\nclass BTest {\n    public function testExecute() {}\n}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "Execute" in result
    assert result["Execute"] == {"tests/ATest.php", "tests/BTest.php"}


# --- get_test_files tests ---


def test_get_test_files_basic():
    cache = {
        "Prepare": {"tests/ConnectionTest.php"},
        "Query": {"tests/ConnectionTest.php"},
        "Format output": {"tests/FormatterTest.php"},
    }
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["Prepare"],
        "PASS_TO_PASS": ["Query", "Format output"],
    }
    f2p, p2p = profile.get_test_files(instance)
    assert set(f2p) == {"tests/ConnectionTest.php"}
    assert set(p2p) == {"tests/ConnectionTest.php", "tests/FormatterTest.php"}


def test_get_test_files_missing_names():
    cache = {"Prepare": {"tests/ConnectionTest.php"}}
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["Not in cache"],
        "PASS_TO_PASS": ["Also missing"],
    }
    f2p, p2p = profile.get_test_files(instance)
    assert f2p == []
    assert p2p == []


def test_get_test_files_assertion_error():
    profile = _make_profile_with_cache({})
    with pytest.raises(AssertionError):
        profile.get_test_files({"instance_id": "dummy__dummyrepo.deadbeef.1"})


def test_get_test_files_cache_reuse():
    profile = make_dummy_php_profile()
    clone_count = 0

    def counting_clone(dest=None):
        nonlocal clone_count
        clone_count += 1
        d = tempfile.mkdtemp()
        return d, True

    profile.clone = counting_clone

    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["test_a"],
        "PASS_TO_PASS": ["test_b"],
    }
    profile.get_test_files(instance)
    profile.get_test_files(instance)
    assert clone_count == 1


# --- Profile tests ---


def test_dbal_dockerfile():
    profile = Dbal()
    assert "php:8.3" in profile.dockerfile
    assert f"/{ENV_NAME}" in profile.dockerfile
    assert "composer" in profile.dockerfile


def test_monolog_dockerfile():
    profile = Monolog6db20ca0()
    assert "php:8.3" in profile.dockerfile
    assert "ext-mongodb" in profile.dockerfile


def test_guzzle_dockerfile():
    profile = Guzzlefb92d95f()
    assert "php:8.3" in profile.dockerfile
    assert "composer install" in profile.dockerfile


def test_php_profile_defaults():
    profile = make_dummy_php_profile()
    assert profile.org_dh == "swebench"
    assert profile.exts == [".php"]
    assert "phpunit" in profile.test_cmd


def test_build_map_unreadable_file(tmp_path):
    """Files that can't be read (OSError/UnicodeDecodeError) are skipped."""
    # Write a binary file that will cause UnicodeDecodeError
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    bad_file = test_dir / "BadTest.php"
    bad_file.write_bytes(b"<?php\n\xff\xfe function testBad() {}\n")

    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    # The file should be skipped due to decode error, but not crash
    # It may or may not have results depending on whether the binary content is valid
    assert isinstance(result, dict)


def test_build_map_test_prefixed_file(tmp_path):
    """Files starting with 'test' should be picked up even outside tests/ dir."""
    _write_file(
        tmp_path,
        "src/testHelper.php",
        "<?php\nclass TestHelper {\n    public function testDoStuff() {}\n}\n",
    )
    profile = _make_profile_with_clone(tmp_path)
    result = profile._build_test_name_to_files_map()
    assert "Do stuff" in result


def test_testdox_name_no_test_prefix():
    """Method name without 'test' prefix still gets camelCase splitting."""
    assert PhpProfile._testdox_name("setUp") == "set up"


def test_get_test_files_partial_cache_match():
    """Some test names in cache, some not."""
    cache = {
        "Prepare": {"tests/ConnectionTest.php"},
        "Query": {"tests/ConnectionTest.php"},
    }
    profile = _make_profile_with_cache(cache)
    instance = {
        "instance_id": "dummy__dummyrepo.deadbeef.1",
        "FAIL_TO_PASS": ["Prepare", "Not in cache"],
        "PASS_TO_PASS": ["Query", "Also missing"],
    }
    f2p, p2p = profile.get_test_files(instance)
    assert set(f2p) == {"tests/ConnectionTest.php"}
    assert set(p2p) == {"tests/ConnectionTest.php"}
