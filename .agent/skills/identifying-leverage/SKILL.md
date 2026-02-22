---
name: identifying-leverage
description: Prioritize work that has high business value or leverage by reusing existing solutions and focusing on core business logic.
---

# Identifying Leverage

This skill guides you to think like a Staff Engineer by focusing on high-leverage activities and avoiding "Not Invented Here" syndrome.

## Core Principles

1.  **Someone else has already solved your problem**:
    *   **Search First**: Before writing any code, search for existing libraries, tools, or templates that solve the problem.
    *   **Don't Reinvent the Wheel**: If a library handles 90% of your use case, use it. Documentation and community support are worth the 10% gap (which you can often patch).
    *   **Standard over Custom**: Prefer industry-standard protocols and tools over custom implementations (e.g., use OAuth2/OIDC providers instead of writing your own auth).

2.  **Know the Core Business**:
    *   **Focus on Differentiators**: Only build custom software for problems that are unique to the business's core value proposition.
    *   **Buy vs. Build**: If the problem is generic (e.g., monitoring, logging, authentication), prefer "buying" (using SaaS or established OSS) over building.
    *   **Maximize Impact**: Ask "Does this change directly improve the product for the customer?" If not, find the quickest way to get it done reliably.

## Actionable Instructions for Agents

*   **When asked to implement a feature**:
    1.  **Read Context**: Read `docs/company_context.md`. **If this file does not exist**, you MUST run the workflow `.agent/workflows/interview_company_context.md` to create it before proceeding.
    2.  Perform a search for existing libraries or tools that achieve the goal.
    3.  If a solution exists, propose using it and explain why (saves time, maintenance, handles edge cases).
    4.  Only proceed with custom implementation if no suitable existing solution is found or if the user explicitly requests a custom build for learning/specific constraints.

*   **When designing a system**:
    1.  **Read Context**: Check `docs/company_context.md`. **If missing**, run `.agent/workflows/interview_company_context.md`.
    2.  Identify which components are "commodity" (database, auth, queue) and which are "core" (business logic).
    2.  Select standard, managed services for commodity components.
    3.  Concentrate effort on the core business logic.
