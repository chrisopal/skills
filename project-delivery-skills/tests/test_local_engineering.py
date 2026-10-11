"""Real local HTTP/SQLite operations for phase-two evidence, synthetic business data."""
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError

SPEC = importlib.util.spec_from_file_location('delivery_work_orders', Path(__file__).parent / 'fixtures/work_order_service.py')
service = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(service)


class Assets(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/assets/A1':
            payload = json.dumps({'asset_id': 'A1', 'name': 'Synthetic Pump'}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == '/assets/WRONG':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"asset_id":"OTHER"}')
        else:
            self.send_error(404)

    def log_message(self, *_):
        pass


class LocalEngineeringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Assets)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.orders = service.WorkOrders(self.base / 'orders.db', f'http://127.0.0.1:{self.server.server_port}')

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_http_mapping_persistence_and_idempotency(self):
        first = self.orders.create('O1', 'Inspect pump', 'A1', 'dispatcher')
        self.assertEqual(first, self.orders.create('O1', 'Inspect pump', 'A1', 'dispatcher'))
        reopened = service.WorkOrders(self.base / 'orders.db', self.orders.assets_url)
        self.assertEqual(reopened.read('O1')['asset_id'], 'A1')
        self.assertEqual(reopened.reconcile(), {'count': 1, 'business_keys': ['O1']})
        with self.assertRaisesRegex(ValueError, 'idempotency'):
            self.orders.create('O1', 'Changed payload', 'A1', 'dispatcher')

    def test_permissions_fields_and_approval_state(self):
        with self.assertRaises(PermissionError):
            self.orders.create('O1', 'Inspect pump', 'A1', 'guest')
        for title in ('', ' ' * 4, 'x' * 101):
            with self.assertRaises(ValueError):
                self.orders.create('O1', title, 'A1', 'dispatcher')
        self.orders.create('O1', 'Inspect pump', 'A1', 'dispatcher')
        with self.assertRaises(PermissionError):
            self.orders.approve('O1', 'dispatcher')
        self.assertEqual(self.orders.approve('O1', 'supervisor')['state'], 'approved')
        with self.assertRaises(ValueError):
            self.orders.approve('O1', 'supervisor')

    def test_http_success_with_wrong_business_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'business key'):
            self.orders.create('O1', 'Inspect pump', 'WRONG', 'dispatcher')
        self.assertEqual(self.orders.reconcile()['count'], 0)

    def test_missing_external_asset_leaves_no_order(self):
        with self.assertRaises(HTTPError):
            self.orders.create('O1', 'Inspect pump', 'MISSING', 'dispatcher')
        self.assertEqual(self.orders.reconcile()['count'], 0)

    def test_migration_counts_keys_and_restored_rollback(self):
        self.orders.create('O1', 'Inspect pump', 'A1', 'dispatcher')
        self.orders.backup(self.base / 'backup.db')
        self.orders.migrate([{'id': 'O2', 'title': 'Imported order', 'asset_id': 'A1', 'state': 'draft'}])
        self.assertEqual(self.orders.reconcile(), {'count': 2, 'business_keys': ['O1', 'O2']})
        self.orders.restore(self.base / 'backup.db')
        self.assertEqual(self.orders.reconcile(), {'count': 1, 'business_keys': ['O1']})
        self.assertEqual(self.orders.read('O1')['title'], 'Inspect pump')

    def test_failed_migration_is_atomic(self):
        rows = [{'id': 'O2', 'title': 'First', 'asset_id': 'A1', 'state': 'draft'},
                {'id': 'O3', 'title': 'Invalid', 'asset_id': 'A1', 'state': 'invalid'}]
        with self.assertRaises(ValueError):
            self.orders.migrate(rows)
        self.assertEqual(self.orders.reconcile(), {'count': 0, 'business_keys': []})


if __name__ == '__main__':
    unittest.main()
