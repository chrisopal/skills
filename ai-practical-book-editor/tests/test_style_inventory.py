"""Lexical inventory checks only; no test below establishes editorial quality."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('style_inventory',Path(__file__).resolve().parents[1]/'scripts'/'audit_inventory.py')
assert spec and spec.loader
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class StyleInventoryTests(unittest.TestCase):
    def test_evaluative_heading_count_is_only_a_count(self):
        r=module.inventory('# 第1章 示例\n## 最值得记住的事\n正文\n')
        self.assertEqual(r['phrase_counts_by_block_type']['最值得']['heading'],1)
        self.assertNotIn('ai_probability',r)
        self.assertNotIn('violations',r)

    def test_archived_prompt_is_separate(self):
        r=module.inventory('# 第1章 示例\n```text\n最值得保留的事\n```\n')
        self.assertEqual(r['phrase_counts_by_block_type']['最值得']['code_or_prompt'],1)
        self.assertEqual(r['phrase_counts_by_block_type']['最值得'].get('narrative',0),0)

    def test_normal_next_step_is_not_a_style_phrase(self):
        r=module.inventory('# 第1章 示例\n|事项|下一步|\n|查看|核对原文|\n')
        self.assertNotIn('下一步',r['phrase_counts_by_block_type'])

    def test_real_business_value_not_blanket_matched(self):
        r=module.inventory('# 第1章 示例\n需要比较投资价值与使用成本。\n')
        self.assertEqual(sum(r['phrase_counts_by_block_type']['真正的价值'].values()),0)

    def test_new_stock_phrase_can_be_counted(self):
        r=module.inventory('# 第1章 示例\n接下来重点聚焦问题。\n')
        self.assertEqual(r['phrase_counts_by_block_type']['重点聚焦']['narrative'],1)

    def test_quote_count_does_not_produce_auto_edit(self):
        text='# 第1章 示例\n错误示例：“最值得保留的事”。\n'
        r=module.inventory(text)
        self.assertEqual(r['phrase_counts_by_block_type']['最值得']['narrative'],1)
        self.assertNotIn('revised_text',r)
        self.assertNotIn('edits',r)

if __name__=='__main__':unittest.main()
