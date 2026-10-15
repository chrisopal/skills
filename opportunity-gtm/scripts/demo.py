#!/usr/bin/env python3
"""Seed the maintained public-research/fictional-interaction example through CLI."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, help='Isolated project database, never a production ledger')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    command = [sys.executable, str(root / 'opportunity-orchestrator/scripts/run.py'), 'gtm-manage', '--db', args.db, '--input', str(Path(__file__).resolve().parents[1] / 'examples/industrial-vision-input.json')]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode:
        print(completed.stderr, file=sys.stderr)
        raise SystemExit(completed.returncode)
    result = json.loads(completed.stdout)
    print(json.dumps({'campaign_id': result['campaign_id'], 'revision': result['revision'], 'targets': len(result['detail']['targets']), 'events': len(result['detail']['events']), 'simulation': result['detail']['campaign']['simulation']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
