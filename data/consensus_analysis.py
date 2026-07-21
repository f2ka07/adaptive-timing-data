#!/usr/bin/env python3
import re, sys, csv, argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

def compile_vote_re(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)

DEFAULT_VOTE_PATTERN = r"(?:vote_id=|vote\s+|Vote\s+)([A-Z]\d+_\d+_\d+)|\b([A-Z]\d+_\d+_\d+)\b"

ROUND_RE   = re.compile(r"Round\s+(\d+)/(\d+)", re.IGNORECASE)
PORT_RE    = re.compile(r"(COM\d+)", re.IGNORECASE)
BFT_RE     = re.compile(r"BFT\s+threshold\s+reached.*?at\s+(\d+)\s*ms", re.IGNORECASE)
FINAL4_RE  = re.compile(r"PERFECT_4_4.*?finalized\s+in\s+(\d+)\s*ms", re.IGNORECASE)
SUCCESS_RE = re.compile(r"Round\s+\d+\s+SUCCESS|BFT\s+SUCCESS", re.IGNORECASE)
TIMEOUT_RE = re.compile(r"CONSENSUS_TIMEOUT|outcome=TIMEOUT", re.IGNORECASE)
PARTIC_RE  = re.compile(r"participants?:\s*([A-Z0-9,]+)|participants=([A-Z0-9,]+)", re.IGNORECASE)
SLOTINT_RE = re.compile(r"slot_interval=([0-9]+)")

WIFI_RE    = re.compile(r"\bWiFi\b|\bUDP\b", re.IGNORECASE)
DEATH_RE   = re.compile(r"CONSENSUS_DEATH_FIX", re.IGNORECASE)
FCLN_RE    = re.compile(r"FORCE_CLEANUP", re.IGNORECASE)
ONTIME_RE  = re.compile(r"on_time=true", re.IGNORECASE)

def parse_file(path: Path, vote_re: re.Pattern, debug: bool=False) -> List[Dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    rows: Dict[str, Dict[str, Any]] = {}

    round_idx = round_planned = None
    wifi = death = fcln = ontime = 0
    port = None
    mfp = PORT_RE.search(path.name)
    if mfp: port = mfp.group(1).upper()

    for ln in text.splitlines():
        if not port:
            mp = PORT_RE.search(ln)
            if mp: port = mp.group(1).upper()

        r = ROUND_RE.search(ln)
        if r:
            round_idx, round_planned = int(r.group(1)), int(r.group(2))

        if WIFI_RE.search(ln):  wifi += 1
        if DEATH_RE.search(ln): death += 1
        if FCLN_RE.search(ln):  fcln += 1
        if ONTIME_RE.search(ln): ontime += 1

        m = vote_re.search(ln)
        vid = None
        if m:
            vid = m.group(1) or m.group(2)

        if not vid:
            continue

        rec = rows.setdefault(vid, {
            "file": path.name,
            "port": port,
            "round_idx": round_idx,
            "round_planned": round_planned,
            "vote_id": vid,
            "leader": None,
            "bft_time_ms": None,
            "finalized_4of4_ms": None,
            "consensus_latency_ms": None,
            "timeout": 0,
            "success": 0,
            "participants": None,
            "slot_interval_ms": None,
        })

        if rec["leader"] is None:
            l = re.search(r"([A-Z]\d+)\s+will initiate vote|Starting vote:\s*([A-Z]\d+)", ln, re.IGNORECASE)
            if l:
                rec["leader"] = (l.group(1) or l.group(2))

        bft = BFT_RE.search(ln)
        if bft:
            rec["bft_time_ms"] = int(bft.group(1))
            if rec["consensus_latency_ms"] is None:
                rec["consensus_latency_ms"] = rec["bft_time_ms"]

        f4 = FINAL4_RE.search(ln)
        if f4:
            rec["finalized_4of4_ms"] = int(f4.group(1))
            if rec["consensus_latency_ms"] is None:
                rec["consensus_latency_ms"] = rec["finalized_4of4_ms"]

        if SUCCESS_RE.search(ln): rec["success"] = 1
        if TIMEOUT_RE.search(ln): rec["timeout"] = 1

        part = PARTIC_RE.search(ln)
        if part:
            p = part.group(1) or part.group(2)
            if p: rec["participants"] = p.strip(",")

        si = SLOTINT_RE.search(ln)
        if si:
            rec["slot_interval_ms"] = int(si.group(1))

    # Attach file level counters (context)
    for rec in rows.values():
        rec["wifi_events"] = wifi
        rec["death_fix_count"] = death
        rec["force_cleanup_count"] = fcln
        rec["on_time_tx_count"] = ontime

    if debug and not rows:
        # Print first 30 lines to help regex tuning
        print(f"[DEBUG] No vote ids found in {path}. First 30 lines:")
        for l in text.splitlines()[:30]:
            print(l)

    return list(rows.values())

def iter_files(root: Path, exts: List[str]) -> List[Path]:
    out = []
    for ext in exts:
        out.extend(root.rglob(f"*{ext}"))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs_dir")
    ap.add_argument("out_csv")
    ap.add_argument("--ext", default=".log,.txt,.LOG,.TXT", help="comma-separated extensions")
    ap.add_argument("--vote-pattern", default=DEFAULT_VOTE_PATTERN, help="regex to capture vote_id")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    root = Path(args.logs_dir)
    out_csv = Path(args.out_csv)
    exts = [e.strip() for e in args.ext.split(",") if e.strip()]
    vote_re = compile_vote_re(args.vote_pattern)

    files = iter_files(root, exts)
    if args.debug:
        print(f"[DEBUG] Found {len(files)} files matching {exts}")
        for p in files[:10]:
            print(f"[DEBUG] {p}")

    all_rows: List[Dict[str, Any]] = []
    for p in files:
        rows = parse_file(p, vote_re, debug=args.debug)
        all_rows.extend(rows)

    if not all_rows:
        print("No rows parsed.")
        sys.exit(2)

    headers = sorted({k for r in all_rows for k in r.keys()})
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in all_rows:
            w.writerow(r)
    print(f"Wrote {len(all_rows)} rows to {out_csv}")

if __name__ == "__main__":
    main()
