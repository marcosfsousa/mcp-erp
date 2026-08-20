"""The organisation generator: the seed's third rendering, in the domain's own words.

The other two renderings are layer 2's, and this one is layer 3's, because it
speaks the words layer 3 owns — cost centres, vendors, and the people who hold
them. Each generator is deleted with the layer whose vocabulary it uses, so
ejecting the domain takes this file and its rendering with it while identity
provisioning carries on (ADR-0013).

The two touch disjoint halves of the seed. This one never reads a role, a
username or the password; :mod:`mcp_erp.authorization.identity` never reads a
display name or a vendor. The one value both read is the cost centre, which
layer 2 renders as the partition — a duplication by generation, which is what
makes a drift check the right control for it (ADR-0003).

**Roles are absent from the person rows, deliberately.** They are policy facts
resolved server-side per request, not domain facts, so they live in the
principal directory beside the issuer and subject that identify the person to
the authorization layer. A `roles` column here would be a second place to hold
them and a second place for them to be wrong.

**What this module's loader refuses, and where that stops.** The same rule
layer 2's generator is bounded by: a loader refuses exactly what would otherwise
fail further away — a key the rows point at that is not unique, a foreign key
with no target — and nothing else. Type-checking every field is not on the list;
that is the seed's own shape and mypy's job, and a check per field would be a
schema written a second time. Stated in both modules rather than shared, for the
reason :data:`SEED` is: the layer that survives ejection may not hold a rule on
behalf of the layer that does not.

This is **row data, not schema**: the database and its loader arrive with the
ticket that stands Compose up, and rendering DDL here would invent a schema
this ticket does not own. What it fixes is which rows exist and what they hold.

Run it from a checkout to re-render::

    python -m mcp_erp.purchase_to_pay.organisation
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

SEED = "docs/organisation/seed.yaml"
"""The authored organisation this generator reads, relative to the repository root.

Named here as well as in layer 2's generator, deliberately. Sharing the string
would mean one layer importing it from the other for no other reason, and the
importer would be the layer that survives ejection holding a constant on behalf
of the layer that does not.
"""

ORGANISATION_RENDERING = "src/mcp_erp/purchase_to_pay/data/organisation.json"
"""Where the ERP rendering is committed, relative to the repository root.

