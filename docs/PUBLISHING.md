# Publishing runbook (updates only; manual and last)

The public repository and GitHub Pages site already exist. Do not recreate the
repository or repeat first-publication setup. Every update remains deliberate and
human-gated.

1. **Confirm authority.** Merge, push, and publication each require explicit user
   approval and a corresponding `true` flag in `.harness/current.yaml`. One approval
   does not imply the others.

2. **Populate local sensitive terms.** Ensure `tools/.publication_terms` exists in the
   checkout used for the release scan. It is gitignored and must never be committed.

3. **Run the release verification named by the active plan.** Use a fresh static build,
   targeted/full site tests appropriate to the change, output-integrity checks, and
   rendered desktop/mobile QA. A passing build alone is not publication evidence.

4. **Run and adjudicate the publication scan.**

   ```bash
   bash tools/publication_check.sh
   ```

   The scanner is report-only. Review every working-tree and reachable-history hit.
   No current-tree match is accepted by default; every such match blocks release.
   Already-public history is accepted only for exact pairs in
   `tools/publication_history_grandfather.yaml`.

5. **Push only the reviewed commit authorized for release.** Do not rewrite published
   `main` history. If a local branch contains a literal-bearing historical commit, use
   the repository's planned clean-tree integration procedure rather than pushing that
   history.

6. **Verify the existing GitHub Pages workflow.** Confirm the deployment workflow
   succeeds, then inspect the live homepage, one changed article, one changed exhibit,
   mobile rendering, formulas, links, and the primary changed interaction.

7. **Record merge and deployment separately.** A merged commit is not proof that the
   live site has deployed or passed rendered validation.
