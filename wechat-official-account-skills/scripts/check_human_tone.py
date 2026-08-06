#!/usr/bin/env python3
"""提示公众号中文稿中的模板化形状，不自动改稿，也不替代人工审校。"""

from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path


PIVOT_PATTERNS = (
    re.compile(r"(?:并)?不是[^。！？\n]{0,80}(?:而是|才是)"),
    re.compile(r"并非[^。！？\n]{0,80}而是"),
    re.compile(r"你以为[^。！？\n]{2,60}(?:其实|才发现|才知道)"),
    re.compile(r"(?:看似|表面上?)[^。！？\n]{2,60}(?:其实|实际|实则)"),
    re.compile(r"[^，。！？\n]{1,16}不重要，(?:重要|要紧)的是"),
    re.compile(r"大家都[^。！？\n]{2,60}(?:其实|真正|才是)"),
)

NOMINALIZATION_PATTERNS = (
    re.compile(
        r"进行(?:了|一次|一场|着)?[^。，！？\n]{0,10}"
        r"(?:调整|优化|升级|分析|讨论|沟通|梳理|复盘|迭代|探索|规划)"
    ),
    re.compile(r"实现了?[^。，！？\n]{0,14}(?:提升|增长|突破|转变|落地)"),
    re.compile(r"完成了?对[^。，！？\n]{0,16}的"),
)

ROAD_SIGNS = (
    "更值得关注的是",
    "值得注意的是",
    "需要指出的是",
    "更深一层",
    "还有一层",
    "只说对了一半",
    "从某种意义上说",
    "真正麻烦的地方是",
    "真正值得企业学的是",
    "下一步该补的是",
)

CONJUNCTIONS = (
    "因为",
    "所以",
    "但是",
    "然而",
    "同时",
    "此外",
    "而且",
    "并且",
    "因此",
    "不仅",
)

OPENERS = (
    "其实",
    "不过",
    "当然",
    "所以",
    "但是",
    "很多人",
    "问题是",
    "更重要的是",
    "说到这里",
)


def han_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def mask_non_prose(text: str) -> str:
    def mask(match: re.Match[str]) -> str:
        return "".join("\n" if char == "\n" else " " for char in match.group())

    patterns = (
        re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", re.DOTALL),
        re.compile(r"```.*?```", re.DOTALL),
        re.compile(r"`[^`\n]*`"),
        re.compile(r"\]\([^\n)]*\)"),
        re.compile(r"https?://[^\s)>]+"),
        re.compile(r"<[^>\n]+>"),
    )
    for pattern in patterns:
        text = pattern.sub(mask, text)
    return text


def prose_paragraphs(text: str) -> list[tuple[int, str]]:
    paragraphs: list[tuple[int, str]] = []
    cursor = 0
    for block in re.split(r"\n\s*\n", text):
        position = text.find(block, cursor)
        cursor = max(cursor, position + len(block))
        clean = re.sub(r"[>*_`]", "", block).strip()
        if not clean or clean.startswith(("#", "http", "![", "```")):
            continue
        if re.match(r"^(?:[-+*]|\d+[.、])\s", clean):
            continue
        if han_count(clean) >= 8:
            paragraphs.append((position, clean))
    return paragraphs


def sentence_length_cv(text: str) -> tuple[float, int] | None:
    lengths = [
        han_count(match.group())
        for match in re.finditer(r"[^。！？!?\n]+[。！？!?]", text)
        if han_count(match.group()) >= 4
    ]
    if len(lengths) < 12:
        return None
    mean = sum(lengths) / len(lengths)
    variance = sum((value - mean) ** 2 for value in lengths) / len(lengths)
    return (variance**0.5 / mean, len(lengths))


def anaphora_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    for sentence in re.finditer(r"[^。！？!?\n]+(?:[。！？!?]|$)", text):
        clauses = [
            clause.strip()
            for clause in re.split(r"[，、；,;]", sentence.group())
            if han_count(clause) >= 3
        ]
        for index in range(len(clauses) - 2):
            starts = [clause[:2] for clause in clauses[index : index + 3]]
            if len(set(starts)) == 1 and re.fullmatch(r"[\u4e00-\u9fff]{2}", starts[0]):
                warnings.append(
                    f"第 {line_number(text, sentence.start())} 行疑似三项同构排比：{sentence.group().strip()[:46]}"
                )
                break
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="检查公众号稿件中的模板化中文形状")
    parser.add_argument("path", help="Markdown 或文本路径；使用 - 从标准输入读取")
    args = parser.parse_args()

    try:
        source = (
            sys.stdin.read()
            if args.path == "-"
            else Path(args.path).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError) as error:
        print(f"无法读取稿件：{error}", file=sys.stderr)
        return 2

    prose = mask_non_prose(source)
    total_han = han_count(prose)
    if total_han == 0:
        print("没有检测到汉字。", file=sys.stderr)
        return 2

    warnings: list[str] = []

    for pattern in PIVOT_PATTERNS:
        for match in pattern.finditer(prose):
            warnings.append(
                f"第 {line_number(source, match.start())} 行疑似动作级翻案：{match.group().strip()[:46]}"
            )

    for phrase in ROAD_SIGNS:
        for match in re.finditer(re.escape(phrase), prose):
            warnings.append(f"第 {line_number(source, match.start())} 行出现洞察路标：{phrase}")

    for pattern in NOMINALIZATION_PATTERNS:
        for match in pattern.finditer(prose):
            warnings.append(
                f"第 {line_number(source, match.start())} 行疑似名词化动作：{match.group().strip()[:40]}"
            )

    warnings.extend(anaphora_warnings(prose))

    conjunction_hits = [
        term
        for term in CONJUNCTIONS
        for _ in re.finditer(re.escape(term), prose)
    ]
    if total_han >= 600 and len(conjunction_hits) * 1000 / total_han > 7:
        counts = collections.Counter(conjunction_hits).most_common(4)
        detail = "、".join(f"{term} {count} 次" for term, count in counts)
        density = len(conjunction_hits) * 1000 // total_han
        warnings.append(f"连词密度偏高，每千字 {density} 个：{detail}")

    cv_result = sentence_length_cv(prose)
    if cv_result and cv_result[0] < 0.42:
        warnings.append(
            f"{cv_result[1]} 个句子的长度过于接近，变异系数 {cv_result[0]:.2f}；检查是否缺少长短变化"
        )

    paragraphs = prose_paragraphs(prose)
    if len(paragraphs) >= 10:
        one_sentence = sum(
            len(re.findall(r"[。！？!?]", value)) <= 1
            for _, value in paragraphs
        )
        if one_sentence / len(paragraphs) >= 0.75:
            ratio = one_sentence / len(paragraphs)
            warnings.append(
                f"可识别段落中 {ratio:.0%} 只有一句，检查是否在排队喊结论"
            )

    opener_counts = collections.Counter()
    opener_lines: dict[str, int] = {}
    for position, paragraph in paragraphs:
        value = paragraph.lstrip("“‘\"（(")
        for opener in OPENERS:
            if value.startswith(opener):
                opener_counts[opener] += 1
                opener_lines.setdefault(opener, line_number(source, position))
                break
    for opener, count in opener_counts.items():
        if count >= 4:
            warnings.append(
                f"从第 {opener_lines[opener]} 行附近开始，"
                f"段落以“{opener}”开头 {count} 次"
            )

    print(f"汉字数 {total_han}，提示 {len(warnings)} 项")
    if warnings:
        print("\n需要人工判断")
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("\n未发现检查器覆盖的模板化形状。")
    print("\n脚本只提示形状。请人工检查材料门槛、段落新增信息和事实边界。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
