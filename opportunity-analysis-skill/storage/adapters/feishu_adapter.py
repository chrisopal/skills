class FeishuAdapter:
    """Extension adapter for Feishu Docs, Sheets, or Bitable storage.

    Typical config values include app credentials, target app/table/document IDs,
    and field mappings for account, contact, opportunity, evidence, and actions.
    The default package does not ship credentials or perform Feishu API calls.
    """

    adapter_id = "feishu"
    config_keys = ["app_id", "app_secret_ref", "base_id", "table_mapping", "field_mapping"]

    def __init__(self, config=None):
        self.config = config or {}

    def upsert_account(self, account):
        raise NotImplementedError("FeishuAdapter.upsert_account is an extension point")

    def upsert_contact(self, contact):
        raise NotImplementedError("FeishuAdapter.upsert_contact is an extension point")

    def upsert_opportunity(self, opportunity):
        raise NotImplementedError("FeishuAdapter.upsert_opportunity is an extension point")

    def create_next_action(self, action):
        raise NotImplementedError("FeishuAdapter.create_next_action is an extension point")

    def append_evidence(self, evidence):
        raise NotImplementedError("FeishuAdapter.append_evidence is an extension point")
