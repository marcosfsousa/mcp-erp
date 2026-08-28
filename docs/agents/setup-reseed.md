# Do not regenerate the agent docs

The files under `docs/agents/` started as scaffolding output and have since been hand-edited. **Setup is complete for this repo**, and any tool that writes seed templates over what is there is a silent revert, not an update.

What a regeneration would undo:

- `docs/agents/issue-tracker.md` — the close-on-merge keyword rule and its negation trap (`bcd006d`), the map-numbers-take-backticks rule (`e9b5e32`), and the commit-message correction to it (`7c94fb6`, `1fe9788`).
- `docs/agents/domain.md` — the single-context layout as recorded there.
- `CLAUDE.md` — the `### Issue references` block, which no template produces.

**If a setup or scaffolding step is invoked here:** diff the existing files against what it would write, report that setup is already complete, and write nothing unless asked for a specific change.

**Label vocabulary is recorded, not created.** `docs/agents/triage-labels.md` records the mapping; it does not make the labels exist. A gap between that file and the labels on the tracker is closed with `gh label create`, not by re-running setup.
