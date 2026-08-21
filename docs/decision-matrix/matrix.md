# The decision matrix

<!-- Rendered from docs/decision-matrix/matrix.yaml by tests/matrix/matrix_table.py. Do not edit. -->
<!-- `Seed renders clean` re-renders this file and refuses a diff. -->

33 rows: what one principal may do to one resource through one tool.

## What the rows reach

| Reason | Rows | Refused as |
| --- | --- | --- |
| `already_decided` | 1 | a tool result marked in error |
| `already_invoiced` | 1 | a tool result marked in error |
| `insufficient_scope` | 5 | `403` with a `WWW-Authenticate` challenge |
| `not_found` | 5 | a tool result marked in error |
| `over_threshold` | 2 | a tool result marked in error |
| `role_missing` | 2 | a JSON-RPC error, `-31010` |
| `segregation_of_duties` | 2 | a tool result marked in error |
| *permitted* | 15 | — |

## `tools/list`

| Row | Person | Token scopes | Acts on | Expected |
| --- | --- | --- | --- | --- |
| `listing_reaches_nothing_without_a_capability_scope` | priya.raman | *none* | — | permitted — lists *nothing* |
| `listing_reaches_the_reading_tools` | priya.raman | `erp.read` | — | permitted — lists `get_requisition`, `list_requisitions` |
| `listing_reaches_the_writing_tools` | priya.raman | `erp.write` | — | permitted — lists `record_invoice`, `submit_requisition` |
| `listing_reaches_the_union_of_two_capabilities` | priya.raman | `erp.read` `erp.write` | — | permitted — lists `get_requisition`, `list_requisitions`, `record_invoice`, `submit_requisition` |
| `listing_reaches_the_deciding_tool_through_a_role_gate` | priya.raman | `erp.decide` | — | permitted — lists `approve_requisition` |

## `list_requisitions`

| Row | Person | Token scopes | Acts on | Expected |
| --- | --- | --- | --- | --- |
| `list_refused_without_the_reading_scope` | priya.raman | *none* | — | refused — `insufficient_scope`, `403` with a `WWW-Authenticate` challenge |
| `list_returns_the_callers_own_partition` | tomas.weber | `erp.read` | — | permitted — returns CC-4100 |
| `list_returns_another_partition_to_its_own_holder` | yusuf.demir | `erp.read` | — | permitted — returns CC-4200 |
| `list_returns_every_partition_to_the_auditing_role` | anna.lindqvist | `erp.read` | — | permitted — returns CC-4100, CC-4200, CC-4300 |

## `get_requisition`

| Row | Person | Token scopes | Acts on | Expected |
| --- | --- | --- | --- | --- |
| `get_refused_without_the_reading_scope` | priya.raman | *none* | `req_9999` — no row carries it | refused — `insufficient_scope`, `403` with a `WWW-Authenticate` challenge |
| `get_returns_a_row_in_the_callers_partition` | tomas.weber | `erp.read` | `req_0001` — CC-4100, 1200.00, raised by `priya-raman` | permitted |
| `get_refuses_a_row_in_another_partition` | yusuf.demir | `erp.read` | `req_0002` — CC-4100, 480.00, raised by `priya-raman` | refused — `not_found`, a tool result marked in error |
| `get_refuses_an_identifier_no_row_carries` | tomas.weber | `erp.read` | `req_9999` — no row carries it | refused — `not_found`, a tool result marked in error |
| `get_reads_across_partitions_for_the_auditing_role` | anna.lindqvist | `erp.read` | `req_0003` — CC-4300, 950.00, raised by `mei-tanaka` | permitted |

## `submit_requisition`

| Row | Person | Token scopes | Acts on | Expected |
| --- | --- | --- | --- | --- |
| `submit_refused_without_the_writing_scope` | priya.raman | `erp.read` | — | refused — `insufficient_scope`, `403` with a `WWW-Authenticate` challenge |
| `submit_is_charged_to_the_submitters_own_partition` | priya.raman | `erp.read` `erp.write` | — | permitted — charged to CC-4100 |
| `submit_is_charged_to_a_third_partition_for_its_own_inhabitant` | mei.tanaka | `erp.read` `erp.write` | — | permitted — charged to CC-4300 |

