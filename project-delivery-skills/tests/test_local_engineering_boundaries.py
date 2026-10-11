"""Additional actual HTTP/SQLite boundaries used by the complete delivery review."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import sqlite3
import unittest
from urllib.error import URLError


SPEC = importlib.util.spec_from_file_location(
    'delivery_local_boundaries_base', Path(__file__).with_name('test_local_engineering.py'))
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)


class LocalEngineeringBoundaryTests(unittest.TestCase):
    setUp = base.LocalEngineeringTests.setUp
    stop_server = base.LocalEngineeringTests.stop_server

    def test_title_boundary_and_normalization_survive_reopen(self):
        self.orders.create('O1', '  ' + '设' * 100 + '  ', 'A1', 'dispatcher')
        reopened = base.service.WorkOrders(self.base / 'orders.db', self.orders.assets_url)
        self.assertEqual(reopened.read('O1')['title'], '设' * 100)

    def test_path_like_asset_is_rejected_without_persistence(self):
        with self.assertRaisesRegex(ValueError, 'alphanumeric'):
            self.orders.create('O1', 'Inspect', '../A1', 'dispatcher')
        self.assertEqual(self.orders.reconcile()['count'], 0)

    def test_sql_looking_order_identifier_remains_literal(self):
        order_id = "O1'); DROP TABLE orders; --"
        self.orders.create(order_id, 'Inspect', 'A1', 'dispatcher')
        self.assertEqual(self.orders.read(order_id)['id'], order_id)
        self.orders.create('O2', 'Inspect again', 'A1', 'dispatcher')
        self.assertEqual(self.orders.reconcile()['count'], 2)

    def test_approval_of_missing_order_has_no_side_effect(self):
        with self.assertRaisesRegex(ValueError, 'transition'):
            self.orders.approve('MISSING', 'supervisor')
        self.assertEqual(self.orders.reconcile()['count'], 0)

    def test_concurrent_identical_replay_produces_one_order(self):
        def create(_):
            return self.orders.create('O1', 'Inspect', 'A1', 'dispatcher')
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(create, range(4)))
        self.assertTrue(all(item == results[0] for item in results))
        self.assertEqual(self.orders.reconcile(), {'count': 1, 'business_keys': ['O1']})

    def test_duplicate_key_migration_rolls_back_earlier_batch_row(self):
        self.orders.create('O1', 'Existing', 'A1', 'dispatcher')
        with self.assertRaises(sqlite3.IntegrityError):
            self.orders.migrate([
                {'id': 'O2', 'title': 'New', 'asset_id': 'A1', 'state': 'draft'},
                {'id': 'O1', 'title': 'Duplicate', 'asset_id': 'A1', 'state': 'draft'},
            ])
        self.assertEqual(self.orders.reconcile(), {'count': 1, 'business_keys': ['O1']})
        self.assertEqual(self.orders.read('O1')['title'], 'Existing')

    def test_unreachable_asset_service_leaves_no_order(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        with self.assertRaises(URLError):
            self.orders.create('O1', 'Inspect', 'A1', 'dispatcher')
        self.assertEqual(self.orders.reconcile()['count'], 0)


if __name__ == '__main__':
    unittest.main()
