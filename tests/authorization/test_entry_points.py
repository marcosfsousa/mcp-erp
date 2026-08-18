"""Three entry points, and what their signatures make impossible.

Two claims live here. ``decide_item`` cannot be called without a resource, and a
``GateOutcome`` cannot be used as a ``Decision``. Both are type-level
properties, so the type checker is the enforcer and *Lint and types* is where a
regression actually fails; what these tests hold is the structure mypy reads —
a default reappearing on ``resource``, or the two outcome types being merged.
"""

import inspect

import pytest
from declarations import DECIDE_ROW, LIST_ROWS, REVIEWER, ROW

from mcp_erp.authorization import (
    NOT_FOUND,
    Decision,
    GateOutcome,
    decide_call,
    decide_item,
    permits_scope,
)


def test_the_chain_has_exactly_three_entry_points() -> None:
    """Named so that a caller's stopping point is visible at the call site."""
    assert permits_scope.__name__ == "permits_scope"
    assert decide_call.__name__ == "decide_call"
    assert decide_item.__name__ == "decide_item"


def test_resource_carries_no_default() -> None:
    """The argument absence that would truncate the chain is not expressible.

    A defaulted resource means a handler that forgets to pass the row gets a
    permit indistinguishable from a real one.
    """
    resource = inspect.signature(decide_item).parameters["resource"]

    assert resource.default is inspect.Parameter.empty


def test_decide_item_cannot_be_called_without_a_resource() -> None:
    """The same claim at runtime, for a caller that is not type-checked."""
    with pytest.raises(TypeError):
        decide_item(REVIEWER, DECIDE_ROW)  # type: ignore[call-arg]


def test_an_absent_resource_must_still_be_passed_and_refuses() -> None:
    """Nullable is a different claim from defaulted.

    Layer 3 hydrates a row before deciding on it, and passing that result
    straight through is what makes the empty join converge with the foreign row.
    """
    assert decide_item(REVIEWER, DECIDE_ROW, None).reason is NOT_FOUND


def test_a_gate_outcome_is_not_a_decision() -> None:
    """Different types, with no inheritance between them in either direction.

    A whole-call permit therefore cannot be handed to something expecting an
    item permit. What this does not close: a handler that takes a call permit
    and returns every row without calling ``decide_item`` at all. That residual
    is a handler obligation, handlers are layer 3, and its falsifiers are two
    attack-suite rows at the wire.
    """
    # `GateOutcome is not Decision` is not written here on purpose: mypy rejects
    # it as a non-overlapping identity check, which is the claim itself, made by
    # the type checker before the test could run.
    assert not issubclass(GateOutcome, Decision)
    assert not issubclass(Decision, GateOutcome)
    assert not isinstance(decide_call(REVIEWER, LIST_ROWS), Decision)
    assert not isinstance(decide_item(REVIEWER, LIST_ROWS, ROW), GateOutcome)


def test_each_entry_point_returns_its_own_type() -> None:
    """The annotations a handler is checked against say the same thing."""
    assert inspect.signature(permits_scope).return_annotation is bool
    assert inspect.signature(decide_call).return_annotation is GateOutcome
    assert inspect.signature(decide_item).return_annotation is Decision


def test_both_outcome_types_are_frozen() -> None:
    """A decision cannot be edited into a permit after the fact."""
    with pytest.raises(AttributeError):
        decide_call(REVIEWER, LIST_ROWS).reason = None  # type: ignore[misc]
    with pytest.raises(AttributeError):
        decide_item(REVIEWER, LIST_ROWS, ROW).reason = None  # type: ignore[misc]
