# Code Review — Phase II (TOML 1.1 prek.toml via tomlkit)

Reviewer: Opus 4.7 (read-only). Scope: Phase II diff only.

## Must-fix

1. `load_toml` opens TOML files in text mode without an explicit encoding.
   `Path.open()` defaults to the platform's locale encoding (e.g. cp1252 on a
   default Windows install). The TOML spec mandates UTF-8, and the previous
   `open('rb')` delegated UTF-8 decoding to `tomllib`. On non-UTF-8 systems any
   non-ASCII byte in `prek.toml` or `uv.lock` will mis-decode or raise. Either:
   - `with toml_fpath.open('rb') as fo: return tomlkit.load(fo).unwrap()`
     (tomlkit's `load` accepts `IO[bytes]` and decodes UTF-8 internally), or
   - `toml_fpath.open(encoding='utf-8')`.
   Preferred: `'rb'` so the only behavioural change vs. Phase I is the parser.

## Should-fix

1. Downstream-installation impact is not called out anywhere user-facing.
   With `tomlkit @ git+https://...` in `[project].dependencies`, every consumer
   of `check-ruff-versions` (via prek/pre-commit, pip, uv, etc.) now needs the
   `git` CLI plus network access to GitHub when the hook environment is first
   built. This is a meaningful change in install requirements for downstream
   repos. Worth a one-line note in `readme.md` and/or in the spec's Decision
   list, plus a TODO to revert to a registry version once upstream tomlkit
   releases TOML 1.1 multi-line inline-table support.

2. Spec hygiene. `specs/2026-05-09-support-prek-toml.md` Phase II section
   restates the implementation prompt and an "Implemented:" bullet list. Per
   the project's spec guidance ("Do not duplicate implementation details ...
   into spec documents when the code is the source of truth"), prune that
   section to just the new Decisions plus the validation outcome already
   present. The two relevant decisions are already captured above the
   `# Validation` heading; the `## Phase II` block is largely redundant.

3. `[tool.uv.sources]` for tomlkit duplicates the PEP 508 direct-URL form
   already in `[project].dependencies`. uv is happy with either alone; keeping
   both is harmless but invites drift if one is bumped without the other.
   Recommend dropping the `[tool.uv.sources]` entry and relying on the PEP 508
   URL (which is also what non-uv consumers must use anyway).

4. Performance / scope creep. `dev_version_uv()` now goes through tomlkit too.
   `uv.lock` is strictly TOML 1.0, machine-generated, and read on every commit.
   tomlkit preserves whitespace/comments and is materially slower than
   `tomllib`. Keep `tomllib` for `uv.lock` (and any future machine-emitted
   TOML) and use tomlkit only for `prek.toml`. That also limits the blast
   radius of the unreleased-tomlkit pin to the one file format that requires
   it.

## Nits

- `tomlkit.load(fo).unwrap()` — `.unwrap()` discards tomlkit's container
  types and returns plain dict/list, which is what the rest of the module
  expects. Fine, but a one-line `# .unwrap() drops tomlkit metadata; we only
  need plain dict/list` comment would document intent.
- Test name `test_toml_1_1` reads as a feature-flag check; something like
  `test_multiline_inline_table` would convey the actual exercised feature
  (matching the rest of the suite which is behaviour-oriented).
- `tests/pre_commit_hooks_tests/check-ruff-versions-prek-toml-1-1/uv.lock`
  is a 5-line fixture without a final newline (matches the existing
  `check-ruff-versions-prek-same/uv.lock` style — leaving as-is is fine).

## Verified

- The new fixture genuinely requires TOML 1.1: `tomllib.load()` and released
  `tomlkit==0.14.0` both raise on lines 5–7 (multi-line inline table +
  trailing comma). The pinned upstream commit parses it cleanly.
- After `uv sync --frozen`, the full `test_check_ruff_versions.py` suite
  (15 tests) passes locally. NB: my first run of the suite failed because
  the venv still had registry tomlkit 0.14.0 installed; `uv sync --frozen`
  was required to pull the git revision. Worth keeping in mind when running
  CI on a cached venv.
- `prek validate-config` accepts both `./prek.toml` (which itself uses
  multi-line inline tables) and the new fixture.
- `hatch.metadata.allow-direct-references = true` is correctly added; without
  it hatchling rejects the PEP 508 direct URL at build time.
- The full git SHA pin is reproducible (good).
- The new test exercises real parser behaviour, not just coverage padding.

## Simpler / better approach considered

- Falling back from `tomllib` to `tomlkit` only when `tomllib` raises would
  scope the new dependency to the prek.toml path only, but it adds branching
  and a second exception type to reason about; not worth it.
- Shelling out to `prek` to dump parsed config would avoid the TOML-parser
  problem entirely, but introduces a hard runtime dependency on the `prek`
  binary in every consumer environment. Worse trade-off.
- The cleanest path forward is the one in this PR plus must-fix #1 plus
  should-fix #4 (keep tomllib for `uv.lock`), and revisiting the pin once
  upstream tomlkit cuts a release with the TOML 1.1 inline-table parser.

## Verdict

Not blocking on correctness for the documented Linux/macOS dev environment,
but the encoding issue in `load_toml` is a real latent bug worth fixing
before tagging a release. The downstream-install footprint change deserves a
brief mention in the spec/readme. Everything else is should-fix or nits.
