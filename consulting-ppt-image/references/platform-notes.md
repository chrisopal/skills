# 技术来源与运行边界

核对日期：2026-10-07。

- Agent Skills格式规范：https://agentskills.io/specification
  - 使用目录＋SKILL.md；YAML前置信息包含name、description；详细规则按需放references，脚本放scripts，参考素材放assets。
- OpenAI官方技能文档：https://developers.openai.com/codex/skills/ （访问时重定向至 https://learn.chatgpt.com/docs/build-skills ）
  - Codex本地用户目录为 `$HOME/.agents/skills`，项目目录为 `.agents/skills`；可显式选择技能。
- Claude Code官方技能文档：https://code.claude.com/docs/en/skills
  - 本地用户目录为 `~/.claude/skills`，项目目录为 `.claude/skills`。

这些资料支持技能格式和本地加载机制，不代表本包已在每个产品中端到端验证。WorkBuddy或其他工具的实际导入方式、图像权限、运行时和路径，以其当前能力为准；本包不声明未验证的通用一键兼容。

本包不配置图像模型或API Key。图片生成须由实际运行Skill的宿主提供；内容与图片理解、真实网页截图同样由宿主执行。脚本只管理任务、状态、文件与PPTX。

本次测试的是本地Python控制链及合成测试图片的原图导出；未重新生成一套35页来声称全流程已验证。前述规范链接不为历史PPT中的案例、工艺、空间图或数字背书。
