import pytest
from swesmith.bug_gen.adapters.php import get_entities_from_file_php
from swesmith.bug_gen.procedural.php.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)

PHP_PREFIX = "<?php\n"


def _get_entity(tmp_path, src):
    test_file = tmp_path / "test.php"
    test_file.write_text(PHP_PREFIX + src, encoding="utf-8")
    entities = []
    get_entities_from_file_php(entities, str(test_file))
    assert len(entities) >= 1
    return entities[0]


@pytest.mark.parametrize(
    "src",
    [
        """function foo($x) {
    if ($x > 0) {
        return "positive";
    } else {
        return "non-positive";
    }
}""",
        """function bar($a, $b) {
    if ($a === $b) {
        $result = true;
    } else {
        $result = false;
    }
    return $result;
}""",
    ],
)
def test_control_if_else_invert_modifier(tmp_path, src):
    entity = _get_entity(tmp_path, src)
    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert result.rewrite != src


@pytest.mark.parametrize(
    "src",
    [
        """function foo($x) {
    $a = 1;
    $b = 2;
    $c = 3;
    for ($i = 0; $i < $x; $i++) {
        echo $i;
    }
    return $a + $b + $c;
}""",
    ],
)
def test_control_shuffle_lines_modifier(tmp_path, src):
    entity = _get_entity(tmp_path, src)
    modifier = ControlShuffleLinesModifier(likelihood=1.0, seed=42)

    found_different = False
    for _ in range(20):
        result = modifier.modify(entity)
        if result and result.rewrite != src:
            found_different = True
            break

    assert found_different, "Expected shuffled output to differ from input"
