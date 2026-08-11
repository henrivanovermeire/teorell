# Maintaining the GitHub Wiki from source

Canonical pages live in **`docs/wiki/`** in this repository.  
GitHub Actions (`.github/workflows/publish-wiki.yml`) copies them into the separate wiki git repo (`<repo>.wiki.git`).

## One-time GitHub setup

1. Repo → **Settings → General → Features** → enable **Wikis**.
2. Open the **Wiki** tab once (optional: add any blank Home page).  
   That creates `https://github.com/<owner>/<repo>/wiki`.
3. Push `docs/wiki/` (or run **Actions → Publish Wiki → Run workflow**).

Until Wikis are enabled, clone/push to `*.wiki.git` fails with `Repository not found` (same message as a missing private repo).

## Local edit workflow

```bash
# edit docs/wiki/*.md in a PR as usual
git add docs/wiki
git commit -m "docs(wiki): …"
git push
```

After merge to `main`/`master`, the publish workflow updates the Wiki.

Optional: clone the live wiki for inspection only:

```bash
git clone https://github.com/henrivanovermeire/teorell.wiki.git
```

Prefer editing `docs/wiki/` so changes go through review; don’t treat the Wiki UI as source of truth.
