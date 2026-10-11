"""Small local-only integration fixture, never a production deployment tool."""
import json
import sqlite3
from urllib.request import urlopen


class WorkOrders:
    def __init__(self, database, assets_url):
        self.database = str(database)
        self.assets_url = assets_url
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, title TEXT, asset TEXT, state TEXT)')

    def create(self, order_id, title, asset_id, role):
        if role != 'dispatcher':
            raise PermissionError('dispatcher required')
        if not order_id or not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
            raise ValueError('title must contain 1-100 characters')
        if not asset_id.isalnum():
            raise ValueError('asset identifier must be alphanumeric')
        with urlopen(f'{self.assets_url}/assets/{asset_id}', timeout=2) as response:
            asset = json.load(response)
        if asset['asset_id'] != asset_id:
            raise ValueError('asset business key mismatch')
        with sqlite3.connect(self.database) as db:
            prior = db.execute('SELECT title, asset FROM orders WHERE id=?', (order_id,)).fetchone()
            if prior:
                if prior != (title.strip(), asset_id):
                    raise ValueError('idempotency conflict')
            else:
                db.execute('INSERT INTO orders VALUES (?, ?, ?, ?)', (order_id, title.strip(), asset_id, 'draft'))
        return self.read(order_id)

    def read(self, order_id):
        with sqlite3.connect(self.database) as db:
            result = db.execute('SELECT id, title, asset, state FROM orders WHERE id=?', (order_id,)).fetchone()
        if result is None:
            raise KeyError(order_id)
        return dict(zip(('id', 'title', 'asset_id', 'state'), result))

    def approve(self, order_id, role):
        if role != 'supervisor':
            raise PermissionError('supervisor required')
        with sqlite3.connect(self.database) as db:
            changed = db.execute('UPDATE orders SET state=? WHERE id=? AND state=?', ('approved', order_id, 'draft')).rowcount
        if changed != 1:
            raise ValueError('invalid approval transition')
        return self.read(order_id)

    def backup(self, target):
        with sqlite3.connect(self.database) as source, sqlite3.connect(str(target)) as destination:
            source.backup(destination)

    def restore(self, backup):
        with sqlite3.connect(str(backup)) as source, sqlite3.connect(self.database) as destination:
            source.backup(destination)

    def migrate(self, rows):
        # Entire batch is atomic; fail without partially migrating the next row.
        with sqlite3.connect(self.database) as db:
            for item in rows:
                if item['state'] not in {'draft', 'approved'} or not item['id'] or not item['asset_id']:
                    raise ValueError('invalid migration row')
                db.execute('INSERT INTO orders VALUES (?, ?, ?, ?)', (item['id'], item['title'], item['asset_id'], item['state']))

    def reconcile(self):
        with sqlite3.connect(self.database) as db:
            keys = [row[0] for row in db.execute('SELECT id FROM orders ORDER BY id')]
        return {'count': len(keys), 'business_keys': keys}
