# skills

这是一个用于集中管理与分发各类 AI skill 的仓库。每个子目录是一套独立 skill，包含 `SKILL.md`、`README.md`、脚本、配置、模板和必要参考资料。

## 当前收录

- [`opportunity-orchestrator`](./opportunity-orchestrator/SKILL.md)：七个商机 Skills，从首次拜访、评分与竞争、方案评审到签单交接；共享 SQLite、本机可编辑工作台及真实售前/PPT版本桥接。[运行与安装说明](./opportunity-orchestrator/references/workbench-presales.md)。

- [`presales-solution-skills`](./presales-solution-skills/README.md)：通用 B 端售前10技能，从混合资料、需求脑图、方案与逐页内容到本地PPT制作和实际文件审核，含版本失效工具与测试。

- [`bid-skills-suite-v1.0.0`](./bid-skills-suite-v1.0.0/README.md)：17 个投标编制 Skills，总控串联解析、分类、目录、写作、配图、评审与 Word/PDF 导出；含通用安装及 WorkBuddy 使用说明。
- [`enterprise-diagrams`](./enterprise-diagrams/README.md)：独立企业技术图 Skill，8 类布局、6 套主题、可编辑 JSON + SVG；可接入投标套件，保留 Draw.io。

- [`xiaohongshu-skill`](./xiaohongshu-skill/SKILL.md)：小红书内容读取与发布；针对成片发布增加清单预检、封面设置、草稿恢复和重复提交保护，保留上游来源与许可。

- [`industrial-ai-architect`](./industrial-ai-architect/README.md)：工业数字化、智能工厂、AI 战略架构、方案蓝图、路线图和业务落地设计。
- [`ppt-maker-with-image`](./ppt-maker-with-image/README.md)：图片优先的 PPT 生成流程，包含需求确认、大纲、逐页提示词、图片生成和 PPTX 组装。
- [`visual-to-editable-ppt`](./visual-to-editable-ppt/README.md)：视觉优先 PPT；按大纲、逐页内容与风格生成设计图，默认重建可编辑 PPTX，也支持明确选择每页整图的图片型 PPTX，内置七套主题。
- [`consulting-ppt-image`](./consulting-ppt-image/README.md)：咨询型图片 PPT 制作，包含内容交接、故事线与固定样式、逐页独立生成、版本审校和确认原图组装。公共版不含客户资料或参考图片；[验证与状态](./consulting-ppt-image/STATUS.md)。
- [`ppt-maker-direct-pptx`](./ppt-maker-direct-pptx/README.md)：七道闸确认式 PPT 生成，输出可编辑 PowerPoint 原生对象。12 个 layout pattern + 5 内置预设 + 自然语言/参考图自定义风格 + 自动 lint + 状态机断点续做，兼容任意 OpenAI 协议 LLM（OpenAI / OpenRouter / Azure / Groq / Together / DeepSeek / vLLM / Ollama / LiteLLM）。
- [`wechat-official-account-skills`](./wechat-official-account-skills/)：微信公众号「智能体架构笔记」运营技能包，覆盖选题、写作、排版配图、审稿、运营复盘和每日端到端草稿生成。
- [`requirements-to-delivery`](./requirements-to-delivery/SKILL.md)：从需求调研、技术方案、SRS、系统设计、原型到开发验收的端到端交付流程 skill。
- [`book2videoskill`](./book2videoskill/SKILL.md)：把书名、书籍摘要或 Book2Skill 输出转成 5 分钟以内知识短视频的 BookCore、封面海报、分镜、资产计划、渲染计划和小红书发布文案。
- [`book2video`](./book2video/README.md)：Book2Video 独立 Node 工程，提供 CLI、三段工具、Provider 占位、Remotion 模板占位和测试，用于把书籍方法论生成短视频生产包。

## 推荐安装方式

商机套件需安装七个兄弟目录：`python3 opportunity-orchestrator/scripts/install.py --dest /absolute/new-skill-directory`。安装器保留已有目录，发现差异会拒绝覆盖；真实售前/PPT联动另需安装相应售前与制作 Skill。

售前套件需将10个技能安装为兄弟目录，请运行 `python3 presales-solution-skills/scripts/install.py --dest "$HOME/.codex/skills"`，不要只链接套件根目录。详见其README。

**投标编制套件：** [查看完整 README、12 张过程截图和模拟 Word/PDF 样稿](./bid-skills-suite-v1.0.0/README.md)。Codex 可用通用 `npx` 命令一次安装 17 个投标 Skill：

