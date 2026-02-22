---
name: technical-strategy
description: Make long-term technical decisions that minimize maintenance burden and avoid over-engineering.
---

# Technical Strategy

This skill guides you to make architectural and design decisions that stand the test of time and scale appropriately.

## Core Principles

1.  **Your Creations Require Maintenance**:
    *   **Cost of Ownership**: Every line of code written is a line of code that must be debugged, upgraded, and secured.
    *   **Minimize Surface Area**: Prefer solutions that require less code and fewer moving parts.
    *   **Lifecycle Management**: Plan for deprecation from day one. How will this be replaced?

2.  **Don't Optimize the Wrong Problem**:
    *   **Premature Optimization**: Don't optimize for massive scale if you don't have users yet.
    *   **Frequency Matters**: Don't spend days automating a task that happens once a year.
    *   **Good Enough Performance**: If a query takes 200ms and runs once a day, don't spend a week making it 10ms.

3.  **You Don't Have to Do What Google Does**:
    *   **Context is King**: Solutions that work for 27,000 engineers (monorepos, custom build systems) may crush a team of 5.
    *   **Right-Size Solutions**: Choose tools appropriate for the current team size and maturity.
    *   **Evaluate Trade-offs**: Understand *why* big tech uses a tool before adopting it.

## Actionable Instructions for Agents

*   **When choosing a technology or pattern**:
    1.  **Read Context**: Check `docs/company_context.md`. **If missing**, run `.agent/workflows/interview_company_context.md`.
    2.  Assess the maintenance burden. Who will patch this?
    3.  Check if the solution is appropriate for the scale. Is it too complex for the current problem size?
    4.  Avoid "hype-driven development". Stick to boring, proven technologies unless the new tech solves a critical, specific pain point.

*   **When planning deployment or operations**:
    1.  **Read Context**: Check `docs/operational_context.md`. **If missing**, run `.agent/workflows/interview_operational_context.md`.
    2.  Ensure decisions align with Ownership, Budget, and Release constraints.
    3.  Identify where secrets and artifacts should live.

*   **When optimizing code**:
    1.  Ask "Is this a bottleneck?"
    2.  If no data suggests it's a problem, leave it alone.
    3.  Focus on readability and maintainability over clever optimization.
