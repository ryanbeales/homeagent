---
name: incremental-delivery
description: Ship value quickly by iterating, failing fast, and avoiding analysis paralysis.
---

# Incremental Delivery

This skill encourages a bias for action and iterative development.

## Core Principles

1.  **Perfection is the Enemy of Good**:
    *   **The 90% Solution**: A working 90% solution today is better than a perfect solution next month.
    *   **Ship It**: Get code into production (or at least main branch) as soon as it provides value.

2.  **Do it the Python Way (EAFP)**:
    *   **Try It**: Instead of debating for days, build a quick Proof of Concept (PoC).
    *   **Fail Fast**: Learn from failures quickly rather than fearing them.
    *   **Handle Errors**: reliability comes from handling failure, not preventing every impossible scenario.

3.  **Don't Fall into the Trap of "We've Already Tried This"**:
    *   **Context Changes**: Technology and teams evolve. What failed 2 years ago might work now.
    *   **Fresh Eyes**: approaches that didn't work for previous engineers might work with your fresh perspective.

## Actionable Instructions for Agents

*   **When planning work**:
    1.  **Read Context**: Check `docs/company_context.md`. **If missing**, run `.agent/workflows/interview_company_context.md`.
    2.  Break large tasks into smaller, shippable chunks.
    3.  Identify the "Critical Path" to getting value to the user.
    3.  Propose an "MVP" (Minimum Viable Product) approach first.

*   **When blocked by uncertainty**:
    1.  Suggest a "Spike" or "PoC" to test assumptions.
    2.  Write a small script to verify behavior instead of theorizing.
    3.  If a decision is reversible, make it quickly and move on.
