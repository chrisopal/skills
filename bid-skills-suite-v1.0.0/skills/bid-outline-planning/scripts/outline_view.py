"""Derive display order and numbers without changing the authoritative outline."""
from __future__ import annotations

import re

CHINESE = '零〇一二三四五六七八九十百千两'


def _chinese_integer(value):
    digits = dict(zip('零〇一二三四五六七八九两', (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2)))
    total, digit = 0, 0
    for character in value:
        if character in digits:
            digit = digits[character]
        else:
            total += (digit or 1) * {'十': 10, '百': 100, '千': 1000}[character]
            digit = 0
    return total + digit


def ordered_sections(sections):
    """Return a parent-first flat view with depth; reject broken parent relationships."""
    nodes, children = {}, {None: []}
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get('id'), str) or not section['id']:
            raise ValueError('目录节点缺少有效ID')
        if section['id'] in nodes:
            raise ValueError('目录节点ID重复')
        parent = section.get('parent_id')
        if parent is not None and not isinstance(parent, str):
            raise ValueError('目录父级ID无效')
        nodes[section['id']] = section
        children.setdefault(parent, []).append(section['id'])
    if any(parent is not None and parent not in nodes for parent in children):
        raise ValueError('目录存在缺失父级')

    # Numbered siblings may have been appended in separate writing batches.
    # Keep custom/unnumbered format order, but display explicit numeric paths naturally.
    for siblings in children.values():
        keys = {}
        for node_id in siblings:
            raw = str(nodes[node_id].get('number') or '').strip()
            mixed = re.fullmatch(f'([{CHINESE}]+)\\.(\\d+(?:\\.\\d+)*)', raw)
            if mixed:
                raw = f'{_chinese_integer(mixed[1])}.{mixed[2]}'
            if re.fullmatch(r'\d+(?:\.\d+)*', raw):
                keys[node_id] = tuple(map(int, raw.split('.')))
        if len(keys) == len(siblings) and len(set(keys.values())) == len(siblings):
            siblings.sort(key=keys.__getitem__)

    roots = children[None]
    stack = [(node, 0, (index + 1,)) for index, node in reversed(list(enumerate(roots)))]
    rows, visited = [], set()
    while stack:
        node_id, depth, ordinal = stack.pop()
        if node_id in visited:
            raise ValueError('目录存在循环')
        visited.add(node_id)
        node = nodes[node_id]
        raw = str(node.get('number') or '').strip()
        mixed = re.fullmatch(f'([{CHINESE}]+)\\.(\\d+(?:\\.\\d+)*)', raw)
        if mixed:
            number = f'{_chinese_integer(mixed[1])}.{mixed[2]}'
        elif depth == 0 and re.fullmatch(f'[{CHINESE}]+', raw):
            number = raw + '、'
        else:
            number = raw or '.'.join(map(str, ordinal))
        numeric_path = tuple(map(int, raw.split('.'))) if re.fullmatch(r'\d+(?:\.\d+)*', raw) else ordinal
        rows.append(dict(node, display_number=number, depth=depth,
                         children_count=len(children.get(node_id, []))))
        for index, child in reversed(list(enumerate(children.get(node_id, [])))):
            stack.append((child, depth + 1, numeric_path + (index + 1,)))
    if len(visited) != len(nodes):
        raise ValueError('目录存在循环或无可用根节点')
    return rows
