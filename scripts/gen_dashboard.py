#!/usr/bin/env python3
import json
import sys
import os
from pathlib import Path

if len(sys.argv) != 2:
  print('Usage: gen_dashboard.py &lt;run_dir&gt;')
  sys.exit(1)

run_dir = Path(sys.argv[1])
summary_path = run_dir / 'report' / 'summary.json'
if not summary_path.exists():
  print('No summary.json')
  sys.exit(1)

with open(summary_path) as f:
  data = json.load(f)

# Symlink data.json
os.symlink(summary_path, 'web/data.json')

template = 'web/dashboard.html'
with open(template) as f:
  html = f.read()

print('Dashboard gen\\'d. python -m http.server 8080 --directory web')
