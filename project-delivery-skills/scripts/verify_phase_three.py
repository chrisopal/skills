#!/usr/bin/env python3
"""Rehearse third-batch local files with explicitly synthetic business evidence."""
import argparse
import importlib.util
import json
from pathlib import Path


def run(out):
    out = Path(out).absolute()
    out.mkdir(parents=True, exist_ok=False)
    script = Path(__file__).resolve().parents[1] / 'skills/delivery-orchestrator/scripts/runtime.py'
    spec = importlib.util.spec_from_file_location('phase_three_runtime', script)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    project = out / 'project'
    runtime.init_project(project, 'DEMO-CLOSURE', purpose='simulation')
    today = runtime.now()[:10]

    def source(aid, data):
        path = out / (aid + '.json')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return runtime.source(project, path, aid)

    def register(aid, kind, data, inputs, revision=1):
        return runtime.register(project, dict(project_id='DEMO-CLOSURE', artifact_id=aid, revision=revision,
            kind=kind, visibility='internal', status='ready', inputs=inputs, data=data))

    basis = source('SRC-BASIS', {'origin': 'simulation', 'text': '模拟合同：交付固定费用100000元；支持服务按小时计费；质保到2099年，行政收尾后仍保留服务义务。'})
    contract = register('CONTRACT', 'contract', dict(obligations=[dict(id='O1', statement='保留质保服务',
        source_id='SRC-BASIS', locator='/text', acceptance='到期且遗留事项清零')], scope_in=['工单系统'],
        scope_out=['实际生产执行'], customer_dependencies=['客户模拟输入']), [basis])
    decision = register('MINUTES', 'minutes', dict(meeting_date=today, participants=['模拟项目经理', '模拟接收人'],
        decisions=['演练行政收尾与质保责任移交'], actions=[], open_items=[]), [basis])
    register('PROFILE', 'profile', dict(billing_mode='mixed', delivery_mode='mixed', streams=[
        dict(id='FIXED', mode='fixed', scope_ids=['implementation'], currency='CNY', amount=100000,
             hours=None, rate=None, cap=None, basis='模拟合同固定范围', terms_refs=[contract]),
        dict(id='TIME', mode='time', scope_ids=['support'], currency='CNY', amount=None,
             hours=20, rate=500, cap=8000, basis='模拟合同支持工时上限', terms_refs=[contract])],
        terms_refs=[contract], open_items=[]), [contract])
    form = source('FORM', {'fields': [dict(id='task_name', type='string', required=True),
                                     dict(id='owner', type='string', required=True)]})
    task = source('TASK', {'title': '质保工单跟进', 'owner': '模拟支持负责人'})
    mapping = register('MAPPING', 'template_mapping', dict(form_ref=form, audience='internal', mappings=[
        dict(id='M1', target_field='task_name', source_ref=task, source_pointer='/title', transform='identity'),
        dict(id='M2', target_field='owner', source_ref=task, source_pointer='/owner', transform='identity')], omissions=[]), [form, task])
    identities = dict(operation_id='OP-DEMO-1', system='local-fixture', entity='task', direction='outbound',
                      record_id='WARRANTY-1', external_id='DEMO-TASK-1')
    exchange_data = dict(identities, mapping_ref=mapping, state='prepared', receipt_ref=None, conflicts=[])
    register('EXCHANGE', 'exchange', exchange_data, [mapping])
    runtime.prepare_mapped(project, 'EXCHANGE', out / 'exchange-candidate.json')
    before = runtime.snapshot(project)['gates']['EXCHANGE']
    payload = json.loads((out / 'exchange-candidate.json').read_text())
    receipt = source('RECEIPT', dict(identities, payload_sha256=payload['payload_sha256'], state='applied', origin='simulation'))
    register('EXCHANGE', 'exchange', dict(exchange_data, state='reconciled', receipt_ref=receipt), [mapping, receipt], revision=2)
    closure = register('CLOSURE', 'closure', dict(origin='simulation', as_of=today,
        obligations=[dict(id='O1', title='质保服务义务', category='service', owner='模拟项目经理', state='transferred',
            due_date='2099-12-31', evidence_refs=[basis], recipient='模拟支持负责人', receipt_refs=[decision])],
        warranty=dict(applicable=True, reason='模拟合同质保条款', owner='模拟支持负责人', start_date=today,
            end_date='2099-12-31', terms_refs=[contract], transfer_refs=[decision], items=[]),
        administration=dict(state='closed', decision_refs=[decision]), settlement=dict(state='reconciled', evidence_refs=[basis]),
        resources=[dict(id='TEAM', owner='模拟项目经理', state='released', reason='转交支持团队', evidence_refs=[decision])],
        archive=[dict(id='A1', artifact_ref=contract, owner='模拟档案员', classification='合同', retention_until='2099-12-31')],
        lessons=[dict(id='L1', observation='行政关闭与质保责任分开核验', action='保留质保主账', owner='模拟项目经理')]), [contract, decision])
    snap = runtime.snapshot(project)
    closure_gate = snap['gates']['CLOSURE']
    assert closure_gate['administrative_closed'] and closure_gate['warranty_transferred']
    assert not closure_gate['warranty_ended'] and not closure_gate['fully_discharged']
    assert not before['ready'] and snap['gates']['EXCHANGE']['ready']
    assert snap['gates']['PROFILE']['billing']['estimates_by_currency'] == {'CNY': '108000.00'}
    validation = runtime.validate(project)
    assert validation['ok'] and validation['effective_ok']
    portfolio_projects = []
    for pid, currency, hours, cost in (('PORT-A', 'CNY', 24, 300), ('PORT-B', 'USD', 20, 100)):
        location = out / pid
        runtime.init_project(location, pid, purpose='simulation', currency=currency)
        ref = runtime.source(location, out / 'SRC-BASIS.json', 'SRC')
        for aid, kind, data in (
            ('HOURS', 'timesheets', dict(items=[], remaining_labor=0, allocations=[dict(
                id='AL1', person='DEV', period=today, work_package_id='WP1', planned_hours=hours)])),
            ('COST', 'costs', dict(currency=currency, budget=1000, other_remaining=0, items=[dict(
                id='C1', category='other', work_package_id='WP1', state='incurred', amount=cost,
                basis='显式模拟费用', payment_status='unpaid')]))):
            runtime.register(location, dict(project_id=pid, artifact_id=aid, revision=1, kind=kind,
                visibility='internal', status='ready', inputs=[ref], data=data))
        portfolio_projects.append(location)
    portfolio = runtime.reuse.portfolio(portfolio_projects, today, runtime,
        identity_map={'PORT-A': {'DEV': 'DEV-GLOBAL'}, 'PORT-B': {'DEV': 'DEV-GLOBAL'}},
        capacities=[dict(person='DEV-GLOBAL', period=today, available_hours=40)])
    assert portfolio['forecast_by_currency'] == {'CNY': '300.00', 'USD': '100.00'}
    assert portfolio['resource_load'][0]['planned_hours'] == '44'
    assert portfolio['resource_load'][0]['overloaded'] is True
    report = dict(purpose='simulation', validation=validation, source_refs=[closure],
        closure_gate=closure_gate, exchange_before=before, exchange_after=snap['gates']['EXCHANGE'],
        mapped_payload=payload['payload'], actual_network_dispatch=False, customer_acceptance=False,
        profile=snap['gates']['PROFILE'], portfolio=portfolio, project=str(project))
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    print(json.dumps(run(parser.parse_args().out), ensure_ascii=False, indent=2))