```bash
npx --yes skills@1.7.2 add \
  'https://github.com/chrisopal/skills/tree/main/bid-skills-suite-v1.0.0/skills' \
  --skill '*' --global --agent codex --copy --yes

npx --yes skills@1.7.2 add \
  'https://github.com/chrisopal/skills/tree/main/enterprise-diagrams' \
  --global --agent codex --copy --yes
```

第二条安装独立绘图 Skill，共 18 个。WorkBuddy 的本地导入、其他 Agent 的选择、运行依赖及下载超时排错见[套件安装说明](./bid-skills-suite-v1.0.0/README.md#通用-npx-安装)。

其他 Skill 也可以选择克隆整个仓库，再把需要的目录软链接到客户端扫描目录。这样后续 `git pull` 即可统一更新。

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/chrisopal/skills.git ~/.codex/skills/chrisopal-skills
ln -sfn ~/.codex/skills/chrisopal-skills/ppt-maker-direct-pptx ~/.codex/skills/ppt-maker-direct-pptx
ln -sfn ~/.codex/skills/chrisopal-skills/ppt-maker-with-image ~/.codex/skills/ppt-maker-with-image
ln -sfn ~/.codex/skills/chrisopal-skills/industrial-ai-architect ~/.codex/skills/industrial-ai-architect
ln -sfn ~/.codex/skills/chrisopal-skills/requirements-to-delivery ~/.codex/skills/requirements-to-delivery
ln -sfn ~/.codex/skills/chrisopal-skills/book2videoskill ~/.codex/skills/book2videoskill
ln -sfn ~/.codex/skills/chrisopal-skills/wechat-official-account-skills/wechat-topic-planner ~/.codex/skills/wechat-topic-planner
ln -sfn ~/.codex/skills/chrisopal-skills/wechat-official-account-skills/wechat-article-writer ~/.codex/skills/wechat-article-writer
ln -sfn ~/.codex/skills/chrisopal-skills/wechat-official-account-skills/wechat-article-layout ~/.codex/skills/wechat-article-layout
ln -sfn ~/.codex/skills/chrisopal-skills/wechat-official-account-skills/wechat-article-reviewer ~/.codex/skills/wechat-article-reviewer
ln -sfn ~/.codex/skills/chrisopal-skills/wechat-official-account-skills/wechat-account-operator ~/.codex/skills/wechat-account-operator
ln -sfn ~/.codex/skills/chrisopal-skills/wechat-official-account-skills/wechat-daily-pipeline ~/.codex/skills/wechat-daily-pipeline
```

如果你的客户端使用 `~/.agents/skills`：

```bash
mkdir -p ~/.agents/skills
ln -sfn ~/.codex/skills/chrisopal-skills/industrial-ai-architect ~/.agents/skills/industrial-ai-architect
ln -sfn ~/.codex/skills/chrisopal-skills/requirements-to-delivery ~/.agents/skills/requirements-to-delivery
ln -sfn ~/.codex/skills/chrisopal-skills/book2videoskill ~/.agents/skills/book2videoskill
ln -sfn ~/.codex/skills/chrisopal-skills/ppt-maker-direct-pptx ~/.agents/skills/ppt-maker-direct-pptx
ln -sfn ~/.codex/skills/chrisopal-skills/consulting-ppt-image ~/.agents/skills/consulting-ppt-image
ln -sfn ~/.codex/skills/chrisopal-skills/wechat-official-account-skills/wechat-daily-pipeline ~/.agents/skills/wechat-daily-pipeline
```

## 只安装某个 skill

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/chrisopal/skills.git /tmp/chrisopal-skills
cp -R /tmp/chrisopal-skills/ppt-maker-direct-pptx ~/.codex/skills/ppt-maker-direct-pptx
```

安装后重启或刷新 Codex/Agent 客户端。

## 更新

```bash
cd ~/.codex/skills/chrisopal-skills
git pull
```

如果使用复制安装方式，重新复制对应 skill 目录即可。

## 仓库目标

这个仓库后续会持续扩展，作为统一的 skill 集合仓库使用。每个子目录都可以单独阅读、单独安装、单独演进。

## 安全说明

- 不要把 API key 写入本仓库。
- 需要模型调用的 skill 使用环境变量读取密钥（`LLM_API_KEY` 或者 legacy `OPENROUTER_API_KEY`）。
- 提交前建议执行密钥扫描。示例命令里的前缀请按实际供应商替换，避免把真实密钥或完整密钥前缀写入仓库文档：

```bash
rg -n "<provider-key-prefix>|OPENROUTER_API_KEY=.*<provider-key-prefix>" .
```
