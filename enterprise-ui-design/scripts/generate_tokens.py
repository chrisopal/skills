#!/usr/bin/env python3
"""Emit scoped token CSS from the Skill's canonical JSON. Standard library only."""
import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def render(tokens):
    def rule(selector, values):
        declarations = '\n'.join(f'  --ui-{key}: {value};' for key, value in values.items())
        return f'{selector} {{\n{declarations}\n}}'

    parts = [
        f'/* Enterprise Workbench UI {tokens["meta"]["version"]}. Token-only: no resets or component overrides.\n'
        '   Generated from tokens.json by scripts/generate_tokens.py; do not edit by hand.\n'
        '   Profile cascade: enterprise base -> theme -> optional profile -> density.\n'
        '   Unsupported profile/theme combinations inherit the declared profile fallback.\n'
        '   Root-scoped tokens inherit into body portals; nested providers must transfer resolved variables. */',
        rule('html[data-ui="enterprise"]', tokens['common'] | tokens['modes']['light']),
        rule('html[data-ui="enterprise"][data-theme="dark"],\nhtml.dark[data-ui="enterprise"]:not([data-theme="light"])',
             tokens['modes']['dark']),
    ]
    for name, profile in tokens.get('profiles', {}).items():
        for theme, values in profile.get('modes', {}).items():
            if name == 'enterprise':
                parts.append(rule(
                    f'html[data-ui="enterprise"][data-theme="{theme}"],\n'
                    f'html.{theme}[data-ui="enterprise"]:not([data-theme="light"])', values))
                continue
            selectors = (
                f'html[data-ui="enterprise"][data-ui-profile="{name}"][data-theme="{theme}"],\n'
                f'html.{theme}[data-ui="enterprise"][data-ui-profile="{name}"]:not([data-theme="light"])'
            )
            parts.append(rule(selectors, values))
    for name, values in tokens.get('densities', {}).items():
        if values:
            parts.append(rule(f'html[data-ui="enterprise"][data-density="{name}"]', values))
    return '\n\n'.join(parts) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokens', type=Path, default=ROOT / 'assets/tokens.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'assets/tokens.css')
    parser.add_argument('--check', action='store_true', help='Fail if CSS is missing or out of date; do not write.')
    args = parser.parse_args()
    expected = render(json.loads(args.tokens.read_text(encoding='utf-8')))
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding='utf-8') != expected:
            print('Token CSS is stale. Run scripts/generate_tokens.py.', file=sys.stderr)
            return 1
        print('Token CSS matches JSON.')
    else:
        args.output.write_text(expected, encoding='utf-8')
        print(f'Generated {args.output.name}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
