# skills

这个仓库用于存放可独立安装的 skill 目录。

当前包含：

- `industrial-ai-architect`：工业数字化与 AI 战略架构 skill
- `ppt-maker-with-image`：图片优先的 PPT 生成与 PPTX 组装 skill

---

# industrial-ai-architect Skill

这是一个用于“**工业数字化与 AI 战略架构**”场景的技能。它的目标是把业务问题转化为可执行的策略与落地方案，并给出：

- AI 战略与业务目标的对齐方式
- 方案架构与实施路径
- 投资回报、风险与里程碑
- 团队与流程落地建议

## 文件结构

- `SKILL.md`：技能主文件，定义触发条件与执行框架
- `README.md`：本说明文档

## 何时使用这个 skill

当你需要我在以下场景给出决策级建议时调用：

- 工业数字化/智能工厂改造
- 智能化运营与流程重构
- AI 落地路线图与优先级排序
- 平台化架构与治理方案设计
- 业务案例、预算、ROI、组织配套设计

## 如何使用

- 在聊天中提出策略性问题，包含目标、场景、约束时，会自动激活：
  - 例如：
    - "帮我做一版某工厂智能排产的改造蓝图"
    - "这个方案的投资回报和里程碑怎么写"
    - "给我一个 30/60/90 天落地计划"
- 在支持命令的客户端可直接输入命令名（来自 `name`）：
  - `/industrial-ai-architect`

## 安装方式

以下示例使用 GitHub 仓库：`https://github.com/chrisopal/skills.git`（当前仓库路径）。

### 1) Claude Code

Claude Code 优先读取个人/项目技能目录中的 `SKILL.md`。

```bash
# 个人级（推荐）
mkdir -p ~/.claude/skills
git clone https://github.com/chrisopal/skills.git ~/.claude/skills/industrial-ai-architect

# 若已在其他目录克隆该仓库，也可改为软链接
# ln -sfn /path/to/repo ~/.claude/skills/industrial-ai-architect
```

也可放到项目级目录（仅该项目可见）：

```bash
REPO_DIR="/path/to/your/repo"
mkdir -p .claude/skills
mkdir -p .claude/skills/industrial-ai-architect
cp "$REPO_DIR/SKILL.md" .claude/skills/industrial-ai-architect/SKILL.md
```

### 2) Codex

Codex 个人技能位于 `~/.agents/skills/`。

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/chrisopal/skills.git ~/.agents/skills/industrial-ai-architect

# 若已在其他目录克隆该仓库，也可用软链接指向现有目录
# ln -sfn /path/to/repo ~/.agents/skills/industrial-ai-architect
```

安装后重启/刷新 Codex，会在技能列表中识别该技能。

### 3) OpenClaw

OpenClaw 会从工作区 `skills/` 目录加载工作区技能。可按以下方式安装：

```bash
# 在你的 OpenClaw 工作区根目录执行
mkdir -p /path/to/openclaw-workspace/skills
git clone https://github.com/chrisopal/skills.git /path/to/openclaw-workspace/skills/industrial-ai-architect
```

如果你希望从 OpenClaw 注册源安装（已发布到 ClawHub），也可用：

```bash
openclaw skills install industrial-ai-architect
```

安装完成后新开一个会话使技能生效。

## 注意

- 此仓库里 `name` 定义为 `industrial-ai-architect`，命令名也会遵循这个值。
- 当前版本以“策略与架构”场景为主，不适合纯写作、翻译、截图类工具性任务。
