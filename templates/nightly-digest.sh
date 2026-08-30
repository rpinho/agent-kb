#!/bin/bash
# Scheduled agent run -> digest -> guaranteed delivery.
#
# A SKELETON, not a drop-in. The value here is the control flow; the prompt body is yours to write.
# Everything the agent should actually DO lives in the heredoc marked YOUR SPEC BELOW.
#
# Flow: throwaway worktree -> headless agent run -> commit -> deliver -> land -> clean up.
# The worktree matters: an unattended agent writing into your live checkout is how you lose work.
#
# ⚠️ This runs the CLI with --dangerously-skip-permissions. That is a real trade-off, accepted
#    because it is unattended and confined to a throwaway worktree. Know what you are agreeing to.

set -uo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

KB="${KB_ROOT:-$HOME/kb}"
DAY="$(date '+%Y-%m-%d')"
BR="nightly-$(date '+%Y%m%d')"
WT="$HOME/.worktrees/kb/$BR"
LOG="$KB/outbox/.nightly.log"
RECIPIENT="${DIGEST_RECIPIENT:?set DIGEST_RECIPIENT}"   # never hardcode an address here

log(){ printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }

# --- Idempotence: never run twice for the same day -----------------------------------------
if git -C "$KB" show-ref --quiet "refs/heads/$BR"; then
  log "branch $BR exists; already ran today"; exit 0
fi
git -C "$KB" worktree add "$WT" -b "$BR" >>"$LOG" 2>&1 || { log "worktree failed"; exit 1; }

# --- Model + effort pinned BEFORE the auth probe -------------------------------------------
# Declare these first so the probe runs on the SAME code path as the real invocation. A probe
# with different flags manufactures false diagnoses — that cost three mornings before it was found.
NIGHTLY_MODEL="${NIGHTLY_MODEL:-<your-model-id>}"
NIGHTLY_EFFORT="${NIGHTLY_EFFORT:-high}"

# --- Auth probe: capture the ERROR, never just the exit code -------------------------------
# The original probe treated ANY non-zero exit as "credentials unavailable". A transient API 500
# and a rate limit both reported the same wrong cause. Capture stderr and log it.
PROBE_OK=""; PROBE_ERR=""
if PROBE_ERR="$(command claude -p "Reply with exactly: OK" \
      --model "$NIGHTLY_MODEL" --dangerously-skip-permissions 2>&1 >/dev/null)"; then
  PROBE_OK=yes
else
  log "probe failed: ${PROBE_ERR:0:400}"
fi
[ -n "$PROBE_OK" ] || { log "aborting: auth probe failed"; exit 1; }

DELIVERY_STEP="8. DELIVERY: write the digest to outbox/, then stop. The wrapper delivers it."

# --- Prompt: QUOTED heredoc ----------------------------------------------------------------
# 'EOF' quoted means backticks, $ and apostrophes are literal. An UNquoted heredoc (or a
# double-quoted string) will execute backticks inside your prompt and kill the script before it
# writes anything — exit 127, no digest, no error you would recognise. `bash -n` does NOT catch it.
# Interpolate ONLY through explicit @@PLACEHOLDER@@ substitution below.
read -r -d '' PROMPT <<'NIGHTLY_PROMPT_EOF' || true
You are running unattended. Work in THIS worktree. Commit here; do not push.

⭐ THE ORDER BELOW IS A PRIORITY ORDER, NOT A CHECKLIST. If you run low on room, skip ahead to the
delivery checkpoint immediately. A digest with fewer sections is a SUCCESS. An exhaustive run that
produces no digest is a FAILURE. This framing exists because a run once did excellent work for hours
and exhausted itself one step before delivering anything.

1. <ingest / gather — YOUR SPEC BELOW>
2. <route + update your index/log/state; commit with explicit paths, never `git add -A`>

3. ⏰ DEADLINE SWEEP — before writing. Surface dated items due on or before @@DAY@@ **and anything
   due within the next 14 days**, with a COUNTDOWN. A sweep that only looks at today surfaces the
   most important appointment of the year on the morning it happens.

4. 🔁 RECURRING + PINNED ITEMS — read templates/digest-pins.md (one-shot) and templates/digest-daily.md
   (recurring) and honour their rules. They exist because a scheduled run only writes up what IT
   processed; anything ingested interactively has no other route in.

5. ⛔ HARD CHECKPOINT — WRITE THE DIGEST NOW, COMMIT IT, THEN CONTINUE.
   Any remaining work happens AFTER a committed digest exists. This is the minimum acceptable
   outcome of the run.

6. <the digest itself — YOUR SPEC: sections, format, length, tone>
   Keep the format rules with the prompt, not in your head: inline styles if it is an email,
   a fixed section set, and an explicit cap so it cannot grow unbounded.

7. If there is nothing to report: still write and commit a short digest saying so, then deliver.
@@DELIVERY_STEP@@
9. Before finishing: `git status --short` and commit anything you created, by explicit path.
NIGHTLY_PROMPT_EOF

PROMPT="${PROMPT//@@DAY@@/$DAY}"
PROMPT="${PROMPT//@@DELIVERY_STEP@@/$DELIVERY_STEP}"

# Abort loudly if interpolation failed or the prompt collapsed. Silent truncation is the failure
# mode you will not notice until a morning is missing.
if [ ${#PROMPT} -lt 1500 ] || [[ "$PROMPT" == *"@@"* ]]; then
  log "prompt malformed (len=${#PROMPT}); aborting"; exit 1
fi

cd "$WT" || exit 1
command claude -p "$PROMPT" --model "$NIGHTLY_MODEL" --effort "$NIGHTLY_EFFORT" \
        --dangerously-skip-permissions >>"$LOG" 2>&1
log "agent run finished (exit $?)"

# --- GUARANTEED DELIVERY -------------------------------------------------------------------
# The whole point. Every branch below either delivers something, or delivers a notice that it
# could not. Silence is not a permitted outcome.
DIGEST="$WT/outbox/Digest - $DAY.html"

if [ ! -s "$DIGEST" ]; then
  log "no digest from the model; building deterministic fallback"
  "$KB/scripts/digest-fallback.py" --date "$DAY" --out "$DIGEST" >>"$LOG" 2>&1 \
    && git -C "$WT" add "outbox/Digest - $DAY.html" \
    && git -C "$WT" -c commit.gpgsign=false commit -qm "fallback digest $DAY"
fi

if [ -s "$DIGEST" ]; then
  if ! "$KB/scripts/send-digest.py" --date "$DAY" --to "$RECIPIENT" >>"$LOG" 2>&1; then
    log "SEND FAILED — emitting failure notice"
    "$KB/scripts/send-digest.py" --notice "digest built but delivery failed on $DAY" \
        --to "$RECIPIENT" >>"$LOG" 2>&1 || log "failure notice ALSO failed"
  fi
else
  log "NO DIGEST AND NO FALLBACK — emitting failure notice"
  "$KB/scripts/send-digest.py" --notice "no digest produced on $DAY" \
      --to "$RECIPIENT" >>"$LOG" 2>&1 || log "failure notice ALSO failed"
fi

# --- Land + clean up -----------------------------------------------------------------------
git -C "$WT" merge --no-edit main >>"$LOG" 2>&1
git -C "$KB" merge --ff-only "$BR" >>"$LOG" 2>&1 \
  && git -C "$KB" worktree remove "$WT" >>"$LOG" 2>&1 \
  && git -C "$KB" branch -d "$BR" >>"$LOG" 2>&1
log "done"
