import pytest
from swesmith.bug_gen.adapters.php import get_entities_from_file_php
from swesmith.bug_gen.procedural.php.remove import (
    RemoveLoopModifier,
    RemoveConditionalModifier,
    RemoveAssignmentModifier,
    RemoveTernaryModifier,
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
    "src,loop_keyword",
    [
        (
            """function foo($arr) {
    $sum = 0;
    for ($i = 0; $i < count($arr); $i++) {
        $sum += $arr[$i];
    }
    return $sum;
}""",
            "for",
        ),
        (
            """function bar($items) {
    $result = [];
    foreach ($items as $item) {
        $result[] = $item * 2;
    }
    return $result;
}""",
            "foreach",
        ),
        (
            """function baz($n) {
    $i = 0;
    while ($i < $n) {
        echo $i;
        $i++;
    }
}""",
            "while",
        ),
    ],
)
def test_remove_loop_modifier(tmp_path, src, loop_keyword):
    entity = _get_entity(tmp_path, src)
    modifier = RemoveLoopModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert result.rewrite != src
    assert loop_keyword not in result.rewrite or len(result.rewrite) < len(src)


@pytest.mark.parametrize(
    "src",
    [
        """function foo($x) {
    if ($x > 0) {
        return "positive";
    }
    return "non-positive";
}""",
        """function bar($a, $b) {
    if ($a === $b) {
        return true;
    }
    return false;
}""",
    ],
)
def test_remove_conditional_modifier(tmp_path, src):
    entity = _get_entity(tmp_path, src)
    modifier = RemoveConditionalModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert result.rewrite != src
    assert len(result.rewrite) < len(src)


@pytest.mark.parametrize(
    "src",
    [
        """function foo($x) {
    $y = $x + 1;
    return $y;
}""",
        """function bar($a) {
    $a += 5;
    return $a;
}""",
    ],
)
def test_remove_assignment_modifier(tmp_path, src):
    entity = _get_entity(tmp_path, src)
    modifier = RemoveAssignmentModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert result.rewrite != src
    assert len(result.rewrite) < len(src)


@pytest.mark.parametrize(
    "src",
    [
        """function foo($x) {
    return $x > 0 ? "yes" : "no";
}""",
        """function bar($a, $b) {
    return $a === $b ? 1 : 0;
}""",
    ],
)
def test_remove_ternary_modifier(tmp_path, src):
    entity = _get_entity(tmp_path, src)
    modifier = RemoveTernaryModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert result.rewrite != src
    assert "?" not in result.rewrite
