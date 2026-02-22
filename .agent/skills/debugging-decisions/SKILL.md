---
name: debugging-decisions
description: Approach bugs and technical debt with a "Staff" mindset, focusing on root causes and simplification.
---

# Debugging Decisions

This skill guides you to fix problems holistically, rather than applying band-aids.

## Core Principles

1.  **Don't Create Code Paths for Unicorns**:
    *   **Standardize**: Don't create special cases for every exception.
    *   **Fix the Data/Environment**: If "unicorns" (weird edge cases) exist, try to fix the data or environment causing them, rather than writing code to handle them.
    *   **Remove Complexity**: Reduce cyclomatic complexity by removing `if/else` blocks for rare exceptions.

2.  **Boy Scout Rule**:
    *   **Leave it Better**: Always improve the code you touch.
    *   **Incremental Refactoring**: Fix typos, improve variable names, or add comments to the file you are editing, even if it's not the main task.
    *   **Put Out Fires**: If you see a "burning fire" (critical bug/bad pattern) nearby, fix it or flag it.

3.  **Don't Be Attached to Old Designs**:
    *   **Sunk Cost Fallacy**: Don't keep bad code just because you wrote it or spent a long time on it.
    *   **Rewrite when Necessary**: If the fundamental design is flawed, a rewrite of that component might be faster than patching it forever.

## Actionable Instructions for Agents

*   **When fixing a bug**:
    1.  **Read Context**: Check `docs/company_context.md`. **If missing**, run `.agent/workflows/interview_company_context.md`.
    2.  Identify the root cause. Why did this happen?
    3.  Don't just add an `if (obj != null)` check. Find out *why* it was null.
    3.  Check if the surrounding code can be cleaned up while you are there.

*   **When handling edge cases**:
    1.  Ask "Can we prevent this state from happening?"
    2.  If yes, prevent it upstream.
    3.  If no, handle it cleanly, but consider logging it as an anomaly to be investigated.
