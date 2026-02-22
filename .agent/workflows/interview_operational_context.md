---
description: Interview the user to establish operational context (ownership, deployment, resources).
---

# Operational Context Interview

Follow these steps to generate `docs/operational_context.md`. This document is critical for the `technical-strategy` skill and for understanding how to *run* the software.

1.  **Check for existing context**:
    -   Check if `docs/operational_context.md` exists.
    -   If it exists, read it and ask the user if they want to update specific sections.

2.  **Gather Information**:
    -   Ask the user the following questions. Group them logically.

    **Group 1: Ownership & Support**
    *   **Owner**: "Who is the primary owner (Team/Person) of this service?"
    *   **On-Call**: "Is there an on-call rotation? How is it triggered?"
    *   **Communication**: "Where should alerts/notifications go? (Slack channel, PagerDuty?)"

    **Group 2: Resources & Limits**
    *   **Budget**: "Are there strict cost constraints or budget limits?"
    *   **Sizing**: "What are the expected resource requirements? (High CPU, High Memory, Storage heavy?)"
    *   **Runtime Scaling**:
        -   *For Node.js/Python*: "Since the runtime is single-threaded, do we plan to scale horizontally (replicas) or use a process manager (PM2/Gunicorn)?"
        -   "Is the traffic steady, bursty, or batch? This determines auto-scaling rules."
    *   **Unknowns**: "If sizing is unknown, do we have historical data (Grafana/CloudWatch) or should we add a task for load testing?"

    **Group 3: Release & Publishing**
    *   **Registry**: "Where are artifacts published? (Docker Hub, ECR, GCR, Artifactory?)"
    *   **Versioning**: "What is the versioning strategy? (SemVer, Date-based, Commit hash?)"
    *   **Secrets**: "How are secrets managed? (Vault, AWS Secrets Manager, K8s Secrets, Env Vars?)"

    **Group 4: Environments**
    *   **Staging/Prod**: "What are the URLs or access points for Staging and Production?"
    *   **Region**: "Which regions is this deployed to?"

3.  **Create/Update Document**:
    -   Based on the answers, create or update `docs/operational_context.md`.
    -   **Important**: Any "Unknowns" identified in Group 2 should be listed under "Production Readiness & Discovery".

    ```markdown
    # Operational Context

    ## 1. Ownership
    - **Owner**: [Team/Person]
    - **Contact**: [Channel/Email]
    - **On-Call**: [Policy]

    ## 2. Resources
    - **Budget**: [Constraints]
    - **Sizing**: [Requirements]
    - **Scaling Strategy**: [Horizontal/Vertical/Process Manager]
    - **Traffic Pattern**: [Steady/Bursty/unknown]

    ## 3. Release & Publishing
    - **Registry**: [Target]
    - **Versioning**: [Strategy]
    - **Secrets**: [Method]

    ## 4. Environments
    - **Production**: [Details]
    - **Staging**: [Details]
    - **Regions**: [Location]

    ## 5. Production Readiness & Discovery
    - [ ] [Unknown Item 1]
    - [ ] [Unknown Item 2]
    ```

4.  **Finalize**:
    -   Confirm creation to the user.
