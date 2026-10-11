"""Versioned project profiles, field mapping and local exchange preparation. No network writes."""
from datetime import date
from decimal import Decimal
import hashlib
import json
import re

KINDS = {'profile', 'template_mapping', 'exchange'}
REQUIRED = {
    'profile': ('billing_mode', 'delivery_mode', 'streams', 'terms_refs', 'open_items'),
    'template_mapping': ('form_ref', 'mappings', 'omissions', 'audience'),
    'exchange': ('operation_id', 'system', 'entity', 'direction', 'record_id', 'external_id',
                 'mapping_ref', 'state', 'receipt_ref', 'conflicts'),
}
REFERENCE_KEYS = {'form_ref', 'mapping_ref', 'receipt_ref', 'terms_refs', 'artifact_ref', 'source_ref'}


def refkey(ref):
    return ref['artifact_id'], ref['revision'], ref['sha256']


def find(upstream, ref):
    for obj in upstream:
        if obj['artifact_id'] == ref['artifact_id'] and obj['revision'] == ref['revision']:
            return obj
    raise ValueError('Reference is outside pinned inputs')


def pointer(value, path):
    if not isinstance(path, str) or (path and not path.startswith('/')):
        raise ValueError('RFC 6901 JSON pointer required')
    for part in path.split('/')[1:] if path else []:
        if re.search(r'~(?![01])', part):
            raise ValueError('Invalid JSON pointer escape')
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', part) or int(part) >= len(value):
                raise ValueError('Missing JSON pointer list item')
            value = value[int(part)]
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise ValueError('Missing JSON pointer field')
    return value


def check_fields(value, forbidden):
    if isinstance(value, dict):
        if any(forbidden(key) for key in value):
            raise ValueError('Sensitive field in mapped output')
        for item in value.values():
            check_fields(item, forbidden)
    elif isinstance(value, list):
        for item in value:
            check_fields(item, forbidden)


def check_exchange_fields(mapping, upstream, read_source, forbidden):
    # Finance amounts may be exchanged; credentials and private source paths may not.
    for item in mapping['data']['mappings']:
        if forbidden(item['target_field']) or any(forbidden(part) for part in item['source_pointer'].split('/')):
            raise ValueError('Sensitive exchange source or target field')
        source = find(upstream, item['source_ref'])
        raw = read_source(source) if source['kind'] == 'source' else source['data']
        check_fields(pointer(raw, item['source_pointer']), forbidden)


