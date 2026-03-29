# Estado de publicación de ForgeSeed

## Sobre el repositorio dedicado
ForgeSeed debería vivir en un repositorio propio.

No lo moví antes porque el conector de GitHub disponible en esta sesión permite trabajar con archivos, ramas, commits y PRs sobre repos ya accesibles, pero **no expone una operación de crear repositorio ni de transferir contenido a un repo nuevo**.

Por eso la publicación se hizo en:
- `Ernest-NA/ExamGen/starter-kits/forgeseed`

La ubicación es funcional, pero no es la ubicación ideal.

## Estado real de la subida

### Subido exactamente desde el ZIP
- `README.md`
- `scaffold_project.py`
- `new-codex-project.bat`
- `build_exe.ps1`
- `repo-template/README.md`
- `repo-template/AGENTS.md`
- `repo-template/.gitignore`
- `repo-template/.editorconfig`
- `repo-template/docs/runbooks/local-setup.md`
- `repo-template/docs/runbooks/release-process.md`
- `repo-template/docs/runbooks/incident-process.md`
- `repo-template/docs/architecture/adr/0001-template.md`
- `repo-template/notion/csv/features.csv`
- `repo-template/notion/csv/decisions.csv`
- `repo-template/notion/csv/skills-catalog.csv`
- `repo-template/src/.gitkeep`
- `repo-template/tests/.gitkeep`
- `repo-template/scripts/.gitkeep`
- `repo-template/tools/.gitkeep`
- `CUSTOMIZE_TEMPLATE.md`

### Subido, pero no idéntico al ZIP original
Estos archivos existen en GitHub y son funcionales, pero quedaron simplificados por las limitaciones del conector en intentos anteriores.

- `repo-template/.github/ISSUE_TEMPLATE/feature_request.md`
- `repo-template/.github/ISSUE_TEMPLATE/bug_report.md`
- `repo-template/.github/pull_request_template.md`
- `repo-template/.github/workflows/ci.yml`
- `repo-template/.agents/skills/create-feature/SKILL.md`
- `repo-template/.agents/skills/bugfix/SKILL.md`
- `repo-template/.agents/skills/write-tests/SKILL.md`
- `repo-template/.agents/skills/refactor-module/SKILL.md`
- `repo-template/.agents/skills/review-pr/SKILL.md`
- `repo-template/.agents/skills/update-docs/SKILL.md`
- `repo-template/docs/architecture/system-overview.md`
- `repo-template/docs/architecture/coding-standards.md`
- `repo-template/docs/product/vision.md`
- `repo-template/docs/product/roadmap.md`
- `repo-template/docs/product/requirements/template-feature-spec.md`
- `repo-template/notion/README.md`
- `repo-template/notion/notion-databases.md`
- `repo-template/notion/csv/projects.csv`

## Contenido canónico exacto para los archivos no idénticos

### repo-template/.github/ISSUE_TEMPLATE/feature_request.md
```md
---
name: Feature request
about: Propose a product or engineering feature
title: "[Feature] "
labels: enhancement
assignees: ''
---

## Context
Describe the problem or opportunity.

## Goal
What outcome do we want?

## Acceptance criteria
- [ ]

## Notes
Links to Notion/GitHub references.
```

### repo-template/.github/ISSUE_TEMPLATE/bug_report.md
```md
---
name: Bug report
about: Report a defect
title: "[Bug] "
labels: bug
assignees: ''
---

## Problem
What is failing?

## Expected behavior
What should happen?

## Reproduction
1.
2.
3.

## Impact
Severity, user impact, affected areas.

## Notes
Logs, screenshots, linked Notion spec, etc.
```

### repo-template/.github/pull_request_template.md
```md
## Summary
- 

## Why
- 

## Changes
- 

## Validation
- [ ] Tests updated
- [ ] Lint/build executed
- [ ] Docs updated when needed

## Risks / follow-up
- 
```

### repo-template/.github/workflows/ci.yml
```yml
name: CI

on:
  pull_request:
  push:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Basic validation
        run: |
          echo "Add your real lint/test/build commands here"
```

### repo-template/.agents/skills/create-feature/SKILL.md
```md
---
name: create-feature
description: Use this skill when implementing a new feature end-to-end, including design alignment, code changes, tests, and docs.
---

# Goal
Implement a new feature with a minimal, safe, reviewable change set.

# Steps
1. Read the relevant requirement in `docs/product/requirements/`.
2. Inspect existing patterns before creating new ones.
3. Propose the smallest viable design.
4. Implement in focused commits or logical chunks.
5. Add or update tests.
6. Update docs if public behavior changed.

# Constraints
- Do not introduce new dependencies without justification.
- Reuse existing patterns where possible.
- Keep changes aligned with the feature scope.

# Deliverable
- Code changes
- Test updates
- Short summary of design choices and risks
```

### repo-template/.agents/skills/bugfix/SKILL.md
```md
---
name: bugfix
description: Use this skill when investigating and fixing a defect with reproduction, root cause, fix, and regression validation.
---

# Goal
Fix a defect safely and reduce regression risk.

# Steps
1. Reproduce the issue if possible.
2. Identify the root cause before coding.
3. Implement the smallest corrective change.
4. Add or update a regression test.
5. Summarize the bug cause and why the fix works.

# Constraints
- Avoid broad refactors during a bug fix unless strictly required.
- Preserve unrelated behavior.
```

