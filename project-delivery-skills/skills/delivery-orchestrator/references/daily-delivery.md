# 实际输入验证 核心文档 日常操作

## 材料冻结与独立执行

先实际读取用户指定的已授权脱敏材料；没有真实材料时不能将测试夹具改名为真实项目。准备显式输入清单：

```json
{
  "project_id": "CUSTOMER-001",
  "material_origin": "actual",
  "authorization_note": "本次任务已授权的本机材料与用途",
  "redaction_note": "脱敏范围与未完成项",
  "materials": [
    {"id":"SRC-CONTRACT","role":"contract","path":"contract.docx"},
    {"id":"SRC-TECH","role":"technical_agreement","path":"technical.md"},
    {"id":"SRC-DISCOVERY","role":"discovery","path":"meeting.txt"}
  ]
}
```

路径相对清单所在目录。支持角色 contract、technical_agreement、discovery、supplement、customer_template。actual 是提交人声明，不是工具认证。TXT/MD/CSV/JSON按逻辑行、DOCX按正文段落摘录；DOCX不是页码解析，页眉/批注/嵌入附件没有自动读取。其他格式列为未读，交给现有解析/OCR/转录能力并补读取覆盖，不从文件名猜结论。

```bash
python3 scripts/field_validation.py prepare /absolute/manifest.json --out /absolute/new-evaluation
```

读取 intake.json、原件快照与 agent-task.md，按任务调用各 Skill。此任务只规定输入、输出和来源契约，没有业务参考答案。独立评估时不要把已知问题/预期答案提供给执行者。输出每条业务结论的精确来源、原文及定位到 claims.json，另登记合同、需求、蓝图、计划、设计和验收草稿及真实使用记录。

```bash
python3 scripts/field_validation.py audit /absolute/new-evaluation
```

自动检查仅证明原件/摘录未变、引文定位一致及运行登记有效，不证明引文支持结论或业务完整。还要独立审核范围冲突、未提供附件、承诺授权、验收负责人和真实联调依赖。保持 technical_pass、semantic_verdict、实际材料来源和客户确认四个独立结果。模拟确认不可进入实际项目。

## 核心文档生成

用已具备 python-docx 的运行环境执行：

```bash
python3 scripts/export_core_documents.py --project /absolute/project --out /absolute/new-core-documents
```

读取最新候选；选中核心记录缺失、损坏或依赖过期时先修复。生成启动、业务蓝图、详细实施设计、WBS、接口迁移、验收六套 DOCX/MD，以及精确来源与有效基线清单。宽表拆成重复编号的业务分组，保持全部字段；空缺明确待确认。输出只支持讨论稿，不自动取得客户确认或独立审核。

输出目录含内部设计、计划、接口及版本清单，不能整体对客发送。客户草稿已作字段过滤，正文敏感信息仍需 delivery-artifact-review 人工语义复核。实际对客包继续走既有审核/确认白名单契约。回读实际 DOCX/MD 和来源，并用已有 Office 渲染能力检查所有页面，文件生成不等于版式通过。

## 日常操作闭环

```bash
python3 scripts/daily_workbench.py /absolute/project --port 18763
```

只对本机开放。沿用实际主账、保留旧修订；项目目录仍须单写入，不与其他CLI/编辑器并发修改。打开工作台后先读取当前版本：

- 进度：选择已有工作包，记录实际结果、下一步与证据；不改变批准计划。完成声明需关联已登记证据，仍需业务核验。
- 工时：提交人员/日期/工作包/工时/费率口径；未知费率或剩余工作保持未知。提交不代表审核。
- 风险：区分风险/已发生问题/质量事项；关闭须精确证据，保留责任人与措施。
- 变更：仅申请，标明影响范围、计划/成本/验收影响及待决项；批准与完整应用继续由 delivery-change-control 和既有运行入口负责。

当前周报从操作记录及项目主账重新读取生成，保留来源版本。内部与客户稿分开，客户稿只读取明确客户可见记录并继续待审核。过期页面保存必须提示冲突、刷新后重填，不能静默覆盖。界面不认证人员身份、签署或ERP事实；本机录入的自由文本仍须事实核验。
