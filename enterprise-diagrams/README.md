# Enterprise Diagrams

用可编辑 JSON 规格生成企业技术图和 SVG，可独立使用，也可接入投标套件的 `bid-visuals`。绘图规则见 [SKILL.md](SKILL.md)，详细字段见 [规格](references/spec.md)。

## 安装

Codex 可通过通用 Skills CLI 安装完整目录：

```bash
npx --yes skills@1.7.2 add \
  'https://github.com/chrisopal/skills/tree/main/enterprise-diagrams' \
  --global --agent codex --copy --yes
```

电脑需有 Node.js/npm；`--copy` 会更新同名安装，已有自定义内容先备份。去掉 `--global` 可安装到当前项目；其他 Agent 选择与 WorkBuddy 导入见[投标套件安装说明](../bid-skills-suite-v1.0.0/README.md#通用-npx-安装)。

从 [chrisopal/skills 的 main](https://github.com/chrisopal/skills/tree/main/enterprise-diagrams) 获取完整 `enterprise-diagrams/` 目录。复制到宿主 Skill 发现目录，例如 Codex 的 `~/.codex/skills/enterprise-diagrams` 或 WorkBuddy 默认的 `~/.workbuddy/skills/enterprise-diagrams`。已有同名目录时先核对并备份到发现目录外，不直接覆盖。

支持 ZIP 导入的宿主可使用本地单 Skill 包。从本仓库根目录运行：

```bash
python -m zipfile -c enterprise-diagrams.zip enterprise-diagrams
```

包内须保留 `enterprise-diagrams/SKILL.md`、脚本、规格及示例。WorkBuddy 进入“专家·技能·连接器 → 技能 → 添加技能 → 上传技能”，选择该包；安装后在“我安装的”核对并启用。

## 使用

> 调用 enterprise-diagrams，按我提供的组件与关系绘制四层功能架构，主题teal，保存JSON源和SVG。标明系统边界，检查连接、中文和A4版心可读性。不要补造未提供的模块或指标。

支持 `layered`、`flow`、`pipeline`、`swimlane`、`network`、`parallel`、`sequence`、`matrix` 八类布局。主题有 `reference`、`blue`、`teal`、`green`、`slate`、`monochrome`；可逐图指定。复杂时序 alt/loop 嵌套应使用 PlantUML 或 Draw.io，过密图拆成总览和局部图。

手动渲染：从本 Skill 目录执行，源文件按规格提供，输出使用未存在的新路径：

```bash
python scripts/diagram_svg.py --source /project/assets/example.diagram.json --out /project/assets/example.svg --theme teal
```

SVG 渲染需要 Python 3.10+，仅用标准库，不需要 API Key。PNG 转换需要宿主已有 CairoSVG 或其他实际转换工具，不能假定已经安装。生成后还需检查业务关系与实际渲染，命令成功不代表语义正确。

## 接入投标套件

由 `bid-visuals` 读取项目 `work/writing-settings.json`，设置 `visuals.diagram_engine=blueprint`、`visuals.diagram_theme=teal`，通过套件 `diagram_tools.py` 渲染并保存源/成图哈希、收据和章节关联。见 [工具配置](../bid-skills-suite-v1.0.0/docs/DIAGRAM_TOOLS.md)。

独立 `bid-visuals` 已包含同源渲染器与规格，因此没有安装本 Skill 也可使用其内置 blueprint；安装独立 Skill 便于其他任务复用。**保留 Draw.io**，不改变原有 auto 路由。系统界面示意、概念效果图交给宿主原生生图能力；本 Skill 不生成真实系统截图。

## 实际效果

[模拟标书配图示例](../bid-skills-suite-v1.0.0/examples/readme-demo/visuals.html)同时展示本 Skill 渲染的六状态 SVG 流程图与宿主生成的界面示意图；[套件 README](../bid-skills-suite-v1.0.0/README.md#6-配图可编辑技术图--宿主生成的界面示意)有浏览器截图。技术图保留[可编辑 JSON 图源](../bid-skills-suite-v1.0.0/examples/readme-demo/assets/fig-4.1-event-flow.diagram.json)和 [SVG](../bid-skills-suite-v1.0.0/examples/readme-demo/assets/fig-4.1-event-flow.svg)，不把图片当作系统实现证据。
