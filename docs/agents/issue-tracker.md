# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`
- **Close on merge**: a PR body closes an issue only through a literal keyword — `close`/`closes`/`closed`, `fix`/`fixes`/`fixed`, `resolve`/`resolves`/`resolved` — followed by `#<n>`. Nothing else counts. Prose openers this repo favours (`Settles #11`, `Answers #9`, `Part of #2`) render as a plain mention and leave the issue open on merge. Keep the prose and add a bare `Closes #<n>` line, then verify before merge: `gh pr view <n> --json closingIssuesReferences` must be non-empty. An empty array means the merge will not close anything.

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues, using the `gh pr` equivalents:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>` for the diff.
- **List external PRs for triage**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` then keep only `authorAssociation` of `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, or `NONE` (drop `OWNER`/`MEMBER`/`COLLABORATOR`).
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either — resolve with `gh pr view 42` and fall back to `gh issue view 42`.

That shared space is why **map numbers take backticks**: constraint, note, cut-order and ship-line numbers are their own sequence and collide with real issue and PR numbers throughout `#1`–`#16`. A noun prefix does not stop the autolink — writing `constraint` before a bare number still links it to the issue of the same value and injects that issue's title into the sentence. Write `` `#10` `` for a map object; keep bare `#N` for actual issues and pull requests. This binds **every surface GitHub autolinks — issue bodies, pull request bodies, and commit messages, subject lines included.** Markdown files are not autolinked, so `#N` in an ADR or in `scenarios.yaml` is already inert and needs nothing.

**In commit messages, drop the `#` entirely — backticks do not work there.** Commit messages are not rendered as Markdown, so a backtick is a literal character and the `#N` inside it still autolinks. Write **`map constraint 13`** or **`constraint no. 13`**; never `` `#13` ``. Bare `#N` for a real issue or pull request stays correct and wanted, including the `Closes #<n>` line.

This is a defect the rule above had, not a case it failed to cover: it named commit messages as a bound surface and prescribed a mechanism that does nothing there, so following it exactly produced the mislink. It was found when the commit establishing map constraint 13 rendered *"map constraint `#13`"* as a link to pull request 13 — an unrelated merged research PR — and *"constraint `#12`"* as a link to issue 12, which is the ticket rather than the constraint and therefore looks right while being wrong. Verify on a rendered commit page, not on `git log`, which shows neither backticks nor links as GitHub does.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (`gh api` on the sub-issues endpoint). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitHub's **native issue dependencies** — the canonical, UI-visible representation. Add an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **database id** (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _not_ the `#number` or `node_id`). GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only — the live gate). Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (`issue_dependencies_summary.blocked_by > 0`, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me` — the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far. Where the answer lands as a PR, close the ticket explicitly by this route rather than trusting the merge — see **Close on merge** above.
