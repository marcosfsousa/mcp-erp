# mcp-erp

A portfolio exhibit: a Model Context Protocol server exposing a mock enterprise resource planning system, with OAuth 2.0 as a first-class concern. Two vocabularies meet here — the protocol and authorization language the exhibit exists to demonstrate, and the purchase-to-pay language it demonstrates them on. Keep them distinct; conflating them is how the exhibit's point gets lost.

## How this binds

Every entry's _Avoid_ line is a hard rule in **binding text**: the write-up,
this file, ADRs, and anything that ships — code identifiers, tool and field
names, scope strings, reason values.

In **working text** — research notes, issue and pull request bodies, commit
messages, code comments — the _Avoid_ line is advice. Abbreviate freely after
one spelled-out use. The vocabulary exists so a technical reader meets each
idea named the same way every time. A tracker has no such reader.

## Language

### The exhibit

**Exhibit**:
This project. A built artifact whose purpose is to make two things legible to a technical reader, not to serve users.
_Avoid_: product, app, service

**Governing rule**:
The project's own constraint that an entity or field earns its place only if it changes an authorization decision.
_Avoid_: minimalism, YAGNI

### Protocol and era

**Modern era**:
Protocol revisions from `2026-07-28` onward, which removed connection initialization entirely.
_Avoid_: current spec, latest revision

**Legacy era**:
Protocol revisions before `2026-07-28`, which negotiate a connection first. Discussable in the write-up, deliberately not built.
_Avoid_: old protocol, deprecated version, session-based

**Dual-era server**:
A server that answers callers from both eras. There is no fall-forward between them, so supporting both is a deliberate act.
_Avoid_: backwards-compatible server

**Authorization server**:
The party that authenticates a person and issues access tokens.
_Avoid_: identity provider, IdP, AS, auth server, token service

**Resource server**:
This server in its token-validating capacity — the party that must reject tokens not audience-bound to it.
_Avoid_: API server, backend

**Client Identity Metadata Document**:
A document hosted by a client that identifies it to an authorization server, standing in place of dynamic registration.
_Avoid_: CIMD, client metadata

**Conformance client**:
A client written for this project to exercise the protocol end to end and assert on the wire. A demonstrator, not a dependency.
_Avoid_: test client, harness

### Authorization

**Principal**:
A Person together with the set of scopes their access token carries. The two halves vary independently — the same Person is a different Principal under a narrower token.
_Avoid_: user, caller, subject, actor

**Granted scope**:
A permission string carried inside an access token, agreed when a person authorizes an application. It is a ceiling on what the application may do on their behalf, not a statement of what they are allowed to do.
_Avoid_: permission, entitlement, grant

**Capability**:
A member of the fixed vocabulary a tool declares, naming what a token must carry to reach it. Joined to a namespace to build a scope string, and never parsed back out of one.
_Avoid_: permission, action, scope, verb

**Role**:
A standing grant of authority held by a Person and resolved server-side per request, never carried in the token.
_Avoid_: group, permission, claim

**Effective permission**:
Granted scope intersected with role permission, with relationship rules applied last.
_Avoid_: access level, authorization

**Relationship rule**:
A rule decided by the identities and amounts involved rather than by the caller alone — segregation of duties and the approval threshold.
_Avoid_: business rule, policy

**Partition**:
The single-valued attribute of a Principal that row scoping compares against. Layer 2's name for the value; layer 3 supplies it from the Person's cost centre. Carried as `principal.partition` and `resource.partition`, with a per-Action set of bypass roles.
_Avoid_: tenant, row scope, unit, cost centre (which is the layer-3 name for what fills it)

**Row scoping**:
Restricting which records a Principal may see to those sharing their partition — one equality check, plus a set of roles that bypass it. The mechanism keeps this name; the attribute it reads is the partition. In the purchase-to-pay layer the partition is the cost centre, and `auditor` is the bypass role on the two read tools.
_Avoid_: filtering, tenant isolation, multi-tenancy

