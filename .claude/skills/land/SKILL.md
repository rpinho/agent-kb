---
name: land
description: Merge a session's git worktree onto main safely, so main never halts on a conflict. Resolve additive-tracker conflicts in the worktree, then fast-forward main.
---

# land — merge a worktree onto main, conflict-free

Run each agent session in its own git worktree (see `AGENTS.md` → Concurrency). When the human says **"land" / "merge" / "push to main"**, do exactly this from inside the worktree — never a plain `git merge`/`git push` onto main.

1. **Confirm you're in a worktree, not main.**
   ```bash
   git rev-parse --abbrev-ref HEAD    # should be your session branch, not "main"
   ```
   If it's `main`, stop — there's nothing to land.

2. **Pull main into the worktree** and resolve conflicts *here* (you have write access to your own worktree):
   ```bash
   git merge --no-edit main
   ```
   - `index.md` and `state.md` are **additive trackers** — on conflict, **keep BOTH sides'** content (merge the entries; never drop one side's edits).
   - `log.md` is set to `merge=union` in `.gitattributes`, so it auto-merges; if it ever conflicts, keep both.
   - For wiki/raw files, keep both sides unless it's genuinely the same edit.
   - Stage resolved files by **explicit path** (never `git add -A`) and commit the merge.

3. **Fast-forward main** (this is the only write to main, and it can't conflict):
   ```bash
   git -C <path-to-main-worktree> merge --ff-only <your-branch>
   ```
   If git refuses (main advanced again), re-run from step 2.

4. **Report success** and print the cleanup line:
   ```bash
   git -C <path-to-main-worktree> worktree remove <this-worktree-dir> && \
   git -C <path-to-main-worktree> branch -d <your-branch>
   ```

**Never** `git push`, **never** check out `main` in this worktree, **never** `git add -A`.

## Why this shape

`main` only ever *fast-forwards*, so a shared `main` never stops on a merge conflict — all conflict resolution happens inside the disposable session worktree. Combined with `log.md`'s union merge and the "keep both" rule for additive trackers, concurrent sessions can't clobber each other.
