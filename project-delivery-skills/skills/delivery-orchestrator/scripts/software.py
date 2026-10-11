"""Software delivery records and evidence gates; never executes production actions."""
import re

KINDS = {'solution', 'ui_design', 'integration', 'work_package', 'testing', 'release', 'handover'}
READINESS_IDS = {'backup', 'rollback', 'window', 'monitoring', 'authorization'}
PUBLIC_KINDS = {'solution', 'ui_design', 'integration', 'testing', 'handover'}
REQUIRED = {
    'solution': ('components', 'decisions', 'requirement_ids'),
    'ui_design': ('pages', 'fields', 'permissions', 'states', 'requirement_ids'),
    'integration': ('interfaces', 'mappings', 'migration', 'reconciliations', 'requirement_ids'),
    'work_package': ('plan_work_package_id', 'requirement_ids', 'design_refs', 'completion_rule', 'build_ref', 'evidence_refs'),
    'testing': ('requirement_ids', 'environment', 'build_ref', 'cases', 'defects', 'uat'),
    'release': ('environment', 'build_ref', 'testing_ref', 'readiness', 'execution', 'rollback'),
    'handover': ('audiences', 'training', 'operations', 'assets', 'open_items'),
}
REFERENCE_KEYS = {'design_refs', 'testing_ref', 'verification_refs', 'restore_refs', 'receipt_refs', 'retest_refs',
                  'backup_refs', 'rehearsal_refs', 'reconciliation_refs', 'runbook_refs'}


def require(value, keys, label):
    if not isinstance(value, dict) or any(key not in value for key in keys):
        raise ValueError(f'{label} requires {keys}')


def state(value, allowed, label):
    if value not in allowed:
        raise ValueError(f'Unknown {label}: {value}')


