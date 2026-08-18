"""The directory the server actually runs on: the committed file, held in memory.

`tests/test_directory.py` proves the mechanism against stand-in rows. This file
proves the wiring — that `lookup` answers from the rendered artifact, that the
file and the renderer agree on one format, and that reading it costs no
database and no Docker.
"""

from pathlib import Path

from mcp_erp.authorization import Claims, Principal, PrincipalDirectory
from mcp_erp.authorization.directory import parse_directory, shipped_directory
from mcp_erp.authorization.identity import directory_entries, read_seed, render_directory

REPO = Path(__file__).parents[2]
SEED_FILE = REPO / "docs" / "organisation" / "seed.yaml"

SEED = read_seed(SEED_FILE.read_text(encoding="utf-8"))
ENTRIES = directory_entries(SEED)


def test_lookup_answers_from_the_committed_file() -> None:
    """Every rendered row resolves, with the roles and partition it was rendered with."""
    directory = shipped_directory()

    for entry in ENTRIES:
        principal = directory.lookup(
            Claims(issuer=entry.issuer, subject=entry.subject, granted_scopes=frozenset())
        )
        assert principal == Principal(
            issuer=entry.issuer,
            subject=entry.subject,
            granted_scopes=frozenset(),
            roles=entry.roles,
            partition=entry.partition,
        )


def test_the_shipped_directory_is_read_once_and_held() -> None:
    """Immutable in memory, so a request cannot pay for a read or change who anybody is."""
    assert shipped_directory() is shipped_directory()


def test_a_stranger_misses_against_the_shipped_rows() -> None:
    """The rows are seven, not everyone: an unknown subject still gets no principal."""
    claims = Claims(issuer=SEED.issuer, subject="nobody-the-seed-names", granted_scopes=frozenset())

    assert shipped_directory().lookup(claims) is None


def test_the_renderer_and_the_reader_agree_on_one_format() -> None:
    """The round trip, asserted, so the writer and the reader cannot drift apart.

    Both sides are layer 2's — ADR-0013 gives it the shape, the implementation
    and the renderer — and this is what stops that ownership becoming two
    formats that only nearly agree.
    """
    assert parse_directory(render_directory(SEED)) == ENTRIES


def test_the_committed_file_needs_nothing_but_itself_to_be_read() -> None:
    """No database, no Docker, no authorization server: bytes in, a directory out.

    Resolving roles from the authorization server per request was never
    available — ADR-0006 rejected a hard per-request dependency on it — and a
    directory table in Postgres would have made layer 2's only shipped
    implementation one the ejection test cannot run.
    """
    committed = (REPO / "src/mcp_erp/authorization/data/principal-directory.json").read_text(
        encoding="utf-8"
    )

    directory = PrincipalDirectory(parse_directory(committed))

    assert directory.lookup(
        Claims(issuer=ENTRIES[0].issuer, subject=ENTRIES[0].subject, granted_scopes=frozenset())
    )
