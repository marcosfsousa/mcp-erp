"""The three beats a minted token can perform, and the README's two derived regions.

`tests/transcripts.py` is what a transcript *is*; this is what drives the half of
them that needs no consent screen. The split is not cosmetic: the flow client
imports that module to snapshot what it saw, and it is independent of layer 3 on
purpose — while every beat here names a seeded row, so this one reads
`tests/fixtures.py` and the domain it belongs to.

**The other three beats are written by the run that earns their tokens.**
Keycloak remembers a grant per Person and client, so a second flow in a second
process would post one form where the first posted two;
`tests/conformance/test_authorization_code_flow.py` therefore writes the earned
beats from the flows it already performs. Both writers write into one directory
that one check reads.

Run it from a checkout, against Compose, to re-capture::

    uv run python tests/capture.py

Or re-render the README's two derived regions — the short form's card and the
one embedded proof — from the committed captures, which needs nothing running::

    uv run python tests/capture.py --include
"""

from __future__ import annotations

import argparse
import sys

import fixtures
import rpc
import transcripts
from tokens import mint


def main(argv: list[str] | None = None) -> int:
    """Capture the minted beats against Compose, or re-render the README's derived regions.

    Two modes rather than two commands, on the terms `tests/conformance_client.py`
    states for its own pair: they are two halves of one job, and the two jobs that
    run them are different — `Authorization code flow` captures with the stack up,
    and `Seed renders clean` includes with nothing running at all.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--include",
        action="store_true",
        help="only re-render the README's derived regions from the committed captures",
    )
    arguments = parser.parse_args(argv)

    return _include() if arguments.include else _capture()


def _include() -> int:
    """Rewrite both of the README's marked regions from the committed capture."""
    committed = transcripts.COMMITTED / f"{transcripts.PROOF}{transcripts.SUFFIX}"
    rendered = transcripts.include(
        transcripts.README.read_text(encoding="utf-8"),
        committed.read_text(encoding="utf-8"),
    )

    transcripts.README.write_bytes(rendered.encode("utf-8"))
    print(f"included {transcripts.PROOF} in README.md, as a card and as the proof")

    return 0


def _capture() -> int:
    """Drive the three minted beats and commit whatever the mask calls new."""
    fixtures.load()

    for name, exchanges in (
        (transcripts.UNDER_SCOPED, _under_scoped()),
        (transcripts.SEGREGATION_OF_DUTIES, _segregation_of_duties()),
        (transcripts.ROW_SCOPED_NOT_FOUND, _row_scoped_not_found()),
    ):
        rewritten = transcripts.keep(name, transcripts.render(name, exchanges))
        print(f"{'captured ' if rewritten else 'unchanged'}  {name}{transcripts.SUFFIX}")

    return 0


def _under_scoped() -> tuple[transcripts.Exchange, ...]:
    """ADR-0002's first denial class: the tool is not in the listing, and asking says why.

    Two exchanges rather than one, because the class is two facts. A token
    carrying read and write reaches four tools and `approve_requisition` is not
    among them — absence, which is the whole of what a conformant client sees.
    The same token calling it anyway is answered `403` with a challenge naming
    the scope it would need, which is the remedy ADR-0002 maps that class to.

    The row is `approve_refused_without_the_deciding_scope`'s own fixture, so the
    call is refused for the reason the matrix says and not for want of a row.
    """
    token = mint("tomas.weber", ["erp.read", "erp.write"]).access_token
    row = fixtures.owned_by("approve_refused_without_the_deciding_scope").id

    return (
        transcripts.snapshot(rpc.post("tools/list", token=token)),
        transcripts.snapshot(
            rpc.call_tool("approve_requisition", {"ids": [row], "decision": "approve"}, token=token)
        ),
    )


def _segregation_of_duties() -> tuple[transcripts.Exchange, ...]:
    """The third class: a domain rejection, which is not an authorization error at all.

    Tomas Weber holds the deciding role, carries the deciding scope and is in the
    row's own partition — every authorization gate lets him through — and the
    chain refuses him because he raised it himself. It comes back as a result
    marked in error with a structured payload, not as a protocol error and not as
    a challenge, which is the distinction ADR-0002 spent its argument on.
    """
    token = mint("tomas.weber", ["erp.decide"]).access_token
    row = fixtures.owned_by("approve_refuses_the_approvers_own_requisition").id

    return (
        transcripts.snapshot(
            rpc.call_tool("approve_requisition", {"ids": [row], "decision": "approve"}, token=token)
        ),
    )


def _row_scoped_not_found() -> tuple[transcripts.Exchange, ...]:
    """Row scoping, as the pair that makes it a claim rather than a refusal.

    Yusuf Demir reads a requisition in CC-4100, which exists and is not his, and
    then reads an identifier no row carries at all. The two answers are the same
    bytes — which is `row_probe_indistinguishable`, and the reason the normative
    register carries *Legible identifiers*: unguessable identifiers would leave
    this demonstrable only by handing the probe the row it is meant to guess.
    """
    token = mint("yusuf.demir", ["erp.read"]).access_token
    row = fixtures.owned_by("get_refuses_a_row_in_another_partition").id

    return (
        transcripts.snapshot(rpc.call_tool("get_requisition", {"id": row}, token=token)),
        transcripts.snapshot(
            rpc.call_tool("get_requisition", {"id": fixtures.ABSENT_IDENTIFIER}, token=token)
        ),
    )


if __name__ == "__main__":
    sys.exit(main())
