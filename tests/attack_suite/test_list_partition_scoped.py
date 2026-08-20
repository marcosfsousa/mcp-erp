"""`list_partition_scoped` — a listing returns the caller's partition and no other.

Scenario: `list_partition_scoped`, `basis: adr`, sourced to ADR-0013 §Named
versus discovered — the refusal contract.

    removal: Return the unfiltered result set after the whole-call gate permits,
             without evaluating row scoping per row.

The other half of the refusal contract from `row_probe_indistinguishable`:

    A resource **named** in the request is refused, never omitted.
    A resource **discovered** by listing is omitted, never refused.

Only the first half had a falsifier before ADR-0013 declared this row. The gap
it closes is a real one and no signature closes it: layer 2 gives the policy
function three entry points, and the type split stops a whole-call permit being
*used* as an item permit — but a handler that takes the whole-call permit and
returns every row type-checks cleanly and fails open. Choosing the entry point is
a handler obligation, handlers are layer 3, and `tests/authorization/` survives
ejection precisely by having none. So the falsifier lives here, at the wire.

**Set equality over returned identifiers**, never order: row scoping is a
question of which rows come back, and no entity carries a timestamp, so there is
no order to assert that the authorization model has an opinion about.
"""

from collections.abc import Iterator

import pytest
from scenarios import exercises

import fixtures
import requisitions as visible
import rpc
from tokens import mint

TOOL = "list_requisitions"


@pytest.fixture(scope="module", autouse=True)
def requisitions() -> Iterator[None]:
    """Wipe and reload the rows **once before this module**, never between tests.

    In the test module rather than in a `conftest.py`, for a reason worth stating
    because it will come up again at #44: `tests/conftest.py` already exists and
    the types job runs over `tests/`, so a second file of that name is a
    duplicate module to mypy — with no `__init__.py` anywhere to tell them apart,
    and adding one would change how every existing suite is imported.

    Session-shaped in spirit and module-scoped in fact: nothing here writes, so
    the reload is about starting from a known set rather than about isolation.
    ADR-0003 chose that shape and named the alternative it was avoiding — a
    test-only reset route on a server whose entire subject is authorization.
    """
    fixtures.load()
    yield


@exercises("list_partition_scoped")
def test_a_caller_sees_their_own_cost_centre_and_no_other() -> None:
    """Tomas Weber holds CC-4100, so he sees CC-4100's rows and exactly those.

    This is the ticket's own criterion — *returns only the caller's partition,
    asserted as set equality* — and set equality is what makes it one. A subset
    assertion would pass on a handler that returned nothing; a membership
    assertion would pass on a handler that returned everything.
    """
    assert visible.visible_to("tomas.weber") == fixtures.identifiers_in("CC-4100")


@exercises("list_partition_scoped")
def test_another_partition_sees_a_disjoint_set() -> None:
    """Yusuf Demir is everything Tomas is, in another centre.

    He exists in the cast for this: the same role, the same scope set, a
    different partition — so a listing that ignored the partition would return
    the same rows to both and this pair would catch it.
    """
    assert visible.visible_to("yusuf.demir") == fixtures.identifiers_in("CC-4200")
    assert not visible.visible_to("yusuf.demir") & visible.visible_to("tomas.weber")


@exercises("list_partition_scoped")
def test_the_third_centre_is_its_own_answer() -> None:
    """Mei Tanaka's centre exists so that three of three is distinguishable from two.

    Without a third inhabited cost centre, an auditing role reading *all* of them
    would be indistinguishable from a principal who merely belonged to two — and
    the whole reason breadth is a role rather than a wider membership would stop
    being observable.
    """
    assert visible.visible_to("mei.tanaka") == fixtures.identifiers_in("CC-4300")


@exercises("list_partition_scoped")
def test_the_auditing_role_reads_across_every_partition() -> None:
    """Anna Lindqvist holds `auditor`, which is `partition_bypass` on this Action.

    The positive half of ADR-0013's non-uniform field: `{auditor}` on the two
    read tools and **empty on the three writes**, because breadth is a read
    widening and never a write grant. Nothing in the type objects to the wrong
    value — on the write tools the same mistake is invisible, and this assertion
    is the only place in the repository where it is not.
    """
    assert visible.visible_to("anna.lindqvist") == fixtures.every_identifier()
    # Three of three, not two: the claim is breadth by role rather than by
    # membership, and the count is what separates them.
    assert len(fixtures.cost_centres()) == 3


@exercises("list_partition_scoped")
def test_a_scoped_away_row_is_omitted_rather_than_refused() -> None:
    """Omission, not refusal — the half of the contract this row exists for.

    A listing that refused per row would be an existence oracle by another
    route: the caller would learn that a row is there and that somebody else can
    see it. So the result is a permitted result containing fewer rows, with no
    reason anywhere in it.
    """
    minted = mint("tomas.weber", ["erp.read"])
    result = rpc.result(rpc.call_tool(TOOL, token=minted.access_token))

    assert result["isError"] is False
    assert "reason" not in result["structuredContent"]
    assert set(result["structuredContent"]) == {"requisitions"}
