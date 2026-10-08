# 17 · Release: 0.1.0 on PyPI (M6)

**Implements:** design § 13's release line and § 14's M6 row: "a tag publishes to PyPI". It amends
`03-cli-and-packaging.md` (the version and the classifiers at release) and the README's Quick start,
Status, and Deployment sections.

**Amended 2026-10-02, by the owner:** inkgrid publishes as their other packages do (feathers,
slowquery-detective): `uv publish` with the repository secret `PYPI_API_TOKEN`, and a `testpypi-v` tag
rehearses on TestPyPI with `TEST_PYPI_API_TOKEN`. This replaces Trusted Publishing with attestations,
the design's first plan; a token upload carries no PEP 740 attestation.
**Modules:**
- `scripts/check_release.py` (new): the release check, a pure function of the tag and the files it
  reads, and its command line (§ 2);
- `.github/workflows/release.yml` (new): the release workflow (§ 3);
- `pyproject.toml`, `CHANGELOG.md`, `README.md`: the release commit (§ 4).

---

## 0 · What was measured first

On 2026-10-01: the name `inkgrid` is free on PyPI and on TestPyPI (`/pypi/inkgrid/json` answers 404
on both). The repository `Abdul-Muizz1310/inkgrid` is public and has no deployment environments.
`pypa/gh-action-pypi-publish` is at v1.14.2 (`dc37677b`), which uploads PEP 740 attestations by
default when the job holds `id-token: write`. `actions/upload-artifact` is at v7.0.1 and
`actions/download-artifact` at v8.0.1. Python 3.15.0 is not yet published: python.org lists no final
3.15 release, and uv 0.12.19 offers 3.15.0rc2. So CI's 3.15 job stays allowed to fail, and the
classifiers name 3.12 to 3.14 until a later release.

## 1 · The release, in order

1. M5 is merged: the README's claims match the committed results (design § 14, M5's exit).
2. **Look-back before the release** (design § 12): the 42 fee schedules of the look-back corpus are
   read and verified at the release commit, one document at a time. The README's verifier sentence
   (characters accounted for, cells reported) is updated to that run.
3. The release commit (§ 4) lands on `main` and CI passes on it.
4. The owner provides the PyPI token (§ 5). **No tag is pushed before it is the repository's
   secret.**
5. The tag `v0.1.0` is pushed. The workflow checks, tests, builds once, and publishes to PyPI.
6. `pip install inkgrid==0.1.0` into a fresh environment runs the smoke test (`tests/smoke_test.py`).

## 2 · The release check (`scripts/check_release.py TAG`)

`problems(tag, *, version, changelog, readme) -> list[str]` returns every reason the tag must not
publish; the command prints each one and exits 1, or exits 0 when there are none. It reads the
version from `pyproject.toml` (`[project].version`). The refusals:

- the tag is not `v` followed by a final version `X.Y.Z` (no `.devN`, `aN`, `bN`, `rcN`, `.postN`, or
  local part);
- the tag's version is not the project's version;
- `CHANGELOG.md` has no section `## [X.Y.Z] - YYYY-MM-DD` with a real date, or no link reference
  `[X.Y.Z]: https://github.com/Abdul-Muizz1310/inkgrid/releases/tag/vX.Y.Z`, or its `[Unreleased]`
  section holds an entry (anything but blank lines before the next `## ` heading);
- the README still says inkgrid is not on PyPI, or its Quick start has no `pip install inkgrid`.
- the README links relatively (a Markdown `](path)` or an HTML `href`/`src` that is not absolute or
  in-page): PyPI renders the README at `pypi.org/project/inkgrid/`, where such a link is a 404, and a
  release's description cannot be changed after upload.

## 3 · The release workflow (`.github/workflows/release.yml`)

- **Trigger:** only a pushed tag matching `v*` (PyPI) or `testpypi-v*` (TestPyPI); no branch push, pull
  request, or manual dispatch.
- **Permissions:** `permissions: {}` at the top; only `build` adds one (`contents: read`).
- **`build`** (`contents: read`): check out without persisting credentials; set up uv; sync with
  `--locked`; run the release check on the tag without its `testpypi-` prefix, passed through an
  environment variable (never interpolated into the script); run the test suite and the slow
  distribution tests; build the sdist and the wheel once with `uv build --no-sources`; upload `dist/`
  as one artifact.
