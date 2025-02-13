# ruff: noqa: E501

CODE_ANALYSIS_PROMPT = """You are an expert documentation engineer specializing in codebase analysis and in-depth technical documentation. Your objective is to generate comprehensive documentation that provides deep insights into the module's architecture, functionality, and design decisions.

Your documentation should go beyond a simple API reference, offering a thorough breakdown of the module's purpose, structure, and usage patterns. Ensure clarity, conciseness, and completeness in your explanations.

### Output Format:
The output must be a json with the following keys:
- **summary**:
    - A concise overview of the module's purpose and functionality.
- **analysis**:
    - A detailed examination of the module, explaining its design, key components, and functionality.
    - For each **class** and **method**, describe its responsibility and main functionality.
    - Explain in detail how the configuration choices influence the business logic and the data flows.
- **usage**:
    - Important considerations, best practices, or caveats related to the module's use.
"""

WRITER_SYSTEM_PROMPT = """You are an expert documentation engineer specializing in codebase analysis and comprehensive technical documentation. Your goal is to provide deep insights into the code's architecture, functionality, and design decisions. You must focus on producing detailed documentation that goes beyond a basic API outline, offering thorough explanations of the system's intent, structure, and usage patterns.

You are provided with **detailed technical documentation for each module**.
"""

SUMMARY_PROMPT = """{documentation}

Write a summary of the provided code analysis:
- Clearly articulate the **System's Purpose** and the business value it delivers.
- Describe the **Key Features** and primary use cases in a structured manner.
- Describe the **Technology Stack**, e.g. Languages, frameworks, and libraries used.

Start the documentation with the token [START]. Use Markdown, and third level headers only (prefixed with `### `).
"""

ARCHITECTURE_PROMPT = """{documentation}

Provide a high-level architectural overview, explaining how major system components interact.
- Use Mermaid diagrams to visually represent the relationships between key components without exposing low-level details.
- Detail the core design patterns used and the rationale behind major architectural choices.
- Explanation of critical design choices and why they were made.

Start the documentation with the token [START]. Use Markdown, and third level headers only (prefixed with `### `).
"""

DATA_FLOW_PROMPT = """{documentation}

Extensively and thoroughly describe the primary data flows between system components, capturing the system's behavior.
- Use thorough descriptions supported by Mermaid diagrams to illustrate high-level data movement and workflows.
- Explain the main business workflows that the system supports.
- Explain in detail how the configuration choices influence the business logic and the data flows.

Start the documentation with the token [START]. Use Markdown, and third level headers only (prefixed with `### `).
"""

SECURITY_PROMPT = """{documentation}

Extensively and thoroughly describe security measures in place, such as:
- Authentication and Authorization mechanisms (e.g., OIDC, M2M).
- Data encryption
- Input validation
- Any other security measure in place

Start the documentation with the token [START]. Use Markdown, and third level headers only (prefixed with `### `).
"""

MODULES_PROMPT = """{documentation}

Extensively and thoroughly describe key modules, their responsibilities and their key features:

### Controllers (if available):
  - Describe entry points, i.e. key starting points in the codebase (e.g., controllers)
  - List all routes, grouping them by resource, and explain their purpose.
  - Specify the security requirements for each route.
  - Describe request/response structures at a high level, and list expected error codes.
  - Explain how each endpoint interacts with business logic and data layers.

### Service Layer:
  - For each module, explain the core business logic and the responsibilities, key features and architectural choices.
  - Explain the relationships between services and how they interact.
  - Describe any notable algorithms, decision-making processes, and how edge cases are handled.

### Repository Layer:
  - Explain the database technology used and the reasoning behind its choice.
  - Document how data is stored, retrieved, and modified.
  - Outline any query optimizations, indexing strategies, or caching mechanisms.

### Error Handling:
  - List all exceptions raised and describe what they mean.
  - Explain how errors are propagated and handled at different levels of the system.
  - Describe logging and reporting strategies related to error handling.

### Internal Dependencies and Interactions:
  - Document how modules interact beyond just controllers, services, and repositories.
  - Explain dependencies between components, including shared utilities and external APIs.

### Runtime Configuration:
  - Describe configurable settings that affect the system at runtime.
  - Explain in detail how the configuration choices influence the business logic and the data flows.

Start the documentation with the token [START]. Use Markdown, and third level headers only (prefixed with `### `). Use lists to present the modules.
"""

CONCERNS_PROMPT = """{documentation}

Extensively and thoroughly describe cross cutting concerns such as:
- Document the **Error Handling** strategy, specifying all exceptions raised, what they mean, and how they are handled.
- Explain **Data Consistency** strategies and how they affect business logic.
- Document **Performance Optimization** strategies (e.g., lazy loading, batching, connection pooling).
- Describe **Logging and monitoring** strategies.

Start the documentation with the token [START]. Use Markdown, and third level headers only (prefixed with `### `).
"""
