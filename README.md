# agent-kb

**A file-based, agent-maintained knowledge base you run locally.** Clone it, point any coding agent (Claude Code, Codex, Goose, …) at it, and start feeding it things you read, decide, and learn. The agent files each piece into the right place, keeps an index, and remembers across sessions — because the memory *is* the filesystem, not the model's context window.

This is a **scaffold**, not an app. There's no server, no database, no account. It ships empty. What it gives you is a *system*: a proven set of conventions and a handful of small scripts that turn a directory of markdown into a durable, queryable second brain an agent can maintain for years.

> The design follows the "LLM wiki" pattern (Karpathy, 2026): **the human curates sources and directs attention; the agent writes and maintains the wiki.** You don't type into a notes app — you hand the agent a podcast, a thread, a decision, a lab result, and it compiles it into the knowledge graph.

---

## Why this works (the load-bearing ideas)

Most "AI memory" is either a vector store you can't read or a chat log you can't trust. This is neither. Five ideas do the work:

1. **The filesystem is the memory.** State lives in plain markdown and JSON on disk, not in runtime state or a vendor's database. Any agent, any runtime, any editor can read it. It survives model upgrades, tool changes, and companies going out of business. You can `grep` it, `git log` it, and read it with your own eyes.

2. **Two layers: an immutable *raw* quarantine and a compiled *wiki*.** Everything you ingest lands first in `raw/` — **never edited, never trusted, one file per source**. The agent then *compiles* the signal into `wiki/` — the trusted, cross-linked layer you actually read. This separation is what makes the system safe against prompt-injection and bad sources: untrusted input can never masquerade as settled knowledge, because settled knowledge lives somewhere the raw input can't write.

3. **One source fans out to many wiki pages.** The wiki is organized by *topic*, not by source. A single article compiles many raw files; a single ingest updates many articles. The wiki is never a 1:1 mirror of what you fed it — it's the synthesis. (The anti-pattern this kills: dumping everything into one "notes" file. Route each piece to where it belongs.)

4. **Index-first retrieval.** `index.md` is the catalog the agent reads *before* it searches or answers. `log.md` is the append-only audit trail. `state.md` is the one-glance list of open loops. The agent checks these first, so it reuses what it already knows instead of re-deriving it (or hallucinating it).

5. **Idempotent, resumable ingestion.** A tiny **ledger** (`scripts/ledger.py`) records what's already been processed by ID, so re-running an ingest is safe and cheap — it processes only the new items. No double-writes, no "did I already do this?"

Plus two operational choices that make it survivable long-term:
- **Runtime-portable.** `AGENTS.md` is the canonical instruction file (read by most agent runtimes). `CLAUDE.md` is a thin overlay. Nothing important is locked to one vendor.
- **Concurrency-safe via git worktrees.** Multiple agent sessions never write the same tree at once; each works in its own worktree and *lands* to `main` with a fast-forward-only merge (see the `land` skill). `log.md` uses `merge=union` so it never conflicts.

And the point of all of it:

6. **It protects you from yourself.** The highest-value thing a second brain does isn't recall — it's **intervention**. A KB that has watched you over time learns your recurring patterns, including your failure modes, and pushes back when you're about to act against your own interest: quit the thing you'd regret quitting, bail under stress, abandon a plan the moment it gets uncomfortable. When you signal one of your patterns, the agent is meant to *name it, cite your own track record, and be direct* — then let you decide with the long view in front of you. Filing is the visible half; this is why it's worth keeping. (See `AGENTS.md` → "The KB as a protector.")

If you believe the near future is **persistent agents that act as long-lived coworkers**, the hard part isn't the model — it's the memory substrate the agent reads and writes. This repo is a working version of that substrate, small enough to understand in an afternoon.

---

## Layout

```
agent-kb/
├── AGENTS.md          ← canonical operating manual for the agent (start here)
├── CLAUDE.md          ← thin Claude-Code overlay → defers to AGENTS.md
├── CONVENTIONS.md     ← naming, routing, and the ingest/query/lint operations
├── index.md           ← catalog of every source + wiki page, with tags (read first)
├── log.md             ← append-only chronological record of every change
├── state.md           ← one-glance list of open loops / what's live right now
├── goals.md           ← what you're working toward (so ingestion has a purpose)
├── memory/
│   ├── MEMORY.md      ← the memory index, loaded every session (one line per fact)
│   └── *.md           ← one durable fact per file (frontmatter: type + description)
├── raw/               ← IMMUTABLE source layer — the agent reads, never edits
│   ├── sources/       ← one folder per author: "Name - @handle/"
│   └── _index/        ← the processed-ledger + generated entity index
├── wiki/              ← COMPILED knowledge layer — the agent writes and maintains
│   └── <domain>/      ← organized by life-area/topic, not by source
├── scripts/
│   ├── ledger.py           ← idempotent processed-set (filter / add / allseen / count)
│   ├── build-entity-index.py  ← index every source by author/entity across raw/
│   ├── whois.py            ← "do we have <entity>, and how much?" — instant lookup
│   └── build-wiki-html.py  ← render the whole wiki to a single browsable HTML file
└── .agents/skills/    ← portable, runtime-agnostic skills
    ├── ingest/        ← fetch an external source → triage → route → ledger
    └── land/          ← merge a worktree onto main, conflict-free
```

## Quickstart

```bash
git clone <your-fork> my-kb && cd my-kb
# open the folder with your agent of choice, e.g.:
claude          # or: codex, goose, etc.
```

Then, to the agent:

> "Read AGENTS.md. Here's a podcast I want to remember: <url>. Ingest it."

The agent will fetch it, save the raw transcript under `raw/sources/`, compile the signal into a `wiki/` page, update `index.md` and `log.md`, and commit. Next session, ask it *"what do we know about X?"* — it reads `index.md` first and answers from what it filed.

**Make it yours:** edit `goals.md` (what is this KB *for*?), rename `wiki/example-domain/` to your real domains, and delete the example files. The scaffold is deliberately empty of content — the value is the machine, not the data.

### The scripts

```bash
python3 scripts/build-entity-index.py     # (re)build the entity index across raw/
python3 scripts/whois.py <entity>         # how much do we have on <entity>?
python3 scripts/ledger.py count           # how many sources processed
python3 scripts/build-wiki-html.py        # render wiki/ → wiki.html
```

None of them need network access or dependencies beyond the Python standard library.

---

## Design credits & philosophy

Built from a personal knowledge base that an agent has maintained daily for months across trading, health, family, work, and research. This scaffold is the **system extracted from that KB** — the conventions and tooling — with **none of the personal content**. It's the machine, published so others can run their own.

The core belief: *your knowledge, decisions, and taste are portable career capital.* Keep them in files you own, in a format any agent can read, and let the agent do the filing. See `AGENTS.md` for the full operating manual.

MIT licensed. Fork it, gut it, make it yours.
