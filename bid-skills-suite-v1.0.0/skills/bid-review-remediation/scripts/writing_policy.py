#!/usr/bin/env python3
"""Resolve chapter writing preferences and check actual drafts, without model calls."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import struct
import zlib
from pathlib import Path
from urllib.parse import unquote

POLICY_DEFAULTS = {'length_mode': 'auto_scoring', 'length_tolerance': 0.2,
                   'chapter_overrides': {}}
VISUAL_POLICY_DEFAULTS = {'system_ui_policy': 'auto', 'min_ui_images': 1}


def _integer(value, name, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, int) or value < 1
            or (maximum is not None and value > maximum)):
        raise ValueError(name + ' 必须是范围内的正整数')


def normalize_settings(settings, section_ids=None):
    result = dict(POLICY_DEFAULTS, **settings)
    result['visuals'] = dict(VISUAL_POLICY_DEFAULTS, **settings.get('visuals', {}))
    if result['length_mode'] not in {'auto_scoring', 'fixed'}:
        raise ValueError('length_mode 必须是 auto_scoring 或 fixed')
    tolerance = result['length_tolerance']
    if (isinstance(tolerance, bool) or not isinstance(tolerance, (int, float))
            or not math.isfinite(tolerance) or not 0 <= tolerance <= 0.5):
        raise ValueError('length_tolerance 必须在 0 到 0.5 之间')
    if result.get('target_words') is not None:
        _integer(result['target_words'], 'target_words')
    if result['visuals']['system_ui_policy'] not in {'auto', 'all_system_sections', 'off'}:
        raise ValueError('system_ui_policy 无效')
    _integer(result['visuals']['min_ui_images'], 'min_ui_images', 8)
    overrides = result['chapter_overrides']
    if not isinstance(overrides, dict):
        raise ValueError('chapter_overrides 必须按 section_id 保存对象')
    for section_id, override in overrides.items():
        if (not isinstance(section_id, str) or not section_id.strip()
                or (section_ids is not None and section_id not in section_ids)):
            raise ValueError('章节覆盖引用不存在的章节：' + str(section_id))
        if not isinstance(override, dict) or set(override) - {
                'target_words', 'detail_level', 'ui_required', 'min_ui_images'}:
            raise ValueError('章节覆盖包含不支持的字段')
        if override.get('target_words') is not None:
            _integer(override['target_words'], '章节 target_words')
        if override.get('detail_level', 'auto') not in {'auto', 'brief', 'standard', 'detailed'}:
            raise ValueError('章节 detail_level 无效')
        required = override.get('ui_required')
        if required is not None and not isinstance(required, bool):
            raise ValueError('章节 ui_required 必须是布尔值或 null')
        if 'min_ui_images' in override:
            _integer(override['min_ui_images'], '章节 min_ui_images', 8)
    return result


def visible_characters(markdown):
    value = re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', '', markdown)
    value = re.sub(r'(?is)<(script|style)\b[^>]*>.*?</\1>', '', value)
    value = re.sub(r'!\[[^\]]*\]\([^\n]*?\)|!\[[^\]]*\]\[[^\]]*\]', '', value)
    value = re.sub(r'(?m)^\s*\[[^\]]+\]:\s*\S+.*$', '', value)
    value = re.sub(r'\[([^\]]+)\]\([^\n]*?\)|\[([^\]]+)\]\[[^\]]*\]',
                   lambda m: m[1] or m[2], value)
    value = re.sub(r'<[^>]*>', '', value)
    value = re.sub(r'(?m)^\s*(?:#{1,6}\s+|[-+*]\s+|\d+[.)]\s+|>\s*)', '', value)
    value = re.sub(r'(?m)^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$', '', value)
    value = re.sub(r'[*_`|~]', '', value)
    return len(re.sub(r'\s+', '', html.unescape(value)))


def _score_type(item):
    text = item.get('title', '') + ' ' + item.get('rule_text', '')
    if re.search(r'价格分|报价公式|基准价|最低报价|投标报价|投标价格', text):
        return 'price'
    if re.search(r'(?:每提供|每个|每项)[^。；;\n]*(?:合同|证书|业绩|案例|人员|资质|证明|检测报告)[^。；;\n]*分|合同.*复印件|证书.*得.*分', text):
        return 'evidence'
    if re.search(r'方案|设计|架构|实施计划|实施组织|措施|功能演示|组织机构|管理制度|工作流程|合理化建议', text):
        return 'scheme'
    if re.search(r'合同|证书|资质|业绩|社保|授权书|证明材料|检测报告', text):
        return 'evidence'
    return 'unknown'


def resolve_policy(section, sections, scoring, requirements, settings):
    settings = normalize_settings(settings, {s['id'] for s in sections})
    override = settings['chapter_overrides'].get(section['id'], {})
    section_by = {s['id']: s for s in sections}
    score_by = {s['id']: s for s in scoring if s.get('node_type') == 'scored'}
    basis, seen, score_ids = [], set(), set()
    node = section
    while node and node['id'] not in seen:
        seen.add(node['id'])
        for sid in node.get('scoring_ids', []):
            if sid in score_by and sid not in score_ids:
                item = score_by[sid]; score_ids.add(sid)
                basis.append({'id': sid, 'title': item.get('title', ''),
                              'rule_text': item.get('rule_text', ''),
                              'max_score': item.get('max_score'), 'type': _score_type(item),
                              'inherited': node['id'] != section['id']})
        node = section_by.get(node.get('parent_id'))
    types = {item['type'] for item in basis}
    base = settings.get('target_words') or 1000
    detail, reasons = 'standard', []
    scheme = [s for s in basis if s['type'] == 'scheme']
    if scheme:
        scheme_scores = [s.get('max_score') for s in score_by.values() if _score_type(s) == 'scheme'
                         and isinstance(s.get('max_score'), (int, float)) and s['max_score'] > 0]
        peak = max(scheme_scores, default=0)
        high = any(isinstance(s['max_score'], (int, float)) and
                   (s['max_score'] >= 20 or (peak > 0 and s['max_score'] >= peak * 0.8)) for s in scheme)
        detail = 'detailed' if high else 'standard'
        reasons.append('方案评分条件需要展开机制、步骤、异常处理及验收；高分项优先。')
    elif types and types <= {'evidence', 'price'}:
        detail = 'brief'
        reasons.append('按证明材料或价格规则计分，增加文字不能替代有效证据或计算。')
    if len(section.get('requirement_ids', [])) >= 8 and not (types and types <= {'evidence', 'price'}):
        detail = 'detailed'
        reasons.append('本章绑定需求较多，需要逐项展开并核对。')
    if not reasons:
        reasons.append('按普通章节基准推荐；未知评分规则需宿主回查原文。')
    if override.get('detail_level', 'auto') != 'auto':
        detail = override['detail_level']; reasons.append('采用用户逐章指定的详细程度。')
    target = round(base * {'brief': 0.5, 'standard': 1, 'detailed': 2}[detail])
    if scheme and detail == 'standard' and override.get('detail_level', 'auto') == 'auto':
        target = round(base * 1.5)
    source, required_length = 'recommendation', False
    fixed_form = bool(re.search(r'投标函|授权委托书|法定代表人.*身份证明|承诺函|报价表|开标一览表|偏离表|评分索引表|逐项响应.*表|证照复印件', section.get('title', '')))
    if fixed_form:
        target = None; reasons.append('固定表单按原格式填写，不为推荐字数填充内容。')
    if settings['length_mode'] == 'fixed':
        target = settings.get('target_words'); source = 'global'; required_length = target is not None
    if override.get('target_words') is not None:
        target = override['target_words']; source = 'chapter'; required_length = True
        reasons.append('采用用户逐章指定的目标字数。')
    req_ids = set(section.get('requirement_ids', []))
    req_text = ' '.join(r.get('text', '') for r in requirements if r['id'] in req_ids)
    title = section.get('title', '')
    context = title + ' ' + section.get('task', '') + ' ' + req_text
    explicit_ui = bool(re.search(r'界面|截图|UI', ' '.join(section.get('visuals_needed', [])), re.I))
    function_title = bool(re.search(r'工单|告警|事件闭环|视频监控|巡检|操作界面|功能模块|系统功能|用户.*管理|角色.*管理|权限.*管理|账号|门禁|驾驶舱|报表|智能分析|数据集成|后台管理|访客管理|资产管理', title))
    function_context = (bool(re.search(r'系统|平台|软件|页面|界面', context))
                        and bool(re.search(r'查询|分派|复核|处置|展示|检索|告警|操作|工单|功能', context)))
    support_title = bool(re.search(r'架构|网络|部署|接口|培训|进度|项目管理|投标函|报价|证明|证书', title))
    support_title = support_title or bool(re.search(r'建设范围|利旧|质量管理|标准适用|保密|信息安全', title))
    system_section = explicit_ui or ((function_title or function_context) and not support_title)
    ui_policy = settings['visuals']['system_ui_policy']
    ui_required = explicit_ui or (ui_policy == 'all_system_sections' and system_section)
    if override.get('ui_required') is not None and not explicit_ui:
        ui_required = override['ui_required']; reasons.append('采用用户逐章界面图要求。')
    elif explicit_ui and override.get('ui_required') is False:
        reasons.append('任务卡明确要求界面图，不能通过用户偏好免除；先复核原文与任务卡。')
    minimum = override.get('min_ui_images', settings['visuals']['min_ui_images']) if ui_required else 0
    tolerance = settings['length_tolerance']
    return {'section_id': section['id'], 'target_words': target,
            'min_words': math.ceil(target * (1 - tolerance)) if target is not None else None,
            'max_words': math.floor(target * (1 + tolerance)) if target is not None else None,
            'detail_level': detail, 'source': source, 'length_required': required_length,
            'reasons': reasons, 'scoring_ids': [s['id'] for s in basis],
            'scoring_basis': basis, 'scoring_types': sorted(types), 'system_section': system_section,
            'ui_required': ui_required, 'min_ui_images': minimum, 'word_unit': 'visible_characters',
            'expansion_requirements': (['响应结论与对应评分条件', '实现机制与实施步骤',
                                       '异常处理与边界', '证据与可验证的验收方法']
                                      if detail == 'detailed' or scheme else ['逐项响应、依据与边界'])}


def _valid_raster(path):
    try:
        from PIL import Image
    except ImportError:
        # PNG validation uses only the standard library in a minimal host.
        content = path.read_bytes()
        if not content.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('此宿主未提供 JPEG 解码能力')
        offset, chunks, compressed = 8, [], bytearray()
        while offset < len(content):
            length = struct.unpack('>I', content[offset:offset + 4])[0]
            end = offset + length + 12
            if end > len(content):
                raise ValueError('PNG 区块不完整')
            kind, data = content[offset + 4:offset + 8], content[offset + 8:end - 4]
            if zlib.crc32(kind + data) & 0xffffffff != struct.unpack('>I', content[end - 4:end])[0]:
                raise ValueError('PNG 校验失败')
            if not chunks and (kind != b'IHDR' or length != 13 or not all(struct.unpack('>II', data[:8]))):
                raise ValueError('PNG 尺寸无效')
            if kind == b'IDAT':
                compressed.extend(data)
            if kind == b'IEND' and (length or end != len(content)):
                raise ValueError('PNG 结束区块无效')
            chunks.append(kind); offset = end
        if not chunks or chunks[-1] != b'IEND' or not zlib.decompress(compressed):
            raise ValueError('PNG 图像数据无效')
    else:
        with Image.open(path) as image:
            if image.format not in {'PNG', 'JPEG'}:
                raise ValueError('界面图必须是 PNG/JPEG')
            image.verify()


def _inserted_paths(project, body):
    values = re.findall(r'!\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))', body)
    result = set()
    for angle, plain in values:
        value = unquote(angle or plain)
        path = (project / value).resolve()
        if path.is_relative_to(project):
            result.add(path)
    return result


def assess_chapters(project, sections, chapters, scoring, requirements, figures, settings):
    project = Path(project).resolve()
    settings = normalize_settings(settings, {s['id'] for s in sections})
    by_section = {c['section_id']: c for c in chapters}
    results, blockers, notices = [], [], []
    for section in sections:
        policy = resolve_policy(section, sections, scoring, requirements, settings)
        body = by_section.get(section['id'], {}).get('body_markdown', '')
        actual, issues, hard = visible_characters(body), [], []
        length_status = 'not_set'
        if policy['target_words'] is not None:
            length_status = ('too_short' if actual < policy['min_words'] else
                             'too_long' if actual > policy['max_words'] else 'in_range')
            if length_status != 'in_range':
                issues.append('可见正文' + str(actual) + '字，目标范围' +
                              str(policy['min_words']) + '—' + str(policy['max_words']) + '字。')
                if policy['length_required']:
                    hard.extend(issues)
        inserted, images = _inserted_paths(project, body), set()
        if policy['ui_required']:
            for figure in figures:
                if figure.get('section_id') != section['id'] or figure.get('state') not in {'rendered', 'reviewed'}:
                    continue
                is_interface = (figure.get('kind') == 'interface' or
                                (figure.get('kind') == 'concept' and
                                 '界面设计示意' in figure.get('caption', '')))
                if not is_interface or not figure.get('rendered_path'):
                    continue
                path = (project / figure['rendered_path']).resolve()
                if (not path.is_relative_to(project) or not path.is_file() or path not in inserted
                        or path.suffix.lower() not in {'.png', '.jpg', '.jpeg'}):
                    continue
                if '界面设计示意' not in figure.get('caption', '') or '非实际系统截图' not in figure.get('caption', ''):
                    issues.append(figure.get('id', '') + '：缺少界面示意属性图注。')
                    continue
                try:
                    _valid_raster(path)
                except (OSError, ValueError, struct.error, zlib.error) as exc:
                    issues.append(figure.get('id', '') + '：界面图无法解码：' + str(exc))
                    continue
                images.add(hashlib.sha256(path.read_bytes()).hexdigest())
            if len(images) < policy['min_ui_images']:
                issue = '需至少' + str(policy['min_ui_images']) + '张界面图，实际已渲染并插入' + str(len(images)) + '张。'
                issues.append(issue); hard.append(issue)
            if settings['visuals'].get('enabled', True) is False or settings['visuals'].get('image_mode') == 'disabled':
                issue = '本章要求界面图，但生成式配图已关闭；需要授权真实材料或调整配置。'
                issues.append(issue)
                if len(images) < policy['min_ui_images']:
                    hard.append(issue)
        ui_status = ('not_required' if not policy['ui_required'] else
                     'complete' if len(images) >= policy['min_ui_images'] else 'missing')
        results.append(dict(policy, actual_words=actual, length_status=length_status,
                            ui_status=ui_status, ui_image_count=len(images), issues=issues,
                            blocking_issues=hard))
        blockers.extend(section['id'] + ': ' + issue for issue in hard)
        notices.extend(section['id'] + ': ' + issue for issue in issues if issue not in hard)
    return {'passed': not blockers, 'chapters': results, 'blocking_issues': blockers,
            'recommendation_issues': notices, 'semantic_acceptance': 'NOT_TESTED',
            'note': '字数与图片结构符合不证明技术专业性、评分满足或真实截图；需宿主逐项评审。'}


def check_project_policy(project):
    project = Path(project).resolve()
    def read(relative):
        path = (project / relative).resolve()
        if not path.is_relative_to(project):
            raise ValueError('写作策略输入路径越界')
        value = json.loads(path.read_text(encoding='utf-8'))
        identity = json.loads((project / 'work/project.json').read_text())['project_id']
        if value.get('project_id') not in {None, identity}:
            raise ValueError(relative + ': 项目身份不一致')
        return value
    settings_path = project / 'work/writing-settings.json'
    if not settings_path.is_file():
        return {'passed': True, 'chapters': [], 'blocking_issues': [],
                'recommendation_issues': [], 'semantic_acceptance': 'NOT_TESTED', 'status': 'NOT_CONFIGURED'}
    sections = read('artifacts/08-outline.json')['data']['sections']
    chapters = read('artifacts/11-technical-content.json')['data']['chapters']
    scoring = read('artifacts/04-scoring.json')['data']['items']
    requirements = read('artifacts/03-requirements.json')['data']['requirements']
    figures = read('artifacts/13-visuals.json')['data'].get('figures', []) if (project / 'artifacts/13-visuals.json').is_file() else []
    return assess_chapters(project, sections, chapters, scoring, requirements, figures,
                           json.loads(settings_path.read_text(encoding='utf-8')))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    try:
        result = check_project_policy(args.project)
        if args.out:
            target = (args.project / args.out).resolve()
            if not target.is_relative_to(args.project.resolve()):
                raise ValueError('输出路径越界')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['passed'] else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'passed': False, 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
