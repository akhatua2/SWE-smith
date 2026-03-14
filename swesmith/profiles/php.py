import os
import re
import shutil

from dataclasses import dataclass, field
from swebench.harness.constants import (
    FAIL_TO_PASS,
    PASS_TO_PASS,
    KEY_INSTANCE_ID,
    TestStatus,
)
from swesmith.constants import ENV_NAME
from swesmith.profiles.base import RepoProfile, registry


@dataclass
class PhpProfile(RepoProfile):
    """
    Profile for PHP repositories.
    """

    org_dh: str = "swebench"
    test_cmd: str = "vendor/bin/phpunit --testdox --colors=never"
    exts: list[str] = field(default_factory=lambda: [".php"])
    _test_name_to_files_cache: dict[str, set[str]] = field(
        default=None, init=False, repr=False
    )

    @staticmethod
    def _testdox_name(method_name: str) -> str:
        """Convert a PHP test method name to its testdox description.

        PHPUnit strips the 'test' prefix, then converts camelCase to
        space-separated lowercase words (first word capitalized).
        e.g. testGetServerVersion -> Get server version
             testFetchAssociative -> Fetch associative
        """
        name = method_name
        if name.startswith("test"):
            name = name[4:]
        # Insert space before uppercase letters (camelCase -> words)
        name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
        # PHPUnit lowercases everything then capitalizes first letter
        words = name.split()
        if words:
            words = [words[0]] + [w.lower() for w in words[1:]]
            name = " ".join(words)
        return name

    def _build_test_name_to_files_map(self) -> dict[str, set[str]]:
        """Build a mapping from testdox names to test file paths.

        Scans PHP test files for method names starting with 'test' and
        converts them to their testdox representation.
        """
        dest, cloned = self.clone()
        name_to_files: dict[str, set[str]] = {}

        test_method_re = re.compile(r"(?:public\s+)?function\s+(test[A-Z]\w*)\s*\(")

        for dirpath, _, filenames in os.walk(dest):
            if "vendor" in dirpath.split(os.sep):
                continue
            for fname in filenames:
                if not fname.endswith(".php"):
                    continue
                # PHPUnit convention: test files end with Test.php or are in tests/ dir
                parts = dirpath.split(os.sep)
                in_test_dir = any(
                    p in ("test", "tests", "Test", "Tests") for p in parts
                )
                is_test_named = fname.endswith("Test.php") or fname.startswith("test")
                if not in_test_dir and not is_test_named:
                    continue

                full_path = os.path.join(dirpath, fname)
                relative_path = os.path.relpath(full_path, dest)

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except (OSError, UnicodeDecodeError):
                    continue

                for match in test_method_re.finditer(content):
                    testdox = self._testdox_name(match.group(1))
                    name_to_files.setdefault(testdox, set()).add(relative_path)

        if cloned:
            shutil.rmtree(dest)
        return name_to_files

    def get_test_files(self, instance: dict) -> tuple[list[str], list[str]]:
        assert FAIL_TO_PASS in instance and PASS_TO_PASS in instance, (
            f"Instance {instance[KEY_INSTANCE_ID]} missing required keys {FAIL_TO_PASS} or {PASS_TO_PASS}"
        )

        if self._test_name_to_files_cache is None:
            with self._lock:
                if self._test_name_to_files_cache is None:
                    self._test_name_to_files_cache = (
                        self._build_test_name_to_files_map()
                    )

        f2p_files: set[str] = set()
        for test_name in instance[FAIL_TO_PASS]:
            if test_name in self._test_name_to_files_cache:
                f2p_files.update(self._test_name_to_files_cache[test_name])

        p2p_files: set[str] = set()
        for test_name in instance[PASS_TO_PASS]:
            if test_name in self._test_name_to_files_cache:
                p2p_files.update(self._test_name_to_files_cache[test_name])

        return list(f2p_files), list(p2p_files)


