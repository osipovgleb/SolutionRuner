# Project experience

This file is the durable cross-task memory for SolutionRuner. Add concise, reusable findings here as runners and converters are developed.

## Repository workflow

- SolutionRuner uses one shared saved-project checkout at `/Users/a1/projects/SolutionRuner`; Codex worktrees are not used.
- Runner implementations accumulate in this repository and reuse its common launcher and infrastructure.
- Test commands are announced to the user before execution.
- MCP/production-changing commands require explicit user authorization. A requested example command containing `--apply` may be documented without being executed.

## Runner design principles

- Prefer an explicit group profile plus a pure deterministic strategy over a separate launcher.
- Validate all supported input forms explicitly and fail closed on unknown or ambiguous cases.
- Complete validation, including comparison with the expected answer, before any write operation.
- Cover reusable behavior with local fixtures and fake-MCP tests.

## Group-specific findings

Add dated entries here when a group investigation produces rules that may help future runners.
