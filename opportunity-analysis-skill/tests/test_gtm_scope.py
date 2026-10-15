"""Keep the browser's filtered projection consistent with canonical GTM metrics."""
from datetime import date, timedelta
import json
from pathlib import Path
import subprocess
import unittest

from opportunity_skill.gtm import _analytics


class GTMScopeTests(unittest.TestCase):
    def test_regional_projection_matches_canonical_metrics_and_geography(self):
        today = date.today().isoformat()
        future = (date.today() + timedelta(days=1)).isoformat()
        targets = [dict(id='A', name='苏州客户', region='江苏', city='苏州'),
                   dict(id='B', name='宁波客户', region='浙江', city='宁波'),
                   dict(id='C', name='上海客户', region='上海', city='上海')]
        events = [dict(id='E', kind='exhibition', name='上海展会', region='上海', city='上海'),
                  dict(id='F', kind='forum', name='广州论坛', region='广东', city='广州')]
        touches = [dict(target_id='A', event_id='E', occurred_on=today, outcome='qualified', channel='展会', actual_cost=100, currency='CNY'),
                   dict(target_id='A', event_id='E', occurred_on=today, outcome='responded', channel='展会'),
                   dict(target_id='A', occurred_on=today, outcome='contacted', channel='电话', actual_cost=0, currency='USD'),
                   dict(target_id='A', occurred_on=today, outcome='no_fit', channel='电话', actual_cost=20, currency='USD'),
                   dict(target_id='B', event_id='E', occurred_on=future, outcome='planned', channel='展会'),
                   dict(target_id='B', occurred_on=future, outcome='qualified', channel='电话', actual_cost=900, currency='CNY')]
        links = [dict(target_id='A', opportunity_id='O', linked_on=today, origin_event_id='E', opportunity=dict(status='won', signed_amounts=[dict(currency='CNY', amount=500)])),
                 dict(target_id='B', opportunity_id='FUTURE', linked_on=future, opportunity=dict(status='won', signed_amounts=[dict(currency='USD', amount=900)]))]
        detail = dict(targets=targets, events=events, touches=touches, links=links, as_of=today, actual_through=today)
        actual = touches[:4]
        expected = _analytics(detail, actual, links[:1])
        local = dict(detail, targets=targets[:1], events=[])
        local_expected = _analytics(local, actual, links[:1])
        assets = Path(__file__).resolve().parents[1] / 'display/workbench'
        script = r"""const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={window:{},document:{}};vm.createContext(context);
const source=fs.readFileSync(process.argv[1]+'/gtm.js','utf8');
vm.runInContext(source.slice(0,source.indexOf('  async function api'))+'})();',context);
vm.runInContext(fs.readFileSync(process.argv[1]+'/gtm-map.js','utf8'),context);
const geo=JSON.parse(fs.readFileSync(process.argv[1]+'/china-map.json','utf8'));
const {detail,expected,local_expected}=JSON.parse(fs.readFileSync(0,'utf8'));
const l=context.window.GTMLogic, objects=l.objects(detail);
const normalize=x=>JSON.parse(JSON.stringify(x));
const scoped=(p,c='')=>l.scopeSnapshot(detail,objects.filter(x=>context.window.GTMMap.fits(x,p,c,geo)));
assert.deepStrictEqual(normalize(l.scopeSnapshot(detail,objects).analytics),expected);
const suzhou=scoped('320000','320500');
assert.deepStrictEqual(normalize(suzhou.analytics),local_expected);
assert.equal(suzhou.actual.length,4);assert.equal(suzhou.events.length,0);
const ningbo=scoped('330000','330200');
assert.equal(ningbo.touches.length,2);assert.equal(ningbo.actual.length,0);assert.equal(ningbo.pending.length,2);
assert.equal(ningbo.links.length,0);assert.equal(ningbo.analytics.missing_cost_count,0);
assert.equal(l.money(ningbo.analytics.costs),'未知');
const shanghai=scoped('310000');
assert.equal(shanghai.events.length,1);assert.equal(shanghai.touches.length,0);
assert.equal(shanghai.analytics.events[0].targets,0);assert.equal(shanghai.links.length,0);
assert.equal(scoped('440000','440100').events.length,1);
assert.equal(scoped('320000','320100').targets.length,0);
const empty=l.scopeSnapshot(detail,[]);assert.equal(empty.analytics.funnel.candidates,0);
assert.equal(empty.analytics.missing_cost_count,0);assert.equal(l.money(empty.analytics.signed_amounts),'未知');
const companyOnly=l.scopeSnapshot(detail,objects.filter(x=>l.matches(x,{type:'company',keyword:'苏州'})));
assert.equal(companyOnly.targets.length,1);assert.equal(companyOnly.events.length,0);assert.equal(companyOnly.actual.length,4);
const eventOnly=l.scopeSnapshot(detail,objects.filter(x=>x.object_type==='exhibition'));
assert.equal(eventOnly.events.length,1);assert.equal(eventOnly.actual.length,0);
const duplicate={...detail,links:[detail.links[0],detail.links[0]]};
assert.equal(l.scopeSnapshot(duplicate,objects).analytics.signed_amounts.CNY,500);
const historical={...detail,as_of:'2000-01-01',actual_through:'2000-01-01'};
assert.equal(l.scopeSnapshot(historical,objects).actual.length,0);
assert.equal(l.scopeSnapshot(historical,objects).links.length,0);
assert.equal(l.money(suzhou.analytics.costs),'CNY 100 · USD 20');
"""
        result = subprocess.run(['node', '-e', script, str(assets)], input=json.dumps(dict(detail=detail, expected=expected, local_expected=local_expected)), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
