# `tests/wire/` — the server's own posture, over the wire

The assertions that belong to no proof artifact: the endpoints that answer and
the ones that do not, the tool listing's freshness hint and declared schemas, two
replicas behind no sticky routing, what `submit_requisition` charges, how the
named-versus-discovered contract behaves across the live tools, everything
`approve_requisition` decides since #40, the fold since #41, and — since #42 —
everything `record_invoice` records.

Needs Compose, with one exception named below. Landed with #37; #39 added two,
#40 a third, #41 a fourth, #42 a fifth. **#43 took the tool listing's filter
away**, which is the first thing this directory has handed over rather than
gained; the table below said it would, and *What moved to #43* records what
happened.

**One seam, one diagnosis.** ADR-0013 names it *Server posture* and #66 gave it
a job: *the server exposes, declares or deploys something other than what it
should, with no caller's authorization involved.* The clause that draws the
boundary is that **nothing here reads a `Principal`** — which is what keeps this
directory out of the decision matrix's territory rather than beside it, and what
decides every handoff argued below.

## Why there is a fifth directory

ADR-0013 named four test directories **for artifacts** — the decision matrix,
the attack suite, the conformance run, and the ejection target — and said that
layers 1 and 3 get none of their own, because ADR-0008 routes every assertion
about them over the wire. Both halves of that still hold, and neither of them
places these three.

- The **metadata route answering without a token, and every other path being
  gated**, is ADR-0006's discovery decision. It defends nothing named in
  `scenarios.yaml` and expects no `(principal × tool × resource)` row.
- **Two replicas, round-robin, nothing remembered** is map constraint `#5`. It
  is a property of the deployment rather than of a caller.
- The **tool listing's filter** ~~will become~~ **became** five rows of
  `matrix.yaml` — one per scope set the filter is exercised across — when #43
  wrote that file. **`cacheScope` and the `ttlMs` cap are not among them**, and
  the amendment below says why.
