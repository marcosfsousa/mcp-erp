"""Layer 3's two loaders, and the falsifier behind each refusal they promise.

`tests/authorization/test_identity.py` is this file's model and its counterpart:
that one holds layer 2's half of the seed to what its docstring promises, and
this one holds layer 3's half and the decision matrix to theirs. Both are run by
`Seed renders clean` beside the re-render it already refuses a diff on — a
re-render catches a hand-edited rendering, and a test catches a loader that
stopped refusing.

**A falsifier per refusal, for the refusals here.** #81 found eight checks whose
docstrings named a refusal the code did not make, and a promise with no falsifier
is how that happens: the `Raises:` list is prose until something feeds it the
input it names. Four promises are fed below, by six cases: three of the four
`read_organisation` declares — a person charged to a centre the seed does not
list, a duplicated cost-centre code, a duplicated vendor identifier — and, three
ways, the one `read_matrix` makes about a row's per-tool expectation.

**That is not the whole of either `Raises:` list, and this file does not claim
it is.** `read_organisation`'s fourth, two people sharing a subject, has no case
here, and neither do the shape and value refusals `_given` and `_expect` make —
a missing fixture field, a status outside the vocabulary, an amount that is not
decimal. A refusal with no case here is a promise still unfed; adding the input
it names is the standing way to close one, and it belongs in this file when
somebody does.

**Not in `tests/matrix/`.** That directory is driven from the table in its
entirety and its invariants file says so — it asserts the parser's refusals by
their effect on the committed table rather than by restating them against
synthetic input. Feeding a loader a document built to be rejected is the other
question, and it belongs beside the loader rather than beside the table.

Nothing here needs Compose. Both loaders are pure functions over text.
"""

import json
from typing import Any

import pytest

from mcp_erp.purchase_to_pay.fixtures import read_matrix
from mcp_erp.purchase_to_pay.organisation import read_organisation
from mcp_erp.purchase_to_pay.reasons import REASONS as DOMAIN_REASONS


def test_a_duplicated_cost_centre_code_is_refused() -> None:
    """The code is what every person row and every requisition points at.

    Two centres sharing one is a primary key that is not unique — the load fails
    on the constraint, or worse succeeds against whichever row won and charges
    the exhibit's requisitions to a centre nobody chose. Either way the diagnosis
    arrives at boot, naming a database object rather than the line of the seed
    that caused it.
    """
    with pytest.raises(ValueError, match="duplicate cost centre 'CC-1'"):
        read_organisation(_organisation_text(codes=["CC-1", "CC-1"]))


def test_a_duplicated_vendor_id_is_refused() -> None:
    """The same argument as the centre code, for the other key the rows point at.

    `submit_requisition` resolves a vendor name to this identifier, so two
    vendors sharing one makes the lookup answer arbitrarily — a wrong row
    written rather than a call refused, which is the worse of the two failures.
    """
    with pytest.raises(ValueError, match="duplicate vendor 'V-1'"):
        read_organisation(_organisation_text(vendors=["V-1", "V-1"]))


def test_a_person_charged_to_a_centre_the_seed_does_not_list_is_refused() -> None:
    """The refusal the loader already made, which had no falsifier either.

    #81's rule is that a `Raises:` list carries no promise without a check *and*
    no check without a line. This is the second half: the refusal was real, and
    nothing fed it the input it names.
    """
    with pytest.raises(ValueError, match="which the seed does not list"):
        read_organisation(_organisation_text(person_centre="CC-9"))


def test_a_per_tool_expectation_on_the_wrong_tool_is_refused() -> None:
    """`charged_to` is `submit_requisition`'s word, and a listing row may not borrow it.

    The hole the parser's own `.get()` argument was written to close and did not:
    it checked that a key is one of the three it knows and that no row states
    two, both of which a known key on the wrong tool passes. The row then expects
    nothing at all, and the defect surfaces as a wire assertion in the Compose
    job rather than here.
    """
    with pytest.raises(ValueError, match=r"expects \['tools'\], and row 'a_row' states"):
        read_matrix(_matrix_text(tool="tools/list", expect={"tools": [], "charged_to": "CC-1"}))


def test_a_permitted_row_omitting_its_own_tools_expectation_is_refused() -> None:
    """The other direction, and the one that makes a row assert only its decision.

    Two tools own a per-tool key — `list_requisitions` and `submit_requisition`
    — and so does the listing, which is not one. A permitted row on any of the
    three that states none has said the call goes through and nothing about what
    came back, which is the assertion this table exists instead of.
    """
    with pytest.raises(ValueError, match=r"expects \['tools'\], and row 'a_row' states \[\]"):
        read_matrix(_matrix_text(tool="tools/list", expect={}))


def test_a_refused_row_stating_a_per_tool_expectation_is_refused() -> None:
    """A refused call wrote nothing and returned nothing, so there is nothing to assert.

    The biconditional's third corner. Stated as a refusal rather than tolerated,
    because a `charged_to` on a refused row asserts against a requisition the run
    never created.
    """
    with pytest.raises(ValueError, match=r"expects \[\], and row 'a_row' states \['charged_to'\]"):
        read_matrix(
            _matrix_text(
                tool="submit_requisition",
                expect={"charged_to": "CC-1"},
                decision="refused",
                reason=next(iter(DOMAIN_REASONS)).value,
            )
        )


def _organisation_text(
    codes: list[str] | None = None,
    vendors: list[str] | None = None,
    person_centre: str | None = None,
) -> str:
    """A minimal organisation, for the defects the committed seed cannot show.

    Written as JSON, which `yaml.safe_load` reads because JSON is YAML. Building
    these as indented text would put the loader under test behind a second thing
    that can be got wrong, which is what `tests/authorization/test_identity.py`'s
    `_seed_text` accepts in exchange for reading like the file it stands in for —
    a trade worth making there, where the seed's own shape is part of the
    assertion, and not here, where only the collision is.
    """
    codes = codes or ["CC-1"]
    vendors = vendors or ["V-1"]
    return json.dumps(
        {
            "cost_centres": [
                {"code": code, "name": f"Centre {index}"} for index, code in enumerate(codes)
            ],
            "people": [
                {
                    "subject": "a-person",
                    "name": "A Person",
                    "cost_centre": person_centre or codes[0],
                }
            ],
            "vendors": [
                {"id": vendor, "name": f"Vendor {index}"} for index, vendor in enumerate(vendors)
            ],
        }
    )


def _matrix_text(
    *,
    tool: str,
    expect: dict[str, Any],
    decision: str = "permitted",
    reason: str | None = None,
) -> str:
    """A one-row matrix, for the malformed expectation blocks the table cannot hold.

    JSON for the same reason :func:`_organisation_text` is. `meta` is present
    because the parser carries it through, and empty because nothing here reads
    it.
    """
    return json.dumps(
        {
            "meta": {},
            "rows": [
                {
                    "id": "a_row",
                    "principal": {"person": "priya.raman", "scopes": []},
                    "tool": tool,
                    "given": None,
                    "expect": {"decision": decision, "reason": reason, **expect},
                }
            ],
        }
    )
