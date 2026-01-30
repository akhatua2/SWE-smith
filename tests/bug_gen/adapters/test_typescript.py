import warnings

import pytest

from swesmith.bug_gen.adapters.typescript import get_entities_from_file_ts


@pytest.fixture
def entities(test_file_ts):
    entities = []
    get_entities_from_file_ts(entities, test_file_ts)
    return entities


def test_get_entities_from_file_ts_count(entities):
    # Calculator class, constructor, add, multiply, greet, incrementCounter
    assert len(entities) >= 5


def test_get_entities_from_file_ts_max(test_file_ts):
    entities = []
    get_entities_from_file_ts(entities, test_file_ts, 3)
    assert len(entities) == 3


def test_get_entities_from_file_ts_names(entities):
    names = [e.name for e in entities]
    assert "Calculator" in names
    assert "greet" in names
    assert "add" in names


def test_get_entities_from_file_ts_extensions(entities):
    assert all(e.ext == "ts" for e in entities)


def test_get_entities_from_file_ts_file_paths(entities, test_file_ts):
    assert all(e.file_path == str(test_file_ts) for e in entities)


def test_get_entities_from_file_ts_no_functions(tmp_path):
    no_functions_file = tmp_path / "no_functions.ts"
    no_functions_file.write_text("// no functions\nconst x: number = 5;")
    entities = []
    get_entities_from_file_ts(entities, no_functions_file)
    assert len(entities) == 0


def test_get_entities_from_file_ts_malformed(tmp_path):
    malformed_file = tmp_path / "malformed.ts"
    malformed_file.write_text("(malformed")
    entities = []
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        get_entities_from_file_ts(entities, malformed_file)
        assert any("Error encountered parsing" in str(w.message) for w in ws)


def test_get_entities_from_file_ts_with_type_annotations(tmp_path):
    ts_file = tmp_path / "typed.ts"
    ts_file.write_text("function add(a: number, b: number): number { return a + b; }")
    entities = []
    get_entities_from_file_ts(entities, ts_file)
    assert len(entities) == 1
    assert entities[0].name == "add"
    assert "number" in entities[0].signature


def test_get_entities_from_file_ts_class(tmp_path):
    ts_file = tmp_path / "class.ts"
    ts_file.write_text(
        """
class MyClass {
    myMethod(x: string): string {
        return x;
    }
}
    """.strip()
    )
    entities = []
    get_entities_from_file_ts(entities, ts_file)
    assert len(entities) == 2
    names = [e.name for e in entities]
    assert "MyClass" in names
    assert "myMethod" in names


def test_get_entities_from_file_ts_function_expression(tmp_path):
    ts_file = tmp_path / "func_expr.ts"
    ts_file.write_text("var myFunc = function(x: number): number { return x * 2; };")
    entities = []
    get_entities_from_file_ts(entities, ts_file)
    assert len(entities) == 1
    assert entities[0].name == "myFunc"


def test_get_entities_from_file_ts_complexity(tmp_path):
    ts_file = tmp_path / "complex.ts"
    ts_file.write_text(
        """
function complex(x: number): number {
    if (x > 0) {
        for (let i = 0; i < x; i++) {
            console.log(i);
        }
    } else {
        while (x < 0) {
            x++;
        }
    }
    return x;
}
    """.strip()
    )
    entities = []
    get_entities_from_file_ts(entities, ts_file)
    assert len(entities) == 1
    # base(1) + if(1) + else(1) + for(1) + while(1) = 5
    assert entities[0].complexity >= 4


def test_get_entities_from_file_ts_boolean_operators(tmp_path):
    ts_file = tmp_path / "bool.ts"
    ts_file.write_text(
        "function f(a: boolean, b: boolean): boolean { return a && b || !a; }"
    )
    entities = []
    get_entities_from_file_ts(entities, ts_file)
    assert len(entities) == 1
    assert entities[0].has_bool_op


def test_get_entities_from_file_ts_interface_ignored(tmp_path):
    """Interfaces should not be collected as entities."""
    ts_file = tmp_path / "interface.ts"
    ts_file.write_text(
        """
interface User {
    name: string;
    age: number;
}

function greet(user: User): string {
    return user.name;
}
    """.strip()
    )
    entities = []
    get_entities_from_file_ts(entities, ts_file)
    # Only the function should be collected, not the interface
    assert len(entities) == 1
    assert entities[0].name == "greet"