@dataclass
class Dbalacb68b38(PhpProfile):
    owner: str = "doctrine"
    repo: str = "dbal"
    commit: str = "acb68b388b2577bb211bb26dc22d20a8ad93d97d"

    @property
    def dockerfile(self):
        return f"""FROM php:8.3
RUN apt-get update && \
    apt-get install -y wget git build-essential unzip libgd-dev libzip-dev libgmp-dev libftp-dev libcurl4-openssl-dev libpq-dev libsqlite3-dev && \
    docker-php-ext-install pdo pdo_mysql pdo_pgsql pdo_sqlite mysqli gd zip gmp ftp curl pcntl && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sS https://getcomposer.org/installer | php -- --2.2 --install-dir=/usr/local/bin --filename=composer

RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN composer update
RUN composer install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_phpunit_testdox(log)


def parse_log_phpunit_testdox(log: str) -> dict[str, str]:
    """Parse PHPUnit --testdox output format."""
    test_status_map = {}
    passed_pattern = re.compile(r"^\s*✔\s*(.+)$")
    failed_pattern = re.compile(r"^\s*✘\s*(.+)$")
    skipped_pattern = re.compile(r"^\s*↩\s*(.+)$")
    for line in log.split("\n"):
        for pattern, status in (
            (passed_pattern, TestStatus.PASSED.value),
            (failed_pattern, TestStatus.FAILED.value),
            (skipped_pattern, TestStatus.SKIPPED.value),
        ):
            match = pattern.match(line)
            if match:
                test_name = match.group(1).strip()
                test_status_map[test_name] = status
                break
    return test_status_map


def parse_log_phpunit_verbose(log: str) -> dict[str, str]:
    """Parse PHPUnit --verbose (non-testdox) output format.

    Matches lines like:
    ✓ testMethodName
    ✗ testMethodName
    Or standard verbose format:
    OK (42 tests, 100 assertions)
    FAILURES!
    Tests: 42, Assertions: 100, Failures: 2.
    """
    test_status_map = {}
    # Match individual test results in verbose mode
    # Format: "Test\\Namespace\\Class::testMethod"
    passed = re.compile(r"^\s*✓\s*(.+)$")
    failed = re.compile(r"^\s*✗\s*(.+)$")
    # Also match standard PHPUnit output lines
    std_pass = re.compile(r"^ok \d+ - (.+)$", re.IGNORECASE)
    std_fail = re.compile(r"^not ok \d+ - (.+)$", re.IGNORECASE)
    for line in log.split("\n"):
        for pattern, status in (
            (passed, TestStatus.PASSED.value),
            (failed, TestStatus.FAILED.value),
            (std_pass, TestStatus.PASSED.value),
            (std_fail, TestStatus.FAILED.value),
        ):
            match = pattern.match(line)
            if match:
                test_name = match.group(1).strip()
                test_status_map[test_name] = status
                break
    return test_status_map


@dataclass
class Guzzlefb92d95f(PhpProfile):
    owner: str = "guzzle"
    repo: str = "guzzle"
    commit: str = "fb92d95f80a9da51bf8f2a5b26d8e8ea3b6d99ed"

    @property
    def dockerfile(self):
        return f"""FROM php:8.3
RUN apt-get update && \
    apt-get install -y git unzip libcurl4-openssl-dev libzip-dev nodejs npm && \
    docker-php-ext-install curl zip && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/*
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN composer install
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_phpunit_testdox(log)


@dataclass
class Monolog6db20ca0(PhpProfile):
    owner: str = "Seldaek"
    repo: str = "monolog"
    commit: str = "6db20ca029219dd8de378cea8e32ee149399ef1b"

    @property
    def dockerfile(self):
        return f"""FROM php:8.3
RUN apt-get update && \
    apt-get install -y git unzip libcurl4-openssl-dev && \
    docker-php-ext-install curl sockets && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/*
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer
RUN git clone https://github.com/{self.mirror_name} /{ENV_NAME}
WORKDIR /{ENV_NAME}
RUN composer install --ignore-platform-req=ext-mongodb
"""

    def log_parser(self, log: str) -> dict[str, str]:
        return parse_log_phpunit_testdox(log)


# Register all PHP profiles with the global registry
for name, obj in list(globals().items()):
    if (
        isinstance(obj, type)
        and issubclass(obj, PhpProfile)
        and obj.__name__ != "PhpProfile"
    ):
        registry.register_profile(obj)
