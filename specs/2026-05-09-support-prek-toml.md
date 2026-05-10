# Spec: add support for prek.toml

We need this project to also work with prek. To accomplish that, we have to be able to get
the ruff version from a prek.toml file as well as a .pre-commit-config.yaml file.

I've put a prek.toml file in ./tmp so you can see what it looks like. You can also get
details on the config format at:

https://prek.j178.dev/configuration/

# Opus Reviews

Get code reviews from Opus for this spec.

# Implementation Notes

- Decision: match prek's documented config precedence by using `prek.toml` before
  pre-commit YAML when both exist in the same directory.
- Decision: preserve the existing expectation that a repo hook config file must exist;
  supported project config names are `prek.toml`, `.pre-commit-config.yaml`, and
  `.pre-commit-config.yml`.
- Decision: include `prek.toml` in the hook trigger pattern.
- Decision: Phase II switches TOML parsing from stdlib `tomllib` to `tomlkit` so TOML 1.1
  prek configs can be parsed.
- Decision: no released `tomlkit` version supports TOML 1.1 multiline inline tables yet as
  of 2026-05-09, so the dependency is pinned to upstream commit
  `7f237d8f5d07d23422571e9daaf411f4a2356855` until a release includes that parser change.
- TODO: switch back to a released `tomlkit` version once an upstream release includes the
  TOML 1.1 parser change.

# Validation

Targeted Ruff and pytest validation passed.

Phase II targeted pytest, `prek validate-config prek.toml`, targeted Ruff, and an Opus
review passed after addressing the review feedback.
