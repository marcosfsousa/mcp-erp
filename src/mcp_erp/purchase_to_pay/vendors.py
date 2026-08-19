"""The vendor catalogue, read from the seed's ERP rendering at import time.

``Vendor`` has no tool of its own. ADR-0002 cut ``list_vendors`` for
demonstrating no authorization behaviour, and put the legal values in
``submit_requisition``'s input schema instead: *"its legal values are a JSON
Schema ``enum`` of names inside ``submit_requisition``, so the tool definition
**is** the lookup."* ADR-0003 adds the half that makes it honest — the enum is
*generated* from the vendor rows, so the tool definition cannot drift from the
data.

**One file feeds both sides.** ``compose.yaml`` mounts
``data/organisation.json`` into Postgres's initialisation, and this module reads
the same committed bytes, so the enum a caller chooses from and the rows the
foreign key checks against are one rendering. `Seed renders clean` re-renders it
from the seed and refuses any diff, which is what makes *cannot drift* a check
rather than a hope.

**Reading, not rendering.** :mod:`~mcp_erp.purchase_to_pay.organisation` writes
that file and this module reads it back, which is the split layer 2 already
makes between its identity generator and its directory reader. The generator is
deliberately not imported here: it has a ``__main__`` entry point, and putting it
in ``sys.modules`` ahead of ``python -m`` is what runs a module's top level twice.
"""

import json
from collections.abc import Mapping
from functools import cache
from importlib import resources
from types import MappingProxyType
from typing import Final

ORGANISATION_FILE: Final = "organisation.json"
"""The ERP rendering, inside layer 3's own package.

A package resource rather than a repository path: the server reads it wherever
it is installed, and the generator that writes it is the only thing that needs to
know where a checkout keeps it. The same argument layer 2's directory makes, and
``rm -rf src/mcp_erp/purchase_to_pay`` takes the rows with the domain.
"""


@cache
def shipped_vendors() -> Mapping[str, str]:
    """Vendor display name to identifier, read once and held immutable in memory.

    Cached because the file is a build artifact rather than configuration: it
    cannot change while the process runs, so re-reading it per call would put a
    file read on the write path and buy nothing.

    **Keyed by name because the schema enumerates names.** The caller picks a
    vendor a human can recognise and the row stores the identifier a join needs,
    so this mapping is the whole of the translation between the two — the same
    shape and the same one-line job as ``Requisition.partition``.

    Raises:
        ValueError: Two vendors share a display name, which would make the enum
            ambiguous and the lookup below arbitrary. A rendering defect, so it
            fails at the first call of the process rather than on whichever
            submission happened to name the duplicated one.
    """
    package = resources.files(__package__)
    document = json.loads(package.joinpath("data", ORGANISATION_FILE).read_text(encoding="utf-8"))

    catalogue: dict[str, str] = {}
    for vendor in document["vendors"]:
        name = str(vendor["name"])
        if name in catalogue:
            raise ValueError(f"duplicate vendor name {name!r}")
        catalogue[name] = str(vendor["id"])

    return MappingProxyType(catalogue)


def names() -> list[str]:
    """The legal values of the ``vendor`` input, sorted, for a tool's ``enum``.

    Sorted rather than left in the rendering's order, which is already sorted by
    identifier: an enum is a set, and a schema whose member order tracked a file's
    would change whenever the file did without changing what it permits.
    """
    return sorted(shipped_vendors())


def identifier_for(name: str) -> str:
    """The identifier of the vendor with this display name.

    Raises:
        ValueError: No vendor carries that name. The tool's schema enumerates
            every legal value, so this is an argument the declaration already
            forbade — layer 1 renders it as *invalid params*, which is what the
            protocol says about a request it cannot act on. It is deliberately
            **not** a refusal: nothing was authorized or denied, and giving it a
            ``Reason`` would amend a closed vocabulary for a spelling mistake.
    """
    identifier = shipped_vendors().get(name)
    if identifier is None:
        raise ValueError(f"no such vendor: {name!r}")
    return identifier
