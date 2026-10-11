# 投标编制 Skill 套件

**版本 1.17.1 · 16 个业务 Skill + 1 个总控 Skill**

把招标文件解析、项目分类、需求与评分提取、目录、证据匹配、写作、配图、评审和 Word/PDF 导出串成一条可追溯的编标流程。安装到支持 `SKILL.md` 的宿主 Agent 后，由宿主模型和实际工具执行；不需要部署 Bid Agent 应用。

源码位于 [chrisopal/skills](https://github.com/chrisopal/skills) 的 `main` 分支。目录名 `bid-skills-suite-v1.0.0` 为兼容已有安装链接而保留，实际版本看本页与 `registry.json`。

## 安装：先拿到完整目录

```bash
git clone --branch main https://github.com/chrisopal/skills.git
cd skills/bid-skills-suite-v1.0.0
```

也可在 GitHub 下载 `main` 的源码 ZIP 并解压。**每个 `skills/bid-*` 文件夹才是一个 Skill**；不要把套件根目录当成单个 Skill，也不要只复制 `SKILL.md`。安装时保留该 Skill 的 `references/`、`assets/`、`scripts/` 等配套文件。

| 宿主 | 安装方式 | 安装后验证 |
|---|---|---|
| Codex 本地 | 完整复制或软链接 17 个 `bid-*` 到 `~/.codex/skills/`（自定义时为 `$CODEX_HOME/skills/`） | 新建会话，选择 `bid-orchestrator` |
| WorkBuddy 桌面端 | “专家·技能·连接器 → 技能 → 添加技能 → 上传技能”逐个导入本地包；技术用户也可复制完整目录 | “我安装的”中确认技能已启用，再新建本地任务 |
| 其他支持 Skills 的 Agent | 按宿主文档，将每个完整 Skill 目录放到其发现目录或导入单 Skill 包 | 核对名称、资源读取、脚本执行和实际输出 |
| 仅能聊天的宿主 | 提供目标 `SKILL.md` 及所需参考文件，按规程执行 | 不能据此宣称已原生安装，文件保存和导出能力需另核验 |

完整流程建议一次安装 17 个；单项使用也可以，但必须提供其必要上游结果。独立绘图 Skill [enterprise-diagrams](../enterprise-diagrams/README.md) 可作为第 18 个安装到同一发现目录，不替代 `bid-visuals`。

以上本地路径不会自动同步到云端、容器或远程 Agent。使用这些环境时，按宿主的安装方式提供完整 Skill，并让实际执行环境能读取项目目录、运行脚本及保存结果；不要把桌面端已发现当成云端已安装。

Mac/Linux 复制安装示例：从本套件根目录执行。默认目标为 Codex；安装到 WorkBuddy 时，将第一行改为 `BID_SKILL_DEST="${WORKBUDDY_CONFIG_DIR:-$HOME/.workbuddy}/skills"`。先检查所有同名目标，发现已有安装就停止，不覆盖。

```bash
BID_SKILL_DEST="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$BID_SKILL_DEST"
for skill in skills/bid-* ../enterprise-diagrams; do
  target="$BID_SKILL_DEST/${skill##*/}"
  if [ -e "$target" ] || [ -L "$target" ]; then
    echo "已存在，请先核对并备份：$target" >&2
    exit 1
  fi
done
for skill in skills/bid-* ../enterprise-diagrams; do
  cp -R "$skill" "$BID_SKILL_DEST/${skill##*/}"
done
```

Windows 可用文件管理器复制完整目录，或用 PowerShell：从本套件根目录执行，先将 `$bidSkillDest` 改成实际宿主目录。WorkBuddy 默认示例为 `$env:USERPROFILE\.workbuddy\skills`；自定义配置目录时以实际位置为准。

```powershell
$bidSkillDest = Join-Path $env:USERPROFILE '.workbuddy/skills'
$bidSources = @(Get-ChildItem './skills/bid-*' -Directory) + @(Get-Item '../enterprise-diagrams')
New-Item -ItemType Directory -Force $bidSkillDest | Out-Null
foreach ($item in $bidSources) {
    if (Test-Path (Join-Path $bidSkillDest $item.Name)) { throw "已存在：$($item.Name)，请先备份" }
}
foreach ($item in $bidSources) { Copy-Item $item.FullName (Join-Path $bidSkillDest $item.Name) -Recurse }
```

需要上传包时，先在本套件目录运行：

```bash
python scripts/refresh_distribution.py
python scripts/check_suite.py
```

这会在本地生成 `installable-zips/` 下 17 个单 Skill ZIP。ZIP 是生成物，**GitHub 源码中不预置这些包**；刷新分发需要保留同一仓库相邻的 `enterprise-diagrams/`。独立绘图 Skill 的打包方法见其 [README](../enterprise-diagrams/README.md)。更详细的安装与更新步骤见 [先读我](START_HERE_先读我.md)。

## 准备运行能力

Skill 不附带模型、API Key、OCR 服务或办公软件。阅读规程不要求 Python；运行辅助脚本需要 **Python 3.10+**，建议在套件目录创建虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/check_suite.py
```

Windows 对应解释器为 `.venv\Scripts\python.exe`。告诉宿主使用该解释器的绝对路径；安装依赖并不保证宿主默认 `python` 指向它。仅结构校验可安装 `requirements-core.txt`；`requirements.txt` 另含 DOCX/PDF 原生处理依赖。

| 能力 | 额外准备 | 不可用时 |
|---|---|---|
| 原生 DOCX/PDF 解析 | `python-docx`、PyMuPDF，已列入 `requirements.txt` | 保留未读范围；不能声称完整解析 |
| 扫描件 OCR | 显式配置已部署的 PaddleOCR 服务，Key 只放环境 | 记录待补读页，见 [OCR 配置](docs/OCR_SETUP.md) |
| 企业知识 | 本地资料或宿主实际开放的知识检索工具 | 记录资料缺口；见 [知识接入](docs/KNOWLEDGE.md) |
| 技术图 | 下节列出的引擎 | 显式引擎缺失时保持 blocked |
| 系统界面示意 | 宿主原生生图 Skill/工具及授权 | 缺图保持整改项，不拿提示词当图片 |
| Word/PDF 与目录刷新 | 宿主文档工具，或本地 LibreOffice/Word | 只交付已验证的格式；目录域未刷新单列未完成 |
| 分章并行 | 宿主实际支持子 Agent | 记录串行执行及原因，不伪造并行记录 |

## 第一次使用

先建一个**独立项目目录**并作为宿主工作空间。把招标原件和补遗放到 `inputs/`，企业方案、证照等作为明确授权的资料输入。原件只读，不把项目结果写回 Skill 安装目录。

第一条指令可直接复制，替换项目路径：

> 请调用 bid-orchestrator，项目目录为【项目绝对路径】。先按 understand 模式读取 inputs 中的招标文件和补遗，识别标包、采购类型及组合模板，提取基础信息、需求、评分、资格否决与强制格式。保存带原文位置和输入哈希的 JSON/Markdown，并生成 HTML 报告。缺页、缺附件或分类歧义保留待确认。先不要编写整本标书。

理解无误后继续：

> 基于当前理解结果，继续响应策略、目录和证据匹配，生成章节任务卡。只使用已提供的企业资料，资质、业绩、人员、报价缺失时保留缺口。给出需要确认的方案和关键承诺。技术图使用 blueprint、teal 主题、SVG 输出；系统界面示意使用本宿主实际生图 Skill。

确认方案后写作：

> 按已确认目录编写所有章节。评分重点自动推荐篇幅，章节【稳定ID】覆盖为2000字、至少1张界面示意。若宿主支持子 Agent，按任务卡独立写章，由一个协调者合并；否则串行。实际保存并回读，保留未满足项。

评审与导出：

> 调用 bid-review-remediation 审核当前版本的评分条件、关键材料完整性和资格/否决条件。可修复的内容定向整改并复评，缺证照或签署不能靠改写通过。再调用 bid-export-acceptance，按招标强制格式及项目导出配置生成实际Word/PDF，核对目录、页码、附件、图表及真实渲染页面。不要代签、盖章或递交。

对话可随时调整目录、章节、篇幅和配图；宿主须保存新修订并使受影响评审/导出重新核验。网页上的“修复/重写/提升”生成版本绑定的任务；没有宿主唤醒接口时须把交接指令送回宿主执行，不能把按钮点击当作已修复。

## 画图：Skill 和渲染工具分别准备

`bid-visuals` 管理图的用途、章节关联、来源与审核；独立 `enterprise-diagrams` 提供可复用版式。配置写入项目 `work/writing-settings.json` 的 `visuals`，不要只在聊天里说“已配置”。建议让总控读取已有设置再保存；不要用片段覆盖整份文件。

| 选择 | 适用图 | 安装/依赖与输出 |
|---|---|---|
| `blueprint` + enterprise-diagrams | 分层架构、流程、泳道、网络、并行、简单时序、矩阵 | Python 标准库生成 SVG；保留 `.diagram.json`。8 类布局、6 套主题；PNG 另需宿主已有 CairoSVG |
| `drawio` | 复杂架构、部署、网络和需图形编辑的流程 | 保留现有 Draw.io 路径；需实际 Draw.io Desktop/CLI。原生 `.drawio` + SVG/PNG；加载 Skill 不等于安装桌面渲染器 |
| `plantuml` | 时序、异常分支与较复杂交互 | 实际 PlantUML 命令，或 Java + `PLANTUML_JAR`；保留 `.puml` |
| `mermaid` | 简单流程 | 已有 Mermaid CLI 与可用浏览器；保留 `.mmd` |
| 宿主生图 | 系统界面示意、概念效果图 | Codex 使用实际 Imagegen；WorkBuddy 使用本次开放的生图能力，不复制 Codex 的工具名冒充兼容 |

主题：`reference`、`blue`、`teal`、`green`、`slate`、`monochrome`。例如“这张架构图改用 blueprint、blue 主题、四层、SVG”；层数服从实际设计，不为模板发明组件。未显式选择时 `auto` 按图型及已安装工具路由，默认 SVG，保留 Draw.io。配置优先级为逐图指令 → 项目偏好 → 默认规则。

先运行 `python scripts/diagram_tools.py doctor` 检查工具发现，再实际渲染。安装包、命令、原生源与渲染收据说明见 [技术图工具](docs/DIAGRAM_TOOLS.md)。独立 Skill 安装后可直接说：

> 调用 enterprise-diagrams，把以下已确认组件和关系画成四层架构，主题teal，保存可编辑JSON源和SVG，检查文字、连线与A4可读性。

系统界面生成图须标 **“界面设计示意，非实际系统截图”**。真实截图必须来自实际系统；两者不能互作证明。图必须实际生成、插入正文并在导出中核验，工具退出码不代替视觉与语义验收。

## 项目如何保存与续写

```text
项目目录/
├── inputs/        原件与补遗（只读）
├── profiles/      分类、导出等显式项目配置
├── work/          project.json、总控状态、写作设置和任务记录
├── artifacts/     01—14结构化结果及可读报告
├── assets/        图源、成图与调用收据
├── reviews/       15评审、缺口与整改结果
├── deliverables/  16实际交付文件与清单
└── reports/       同版本HTML展示
```

跨 Skill 通过项目文件、稳定 ID、修订号和实际输入哈希交接，不依赖聊天记忆。更换 Agent 后提供同一项目目录并要求读状态再继续；本地文件需显式迁移到另一个设备。宿主知识库结果需导入项目快照/Wiki；安装 Skill 不会自动同步不同宿主的知识库、密钥和模型。

## 技能目录

| 编号 | 技能 | 标识 |
|---|---|---|
| 01 | 招标资料整理与原文解析 | `bid-source-intake` |
| 02 | 项目画像与场景适配 | `bid-project-profile` |
| 03 | 需求提取与结构化 | `bid-requirements` |
| 04 | 评分体系提取与分析 | `bid-scoring` |
| 05 | 资格、否决条件与提交要求提取 | `bid-compliance` |
| 06 | 强制目录与格式模板提取 | `bid-format-extraction` |
| 07 | 需求澄清与投标响应策划 | `bid-response-strategy` |
| 08 | 标书目录规划与覆盖映射 | `bid-outline-planning` |
| 09 | 企业素材与证明材料匹配 | `bid-evidence-matching` |
| 10 | 技术方案设计 | `bid-solution-design` |
| 11 | 技术标正文与响应表编写 | `bid-technical-writing` |
| 12 | 商务与资格文件编制 | `bid-commercial-documents` |
| 13 | 标书配图与图表制作 | `bid-visuals` |
| 14 | 标书排版与文档编排 | `bid-document-layout` |
| 15 | 综合评审与整改闭环 | `bid-review-remediation` |
| 16 | 导出与成稿验收 | `bid-export-acceptance` |
| 17 | 投标编制总控 | `bid-orchestrator` |

## 配置与进阶说明

- 分类：四类采购内容（工程、硬件供货、软件集成、服务外包）可组合，智慧园区/智能工厂是场景标签；见 [分类与模板](docs/TENDER_ROUTING.md)。
- 写作：[目录、编辑与保存](docs/WRITING_WORKFLOW.md)、[评分篇幅与界面图策略](docs/CHAPTER_WRITING_POLICY.md)、[实际子 Agent 并行](docs/PARALLEL_WRITING.md)。
- 成稿：[版式模板](docs/BID_LAYOUT_TEMPLATES.md)、[封面/目录/字体/缩进/行距配置](docs/EXPORT_LAYOUT.md)。招标文件和有效补遗优先于通用模板。
- 质量：[核心逐项评审](docs/CORE_REVIEW.md)、[质量闭环](docs/QUALITY_WORKFLOW.md)、[修复/重写/提升](docs/REVIEW_ACTIONS.md)、[评审展示](docs/REVIEW_PRESENTATION.md)。
- 报告：[HTML展示](docs/REPORTS.md)、[执行复核](docs/EXECUTION_QUALITY.md)、[已知问题](docs/KNOWN_ISSUES.md)。
- 测试：[工程记录](QA_REPORT.md)、[WorkBuddy实测](docs/WORKBUDDY.md)、[模拟材料闭环](docs/SIMULATION_TESTING.md)、[公开招标语料](benchmarks/public-tenders/README.md)。

## 更新与验证边界

源码副本用 `git pull --ff-only` 更新；复制安装需先把同名旧 Skill 备份到宿主发现目录**以外**，再安装完整新目录。软链接安装保留源码路径，新会话核对实际加载版本。不要删除其他 Skill 或把旧、新目录同时留在发现目录造成重复加载。现有项目不因更新自动重跑，继续前核对版本及受影响产物。

工程检查可在已安装依赖的环境运行 `python scripts/check_suite.py` 和 `python -m unittest discover -s tests -v`。需要完整 pytest 回归时另使用已有 pytest 环境。结构、分发一致性、模型执行、视觉检查和真实业务验收是不同证据。DOCX 原生解析与核心评审现在可按段落／单元格精确核验引文；复杂页眉歧义、扫描及渲染范围仍保留限制，见 [WorkBuddy实测边界](docs/WORKBUDDY.md#docx-来源核验与边界)。

本套件不附真实客户原件、证照或法定行业结论，不代签、不递交。种子模板和合成材料用于验证；模拟评审通过不能替代真实材料与授权。宿主/模型/工具组合的实际覆盖以测试记录为准，不承诺所有平台自动兼容。
