# AGENT_LOOP_PLAN_R3.md

## Objective
Close the CPU-category reliability gap where suite runs report:
- `encoding_ffmpeg_fallback_failed`

…even when a manual ffmpeg encode command succeeds in an interactive shell.

This round focuses on **deterministic CPU encode behavior across shells/environments** and on adding acceptance tests that:
1. Reproduce the current failure mode in a controlled way.
2. Verify the fix eliminates the false-negative failure.

---

## Problem statement (R3 scope)
Observed behavior:
- CPU baseline/compression complete.
- Encoding path fails with note `encoding_ffmpeg_fallback_failed` (sometimes with empty or low-signal stderr tail).
- Running ffmpeg manually often succeeds.

Likely class of issue:
- **Execution-context drift** between interactive shell and non-interactive benchmark runner (PATH, env, timeout wrapper, stdin/tty behavior, binary selection).
- Plus insufficient diagnostics to distinguish:
  - true codec failure,
  - timeout kill,
  - wrong binary/feature set,
  - wrapper/tooling mismatch.

---

## Design principles for remediation
1. **Deterministic command construction**
   - One canonical ffmpeg command string used by both primary run and diagnostics replay.
2. **Deterministic environment**
   - Stable locale + minimal explicit env (`LC_ALL=C`, fixed PATH policy, explicit `FFMPEG_BIN` override support).
3. **Deterministic failure classification**
   - Convert opaque “fallback failed” into structured reason codes.
4. **Fast-fail capability probe**
   - Verify selected ffmpeg supports required source/filter/codec before timed run.
5. **Actionable artifacts**
   - Persist exact command, resolved binary path/version, wrapper used, exit code, stderr tail, and reason.

---

## Ordered remediation plan

### R3-1 (P0): Normalize ffmpeg execution context
**Goal:** Ensure benchmark runner uses a predictable ffmpeg binary and env, matching manual reproducibility.

Implementation actions:
1. Resolve ffmpeg using strict precedence:
   - `CPU_FFMPEG_BIN` → `FFMPEG_BIN` → absolute path from `command -v ffmpeg`.
2. Require executable existence; emit explicit note if invalid override.
3. Run encoding with explicit env normalization:
   - `LC_ALL=C LANG=C`
   - explicit PATH snapshot recorded in diagnostics.
4. Keep `-nostdin` (non-interactive safety) but record this in command metadata.

Acceptance signal:
- Re-running same command from diagnostics in a clean shell reproduces benchmark result deterministically.

---

### R3-2 (P0): Add pre-encode capability probe + structured reason codes
**Goal:** Separate “cannot encode here” from “run wrapper/context issue”.

Implementation actions:
1. Before timed encode, execute a short probe (`-t 1`) for:
   - lavfi `testsrc` ingest,
   - primary codec (`libx264`) and fallback codec (`mpeg4`).
2. Map probe/encode exits to reason codes, e.g.:
   - `ffmpeg_missing`
   - `ffmpeg_bin_invalid`
   - `ffmpeg_probe_libx264_failed`
   - `ffmpeg_probe_mpeg4_failed`
   - `ffmpeg_timeout`
   - `ffmpeg_exit_<code>`
   - `ffmpeg_no_stderr`
3. Update notes to include these codes (retain backward-compatible prefix if needed).

Acceptance signal:
- No more low-information `encoding_ffmpeg_fallback_failed` without a reason.

---

### R3-3 (P0): Make timeout behavior explicit and shell-stable
**Goal:** Prevent timeout-wrapper differences from causing false negatives.

Implementation actions:
1. Use one wrapper function for all encode attempts.
2. Detect and record wrapper mode (`timeout --foreground` vs no-timeout fallback).
3. When timeout is unavailable, enforce deterministic no-wrapper path and note `timeout_wrapper=none`.
4. Distinguish timeout exits (`124`, `137`) from codec/runtime exits in status/notes.

Acceptance signal:
- Timeout-induced failures are labeled timeout-specific, not generic fallback failure.

---

### R3-4 (P1): Add deterministic regression tests for reproduce-and-clear
**Goal:** Lock in behavior and prevent recurrence.

Implementation actions:
1. Add a CPU encode reliability test script (e.g., `scripts/tests/test_cpu_encode_reliability.sh`) that runs only CPU with short durations.
2. Include both negative and positive scenarios below.

---

## Acceptance tests (must reproduce then clear)

### A. Reproduce current failure mode (controlled)
Use an intentionally bad ffmpeg override to force deterministic failure classification.

