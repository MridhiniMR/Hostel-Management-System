from pathlib import Path
import ast


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HMS_DIR = PROJECT_ROOT / "hms"


def get_module_tree(filename):
    source = (HMS_DIR / filename).read_text(encoding="utf-8")
    return ast.parse(source)


def test_web_layer_does_not_execute_database_queries():
    tree = get_module_tree("web.py")

    forbidden_methods = {
        "scalar",
        "scalars",
        "execute",
        "commit",
        "rollback",
        "refresh",
        "delete",
        "add",
    }

    violations = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "db"
                and node.func.attr in forbidden_methods
            ):
                violations.append(node.func.attr)

    assert not violations, (
        f"Presentation layer contains direct database operations: {violations}"
    )


def test_repository_layer_contains_database_access():
    tree = get_module_tree("repositories.py")

    database_methods = {"scalar", "scalars", "execute"}

    found = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in database_methods
        for node in ast.walk(tree)
    )

    assert found, "Repository layer should contain database query operations"
