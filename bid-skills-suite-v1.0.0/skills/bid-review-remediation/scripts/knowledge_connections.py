#!/usr/bin/env python3
"""Bind a designated knowledge source to real host-tool retrieval handoffs.

This helper never invents an API or executes an arbitrary shell command. A host
performs the authorized search/read; this module validates and saves its result.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

import bidkit
import knowledge

CONFIG = 'profiles/knowledge-connections.json'


@contextmanager
def _writer(project):
    path = bidkit.safe(project, 'work/.knowledge-connections.lock')
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('已有知识库连接写入者') from exc
    try:
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', value):
        raise ValueError('连接ID无效')
    return value


def _resource(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('资源引用不能为空')
    knowledge._metadata(value)
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('资源范围需使用不含查询或片段的稳定引用')
    decoded = parsed.path
    for _ in range(4):
        decoded = unquote(decoded)
    if '\\' in decoded or any(p in {'.', '..'} for p in decoded.split('/')):
        raise ValueError('资源引用包含路径跳转')
    return parsed.scheme.lower(), parsed.netloc.lower(), decoded.rstrip('/')


def _within(source, roots):
    scheme, netloc, path = _resource(source)
    for root in roots:
        r_scheme, r_netloc, r_path = _resource(root)
        if (scheme, netloc) == (r_scheme, r_netloc) and (
                path == r_path or path.startswith(r_path + '/')):
            return True
    return False


def load(project):
    project = Path(project).resolve()
    path = bidkit.safe(project, CONFIG)
    if not path.exists():
        return {'schema_version': '1.0', 'project_id': bidkit.project_id(project),
                'revision': 0, 'connections': {}}
    value = bidkit.read(path)
    if value.get('project_id') != bidkit.project_id(project):
        raise ValueError('知识库连接与项目身份不一致')
    return value


def _save(project, config):
    config['revision'] += 1
    bidkit.atomic(bidkit.safe(project, CONFIG), config)


def configure(project, connection_id, *, provider, resource_ref, tool_name,
              permission_scope, allowed_sources, max_age_hours=24):
    project = Path(project).resolve()
    _identifier(connection_id)
    _resource(resource_ref)
    for text in (provider, tool_name, permission_scope):
        if not isinstance(text, str) or not text.strip():
            raise ValueError('提供方、实际工具名及授权范围不能为空')
        knowledge._metadata(text)
    if not isinstance(allowed_sources, list) or not allowed_sources:
        raise ValueError('请明确允许采用的文档引用范围')
    for source in allowed_sources:
        _resource(source)
    if (isinstance(max_age_hours, bool) or not isinstance(max_age_hours, (float, int))
            or not 0 < max_age_hours <= 8760):
        raise ValueError('复核间隔需为0到8760小时之间的正数')
    with _writer(project):
        config = load(project)
        previous = config['connections'].get(connection_id, {})
        value = {'id': connection_id, 'revision': previous.get('revision', 0) + 1,
                 'provider': provider, 'resource_ref': resource_ref, 'tool_name': tool_name,
                 'permission_scope': permission_scope, 'allowed_sources': allowed_sources,
                 'max_age_hours': max_age_hours, 'state': 'configured',
                 'host_call_verified': False, 'updated_at': bidkit.now()}
        config['connections'][connection_id] = value
        _save(project, config)
        return value


def status(project, connection_id):
    connection = load(project)['connections'].get(_identifier(connection_id))
    if connection is None:
        raise ValueError('知识库连接不存在')
    value = dict(connection)
    value['usable'] = False
    value['remote_freshness'] = 'NOT_CHECKED'
    if value['state'] == 'snapshot_saved':
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(value['retrieved_at'])).total_seconds()
        value['usable'] = -300 <= age <= value['max_age_hours'] * 3600
        if not value['usable']:
            value['state'] = 'needs_refresh'
    return value


def request(project, connection_id, query):
    project = Path(project).resolve()
    if not isinstance(query, str) or not query.strip():
        raise ValueError('检索问题不能为空')
    knowledge._metadata(query)
    with _writer(project):
        config = load(project)
        connection = config['connections'].get(_identifier(connection_id))
        if connection is None:
            raise ValueError('知识库连接不存在')
        request_id = 'KR-' + uuid.uuid4().hex[:16]
        path = f'inputs/knowledge/requests/{request_id}.json'
        value = {'project_id': bidkit.project_id(project), 'request_id': request_id,
                 'connection_id': connection_id, 'connection_revision': connection['revision'],
                 'provider': connection['provider'], 'resource_ref': connection['resource_ref'],
                 'tool_name': connection['tool_name'], 'permission_scope': connection['permission_scope'],
                 'allowed_sources': connection['allowed_sources'], 'query': query,
                 'created_at': bidkit.now(), 'state': 'awaiting_host', 'relative_path': path}
        bidkit.atomic(bidkit.safe(project, path), value)
        connection['state'] = 'awaiting_host'
        _save(project, config)
        return value


def ingest(project, request_path, response_path):
    project = Path(project).resolve()
    request_path = bidkit.safe(project, str(request_path))
    task = bidkit.read(request_path)
    raw = Path(response_path).read_bytes()
    response = json.loads(raw)
    if (task['project_id'] != bidkit.project_id(project)
            or response.get('request_id') != task['request_id']
            or response.get('resource_ref') != task['resource_ref']):
        raise ValueError('知识库结果不对应当前项目、请求或资源')
    outcome = response.get('outcome')
    with _writer(project):
        config = load(project)
        connection = config['connections'].get(task['connection_id'])
        if connection is None or connection['revision'] != task['connection_revision']:
            raise ValueError('知识库连接已经变更，请重新检索')
        receipt_path = f'inputs/knowledge/requests/{task["request_id"]}-receipt.json'
        receipt = bidkit.safe(project, receipt_path)
        if receipt.exists():
            old = bidkit.read(receipt)
            if old['response_sha256'] == bidkit.digest(response_path):
                return old['result']
            raise ValueError('该检索请求已有结果，不能替换历史快照')
        if outcome == 'success':
            if set(response) != {'request_id', 'resource_ref', 'outcome', 'host_result'}:
                raise ValueError('成功结果只接收约定字段')
            result = response['host_result']
            knowledge.validate_host_result(result, task['project_id'])
            for key in ('provider', 'tool_name', 'query', 'permission_scope'):
                if result[key] != task[key]:
                    raise ValueError('宿主结果与检索请求的' + key + '不一致')
            stamp = datetime.fromisoformat(result['retrieved_at'].replace('Z', '+00:00'))
            created = datetime.fromisoformat(task['created_at'])
            if (stamp < created or
                    (stamp - datetime.now(timezone.utc)).total_seconds() > 300):
                raise ValueError('检索时间早于当前请求或位于未来')
            if any(not _within(row['source_ref'], task['allowed_sources']) for row in result['results']):
                raise ValueError('命中文档超出本连接允许采用的范围')
            result_path = f'inputs/knowledge/requests/{task["request_id"]}-host.json'
            bidkit.atomic(bidkit.safe(project, result_path), result)
            imported = knowledge.import_host(project, bidkit.safe(project, result_path),
                                             connection_id=task['connection_id'],
                                             connection_revision=task['connection_revision'])
            connection['state'] = 'snapshot_saved' if result['results'] else 'empty'
            connection['retrieved_at'] = result['retrieved_at']
            connection['last_request_id'] = task['request_id']
            imported['connection_id'] = task['connection_id']
            imported['connection_revision'] = task['connection_revision']
        elif outcome in {'permission_denied', 'unavailable', 'failed'}:
            if set(response) != {'request_id', 'resource_ref', 'outcome', 'message'}:
                raise ValueError('失败结果只接收状态及简要原因')
            knowledge._metadata(response['message'])
            connection['state'] = outcome
            if outcome == 'permission_denied':
                connection['invalid_before'] = bidkit.now()
            connection['last_request_id'] = task['request_id']
            imported = {'entries_added': 0, 'status': outcome, 'host_call_verified': False,
                        'message': response['message']}
        else:
            raise ValueError('未知知识库检索状态')
        response_saved = f'inputs/knowledge/requests/{task["request_id"]}-response.json'
        target = bidkit.safe(project, response_saved)
        target.write_bytes(raw)
        bidkit.atomic(receipt, {'request': knowledge.reference(project, request_path, task['request_id']),
                               'response_path': response_saved, 'response_sha256': bidkit.digest(target),
                               'recorded_at': bidkit.now(), 'result': imported})
        connection['updated_at'] = bidkit.now()
        _save(project, config)
        return imported


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    setup = commands.add_parser('configure')
    setup.add_argument('--id', required=True)
    for key in ('provider', 'resource-ref', 'tool-name', 'permission-scope'):
        setup.add_argument('--' + key, required=True)
    setup.add_argument('--allowed-source', action='append', required=True)
    setup.add_argument('--max-age-hours', type=float, default=24)
    query = commands.add_parser('request')
    query.add_argument('--id', required=True)
    query.add_argument('--query', required=True)
    result = commands.add_parser('ingest')
    result.add_argument('--request', required=True)
    result.add_argument('--response', type=Path, required=True)
    show = commands.add_parser('status')
    show.add_argument('--id', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'configure':
            value = configure(args.project, args.id, provider=args.provider,
                              resource_ref=args.resource_ref, tool_name=args.tool_name,
                              permission_scope=args.permission_scope,
                              allowed_sources=args.allowed_source, max_age_hours=args.max_age_hours)
        elif args.command == 'request':
            value = request(args.project, args.id, args.query)
        elif args.command == 'ingest':
            value = ingest(args.project, args.request, args.response)
        else:
            value = status(args.project, args.id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
