# 投标 Skill 精简离线安装包

包含 **17 个投标 Skill + enterprise-diagrams 独立绘图 Skill**。解压下载的 ZIP 后，`packages/` 中每个 ZIP 是一个完整 Skill，包含自己的 SKILL.md、脚本、参考、Schema 和模板。保留 Draw.io、Mermaid 等可选引擎配置。

精简仅删除分发内容中的测试、展示截图、示例成稿、缓存和开发文件；保留运行时资源与绘图模板。没有附带客户原件、企业材料、模型、API Key 或 Python 环境。总包不是单个 Skill，**不要把整个总包上传为一个 Skill**。

## WorkBuddy

解压总包，在 WorkBuddy 的“技能 → 添加技能 → 上传技能”中逐个选择 `packages/` 下的 ZIP。按实际版本的界面入口操作；安装后确认 18 个技能已启用，新建任务调用 `bid-orchestrator`。

也可在当前解压目录执行（Python 3.10+）：

```bash
python3 install.py --agent workbuddy --dry-run
python3 install.py --agent workbuddy
```

默认目标为 `~/.workbuddy/skills/`；支持 `WORKBUDDY_CONFIG_DIR`。自定义安装目录时改用 `--dest`。

## Claude Code / Codex / 其他 Agent

在当前解压目录执行：

```bash
python3 install.py --agent claude-code --dry-run
python3 install.py --agent claude-code
```

默认写入 `~/.claude/skills/`。Codex 使用 `--agent codex`，遵循 `CODEX_HOME`，默认 `~/.codex/skills/`。

其他宿主，或仅安装到当前项目，指定它实际使用的 Skill 发现目录：

```bash
python3 install.py --dest /absolute/path/to/project/.claude/skills --dry-run
python3 install.py --dest /absolute/path/to/project/.claude/skills
```

Windows 将 `python3` 换为 `py -3` 或实际 Python 命令，路径也换为本机路径。无 Python 时可逐个解压 `packages/*.zip` 到宿主技能目录，使其结构为 `技能目录/bid-orchestrator/SKILL.md`，不能额外多套一层目录。安装器先校验所有 ZIP 的 SHA256 与路径，再写入；已有任何同名 Skill 或符号链接就停止，不覆盖，请先备份并移开旧目录。只校验完整包时，可对一个空目录运行 `--dry-run`，不会创建该目录。

## 运行准备与开始使用

安装规程与运行脚本是两件事。宿主需要能读取/写入项目文件、执行工具；仅聊天或受限云端不能据此视为可完整运行。安装不保证不同 Agent 的模型、子 Agent、生图或文档工具能力相同。

原生 DOCX/PDF 处理与校验依赖见 `requirements.txt`，建议安装到独立环境，然后告诉宿主使用其 Python 的绝对路径：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows 对应 `.venv\Scripts\python.exe`。Word/PDF 渲染、目录更新仍需 Word/LibreOffice 或宿主文档工具；OCR 按 `bid-source-intake/references/OCR_SETUP.md` 配置；飞书依赖宿主已授权的 CLI/Skill。界面示意调用宿主可用的生图能力，缺工具时保留缺口。无需部署 Bid Agent 应用。

安装后刷新宿主、新建会话，示例指令：

> 使用 bid-orchestrator 处理我提供的招标文件，在指定项目目录完成解析、分类、需求/评分/废标项提取、目录、材料 Wiki、完整章节写作、配图、审核、模拟专家评分及 Word/PDF 导出。先检查可用工具，缺材料要加亮提示，不虚构企业事实或实际执行结果；有未满足项不要标记正式评审通过。

完整说明与效果截图：[GitHub README](https://github.com/chrisopal/skills/tree/main/bid-skills-suite-v1.0.0)。本包验证覆盖压缩完整性、源文件一致性及隔离目录安装；不等于 WorkBuddy/Claude Code 内实际模型编标验收。
