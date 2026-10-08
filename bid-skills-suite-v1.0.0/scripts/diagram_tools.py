#!/usr/bin/env python3
"""Route bid diagrams and export retained native sources with local tools.

This helper does not invoke an LLM, install tools, or mark a figure reviewed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zlib
from datetime import datetime, timezone
from pathlib import Path


class DiagramError(ValueError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command_for(engine):
    if engine == 'drawio':
        executable = shutil.which('drawio')
        if not executable:
            candidates = [Path('/Applications/draw.io.app/Contents/MacOS/draw.io')]
            if os.name == 'nt':
                candidates += [Path(os.environ.get(key, '')) / 'draw.io/draw.io.exe'
                               for key in ('PROGRAMFILES', 'LOCALAPPDATA')]
            executable = next((str(p) for p in candidates if p.is_file()), None)
        return [executable] if executable else None
    if engine == 'plantuml':
        executable = shutil.which('plantuml')
        if executable:
            return [executable]
        jar = Path(os.environ.get('PLANTUML_JAR', str(
            Path.home() / '.local/share/bid-diagrams/plantuml.jar'))).expanduser()
        java = shutil.which('java')
        if jar.is_file() and java:
            return [java, '-DPLANTUML_SECURITY_PROFILE=SANDBOX', '-jar', str(jar)]
        return None
    if engine == 'mermaid':
        executable = shutil.which('mmdc')
        return [executable] if executable else None
    raise DiagramError('绘图工具必须为 drawio、plantuml 或 mermaid')


def doctor():
    result = {}
    for engine in ('drawio', 'plantuml', 'mermaid'):
        command = command_for(engine)
        result[engine] = {'available': bool(command), 'command': command,
                          'verification': 'located_only'}
    result['host_image_skill'] = {'available': None, 'verification': 'discover_in_host'}
    return result


def plan(settings, kind, capabilities=None, complex_flow=False):
    visuals = settings.get('visuals', settings)
    requested = visuals.get('diagram_engine', 'auto')
    if requested not in ('auto', 'drawio', 'plantuml', 'mermaid'):
        raise DiagramError('diagram_engine 无效')
    output_format = visuals.get('diagram_format', 'svg')
    if output_format not in ('svg', 'png'):
        raise DiagramError('diagram_format 无效')
    template = visuals.get('layout_template', 'auto')
    if template not in ('auto', 'layered', 'swimlane', 'sequence', 'flow'):
        raise DiagramError('layout_template 无效')
    layers = visuals.get('architecture_layers')
    if layers is not None and (type(layers) is not int or not 3 <= layers <= 6):
        raise DiagramError('architecture_layers 须为空或 3—6 的整数')
    if kind == 'sequence':
        preferred = 'plantuml'
    elif kind == 'flow' and not complex_flow:
        preferred = 'mermaid'
    elif kind in ('architecture', 'network', 'flow', 'swimlane', 'configuration'):
        preferred = 'drawio'
    else:
        raise DiagramError('此路由仅处理技术结构图；界面示意由宿主生图 Skill 执行')
    capabilities = doctor() if capabilities is None else capabilities
    fallbacks = (['mermaid', 'drawio'] if kind == 'sequence' else ['drawio', 'mermaid'])
    candidates = ([preferred, *fallbacks] if requested == 'auto'
                  else [requested])
    available = next((tool for tool in candidates
                      if capabilities.get(tool, {}).get('available')), None)
    if template == 'auto':
        template = {'architecture': 'layered', 'sequence': 'sequence',
                    'swimlane': 'swimlane'}.get(kind, 'flow')
    return {'engine': available or candidates[0], 'requested_engine': requested,
            'preferred_engine': preferred, 'format': output_format,
            'layout_template': template,
            'architecture_layers': layers,
            'status': 'planned' if available else 'blocked',
            'fallback_reason': (f'{preferred} 未安装，auto 选择 {available}'
                                if available and requested == 'auto'
                                and available != preferred else None)}


def inside(project, path):
    project = Path(project).resolve()
    path = Path(path)
    path = (project / path if not path.is_absolute() else path).resolve()
    if not path.is_relative_to(project):
        raise DiagramError('图表路径超出项目目录')
    return path


def validate_image(path, engine):
    content = path.read_bytes() if path.is_file() else b''
    if not content:
        raise DiagramError('工具未生成实际文件')
    if path.suffix == '.svg':
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise DiagramError('SVG 无法解析') from exc
        if root.tag.rsplit('}', 1)[-1] != 'svg':
            raise DiagramError('导出不是 SVG')
        box = root.get('viewBox', '').replace(',', ' ').split()
        if len(box) == 4:
            try:
                dimensions = [float(box[2]), float(box[3])]
            except ValueError as exc:
                raise DiagramError('SVG 尺寸无效') from exc
        else:
            dimensions = []
            for key in ('width', 'height'):
                match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)(?:px|pt|mm|cm|in)?',
                                     root.get(key, ''))
                dimensions.append(float(match[1]) if match else 0)
        if not all(math.isfinite(value) and value > 0 for value in dimensions):
            raise DiagramError('SVG 尺寸无效')
        visible = {'text', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline',
                   'polygon', 'image', 'foreignObject', 'use'}
        if not any(node.tag.rsplit('}', 1)[-1] in visible for node in root.iter()
                   if node is not root):
            raise DiagramError('SVG 没有图形内容')
        if engine == 'plantuml' and 'Syntax Error' in content.decode('utf-8', 'replace'):
            raise DiagramError('PlantUML 返回语法错误图')
    elif path.suffix == '.png':
        if len(content) < 33 or not content.startswith(b'\x89PNG\r\n\x1a\n'):
            raise DiagramError('导出不是 PNG')
        offset, chunks, compressed = 8, [], bytearray()
        while offset < len(content):
            if offset + 12 > len(content):
                raise DiagramError('PNG 区块不完整')
            length = struct.unpack('>I', content[offset:offset + 4])[0]
            end = offset + 12 + length
            if end > len(content):
                raise DiagramError('PNG 区块不完整')
            kind = content[offset + 4:offset + 8]
            data = content[offset + 8:offset + 8 + length]
            crc = struct.unpack('>I', content[end - 4:end])[0]
            if zlib.crc32(kind + data) & 0xffffffff != crc:
                raise DiagramError('PNG 校验失败')
            if kind == b'IHDR':
                if chunks or length != 13:
                    raise DiagramError('PNG 头无效')
                width, height = struct.unpack('>II', data[:8])
                if not width or not height:
                    raise DiagramError('PNG 尺寸无效')
            elif kind == b'IDAT':
                compressed.extend(data)
            elif kind == b'IEND' and (length or end != len(content)):
                raise DiagramError('PNG 结束区块无效')
            chunks.append(kind)
            offset = end
        if not chunks or chunks[0] != b'IHDR' or chunks[-1] != b'IEND' or not compressed:
            raise DiagramError('PNG 缺少完整图像区块')
        try:
            decoder = zlib.decompressobj()
            pixels = decoder.decompress(compressed, 64 * 1024 * 1024)
            if not pixels or not decoder.eof or decoder.unused_data:
                raise DiagramError('PNG 像素数据无效或过大')
        except zlib.error as exc:
            raise DiagramError('PNG 像素数据无法解码') from exc
    else:
        raise DiagramError('输出仅支持 SVG 或 PNG')


def render(project, source, out, engine, *, layout='none', base_sha256=None, timeout=60):
    project = Path(project).resolve()
    source, out = inside(project, source), inside(project, out)
    receipt_path = out.with_name(out.name + '.receipt.json')
    if out.exists() or receipt_path.exists():
        raise DiagramError('拒绝覆盖已有图表或调用记录，请使用新版本文件名')
    if not source.is_file():
        raise DiagramError('图源不存在')
    extensions = {'drawio': '.drawio', 'plantuml': '.puml', 'mermaid': '.mmd'}
    if engine not in extensions or source.suffix != extensions[engine]:
        raise DiagramError('工具与图源扩展名不匹配')
    if out.suffix not in ('.svg', '.png'):
        raise DiagramError('输出仅支持 SVG 或 PNG')
    if layout not in ('none', 'libavoid', 'verticalFlow', 'horizontalFlow'):
        raise DiagramError('布局参数无效')
    if engine != 'drawio' and layout != 'none':
        raise DiagramError('layout 仅适用于 Draw.io')
    if not 1 <= timeout <= 300:
        raise DiagramError('渲染超时须为 1—300 秒')
    before = digest(source)
    if not isinstance(base_sha256, str) or not re.fullmatch('[a-f0-9]{64}', base_sha256):
        raise DiagramError('必须提供 64 位小写十六进制 base_sha256')
    if before != base_sha256:
        raise DiagramError('图源版本冲突，请重新读取并合并')
    command = command_for(engine)
    if not command:
        raise DiagramError(f'{engine} 未安装；保留图源，不能标记已渲染')
    out.parent.mkdir(parents=True, exist_ok=True)
    output_format = out.suffix[1:]
    with tempfile.TemporaryDirectory(prefix='.diagram-', dir=out.parent) as folder:
        temporary = Path(folder) / out.name
        snapshot = Path(folder) / source.name
        snapshot.write_bytes(source.read_bytes())
        if digest(snapshot) != before:
            raise DiagramError('读取图源时版本改变，拒绝渲染')
        # Draw.io exports a copy; optional layout never mutates the retained source.
        if engine == 'drawio':
            command += ['-x', '-f', output_format, '-e', '-b', '24', '--disable-update',
                        '--theme', 'light', '-o', str(temporary)]
            if layout != 'none':
                command += ['--layout', layout]
            command += [str(snapshot)]
            payload = None
        elif engine == 'plantuml':
            command += [f'-t{output_format}', '-charset', 'UTF-8', '-pipe', '-failfast2']
            payload = snapshot.read_bytes()
        else:
            command += ['-i', str(snapshot), '-o', str(temporary), '-b', 'white']
            browser = os.environ.get('MERMAID_BROWSER_EXECUTABLE')
            if not browser and Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome').is_file():
                browser = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            if browser:
                if not Path(browser).is_file():
                    raise DiagramError('Mermaid 浏览器路径不存在')
                config = Path(folder) / 'puppeteer.json'
                config.write_text(json.dumps({'executablePath': browser}), encoding='utf-8')
                command += ['-p', str(config)]
            payload = None
        environment = dict(os.environ, PLANTUML_SECURITY_PROFILE='SANDBOX')
        try:
            completed = subprocess.run(command, input=payload, capture_output=True,
                                       timeout=timeout, env=environment)
        except subprocess.TimeoutExpired as exc:
            raise DiagramError(f'{engine} 渲染超时，未发布图表') from exc
        if completed.returncode:
            # Full logs remain the host's responsibility; do not print source or environment.
            raise DiagramError(f'{engine} 渲染失败，退出码 {completed.returncode}')
        if engine == 'plantuml':
            temporary.write_bytes(completed.stdout)
        if digest(source) != before:
            raise DiagramError('渲染期间图源改变，拒绝发布过期图表')
        validate_image(temporary, engine)
        if digest(source) != before:
            raise DiagramError('校验期间图源改变，拒绝发布过期图表')
        receipt = {'state': 'rendered', 'engine': engine, 'command': command,
                   'layout': layout, 'source_path': str(source.relative_to(project)),
                   'source_sha256': before, 'output_path': str(out.relative_to(project)),
                   'base_source_sha256': base_sha256, 'cas_result': 'matched',
                   'output_sha256': digest(temporary),
                   'created_at': datetime.now(timezone.utc).isoformat(),
                   'visual_review': 'NOT_RUN'}
        # Use exclusive creation to protect another renderer publishing the same filename.
        published = False
        receipt_created = False
        try:
            with out.open('xb') as file:
                published = True
                file.write(temporary.read_bytes())
            with receipt_path.open('x', encoding='utf-8') as file:
                receipt_created = True
                json.dump(receipt, file, ensure_ascii=False, indent=2)
            if digest(source) != before:
                raise DiagramError('发布期间图源改变，已撤回图表和记录')
        except Exception:
            if published:
                out.unlink(missing_ok=True)
            if receipt_created:
                receipt_path.unlink(missing_ok=True)
            raise
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    commands.add_parser('doctor')
    routing = commands.add_parser('plan')
    routing.add_argument('--settings', type=Path)
    routing.add_argument('--kind', required=True)
    routing.add_argument('--complex-flow', action='store_true')
    rendering = commands.add_parser('render')
    rendering.add_argument('--project', type=Path, required=True)
    rendering.add_argument('--source', type=Path, required=True)
    rendering.add_argument('--out', type=Path, required=True)
    rendering.add_argument('--engine', choices=('drawio', 'plantuml', 'mermaid'), required=True)
    rendering.add_argument('--layout', default='none')
    rendering.add_argument('--base-sha256', required=True)
    rendering.add_argument('--timeout', type=int, default=60)
    args = parser.parse_args()
    try:
        if args.action == 'doctor':
            result = doctor()
        elif args.action == 'plan':
            settings = json.loads(args.settings.read_text()) if args.settings else {}
            result = plan(settings, args.kind, complex_flow=args.complex_flow)
        else:
            result = render(args.project, args.source, args.out, args.engine,
                            layout=args.layout, base_sha256=args.base_sha256, timeout=args.timeout)
    except (DiagramError, OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('status') != 'blocked' else 1


if __name__ == '__main__':
    sys.exit(main())
