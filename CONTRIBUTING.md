# Contributing

Architecture and code rules live in [CLAUDE.md](CLAUDE.md). This file
covers contributor process: release flow, language policy, and how
the repo is kept tidy.

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

## Language policy

**All repo content is English-only until v1.0.** README, CHANGELOG,
docs, code comments, commit messages, advisor messages, dashboard
strings, persistent_notification bodies — every word is English.

Translations of descriptive content (README, docs, info) start at
**v1.0**, alongside the v0.9 Python custom integration that enables
per-locale dashboard strings via `translations/{en,de,nl}.json`. Until
then, translation PRs add maintenance burden without user value (no
production installs exist yet).

If a contributor's first language isn't English, write the doc in
their language and ask for a translation review in the PR — easier
than guessing English idioms.

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
- [ ] No new `*.de.md` / `*.nl.md` files — translations resume at v1.0
- [ ] No drive-by reformatting outside the change scope
