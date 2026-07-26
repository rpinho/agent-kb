# CLAUDE.md — Claude Code overlay

**Read [`AGENTS.md`](./AGENTS.md) first.** It is the canonical operating manual for this KB. This file only adds Claude-Code-specific notes; everything substantive lives in `AGENTS.md` so the KB stays portable across runtimes.

## Claude-specific notes

- Skills live in `.claude/skills/` as a mirror of the portable `.agents/skills/`. Keep the two byte-identical unless Claude genuinely needs a local overlay.
- When the human says **"land"** / **"merge"** / **"push to main"**, follow the [`land`](.claude/skills/land/SKILL.md) skill exactly — do not run a plain `git merge`/`git push`.
- Commit with explicit pathspecs; avoid `git add -A` so nothing unintended is staged.
- Before answering "what do we know about X?", read `index.md` first (per `AGENTS.md` → Query).

## Optional: worktree-per-session

For concurrency safety (see `AGENTS.md` → Concurrency), run each session in its own git worktree and `land` back to `main`. A minimal helper:

```bash
# start a session worktree
git worktree add ../agent-kb-$(date +%s) -b session-work
# ...work, commit...
# then land (see the land skill), and clean up:
# git worktree remove <dir> && git branch -d <branch>
```