def build(value):
    require(value, ('repository', 'revision', 'sha256'), 'build_ref')
    if not value['repository'] or not isinstance(value['revision'], str) or not value['revision']:
        raise ValueError('Build needs repository and exact revision')
    if not isinstance(value['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', value['sha256']):
        raise ValueError('Build needs a complete artifact SHA-256')


def validate(value, upstream, rows, number, purpose):
    """upstream contains the already hash-checked transitive input closure."""
    kind, data = value['kind'], value['data']
    if kind not in KINDS:
        return
    reqs = {x['id'] for obj in upstream if obj['kind'] == 'requirements' for x in obj['data']['items']}
    scope = data.get('requirement_ids')
    if kind in {'solution', 'ui_design', 'integration', 'work_package', 'testing'}:
        if not isinstance(scope, list) or not scope or len(scope) != len(set(scope)) or not set(scope) <= reqs:
            raise ValueError('Software scope requires unique requirement IDs from pinned inputs')
    if kind == 'solution':
        components = rows(data, 'components', ('purpose', 'requirement_ids', 'deployment', 'security', 'nonfunctional'))
        for decision in rows(data, 'decisions', ('question', 'options', 'selected', 'rationale', 'status', 'evidence_refs')):
            state(decision['status'], {'proposed', 'decided', 'blocked'}, 'decision status')
            if decision['status'] == 'decided' and not all(decision[k] for k in ('selected', 'rationale', 'evidence_refs')):
                raise ValueError('Decided architecture choice needs rationale and evidence')
        covered = {r for component in components for r in component['requirement_ids']}
        if not set(scope) <= covered or not covered <= reqs:
            raise ValueError('Solution components do not cover the declared requirements')
    elif kind == 'ui_design':
        pages = rows(data, 'pages', ('title', 'requirement_ids', 'states'))
        fields = rows(data, 'fields', ('page_id', 'type', 'length', 'precision', 'unit', 'required', 'default',
                                     'enum', 'validation', 'source', 'sensitivity'))
        permissions = rows(data, 'permissions', ('page_id', 'field_ids', 'role', 'action', 'condition', 'effect'))
        states = rows(data, 'states', ('page_id', 'from', 'action', 'to', 'allowed_roles', 'error'))
        page_ids, field_ids = {x['id'] for x in pages}, {x['id'] for x in fields}
        if any(x['page_id'] not in page_ids for x in fields + permissions + states):
            raise ValueError('UI detail references an unknown page')
        if any(not set(x['field_ids']) <= field_ids for x in permissions):
            raise ValueError('Permission references an unknown field')
        for permission in permissions:
            state(permission['effect'], {'allow', 'deny'}, 'permission effect')
            if any(x['page_id'] != permission['page_id'] for x in fields if x['id'] in permission['field_ids']):
                raise ValueError('Permission field belongs to a different page')
        for transition in states:
            page = next(x for x in pages if x['id'] == transition['page_id'])
            if transition['from'] not in page['states'] or transition['to'] not in page['states'] or not transition['allowed_roles']:
                raise ValueError('UI transition needs known states and allowed roles')
        covered = {r for page in pages for r in page['requirement_ids']}
        if not set(scope) <= covered or not covered <= reqs:
            raise ValueError('UI pages do not cover the declared requirements')
        if value['status'] == 'ready' and (not fields or not permissions or not states):
            raise ValueError('Ready UI needs fields, permissions and state transitions')
    elif kind == 'integration':
        interfaces = rows(data, 'interfaces', ('owner', 'source_system', 'target_system', 'direction', 'trigger',
                            'protocol', 'auth_method', 'environment', 'status', 'idempotency', 'timeout', 'retry', 'compensation'))
        interface_ids = {x['id'] for x in interfaces}
        mappings = rows(data, 'mappings', ('interface_id', 'source_field', 'target_field', 'type', 'unit', 'transform', 'business_key'))
        reconciliations = rows(data, 'reconciliations', ('interface_id', 'state', 'build_ref', 'environment', 'counts', 'business_keys', 'evidence_refs'))
        if any(x['interface_id'] not in interface_ids for x in mappings + reconciliations):
            raise ValueError('Mapping/reconciliation references an unknown interface')
        for interface in interfaces:
            state(interface['status'], {'unknown', 'blocked', 'designed', 'verified'}, 'interface status')
            if not any(x['interface_id'] == interface['id'] for x in mappings):
                raise ValueError('Interface needs a field mapping')
            if interface['status'] == 'verified' and not any(x['interface_id'] == interface['id'] and x['state'] == 'pass' for x in reconciliations):
                raise ValueError('Verified interface needs a passing business reconciliation')
        for item in reconciliations:
            state(item['state'], {'not_run', 'pass', 'fail'}, 'reconciliation state')
            if item['state'] != 'not_run':
                build(item['build_ref'])
                if not all(item[k] for k in ('environment', 'counts', 'business_keys', 'evidence_refs')):
                    raise ValueError('Executed reconciliation needs environment, count/key results and evidence')
            if item['state'] == 'pass' and any(x.get('state') != 'pass' for x in item['counts'] + item['business_keys']):
                raise ValueError('Passing reconciliation cannot contain failed/unchecked counts or keys')
            if item['state'] == 'pass':
                interface = next(x for x in interfaces if x['id'] == item['interface_id'])
                if item['environment'] != interface['environment']:
                    raise ValueError('Reconciliation environment differs from interface environment')
                for result in item['counts'] + item['business_keys']:
                    require(result, ('expected', 'actual'), 'reconciliation result')
                    if result['expected'] != result['actual']:
                        raise ValueError('Passing reconciliation has unequal expected/actual values')
        migration = data['migration']
        require(migration, ('applicable',), 'migration')
        if not isinstance(migration['applicable'], bool):
            raise ValueError('migration.applicable must be boolean')
        if migration['applicable']:
            require(migration, ('owner', 'state', 'backup_refs', 'rollback_plan', 'freeze_window', 'rehearsal_refs', 'reconciliation_refs'), 'migration')
            state(migration['state'], {'planned', 'rehearsed', 'completed', 'failed'}, 'migration state')
            if migration['state'] in {'rehearsed', 'completed'} and not all(migration[k] for k in ('owner', 'backup_refs', 'rollback_plan', 'freeze_window', 'rehearsal_refs', 'reconciliation_refs')):
                raise ValueError('Migration completion needs backup, rehearsal and reconciliation evidence')
        elif not migration.get('reason'):
            raise ValueError('Inapplicable migration needs a reason')
    elif kind == 'work_package':
        plans = [obj for obj in upstream if obj['kind'] == 'plan']
        if not any(x['id'] == data['plan_work_package_id'] and set(scope) <= set(x['requirement_ids'])
                   for obj in plans for x in obj['data']['work_packages']):
            raise ValueError('Work package is not mapped to its pinned plan scope')
        designs = [obj for obj in upstream if obj['kind'] in {'solution', 'ui_design', 'integration', 'blueprint'}]
        design_keys = {(obj['artifact_id'], obj['revision']) for obj in designs}
        if not data['design_refs'] or any((ref['artifact_id'], ref['revision']) not in design_keys for ref in data['design_refs']):
            raise ValueError('Work package needs pinned design artifacts')
        if not data['completion_rule']:
            raise ValueError('Work package needs a completion rule')
        if data['build_ref'] is not None:
            build(data['build_ref'])
        if data.get('state', 'planned') == 'completed' and (data['build_ref'] is None or not data['evidence_refs']):
            raise ValueError('Completed work package needs exact build and actual evidence')
        state(data.get('state', 'planned'), {'planned', 'in_progress', 'completed', 'blocked'}, 'work package state')
    elif kind == 'testing':
        build(data['build_ref'])
        if not data['environment']:
            raise ValueError('Testing needs an environment')
        cases = rows(data, 'cases', ('requirement_ids', 'steps', 'expected', 'actual', 'state', 'evidence_refs'))
        for case in cases:
            if not case['requirement_ids'] or not set(case['requirement_ids']) <= set(scope):
                raise ValueError('Test case references a requirement outside test scope')
            state(case['state'], {'not_run', 'pass', 'fail', 'blocked'}, 'test case state')
            if case['state'] in {'pass', 'fail'} and not all(case[k] for k in ('steps', 'expected', 'actual', 'evidence_refs')):
                raise ValueError('Executed test needs steps, expected/actual results and evidence')
        defects = rows(data, 'defects', ('case_id', 'severity', 'state', 'owner', 'retest_case_id', 'retest_refs'))
        case_map = {x['id']: x for x in cases}
        for defect in defects:
            state(defect['severity'], {'blocking', 'major', 'minor'}, 'defect severity')
            state(defect['state'], {'open', 'fixed', 'closed'}, 'defect state')
            if defect['case_id'] not in case_map or not defect['owner']:
                raise ValueError('Defect needs known case and owner')
            if defect['state'] == 'closed' and (case_map.get(defect['retest_case_id'], {}).get('state') != 'pass' or not defect['retest_refs']):
                raise ValueError('Closed defect needs passing retest on this build and evidence')
        uat = data['uat']
        require(uat, ('state', 'scope_requirement_ids', 'actor', 'role', 'origin', 'evidence_refs', 'open_items'), 'uat')
        state(uat['state'], {'pending', 'accepted', 'conditional', 'rejected'}, 'UAT state')
        if not set(uat['scope_requirement_ids']) <= set(scope):
            raise ValueError('UAT scope is outside tested requirements')
        if uat['state'] != 'pending':
            state(uat['origin'], {'actual', 'simulation'}, 'UAT origin')
            if uat['origin'] == 'simulation' and purpose != 'simulation':
                raise ValueError('Simulated UAT is invalid in a real project')
            if not all(uat[k] for k in ('actor', 'role', 'evidence_refs', 'scope_requirement_ids')):
                raise ValueError('UAT decision needs actor, scope and evidence')
        if uat['state'] == 'accepted' and (uat['open_items'] or set(uat['scope_requirement_ids']) != set(scope)):
            raise ValueError('Accepted UAT cannot hide open items or partial scope')
    elif kind == 'release':
        build(data['build_ref'])
        tests = [obj for obj in upstream if obj['artifact_id'] == data['testing_ref']['artifact_id'] and obj['revision'] == data['testing_ref']['revision']]
        if not tests or tests[0]['kind'] != 'testing' or tests[0]['data']['build_ref'] != data['build_ref']:
            raise ValueError('Release testing_ref must test this exact build')
        for item in rows(data, 'readiness', ('title', 'state', 'owner', 'evidence_refs')):
            state(item['state'], {'pass', 'fail', 'not_checked'}, 'readiness state')
            if item['state'] == 'pass' and (not item['owner'] or not item['evidence_refs']):
                raise ValueError('Passing readiness check needs owner and evidence')
        execution, rollback = data['execution'], data['rollback']
        require(execution, ('state', 'evidence_refs', 'verification_refs'), 'release execution')
        require(rollback, ('state', 'plan', 'evidence_refs', 'restore_refs'), 'rollback')
        state(execution['state'], {'planned', 'succeeded', 'failed', 'rolled_back'}, 'release execution')
        state(rollback['state'], {'planned', 'not_needed', 'succeeded', 'failed'}, 'rollback')
        if not data['environment'] or not rollback['plan']:
            raise ValueError('Release needs environment and actionable rollback plan')
        if execution['state'] != 'planned' and not execution['evidence_refs']:
            raise ValueError('Actual execution needs evidence')
        if execution['state'] == 'succeeded' and (not execution['verification_refs'] or rollback['state'] != 'not_needed'):
            raise ValueError('Successful release needs business verification and no rollback')
        if rollback['state'] == 'succeeded' and (not rollback['evidence_refs'] or not rollback['restore_refs']):
            raise ValueError('Successful rollback needs action and restoration evidence')
        if execution['state'] == 'rolled_back' and rollback['state'] != 'succeeded':
            raise ValueError('Rolled-back release needs successful rollback')
    elif kind == 'handover':
        audiences = rows(data, 'audiences', ('role', 'owner'))
        if any(not x['role'] or not x['owner'] for x in audiences):
            raise ValueError('Training audience needs role and responsible owner')
        training = rows(data, 'training', ('audience_id', 'attendance', 'competency', 'evidence_refs'))
        if any(x['audience_id'] not in {a['id'] for a in audiences} for x in training):
            raise ValueError('Training references unknown audience')
        for item in training:
            state(item['competency'], {'not_checked', 'pass', 'fail'}, 'competency')
            if item['competency'] == 'pass' and not item['evidence_refs']:
                raise ValueError('Competency pass needs assessment evidence')
        operations = data['operations']
        require(operations, ('owner', 'state', 'runbook_refs', 'receipt_refs'), 'operations')
        state(operations['state'], {'pending', 'accepted', 'conditional', 'rejected'}, 'operations state')
        if operations['state'] == 'accepted' and not all(operations[k] for k in ('owner', 'runbook_refs', 'receipt_refs')):
            raise ValueError('Operations acceptance needs owner, runbook and receipt')
        for item in rows(data, 'assets', ('owner', 'version', 'evidence_refs')):
            if not all(item[k] for k in ('owner', 'version', 'evidence_refs')):
                raise ValueError('Handover asset needs owner, version and evidence')


def gate(value):
    """Completion checks on bound records, not proof of evidence authenticity."""
    kind, data = value['kind'], value['data']
    reasons = []
    if value['status'] != 'ready':
        reasons.append('Artifact is not ready')
    if kind == 'solution':
        if any(x['status'] != 'decided' for x in data['decisions']):
            reasons.append('Architecture decisions remain unresolved')
    elif kind == 'ui_design':
        for page in data['pages']:
            exceptions = data.get('not_applicable', {}).get(page['id'], {})
            for group in ('fields', 'permissions', 'states'):
                if not any(x['page_id'] == page['id'] for x in data[group]):
                    reason = exceptions.get(group)
                    if not isinstance(reason, str) or not reason.strip():
                        reasons.append(f'Page {page["id"]} lacks {group} detail or applicability reason')
    elif kind == 'integration':
        if not data['interfaces'] or any(x['status'] != 'verified' for x in data['interfaces']):
            reasons.append('Interfaces are not business-verified')
        for interface in data['interfaces']:
            records = [x for x in data['reconciliations'] if x['interface_id'] == interface['id']]
            builds = {(x['build_ref']['repository'], x['build_ref']['revision'], x['build_ref']['sha256'])
                      for x in records if x['state'] != 'not_run'}
            if (not records or any(x['state'] != 'pass' or x['environment'] != interface['environment'] for x in records)
                    or len(builds) != 1):
                reasons.append(f'Interface {interface["id"]} has failed/unexecuted or mixed-build reconciliations')
        migration = data['migration']
        if migration['applicable'] and migration['state'] != 'completed':
            reasons.append('Migration is not complete')
    elif kind == 'work_package':
        if data.get('state') != 'completed':
            reasons.append('Work package is not completed')
    elif kind == 'testing':
        cases = data['cases']
        covered = {r for case in cases if case['state'] == 'pass' for r in case['requirement_ids']}
        if not cases or any(x['state'] != 'pass' for x in cases) or not set(data['requirement_ids']) <= covered:
            reasons.append('Test scope has failed, unexecuted or uncovered cases')
        if any(x['state'] != 'closed' for x in data['defects']):
            reasons.append('Defects remain unresolved; residual acceptance requires explicit review')
        if data['uat']['state'] != 'accepted':
            reasons.append('UAT is pending, conditional or rejected')
    elif kind == 'release':
        if not readiness_passed(data):
            reasons.append('Readiness checks incomplete')
        if data['execution']['state'] != 'succeeded':
            reasons.append('Release did not succeed; a restored rollback is not a delivered release')
    elif kind == 'handover':
        if not data['audiences'] or any(not any(x['audience_id'] == a['id'] and x['competency'] == 'pass' for x in data['training']) for a in data['audiences']):
            reasons.append('Attendance does not establish competency for every audience')
        if data['operations']['state'] != 'accepted' or not data['assets'] or data['open_items']:
            reasons.append('Operations/assets/open items prevent complete handover')
    return {'ready': not reasons, 'reasons': reasons}


def readiness_passed(data):
    return (READINESS_IDS <= {x['id'] for x in data['readiness']}
            and all(x['state'] == 'pass' for x in data['readiness']))
