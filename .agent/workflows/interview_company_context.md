---
description: Interview the user to establish the company context and technology stack.
---

# Company Context Interview

Follow these steps to generate `docs/company_context.md`. This document is critical for the `identifying-leverage` and `technical-strategy` skills.

1.  **Check for existing context**:
    -   Check if `docs/company_context.md` exists.
    -   If it exists, read it and ask the user if they want to update specific sections.

2.  **Gather Information**:
    -   Ask the user the following questions. **Group these into 3-4 distinct prompts** to avoid overwhelming the user with a massive list.

    **Group 1: Strategy & Business**
    *   **Core Business**: "What is the primary business value or product? What directly drives revenue vs what is supporting infrastructure?"
    *   **Strategic Focus**: "What is the current highest priority for engineering? (e.g., Velocity/Speed to market, High Stability, Cost Optimization, Scalability)."
    *   **Build vs. Buy**: "What is the organization's stance on building custom tools vs. buying SaaS/off-the-shelf solutions?"

    **Group 2: Infrastructure & Cloud**
    *   **Cloud Provider**: "Which Cloud Provider do we use? (AWS, GCP, Azure, On-prem/Hybrid?)"
    *   **Orchestration**: "How are applications deployed? (Kubernetes, Serverless/Lambda, VMs, PaaS/Heroku?)"
    *   **Infrastructure as Code**: "What do we use for IaC? (Terraform, Pulumi, CloudFormation, none?)"
    *   **Database & Storage**: "What are the standard data stores? (Postgres, MySQL, DynamoDB, Redis, S3?)"

    **Group 3: Development & CI/CD**
    *   **Local Environment**: "What is the standard local dev setup? (Mac/Linux/Windows? Docker/DevContainers?)"
    *   **CI/CD**: "What CI/CD system is used? (GitHub Actions, GitLab CI, Jenkins?)"
    *   **Key Constraints**: "Are there strict deployment windows or change freeze periods?"

    **Group 4: Observability, Standards & specific constraints**
    *   **Observability**: "What tools are used for Logs, Metrics, and Traces? (Datadog, Splunk, Prometheus/Grafana, ELK?)"
    *   **Languages**: "What are the primary and secondary programming languages?"
    *   **Compliance**: "Are there major regulatory requirements? (HIPAA, PCI, GDPR, SOC2?)"

3.  **Create/Update Document**:
    -   Based on the answers, create or update `docs/company_context.md` with the following structure:

    ```markdown
    # Company Context

    ## 1. Core Business & Strategy
    - **Value Proposition**: [Description]
    - **Strategic Priorities**: [Priorities]
    - **Build vs Buy Stance**: [Philosophy]

    ## 2. Infrastructure & Cloud
    - **Cloud**: [Provider]
    - **Orchestration**: [Platform]
    - **IaC**: [Tooling]
    - **Data**: [Stores]

    ## 3. Development Process
    - **Local Env**: [OS/Tools]
    - **CI/CD**: [System]
    - **Languages**: [Primary/Secondary]

    ## 4. Operations & Standards
    - **Observability**: [Tools]
    - **Compliance**: [Requirements]
    ```

4.  **Finalize**:
    -   Commit the file to the repository (if applicable) or confirm creation to the user.
