# 视觉优先可编辑 PPT

`visual-to-editable-ppt` 接收内容大纲、每页内容与风格，先用宿主生图工具制作设计图，再通过 `image-to-editable-ppt` 重建可编辑 PPTX。

七套主题：白底深蓝、白底朱红、紫色科技咨询、白底墨绿、产品解决方案、市场营销、年会盛典。另有12类页面配方。文字与普通结构可编辑，照片/插画作为独立图片保留；图表以原始数据为准，不保证全部转换为可直接“编辑数据”的原生图表。

## 安装

本包是编排 skill，需要同一仓库中的两项依赖。克隆仓库后，将三个入口放入宿主可发现的技能目录。以 Codex 为例（在仓库根目录运行，目标已存在时先核对，不覆盖）：

```bash
mkdir -p ~/.agents/skills
ln -s "$PWD/visual-to-editable-ppt" ~/.agents/skills/visual-to-editable-ppt
ln -s "$PWD/consulting-ppt-image" ~/.agents/skills/consulting-ppt-image
ln -s "$PWD/image-to-editable-ppt/skills/image-to-editable-ppt" ~/.agents/skills/image-to-editable-ppt
```

Claude Code 可使用其实际技能目录，WorkBuddy 使用其支持的导入/目录方式；本包不把复制文件视为加载成功。重新加载宿主并确认技能被发现。

Python 3.10+；使用隔离环境安装既有依赖及仓库内转换 CLI，不额外引入新的依赖：

```bash
python3 -m venv /你的环境目录/visual-ppt
/你的环境目录/visual-ppt/bin/python -m pip install -r consulting-ppt-image/requirements.txt
/你的环境目录/visual-ppt/bin/python -m pip install -e image-to-editable-ppt/skills/image-to-editable-ppt/cli
/你的环境目录/visual-ppt/bin/editppt --help
/你的环境目录/visual-ppt/bin/editppt doctor --json
```

CLI 的系统渲染依赖按它自己的安装指引配置。`host-tool` 支持来自本仓库配套修改；上游旧版 CLI 不一定具有该接口。`doctor` 检查本地运行时，不能代替宿主原生工具发现。宿主有实际图像生成、编辑和多 Agent 能力，才可执行完整多页流程。

## 直接对 Agent 说

> 使用 visual-to-editable-ppt。根据我提供的已确认大纲和逐页内容，采用白底深蓝咨询风。先完成三张代表页的生图、可编辑重建和预览，风格确定后继续全稿。最终提供可编辑 PPTX；保留原文和数字，图片素材独立可替换。

已授权 Agent 代审时，一并说明授权范围，之后无需每页重复确认。也可提供自己的品牌参考图和配色。

## 可复跑示例

[三页内容包](examples/slide-content-pack.json) 是通用演示草稿，不是已批准客户材料。在仓库根目录、使用配置好的 Python 环境运行：

```bash
python consulting-ppt-image/scripts/ppt_pipeline.py init \
  --pack visual-to-editable-ppt/examples/slide-content-pack.json \
  --style visual-to-editable-ppt/assets/themes/consulting-purple.json \
  --project /你的项目目录
python visual-to-editable-ppt/scripts/visual_bridge.py plan \
  --project /你的项目目录 --draft
```

根据实际内容确认更新 pack 的版本、review_status、approval_ref，再通过原技能 `sync` 写入。正式 `plan` 不加 draft，然后由 Agent 调用宿主生图工具并执行原技能 register/review/select。不要为运行示例而伪造确认记录。

```bash
python visual-to-editable-ppt/scripts/visual_bridge.py handoff \
  --project /你的项目目录 --output /你的项目目录/handoff-v001
python visual-to-editable-ppt/scripts/visual_bridge.py verify-handoff \
  --project /你的项目目录 --output /你的项目目录/handoff-v001
```

后续按 [转换流程](references/editable-conversion.md) 执行 editppt，再做机器与视觉验收。继续指定页时用 `--range 2-3`；不要把部分稿标为完整交付。

## 验证与边界

```bash
python -m unittest discover -s visual-to-editable-ppt/tests -v
python -m unittest discover -s consulting-ppt-image/tests -v
python -m unittest discover -s image-to-editable-ppt/tests -v
```

本包脚本不调用模型、不配置账户、不自动发布资料。自动测试覆盖状态交接和合成 PPTX；没有据此宣称实际模型生成质量、全部宿主兼容性或客户内容正确。每套新主题的视觉效果需以真实生成并重建后的代表页验证。
