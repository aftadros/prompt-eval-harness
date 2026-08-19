#!/bin/bash
# One overnight batch of the C1 collection: both prompts over all 50 cases on
# the same served build, then judging, then the comparison. Every step is a
# record the harness writes itself; this script only sequences them and
# refuses to start on top of another collection, which is what produced the
# orphaned duplicate run on 2026-08-18.
#
# Usage: scripts/c1-overnight.sh [N]          (reruns per case, default 5)
# Logs what it did to the day log at the end. Safe to rerun: generation
# writes outputs as they arrive and judging skips rows already present, but
# a rerun of `harness run` is a NEW record, so resume judging by hand
# (`harness judge <run>`) rather than rerunning this whole script.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO/.venv/bin/python"
N="${1:-5}"
CONC="${C1_CONCURRENCY:-6}"
JCONC="${C1_JUDGE_CONCURRENCY:-3}"
# Smoke-test hooks only: e.g. C1_RUN_EXTRA="--case ord-streaming-cost" C1_JUDGE_EXTRA="--samples 1"
RUN_EXTRA="${C1_RUN_EXTRA:-}"
JUDGE_EXTRA="${C1_JUDGE_EXTRA:-}"
cd "$REPO" || exit 1

stamp() { date '+%Y-%m-%d %H:%M:%S'; }
say() { echo "[$(stamp)] $*"; }
T="$(mktemp -d "${TMPDIR:-/tmp}/peh-c1.XXXXXX")"
trap 'rm -r "$T"' EXIT

if pgrep -f "harness (run|judge)" >/dev/null; then
  say "refusing to start: another harness run/judge process is alive:"
  pgrep -fl "harness (run|judge)"
  exit 3
fi

record_of() { sed -n 's/^record: //p' "$1" | tail -1; }

say "arm B: prompts/v2.txt, n=$N, concurrency=$CONC"
"$PY" -m harness run --prompt prompts/v2.txt --n "$N" --concurrency "$CONC" $RUN_EXTRA > $T/armB 2>&1
rcB=$?; cat $T/armB; RUN_B="$(record_of $T/armB)"
[ $rcB -eq 0 ] && [ -n "$RUN_B" ] || { say "arm B failed (rc=$rcB); stopping"; exit 1; }

say "arm A: prompts/v1.txt, n=$N, concurrency=$CONC"
"$PY" -m harness run --prompt prompts/v1.txt --n "$N" --concurrency "$CONC" $RUN_EXTRA > $T/armA 2>&1
rcA=$?; cat $T/armA; RUN_A="$(record_of $T/armA)"
[ $rcA -eq 0 ] && [ -n "$RUN_A" ] || { say "arm A failed (rc=$rcA); arm B is at $RUN_B; stopping"; exit 1; }

say "judging both arms concurrently, $JCONC items in flight per arm (6 on the server, the measured knee)"
"$PY" -m harness judge "$RUN_A" --concurrency "$JCONC" $JUDGE_EXTRA > $T/judgeA 2>&1 &
pa=$!
"$PY" -m harness judge "$RUN_B" --concurrency "$JCONC" $JUDGE_EXTRA > $T/judgeB 2>&1 &
pb=$!
wait $pa; rja=$?; wait $pb; rjb=$?
tail -3 $T/judgeA $T/judgeB
say "judge exit codes: A=$rja B=$rjb (judging is resumable: harness judge <run>)"

say "compare $RUN_A -> $RUN_B"
"$PY" -m harness compare "$RUN_A" "$RUN_B" > $T/cmp 2>&1
rcC=$?; CMP="$(record_of $T/cmp)"
tail -60 $T/cmp
say "done: A=$RUN_A B=$RUN_B cmp=$CMP (rc=$rcC)"

NC="$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1]+'/manifest.json'))['n_cases'])" "$RUN_A" 2>/dev/null || echo '?')"
MODEL="$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1]+'/manifest.json'))['model']['server_reported'])" "$RUN_A" 2>/dev/null || echo '?')"
line="- [$(date '+%H:%M')] prompt-eval-harness C1 overnight batch finished: both prompts over $NC case(s) at n=$N on $MODEL, judged, compared. Records: $RUN_A (v1), $RUN_B (v2), $CMP; judge rc A=$rja B=$rjb, compare rc=$rcC. Not committed; read the report before committing | share:ask src:launchd:peh-c1-overnight"
printf '%s\n' "$line" | "$HOME/bin/day-evidence.py" --stdin || say "day-log append failed; line was: $line"
