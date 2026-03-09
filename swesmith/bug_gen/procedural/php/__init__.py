"""
PHP procedural modifiers for bug generation.

PHP shares most tree-sitter node types with JavaScript (binary_expression,
if_statement, for_statement, etc.), so we reuse the JavaScript modifiers.
"""

from swesmith.bug_gen.procedural.javascript import MODIFIERS_JAVASCRIPT

# PHP uses the same tree-sitter AST node types as JavaScript for
# operators, control flow, and assignments, so we reuse JS modifiers directly.
MODIFIERS_PHP = MODIFIERS_JAVASCRIPT
