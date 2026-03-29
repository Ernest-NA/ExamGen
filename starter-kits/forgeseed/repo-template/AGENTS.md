# AGENTS.md

## Project context
- Project name: __PROJECT_NAME__
- Slug: __PROJECT_SLUG__
- Description: __PROJECT_DESCRIPTION__
- Owner: __AUTHOR__

## Operating model
This repository uses:
- Codex for execution of coding tasks
- GitHub as source of truth for code and pull requests
- Notion as source of truth for roadmap, specs, and decisions

## Working rules
- Prefer small, reviewable diffs.
- Preserve existing conventions unless the task requires a change.
- Update documentation when behavior, structure, or public APIs change.
- Avoid adding new dependencies without clear justification.
- Avoid rewriting large areas of code when a local change is enough.

## Expected workflow
1. Read related docs in `docs/`.
2. Select the relevant skill from `.agents/skills/`.
3. Implement the minimum safe change.
4. Add or update tests.
5. Summarize files changed, risks, and follow-ups.

## Repository map
- `src/`: code
- `tests/`: tests
- `docs/architecture/`: technical guidance
- `docs/product/`: requirements and roadmap excerpts
- `docs/runbooks/`: operational procedures
- `.agents/skills/`: reusable workflows
- `.github/`: GitHub workflows and templates
- `notion/`: Notion setup guidance and CSV seeds

## Done means
- The requested scope is implemented.
- Tests were added or updated where applicable.
- Relevant docs were updated.
- Risks and follow-up items are explicitly called out.