### repo-template/.agents/skills/write-tests/SKILL.md
```md
---
name: write-tests
description: Use this skill when adding or improving automated tests for changed or critical behavior.
---

# Goal
Create clear tests that validate behavior and are easy to maintain.

# Steps
1. Identify the behavior under test.
2. Prefer tests close to the affected module boundary.
3. Cover happy path, key edge case, and failure mode where appropriate.
4. Keep assertions precise and readable.

# Constraints
- Do not overmock.
- Avoid brittle implementation-detail assertions.
```

### repo-template/.agents/skills/refactor-module/SKILL.md
```md
---
name: refactor-module
description: Use this skill when restructuring an existing module without changing intended behavior.
---

# Goal
Improve code structure while preserving behavior.

# Steps
1. Understand current responsibilities.
2. Define the target improvement.
3. Preserve behavior through tests.
4. Refactor incrementally.
5. Call out any behavioral uncertainty explicitly.

# Constraints
- No hidden feature work.
- Avoid changing public contracts unless approved.
```

### repo-template/.agents/skills/review-pr/SKILL.md
```md
---
name: review-pr
description: Use this skill when reviewing a pull request for correctness, scope control, tests, and maintainability.
---

# Goal
Review a change set with a practical engineering lens.

# Review checklist
- Is the scope focused?
- Are naming and structure clear?
- Are tests sufficient?
- Are risks called out?
- Is documentation updated where needed?

# Output
- Findings ordered by severity
- Missing tests or validation
- Suggested improvements
```

### repo-template/.agents/skills/update-docs/SKILL.md
```md
---
name: update-docs
description: Use this skill when technical or product documentation must be updated to reflect implemented changes.
---

# Goal
Keep docs aligned with reality.

# Steps
1. Identify which docs are affected.
2. Update the minimum set of pages required.
3. Prefer concise, accurate, operationally useful text.
4. Remove stale assumptions when possible.

# Constraints
- Do not invent behavior not present in the code or product spec.
```

### repo-template/docs/architecture/system-overview.md
```md
# System Overview

## Objective
Describe what the system does at a high level.

## Context
- Business domain:
- Primary users:
- Core flows:
- External integrations:

## Architecture principles
- Keep the design simple and evolvable.
- Prefer modular boundaries.
- Avoid premature abstraction.
- Document decisions that affect multiple modules.

## Suggested sections to complete
- Logical components
- Data flow
- External services
- Security constraints
- Deployment model
```

### repo-template/docs/architecture/coding-standards.md
```md
# Coding Standards

## General
- Prefer readability over cleverness.
- Keep functions focused.
- Use clear names.
- Avoid hard-coded magic values.

## Reviews
- Small PRs are preferred.
- Document trade-offs where needed.
- Include validation evidence.

## Testing
- Add unit tests for changed behavior.
- Add integration tests where module boundaries are affected.
```

### repo-template/docs/product/vision.md
```md
# Product Vision

## Problem
What user problem does this project solve?

## Outcome
What better future state do we want?

## Non-goals
What is explicitly out of scope for now?
```

### repo-template/docs/product/roadmap.md
```md
# Roadmap

## Now
- Core foundation
- First usable workflow

## Next
- Team automation
- More specialized skills
- Better CI/CD

## Later
- Plugins / MCP / subagents
- Domain-specific automation
```

### repo-template/docs/product/requirements/template-feature-spec.md
```md
# Feature Spec Template

## Summary
Brief description of the feature.

## User story
As a...
I want...
So that...

## Acceptance criteria
- [ ]

## Constraints
- 

## Technical notes
- 

## Risks
- 
```

### repo-template/notion/README.md
```md
# Notion Setup

This folder helps you bootstrap the Notion side of the operating model.

## Suggested databases
- Projects
- Features
- Decisions
- Skills Catalog

## Import
Use the CSV files in `csv/` as initial imports into Notion databases.

## Recommended operating model
- Notion stores roadmap, specs, and decisions.
- GitHub stores code, issues, pull requests, and CI.
- The repository stores Codex guidance, skills, and technical docs.
```

### repo-template/notion/notion-databases.md
```md
# Notion Databases

## 1. Projects
Fields:
- Name
- Status
- Owner
- Repo
- Priority
- Quarter
- Notes

## 2. Features
Fields:
- Name
- Project
- Status
- Owner
- GitHub Issue
- Notion Spec URL
- Acceptance Criteria
- Recommended Skill

## 3. Decisions
Fields:
- Title
- Date
- Status
- Context
- Decision
- Consequences
- Related PR
- Related Doc

## 4. Skills Catalog
Fields:
- Skill Name
- Purpose
- Trigger
- Input
- Output
- Repo Path
- Owner
- Version
```

### repo-template/notion/csv/projects.csv
```csv
Name,Status,Owner,Repo,Priority,Quarter,Notes
__PROJECT_NAME__,Idea,__AUTHOR__,__PROJECT_SLUG__,High,2026-Q2,Initial project seed
```
