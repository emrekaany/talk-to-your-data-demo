# Contributing

Contributions that strengthen the offline demo, tests, documentation or safe question catalog are welcome.

## Local gate

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -m talk_to_your_data_demo demo --json
```

## Data and secret boundary

Only fictional, deterministically generated fixtures are accepted. Never submit credentials, URLs with embedded tokens, real schema/table names, client data, private prompts, exported logs or screenshots from a private environment.

New question templates must remain aggregate-only, reference allowlisted synthetic tables, include a row cap and ship with positive and negative tests.
