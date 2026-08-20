-- The ERP's schema, which ADR-0003 calls the policy function's argument list.
--
-- Every column here is transcribed from that ADR's entity table and its four
-- rules; nothing is invented. The governing rule is that a field earns its
-- place only if it changes an authorization decision, with one named exception
-- granted for the reader's benefit — `description`, and the display name on a
-- person, which narrate in a way `req_0104` does not.
--
-- Three things are deliberately absent, and each has an owner:
--
--   roles        Policy facts, not domain facts. They live in the principal
--                directory, beside the issuer and subject that identify a
--                person to the authorization layer. A column here would be a
--                second place to hold them and a second place for them to be
--                wrong.
--   timestamps   No entity carries one. ADR-0003 left *when things happened*
--                to the audit-trail work with a blank page, and the cost is
--                stated there: list results have no defined order until
--                somebody specifies one.
--   an editor    There is no update tool among the five, so a requisition is
--                immutable once submitted and no editor identity exists to
--                reason about.
--
-- The three tables below the organisation are empty at boot, and they stay that
-- way: their rows are the seed's *other* half — per-row fixtures generated from
-- `docs/decision-matrix/matrix.yaml` since #43 — and they are loaded by the
-- suites rather than by this directory. ADR-0003 chose a wipe per run over a
-- reset between rows, and the alternative it rejected is a test-only reset route
-- on a server whose entire subject is authorization; so the loader is
-- `tests/fixtures.py`, on the far side of the wire, and nothing at boot writes
-- a requisition.

BEGIN;

-- ─── The organisation: authored, and loaded from the seed's ERP rendering ───

-- Flat, with no hierarchy and no membership table. A person who must see more
-- than one centre holds the `auditor` role instead, which keeps row scoping to
-- one equality check plus one role bypass — and keeps an auditor reading three
-- of three visibly different from an approver who merely belongs to two.
CREATE TABLE cost_centre (
    code text PRIMARY KEY,
    name text NOT NULL
);

-- A party a requisition may be raised against. The `submit_requisition` enum is
-- generated from these rows, so the tool definition cannot drift from the data.
CREATE TABLE vendor (
    id   text PRIMARY KEY,
    name text NOT NULL
);

-- Keyed by the subject, because that is what a request arrives holding: the
-- join at request time is on the standard subject claim, and a person row a
-- token cannot be matched to would be a row nothing can reach.
--
-- Exactly one cost centre, enforced by the column rather than described. That
-- is what makes a cross-centre submission inexpressible rather than merely
-- refused, and it is why `submit_requisition` takes no cost-centre input —
-- a free-text one would leak which centres exist.
CREATE TABLE person (
    subject     text PRIMARY KEY,
    name        text NOT NULL,
    cost_centre text NOT NULL REFERENCES cost_centre (code)
);

-- ─── The chain: generated per matrix row, and loaded by the suites ─────────

CREATE TYPE requisition_status AS ENUM ('submitted', 'approved', 'rejected');
CREATE TYPE purchase_order_status AS ENUM ('open', 'invoiced');

-- `currency` has one legal value and is kept anyway: an amount without a
-- currency is a defect waiting for a second currency, and ADR-0002 specified
-- amounts as a decimal string plus an explicit currency.
--
-- `cost_centre` is the submitter's own, stamped at submission. `submitted_by`
-- is what the first segregation-of-duties edge is tested against — submitter ≠
-- approver — and it is an identity rather than a role, because a position is
-- occupied once on one chain while a role is held standing.
CREATE TABLE requisition (
    id           text PRIMARY KEY,
    cost_centre  text NOT NULL REFERENCES cost_centre (code),
    vendor       text NOT NULL REFERENCES vendor (id),
    amount       numeric(12, 2) NOT NULL CHECK (amount > 0),
    currency     text NOT NULL DEFAULT 'EUR' CHECK (currency = 'EUR'),
    description  text NOT NULL,
    submitted_by text NOT NULL REFERENCES person (subject),
    status       requisition_status NOT NULL DEFAULT 'submitted'
);

-- Emitted when a requisition is approved, and it carries the approver's
-- identity forward but **not** a copy of the cost centre: the identity is
-- load-bearing and the centre is a join away, so denormalising it would buy a
-- shorter query and a second copy of a fact that can disagree with the first.
--
-- One order per requisition, which is what makes a second decision on a decided
-- requisition answer `already_decided` rather than mint a second order.
CREATE TABLE purchase_order (
    id             text PRIMARY KEY,
    requisition_id text NOT NULL UNIQUE REFERENCES requisition (id),
    approved_by    text NOT NULL REFERENCES person (subject),
    status         purchase_order_status NOT NULL DEFAULT 'open'
);

-- Where the governing rule bites hardest: no amount, no vendor, no supplier
-- reference. The purchase order fixes all three, and since an order takes
-- exactly one invoice at full value, an amount field could only restate one.
--
-- `recorded_by` is the second edge — approver ≠ invoice recorder — and the
-- UNIQUE below is `already_invoiced`, which is what makes a blind retry of a
-- whole batch unable to record twice.
CREATE TABLE invoice (
    id                text PRIMARY KEY,
    purchase_order_id text NOT NULL UNIQUE REFERENCES purchase_order (id),
    recorded_by       text NOT NULL REFERENCES person (subject)
);

-- Row scoping asks one question of the read path — which rows share the
-- caller's partition — so the cost centre is the one column that earns an index
-- before a query has been written against it.
CREATE INDEX requisition_cost_centre_idx ON requisition (cost_centre);

COMMIT;
