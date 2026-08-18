"""Purity is structural, so it is asserted structurally.

Two claims here cannot be reached by calling the chain and looking at the
answer, so they are read off the module itself:

* **The policy function takes no collaborators and performs no input or output.**
  A behavioural test can only show that it did not do so on the inputs it was
  given. What makes the property true is that there is nothing to inject and
  nothing imported that could reach a file or a socket.
* **The empty join and the foreign row converge on a single return site.**
  Byte-identity on the wire is a different assertion at a different altitude,
  made by an attack-suite row; convergence in layer 2 is this one. Constant time
  is not measured at either altitude and is not claimed at either.
"""

import ast
import inspect
from pathlib import Path

from mcp_erp.authorization import decide_call, decide_item, permits_scope, policy

POLICY_SOURCE = Path(inspect.getfile(policy)).read_text(encoding="utf-8")
POLICY_TREE = ast.parse(POLICY_SOURCE)

ALLOWED_IMPORTS = frozenset({"dataclasses", "typing", "mcp_erp.authorization"})
"""What the chain may import: its own types, and the two stdlib modules that
declare them. Nothing here can reach a file, a socket or a clock."""


def _imported_modules() -> set[str]:
    """Every module name the policy module imports, as written."""
    modules: set[str] = set()
    for node in ast.walk(POLICY_TREE):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def _called_names() -> set[str]:
    """Every bare name called in the policy module, ignoring attribute calls."""
    return {
        node.func.id
        for node in ast.walk(POLICY_TREE)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def test_the_entry_points_take_no_collaborators() -> None:
    """A principal, a declaration, and at most the row. Nothing injected."""
    assert list(inspect.signature(permits_scope).parameters) == ["principal", "action"]
    assert list(inspect.signature(decide_call).parameters) == ["principal", "action"]
    assert list(inspect.signature(decide_item).parameters) == [
        "principal",
        "action",
        "resource",
    ]


def test_the_chain_imports_nothing_that_could_perform_input_or_output() -> None:
    """An injected directory would make purity a promise; there is nothing to inject.

    The shipped directory reads from a file, which is exactly why lookup is a
    named step ahead of the chain rather than a collaborator inside it.
    """
    unexpected = {
        imported
        for imported in _imported_modules()
        if not any(
            imported == allowed or imported.startswith(f"{allowed}.") for allowed in ALLOWED_IMPORTS
        )
    }

    assert unexpected == set()


def test_the_chain_calls_nothing_that_reaches_the_world() -> None:
    """No file handle, no console, no input — not even in a branch nothing takes."""
    assert not _called_names() & {"open", "print", "input", "eval", "exec", "__import__"}


def test_the_chain_holds_no_module_level_state() -> None:
    """Nothing to memoise into, so two identical calls cannot answer differently."""
    assignments = [
        node
        for node in POLICY_TREE.body
        if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign)
    ]

    assert assignments == []


def test_the_absent_row_and_the_foreign_row_share_one_return_site() -> None:
    """Two sites would make the refusal an existence oracle."""
    sites = [
        node
        for node in ast.walk(POLICY_TREE)
        if isinstance(node, ast.Return)
        and node.value is not None
        and any(
            isinstance(inner, ast.Name) and inner.id == "NOT_FOUND"
            for inner in ast.walk(node.value)
        )
    ]

    assert len(sites) == 1


def test_layer_2_imports_nothing_from_the_layers_above_it() -> None:
    """The ejection claim, read off the package rather than off the checkout.

    ``import-linter`` makes the same assertion over the whole static graph and
    the ejection job makes it over what these tests actually run. This one
    catches the case where a layer-2 module grows an import that neither reaches
    before a reader does.
    """
    package = Path(inspect.getfile(policy)).parent
    for source in sorted(package.glob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                assert "purchase_to_pay" not in node.module, source.name
                assert "transport" not in node.module, source.name
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert "purchase_to_pay" not in alias.name, source.name
                    assert "transport" not in alias.name, source.name
