import pytest
from swesmith.bug_gen.adapters.php import get_entities_from_file_php
from swesmith.bug_gen.procedural.php.operations import (
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
    OperationChangeConstantsModifier,
    OperationBreakChainsModifier,
    AugmentedAssignmentSwapModifier,
    TernaryOperatorSwapModifier,
    FunctionArgumentSwapModifier,
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
    "src,expected_variants",
    [
        (
            """function foo($a, $b) {
    return $a + $b;
}""",
            ["return $a - $b;"],
        ),
        (
            """function bar($x, $y) {
    return $x * $y;
}""",
            ["return $x / $y;", "return $x % $y;"],
        ),
        (
            """function baz($a, $b) {
    return $a & $b;
}""",
            ["return $a | $b;", "return $a ^ $b;"],
        ),
        # PHP string concatenation
        (
            """function concat($a, $b) {
    return $a . $b;
}""",
            ["return $a + $b;"],
        ),
    ],
)
def test_operation_change_modifier(tmp_path, src, expected_variants):
    entity = _get_entity(tmp_path, src)
    modifier = OperationChangeModifier(likelihood=1.0, seed=42)

    found_variant = False
    for _ in range(20):
        result = modifier.modify(entity)
        if result and any(v in result.rewrite for v in expected_variants):
            found_variant = True
            break

    assert found_variant, f"Expected one of {expected_variants} in output"


@pytest.mark.parametrize(
    "src,expected_substring",
    [
        (
            """function foo($a, $b) {
    return $a === $b;
}""",
            "!==",
        ),
        (
            """function bar($x, $y) {
    return $x < $y;
}""",
            ">=",
        ),
        (
            """function baz($a, $b) {
    return $a && $b;
}""",
            "||",
        ),
        (
            """function qux($a, $b) {
    return $a + $b;
}""",
            "-",
        ),
    ],
)
def test_operation_flip_operator_modifier(tmp_path, src, expected_substring):
    entity = _get_entity(tmp_path, src)
    modifier = OperationFlipOperatorModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert expected_substring in result.rewrite


@pytest.mark.parametrize(
    "src",
    [
        """function foo($a, $b) {
    return $a + $b;
}""",
        """function bar($x, $y) {
    return $x - $y;
}""",
    ],
)
def test_operation_swap_operands_modifier(tmp_path, src):
    entity = _get_entity(tmp_path, src)
    modifier = OperationSwapOperandsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert result.rewrite != src


@pytest.mark.parametrize(
    "src,expected_variants",
    [
        (
            """function foo() {
    return 2 + $x;
}""",
            ["1", "3", "0", "4"],
        ),
        (
            """function bar() {
    return $y - 5;
}""",
            ["4", "6", "3", "7"],
        ),
    ],
)
def test_operation_change_constants_modifier(tmp_path, src, expected_variants):
    entity = _get_entity(tmp_path, src)
    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert any(v in result.rewrite for v in expected_variants)


@pytest.mark.parametrize(
    "src",
    [
        """function foo($a, $b, $c) {
    return $a + $b + $c;
}""",
        """function bar($x, $y, $z) {
    return $x * $y * $z;
}""",
    ],
)
def test_operation_break_chains_modifier(tmp_path, src):
    entity = _get_entity(tmp_path, src)
    modifier = OperationBreakChainsModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert result.rewrite != src


@pytest.mark.parametrize(
    "src,expected_substring",
    [
        (
            """function foo($x) {
    $x += 5;
    return $x;
}""",
            "-=",
        ),
        (
            """function bar($y) {
    $y *= 2;
    return $y;
}""",
            "/=",
        ),
        (
            """function baz($n) {
    $n++;
    return $n;
}""",
            "--",
        ),
    ],
)
def test_augmented_assignment_swap_modifier(tmp_path, src, expected_substring):
    entity = _get_entity(tmp_path, src)
    modifier = AugmentedAssignmentSwapModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert expected_substring in result.rewrite


@pytest.mark.parametrize(
    "src",
    [
        """function foo($condition) {
    return $condition ? "yes" : "no";
}""",
        """function bar($x) {
    return $x > 0 ? 1 : -1;
}""",
    ],
)
def test_ternary_operator_swap_modifier(tmp_path, src):
    entity = _get_entity(tmp_path, src)
    modifier = TernaryOperatorSwapModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert result.rewrite != src


@pytest.mark.parametrize(
    "src",
    [
        """function foo() {
    return add(1, 2);
}""",
        """function bar() {
    return compute($a, $b, $c);
}""",
    ],
)
def test_function_argument_swap_modifier(tmp_path, src):
    entity = _get_entity(tmp_path, src)
    modifier = FunctionArgumentSwapModifier(likelihood=1.0, seed=42)
    result = modifier.modify(entity)

    assert result is not None
    assert result.rewrite != src