**Segregation of duties**:
The requirement that two steps which check each other be performed by different people.
_Avoid_: SoD, four-eyes principle, dual control (a distinct and rejected mechanism)

**Approval threshold**:
The amount above which approving a requisition requires a more senior role.
_Avoid_: limit, ceiling, spending cap

**Refusal**:
Any authorization decision that stops a call. Deliberately not "error" — two of the three kinds are not errors in any protocol sense.
_Avoid_: error, failure, rejection, denial

**Denial class**:
One of the three shapes a refusal takes on the wire, chosen by what would fix it for the caller.
_Avoid_: error type, status

**Reason**:
The value from a closed vocabulary naming why a refusal happened.
_Avoid_: error code, message, detail

**Remedy**:
What would resolve a refusal, expressed as a class of action — re-authorize, an administrator grants, a different person acts. Never a named human, and never a promise that such a person exists.
_Avoid_: fix, resolution, next step

### Identity and organisation

**Person**:
A named human in the seeded organisation, holding exactly one cost centre. Roles are **not** held here — they are policy facts, kept in the principal directory alongside the issuer and subject that identify the Person to the authorization layer.
_Avoid_: user, account, employee, persona

**Principal directory**:
The layer-2 record mapping an issuer-and-subject pair to a set of roles and a partition. Owned by the authorization layer, rendered from the seed, and consulted once per request between token validation and the first gate. Its shape survives ejection of the domain; only its rows are domain-supplied.
_Avoid_: user table, identity store, profile

**Cast**:
The named People seeded into the exhibit. Each one exists to make some branch of the decision matrix reachable.
_Avoid_: test users, personas, dummy data

**Cost centre**:
A flat accounting bucket owning a budget. Every Person holds exactly one; every requisition is charged to one. There is no hierarchy and no shared membership.
_Avoid_: department, team, org unit, tenant, business unit

**Organisation**:
The hand-authored half of the seed — the Cast, the cost centres, the vendors. Stable and legible, as opposed to the generated fixtures.
_Avoid_: master data, reference data

### Purchase-to-pay

**Purchase-to-pay**:
The domain this exhibit models: raising a request to buy something, approving it, and recording the resulting bill.
_Avoid_: P2P, procure-to-pay, procurement

**Chain**:
One requisition together with everything descending from it. Segregation of duties is stated in terms of positions on a single chain.
_Avoid_: workflow, process, transaction, flow

**Requisition**:
A request to buy something from a vendor, charged to the submitter's own cost centre.
_Avoid_: purchase request, order, requisition request, PR

**Purchase order**:
The record emitted when a requisition is approved. It is what carries the approver's identity forward.
_Avoid_: PO in prose, order

**Invoice**:
The record that a purchase order has been billed.
_Avoid_: bill, payment request, receipt

**Vendor**:
A party a requisition may be raised against.
_Avoid_: supplier, merchant, counterparty

**Submitter**, **Approver**, **Invoice recorder**:
Positions occupied on one chain, as distinct from roles. A role is held standing; a position is occupied once, by one Person, on one chain — which is why segregation of duties is checked against positions and never against roles. **Approver names both a role and a position, deliberately**: the role is held standing, the position is occupied once on one chain, and it is the position segregation of duties is checked against.
_Avoid_: requester, authorizer, clerk

### Proof artifacts

**Decision matrix**:
The expectations of who may do what to which record, held as data and rendered into tests, fixtures and the write-up alike. Never a language of its own.
_Avoid_: test matrix, permission matrix, access control list

**Attack suite**:
Named scenarios, each citing the specification or standard clause it defends.
_Avoid_: security tests, penetration tests, negative tests

**Fixture**:
A disposable seeded record owned outright by one matrix row, generated from that row rather than hand-written.
_Avoid_: test data, seed data, sample