def mapped_values(value, upstream, read_source, forbidden):
    """The target specification is an actual pinned JSON source, not caller-invented fields."""
    data = value['data']
    form = find(upstream, data['form_ref'])
    if form['kind'] != 'source':
        raise ValueError('form_ref must bind an actual JSON field specification source')
    spec = read_source(form)
    fields = spec.get('fields') if isinstance(spec, dict) else None
    if not isinstance(fields, list) or not fields:
        raise ValueError('Target specification needs fields')
    by_id = {}
    for field in fields:
        if (not isinstance(field, dict) or not isinstance(field.get('id'), str) or not field['id']
                or field['id'] in by_id or field.get('type') not in {'string', 'number', 'boolean', 'array', 'object'}
                or not isinstance(field.get('required'), bool)):
            raise ValueError('Invalid/duplicate target field definition')
        by_id[field['id']] = field
    if data['audience'] not in {'internal', 'customer'}:
        raise ValueError('Unknown mapped audience')
    out, covered = {}, set()
    for item in data['mappings']:
        target = item['target_field']
        if target not in by_id or target in covered:
            raise ValueError('Unknown/duplicate target mapping')
        covered.add(target)
        source = find(upstream, item['source_ref'])
        raw = read_source(source) if source['kind'] == 'source' else source['data']
        if data['audience'] == 'customer':
            # A public target label cannot launder an internal field or entire object.
            if source['visibility'] != 'customer' or source['kind'] in {'costs', 'timesheets', 'profile', 'exchange', 'closure'}:
                raise ValueError('Customer mapping cannot expose an internal source')
            if any(forbidden(p.replace('~1', '/').replace('~0', '~')) for p in item['source_pointer'].split('/')):
                raise ValueError('Customer mapping references a sensitive source field')
        actual = pointer(raw, item['source_pointer'])
        if data['audience'] == 'customer':
            check_fields(actual, forbidden)
        transform = item['transform']
        if transform == 'string':
            actual = None if actual is None else str(actual)
        elif transform == 'number' and actual is not None:
            if isinstance(actual, bool):
                raise ValueError('Boolean cannot be converted to amount')
            try:
                actual = Decimal(str(actual))
            except Exception as exc:
                raise ValueError('Invalid mapped number') from exc
            if not actual.is_finite():
                raise ValueError('Non-finite mapped number')
            actual = float(actual)
        elif transform not in {'identity', 'number'}:
            raise ValueError('Only identity/string/number transforms are supported')
        field = by_id[target]
        types = {'string': str, 'number': (int, float), 'boolean': bool, 'array': list, 'object': dict}
        if actual is not None and (not isinstance(actual, types[field['type']])
                or (field['type'] == 'number' and isinstance(actual, bool))):
            raise ValueError('Mapped value does not match target type')
        if field['required'] and (actual is None or actual == '' or actual == [] or actual == {}):
            raise ValueError('Required mapped value is missing')
        out[target] = actual
    for item in data['omissions']:
        target = item['target_field']
        if target not in by_id or target in covered or not item['reason']:
            raise ValueError('Unknown/duplicate/unexplained omitted target')
        if by_id[target]['required']:
            raise ValueError('Required target fields cannot be waived by a mapping')
        covered.add(target)
    if covered != set(by_id):
        raise ValueError('Every target field needs a mapping or explicit omission')
    if data['audience'] == 'customer':
        def check(obj):
            if isinstance(obj, dict):
                if any(forbidden(k) for k in obj):
                    raise ValueError('Sensitive field in mapped output')
                for v in obj.values():
                    check(v)
            elif isinstance(obj, list):
                for v in obj:
                    check(v)
        check(out)
    try:
        json.dumps(out, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError('Mapped output must contain finite JSON values') from exc
    return out


def payload_hash(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate(value, upstream, rows, number, purpose, read_source, forbidden):
    kind, data = value['kind'], value['data']
    if kind == 'profile':
        if data['billing_mode'] not in {'fixed', 'time', 'mixed'} or data['delivery_mode'] not in {'staged', 'iterative', 'mixed'}:
            raise ValueError('Unknown billing/delivery mode')
        streams = rows(data, 'streams', ('mode', 'scope_ids', 'currency', 'amount', 'hours', 'rate', 'cap', 'basis', 'terms_refs'))
        if (not streams or not isinstance(data['terms_refs'], list) or not data['terms_refs']
                or not isinstance(data['open_items'], list)):
            raise ValueError('Billing profile requires streams and contract/decision evidence')
        seen = set()
        for s in streams:
            if (s['mode'] not in {'fixed', 'time'} or not isinstance(s['scope_ids'], list) or not s['scope_ids']
                    or not isinstance(s['terms_refs'], list) or not s['terms_refs'] or not s['basis']):
                raise ValueError('Billing stream requires scope and terms')
            if not re.fullmatch('[A-Z]{3}', s['currency']):
                raise ValueError('Billing stream currency required')
            for scope in s['scope_ids']:
                if not isinstance(scope, str) or not scope or scope in seen:
                    raise ValueError('Billing scope cannot be charged in overlapping streams')
                seen.add(scope)
            for field in ('amount', 'hours', 'rate', 'cap'):
                number(s[field], field, True)
            if (s['mode'] == 'fixed' and any(s[k] is not None for k in ('hours', 'rate'))
                    or s['mode'] == 'time' and s['amount'] is not None):
                raise ValueError('Billing stream must use only its own calculation inputs')
        modes = {s['mode'] for s in streams}
        if (data['billing_mode'] == 'mixed' and modes != {'fixed', 'time'}
                or data['billing_mode'] != 'mixed' and modes != {data['billing_mode']}):
            raise ValueError('Billing mode disagrees with its streams')
    elif kind == 'template_mapping':
        rows(data, 'mappings', ('target_field', 'source_ref', 'source_pointer', 'transform'))
        rows(data, 'omissions', ('target_field', 'reason'))
        mapped_values(value, upstream, read_source, forbidden)
    elif kind == 'exchange':
        if (data['entity'] not in {'task', 'code', 'finance', 'document'} or data['direction'] not in {'inbound', 'outbound'}
                or data['state'] not in {'prepared', 'reconciled'}):
            raise ValueError('Unknown exchange entity/direction/state')
        if any(not isinstance(data[k], str) or not data[k].strip() for k in ('operation_id', 'system', 'record_id', 'external_id')):
            raise ValueError('Stable operation/system/internal/external identifiers required')
        if not isinstance(data['conflicts'], list):
            raise ValueError('conflicts must be a list')
        mapping = find(upstream, data['mapping_ref'])
        if mapping['kind'] != 'template_mapping':
            raise ValueError('Exchange requires a field mapping')
        payload = mapped_values(mapping, upstream, read_source, forbidden)
        check_exchange_fields(mapping, upstream, read_source, forbidden)
        if data['state'] == 'reconciled':
            if data['conflicts'] or not data['receipt_ref']:
                raise ValueError('Reconciled exchange needs receipt and no unresolved conflicts')
            receipt = find(upstream, data['receipt_ref'])
            if receipt['kind'] != 'source':
                raise ValueError('Receipt must bind actual source content')
            record = read_source(receipt)
            if not isinstance(record, dict):
                raise ValueError('Exchange receipt must be a JSON object')
            expected = {k: data[k] for k in ('operation_id', 'system', 'entity', 'direction', 'record_id', 'external_id')}
            expected.update(
                            payload_sha256=payload_hash(payload), state='applied', origin='actual' if purpose != 'simulation' else record.get('origin'))
            if record.get('origin') not in {'actual', 'simulation'} or any(record.get(k) != v for k, v in expected.items()):
                raise ValueError('Exchange receipt does not match operation, payload, ID or origin')
        elif data['receipt_ref'] is not None:
            raise ValueError('Use reconciled state to bind an execution receipt')


def billing_summary(data):
    totals, gaps = {}, []
    for stream in data['streams']:
        if stream['mode'] == 'fixed':
            raw = stream['amount']
        else:
            raw = None if stream['hours'] is None or stream['rate'] is None else Decimal(str(stream['hours'])) * Decimal(str(stream['rate']))
        if raw is None:
            gaps.append(stream['id'] + ': billing estimate unknown')
            continue
        amount = Decimal(str(raw))
        if stream['cap'] is not None:
            amount = min(amount, Decimal(str(stream['cap'])))
        totals[stream['currency']] = totals.get(stream['currency'], Decimal(0)) + amount
    return {'estimates_by_currency': {c: str(v.quantize(Decimal('.01'))) for c, v in totals.items()},
            'complete': not gaps and not data['open_items'], 'gaps': gaps + list(data['open_items']),
            'revenue_recognized': False, 'invoice_created': False}


def gate(value):
    data = value['data']
    if value['kind'] == 'profile':
        result = billing_summary(data)
        return dict(ready=value['status'] == 'ready' and result['complete'], reasons=result['gaps'], billing=result)
    if value['kind'] == 'exchange':
        return dict(ready=value['status'] == 'ready' and data['state'] == 'reconciled' and not data['conflicts'],
                    reasons=[] if data['state'] == 'reconciled' and not data['conflicts'] else ['Exchange is only prepared or has conflicts'],
                    dispatched_by_tool=False)
    return dict(ready=value['status'] == 'ready', reasons=[])


def check_revision(previous, current):
    if current['kind'] == 'exchange':
        keys = ('operation_id', 'system', 'entity', 'direction', 'record_id', 'external_id', 'mapping_ref')
        if any(previous['data'][k] != current['data'][k] for k in keys):
            raise ValueError('Exchange operation and payload mapping are immutable; use a new operation')
        if previous['data']['state'] == 'reconciled' and previous['data'] != current['data']:
            raise ValueError('Reconciled receipt cannot be rewritten')


def portfolio(projects, as_of, runtime, identity_map=None, capacities=None):
    """Read current snapshots, never silently sum currencies or combine same-named people."""
    date.fromisoformat(as_of)
    if as_of != runtime.now()[:10]:
        raise ValueError('Portfolio supports only the current UTC extraction date')
    identity_map = identity_map or {}
    results, ids, purposes, currencies, gaps, loads = [], set(), set(), {}, [], {}
    for project in projects:
        snap = runtime.snapshot(project)
        pid = snap['project_id']
        if pid in ids:
            raise ValueError('Duplicate portfolio project ID')
        ids.add(pid); purposes.add(snap['purpose'])
        validation = runtime.validate(project)
        if not validation['ok'] or not validation['effective_ok'] or snap['alerts']:
            raise ValueError('Portfolio project has invalid or stale records: ' + pid)
        summaries = snap['cost_summary']
        currency = runtime.read_project(project)['currency']
        if summaries.get('forecast') is not None:
            currencies[currency] = currencies.get(currency, Decimal(0)) + Decimal(summaries['forecast'])
        if not summaries.get('complete'):
            gaps.append(pid + ': cost coverage incomplete')
        refs = []
        for obj in snap['artifacts']:
            refs.append({k: obj[k] for k in ('artifact_id', 'revision', 'sha256')})
            if obj['kind'] == 'timesheets':
                # Same person labels in different projects are ambiguous unless explicitly mapped.
                data = obj['data']
                for allocation in data.get('allocations', []):
                    local = allocation['person']
                    person = identity_map.get(pid, {}).get(local)
                    if not person:
                        gaps.append(pid + ': unmapped resource ' + local)
                        continue
                    key = person, allocation['period']
                    if allocation['planned_hours'] is None:
                        gaps.append(pid + ': planned hours unknown for ' + local)
                        loads[key] = None
                    else:
                        if loads.get(key, Decimal(0)) is not None:
                            loads[key] = loads.get(key, Decimal(0)) + Decimal(str(allocation['planned_hours']))
        # as_of is the extraction date, not an invented historical state.
        created = runtime.read_project(project)['created_at'][:10]
        if as_of < created:
            raise ValueError('Historical portfolio reconstruction is unsupported')
        results.append({'project_id': pid, 'purpose': snap['purpose'], 'currency': currency,
                        'source_refs': refs, 'cost_summary': summaries, 'gates': snap['gates']})
    if len(purposes) > 1:
        raise ValueError('Cannot aggregate simulation and real projects')
    if not results:
        raise ValueError('Portfolio needs projects')
    available = {}
    for row in capacities or []:
        key = row['person'], row['period']
        if key in available or not all(key):
            raise ValueError('Duplicate/invalid shared resource capacity')
        available[key] = runtime.number(row['available_hours'], 'shared capacity', True)
    resource_load = []
    for key, hours in sorted(loads.items()):
        capacity = available.get(key)
        if capacity is None:
            gaps.append('Shared capacity unknown: ' + key[0] + '/' + key[1])
        resource_load.append({'person': key[0], 'period': key[1], 'planned_hours': None if hours is None else str(hours),
                              'available_hours': None if capacity is None else str(capacity),
                              'overloaded': None if capacity is None or hours is None else hours > capacity})
    return {'as_of': as_of, 'extracted_at': runtime.now(), 'historical_reconstruction': False,
            'projects': results, 'forecast_by_currency': {c: str(v.quantize(Decimal('.01'))) for c, v in currencies.items()},
            'resource_load': resource_load,
            'complete': not gaps, 'gaps': sorted(set(gaps)), 'external_actions': False}
