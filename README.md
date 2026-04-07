# skills

这是一个用于集中管理与分发各类 AI skill 的仓库。  
每个 skill 都放在独立目录中，并且目录内自带：

- `SKILL.md`：技能定义
- `README.md`：安装方式、使用方法、示例
- `assets/`、`references/`、`scripts/`：按需要提供资源、模板和工具链

## 当前收录

### 1. industrial-ai-architect

面向工业数字化、AI 战略、方案架构、业务案例、路线图与经营落地设计。

- 目录：[`industrial-ai-architect/`](./industrial-ai-architect/)
- 说明：[`industrial-ai-architect/README.md`](./industrial-ai-architect/README.md)

### 2. ppt-maker-with-image

面向图片优先的 PPT 生成：需求确认、大纲、逐页提示词、图片生成、单页/整套 `pptx` 组装。

- 目录：[`ppt-maker-with-image/`](./ppt-maker-with-image/)
- 说明：[`ppt-maker-with-image/README.md`](./ppt-maker-with-image/README.md)

## 推荐使用方式

按目录安装单个 skill，而不是把整个仓库根目录当作一个 skill。

例如安装 `ppt-maker-with-image`：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/chrisopal/skills.git ~/.codex/skills/chrisopal-skills
ln -sfn ~/.codex/skills/chrisopal-skills/ppt-maker-with-image ~/.codex/skills/ppt-maker-with-image
```

例如安装 `industrial-ai-architect`：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/chrisopal/skills.git ~/.codex/skills/chrisopal-skills
ln -sfn ~/.codex/skills/chrisopal-skills/industrial-ai-architect ~/.codex/skills/industrial-ai-architect
```

## 仓库目标

这个仓库后续会持续扩展，作为统一的 skill 集合仓库使用。  
每个子目录都可以单独阅读、单独安装、单独演进。
