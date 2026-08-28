# mcp-erp

## Agent skills

### Issue tracker

Issues live as GitHub issues in `marcosfsousa/mcp-erp`, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Issue references

Bare `#N` means an issue or pull request; map constraint and note numbers take backticks — in commit messages too. See `docs/agents/issue-tracker.md`.

### Issue bodies

Every issue carries `## Checked and dropped`, recording each candidate claim checked and rejected, or the line `Nothing dropped.` See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Running the stack

Every compose command selects the TLS profile, and the certificate is per-checkout. See `docs/agents/running-the-stack.md` before bringing the exhibit up, driving Claude Code against it, or minting a token.

### Setup re-seeding

The files under `docs/agents/` were seeded by a scaffolding tool and then hand-edited; regenerating them reverts the edits. See `docs/agents/setup-reseed.md`.
