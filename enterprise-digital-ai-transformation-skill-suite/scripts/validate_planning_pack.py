"""Validate planning traceability and cash-flow reconciliation, not client approval.

Usage: python scripts/validate_planning_pack.py /path/to/planning-pack.json
Financial amount units and periods must already be normalized by the author.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def validate(pack):
    errors = []
    required = ('evidence', 'processes', 'information_objects', 'applications',
                'technology_services', 'kpis', 'initiatives', 'waves')
    for key in required:
        if not isinstance(pack.get(key), list) or not pack[key]:
            errors.append(f'missing nonempty collection: {key}')
    if errors:
        return errors
    indexes = {}
    for key in required:
        indexes[key] = {}
        for row in pack[key]:
            if not isinstance(row, dict) or not row.get('id'):
                errors.append(f'{key}: missing id')
                continue
            if row['id'] in indexes[key]:
                errors.append(f'{key}: duplicate id {row["id"]}')
            indexes[key][row['id']] = row

    def fields(row, names):
        for name in names:
            if name not in row or row[name] is None or row[name] == '' or row[name] == [] or row[name] == {}:
                errors.append(f'{row.get("id")}: missing {name}')

    def refs(row, field, target, allow_empty=False):
        values = row.get(field)
        if not isinstance(values, list) or (not values and not allow_empty):
            errors.append(f'{row.get("id")}: empty/invalid {field}')
            return
        for value in values:
            if value not in indexes[target]:
                errors.append(f'{row.get("id")}: unknown {field} {value}')

    for p in pack['processes']:
        fields(p, ('name', 'owner', 'level'))
        level = p.get('level')
        parent = indexes['processes'].get(p.get('parent_id'))
        if level not in (1, 2, 3, 4) or (level == 1 and p.get('parent_id')) or (
                level in (2, 3, 4) and (not parent or parent.get('level') != level - 1)):
            errors.append(f'{p.get("id")}: invalid level/parent')
        if level in (1, 2, 3) and not any(c.get('parent_id') == p['id'] for c in pack['processes']):
            errors.append(f'{p["id"]}: no child at next level')
        if level == 4:
            fields(p, ('inputs', 'outputs', 'control_points'))
            for field, target in [('information_ids', 'information_objects'), ('application_ids', 'applications'), ('kpi_ids', 'kpis')]:
                refs(p, field, target)
    if {p.get('level') for p in pack['processes']} != {1, 2, 3, 4}:
        errors.append('process hierarchy must cover four levels')
    for obj in pack['information_objects']:
        fields(obj, ('name', 'owner'))
    for app in pack['applications']:
        fields(app, ('name', 'lifecycle'))
        for field, target in [('process_ids', 'processes'), ('information_ids', 'information_objects'), ('technology_ids', 'technology_services')]:
            refs(app, field, target)
    for tech in pack['technology_services']:
        fields(tech, ('name', 'nfr'))
        refs(tech, 'application_ids', 'applications')
    for kpi in pack['kpis']:
        fields(kpi, ('name', 'formula', 'owner', 'baseline', 'target', 'aggregation'))
    wave_order = {w['id']: n for n, w in enumerate(pack['waves'])}
    for wave in pack['waves']:
        refs(wave, 'initiative_ids', 'initiatives')
        for i in wave.get('initiative_ids', []):
            if i in indexes['initiatives'] and indexes['initiatives'][i].get('wave_id') != wave['id']:
                errors.append(f'{i}: inconsistent wave membership')
    for item in pack['initiatives']:
        for field, target in [('process_ids', 'processes'), ('application_ids', 'applications'), ('kpi_ids', 'kpis')]:
            refs(item, field, target)
        refs(item, 'depends_on', 'initiatives', allow_empty=True)
        wave = item.get('wave_id')
        if wave not in wave_order or item['id'] not in indexes['waves'][wave].get('initiative_ids', []):
            errors.append(f'{item["id"]}: missing wave membership')
        for dep in item.get('depends_on', []):
            producer = indexes['initiatives'].get(dep)
            if producer and wave in wave_order and wave_order.get(producer.get('wave_id'), -1) >= wave_order[wave]:
                errors.append(f'{item["id"]}: dependency must finish in an earlier wave: {dep}')
    header = pack.get('artifact_header', {})
    if not header.get('status'):
        errors.append('missing artifact status')
    if header.get('status') in ('approved', 'validated') and any(e.get('status') == 'assumed' for e in pack['evidence']):
        errors.append('assumed evidence cannot be promoted by this simulation validator')

    f = pack.get('financials', {})
    fields(f, ('currency', 'unit', 'costs', 'benefits', 'annual_cash_flow'))
    totals = {'cost': defaultdict(float), 'benefit': defaultdict(float)}
    seen = set()
    for kind, collection in [('cost', 'costs'), ('benefit', 'benefits')]:
        for row in f.get(collection, []):
            amount, year = row.get('amount'), row.get('year')
            if not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0 or not isinstance(year, int):
                errors.append(f'invalid {kind} amount/year'); continue
            if kind == 'cost':
                if row.get('initiative_id') not in indexes['initiatives']:
                    errors.append('unknown cost initiative')
            else:
                fields(row, ('id', 'basis'))
                refs(row, 'initiative_ids', 'initiatives')
                identity = (row.get('id'), year)
                if identity in seen:
                    errors.append(f'duplicate benefit/year: {identity}')
                seen.add(identity)
            totals[kind][year] += amount
    cumulative = 0
    rows = f.get('annual_cash_flow', [])
    years = [row.get('year') for row in rows]
    expected_years = set(totals['cost']) | set(totals['benefit'])
    if len(years) != len(set(years)) or set(years) != expected_years or years != sorted(years):
        errors.append('cash flow years do not reconcile')
    for row in rows:
        year = row.get('year')
        cost, benefit = totals['cost'][year], totals['benefit'][year]
        net = benefit - cost
        cumulative += net
        for field, expected in [('cost', cost), ('benefit', benefit), ('net', net), ('cumulative', cumulative)]:
            value = row.get(field)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value - expected) > 0.01:
                errors.append(f'cash flow {year}/{field}: expected {expected}, got {value}')
    return errors


if __name__ == '__main__':
    try:
        result = validate(json.loads(Path(sys.argv[1]).read_text()))
    except (IndexError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f'Invalid planning pack: {exc}', file=sys.stderr)
        sys.exit(2)
    print(json.dumps({'passed': not result, 'errors': result,
                      'scope': 'structural traceability and arithmetic only; not client approval'}, ensure_ascii=False, indent=2))
    sys.exit(bool(result))
