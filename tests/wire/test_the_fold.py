"""The fold — what layer 1 does with N outcomes, and what it still does not know.

ADR-0013 specifies it and #41 lands it: **N outcomes fold into one result body,
one answer per item named in the request**. There is one wire shape — every POST
is answered `application/json` — so cardinality does not choose a response mode.
It chooses a body, and this is the file that says which body.

Three claims, and the third is the one a reader will not expect.

- **A batch of N items answers with exactly N answers**, asserted against the
  request rather than against the data. That is *outcomes equal items requested*,
  the invariant the fold rests on: a batch yields one answer per item, permit or
  refusal, never a silent drop.
- **One outcome renders directly.** The body of a one-item call is the answer
  itself, not a list of one. Layer 1 has nothing but cardinality to key on —
  learning the tool's name is the coupling this whole design exists to refuse —
  so a one-item batch is indistinguishable to it from `get_requisition`, and it
  renders the same way. The visible price is `approve_requisition` declaring two
  bodies in one `outputSchema`, and it is the right price.
- **Result rows are not outcomes.** A list returning three requisitions is *one*
  outcome containing three rows, so a list tool never reaches this decision at
  all. Asserted here because it is a claim about the fold rather than about
  listing: the failure it forbids is layer 1 counting rows.

**Why the structural assertion sits in a wire directory.** ADR-0013 gives layers
1 and 3 no test directory and routes every assertion about them over the wire;
`tests/wire/` was added at #37 for the assertions that belong to none of the four
artifacts. *Layer 1 contains no reference to the tool name, nor to which argument
is the batch* is not reachable at that altitude — a name absent from a module is
absent, and no request can show it — so it is read off layer 1's own source here,
beside the three assertions that are its behavioural half. The alternative was a
sixth directory holding one file.
"""

import ast
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

import rpc
import seeded_requisitions
from mcp_erp import transport
from requisitions import raised_by
from tokens import mint

APPROVE = "approve_requisition"
LIST = "list_requisitions"

FOLD_KEY = "outcomes"
"""What layer 1 calls the list of answers, spelled here a third time.

`mcp_erp.transport.dispatch` holds one spelling and layer 3's declared
`outputSchema` holds the other; the two packages import nothing from each other,
so nothing on either side can notice them disagreeing. A caller would, and
`test_the_declared_key_and_the_rendered_one_are_one_key` is where the three
spellings are held equal.
"""

APPROVER = "tomas.weber"
"""CC-4100, `approver`. Decides at or below the threshold."""

SUBMITTER = "priya.raman"
"""CC-4100, no ERP role at all. Raises the rows the approver decides."""

AMOUNT = "480.00"
"""Below the threshold, so nothing but the fold is under test here."""


@pytest.fixture(scope="module", autouse=True)
def requisitions() -> Iterator[None]:
    """Start from the seeded four, with the descendant tables cleared.

    This module writes — it raises rows and decides them — so it must know where
    it began. Module-scoped for the reason every suite beside it states.
    """
    seeded_requisitions.load()
    yield


def _decide(username: str, identifiers: list[str]) -> dict[str, Any]:
    """One `approve_requisition` call over however many items are named."""
    result = rpc.result(
        rpc.call_tool(
            APPROVE,
            {"ids": identifiers, "decision": "approve"},
            token=mint(username, ["erp.decide"]).access_token,
        )
    )

    payload: dict[str, Any] = result["structuredContent"]
    return payload


def test_a_batch_of_n_items_answers_with_exactly_n_answers() -> None:
    """*Outcomes equal items requested*, asserted against the request.

    The count comes from the list this test sent, never from the number of rows
    that happen to exist or from a literal written beside it. That is the whole
    of the invariant: a batch that quietly answered for two of three items would
    pass any assertion phrased against the data.
    """
    requested = [
        raised_by(SUBMITTER, AMOUNT),
        raised_by(SUBMITTER, AMOUNT),
        raised_by(SUBMITTER, AMOUNT),
    ]

    decided = _decide(APPROVER, requested)

    assert len(decided[FOLD_KEY]) == len(requested)
    # And in the order they were named, which is how a caller tells which answer
    # belongs to which item. These three are permitted, so each carries the row
    # it decided — a refusal carries none, and that is the half the rule is
    # about: one that named its row would make `not_found` on a foreign row
    # distinguishable from `not_found` on a row that never existed.
    assert [answer["requisition"]["id"] for answer in decided[FOLD_KEY]] == requested


