#!/bin/sh
# Load the organisation from the seed's ERP rendering, which is mounted read-only.
#
# **Committed executable, deliberately.** Postgres's entrypoint runs a `.sh` in
# this directory if it is executable and `source`s it if it is not — and sourced,
# the `set -eu` below would stay set in the entrypoint's own shell for the rest
# of initialisation, changing how every later step fails. It works either way
# today, which is exactly why the mode is stated here rather than left to
# whatever a checkout produced.
#
# The rendering is JSON rather than SQL deliberately. `Seed renders clean`
# re-renders it and refuses any diff, so it is already policed as a rendering;
# emitting DDL or INSERT statements from the generator instead would put a
# second dialect in `src/` and make the drift check compare SQL rather than data.
# The translation from one to the other belongs here, next to the database that
# needs it.
#
# This runs once, on an empty data directory. There is no volume, so `docker
# compose up` after a `down` is a cold start every time — the same property the
# authorization server gets from an in-memory database, and for the same reason:
# what the database holds is a function of what is committed, not of what
# happened to it since.

set -eu

psql --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" \
     --set ON_ERROR_STOP=1 \
     --set organisation="$(cat /seed/organisation.json)" <<'SQL'
BEGIN;

-- Cost centres before people, because a person references one. Vendors are
-- independent of both and are loaded here to keep the whole organisation in one
-- transaction: a half-loaded organisation would boot and then fail on a join.
INSERT INTO cost_centre (code, name)
SELECT centre ->> 'code', centre ->> 'name'
FROM jsonb_array_elements((:'organisation')::jsonb -> 'cost_centres') AS centre;

INSERT INTO vendor (id, name)
SELECT vendor ->> 'id', vendor ->> 'name'
FROM jsonb_array_elements((:'organisation')::jsonb -> 'vendors') AS vendor;

-- No roles column to fill: they are policy facts and live in the principal
-- directory, which is the rendering beside this one.
INSERT INTO person (subject, name, cost_centre)
SELECT member ->> 'subject', member ->> 'name', member ->> 'cost_centre'
FROM jsonb_array_elements((:'organisation')::jsonb -> 'people') AS member;

COMMIT;

-- Printed rather than assumed. A silent load and an empty database look
-- identical in the container log, and the first thing anybody wants to know
-- after a cold start is whether the seed arrived.
\echo 'organisation loaded:'
SELECT
    (SELECT count(*) FROM cost_centre) AS cost_centres,
    (SELECT count(*) FROM person)      AS people,
    (SELECT count(*) FROM vendor)      AS vendors;
SQL
