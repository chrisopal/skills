"""GTM research and follow-up beside, rather than inside, the sales lifecycle."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import math
import re
from urllib.parse import urlsplit

from .storage import OpportunitySQLiteAdapter
from .utils import now_iso
from .lifecycle import artifact_verification

OUTCOMES = ('contacted', 'responded', 'meeting', 'qualified')
WEIGHTS = {'industry': 35, 'pain': 30, 'access': 20, 'evidence': 15}
COLLECTIONS = {'source': 'sources', 'target': 'targets', 'event': 'events', 'message': 'messages'}


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + '不能为空')
    if len(value) > 20000:
        raise ValueError(label + '过长')
    return value.strip()


def identifier(value):
    value = text(value, '记录编号')
    if not re.fullmatch(r'[A-Za-z0-9_\-]{1,80}', value):
        raise ValueError('记录编号仅支持80位以内的字母、数字、横线和下划线')
    return value


def day(value, label='日期'):
    value = text(value, label)
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError()
    except ValueError:
        raise ValueError(label + '必须为YYYY-MM-DD') from None
    return value


def url(value):
    value = text(value, '来源链接')
    parsed = urlsplit(value)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('来源链接必须是无凭证的http或https地址')
    return value


def strings(value, label, *, required=False):
    if not isinstance(value, list) or (required and not value) or len(value) > 200:
        raise ValueError(label + '必须为文本数组')
    return list(dict.fromkeys(text(v, label) for v in value))


def money(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('实际费用必须为非负有限数值')
    return value


def currency(value):
    value = text(value, '币种').upper()
    if not re.fullmatch('[A-Z]{3}', value):
        raise ValueError('币种必须为三位代码，如CNY')
    return value


def find(state, collection, record_id):
    item = next((v for v in state[collection] if v['id'] == record_id), None)
    if item is None:
        raise ValueError('未找到本计划的' + collection + '记录：' + str(record_id))
    return item


def refs(state, values):
    values = strings(values, '来源编号', required=True)
    for value in values:
        find(state, 'sources', value)
    return values


def search_brief(brief):
    """Build executable research tasks; no pretend background search or scraping."""
    product = brief.get('product', '')
    customer = brief.get('target_customer', '')
    regions = brief.get('regions', [])
    if not isinstance(product, str) or not isinstance(customer, str):
        raise ValueError('产品和目标客户必须为文本')
    regions = strings(regions, '目标区域')
    missing = [label for label, value in [('主打产品', product), ('目标客户', customer), ('目标区域', regions)] if not value]
    queries = []
    for region in regions or ['待确认区域']:
        for kind, suffix, checks in [
            ('company', '企业 官网 产品 生产基地', ['企业主体及官网', '区域与行业事实', '适配推断和需求未知分开']),
            ('event', '展会 行业论坛 主办方 日期', ['届次和开始结束日期', '主办方地点及官方报名页', '历史活动不作未来参会承诺']),
            ('channel', '行业协会 产业园 合作伙伴 官网', ['公开渠道及业务范围', '合作入口与准入规则', '不虚构成员联系或渠道效果']),
        ]:
            queries.append({'kind': kind, 'query': ' '.join([region, customer, product, suffix]).strip(), 'checks': checks})
    return {'queries': queries, 'missing_inputs': missing}


def _location(value):
    if not isinstance(value, dict) or value.get('precision') not in ('city', 'site'):
        raise ValueError('坐标需标注city或site精度')
    for key, low, high in [('lon', -180, 180), ('lat', -90, 90)]:
        if type(value.get(key)) not in (int, float) or not math.isfinite(value[key]) or not low <= value[key] <= high:
            raise ValueError('经纬度超出有效范围')
    return {key: value[key] for key in ('lon', 'lat', 'precision')}


def _record(state, kind, raw):
    if not isinstance(raw, dict):
        raise ValueError('record必须为对象')
    result = {'id': identifier(raw.get('id'))}
    if kind == 'source':
        for key in ('title', 'publisher', 'claim'):
            result[key] = text(raw.get(key), key)
        result['url'] = url(raw.get('url'))
        result['accessed_on'] = day(raw.get('accessed_on'), '访问日期')
        if result['accessed_on'] > date.today().isoformat():
            raise ValueError('访问日期不能在未来')
        if raw.get('verification') not in ('official', 'unverified'):
            raise ValueError('来源类型必须为official或unverified')
        result['verification'] = raw['verification']
        if raw.get('published_on'):
            result['published_on'] = day(raw['published_on'], '发布日期')
        return result
    if kind in ('target', 'event'):
        for key in ('name', 'region', 'city', 'fit_reason'):
            result[key] = text(raw.get(key), key)
        result['source_ids'] = refs(state, raw.get('source_ids'))
        if raw.get('location') is not None:
            result['location'] = _location(raw['location'])
    if kind == 'target':
        result['industry'] = text(raw.get('industry'), '行业')
        fit = raw.get('fit', {})
        if not isinstance(fit, dict) or set(fit) - set(WEIGHTS):
            raise ValueError('适配分项无效')
        result['fit'] = {key: fit.get(key) for key in WEIGHTS}
        for value in result['fit'].values():
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 5):
                raise ValueError('适配分项必须为0到5或null')
        if raw.get('website'):
            result['website'] = url(raw['website'])
        result['roles'] = strings(raw.get('roles', []), '目标角色')
        result['hypothesis'] = str(raw.get('hypothesis') or '')
    elif kind == 'event':
        if raw.get('kind') not in ('exhibition', 'forum', 'channel'):
            raise ValueError('活动类型无效')
        result['kind'] = raw['kind']
        if raw.get('starts_on') or raw.get('ends_on'):
            result['starts_on'] = day(raw.get('starts_on'), '开始日期')
            result['ends_on'] = day(raw.get('ends_on'), '结束日期')
            if result['ends_on'] < result['starts_on']:
                raise ValueError('结束日期不能早于开始日期')
        for key in ('organizer', 'audience'):
            if raw.get(key):
                result[key] = text(raw[key], key)
        if raw.get('url'):
            result['url'] = url(raw['url'])
    elif kind == 'message':
        for key in ('title', 'channel', 'role', 'opening', 'value', 'proof', 'cta', 'objection'):
            result[key] = text(raw.get(key), key)
        if raw.get('target_id'):
            find(state, 'targets', raw['target_id'])
            result['target_id'] = raw['target_id']
        result['source_ids'] = refs(state, raw.get('source_ids'))
        result['status'] = 'draft'
    return result


def _touch(state, raw):
    if not isinstance(raw, dict):
        raise ValueError('跟进record必须为对象')
    record = {'id': identifier(raw.get('id')), 'target_id': identifier(raw.get('target_id'))}
    find(state, 'targets', record['target_id'])
    if any(t['id'] == record['id'] for t in state['touches']):
        raise ValueError('跟进编号已存在；历史跟进不可覆盖')
    for key in ('channel', 'summary', 'owner'):
        record[key] = text(raw.get(key), key)
    record['occurred_on'] = day(raw.get('occurred_on'), '发生日期')
    if raw.get('outcome') not in OUTCOMES + ('planned', 'no_fit'):
        raise ValueError('跟进结果无效')
    record['outcome'] = raw['outcome']
    record['evidence'] = str(raw.get('evidence') or '').strip()
    if record['outcome'] != 'planned':
        text(record['evidence'], '实际跟进证据')
        if not state['campaign']['simulation'] and '模拟' in record['evidence']:
            raise ValueError('模拟跟进只能登记在模拟计划')
    record['next_action'] = str(raw.get('next_action') or '').strip()
    if raw.get('event_id'):
        find(state, 'events', raw['event_id'])
        record['event_id'] = raw['event_id']
    if raw.get('due_on'):
        record['due_on'] = day(raw['due_on'], '下次期限')
    if raw.get('actual_cost') is not None:
        if record['outcome'] == 'planned':
            raise ValueError('计划跟进不能登记实际费用')
        record['actual_cost'] = money(raw['actual_cost'])
        record['currency'] = currency(raw.get('currency'))
    return record


def _name(value):
    return ''.join(str(value).casefold().split())


class GTMStore:
    """Small campaign state using the existing adapter transaction/request journal."""
    def __init__(self, db_path):
        self.adapter = OpportunitySQLiteAdapter(db_path)
        self.adapter.conn.execute('CREATE TABLE IF NOT EXISTS gtm_campaigns (id TEXT PRIMARY KEY, state_json TEXT NOT NULL)')
        self.adapter.conn.commit()

    def close(self):
        self.adapter.close()

    def _load(self, campaign_id):
        import json
        row = self.adapter.conn.execute('SELECT state_json FROM gtm_campaigns WHERE id=?', (campaign_id,)).fetchone()
        if row is None:
            raise ValueError('推广计划不存在：' + str(campaign_id))
        return json.loads(row['state_json'])

    def campaigns(self):
        import json
        rows = self.adapter.conn.execute('SELECT state_json FROM gtm_campaigns ORDER BY id').fetchall()
        return {'campaigns': [dict(json.loads(row[0])['campaign'], revision=json.loads(row[0])['revision']) for row in rows]}

    def manage(self, change):
        import json
        campaign_id = identifier(change.get('campaign_id'))
        request_id = text(change.get('request_id'), '请求编号')
        actor = text(change.get('actor'), '记录人')
        operations = change.get('operations')
        if not isinstance(operations, list) or not operations or len(operations) > 200:
            raise ValueError('operations必须为非空数组且不超过200项')
        with self.adapter.transaction():
            payload = {'command': 'gtm', 'change': change}
            replay = self.adapter._request_replay(request_id, payload)
            if replay:
                replay['detail'] = self.detail(campaign_id)
                replay['revision'] = replay['detail']['revision']
                return replay
            exists = self.adapter.conn.execute('SELECT 1 FROM gtm_campaigns WHERE id=?', (campaign_id,)).fetchone()
            state = self._load(campaign_id) if exists else {'revision': 0, 'campaign': {}, 'sources': [], 'targets': [], 'events': [], 'messages': [], 'touches': [], 'links': [], 'history': []}
            if type(change.get('expected_revision')) is not int or change['expected_revision'] != state['revision']:
                raise ValueError('revision conflict：推广计划已更新，请刷新后重试')
            for op in operations:
                if not isinstance(op, dict):
                    raise ValueError('操作必须为对象')
                kind = op.get('type')
                if kind == 'create_campaign':
                    if state['campaign']:
                        raise ValueError('推广计划已存在')
                    campaign = {'id': campaign_id}
                    for key in ('name', 'product', 'target_customer', 'owner'):
                        campaign[key] = text(op.get(key), key)
                    campaign['regions'] = strings(op.get('regions'), '目标区域', required=True)
                    if type(op.get('simulation')) is not bool:
                        raise ValueError('必须明确是否为模拟计划')
                    campaign['simulation'] = op['simulation']
                    campaign['currency'] = currency(op.get('currency', 'CNY'))
                    campaign['value_proposition'] = str(op.get('value_proposition') or '')
                    campaign['proof_points'] = strings(op.get('proof_points', []), '卖点证据')
                    state['campaign'] = campaign
                elif not state['campaign']:
                    raise ValueError('请先创建推广计划')
                elif kind in ['upsert_' + key for key in COLLECTIONS]:
                    entity = kind.removeprefix('upsert_')
                    record = _record(state, entity, op.get('record'))
                    items = state[COLLECTIONS[entity]]
                    old = next((v for v in items if v['id'] == record['id']), None)
                    if entity == 'target':
                        # A different target id must not inflate the same enterprise funnel.
                        if any(v['id'] != record['id'] and _name(v['name']) == _name(record['name']) for v in items):
                            raise ValueError('本计划已存在同名企业，请更新原目标记录')
                        if old and _name(old['name']) != _name(record['name']):
                            raise ValueError('不可用原目标编号替换另一企业')
                    if old:
                        items[items.index(old)] = record
                    else:
                        items.append(record)
                elif kind == 'record_touch':
                    state['touches'].append(dict(_touch(state, op.get('record')), actor=actor, recorded_at=now_iso()))
                elif kind == 'link_opportunity':
                    target = find(state, 'targets', op.get('target_id'))
                    touch = find(state, 'touches', op.get('touch_id'))
                    if touch['target_id'] != target['id'] or touch['outcome'] != 'qualified' or touch['occurred_on'] > date.today().isoformat():
                        raise ValueError('商机关联需要本企业已经发生的有效线索跟进')
                    oid = text(op.get('opportunity_id'), '商机编号')
                    try:
                        detail = self.adapter.get_opportunity_detail(oid)
                    except KeyError:
                        raise ValueError('关联商机不存在') from None
                    if _name(detail['account']['company_name']) != _name(target['name']):
                        raise ValueError('商机客户与目标企业不一致，请核对企业主体')
                    old = next((v for v in state['links'] if v['opportunity_id'] == oid), None)
                    if old:
                        raise ValueError('该商机在本计划已有来源关联，不可覆盖归因')
                    state['links'].append({'target_id': target['id'], 'opportunity_id': oid, 'touch_id': touch['id'], 'origin_event_id': touch.get('event_id'), 'actor': actor, 'linked_on': date.today().isoformat()})
                else:
                    raise ValueError('不支持的GTM操作：' + str(kind))
            state['revision'] += 1
            state['history'].append({'revision': state['revision'], 'actor': actor, 'time': now_iso(), 'operations': deepcopy(operations)})
            self.adapter.conn.execute('INSERT INTO gtm_campaigns VALUES (?,?) ON CONFLICT(id) DO UPDATE SET state_json=excluded.state_json', (campaign_id, json.dumps(state, ensure_ascii=False)))
            receipt = {'campaign_id': campaign_id, 'receipt_revision': state['revision'], 'revision': state['revision']}
            self.adapter._save_request(request_id, payload, receipt)
            return dict(receipt, detail=self.detail(campaign_id))

    def detail(self, campaign_id, as_of=None):
        state = deepcopy(self._load(campaign_id))
        as_of = day(as_of or date.today().isoformat(), '统计截止日')
        state['as_of'] = as_of
        actual_through = min(as_of, date.today().isoformat())
        state['actual_through'] = actual_through
        for source in state['sources']:
            source['age_days'] = (date.fromisoformat(as_of) - date.fromisoformat(source['accessed_on'])).days
        actual = [t for t in state['touches'] if t['outcome'] != 'planned' and t['occurred_on'] <= actual_through]
        links = [link for link in state['links'] if link['linked_on'] <= as_of]
        for target in state['targets']:
            fit = target['fit']
            target['fit_coverage'] = sum(v is not None for v in fit.values()) / len(WEIGHTS)
            target['fit_score'] = round(sum(fit[k] / 5 * weight for k, weight in WEIGHTS.items())) if target['fit_coverage'] == 1 else None
            matches = [t for t in actual if t['target_id'] == target['id']]
            latest = max(enumerate(matches), key=lambda it: (it[1]['occurred_on'], it[0]))[1] if matches else None
            target['status'] = 'opportunity' if any(l['target_id'] == target['id'] for l in links) else latest['outcome'] if latest else 'candidate'
        for event in state['events']:
            event['timing'] = ('ongoing' if event['kind'] == 'channel' else 'unknown' if not event.get('starts_on') else 'past' if event['ends_on'] < as_of else 'upcoming' if event['starts_on'] > as_of else 'ongoing')
        for link in state['links']:
            try:
                detail = self.adapter.get_opportunity_detail(link['opportunity_id'])
                lc, opp = detail['lifecycle'], detail['opportunity']
                # Only the latest recorded contract matching its current artifact is effective.
                signed = []
                if lc['contracts']:
                    contract = lc['contracts'][-1]
                    artifact = next((a for a in lc['artifacts'] if a['id'] == contract['artifact_id']), None)
                    if artifact and artifact_verification(lc, artifact)[0] == 'valid' and artifact['sha256'] == contract['sha256'] and contract['signing_date'] <= actual_through:
                        signed = [{key: contract[key] for key in ('amount', 'currency')}]
                assessment = detail.get('commercial_assessment') or {}
                link['opportunity'] = {'id': opp['id'], 'name': opp.get('name') or opp.get('opportunity_name'), 'company_name': detail['account']['company_name'], 'current_stage_id': lc['current_stage_id'], 'current_stage_name': lc.get('current_stage_name'), 'status': lc['status'], 'score': assessment.get('overall_opportunity_score', opp.get('score')), 'signed_amounts': signed, 'verification_status': lc['verification_status']}
            except (KeyError, ValueError, OSError) as exc:
                link['link_error'] = str(exc)
        state['analytics'] = _analytics(state, actual, links)
        state['search_brief'] = search_brief(state['campaign'])
        state['analytics']['opportunity_snapshot'] = '当前商机回读；截止日只约束推广跟进和关联，不重建历史商机状态'
        return state


def _costs(touches):
    costs, missing = {}, 0
    for touch in touches:
        if 'actual_cost' not in touch:
            missing += 1
        else:
            code = touch['currency']
            costs[code] = round(costs.get(code, 0) + touch['actual_cost'], 2)
    return costs, missing


def _reached(touches, outcome):
    index = OUTCOMES.index(outcome)
    return {t['target_id'] for t in touches if t['outcome'] in OUTCOMES and OUTCOMES.index(t['outcome']) >= index}


def _analytics(state, touches, links):
    # milestone nesting expresses the funnel; unique target ids avoid repeat-touch inflation.
    funnel = {'candidates': len(state['targets'])}
    for key in OUTCOMES:
        funnel[key] = len(_reached(touches, key))
    funnel['opportunities'] = len({l['target_id'] for l in links})
    funnel['won'] = len({l['target_id'] for l in links if l.get('opportunity', {}).get('status') == 'won' and l.get('opportunity', {}).get('signed_amounts')})
    regions = []
    for region in dict.fromkeys(t['region'] for t in state['targets']):
        ids = {t['id'] for t in state['targets'] if t['region'] == region}
        regions.append({'name': region, 'candidates': len(ids), 'contacted': len(ids & _reached(touches, 'contacted')), 'qualified': len(ids & _reached(touches, 'qualified')), 'opportunities': len({l['target_id'] for l in links} & ids), 'won': len({l['target_id'] for l in links if l.get('opportunity', {}).get('status') == 'won' and l.get('opportunity', {}).get('signed_amounts')} & ids)})
    channels = []
    for channel in dict.fromkeys(t['channel'] for t in touches):
        items = [t for t in touches if t['channel'] == channel]
        costs, missing = _costs(items)
        channels.append({'name': channel, 'touches': len(items), **{k: len(_reached(items, k)) for k in ('contacted', 'responded', 'qualified')}, 'costs': costs, 'missing_cost_count': missing})
    events = []
    for event in state['events']:
        items = [t for t in touches if t.get('event_id') == event['id']]
        costs, missing = _costs(items)
        events.append({'id': event['id'], 'name': event['name'], 'targets': len({t['target_id'] for t in items}), 'qualified': len(_reached(items, 'qualified')), 'opportunities': len({l['target_id'] for l in links if l.get('origin_event_id') == event['id']}), 'costs': costs, 'missing_cost_count': missing})
    signed = {}
    # One opportunity can have several contacts, but only one effective signed sum.
    for link in {l['opportunity_id']: l for l in links}.values():
        for amount in link.get('opportunity', {}).get('signed_amounts', []):
            code = amount['currency']
            signed[code] = round(signed.get(code, 0) + amount['amount'], 2)
    costs, missing = _costs(touches)
    return {'funnel': funnel, 'regions': regions, 'channels': channels, 'events': events, 'costs': costs, 'missing_cost_count': missing, 'signed_amounts': signed, 'unmapped_targets': sum(not t.get('location') for t in state['targets'])}
