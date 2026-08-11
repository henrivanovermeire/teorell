# Publishing teorell-core to PyPI

The **PyPI package is the simulation core only** (`teorell_core`). The live Vite/FastAPI UI stays in this GitHub repository (run via `./scripts/run-live.sh` or Docker Compose).

## One-time setup (Trusted Publishing)

No API tokens in GitHub Secrets. Use [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/):

1. Create a PyPI account and verify email.
2. Create project **teorell-core** (or publish once manually, then attach the publisher).
3. On PyPI → Project → **Publishing** → **Add a new pending publisher**:
   - Owner: `henrivanovermeire`
   - Repository: `teorell`
   - Workflow: `publish.yml`
   - Environment: `pypi`
4. In GitHub → **Settings → Environments → New environment** named `pypi`.
   - Optional: require yourself as a required reviewer before deploy.
5. Ensure the default branch is `main` (or `master` — CI listens to both).

## Cut a release

1. Bump `version` in `pyproject.toml` (e.g. `0.1.0` → `0.1.1`).
2. Commit and push.
3. GitHub → **Releases → Draft a new release**:
   - Tag: `v0.1.1` (must match `pyproject.toml`, with a `v` prefix)
   - Title / notes: summarize changes
   - Publish the release
4. The **Publish to PyPI** workflow runs tests, builds the wheel/sdist, and uploads via OIDC.

Install:

```bash
pip install teorell-core
```

## Who can run Actions? (public repo)

| Actor | CI on PRs | Publish to PyPI |
|-------|-----------|-----------------|
| You (admin/maintainer) | Yes | Yes (create releases; environment may require approval) |
| Collaborators with write access | Yes | Only if they can create releases / approve `pypi` env |
| Outside contributors (fork PRs) | CI runs on your repo with **no** secrets / **no** OIDC publish credentials | **Cannot** publish |
| Anyone else | Can fork and run Actions on **their** fork (their minutes) | Cannot publish to **your** PyPI project |

Trusted Publishing binds PyPI uploads to **this** repo + **publish.yml** + **pypi** environment. Random public users cannot push packages as `teorell-core` even if the repo is public.
