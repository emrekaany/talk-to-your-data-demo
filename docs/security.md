# Security model

## Protected assets

There are no production assets in this repository. The security objective is to prevent the demo from becoming an accidental arbitrary-SQL or network service.

## Controls

- deterministic synthetic in-memory data;
- no runtime dependencies or outbound networking;
- no environment-variable credential interface;
- bounded question and request sizes;
- static SQL templates plus independent policy validation;
- table allowlist and blocked write/schema keywords;
- SQLite query-only mode and write-denying authorizer;
- 200-row result cap and 500 ms default execution budget;
- loopback-only HTTP bind, host/origin validation and browser security headers;
- JSON/DOM rendering without response HTML injection.

## Non-goals

This demo is not approved for public hosting, real databases, untrusted multi-user traffic or arbitrary model-generated SQL. Treat any such extension as a new security design, not a configuration switch.

## Secret policy

Do not add `.env` files, tokens, connection strings, real metadata, customer data, internal screenshots, production prompts or exported query logs. CI and contribution review should reject them.
