#!/usr/bin/env python3
"""
digest-fallback.py — build a Morning Digest with NO model involved.

WHY THIS EXISTS (2026-08-28). The digest is the deliverable, and it had never once
been delivered by the nightly job without a human intervening:
  08-25  keychain unavailable                        -> no email
  08-26  probe misreported the cause                 -> no email
  08-27  probe ran without the real run's flags      -> no email
  08-28  unescaped backticks killed the script (127) -> no digest file at all
  08-28  re-run finished the INGEST but exhausted itself before the digest step
Every fix so far addressed one cause and the next morning found another. This file
stops trying to prevent failure and instead guarantees an OUTPUT: it reads the
triage file and state.md and emits a real digest deterministically. It is ugly
compared to the model-written one; it is never absent.

Usage: digest-fallback.py [--date YYYY-MM-DD] [--out PATH]
"""
import argparse, datetime, html, os, re, sys
from pathlib import Path

KB = Path(os.environ.get("KB_ROOT", Path.home() / "kb"))

def esc(t): return html.escape(t, quote=False)

def md_inline(t):
    t = esc(t)
    t = re.sub(r'\[\[([^\]|]+)\]\]', lambda m: f'<a href="http://localhost:8787/">{m.group(1)}</a>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'\*(.+?)\*', r'<i>\1</i>', t)
    t = re.sub(r'`(.+?)`', r'<code>\1</code>', t)
    return t

def dated_items(day):
    """Today's actionable lines.

    IMPORTANT: state.md is long and full of OLD open items that still carry ⏳/due.
    A naive scan surfaces 2026-06 leftovers instead of this morning's deadlines
    (observed 2026-08-28). So: prefer the items under the MOST RECENT dated
    section header, and only widen the net if that section is empty.
    """
    p = KB / "state.md"
    if not p.exists(): return []
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

    # Find the section with the LATEST date. state.md is newest-FIRST, so the
    # positionally-last header is the OLDEST one (this bit was wrong on 2026-08-28
    # and surfaced the previous day's deadlines). Select by max date, and take the
    # slice up to the next header of the same level.
    heads = []
    for i, l in enumerate(lines):
        m = re.match(r"^##\s+(\d{4}-\d{2}-\d{2})", l.strip())
        if m: heads.append((m.group(1), i))
    scoped = []
    if heads:
        target = max(h for h, _ in heads)
        if day in {h for h, _ in heads}:
            target = day                      # prefer today's own section when present
        start = next(i for h, i in heads if h == target)
        nxt = next((i for _, i in heads if i > start), len(lines))
        scoped = lines[start:nxt]

    def collect(src, require_marker):
        hits, seen = [], set()
        for line in src:
            t = line.strip()
            if not t.startswith("- [ ]"): continue
            body = t[5:].strip()
            if not body or body in seen: continue
            if require_marker and not re.search(r"TODAY|⏳|closes|expires|DEADLINE|⛔|🚨|🩸", body, re.I):
                continue
            seen.add(body); hits.append(body)
        return hits

    out = collect(scoped, require_marker=False)      # everything in today's section
    if not out:
        out = collect(lines, require_marker=True)    # widen only if today's section is empty
    return out[:8]

def triage_summary(day):
    p = KB / "raw" / "_index" / f"triage-{day}.md"
    if not p.exists(): return None, []
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    header = lines[0].lstrip("# ").strip() if lines else ""
    notes = [l.strip() for l in lines[1:12] if l.strip() and not l.startswith("|")]
    return header, notes[:6]

def new_pages(day):
    """Wiki pages created today, from the filesystem (no git needed)."""
    out = []
    for root in ("wiki",):
        for p in (KB / root).rglob("*.md"):
            try:
                if datetime.date.fromtimestamp(p.stat().st_mtime).isoformat() == day and p.stat().st_size > 3000:
                    out.append(p.relative_to(KB).as_posix())
            except OSError:
                pass
    return sorted(out)[:14]

def build(day):
    header, notes = triage_summary(day)
    todo = dated_items(day)
    pages = new_pages(day)
    pretty = datetime.date.fromisoformat(day).strftime("%A %-d %B %Y")

    def section(title, inner, accent="#b0562c"):
        return (f'<tr><td style="padding:20px 26px 0;font-family:Georgia,serif;">'
                f'<div style="font-size:11px;letter-spacing:1.6px;text-transform:uppercase;color:{accent};'
                f'font-weight:bold;border-bottom:2px solid {accent};padding-bottom:5px;">{title}</div>'
                f'<div style="font-size:14px;color:#241f1a;line-height:1.68;padding-top:11px;">{inner}</div>'
                f'</td></tr>')

    parts = []
    parts.append(
        '<tr><td style="padding:22px 26px 6px;font-family:Georgia,serif;">'
        f'<div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#b0562c;font-weight:bold;">{pretty}</div>'
        '<div style="font-size:26px;font-weight:bold;color:#1d1a17;padding-top:5px;">Morning Digest</div>'
        '<div style="font-size:13px;color:#6a635a;padding-top:6px;">'
        '⚠️ Built by the deterministic fallback — the nightly run did not produce a digest. '
        'Content below is real but unsynthesised.</div></td></tr>')

    if todo:
        parts.append(section("Today", "<br><br>".join(md_inline(t) for t in todo)))
    if header:
        parts.append(section("The batch", md_inline(header) +
                     ("<br><br>" + "<br><br>".join(md_inline(n) for n in notes) if notes else "")))
    if pages:
        links = "<br>".join(
            f'<a href="http://localhost:8787/{p.replace(" ", "%20")}" style="color:#b0562c;">{esc(Path(p).stem)}</a>'
            for p in pages)
        parts.append(section("Built overnight", links, "#7a6f62"))

    parts.append(
        '<tr><td style="padding:20px 26px 24px;font-family:Georgia,serif;font-size:12px;color:#8a8178;'
        'border-top:1px solid #eee9e1;">'
        '<a href="http://localhost:8787/" style="color:#8a8178;">Browse KB</a> · '
        '<a href="http://localhost:8787/index.md" style="color:#8a8178;">Index</a> · '
        '<a href="http://localhost:8787/state.md" style="color:#8a8178;">State</a>'
        f'<div style="padding-top:7px;color:#a89f94;">Fallback digest for {day}.</div></td></tr>')

    return ('<html><body style="margin:0;padding:0;background:#f4f2ee;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="background:#f4f2ee;padding:18px 10px;"><tr><td align="center">'
            '<table role="presentation" width="640" cellpadding="0" cellspacing="0" '
            'style="width:640px;max-width:100%;background:#ffffff;border:1px solid #e0dbd2;">'
            + "".join(parts) +
            '</table></td></tr></table></body></html>')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--out")
    a = ap.parse_args()
    out = Path(a.out) if a.out else KB / "outbox" / f"Morning Digest - {a.date}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(a.date), encoding="utf-8")
    print(f"fallback digest written: {out} ({out.stat().st_size:,} bytes)")

if __name__ == "__main__":
    main()
