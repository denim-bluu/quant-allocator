# Quant Allocator Current Context

## Normal initialization

1. Read `docs/PRODUCT.md`.
2. Read `.harness/current.yaml`.
3. Read `AGENTS.md`.
4. Read only the specification or plan explicitly named by the current task.
5. Verify the Git branch and worktree before editing.

Do not initialize from `.superpowers/sdd/progress.md`, old continuation prompts,
completed implementation plans, or review reports. They are historical evidence for
targeted archaeology only.

The current harness is intentionally small. It records the product objective, current
task, next action, parked work, verification level, and outward-action authority. It
does not select models, estimate token use, or turn the historical backlog into active
work.