- **`publish-testpypi`** (a `testpypi-v` tag only; needs `build`; environment `testpypi`): download the
  artifact and `uv publish` it to `https://test.pypi.org/legacy/` with `TEST_PYPI_API_TOKEN`, checking
  TestPyPI's index so a file it already has is skipped.
- **`publish-pypi`** (a `v` tag only; needs `build`; environment `pypi`): download the artifact and
  `uv publish` it to PyPI with `PYPI_API_TOKEN`, checking PyPI's index, so a rerun after a partial
  upload skips what landed.
- The publish jobs never check out or run the repository's code. Each secret appears once, as
  `UV_PUBLISH_TOKEN` in its own job's step environment; `--trusted-publishing never` keeps uv from
  trying OIDC.
- Every action is pinned by its full commit SHA with its version as a comment, as in `ci.yml`.

## 4 · The release commit

- The version goes from `0.1.0.dev0` to `0.1.0` with `uv version --bump stable`, and `uv.lock` follows.
- `CHANGELOG.md`: `[Unreleased]`'s entries move under `## [0.1.0] - <date>`, `[Unreleased]` stays as
  an empty heading, and the link references are added at the foot.
- The classifier becomes `Development Status :: 3 - Alpha`.
- README: the Status line names 0.1.0; the Quick start opens with `pip install inkgrid` (uv:
  `uv add inkgrid`), keeping the from-a-clone commands for development; Deployment states how a
  release is made.

## 5 · The tokens (the owner)

The owner's PyPI API token is the repository secret `PYPI_API_TOKEN`, set from the workspace's
git-ignored `.env` without being printed; a TestPyPI token, when the owner makes one, is
`TEST_PYPI_API_TOKEN`. The workflow creates the environments `pypi` and `testpypi` on first use; a
required reviewer on `pypi` is the owner's choice and is not required by this spec.

## 6 · Cases

| Case | Input | Expected |
|---|---|---|
| RL1 | the tag `v0.1.0`, version `0.1.0`, a changelog with a dated `[0.1.0]` section, its link, and an empty `[Unreleased]`, a README with `pip install inkgrid` | no problems |
| RL2 | the tags `0.1.0`, `v0.1`, `v0.1.0rc1`, `v0.1.0.dev0`, `v0.1.0.post1`, `v0.1.0+local` | each refused: not a final version tag |
| RL3 | the tag `v0.1.1` with version `0.1.0`; the version `0.1.0.dev0` with the tag `v0.1.0` | refused: the tag is not the project's version |
| RL4 | a changelog with no `[0.1.0]` section; with `## [0.1.0] - 2026-02-30`; with no link reference; with an entry under `[Unreleased]` | each refused, naming what is missing |
| RL5 | a README that says inkgrid is not on PyPI yet; one with no `pip install inkgrid` | refused |
| RL6 | `scripts/check_release.py` run on a refused tag; on the release commit's tag | exits 1 printing every problem; exits 0 |
| RL7 | `release.yml` | triggered only by `v*` and `testpypi-v*` tags; `permissions: {}`; `build`, then `publish-testpypi` (a `testpypi-v` tag) or `publish-pypi` (a `v` tag), each in its environment; each token only as its job's `UV_PUBLISH_TOKEN`; `uv publish --trusted-publishing never` with its index's `--check-url`; no checkout or `id-token` in a publish job |
| RL8 | every workflow under `.github/workflows/` | every `uses:` pinned to a 40-character commit SHA with a version comment |
| RL9 | a README with `<a href="LICENSE">` and `[spec](docs/specs/12.md)`; one whose links are absolute or in-page | refused, naming both targets; no problem |
| RL10 | a README whose Quick start heading carries the house style's emoji (`## <emoji> Quick start`); one whose `pip install inkgrid` stands only in another section | no problem; refused |

## 7 · Acceptance

- RL1 to RL10 pass, and `scripts/dev.sh` is green.
- § 1's steps 1 to 3 are done, with the look-back run's result recorded in the README and in
  `docs/specs/10-verify.md`.
- Once the token is the repository's secret (§ 5): the tag is pushed, the upload succeeds, and a
  fresh install of `inkgrid==0.1.0` from PyPI passes the smoke test.
