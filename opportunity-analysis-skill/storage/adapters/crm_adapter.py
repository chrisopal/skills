class CRMAdapter:
    """Extension adapter for customer CRM or MCP-backed CRM services.

    Keep the same method names and return shapes as OpportunitySQLiteAdapter.
    A host agent can pass credentials, endpoint URLs, tenant IDs, or MCP tool
    names through a config object when this adapter is implemented.
    """

    adapter_id = "crm"
    config_keys = ["endpoint", "tenant_id", "auth_ref", "object_mapping"]

    def __init__(self, config=None):
        self.config = config or {}

    def upsert_account(self, account):
        raise NotImplementedError("CRMAdapter.upsert_account is an extension point")

    def upsert_contact(self, contact):
        raise NotImplementedError("CRMAdapter.upsert_contact is an extension point")

    def upsert_opportunity(self, opportunity):
        raise NotImplementedError("CRMAdapter.upsert_opportunity is an extension point")

    def create_next_action(self, action):
        raise NotImplementedError("CRMAdapter.create_next_action is an extension point")

    def append_evidence(self, evidence):
        raise NotImplementedError("CRMAdapter.append_evidence is an extension point")
