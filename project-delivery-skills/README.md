# 软件项目交付 Skills 第一批

版本 0.1.0。17 个可独立调用的技能，覆盖软件定制开发与系统集成项目的交接、启动、调研、需求蓝图、总体计划、进度周报、资源工时/成本差旅、风险质量/变更和里程碑确认。

Agent 负责读取、分析和编写；运行工具负责可复现的登记、版本依赖、基线、金额和交付包检查。工具本身不生成业务结论、不转录录音、不认证客户身份、不发送文件、不开发业务系统、不执行生产上线。

## 安装与调用

项目运行/安装/结构检查仅需 Python 3.11+ 标准库。Office 导出复用现有 `python-docx`、`openpyxl`；没有这些库时仍可直接使用 Markdown/CSV 模板，不自动安装依赖。

```bash
python3 project-delivery-skills/scripts/validate_suite.py
python3 -m unittest discover -s project-delivery-skills/tests -v
# 完整 Office 集成测试须使用已有 python-docx/openpyxl 的 Python；
# 缺少时 2 项 Office 集成测试显式 skip，不影响标准库运行工具。
python3 project-delivery-skills/scripts/install.py --dest "$HOME/.codex/skills"
```

安装检查全部目标后再复制，有差异先停止，已有相同内容可重复使用。升级先保留用户修改并比较差异，不提供覆盖开关。安装后刷新技能列表或开启新会话。

向 Agent 发送：

> 使用 $delivery-orchestrator 推进当前软件定制与集成项目。工作目录为我指定的位置，先读取合同和技术协议，整理范围、客户配合项和待澄清问题，再准备启动会、调研计划、蓝图及 Master Plan。所有未确认事实保留未知；沿用已有授权，确认绑定实际版本。需要界面时用 enterprise-ui-design 蓝色风格。

单项任务也可以调用 `$delivery-discovery-planning`、`$delivery-business-blueprint`、`$delivery-reporting` 等，不要求补造完整流程历史。

## 第一批技能

| 技能 | 用途 |
|---|---|
| [delivery-orchestrator](skills/delivery-orchestrator/SKILL.md) | 恢复项目、编排、有效版本与产物登记 |
| [delivery-source-intake](skills/delivery-source-intake/SKILL.md) | 原件、读取覆盖、证据定位 |
| [delivery-contract-handover](skills/delivery-contract-handover/SKILL.md) | 合同义务、售前承诺、交接与范围 |
| [delivery-initiation-kickoff](skills/delivery-initiation-kickoff/SKILL.md) | 项目组织、启动会和客户配合 |
| [delivery-master-planning](skills/delivery-master-planning/SKILL.md) | WBS、依赖、里程碑、计划基线 |
| [delivery-discovery-planning](skills/delivery-discovery-planning/SKILL.md) | 调研对象、时间、内容、双方材料及输出 |
| [delivery-meeting-records](skills/delivery-meeting-records/SKILL.md) | 纪要、事实/观点/决定、行动项 |
| [delivery-requirements-baseline](skills/delivery-requirements-baseline/SKILL.md) | 需求、澄清、验收标准与基线 |
| [delivery-business-blueprint](skills/delivery-business-blueprint/SKILL.md) | 流程、页面/字段/权限、接口和确认范围 |
| [delivery-progress-control](skills/delivery-progress-control/SKILL.md) | 实际/预测偏差、延期影响与纠偏 |
| [delivery-resource-timesheets](skills/delivery-resource-timesheets/SKILL.md) | 人员容量、工时、暂估与核验 |
| [delivery-cost-expenses](skills/delivery-cost-expenses/SKILL.md) | 预算、人工/费用、完工预测和去重 |
| [delivery-risk-issue](skills/delivery-risk-issue/SKILL.md) | 风险、问题、质量事项及处置证据 |
| [delivery-change-control](skills/delivery-change-control/SKILL.md) | 变更影响、决策和完整应用 |
| [delivery-reporting](skills/delivery-reporting/SKILL.md) | 客户/内部周报及周会议程 |
| [delivery-milestone-acceptance](skills/delivery-milestone-acceptance/SKILL.md) | 阶段确认、交付和验收证据 |
| [delivery-artifact-review](skills/delivery-artifact-review/SKILL.md) | 事实、追溯、版本、敏感内容与文件回读 |

