---
name: create-feature
description: Use this skill when implementing a new feature end to end, including design review, code changes, tests, and documentation updates.
---

# Goal
Implement a feature safely with minimal ambiguity.

# Steps
1. Review relevant docs in `docs/`.
2. Inspect existing patterns before adding new abstractions.
3. Implement the smallest coherent solution.
4. Add or update tests.
5. Update docs if behavior or public interfaces changed.
6. Summarize files changed, risks, and follow-up items.

# Constraints
- Avoid new dependencies unless clearly justified.
- Prefer extending established patterns.
- Keep the scope reviewable.
