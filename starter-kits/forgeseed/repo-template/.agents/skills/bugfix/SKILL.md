---
name: bugfix
description: Use this skill when diagnosing and fixing an observed bug, regression, or incorrect behavior in an existing flow.
---

# Goal
Fix the bug with the smallest safe change.

# Steps
1. Reproduce or infer the failing path.
2. Identify the likely root cause.
3. Apply the minimal targeted fix.
4. Add or update tests when possible.
5. Document risks, limitations, or follow-ups.

# Constraints
- Avoid unrelated refactors.
- Preserve working behavior outside the bug scope.
