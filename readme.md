# pre-commit-hooks
[![CircleCI](https://dl.circleci.com/status-badge/img/gh/level12/pre-commit-hooks/tree/main.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/gh/level12/pre-commit-hooks/tree/main)

## Usage

Ruff needs to be specified as a dependency in a Python package's `uv.lock` or
`requirements/dev.txt`.

Then, in `.pre-commit-config.yaml`:

```yaml

---
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.7
    hooks:
      - id: ruff
      - id: ruff-format
        args: [ --check ]
  - repo: https://github.com/level12/pre-commit-hooks
    rev: v0.20250226.1
    hooks:
      - id: check-ruff-versions
      # OPTIONAL: if you have a non-typical repo where the python packages are not in the root
      # and/or you have more than one package.  Most projects will not add these args.
      - args: [--package, foo-pkg, --package, bar-pkg]
```

## Dev

### Copier Template

Project structure and tooling mostly derives from the [Coppy](https://github.com/level12/coppy),
see its documentation for context and additional instructions.

This project can be updated from the upstream repo, see
[Updating a Project](https://github.com/level12/coppy?tab=readme-ov-file#updating-a-project).

### Project Setup

From zero to hero (passing tests that is):

1. Ensure [host dependencies](https://github.com/level12/coppy/wiki/Mise) are installed

2. Start docker service dependencies (if applicable):

   `docker compose up -d`

3. Sync [project](https://docs.astral.sh/uv/concepts/projects/) virtualenv w/ lock file:

   `uv sync`

4. Configure pre-commit:

   `pre-commit install`

5. Run tests:

   `nox`

### Versions

Versions are date based.  A `bump` action exists to help manage versions:

```shell

  # Show current version
  mise bump --show

  # Bump version based on date, tag, and push:
  mise bump

  # See other options
  mise bump -- --help
```
