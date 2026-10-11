# 通用 B 端售前方案 Skill 套件

版本：0.1.0。10个技能覆盖混合材料读取、需求、澄清、汇报脑图、选材、方案、大纲、内容包、PPT交接与审核。行业差异通过补充材料表达。

这是一套供 Codex 等 Agent 调用的技能和本地工具。Agent 负责语义工作；脚本负责可重复的提取、文件版本与检查。`runtime.py`不是一个在没有Agent时自动生成客户方案的模型服务。

## 安装与使用

Python 3.10或更新版本；工具本身仅用标准库。PDF文本提取可选已安装的 `pdftotext`；OCR、视觉读取和PPT能力使用客户端现有工具，缺失时明确报告，不自动安装依赖。

```bash
python3 presales-solution-skills/scripts/validate_suite.py
python3 -m unittest discover -s presales-solution-skills/tests -v
python3 presales-solution-skills/scripts/install.py --dest "$HOME/.codex/skills"
```

安装器复制10个兄弟目录并核对hash；已存在且内容一致可重复执行，有差异则停止，不覆盖用户已有技能。首次试装可指定另一个空目录。升级时先比较差异和保存本地修改，再由用户授权选择更新方式。安装后刷新技能列表或开启新会话。

直接发送给Agent：

> 使用 $presales-orchestrator，为当前客户资料制作一份内部售前交流方案。工作目录为我指定的项目目录，受众为业务负责人和IT负责人，先整理需求和脑图，再形成逐页方案。PPT使用本地ppt-master-plus。已有明确授权的步骤继续，未知事实保留限定，最终检查真实文件。

也可以只调用 `$presales-requirements`、`$presales-storyline`、`$presales-solution-review` 等单项能力。单项任务不要求补造完整流程历史。

## 技能入口

| Skill | 用途 |
|---|---|
| [presales-orchestrator](skills/presales-orchestrator/SKILL.md) | 总控、恢复和局部修订 |
| [presales-source-intake](skills/presales-source-intake/SKILL.md) | 原件快照、原文与读取覆盖 |
| [presales-requirements](skills/presales-requirements/SKILL.md) | 原子需求、角色及条件 |
| [presales-clarification](skills/presales-clarification/SKILL.md) | 问题、补答与影响 |
| [presales-storyline](skills/presales-storyline/SKILL.md) | 汇报脑图与主线 |
| [presales-material-matching](skills/presales-material-matching/SKILL.md) | 产品/公司/案例适用性 |
| [presales-solution-design](skills/presales-solution-design/SKILL.md) | 需求响应机制与方案边界 |
| [presales-outline-planning](skills/presales-outline-planning/SKILL.md) | 章节和逐页计划 |
| [presales-content-authoring](skills/presales-content-authoring/SKILL.md) | 可直接排版的内容包 |
| [presales-solution-review](skills/presales-solution-review/SKILL.md) | 方向、内容、真实文件审核 |

## 可执行项目工具

```bash
RUNTIME="$HOME/.codex/skills/presales-orchestrator/scripts/runtime.py"
PROJECT="/absolute/path/to/customer-project"
python3 "$RUNTIME" init "$PROJECT" --project-id CUSTOMER-001 --purpose internal-draft
python3 "$RUNTIME" source "$PROJECT" /absolute/path/to/customer.docx --id SRC-001
python3 "$HOME/.codex/skills/presales-source-intake/scripts/extract.py" /absolute/path/to/customer.docx --out "$PROJECT/work/source-readback.json"
# Agent 按契约写出各阶段成果，再登记；这里的JSON必须是真实任务产物。
python3 "$RUNTIME" register "$PROJECT" /absolute/path/to/artifact.json
python3 "$RUNTIME" status "$PROJECT"
python3 "$RUNTIME" validate "$PROJECT"
# 当前内容及独立审核均有效后才可执行：
python3 "$RUNTIME" prepare-ppt "$PROJECT" CONTENT --out "$PROJECT/ppt-handoff"
```

目录、文件和hash以实际命令返回值为准。遇到macOS `/tmp` 等符号链接别名，先解析到真实目录；项目路径禁止符号链接越界。

schema、阶段字段、review记录及确认边界见[交接契约](skills/presales-orchestrator/references/artifact-contract.md)；本地PPT接入见[适配说明](skills/presales-orchestrator/references/ppt-master-plus.md)。创建内容包可以参考[结构示例](skills/presales-orchestrator/assets/content.example.json)，示例没有真实客户证据且不能直接通过制作门槛。

## 有效性与限制

- 原件和成果都有稳定ID、修订和SHA-256；新源版本或外改触发下游stale，旧审核不能批准新版本。修订同一审核使用同artifact_id递增revision；未解决的同目标审核不能换ID后绕过。
- 制作包采用字段白名单；字段内的自然语言是否包含内部信息仍须Agent审核，不能把白名单当自动脱敏。
- 交付登记检查真实PPT页数、内容包映射、输出及渲染文件hash；语义引用、实际页序内容、图片可读性由审核技能执行。
- 本地索引采用单写者约定，不是数据库、并发调度器或防篡改签名系统。不要并行修改同一项目索引。
- `ready`、审核`pass`、业务确认与外发授权分别记录；CLI不会自动认证reviewer身份或客户确认。
- PPT使用外部技能；优先用户指定的本地`ppt-master-plus`，不复制其引擎或模板进入本套件。

设计与验证记录保存在仓库 `docs/plans/`；实际客户或模拟生成产物留在各项目目录，不纳入发布包。