def test_the_declared_key_and_the_rendered_one_are_one_key() -> None:
    """The key layer 1 renders under, and the key layer 3 declares, are the same word.

    It is written twice in `src/` because the two packages import nothing from
    each other and a constant they shared would have to live in layer 2 — which
    would then hold a value describing how layer 1 renders. Nothing on either
    side can catch them drifting apart: layer 3 would publish an `outputSchema`
    describing a body no call produces, and every existing assertion would still
    pass. So the equality is asserted at the one altitude that sees both.
    """
    requested = [raised_by(SUBMITTER, AMOUNT), raised_by(SUBMITTER, AMOUNT)]

    rendered = _decide(APPROVER, requested)
    declared = _declaration()["outputSchema"]

    # The folded body carries the answers and nothing else, so its one key is
    # the key — read off the response rather than assumed from the constant.
    (key,) = rendered
    assert key == FOLD_KEY
    assert key in declared["properties"]
    assert {"required": [key]} in declared["oneOf"]


def _declaration() -> dict[str, Any]:
    """`approve_requisition` as `tools/list` publishes it."""
    tools = rpc.result(rpc.post("tools/list", token=mint(APPROVER, ["erp.decide"]).access_token))
    (declared,) = [entry for entry in tools["tools"] if entry["name"] == APPROVE]
    published: dict[str, Any] = declared
    return published


def test_a_single_item_call_renders_its_outcome_directly() -> None:
    """One outcome is the body, not a list holding one.

    Layer 1 counts outcomes and has nothing else to count: it never learns the
    tool's name nor which argument was the batch, so a one-item call here and a
    `get_requisition` call are the same shape of thing to it. The price is
    visible in this tool's `outputSchema`, which declares both bodies.
    """
    identifier = raised_by(SUBMITTER, AMOUNT)

    decided = _decide(APPROVER, [identifier])

    assert FOLD_KEY not in decided
    assert decided["requisition"]["id"] == identifier
    assert decided["purchase_order"]["requisition"]["id"] == identifier


def test_a_list_tool_returning_several_rows_still_answers_with_one_outcome() -> None:
    """**Result rows are not outcomes**, so listing never reaches the fold.

    Three requisitions in one result is one outcome containing three rows. The
    failure this forbids is layer 1 counting rows rather than outcomes, which
    would fold a listing into a list of one-row bodies and make every read tool
    a batch.
    """
    result = rpc.result(rpc.call_tool(LIST, {}, token=mint(APPROVER, ["erp.read"]).access_token))

    assert result["isError"] is False, result
    listed = result["structuredContent"]
    assert FOLD_KEY not in listed
    assert len(listed["requisitions"]) > 1


def test_layer_1_names_no_tool_and_no_batch_argument() -> None:
    """The negative guarantee, read off layer 1's own source.

    Docstrings are stripped first, and they have to be: the guarantee is
    *stated* in two of these modules, and a check that read prose would fail on
    the sentence describing what it asserts. What is left is the code — every
    identifier, attribute, argument name and string literal layer 1 actually
    runs — and none of it may name a tool or the argument that carries the
    batch.

    `import-linter` holds the other half: layer 1 imports nothing from layer 3,
    so the only way one of these names could get here is as a literal.
    """
    forbidden = {
        "approve_requisition",
        "get_requisition",
        "list_requisitions",
        "submit_requisition",
        "record_invoice",
        "ids",
    }

    # `rglob`, so the guarantee survives layer 1 growing a sub-package. It is
    # flat today, and a check that held only while it stayed flat would be one
    # directory away from asserting nothing.
    for module in sorted(Path(transport.__file__).parent.rglob("*.py")):
        assert _vocabulary(module) & forbidden == set(), module.name


def _vocabulary(module: Path) -> set[str]:
    """Every word layer 1's code uses, with the prose it is documented in removed."""
    tree = ast.parse(module.read_text(encoding="utf-8"))
    _strip_docstrings(tree)

    words: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            words.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", node.value))
        elif isinstance(node, ast.Name):
            words.add(node.id)
        elif isinstance(node, ast.Attribute):
            words.add(node.attr)
        elif isinstance(node, ast.arg):
            words.add(node.arg)
        elif isinstance(node, ast.keyword) and node.arg is not None:
            words.add(node.arg)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            words.add(node.name)
    return words


def _strip_docstrings(tree: ast.Module) -> None:
    """Replace every docstring with a statement that says nothing.

    Replaced rather than removed, because a body may hold nothing else and an
    empty one is not parseable back out. Attribute docstrings — the bare string
    after an assignment, which is most of this project's prose — are not
    docstrings to :mod:`ast` at all, so they are dropped by the same walk that
    finds the real ones.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        node.body = [ast.Pass() if _is_prose(statement) else statement for statement in node.body]


def _is_prose(statement: ast.stmt) -> bool:
    """Whether this statement is a bare string — a docstring, or one documenting a name."""
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )
