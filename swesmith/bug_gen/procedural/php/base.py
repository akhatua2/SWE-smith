"""
Base class for PHP procedural modifications.
"""

from abc import ABC

import tree_sitter_php as tsphp
from tree_sitter import Language, Parser

from swesmith.bug_gen.procedural.base import ProceduralModifier

PHP_LANGUAGE = Language(tsphp.language_php())

# PHP's tree-sitter parser requires the <?php tag to parse PHP code.
# Entity src_code doesn't include it, so we prepend it before parsing
# and strip it from the result after modification.
PHP_TAG = "<?php\n"


def php_parse(src_code: str):
    """Parse PHP source code, prepending <?php tag if needed.

    Returns (tree, offset) where offset is the number of bytes added.
    """
    parser = Parser(PHP_LANGUAGE)
    if not src_code.lstrip().startswith("<?"):
        wrapped = PHP_TAG + src_code
        offset = len(PHP_TAG.encode("utf-8"))
    else:
        wrapped = src_code
        offset = 0
    tree = parser.parse(bytes(wrapped, "utf8"))
    return tree, offset


class PhpProceduralModifier(ProceduralModifier, ABC):
    """Base class for PHP-specific procedural modifications using tree-sitter AST."""

    pass
