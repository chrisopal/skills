from datetime import date, timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from opportunity_skill.gtm import GTMStore, search_brief
from opportunity_skill.pipeline import run_analyze, run_manage
from opportunity_skill.workbench import make_server


class GTMTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / 'opportunity.db'
        self.store = GTMStore(self.db)
        self.seq = 0
        self.today = date.today().isoformat()
        self.write([{'type': 'create_campaign', 'name': '质检推广', 'product': '视觉质检', 'target_customer': '汽车零件工厂', 'regions': ['上海'], 'owner': '推广负责人', 'simulation': True},
                    {'type': 'upsert_source', 'record': {'id': 'S1', 'title': '企业官网', 'url': 'https://example.org/company', 'publisher': '企业', 'accessed_on': self.today, 'claim': '公开业务资料', 'verification': 'official'}},
                    self.target()])

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def target(self, tid='T1', name='星河制造'):
        return {'type': 'upsert_target', 'record': {'id': tid, 'name': name, 'region': '上海', 'city': '上海', 'industry': '制造', 'source_ids': ['S1'], 'fit_reason': '行业交集，痛点未知', 'fit': {'industry': 4, 'pain': None, 'access': None, 'evidence': 3}, 'location': {'lon': 121.47, 'lat': 31.23, 'precision': 'city'}}}

    def touch(self, tid='F1', outcome='qualified', **extra):
        return {'type': 'record_touch', 'record': {'id': tid, 'target_id': 'T1', 'channel': '技术交流', 'occurred_on': self.today, 'outcome': outcome, 'summary': '模拟讨论样件评估', 'evidence': '模拟会议纪要', 'next_action': '补充样本', 'owner': '顾宁', **extra}}

    def write(self, operations, **override):
        self.seq += 1
        changes = {'campaign_id': 'C1', 'request_id': 'REQ-' + str(self.seq), 'actor': '测试负责人', 'expected_revision': self.store._load('C1')['revision'] if self.seq > 1 else 0, 'operations': operations, **override}
        return self.store.manage(changes)

    def test_brief_uses_actual_product_icp_and_missing_inputs(self):
        brief = search_brief({'product': '视觉质检', 'target_customer': '冲压件制造', 'regions': ['苏州', '宁波']})
        self.assertEqual(len(brief['queries']), 6)
        self.assertTrue(all('冲压件制造' in q['query'] and '视觉质检' in q['query'] for q in brief['queries']))
        self.assertEqual(len(search_brief({})['missing_inputs']), 3)

    def test_atomic_rejection_does_not_save_prior_operations(self):
        before = self.store.detail('C1')
        with self.assertRaisesRegex(ValueError, '未找到'):
            self.write([self.touch(), {'type': 'upsert_target', 'record': {**self.target()['record'], 'source_ids': ['OTHER-CAMPAIGN']}}])
        after = self.store.detail('C1')
        self.assertEqual(after, before)

    def test_revision_conflict_and_idempotence_return_live_detail(self):
        op = {'campaign_id': 'C1', 'request_id': 'ONCE', 'expected_revision': 1, 'actor': 'A', 'operations': [self.touch()]}
        self.store.manage(op)
        self.write([self.touch('F2', 'responded')])
        replay = self.store.manage(op)
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(replay['receipt_revision'], 2)
        self.assertEqual(replay['revision'], 3)
        self.assertEqual(len(replay['detail']['touches']), 2)
        with self.assertRaisesRegex(ValueError, 'revision conflict'):
            self.write([self.touch('F3')], expected_revision=1)
        with self.assertRaises(ValueError):
            self.store.manage({**op, 'actor': 'other'})

    def test_duplicate_enterprise_and_touch_do_not_inflate_funnel(self):
        with self.assertRaisesRegex(ValueError, '同名企业'):
            self.write([self.target('T2', ' 星河制造 ')])
        self.write([self.touch(), self.touch('F2'), self.touch('F3', 'no_fit')])
        result = self.store.detail('C1')
        self.assertEqual(result['analytics']['funnel']['qualified'], 1)
        self.assertEqual(result['targets'][0]['status'], 'no_fit')
        with self.assertRaisesRegex(ValueError, '历史跟进不可覆盖'):
            self.write([self.touch()])

    def test_planned_future_and_missing_cost_are_not_actual_zero(self):
        future = (date.today() + timedelta(days=2)).isoformat()
        self.write([self.touch('P', 'planned', evidence=''), self.touch('F', 'qualified', occurred_on=future), self.touch('A', 'contacted')])
        result = self.store.detail('C1')['analytics']
        self.assertEqual(result['funnel']['contacted'], 1)
        self.assertEqual(result['funnel']['qualified'], 0)
        self.assertEqual(result['costs'], {})
        self.assertEqual(result['missing_cost_count'], 1)
        future_result = self.store.detail('C1', future)['analytics']
        self.assertEqual(future_result['funnel']['qualified'], 0)
        with self.assertRaisesRegex(ValueError, '计划跟进'):
            self.write([self.touch('P2', 'planned', actual_cost=0, currency='CNY')])

    def test_mixed_currency_costs_and_event_attribution(self):
        self.write([{'type': 'upsert_event', 'record': {'id': 'E1', 'name': '论坛', 'kind': 'forum', 'region': '上海', 'city': '上海', 'source_ids': ['S1'], 'fit_reason': '技术主题相符'}}])
        self.write([self.touch('F1', actual_cost=100, currency='CNY', event_id='E1'), self.touch('F2', actual_cost=20, currency='USD', event_id='E1')])
        analytics = self.store.detail('C1')['analytics']
        self.assertEqual(analytics['costs'], {'CNY': 100, 'USD': 20})
        self.assertEqual(analytics['events'][0]['targets'], 1)
        self.assertEqual(analytics['events'][0]['qualified'], 1)
        self.assertEqual(analytics['signed_amounts'], {})

    def test_dates_locations_urls_and_scores_reject_invalid_values(self):
        invalid = []
        target = self.target()
        target['record']['location']['lat'] = 91
        invalid.append(target)
        target = self.target()
        target['record']['fit']['pain'] = True
        invalid.append(target)
        invalid.append(self.touch('bad', actual_cost=float('nan'), currency='CNY'))
        invalid.append(self.touch('bad', occurred_on='2026-02-30'))
        invalid.append({'type': 'upsert_source', 'record': {'id': 'X', 'title': 'X', 'url': 'javascript:alert(1)', 'publisher': 'X', 'accessed_on': self.today, 'claim': 'X', 'verification': 'official'}})
        for op in invalid:
            with self.subTest(op=op), self.assertRaises(ValueError):
                self.write([op])
        self.assertIsNone(self.store.detail('C1')['targets'][0]['fit_score'])
        self.assertEqual(self.store.detail('C1')['targets'][0]['fit_coverage'], .5)

    def test_events_past_unknown_upcoming_and_unknown_coordinate(self):
        base = {'name': '活动', 'kind': 'exhibition', 'region': '上海', 'city': '上海', 'source_ids': ['S1'], 'fit_reason': '待核实'}
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.write([{'type': 'upsert_event', 'record': dict(base, id='past', starts_on=yesterday, ends_on=yesterday)}, {'type': 'upsert_event', 'record': dict(base, id='future', starts_on=tomorrow, ends_on=tomorrow)}, {'type': 'upsert_event', 'record': dict(base, id='unknown')}])
        self.assertEqual([e['timing'] for e in self.store.detail('C1')['events']], ['past', 'upcoming', 'unknown'])
        target = self.target(); del target['record']['location']
        self.write([target])
        self.assertEqual(self.store.detail('C1')['analytics']['unmapped_targets'], 1)

    def test_link_requires_qualified_same_company_and_reads_live_lifecycle(self):
        saved = run_analyze({'request_id': 'GTM-OPP', 'materials': [{'evidence_id': 'EV-GTM', 'content': '星河制造需要 MES 集成，联系人：王敏，业务负责人。'}]}, self.db)
        oid = saved['storage_result']['opportunity_id']
        adapter_detail = self.store.adapter.get_opportunity_detail(oid)
        record = self.target()['record']; record['name'] = adapter_detail['account']['company_name']
        # Seed name has same normalized enterprise identity; no fuzzy group merge.
        if record['name'] != '星河制造':
            self.write([self.target('T-OTHER', record['name'])])
            tid = 'T-OTHER'
        else:
            tid = 'T1'
        link = {'type': 'link_opportunity', 'target_id': tid, 'opportunity_id': oid, 'touch_id': 'F1'}
        with self.assertRaises(ValueError):
            self.write([link])
        self.write([self.touch('F1', target_id=tid)])
        self.write([link])
        self.assertEqual(self.store.detail('C1')['analytics']['funnel']['opportunities'], 1)
        lc = self.store.adapter.get_lifecycle(oid)
        run_manage(self.db, {'request_id': 'GTM-PAUSE', 'actor': '销售', 'opportunity_id': oid, 'expected_revision': lc['revision'], 'operations': [{'type': 'set_status', 'status': 'paused', 'reason': '模拟客户延期', 'evidence': ['EV-GTM']}]})
        result = self.store.detail('C1')['links'][0]['opportunity']
        self.assertEqual(result['status'], 'paused')
        self.assertEqual(result['signed_amounts'], [])
        with self.assertRaisesRegex(ValueError, '已有来源关联'):
            self.write([link])
        self.write([self.target('T-WRONG', '另一企业'), self.touch('F-WRONG', target_id='T-WRONG')])
        with self.assertRaisesRegex(ValueError, '企业不一致'):
            self.write([{**link, 'target_id': 'T-WRONG', 'touch_id': 'F-WRONG'}])
        before = self.store.detail('C1', (date.today() - timedelta(days=1)).isoformat())
        self.assertEqual(before['analytics']['funnel']['opportunities'], 0)

    def test_signed_enterprise_metric_requires_effective_signature(self):
        from opportunity_skill.gtm import _analytics
        state = self.store.detail('C1')
        link = {'target_id': 'T1', 'opportunity_id': 'OPP', 'opportunity': {'status': 'won', 'signed_amounts': []}}
        result = _analytics(state, [], [link])
        self.assertEqual(result['funnel']['won'], 0)
        self.assertEqual(result['regions'][0]['won'], 0)
        link['opportunity']['signed_amounts'] = [{'currency': 'CNY', 'amount': 100}]
        result = _analytics(state, [], [link])
        self.assertEqual(result['funnel']['won'], 1)
        self.assertEqual(result['signed_amounts'], {'CNY': 100})

    def test_javascript_city_aggregation_preserves_coordinates_and_selection_items(self):
        source = Path(__file__).resolve().parents[1] / 'display/workbench/gtm.js'
        script = """const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
const context={window:{},document:{}};vm.createContext(context);
vm.runInContext(source.slice(0,source.indexOf('  async function api'))+'})();',context);
const logic=context.window.GTMLogic;
const items=[{name:'A',location:{lon:120,lat:31},city:'苏州'}, {name:'B',location:{lon:120,lat:31},city:'苏州'}, {name:'C',location:{lon:121,lat:30},city:'宁波'}, {name:'unknown'}];
const groups=logic.groupPoints(items);
assert.equal(groups.length,2);assert.equal(groups[0].items.length,2);
assert.equal(groups[0].location.lon,120);assert.equal(groups[0].items[1].name,'B');
assert.equal(logic.fitLabel({fit_score:76}),'适配 76.0 / 100');
assert.equal(logic.hasLocation(items[3]),false);
"""
        result = subprocess.run(['node', '-e', script, str(source)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_china_geography_provinces_city_coverage_and_business_filter(self):
        assets = Path(__file__).resolve().parents[1] / 'display/workbench'
        data = json.loads((assets / 'china-map.json').read_text())
        self.assertEqual(len([f for f in data['features'] if f['name']]), 34)
        self.assertTrue(any(f['code'] == '100000_JD' for f in data['features']))
        self.assertEqual(len(data['cities']['320000']), 13)
        self.assertEqual(len(data['cities']['330000']), 11)
        self.assertEqual(len(data['cities']['710000']), 0)
        self.assertEqual(sum(len(v) for v in data['cities'].values()), 475)
        script = """const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={window:{}};vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
const m=context.window.GTMMap,d=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const target={city:'苏州',region:'苏州',location:{lon:120.5853,lat:31.2989}};
assert.equal(m.provinceOf(target,d),'320000');
assert(m.fits(target,'320000','320500',d));assert(!m.fits(target,'330000','',d));
assert.equal(m.provinceOf({city:'上海',region:'上海'},d),'310000');
const project=m.projection([72,16,137,55],{x:0,y:0,w:960,h:620});
assert(project([120,31]).every(Number.isFinite));assert(m.path(d.features[0].geometry,project).startsWith('M'));
"""
        result = subprocess.run(['node', '-e', script, str(assets / 'gtm-map.js'), str(assets / 'china-map.json')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_handoff_unknown_budget_and_negative_quote_do_not_promote_suggestion(self):
        from opportunity_skill.stage_management import infer_opportunity_stage
        from opportunity_skill.stages.opportunity_analysis import extract_budget_signal
        raw = '具体工序、节拍、缺陷判定、样本覆盖、预算、采购路径、责任人、准确率和现有供应商均未知。没有签署、报价或已验证效果。'
        self.assertEqual(extract_budget_signal(raw), ('预算信息未明确', None))
        stage = infer_opportunity_stage({'text': raw, 'core_need': '客户需求待进一步澄清'})
        self.assertNotEqual(stage['stage_id'], 'proposal_bidding')
        self.assertFalse(stage['opportunity_confirmed'])
        self.assertEqual(extract_budget_signal('预算未提供。后续预算已批100万元。'), ('存在预算/立项信号', '100万元'))
        self.assertEqual(infer_opportunity_stage({'text': '已提交报价', 'core_need': '质检'})['stage_id'], 'proposal_bidding')

    def test_cli_actual_write_read_and_brief(self):
        run = Path(__file__).resolve().parents[2] / 'opportunity-orchestrator/scripts/run.py'
        brief = self.root / 'brief.json'; brief.write_text(json.dumps({'product': '检测', 'target_customer': '零件厂', 'regions': ['苏州']}))
        result = subprocess.run([sys.executable, str(run), 'gtm-brief', '--input', str(brief)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['queries']), 3)
        result = subprocess.run([sys.executable, str(run), 'gtm-query', '--db', str(self.db), '--campaign-id', 'C1'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['revision'], 1)
        invalid = self.root / 'invalid.json'
        invalid.write_text(json.dumps({'campaign_id': 'C1', 'request_id': 'BAD-LOCATION', 'actor': '测试', 'expected_revision': 1, 'operations': [{'type': 'upsert_target', 'record': {**self.target()['record'], 'location': '上海展馆'}}]}))
        result = subprocess.run([sys.executable, str(run), 'gtm-manage', '--input', str(invalid), '--db', str(self.db)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)
        self.assertIn('坐标', result.stderr)


class GTMHTTPTests(unittest.TestCase):
    def test_http_reuses_session_security_and_saves_revision(self):
        with tempfile.TemporaryDirectory() as temp:
            server = make_server(Path(temp) / 'test.db', port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            data = {'campaign_id': 'WEB', 'request_id': 'WEB-NEW', 'actor': '工作台', 'expected_revision': 0, 'operations': [{'type': 'create_campaign', 'name': '新推广', 'product': '检测', 'target_customer': '制造业', 'regions': ['苏州'], 'owner': '顾宁', 'simulation': True}]}
            try:
                def post(origin, token, payload=data):
                    return urlopen(Request(base + '/api/gtm/manage', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json', 'Origin': origin, 'X-Workbench-Token': token}))
                for origin, token in [('https://evil.example', server.session_token), (base, 'bad')]:
                    with self.assertRaises(HTTPError) as err: post(origin, token)
                    self.assertEqual(err.exception.code, 403)
                self.assertEqual(json.load(post(base, server.session_token))['detail']['revision'], 1)
                self.assertEqual(json.load(urlopen(base + '/api/gtm/campaign/WEB'))['detail']['campaign']['product'], '检测')
                geography = json.load(urlopen(base + '/assets/china-map.json'))
                self.assertEqual(len(geography['features']), 35)
                self.assertIn(b'GTMMap', urlopen(base + '/assets/gtm-map.js').read())
                with self.assertRaises(HTTPError) as err:
                    post(base, server.session_token, {**data, 'request_id': 'WEB-STALE'})
                self.assertEqual(err.exception.code, 409)
                # A browser never grants arbitrary local-file access.
                with self.assertRaises(HTTPError) as err:
                    post(base, server.session_token, {**data, 'path': '/tmp/private'})
                self.assertEqual(err.exception.code, 400)
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