- **What `submit_requisition` charges** (#39) is the same case one ticket later:
  a principal and a tool mapped to an expected answer is a matrix row, and there
  is still nothing to generate it from. It is not `state_handle_hijack` either —
  that row is a refused write against a *named* resource, and this tool has none.
- **Everything `approve_requisition` decides** (#40) is the same case again, and
  the largest of them: a threshold, a submitter edge, a terminal state and two
  denial classes, every one of which is a `(principal × tool × resource →
  expected)` row waiting for a file to be generated from. Two of its assertions
  are *not* matrix rows and would not become ones — that the rules run in the
  declared order, and that CC-4300's remedy names a class of action no available
  human fills. The first is a property of the `Action` rather than of a row; the
  second is a property of the organisation's shape, which is what makes it worth
  a named test rather than a matrix row that happens to expect `over_threshold`.
- **The fold** (#41) is layer 1's, and layer 1 has no directory. What one call
  answers with when it yields more than one outcome is not a
  `(principal × tool × resource)` row — the same call, the same caller and the
  same rows produce it — and it defends nothing named in `scenarios.yaml`. Two
  of its assertions would not become matrix rows under any file: that a list
  tool returning several rows is still *one* outcome, which is a claim about
  what an outcome is rather than about who may see what; and the one below,
  which has no altitude at all.
- **Everything `record_invoice` records** (#42) is the same case once more, and
  the smallest of them: the second separation edge, a terminal state, and the
  role gate on a scope that reaches two tools — every one of which is a
  `(principal × tool × resource → expected)` row waiting for a file to be
  generated from. Two of its assertions are *not* matrix rows. That an approver
  who holds `invoice_clerk` is refused on the order she approved and permitted on
  the one she did not is a statement about a **position versus a role**, which
  needs both calls to say anything and would be two rows expecting two answers
  with the connection between them lost. And what the suite deliberately does
  **not** assert is `partition_bypass`: nobody in the cast holds `auditor`
  together with `invoice_clerk`, row scoping runs after the role gate, so a
  declaration that wrongly granted breadth on this write would ship green — which
  ADR-0013 names as the mistake a reader makes on this tool by name. Review is
  the guard, and the reasoning is in the declaration.
- **The named-versus-discovered contract across all three tools** (#39) is the
  seam between two attack-suite rows rather than a third one. Each of
  `row_probe_indistinguishable` and `list_partition_scoped` asserts its own half
  about its own tool; neither says the *same* row takes the *other* shape through
  the other tool. Minting a row for the seam would move a derived count to record
  something that is not an attack, which is the same refusal the two above take.

The alternative was to mint scenario rows for the ones that could carry them.
That was declined:
membership in the attack suite is ADR-0010's rule — one row per distinct clause
this project *enforces*, each recording the exact removal that makes it pass —
and the row count is a derived artifact under map constraint `#12`. Inventing
rows to give these tests a home would move a number three documents track, to
record something that is not an attack.

**This directory is named for the altitude every assertion in it shares, not for
a layer.** ADR-0013's prohibition is on a directory named `transport/` or
`purchase_to_pay/` collecting in-process unit tests of a layer; ~~everything
here drives real HTTP against Compose like the three suites beside it~~.
Recorded as an amendment to ADR-0013 by #37.

**One assertion here is not over HTTP, since #41.** *Layer 1 contains no
reference to the tool name, nor to which argument is the batch* is the negative
guarantee the fold had to be built without breaking, and it is not reachable at
this altitude: a name absent from a module is absent, and no request can show
it. So `test_the_fold.py` reads layer 1's own source, with docstrings stripped
first — the guarantee is *stated* in two of those modules, and a check that read
prose would fail on the sentence describing what it asserts. The precedent is
`tests/authorization/test_purity.py`, which reads layer 2's source for the same
class of reason: a property true by **absence** has no behaviour to drive. The
alternative was a sixth directory holding one file. Recorded as an amendment to
ADR-0013 by #41, which narrows the struck sentence above rather than keeping it.

**The listing's freshness hint stays here, since #66.** `cacheScope`, the
`ttlMs` cap, the declared schemas and `listChanged: false` were listed above as
matrix-bound and are not: they are things the server states **identically to
every caller**, so there is no `(principal × tool × resource)` to key them on and
they never had a destination in `matrix.yaml`. The dividing line is this
directory's own — what varies with the caller is the matrix's, what the server
declares regardless is ours. Recorded as an amendment to ADR-0013 by #66.

**Five of the seven bullets above say *waiting for a file to be generated from*,
and the file exists now.** #43 wrote `matrix.yaml` and every branch those bullets
name has a row in it. The bullets stand as written because they record why this
directory came to hold what it holds, and the reader who wants to know what is
still true here should read *What moved to #43* below — which moved the listing's
filter and, deliberately, nothing else. The section after it names what a later
ticket has to decide about the rest.

## What moved to #43, and what did not

Named here rather than left for #43 to re-derive, because the rule is easy to
state and the boundary is not obvious at every line. **An assertion whose
expected value changes with the caller is decision-matrix business; an assertion
the server makes identically to every caller stays.**

*Written in the future tense by #66 and settled by #43, which moved all five and
nothing else.* The table below is what happened, not a plan.

Five of `test_tool_listing.py`'s assertions **moved**, one per scope set the
filter is exercised across, and each is a row of `matrix.yaml` now:

| Assertion | The row it becomes |
| --- | --- |
| `test_a_read_token_reaches_the_read_tools` | `listing_reaches_the_reading_tools` |
| `test_the_write_scope_reaches_the_write_tool_and_no_read_tool` | `listing_reaches_the_writing_tools` |
| `test_both_scopes_reach_the_union_and_nothing_else` | `listing_reaches_the_union_of_two_capabilities` |
| `test_the_deciding_scope_reaches_the_deciding_tool_for_a_person_who_may_not_use_it` | `listing_reaches_the_deciding_tool_through_a_role_gate` |
| `test_a_token_with_no_capability_scope_reaches_nothing` | `listing_reaches_nothing_without_a_capability_scope` |

Five **stayed**, and each for a reason the rule gives directly:

- `test_the_listing_is_private_and_expires_with_the_token` — `cacheScope` and
  the `ttlMs` cap are declarations, identical for everyone.
- `test_the_listing_declares_the_schemas_layer_three_authored` — likewise.
- `test_the_tool_set_is_fixed_at_deploy` — `listChanged: false`, likewise.
- `test_the_listing_is_a_function_of_the_token_and_not_of_the_person` — this is
  the same rule read backwards. It asserts an invariance **across** callers
  rather than a value that varies with one, so splitting it into two matrix rows
  would keep both halves and lose the equality between them, which is the whole
  claim.
- `test_calling_a_tool_the_listing_omits_is_refused_and_says_which_scope` —
  stays, and it is **not** a duplicate of the attack suite's `insufficient_scope`
  row. That row defends the challenge's *shape*. This asserts the **agreement
  between the listing and the call**: a tool the listing omits, called anyway, is
  refused naming the scope that would have reached it. Nothing in
  `scenarios.yaml` consults the listing, so handing it away would drop the
  linkage rather than relocate it. Recorded for #44 as well.

**The cost of the handoff is priced in the map, not left implicit.** Cutting the
decision matrix — rank 3 on cut order `#9` — now takes the tool listing's scope
filter with it, which was not true before #66. What survives the cut is
everything in the table's second half, so *Server posture* stays whole and this
directory keeps its seam.

## What #43 did not settle, and a later ticket has to

`matrix.yaml` now holds a row for every branch of all five tools. Several
assertions in this directory sit at the same `(principal x tool x resource ->
expected)` shape and were **not** moved: #66's handoff named five and named no
others, and #43 moved those five and stopped rather than quietly widening its
own scope.

The rule that would decide the rest is available and is not applied here: **a
matrix row asserts the decision; these files additionally assert what the call
*did*** — the purchase order an approval emitted and what it carries, the status
the row reads back as afterwards, the declared schemas, the order the rules run
in, and the argument errors that are not refusals at all. Where a test asserts
only the decision it is now a genuine duplicate of a row, and where it asserts an
effect it is not. Working through them file by file is a ticket of its own, and
it wants the count and the cut-order line repriced in the same act — which is
exactly the work #66 did for the five above.

## Running it

```
docker compose up -d
uv run pytest tests/wire
```

The token helper mints against the issuer the seed declares, which is
`http://keycloak:8081/...`. Either add one line to your hosts file —

```
127.0.0.1 keycloak
```

— or point the helper's transport somewhere reachable, which changes the address
the requests go to and never the issuer they assert:

```
KEYCLOAK_BASE_URL=http://localhost:8081 uv run pytest tests/wire
```

`MCP_ERP_BASE_URL` moves the server's address the same way; it defaults to the
gateway's published `http://localhost:8080`.

## In continuous integration

**`Server posture`** runs this directory on every pull request and every push to
`main`, and #66 built it. It is the **first Compose bring-up in continuous
integration** — of the three jobs expected to bring one, #46 has since landed
beside it and #43 and #44 are still to come — so `.github/workflows/ci.yml`
carries the bring-up written plainly inside the job rather than factored into a
shared action, and the rest inherit the pattern by reading it. Why it is not
factored is argued where an editor of that file meets it, in the
`server-posture` header comment, and recorded in ADR-0013
§*Continuous-integration jobs, one per seam*.

**`Authorization code flow` landed on 2026-08-20 and does not run this
directory**, which is the point rather than an omission: it runs
`tests/conformance` alone, because a red check there has to mean the flow broke.
A job that also ran these would report a tool listing's freshness hint as the
authorization code flow failing — two seams answering to one diagnosis, which is
the thing *one job per seam* exists to prevent.

The runner takes the **hosts-file** branch of the choice above rather than the
rebase, so the path `compose.yaml` and this file tell a reader to take is the
one exercised on every run.

~~ADR-0013 fixes the job set at eight~~ — it never did, and #66 struck the
count. The heading named a number and the paragraph under it requires set
equality between job names and the ruleset's required contexts; *one job per
seam* is the only rule. What holds the table and the workflow together is the
test #47 brings, never a number either document has to keep current.