专业开发执行、专项 UI/接口/迁移工程、完整测试/上线及质保收尾属于后续批次。第一批可以登记这些环节已有的真实工程证据，并组织里程碑确认；不把登记能力当作已实现工程能力。

## 项目工具

```bash
RUNTIME="$HOME/.codex/skills/delivery-orchestrator/scripts/runtime.py"
PROJECT="/absolute/path/to/customer-project"
python3 "$RUNTIME" init "$PROJECT" --project-id CUSTOMER-001
python3 "$RUNTIME" source "$PROJECT" /absolute/path/to/contract.docx --id SRC-CONTRACT
# Agent 按契约编写实际成果 JSON，命令返回 SHA-256 供下游绑定。
python3 "$RUNTIME" register "$PROJECT" /absolute/path/to/requirements.json
python3 "$RUNTIME" status "$PROJECT"
python3 "$RUNTIME" validate "$PROJECT"
# 初次有效基线；已有基线修改必须经过实际授权的 change 记录。
python3 "$RUNTIME" activate "$PROJECT" REQ BLUEPRINT PLAN
python3 "$RUNTIME" apply-change "$PROJECT" CHANGE-001
```

[产物契约](skills/delivery-orchestrator/references/artifact-contract.md)包含各 kind 字段、状态、范围和精确引用。实际命令参数见 `--help`。项目目录不能并发写入；确认人的权限和证据真实性由业务核验。

## 模板与审阅

模板是可编辑 Markdown 文档与 CSV 台账，位于[公共模板目录](skills/delivery-orchestrator/assets/templates/)，由 `index.json` 登记。客户已有模板优先，通过字段映射适配。

```bash
# 使用已具备 python-docx/openpyxl 的 Python（Codex 可读取内置运行环境）。
python3 "$HOME/.codex/skills/delivery-orchestrator/scripts/export_templates.py" --out /absolute/path/to/template-kit
python3 "$HOME/.codex/skills/delivery-orchestrator/scripts/render_review.py" "$PROJECT" --out /absolute/path/to/review.html --view internal
```

Office 导出生成原生可编辑 DOCX 和 XLSX，不从截图重建。输出目录有冲突时停止。审阅页按 Enterprise UI Design 蓝色风格实现；internal 显示内部台账，customer 过滤内部数据。静态文件仅反映生成时状态，源变更后需重新生成。

准备客户包：

```bash
python3 "$RUNTIME" prepare-customer "$PROJECT" --ids BLUEPRINT WEEKLY --out /absolute/path/to/customer-pack --mode discussion
```

这一步只准备本地包，不发送。每个选定产物需当前独立 pass 审核；confirmed 模式另需同版本客户确认。工具白名单防止直接打包内部主账，仍需业务审核自然语言/附件中的敏感信息。

## 验证与边界

测试覆盖来源/产物篡改、版本依赖、候选与基线分离、变更失败不混用、确认/审核精确绑定、工时缺口、差旅/外包去重、客户过滤和非覆盖安装。Office 文件回读、浏览器和 Agent 业务复核见[第一批验证记录](docs/VALIDATION.md)。Word/XLSX 使用 Arial Unicode MS；跨机器打开时检查字体替换和分页。模板台账由 Agent 映射到共享 JSON 契约，首版没有自动双向同步。

模拟案例使用 purpose=simulation，模拟确认不能进入真实项目。JSON 校验、语义审查、实际文件可读、客户接受是不同证据，不互相替代。没有真实合同、客户回答或工程测试证据时保留草稿与明确缺口。
