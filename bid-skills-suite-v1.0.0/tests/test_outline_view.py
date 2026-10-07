import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from outline_view import ordered_sections


class OutlineViewTests(unittest.TestCase):
    def test_preorder_and_mixed_numbers_without_mutating_source(self):
        sections = [
            {'id': 'a', 'parent_id': None, 'number': '一', 'title': '资格'},
            {'id': 'b', 'parent_id': None, 'number': '二', 'title': '技术'},
            {'id': 'a1', 'parent_id': 'a', 'number': '一.1', 'title': '证明'},
            {'id': 'b1', 'parent_id': 'b', 'number': '二.1', 'title': '方案'},
            {'id': 'b11', 'parent_id': 'b1', 'number': '二.1.1', 'title': '架构'},
        ]
        before = copy.deepcopy(sections)
        rows = ordered_sections(sections)
        self.assertEqual([r['id'] for r in rows], ['a', 'a1', 'b', 'b1', 'b11'])
        self.assertEqual([r['display_number'] for r in rows], ['一、', '1.1', '二、', '2.1', '2.1.1'])
        self.assertEqual([r['depth'] for r in rows], [0, 1, 0, 1, 2])
        self.assertEqual(rows[2]['children_count'], 1)
        self.assertEqual(sections, before)

    def test_numeric_and_custom_format_numbers_are_preserved(self):
        rows = ordered_sections([
            {'id': 'a', 'parent_id': None, 'number': '9'},
            {'id': 'b', 'parent_id': 'a', 'number': '9.3'},
            {'id': 'c', 'parent_id': 'b', 'number': '（一）'},
        ])
        self.assertEqual([r['display_number'] for r in rows], ['9', '9.3', '（一）'])

    def test_child_before_parent_and_empty_outline(self):
        rows = ordered_sections([{'id': 'b', 'parent_id': 'a', 'number': '一.2'},
                                 {'id': 'a', 'parent_id': None, 'number': '一'}])
        self.assertEqual([r['id'] for r in rows], ['a', 'b'])
        self.assertEqual(rows[1]['display_number'], '1.2')
        self.assertEqual(ordered_sections([]), [])

    def test_invalid_tree_is_not_silently_flattened(self):
        cases = [
            [{'id': 'a', 'parent_id': 'missing'}],
            [{'id': 'a'}, {'id': 'a'}],
            [{'id': 'a', 'parent_id': 'a'}],
            [{'id': 'a', 'parent_id': 'b'}, {'id': 'b', 'parent_id': 'a'}],
            [{'number': '1'}],
        ]
        for sections in cases:
            with self.subTest(sections=sections), self.assertRaises(ValueError):
                ordered_sections(sections)


if __name__ == '__main__':
    unittest.main()
