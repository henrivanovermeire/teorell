# Publishing teorell-core

The **PyPI package is the simulation core only** (`teorell_core`). The live Vite/FastAPI UI stays in this GitHub repository (run via `./scripts/run-live.sh` or Docker Compose).

**Default path: TestPyPI first**, then production PyPI only by manual workflow.

```text
bump version → GitHub Release (vX.Y.Z)
       ↓
 Publish to TestPyPI  (automatic)
       ↓
 pip install from TestPyPI, sanity-check
       ↓
 Actions → “Publish to PyPI” → type publish
```

## One-time setup (Trusted Publishing)

No API tokens in GitHub Secrets. Use [Trusted Publishers](https://docs.pypi.org/trusted-publishers/).

### TestPyPI (required first)

1. Account on [test.pypi.org](https://test.pypi.org/) (separate from production PyPI).
2. Add a **pending publisher** for project `teorell-core`:
   - Owner: `henrivanovermeire`
   - Repository: `teorell`
   - Workflow: `publish-testpypi.yml`
   - Environment: `testpypi`
3. GitHub → **Settings → Environments** → create **`testpypi`**.

### Production PyPI (when ready)

1. Account on [pypi.org](https://pypi.org/).
2. Pending publisher for `teorell-core`:
   - Workflow: `publish-pypi.yml`
   - Environment: `pypi`
3. GitHub environment **`pypi`** — strongly recommended: require **your** review before deploy.

## Cut a release (TestPyPI)

1. Bump `version` in `pyproject.toml` (e.g. `0.1.0` → `0.1.1`).
2. Commit and push.
3. GitHub → **Releases → Draft a new release**:
   - Tag: `v0.1.1` (must match `pyproject.toml`, with a `v` prefix)
   - Publish the release
4. Workflow **Publish to TestPyPI** builds and uploads via OIDC.

Install the TestPyPI build (numpy still comes from real PyPI):

```bash
pip install -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  teorell-core==0.1.1
```

## Promote to production PyPI

After the TestPyPI install looks good:

1. Actions → **Publish to PyPI** → **Run workflow**
2. In the `confirm` field, type exactly: `publish`
3. Approve the `pypi` environment if you enabled required reviewers

Checkout uses the default branch tip — **ensure `pyproject.toml` version on that branch is the version you intend to ship** (same as the TestPyPI release).

```bash
pip install teorell-core
```

## Who can run Actions? (public repo)

| Actor | CI on PRs | TestPyPI / PyPI publish |
|-------|-----------|-------------------------|
| You (admin/maintainer) | Yes | Yes (releases + workflow_dispatch; env may need approval) |
| Collaborators with write access | Yes | Only if they can create releases / run workflows / approve envs |
| Outside contributors (fork PRs) | CI may run; **no** OIDC publish | **Cannot** publish |
| Anyone else | Actions on **their** fork only | Cannot publish to **your** projects |

Trusted Publishing binds uploads to **this** repo + the named workflow + environment. Public visibility does not let strangers release `teorell-core`.
