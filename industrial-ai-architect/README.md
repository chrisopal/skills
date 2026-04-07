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

以下示例使用 GitHub 仓库：`https://github.com/chrisopal/skills.git`。

### 1) Claude Code

Claude Code 优先读取个人/项目技能目录中的 `SKILL.md`。

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/chrisopal/skills.git ~/.claude/skills/chrisopal-skills
ln -sfn ~/.claude/skills/chrisopal-skills/industrial-ai-architect ~/.claude/skills/industrial-ai-architect
```

### 2) Codex

Codex 个人技能位于 `~/.agents/skills/` 或 `~/.codex/skills/`。

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/chrisopal/skills.git ~/.codex/skills/chrisopal-skills
ln -sfn ~/.codex/skills/chrisopal-skills/industrial-ai-architect ~/.codex/skills/industrial-ai-architect
```

安装后重启/刷新客户端即可识别。

### 3) OpenClaw

```bash
mkdir -p /path/to/openclaw-workspace/skills
git clone https://github.com/chrisopal/skills.git /path/to/openclaw-workspace/skills/chrisopal-skills
ln -sfn /path/to/openclaw-workspace/skills/chrisopal-skills/industrial-ai-architect /path/to/openclaw-workspace/skills/industrial-ai-architect
```

## 注意

- 此 skill 以“策略与架构”场景为主。
- 不适合纯调试、低层代码修复、截图、翻译这类工具性任务。
