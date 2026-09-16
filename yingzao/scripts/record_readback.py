#!/usr/bin/env python3
"""Record explicit Agent visual observations; this script does not inspect aesthetics."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from _runtime import ensure_runtime
from _integrity import sha256

ensure_runtime(('PIL',))
from PIL import Image

DOMAINS = ('subject', 'background', 'glyphs', 'interaction', 'reference')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, help='bind this readback to a generation manifest')
    args = parser.parse_args()
    inputs = [args.image, args.observations] + ([args.manifest] if args.manifest else [])
    try:
        if args.output.resolve() in {path.resolve() for path in inputs}:
            raise ValueError('output must not overwrite an input')
        with Image.open(args.image) as image:
            image.verify()
        observations = json.loads(args.observations.read_text(encoding='utf-8'))
        domains = list(DOMAINS)
        manifest = None
        if args.manifest:
            manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
            if not isinstance(manifest, dict) or not manifest.get('call_signature'):
                raise ValueError('manifest must contain a call_signature')
            if manifest.get('series'):
                domains.append('series')
        if not isinstance(observations, dict) or set(observations) != set(domains):
            raise ValueError('observations must contain exactly: ' + ', '.join(domains))
        for domain in domains:
            item = observations[domain]
            if (not isinstance(item, dict) or item.get('status') not in ('pass', 'issue', 'uncertain')
                    or not isinstance(item.get('evidence'), str) or not item['evidence'].strip()):
                raise ValueError(f'{domain} needs status=pass|issue|uncertain and nonempty evidence')
        lines = ['# Visual readback', '',
                 'Agent-authored observations after opening the image; not an automated visual verdict.',
                 'Recording this report does not authorize regeneration.', '',
                 f'Image: {args.image.resolve()}', f'Image SHA-256: {sha256(args.image)}']
        if args.manifest:
            lines.extend([f'Manifest SHA-256: {sha256(args.manifest)}',
                          f'Call signature: {manifest["call_signature"]}'])
        for domain in domains:
            item = observations[domain]
            lines.extend(['', f'## {domain}: {item["status"]}', '', item['evidence'].strip()])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    print(f'Recorded observations: {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