Inside layer 3's package, so ``rm -rf src/mcp_erp/purchase_to_pay`` takes the
domain's rows with the domain — the ejection command is one deletion, and a
data directory elsewhere would leave a puddle of purchasing behind it.
"""


@dataclass(frozen=True, slots=True)
class CostCentre:
    """A flat accounting bucket owning a budget. No hierarchy, no shared membership."""

    code: str
    name: str


@dataclass(frozen=True, slots=True)
class Person:
    """A named human in the seeded organisation, holding exactly one cost centre.

    Keyed by the subject, because that is what a request arrives holding: the
    join at request time is on the standard subject claim, and a person row a
    token cannot be matched to would be a row nothing can reach.

    Attributes:
        subject: The subject claim the token names, and this row's key.
        name: The display name — the single named exception to the rule that a
            field earns its place only by changing an authorization decision.
        cost_centre: The one centre they hold. Every requisition they raise is
            charged to it, which is what makes a cross-centre submission
            inexpressible rather than merely refused.
    """

    subject: str
    name: str
    cost_centre: str


@dataclass(frozen=True, slots=True)
class Vendor:
    """A party a requisition may be raised against."""

    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Organisation:
    """The hand-authored half of the seed, in the shape the ERP holds it."""

    cost_centres: tuple[CostCentre, ...]
    people: tuple[Person, ...]
    vendors: tuple[Vendor, ...]


def read_organisation(text: str) -> Organisation:
    """Parse the domain half of the seed, refusing what the ERP's own rows cannot hold.

    Four refusals, each an instance of the rule this module's docstring states,
    and all four are layer 3's — it makes them for itself rather than inheriting
    them. A person charged to a centre nobody declared; two people sharing the
    key their rows are keyed by; and the two keys the rows *point at* being
    non-unique, a duplicated cost-centre code and a duplicated vendor
    identifier. Layer 2's generator refuses a duplicated subject too, for its own
    reason — a directory key collision — and neither layer may rely on the other
    having looked.

    Raises:
        ValueError: A person holds a cost centre the seed does not list; two
            people share a subject; two cost centres share a code; or two
            vendors share an identifier.
    """
    document = yaml.safe_load(text)

    centres: list[CostCentre] = []
    codes: set[str] = set()
    for entry in document["cost_centres"]:
        code = str(entry["code"])
        if code in codes:
            raise ValueError(f"duplicate cost centre {code!r}")
        codes.add(code)
        centres.append(CostCentre(code=code, name=str(entry["name"])))

    people: list[Person] = []
    seen: set[str] = set()
    for entry in document["people"]:
        subject = str(entry["subject"])
        cost_centre = str(entry["cost_centre"])
        if cost_centre not in codes:
            raise ValueError(
                f"person {subject!r} holds cost centre {cost_centre!r}, "
                f"which the seed does not list"
            )
        if subject in seen:
            raise ValueError(f"duplicate subject {subject!r}")
        seen.add(subject)
        people.append(
            Person(
                subject=subject,
                name=str(entry["name"]),
                cost_centre=cost_centre,
            )
        )

    vendors: list[Vendor] = []
    identifiers: set[str] = set()
    for entry in document["vendors"]:
        identifier = str(entry["id"])
        if identifier in identifiers:
            raise ValueError(f"duplicate vendor {identifier!r}")
        identifiers.add(identifier)
        vendors.append(Vendor(id=identifier, name=str(entry["name"])))

    return Organisation(
        cost_centres=tuple(centres),
        people=tuple(people),
        vendors=tuple(vendors),
    )


def render_organisation(organisation: Organisation) -> str:
    """Render the ERP's rows: the centres, the people who hold them, and the vendors.

    Byte-stable on the same terms as layer 2's renderings — sorted keys, rows in
    a fixed order, nothing generated and nothing dated — because all three are
    policed by one drift check and a check that flakes on any of them is a
    required check somebody will want turned off.
    """
    return _as_json(
        {
            "cost_centres": [
                {"code": centre.code, "name": centre.name}
                for centre in sorted(organisation.cost_centres, key=lambda centre: centre.code)
            ],
            "people": [
                {
                    "cost_centre": person.cost_centre,
                    "name": person.name,
                    "subject": person.subject,
                }
                for person in sorted(organisation.people, key=lambda person: person.subject)
            ],
            "vendors": [
                {"id": vendor.id, "name": vendor.name}
                for vendor in sorted(organisation.vendors, key=lambda vendor: vendor.id)
            ],
        }
    )


def _as_json(document: object) -> str:
    """The same serialisation layer 2's renderer uses, stated again rather than shared.

    Sharing it would put a domain-free helper in one layer and its only other
    caller in the other, so the module that survives ejection would be
    importing on behalf of the module that does not. Six identical arguments is
    the cheaper duplication.
    """
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write(path: Path, text: str) -> None:
    """Write a rendering, in bytes, with the newline the renderer chose."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def main() -> None:
    """Re-render the ERP rows from the committed seed.

    Resolves paths from this file's location, so it runs from a checkout and
    nowhere else — the rendering is committed, and the ``Seed renders clean``
    job re-runs this and fails on any diff.
    """
    repo = Path(__file__).resolve().parents[3]
    seed = (repo / SEED).read_text(encoding="utf-8")

    _write(repo / ORGANISATION_RENDERING, render_organisation(read_organisation(seed)))
    print(f"rendered {ORGANISATION_RENDERING}")


if __name__ == "__main__":
    main()
