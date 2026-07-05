# Storage Contract

所有写入和查询必须通过Storage Adapter完成，不允许LLM直接生成和执行SQL。

默认可运行实现是`src/opportunity_skill/storage.py`中的`OpportunitySQLiteAdapter`。
其他宿主（飞书、CRM、PostgreSQL、MCP工具）应实现同一组动作和返回值，不改变上层Pipeline。

## Adapter Selection

- `sqlite`: 默认闭环存储，零外部依赖。
- `feishu`: 扩展点，用于飞书多维表格、表格或文档。
- `crm`: 扩展点，用于客户CRM API或MCP工具。
- `postgres`: 扩展点，用于团队共享数据库。

外部Adapter必须从宿主配置中读取凭证引用，不得把token、secret或租户私密信息写入Skill包。

## Actions

- `upsert_account(account) -> account_id`
- `upsert_contact(contact) -> contact_id`
- `upsert_opportunity(opportunity) -> opportunity_id`
- `append_interaction(interaction) -> interaction_id`
- `append_evidence(evidence) -> evidence_id`
- `append_evidence_file(file_metadata) -> file_id`
- `link_evidence_to_field(map_item) -> map_id`
- `create_risk(risk) -> risk_id`
- `create_next_action(action) -> action_id`
- `query_opportunities(query_json) -> list`
- `get_opportunity_detail(opportunity_id) -> dict`

## Source Material Archive

默认SQLite实现会把可读原始文件复制到本地归档目录，并把文件元数据写入`evidence_files`：

- `evidence_id`
- `original_path`
- `archived_path`
- `relative_path`
- `file_name`
- `display_name`
- `mime_type`
- `size_bytes`
- `sha256`
- `is_image`

外部Adapter可以把文件上传到飞书Drive、CRM对象附件或对象存储，但必须保留同等字段或可渲染链接，确保商机详情页能展示缩略图和可点击材料链接。

## Safe Query Rule

自然语言查询必须先转换为`schemas/query.schema.json`格式，再由Query Service转换成参数化SQL。

## Config Shape

Adapter配置建议由宿主传入，格式示例：

```json
{
  "adapter": "feishu",
  "config": {
    "auth_ref": "FEISHU_APP_SECRET",
    "base_id": "base_xxx",
    "table_mapping": {
      "accounts": "tbl_accounts",
      "opportunities": "tbl_opportunities"
    }
  }
}
```