```bash
cd /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool

CPU_DURATION=2 CPU_COMPRESS_DURATION=2 CPU_ENCODE_DURATION=2 \
CPU_FFMPEG_BIN=/nonexistent/ffmpeg \
./run_suite.sh quick cpu --skip-preflight || true

LATEST="$(ls -td reports/run-* | head -n1)"
jq '.subtests.encoding, .diagnostics.ffmpeg, .notes' "$LATEST/raw/cpu.json"
```

Expected (pre-fix baseline may be generic):
- Encoding is `failed`.
- After remediation, notes/diagnostics explicitly classify invalid binary (not ambiguous fallback text).

### B. Reproduce shell/env drift scenario
Run with a constrained PATH that can differ from interactive shell resolution.

```bash
cd /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool

env -i HOME="$HOME" PATH="/usr/bin:/bin" LC_ALL=C LANG=C \
CPU_DURATION=2 CPU_COMPRESS_DURATION=2 CPU_ENCODE_DURATION=2 \
./run_suite.sh quick cpu --skip-preflight || true

LATEST="$(ls -td reports/run-* | head -n1)"
jq '.subtests.encoding, .diagnostics.ffmpeg.path, .diagnostics.ffmpeg.version, .diagnostics.ffmpeg.error_reason, .notes' "$LATEST/raw/cpu.json"
```

Expected:
- Deterministic ffmpeg path/version captured.
- Failure (if any) is reason-coded and reproducible via logged command.

### C. Clear failure with explicit known-good ffmpeg
Use resolved absolute ffmpeg path from interactive shell and verify CPU no longer fails encode on healthy systems.

```bash
cd /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool
GOOD_FFMPEG="$(command -v ffmpeg)"

CPU_DURATION=2 CPU_COMPRESS_DURATION=2 CPU_ENCODE_DURATION=2 \
CPU_FFMPEG_BIN="$GOOD_FFMPEG" \
./run_suite.sh quick cpu --skip-preflight

LATEST="$(ls -td reports/run-* | head -n1)"
jq '.status, .subtests.encoding, .diagnostics.ffmpeg, .notes' "$LATEST/raw/cpu.json"
```

Pass criteria:
- `subtests.encoding.status` is `ok` or approved `degraded` fallback.
- CPU category overall is not `failed` due to ambiguous ffmpeg fallback failure.
- Notes do **not** contain legacy ambiguous `encoding_ffmpeg_fallback_failed` without reason code.

### D. Determinism check across shells
Run the same CPU command from two contexts and compare ffmpeg diagnostics.

```bash
cd /home/openclaw/.openclaw/workspace/project-linux-benchmark-tool
GOOD_FFMPEG="$(command -v ffmpeg)"

CPU_DURATION=2 CPU_COMPRESS_DURATION=2 CPU_ENCODE_DURATION=2 \
CPU_FFMPEG_BIN="$GOOD_FFMPEG" ./run_suite.sh quick cpu --skip-preflight
R1="$(ls -td reports/run-* | head -n1)"

env -i HOME="$HOME" PATH="/usr/bin:/bin" LC_ALL=C LANG=C \
CPU_DURATION=2 CPU_COMPRESS_DURATION=2 CPU_ENCODE_DURATION=2 \
CPU_FFMPEG_BIN="$GOOD_FFMPEG" ./run_suite.sh quick cpu --skip-preflight
R2="$(ls -td reports/run-* | head -n1)"

jq '.diagnostics.ffmpeg | {path,version,timeout_wrapper,error_reason}' "$R1/raw/cpu.json"
jq '.diagnostics.ffmpeg | {path,version,timeout_wrapper,error_reason}' "$R2/raw/cpu.json"
```

Pass criteria:
- Same ffmpeg path/version and consistent reason/status behavior across both contexts.

---

## Validator rerun focus (R3)
After implementing R3-1..R3-4, rerun:
1. `./run_suite.sh quick cpu --skip-preflight`
2. `./run_suite.sh balanced cpu --skip-preflight`
3. Determinism pair from Acceptance D.

Required outcome:
- CPU no longer fails with ambiguous `encoding_ffmpeg_fallback_failed` when ffmpeg is healthy.
- Any encode failure is explicitly classified and reproducible from diagnostics.

---

## Definition of done
- CPU encode path is deterministic across interactive/non-interactive shells.
- Diagnostics are sufficient to replay the exact failing command.
- Acceptance A/B reproduce controlled failures with explicit reason codes.
- Acceptance C/D demonstrate failure cleared under known-good ffmpeg and stable cross-shell behavior.
