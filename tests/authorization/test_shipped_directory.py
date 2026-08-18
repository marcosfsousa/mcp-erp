"""The directory the server actually runs on: the committed file, held in memory.

`test_directory.py` beside this one proves the mechanism against stand-in rows.
This file proves the wiring — that `lookup` answers from the rendered artifact,
that the file and the renderer agree on one format, and that reading it costs
no database and no Docker.
"""

from pathlib import Path

import pytest

from mcp_erp.authorization import Claims, Principal, PrincipalDirectory
from mcp_erp.authorization.directory import DirectoryEntry, parse_directory, shipped_directory
from mcp_erp.authorization.identity import (
    DIRECTORY_RENDERING,
    SEED,
    directory_entries,
    read_identity_seed,
    render_directory,
)

REPO = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def entries() -> tuple[DirectoryEntry, ...]:
    """The rows the committed seed describes, read at test time rather than at import."""
    return directory_entries(read_identity_seed((REPO / SEED).read_text(encoding="utf-8")))


def test_lookup_answers_from_the_committed_file(entries: tuple[DirectoryEntry, ...]) -> None:
    """Every rendered row resolves, with the roles and partition it was rendered with."""
    directory = shipped_directory()

    for entry in entries:
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


def test_a_stranger_misses_against_the_shipped_rows(
    entries: tuple[DirectoryEntry, ...],
) -> None:
    """The rows are the cast, not everyone: an unknown subject still gets no principal."""
    claims = Claims(
        issuer=entries[0].issuer, subject="nobody-the-seed-names", granted_scopes=frozenset()
    )

    assert shipped_directory().lookup(claims) is None


def test_the_renderer_and_the_reader_agree_on_one_format(
    entries: tuple[DirectoryEntry, ...],
) -> None:
    """The round trip, asserted, so the writer and the reader cannot drift apart.

    Both sides are layer 2's — ADR-0013 gives it the shape, the implementation
    and the renderer — and this is what stops that ownership becoming two
    formats that only nearly agree.
    """
    seed = read_identity_seed((REPO / SEED).read_text(encoding="utf-8"))

    assert parse_directory(render_directory(seed)) == entries


def test_the_committed_file_needs_nothing_but_itself_to_be_read(
    entries: tuple[DirectoryEntry, ...],
) -> None:
    """No database, no Docker, no authorization server: bytes in, a directory out.

    Resolving roles from the authorization server per request was never
    available — ADR-0006 rejected a hard per-request dependency on it — and a
    directory table in Postgres would have made layer 2's only shipped
    implementation one the ejection test cannot run.
    """
    committed = (REPO / DIRECTORY_RENDERING).read_text(encoding="utf-8")

    directory = PrincipalDirectory(parse_directory(committed))

    assert directory.lookup(
        Claims(issuer=entries[0].issuer, subject=entries[0].subject, granted_scopes=frozenset())
    )
