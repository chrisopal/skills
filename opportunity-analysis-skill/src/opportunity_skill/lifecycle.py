"""Deterministic lifecycle mutations. Evidence records attest provenance, not legal validity."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import math
import hashlib
from pathlib import Path
from typing import Any

from .stage_management import stage_by_id
from .utils import new_id, now_iso

FACT_GATES = {
    'customer_contacted': ('contact_established',),
    'needs_discovery': ('need_confirmed',),
    'opportunity_confirmed': ('need_confirmed', 'requirement_owner', 'continue_intent'),
    'solution_cocreation': ('solution_scope',),
    'budget_project_confirmed': ('budget_confirmed',),
    'proposal_bidding': ('quote_authorized',),
}
ARTIFACT_GATES = {'solution_cocreation': 'solution', 'proposal_bidding': 'quote',
                  'commercial_negotiation': 'negotiation', 'contract_signing': 'contract'}
BOOLEAN_FACTS = {'contact_established', 'need_confirmed', 'continue_intent', 'budget_confirmed', 'quote_authorized'}
UNKNOWN_VALUES = {'unknown', '未知', '待确认', '不确定', '不知道'}
ARTIFACT_KINDS = {'handoff', 'solution', 'quote', 'negotiation', 'contract'}


def initial_lifecycle(suggested_stage_id: str | None = None, *, legacy: bool = False) -> dict[str, Any]:
    return {'current_stage_id': 'lead_identified', 'suggested_stage_id': suggested_stage_id,
            'status': 'active', 'revision': 0, 'facts': [], 'history': [], 'actions': [],
            'artifacts': [], 'contracts': [], 'status_history': [], 'next_action': None,
            'owner': None, 'owner_history': [],
            'close_reason': None, 'migration_note': 'Legacy stage retained as suggestion; no confirmed facts or history inferred.' if legacy else None}


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be nonempty text')
    return value.strip()


def require_date(value: Any, label: str) -> str:
    value = require_text(value, label)
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError(f'{label} must be an ISO date (YYYY-MM-DD)') from None
    return value


def file_digest(path: Any) -> tuple[str, str]:
    source = Path(require_text(path, 'file_path')).expanduser().resolve()
    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError('artifact requires a real nonempty local file')
    return str(source), hashlib.sha256(source.read_bytes()).hexdigest()


def artifact_is_current(artifact: dict[str, Any]) -> bool:
    try:
        return file_digest(artifact.get('file_path'))[1] == artifact.get('sha256')
    except (ValueError, OSError):
        return False


def latest_facts(state):
    return {f['fact_id']: f for f in state['facts']}


def fact_satisfies(fact):
    value = fact['value']
    if fact['status'] != 'confirmed':
        return False
    if fact['fact_id'] in BOOLEAN_FACTS:
        return value is True
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in UNKNOWN_VALUES


def effective_artifact(state, artifact):
    return max((a for a in state['artifacts'] if a.get('document_id', a['kind']) == artifact.get('document_id', artifact['kind'])), key=lambda a: a['version'])['id'] == artifact['id']


def lifecycle_blockers(state):
    blockers = []
    required_facts = set(FACT_GATES.get(state['current_stage_id'], ()))
    for event in state['history']:
        required_facts.update(FACT_GATES.get(event['to_stage'], ()))
    facts = latest_facts(state)
    for fact_id in sorted(required_facts):
        if fact_id not in facts or not fact_satisfies(facts[fact_id]):
            blockers.append('fact unresolved, missing or negative: ' + fact_id)
    if 'quote_authorized' in required_facts and 'quote_authorized' in facts and fact_satisfies(facts['quote_authorized']):
        fact = facts['quote_authorized']
        artifact = next((a for a in state['artifacts'] if a['id'] == fact.get('artifact_id')), None)
        if not artifact or artifact['sha256'] != fact.get('sha256') or not effective_artifact(state, artifact) or not artifact_is_current(artifact):
            blockers.append('quote authorization is stale or unbound')
    artifact_kind = ARTIFACT_GATES.get(state['current_stage_id'])
    if artifact_kind:
        candidates = [a for a in state['artifacts'] if a['kind'] == artifact_kind and effective_artifact(state, a)]
        if not candidates or not any(artifact_is_current(a) for a in candidates):
            blockers.append('current artifact stale or missing: ' + artifact_kind)
    if state['status'] == 'won':
        if not state['contracts']:
            blockers.append('signed contract record missing')
        else:
            contract = state['contracts'][-1]
            artifact = next((a for a in state['artifacts'] if a['id'] == contract['artifact_id']), None)
            if not artifact or not artifact_is_current(artifact) or not effective_artifact(state, artifact):
                blockers.append('signed contract stale, missing or superseded')
    return blockers


def read_lifecycle(state: dict[str, Any]) -> dict[str, Any]:
    state = deepcopy(state)
    for artifact in state['artifacts']:
        artifact['validity'] = 'superseded' if not effective_artifact(state, artifact) else 'valid' if artifact_is_current(artifact) else 'stale_or_missing'
    pending = [a for a in state['actions'] if a['status'] == 'open']
    state['blockers'] = lifecycle_blockers(state)
    state['verification_status'] = 'needs_review' if state['blockers'] else 'current'
    state['next_action'] = min(pending, key=lambda a: (a['due_date'], a['created_at'])) if pending else None
    return state


def apply_operations(state: dict[str, Any], operations: Any, actor: str, evidence_ids: set[str]) -> dict[str, Any]:
    if not isinstance(operations, list) or not operations:
        raise ValueError('operations must be a nonempty array')
    state = deepcopy(state)
    timestamp = now_iso()

    def evidence(op):
        refs = op.get('evidence')
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or ref not in evidence_ids for ref in refs):
            raise ValueError('evidence must reference existing evidence owned by this opportunity')
        return list(dict.fromkeys(refs))

    def item_by_id(collection, item_id, label):
        item = next((i for i in collection if i['id'] == item_id), None)
        if item is None:
            raise ValueError(f'{label} not found in this opportunity: {item_id}')
        return item

    for op in operations:
        if not isinstance(op, dict):
            raise ValueError('each operation must be an object')
        kind = op.get('type')
        if state['status'] in {'won', 'lost', 'cancelled'}:
            reopening = kind == 'set_status' and op.get('status') == 'active'
            handoff = state['status'] == 'won' and (kind in {'add_action', 'complete_action', 'set_owner'} or (kind == 'register_artifact' and op.get('kind') == 'handoff'))
            if not reopening and not handoff:
                raise ValueError('reopen closed opportunity explicitly before this operation')
        if kind == 'set_owner':
            owner = require_text(op.get('owner'), 'owner')
            reason = require_text(op.get('reason'), 'reason')
            state.setdefault('owner_history', []).append({'from_owner': state.get('owner'),
                'to_owner': owner, 'actor': actor, 'time': timestamp, 'reason': reason})
            state['owner'] = owner
        elif kind == 'confirm_fact':
            fact_id = require_text(op.get('fact_id'), 'fact_id')
            value = op.get('value')
            if value is None or value == '':
                raise ValueError('fact requires a value')
            if fact_id in BOOLEAN_FACTS and type(value) is not bool and not (isinstance(value, str) and value.strip().lower() in UNKNOWN_VALUES):
                raise ValueError('boolean gate facts require true, false or unknown')
            unresolved = isinstance(value, str) and value.strip().lower() in UNKNOWN_VALUES
            refs = evidence(op)
            binding = {}
            if fact_id == 'quote_authorized' and value is True:
                artifact = item_by_id(state['artifacts'], op.get('artifact_id'), 'authorized quote artifact')
                if artifact['kind'] != 'quote' or not effective_artifact(state, artifact) or not artifact_is_current(artifact):
                    raise ValueError('quote authorization must bind the current hash-matching quote artifact')
                binding = {'artifact_id': artifact['id'], 'sha256': artifact['sha256']}
            version = 1 + max((f['version'] for f in state['facts'] if f['fact_id'] == fact_id), default=0)
            state['facts'].append({'id': new_id('fact'), 'fact_id': fact_id, 'value': value, 'version': version,
                                   **binding, 'status': 'unresolved' if unresolved else 'confirmed', 'actor': actor, 'time': timestamp, 'evidence': refs})
        elif kind == 'add_action':
            action_id = op.get('action_id') or new_id('act')
            if any(a['id'] == action_id for a in state['actions']):
                raise ValueError('action_id already exists')
            state['actions'].append({'id': action_id, 'title': require_text(op.get('title'), 'title'),
                'owner': require_text(op.get('owner'), 'owner'), 'due_date': require_date(op.get('due_date'), 'due_date'),
                'status': 'open', 'result': None, 'evidence': [], 'created_at': timestamp, 'actor': actor})
        elif kind == 'complete_action':
            action = item_by_id(state['actions'], op.get('action_id'), 'action')
            if action['status'] != 'open':
                raise ValueError('action already completed')
            action.update(status='completed', result=require_text(op.get('result'), 'result'), evidence=evidence(op),
                          completed_at=timestamp, completed_by=actor)
        elif kind == 'register_artifact':
            artifact_kind = op.get('kind')
            if artifact_kind not in ARTIFACT_KINDS:
                raise ValueError('unsupported artifact kind')
            version = op.get('version')
            document_id = require_text(op.get('document_id', artifact_kind), 'document_id')
            if any(a['kind'] != artifact_kind for a in state['artifacts'] if a.get('document_id', a['kind']) == document_id):
                raise ValueError('document_id cannot change artifact kind')
            versions = [a['version'] for a in state['artifacts'] if a.get('document_id', a['kind']) == document_id]
            if type(version) is not int or version <= max(versions, default=0):
                raise ValueError('artifact version must be a positive, increasing integer per document_id')
            artifact_id = op.get('artifact_id') or new_id('artifact')
            if any(a['id'] == artifact_id for a in state['artifacts']):
                raise ValueError('artifact_id already exists')
            path, digest = file_digest(op.get('file_path'))
            metadata = op.get('metadata', {})
            if not isinstance(metadata, dict):
                raise ValueError('metadata must be an object')
            state['artifacts'].append({'id': artifact_id, 'document_id': document_id, 'kind': artifact_kind, 'version': version,
                'file_path': path, 'sha256': digest, 'metadata': metadata, 'evidence': evidence(op),
                'actor': actor, 'time': timestamp, 'status': 'registered'})
        elif kind == 'record_contract':
            artifact = item_by_id(state['artifacts'], op.get('artifact_id'), 'artifact')
            if artifact['kind'] != 'contract' or not artifact_is_current(artifact) or not effective_artifact(state, artifact):
                raise ValueError('contract requires a hash-matching contract artifact')
            parties = op.get('parties')
            if not isinstance(parties, list) or len(parties) < 2 or any(not isinstance(p, str) or not p.strip() for p in parties):
                raise ValueError('contract requires at least two named parties')
            amount = op.get('amount')
            if type(amount) not in (int, float) or not math.isfinite(amount) or amount < 0:
                raise ValueError('contract amount must be a nonnegative number')
            signatures = op.get('signature_facts', {})
            if not isinstance(signatures, dict) or signatures.get('customer_signed') is not True or signatures.get('supplier_signed') is not True:
                raise ValueError('both customer_signed and supplier_signed facts must be explicitly true')
            contract_id = op.get('contract_id') or new_id('contract')
            if any(c['id'] == contract_id for c in state['contracts']):
                raise ValueError('contract_id already exists')
            state['contracts'].append({'id': contract_id, 'artifact_id': artifact['id'], 'sha256': artifact['sha256'],
                'signing_date': require_date(op.get('signing_date'), 'signing_date'), 'parties': parties,
                'amount': amount, 'currency': require_text(op.get('currency'), 'currency'),
                'signature_facts': signatures, 'evidence': evidence(op), 'actor': actor, 'time': timestamp,
                'verification_scope': 'Recorded signature facts; no legal or signature authenticity verification.'})
        elif kind == 'transition':
            target = op.get('to_stage')
            if stage_by_id(str(target)) is None or target in {'lost', 'cancelled'}:
                raise ValueError('unsupported active stage; use set_status for lost/cancelled')
            if state['status'] != 'active':
                raise ValueError('resume paused opportunity before transitioning')
            if target == state['current_stage_id']:
                raise ValueError('transition requires a different stage')
            reason, refs = require_text(op.get('reason'), 'reason'), evidence(op)
            blockers = lifecycle_blockers(state)
            if blockers:
                raise ValueError('resolve lifecycle blockers before transition: ' + '; '.join(blockers))
            confirmed = {key for key, fact in latest_facts(state).items() if fact_satisfies(fact)}
            missing = set(FACT_GATES.get(target, ())) - confirmed
            if missing:
                raise ValueError('missing confirmed facts: ' + ', '.join(sorted(missing)))
            if target == 'proposal_bidding':
                fact = latest_facts(state)['quote_authorized']
                artifact = item_by_id(state['artifacts'], fact.get('artifact_id'), 'authorized quote artifact')
                if not effective_artifact(state, artifact) or not artifact_is_current(artifact) or fact.get('sha256') != artifact['sha256']:
                    raise ValueError('quote authorization is stale for the current artifact')
            required_kind = ARTIFACT_GATES.get(target)
            if required_kind:
                candidates = [a for a in state['artifacts'] if a['kind'] == required_kind and effective_artifact(state, a)]
                if not candidates or not any(artifact_is_current(a) for a in candidates):
                    raise ValueError(f'{target} requires current {required_kind} artifact')
            if target == 'won':
                if not state['contracts']:
                    raise ValueError('won requires a recorded signed contract')
                contract = state['contracts'][-1]
                artifact = item_by_id(state['artifacts'], contract['artifact_id'], 'contract artifact')
                if not artifact_is_current(artifact) or not effective_artifact(state, artifact) or contract['sha256'] != artifact['sha256']:
                    raise ValueError('signed contract file is stale or missing')
                state['status'] = 'won'
            state['history'].append({'id': new_id('transition'), 'from_stage': state['current_stage_id'],
                'to_stage': target, 'actor': actor, 'time': timestamp, 'reason': reason, 'evidence': refs})
            state['current_stage_id'] = target
        elif kind == 'set_status':
            target = op.get('status')
            if target not in {'active', 'paused', 'lost', 'cancelled'} or target == state['status']:
                raise ValueError('status must change to active, paused, lost or cancelled')
            reason, refs = require_text(op.get('reason'), 'reason'), evidence(op)
            state['status_history'].append({'from_status': state['status'], 'to_status': target,
                'actor': actor, 'time': timestamp, 'reason': reason, 'evidence': refs})
            if state['status'] == 'won' and target == 'active':
                state['history'].append({'id': new_id('transition'), 'from_stage': 'won', 'to_stage': 'contract_signing',
                    'actor': actor, 'time': timestamp, 'reason': reason, 'evidence': refs})
                state['current_stage_id'] = 'contract_signing'
            state['status'] = target
            if target == 'active':
                state['close_reason'] = None
            if target in {'lost', 'cancelled'}:
                state['close_reason'] = reason
        else:
            raise ValueError(f'unsupported operation type: {kind}')
    return state
