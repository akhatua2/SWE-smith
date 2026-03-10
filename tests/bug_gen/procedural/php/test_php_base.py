from swesmith.bug_gen.procedural.php.base import php_parse


def test_php_parse_without_tag():
    """Code without <?php tag should have it prepended."""
    src = "function foo() { return 1; }"
    tree, offset = php_parse(src)
    assert offset > 0
    assert tree.root_node is not None


def test_php_parse_with_tag():
    """Code already starting with <?php should not be re-wrapped."""
    src = "<?php\nfunction foo() { return 1; }"
    tree, offset = php_parse(src)
    assert offset == 0
    assert tree.root_node is not None


def test_php_parse_with_short_tag():
    """Code starting with <? (short open tag) should not be re-wrapped."""
    src = "<?\nfunction foo() { return 1; }"
    tree, offset = php_parse(src)
    assert offset == 0
    assert tree.root_node is not None


def test_php_parse_with_whitespace_before_tag():
    """Code with leading whitespace before <?php should not be re-wrapped."""
    src = "  <?php\nfunction foo() { return 1; }"
    tree, offset = php_parse(src)
    assert offset == 0
    assert tree.root_node is not None
