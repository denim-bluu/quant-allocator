# Publishing runbook (manual, last)

Publication is deliberate and human-gated. Do not automate these steps.

1. **Populate local sensitive terms.** Create `tools/.publication_terms`
   (gitignored) with any employer or manager names to scan for, one per line.
   This file is never committed.

2. **Run the readiness scan and review every hit.**
   ```bash
   bash tools/publication_check.sh | less
   ```
   The scan is report-only. Joon reviews all working-tree and git-history hits
   and decides whether any history rewrite is required before the repo goes
   public. Nothing proceeds until this review is done.

3. **Create the public repository and push.**
   ```bash
   gh repo create quant-allocator --public --source=. --push
   ```

4. **Enable GitHub Pages.** In the new repo: Settings → Pages → Source:
   "GitHub Actions". The `pages.yml` workflow runs on push to `main`.

5. **Verify the workflow.** Confirm the "Deploy gallery to GitHub Pages" run
   succeeds and the published gallery renders (index, `e1.html`, `specs/e1.html`).

6. **Set the gallery URL in the README.** Replace the
   `<!-- set after Pages enablement -->` placeholder and the `USERNAME`
   gallery URL with the real Pages URL, then commit.
