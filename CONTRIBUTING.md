# Contributing

Branch from the latest `origin/main`. Keep each pull request to one concern.

## Checks

Before committing:

```bash
./scripts/quick-lint-check.sh
```

Before pushing:

```bash
./scripts/ci-lint-check.sh
```

`./scripts/check-lint-issues.sh --fix` applies Black and isort. The lint settings in `pyproject.toml` stay as they are.

Tests need Docker:

```bash
cd tests && ./run_all_tests.sh --quick
```

A change that does not touch the registry client can run the relevant pytest file instead. [TESTING_SETUP_GUIDE.md](TESTING_SETUP_GUIDE.md) describes the Docker environment. [AGENTS.md](AGENTS.md) is the full checklist.

## Review

[CODEOWNERS](CODEOWNERS) requests `@aywengo` on every pull request.

Publishing images and the Helm chart is described in [docs/release-process.md](docs/release-process.md).
