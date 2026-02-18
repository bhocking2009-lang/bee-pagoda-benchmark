#!/usr/bin/env bash
set -euo pipefail

OUT_JSON="$1"
OUT_CSV="$2"

WORKDIR="${STORAGE_WORKDIR:-$PWD}"
TEST_SIZE="${STORAGE_TEST_SIZE:-512M}"
RUNTIME="${STORAGE_RUNTIME:-20}"
FIO_FILE="$WORKDIR/.bench_fio_testfile.bin"

status="ok"
bench="fio_file_safe"
score=""
notes=()

seq_status="skipped"
seq_bw=""
rand_status="skipped"
rand_iops=""

cleanup() {
  rm -f "$FIO_FILE" "$WORKDIR/.fio_seq.json" "$WORKDIR/.fio_rand.json"
}
trap cleanup EXIT

if ! command -v fio >/dev/null 2>&1; then
  status="skipped"
  notes+=("missing_fio")
else
  seq_json="$WORKDIR/.fio_seq.json"
  rand_json="$WORKDIR/.fio_rand.json"

  if fio --name=seqrw --filename="$FIO_FILE" --rw=readwrite --bs=1M --size="$TEST_SIZE" \
      --ioengine=libaio --direct=1 --iodepth=8 --runtime="$RUNTIME" --time_based=1 \
      --output-format=json --output="$seq_json" >/dev/null 2>&1; then
    seq_status="ok"
    seq_bw="$(python3 - <<PY
import json
p='$seq_json'
with open(p) as f:
  d=json.load(f)
j=d['jobs'][0]
rbw=j['read'].get('bw',0)
wbw=j['write'].get('bw',0)
print(max(rbw,wbw))
PY
)"
    notes+=("fio_seq_ok")
  else
    seq_status="failed"
    notes+=("fio_seq_failed")
  fi

  if fio --name=randrw --filename="$FIO_FILE" --rw=randrw --rwmixread=70 --bs=4k --size="$TEST_SIZE" \
      --ioengine=libaio --direct=1 --iodepth=1 --runtime="$RUNTIME" --time_based=1 \
      --output-format=json --output="$rand_json" >/dev/null 2>&1 && \
     fio --name=randrw_qd16 --filename="$FIO_FILE" --rw=randrw --rwmixread=70 --bs=4k --size="$TEST_SIZE" \
      --ioengine=libaio --direct=1 --iodepth=16 --runtime="$RUNTIME" --time_based=1 \
      --output-format=json --output="$rand_json" >/dev/null 2>&1; then
    rand_status="ok"
    rand_iops="$(python3 - <<PY
import json
p='$rand_json'
with open(p) as f:
  d=json.load(f)
j=d['jobs'][0]
ri=j['read'].get('iops',0)
wi=j['write'].get('iops',0)
print(max(ri,wi))
PY
)"
    notes+=("fio_rand_ok_qd1_qd16")
  else
    rand_status="failed"
    notes+=("fio_rand_failed")
  fi
fi

if [[ "$seq_status" == "failed" || "$rand_status" == "failed" ]]; then
  status="failed"
elif [[ "$seq_status" == "ok" && "$rand_status" == "skipped" ]]; then
  status="degraded"
elif [[ "$seq_status" == "skipped" && "$rand_status" == "skipped" ]]; then
  status="skipped"
fi

score="$seq_bw"
notes+=("safe_file=$FIO_FILE")
notes+=("test_size=$TEST_SIZE")
notes+=("runtime=$RUNTIME")
notes_str="$(IFS=';'; echo "${notes[*]}")"

cat > "$OUT_JSON" <<EOF
{
  "category": "disk",
  "status": "$status",
  "benchmark": "$bench",
  "primary_metric": "seq_bw_kib_per_sec",
  "score": "${score}",
  "subtests": {
    "fio_seq": {
      "status": "$seq_status",
      "bw_kib_per_sec": "${seq_bw}",
      "size": "$TEST_SIZE",
      "runtime_sec": "$RUNTIME"
    },
    "fio_rand4k": {
      "status": "$rand_status",
      "iops": "${rand_iops}",
      "queue_depths": "1,16"
    }
  },
  "notes": "$notes_str"
}
EOF

printf "category,status,benchmark,primary_metric,score,notes\n" > "$OUT_CSV"
printf "disk,%s,%s,seq_bw_kib_per_sec,%s,%s\n" "$status" "$bench" "${score}" "${notes_str//,/;}" >> "$OUT_CSV"
