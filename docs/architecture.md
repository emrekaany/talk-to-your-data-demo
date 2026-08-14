# Architecture

## Objective

Demonstrate the smallest credible Talk to Your Data loop without a secret, provider account, real database or unrestricted SQL-generation path.

## Components

| Component | Responsibility | Trust boundary |
| --- | --- | --- |
| `catalog.py` | Normalize English/Turkish questions and select one reviewed plan | User text is untrusted and bounded to 500 characters |
| `guardrails.py` | Enforce SELECT/CTE, table allowlist, blocked operations and row cap | SQL is revalidated even though templates are maintained in-repo |
| `synthetic.py` | Build deterministic in-memory SQLite fixtures | No filesystem, client or network data is loaded |
| `service.py` | Execute with timeout, read-only authorizer and safe output projection | SQLite output is converted to JSON-safe scalar values |
| `web/server.py` | Serve the local UI and bounded JSON endpoints | Loopback host/origin, body-size and content-type checks |
| `cli.py` | Provide reproducible demo, ask, questions and serve commands | Does not load environment credentials |

## Request sequence

1. Validate question type, length and control characters.
2. Normalize only for template matching; keep the original question for display.
3. Require every keyword group for one supported plan.
4. Compile a static SQL template and explicit bind parameters.
5. Validate statement form, comments, blocked keywords, referenced tables and row limit.
6. Build a fresh deterministic in-memory database.
7. Enable SQLite `query_only`, write-denying authorizer and progress timeout.
8. Execute, fetch at most 201 rows, return at most 200 and mark truncation.
9. Produce a deterministic summary from aggregate result fields.

## Failure behavior

- Unsupported question: HTTP 400 / CLI error with supported examples.
- Invalid SQL policy: fail before SQLite execution.
- SQLite write attempt: denied by both `query_only` and authorizer.
- Execution budget exceeded: SQLite is interrupted and no partial result is returned.
- Invalid host/origin/body: request rejected before service execution.

## Deliberate exclusions

The public repo excludes real metadata, arbitrary SQL, LLM credentials, customer connections, vector databases, feedback persistence, enterprise auth, distributed cancellation and production deployment. Those require a private threat model and an authorized environment.
