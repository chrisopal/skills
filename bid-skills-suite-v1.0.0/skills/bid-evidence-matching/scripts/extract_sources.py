#!/usr/bin/env python3
"""Conservative native extraction with explicit, selective PaddleOCR support."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

OCR_MIN_CONFIDENCE = 0.80
ARTIFACT_ID = "ART-01-NATIVE"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _confidence(value: float | str | None) -> float:
    try:
        result = float(value if value is not None else os.environ.get("BID_OCR_MIN_CONFIDENCE", OCR_MIN_CONFIDENCE))
    except (TypeError, ValueError):
        raise ValueError("OCR 最低置信度必须是 0 到 1 之间的数字") from None
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ValueError("OCR 最低置信度必须是 0 到 1 之间的数字")
    return result


def _revision(
    project: Path,
    project_id: str,
    artifact_id: str,
    explicit: int | None,
    previous: Path | None,
) -> int:
    """Return a monotonic revision after validating same-project history."""

    def valid_revision(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    previous_path: Path | None = None
    if previous is not None:
        previous_path = previous.expanduser().resolve()
        if not previous_path.is_relative_to(project):
            raise ValueError("previous产物必须位于当前项目目录内")
        if not previous_path.is_file():
            raise ValueError("previous产物不存在")

    candidates: list[Path] = []
    if previous_path is not None:
        candidates.append(previous_path)
    artifacts = project / "artifacts"
    if artifacts.is_dir():
        candidates.extend(sorted(artifacts.rglob("*.json")))

    revisions: list[int] = []
    seen_paths: set[Path] = set()
    previous_record: dict | None = None
    for path in candidates:
        if path in seen_paths:
            continue
        seen_paths.add(path)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            if path == previous_path:
                raise ValueError("previous产物不是有效JSON") from None
            continue
        if not isinstance(value, dict):
            if path == previous_path:
                raise ValueError("previous产物结构无效")
            continue
        if path == previous_path:
            previous_record = value
        if value.get("artifact_id") != artifact_id:
            continue
        if value.get("project_id") != project_id:
            raise ValueError("同artifact_id产物属于其他项目")
        if not valid_revision(value.get("revision")):
            raise ValueError("同artifact_id产物revision无效")
        revisions.append(value["revision"])

    if previous_path is not None:
        if previous_record is None:
            raise ValueError("previous产物缺少可匹配的artifact_id")
        if previous_record.get("artifact_id") != artifact_id:
            raise ValueError("previous产物artifact_id不匹配")
        if previous_record.get("project_id") != project_id:
            raise ValueError("previous产物项目不匹配")
        if not valid_revision(previous_record.get("revision")):
            raise ValueError("previous产物revision无效")

    if len(revisions) != len(set(revisions)):
        raise ValueError("同artifact_id存在重复revision")
    highest = max(revisions, default=0)
    if explicit is not None:
        if not valid_revision(explicit):
            raise ValueError("revision必须是大于等于1的整数")
        if explicit <= highest:
            raise ValueError("显式revision必须大于当前最高revision")
        return explicit
    return highest + 1


def _render_pdf_page(page) -> bytes:  # type: ignore[no-untyped-def]
    """Render at a readable resolution without writing an intermediate file."""

    import fitz

    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    return pixmap.tobytes("png")


def extract(
    project: Path,
    project_id: str,
    source_ids: list[str] | None = None,
    ocr: str | None = None,
    *,
    ocr_api_url: str | None = None,
    ocr_api_key: str | None = None,
    ocr_auth_scheme: str | None = None,
    allow_remote_ocr: bool = False,
    ocr_timeout: float = 30.0,
    min_confidence: float | None = None,
    revision: int | None = None,
    previous: Path | None = None,
) -> dict:
    """Extract registered sources, optionally OCRing selected image-like pages.

    ``ocr`` is intentionally opt-in. Its only supported value is
    ``paddle-service``. ``source_ids`` limits work to registered source IDs and
    is used by the parent knowledge workflow for supplier-only extraction.
    """

    project = project.resolve()
    registry = json.loads((project / "inputs/source-registry.json").read_text(encoding="utf-8"))
    actual_project_id = json.loads((project / "work/project.json").read_text(encoding="utf-8")).get("project_id")
    if not actual_project_id or project_id != actual_project_id:
        raise ValueError("请求项目ID与工作目录不一致")
    if ocr not in {None, "paddle-service"}:
        raise ValueError("--ocr只支持paddle-service")
    result_revision = _revision(project, project_id, ARTIFACT_ID, revision, previous)
    threshold = _confidence(min_confidence) if ocr == "paddle-service" else OCR_MIN_CONFIDENCE
    entries = registry.get("sources", [])
    requested = None if source_ids is None else list(source_ids)
    if requested is not None and len(set(requested)) != len(requested):
        raise ValueError("--source-id不能重复")
    known_ids = {entry.get("source_id") for entry in entries}
    if requested is not None:
        unknown = [sid for sid in requested if sid not in known_ids]
        if unknown:
            raise ValueError("来源ID不存在：" + ",".join(unknown))
        selected_ids = set(requested)
        entries = [entry for entry in entries if entry.get("source_id") in selected_ids]

    client = None
    if ocr == "paddle-service":
        from paddle_ocr import make_client

        client = make_client(
            url=ocr_api_url,
            api_key=ocr_api_key,
            auth_scheme=ocr_auth_scheme,
            allow_remote=allow_remote_ocr,
            timeout=ocr_timeout,
        )

    docs: list[dict] = []
    blocks: list[dict] = []
    audit: list[dict] = []
    warnings: list[str] = []
    blockers: list[str] = []
    inputs: list[dict] = []
    for entry in entries:
        rel = Path(entry["relative_path"])
        path = (project / rel).resolve()
        sid = entry["source_id"]
        review = False
        source_failed = False
        if rel.is_absolute() or ".." in rel.parts or not path.is_relative_to(project):
            raise ValueError("来源路径越界")
        actual_hash = sha(path)
        if actual_hash != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            raise ValueError("原件身份变更：" + sid)
        row = {
            "source_id": sid,
            "filename": path.name,
            "relative_path": rel.as_posix(),
            "sha256": actual_hash,
            "bytes": path.stat().st_size,
            "role": entry["role"],
            "revision": entry["revision"],
            "duplicate_group": None,
            "status": "parsed",
        }
        inputs.append(
            {
                "artifact_id": sid,
                "revision": entry["revision"],
                "relative_path": rel.as_posix(),
                "sha256": actual_hash,
            }
        )
        block_index = [0]

        def add(text: str, location: str, page: int | None = None, method: str = "native") -> None:
            if text.strip():
                block_index[0] += 1
                blocks.append(
                    {
                        "block_id": f"{sid}-B{block_index[0]:05d}",
                        "source_id": sid,
                        "location": location,
                        "page": page,
                        "text": text,
                        "method": method,
                    }
                )

        def ocr_page(image: bytes, page_number: int, reason: str, mandatory: bool) -> None:
            nonlocal review, source_failed
            try:
                result = client.recognize(image)  # type: ignore[union-attr]
            except RuntimeError as exc:
                review = True
                if mandatory:
                    source_failed = True
                    blockers.append(f"{sid}: P{page_number} OCR失败（{str(exc)}）")
                    status = "failed"
                    note = f"OCR失败；原生原因：{reason}"
                else:
                    warnings.append(
                        f"{sid}: P{page_number} 补充OCR失败，原生文字保留但图像区域仍需人工复核。"
                    )
                    status = "needs_review"
                    note = f"补充OCR失败，原生文字保留；图像区域仍需复核；原生原因：{reason}"
                audit.append(
                    {
                        "source_id": sid,
                        "page": page_number,
                        "status": status,
                        "method": "ocr",
                        "note": note,
                    }
                )
                return
            lines = result.text.splitlines() or [result.text]
            for line_number, line in enumerate(lines, 1):
                add(line, f"P{page_number}/OCR{line_number}", page_number, "ocr")
            low = result.confidence < threshold
            review = review or low
            note = (
                f"OCR逐页提交PNG，识别{result.line_count}行，最低置信度={result.confidence:.3f}；"
                f"{'低置信度，需人工复核' if low else '置信度达到配置阈值'}；"
                f"原生原因：{reason}"
            )
            audit.append(
                {
                    "source_id": sid,
                    "page": page_number,
                    "status": "needs_review" if low else "processed",
                    "method": "ocr",
                    "note": note,
                }
            )

        try:
            suffix = path.suffix.lower()
            if suffix in {".md", ".txt"}:
                for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                    add(line, f"L{line_number}")
            elif suffix == ".docx":
                from docx import Document
                from docx.table import Table
                from docx.text.paragraph import Paragraph

                doc = Document(path)
                for body_index, child in enumerate(doc.element.body, 1):
                    if child.tag.endswith("}p"):
                        add(Paragraph(child, doc).text, f"body[{body_index}]/paragraph")
                    elif child.tag.endswith("}tbl"):
                        table = Table(child, doc)
                        for row_number, cells in enumerate(table.rows, 1):
                            for column_number, cell in enumerate(cells.cells, 1):
                                add(cell.text, f"body[{body_index}]/table/r{row_number}/c{column_number}")
                seen: set[int] = set()
                for section in doc.sections:
                    for part in (section.header, section.footer):
                        if id(part._element) in seen:
                            continue
                        seen.add(id(part._element))
                        for number, paragraph in enumerate(part.paragraphs, 1):
                            add(paragraph.text, f'{part._element.tag.split("}")[-1]}/p{number}')
                review = True
                warnings.append(
                    sid
                    + (": DOCX页码依赖渲染，原生提取不保证文本框、修订、批注及"
                       "复杂合并表完整，需复核。")
                )
            elif suffix == ".pdf":
                import fitz

                with fitz.open(path) as document:
                    if document.needs_pass:
                        raise ValueError("加密PDF需要人工提供可读取版本")
                    for page_number, page in enumerate(document, 1):
                        text = page.get_text("text")
                        images = bool(page.get_images(full=True))
                        native_sufficient = len(text.strip()) >= 30 and "\ufffd" not in text
                        needs_ocr = not native_sufficient
                        supplemental_ocr = images and native_sufficient
                        reason = (
                            "含图片且原生文字充分（补充OCR）"
                            if supplemental_ocr
                            else "文字稀少、编码异常或图像页"
                            if needs_ocr
                            else "原生文字层"
                        )
                        add(text, f"P{page_number}", page_number)
                        if ocr == "paddle-service" and (needs_ocr or supplemental_ocr):
                            ocr_page(
                                _render_pdf_page(page),
                                page_number,
                                reason,
                                mandatory=needs_ocr,
                            )
                        else:
                            review = review or needs_ocr or supplemental_ocr
                            audit.append(
                                {
                                    "source_id": sid,
                                    "page": page_number,
                                    "status": "needs_review" if needs_ocr else "processed",
                                    "method": "native",
                                    "note": (
                                        "含图片／文字稀少／编码异常，需视觉或OCR复核"
                                        if needs_ocr
                                        else "已抽取文字层，仍须按任务核对表格和关键参数"
                                    ),
                                }
                            )
                if review and ocr is None:
                    warnings.append(
                        sid + ": 本脚本未执行OCR，不得把扫描或图像区域标为已完整读取。"
                    )
            elif suffix in {".png", ".jpg", ".jpeg"}:
                if ocr == "paddle-service":
                    ocr_page(path.read_bytes(), 1, "PNG/JPEG原件", mandatory=True)
                else:
                    review = True
                    audit.append(
                        {
                            "source_id": sid,
                            "page": 1,
                            "status": "needs_review",
                            "method": "none",
                            "note": "PNG/JPEG原件未启用OCR，保留原件并待人工或显式OCR复核",
                        }
                    )
                    warnings.append(
                        sid + ": PNG/JPEG仅登记原件；需显式--ocr paddle-service才能提取文字。"
                    )
            else:
                raise ValueError(
                    "此脚本不支持该格式；请使用已授权宿主工具或保留原件后受控转换"
                )
            if not any(block["source_id"] == sid for block in blocks):
                review = True
                warnings.append(sid + ": 没有提取到有效文字")
            if source_failed:
                row["status"] = "failed"
            elif review:
                row["status"] = "needs_review"
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            row["status"] = "failed"
            blockers.append(sid + ": " + str(exc))
        docs.append(row)

    complete = bool(docs) and all(document["status"] == "parsed" for document in docs)
    if not docs:
        blockers.append("未注册任何来源或筛选后没有来源")
    return {
        "schema_version": "1.0",
        "skill_id": "bid-source-intake",
        "project_id": project_id,
        "artifact_id": ARTIFACT_ID,
        "revision": result_revision,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blockers else "needs_review",
        "inputs": inputs,
        "summary": (
            "原生抽取结果；人工未核验，尚不是业务验收通过。"
            if ocr is None
            else "原生抽取并对选定扫描／图像页调用PaddleOCR服务；人工未核验，"
            "尚不是业务验收通过。"
        ),
        "data": {
            "documents": docs,
            "blocks": blocks,
            "page_audit": audit,
            "coverage": "complete" if complete else "partial",
        },
        "warnings": warnings,
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ocr", choices=["paddle-service"])
    parser.add_argument("--ocr-api-url", help="覆盖BID_OCR_API_URL；凭据不得放入URL")
    parser.add_argument("--ocr-auth-scheme", choices=["token", "bearer"])
    parser.add_argument("--ocr-timeout", type=float, default=30.0)
    parser.add_argument("--min-confidence", type=float)
    parser.add_argument("--allow-remote-ocr", action="store_true")
    parser.add_argument(
        "--source-id", action="append", dest="source_ids", help="只处理指定注册来源，可重复"
    )
    parser.add_argument("--revision", type=int)
    parser.add_argument("--previous", type=Path, help="指定同artifact_id旧产物，用于计算下一revision")
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError("输出已存在，请使用新的产物版本文件名")
        result = extract(
            args.project,
            args.project_id,
            source_ids=args.source_ids,
            ocr=args.ocr,
            ocr_api_url=args.ocr_api_url,
            ocr_auth_scheme=args.ocr_auth_scheme,
            allow_remote_ocr=args.allow_remote_ocr,
            ocr_timeout=args.ocr_timeout,
            min_confidence=args.min_confidence,
            revision=args.revision,
            previous=args.previous,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as output:
            json.dump(result, output, ensure_ascii=False, indent=2)
            output.write("\n")
        print(
            json.dumps(
                {
                    "output": str(args.out),
                    "status": result["status"],
                    "coverage": result["data"]["coverage"],
                },
                ensure_ascii=False,
            )
        )
        return 1 if result["blockers"] else 0
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