## `approve_requisition`

| Row | Person | Token scopes | Acts on | Expected |
| --- | --- | --- | --- | --- |
| `approve_refused_without_the_deciding_scope` | tomas.weber | `erp.read` `erp.write` | `req_0004` — CC-4100, 1450.00, raised by `priya-raman` | refused — `insufficient_scope`, `403` with a `WWW-Authenticate` challenge |
| `approve_refused_when_the_scope_carries_no_role` | priya.raman | `erp.decide` | `req_0005` — CC-4100, 620.00, raised by `tomas-weber` | refused — `role_missing`, a JSON-RPC error, `-31010` |
| `approve_refuses_a_row_in_another_partition` | yusuf.demir | `erp.decide` | `req_0006` — CC-4100, 300.00, raised by `priya-raman` | refused — `not_found`, a tool result marked in error |
| `approve_refuses_an_identifier_no_row_carries` | tomas.weber | `erp.decide` | `req_9999` — no row carries it | refused — `not_found`, a tool result marked in error |
| `approve_refuses_the_approvers_own_requisition` | tomas.weber | `erp.decide` | `req_0007` — CC-4100, 740.00, raised by `tomas-weber` | refused — `segregation_of_duties`, a tool result marked in error |
| `approve_refuses_above_the_threshold` | tomas.weber | `erp.decide` | `req_0008` — CC-4100, 7500.00, raised by `priya-raman` | refused — `over_threshold`, a tool result marked in error |
| `approve_permits_at_the_threshold` | tomas.weber | `erp.decide` | `req_0009` — CC-4100, 5000.00, raised by `priya-raman` | permitted |
| `approve_permits_above_the_threshold_for_the_unlimited_role` | ingrid.holm | `erp.decide` | `req_0010` — CC-4100, 9200.00, raised by `priya-raman` | permitted |
| `approve_refuses_a_row_already_decided` | tomas.weber | `erp.decide` | `req_0011` — CC-4100, 900.00, raised by `priya-raman`, approved by `ingrid-holm`, order open | refused — `already_decided`, a tool result marked in error |
| `approve_refuses_above_the_threshold_where_no_unlimited_approver_exists` | yusuf.demir | `erp.decide` | `req_0012` — CC-4200, 7500.00, raised by `anna-lindqvist` | refused — `over_threshold`, a tool result marked in error |

## `record_invoice`

| Row | Person | Token scopes | Acts on | Expected |
| --- | --- | --- | --- | --- |
| `record_refused_without_the_writing_scope` | rafael.costa | `erp.read` | `po_0002` — CC-4100, 1100.00, raised by `priya-raman`, approved by `tomas-weber`, order open | refused — `insufficient_scope`, `403` with a `WWW-Authenticate` challenge |
| `record_refused_when_the_scope_carries_no_role` | priya.raman | `erp.read` `erp.write` | `po_0003` — CC-4100, 260.00, raised by `rafael-costa`, approved by `tomas-weber`, order open | refused — `role_missing`, a JSON-RPC error, `-31010` |
| `record_refuses_an_identifier_no_order_carries` | rafael.costa | `erp.read` `erp.write` | `po_9999` — no order carries it | refused — `not_found`, a tool result marked in error |
| `record_refuses_the_order_the_recorder_approved` | ingrid.holm | `erp.read` `erp.write` | `po_0004` — CC-4100, 6400.00, raised by `priya-raman`, approved by `ingrid-holm`, order open | refused — `segregation_of_duties`, a tool result marked in error |
| `record_permits_the_order_someone_else_approved` | rafael.costa | `erp.read` `erp.write` | `po_0005` — CC-4100, 6800.00, raised by `priya-raman`, approved by `ingrid-holm`, order open | permitted |
| `record_refuses_an_order_already_billed` | rafael.costa | `erp.read` `erp.write` | `po_0006` — CC-4100, 380.00, raised by `priya-raman`, approved by `tomas-weber`, order invoiced, invoiced by `ingrid-holm` | refused — `already_invoiced`, a tool result marked in error |
