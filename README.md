# skills

这是一个用于集中管理与分发各类 AI skill 的仓库。每个子目录是一套独立 skill，包含 `SKILL.md`、`README.md`、脚本、配置、模板和必要参考资料。

## 当前收录

- [`industrial-ai-architect`](./industrial-ai-architect/README.md)：工业数字化、智能工厂、AI 战略架构、方案蓝图、路线图和业务落地设计。
- [`ppt-maker-with-image`](./ppt-maker-with-image/README.md)：图片优先的 PPT 生成流程，包含需求确认、大纲、逐页提示词、图片生成和 PPTX 组装。
- [`ppt-maker-direct-pptx`](./ppt-maker-direct-pptx/README.md)：七道闸确认式 PPT 生成，输出可编辑 PowerPoint 原生对象。12 个 layout pattern + 5 内置预设 + 自然语言/参考图自定义风格 + 自动 lint + 状态机断点续做，兼容任意 OpenAI 协议 LLM（OpenAI / OpenRouter / Azure / Groq / Together / DeepSeek / vLLM / Ollama / LiteLLM）。
- [`wechat-official-account-skills`](./wechat-official-account-skills/)：微信公众号「智能体架构笔记」运营技能包，覆盖选题、写作、排版配图、审稿、运营复盘和每日端到端草稿生成。
- [`requirements-to-delivery`](./requirements-to-delivery/SKILL.md)：从需求调研、技术方案、SRS、系统设计、原型到开发验收的端到端交付流程 skill。

## 推荐安装方式

建议先克隆整个仓库，再把需要的 skill 软链接到客户端扫描目录。这样后续 `git pull` 即可统一更新。

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/chrisopal/skills.git ~/.codex/skills/chrisopal-skills
ln -sfn ~/.codex/skills/chrisopal-skills/ppt-maker-direct-pptx ~/.codex/skills/ppt-maker-direct-pptx
ln -sfn ~/.codex/skills/chrisopal-skills/ppt-maker-with-image ~/.codex/skills/ppt-maker-with-image
ln -sfn ~/.codex/skills/chrisopal-skills/industrial-ai-architect ~/.codex/skills/industrial-ai-architect
ln -sfn ~/.codex/skills/chrisopal-skills/requirements-to-delivery ~/.codex/skills/requirements-to-delivery
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
ln -sfn ~/.codex/skills/chrisopal-skills/ppt-maker-direct-pptx ~/.agents/skills/ppt-maker-direct-pptx
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
