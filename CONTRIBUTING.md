# Contributing

🌐 English (this file)

Architecture and code rules live in [CLAUDE.md](CLAUDE.md). This file
covers contributor process: how releases happen, how translations
work, and how the repo is kept tidy.

## Release flow

1. All changes for the release land on `main` with passing smoke + CI.
2. Update `VERSION` to the new SemVer (`x.y.z`).
3. Add a new section to `CHANGELOG.md` under the version, following
   [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) conventions
   (Added / Changed / Fixed / Removed).
4. Commit as `chore(release): vX.Y.Z` (or fold into the last `feat:`
   commit if the release is a single feature).
5. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z — one-line summary"`.
6. Push: `git push origin main --tags`.

HACS picks up the tag automatically once the repo is registered as a
HACS-default plugin (currently custom-repo only).

For SemVer scope (what counts as MAJOR / MINOR / PATCH), see
[CLAUDE.md → SemVer scope](CLAUDE.md#semver-scope-post-v10).

## Translation convention

Repo-level documentation is bilingual:

- English is primary (`README.md`, `CHANGELOG.md`, `docs/*.md`,
  `CLAUDE.md`).
- German translations live alongside as `*.de.md` (root level) or under
  `docs/de/*.md`.
- Dutch translations follow the same pattern as `*.nl.md` for
  high-traffic files only (currently `README.nl.md`, `info.nl.md`).

When you change an English doc, the corresponding German file goes out
of sync. Either update both in the same commit, or open a follow-up
issue tagged `i18n` so the drift is visible.

User-facing dashboard strings and advisor messages are **always
English** (see CLAUDE.md). This is an architectural decision, not a
translation gap — per-language dashboard strings require the v0.9
Python custom integration.

## Line endings

The repo uses LF line endings on every file. Windows clients see CRLF
warnings on commit; if those become a real annoyance, add a
`.gitattributes`:

```
* text=auto eol=lf
```

Don't bypass via per-developer `core.autocrlf` settings — that produces
phantom diffs in shared review.

## Pull requests

- Reference the related issue (or open one first for non-trivial work)
- Run `py tests/smoke.py` and confirm green in the PR description
- One feature axis per PR — split mixed concerns into separate PRs
- Commit messages: `feat|fix|refactor|chore|docs(scope): summary` with
  a body explaining *why* for non-trivial changes
- For new vendor recipes: add a file under `docs/vendors/<vendor>.md`
  matching the structure of `panasonic_heishamon.md`
- For new fault codes: extend `hph_diagnostics.yaml` and document in
  `docs/diagnostics.md` — smoke test verifies consistency

## Code review checklist (for reviewers)

Architecture / behavior — is the change consistent with CLAUDE.md?

- [ ] New sensors have `unique_id`, `availability:` if source-adapter-dependent
- [ ] New advisor entries are aggregated in `hph_advisor_summary`
- [ ] No new `panasonic_*` references outside the whitelisted files
- [ ] `CHANGELOG.md` updated under the right version block
- [ ] Smoke green (CI confirms; reviewer can re-verify locally)

Process:

- [ ] Commit message follows the convention
- [ ] German translation kept in sync OR `i18n` issue opened
- [ ] No drive-by reformatting outside the change scope
