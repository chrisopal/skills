class PostgresAdapter:
    """Extension adapter for shared team or enterprise PostgreSQL storage.

    Use the same storage contract as OpportunitySQLiteAdapter. Implementations
    should use parameterized SQL and the schema in storage/sqlite/schema.sql as
    the reference logical model.
    """

    adapter_id = "postgres"
    config_keys = ["dsn_ref", "schema", "ssl_mode"]

    def __init__(self, config=None):
        self.config = config or {}

    def upsert_account(self, account):
        raise NotImplementedError("PostgresAdapter.upsert_account is an extension point")

    def upsert_contact(self, contact):
        raise NotImplementedError("PostgresAdapter.upsert_contact is an extension point")

    def upsert_opportunity(self, opportunity):
        raise NotImplementedError("PostgresAdapter.upsert_opportunity is an extension point")

    def create_next_action(self, action):
        raise NotImplementedError("PostgresAdapter.create_next_action is an extension point")

    def append_evidence(self, evidence):
        raise NotImplementedError("PostgresAdapter.append_evidence is an extension point")
