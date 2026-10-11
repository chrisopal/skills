# 视觉优先 PPT：可编辑或图片型

`visual-to-editable-ppt` 接收内容大纲、每页内容与风格，用宿主生图工具制作单页设计图，支持两种输出：

| 模式 | 成稿内容 | 额外依赖 |
|---|---|---|
| `editable`（默认） | 原生文字与普通结构，照片/插画为独立图片；图表以原始数据为准，不保证全部是可编辑数据的原生图表 | image-to-editable-ppt、转换运行时、素材分离能力，多页重建还需子 Agent |
| `image`（用户明确选择） | 每页一张完整图片，可替换整图；图片内文字与结构不能单独编辑 | 无需转换 CLI、拆图或重建能力 |

七套主题：白底深蓝、白底朱红、紫色科技咨询、白底墨绿、产品解决方案、市场营销、年会盛典；另有12类页面配方。输出模式与主题独立。不得因可编辑转换失败擅自降级成图片版。

正文默认20pt、内容标题32pt，封面与短标签分别设定；[字号依据及验收规则](references/typography.md)说明适用场景和pt/像素换算。

## 安装

两条路径都需要 `consulting-ppt-image`。在仓库根目录，将入口放入宿主可发现的目录；目标已存在时先核对，不覆盖。Codex 示例：

```bash
mkdir -p ~/.agents/skills
ln -s "$PWD/visual-to-editable-ppt" ~/.agents/skills/visual-to-editable-ppt
ln -s "$PWD/consulting-ppt-image" ~/.agents/skills/consulting-ppt-image
```

Python 3.10+；使用隔离环境安装既有依赖：

```bash
python3 -m venv /你的环境目录/visual-ppt
/你的环境目录/visual-ppt/bin/python -m pip install -r consulting-ppt-image/requirements.txt
```

仅可编辑路径还需安装仓库配套转换 CLI 和技能：

```bash
ln -s "$PWD/image-to-editable-ppt/skills/image-to-editable-ppt" ~/.agents/skills/image-to-editable-ppt
/你的环境目录/visual-ppt/bin/python -m pip install -e image-to-editable-ppt/skills/image-to-editable-ppt/cli
/你的环境目录/visual-ppt/bin/editppt --help
/你的环境目录/visual-ppt/bin/editppt doctor --json
```

渲染能力两条路径都要核实，用于查看最终 PPTX；系统依赖按所用渲染工具安装。转换 `host-tool` 接口来自本仓库配套修改，上游旧版不一定具备。`doctor` 不替代宿主工具发现，详见 [宿主能力](references/host-tools.md)。Claude Code、WorkBuddy 使用各自支持的技能目录或导入方式，重新加载并确认发现成功；复制文件不等于已加载。

## 直接对 Agent 说

可编辑版：

> 使用 visual-to-editable-ppt。根据我提供的已确认大纲和逐页内容，采用白底深蓝咨询风。先完成三张代表页的生图、可编辑重建和预览，再继续全稿。最终提供可编辑 PPTX；保留原文和数字，图片素材独立可替换。

图片版：

> 使用 visual-to-editable-ppt，选择 image 图片版。按已确认内容制作营销主题设计图，先验证代表页，再将选定图片按顺序做成每页一张整图的 PPTX，保留演讲备注。我接受图片内文字不能单独编辑。

可提供品牌参考图和配色。已有 Agent 代审授权时沿用授权范围，无需每页重复确认。

## 可复跑示例

[三页内容包](examples/slide-content-pack.json) 是通用演示草稿，不是已批准客户材料。在仓库根目录、使用配置好的 Python 环境运行：

```bash
python consulting-ppt-image/scripts/ppt_pipeline.py init \
  --pack visual-to-editable-ppt/examples/slide-content-pack.json \
  --style visual-to-editable-ppt/assets/themes/consulting-purple.json \
  --project /你的项目目录
python visual-to-editable-ppt/scripts/visual_bridge.py plan \
  --project /你的项目目录 --draft --output-mode image
```

省略 `--output-mode` 时默认 editable；草稿队列禁止生图。根据实际确认更新 pack 的版本、review_status、approval_ref，再用依赖 `sync` 写入。正式 `plan` 去掉 `--draft`，由 Agent 调用宿主生图并执行 register/review/select，不伪造确认记录。

两条路径共用不可覆盖的 handoff：

```bash
python visual-to-editable-ppt/scripts/visual_bridge.py handoff \
  --project /你的项目目录 --output /你的项目目录/handoff-v001
python visual-to-editable-ppt/scripts/visual_bridge.py verify-handoff \
  --project /你的项目目录 --output /你的项目目录/handoff-v001
```

仅做部分稿时，在 plan 和 handoff 显式传 `--range 2-3`；导出和审计继承 handoff 范围，不另传 range。

**editable：** 按 [转换流程](references/editable-conversion.md) 执行 editppt，再运行 `audit-pptx`，查看实际渲染并在副本中编辑保存重开。

**image：** 命令名本身明确选择图片型，不再重复传 output-mode：

```bash
python visual-to-editable-ppt/scripts/visual_bridge.py export-images \
  --project /你的项目目录 --output /你的项目目录/handoff-v001 \
  --pptx /你的项目目录/output/图片版-v001.pptx
python visual-to-editable-ppt/scripts/visual_bridge.py audit-images \
  --project /你的项目目录 --output /你的项目目录/handoff-v001 \
  --pptx /你的项目目录/output/图片版-v001.pptx
```

`--output` 指已有交接目录，`--pptx` 才是成稿。导出先校验 handoff，再保持原图字节、顺序、比例和备注写入新文件并回读审计。目标必须为新 `.pptx`，不得位于 handoff 内；项目内仅允许 `output/`，也可写到项目外的新路径。已有文件和目标符号链接均拒绝覆盖。不要直接交付 `conversion-input.pptx`；它仍是带输入标记的中间载体。

两种输出均按 [质量检查](references/quality.md) 打开最终 PPTX 并检查实际渲染，不把部分稿标为完整交付。依赖不在相邻目录时，将 `--consulting-root /实际技能目录` 放在脚本名后、子命令前。

## 验证与边界

```bash
python -m unittest discover -s visual-to-editable-ppt/tests -v
python -m unittest discover -s consulting-ppt-image/tests -v
```

可编辑转换改动另外运行依赖测试：

```bash
python -m unittest discover -s image-to-editable-ppt/tests -v
```

脚本不调用模型、不配置账户、不自动发布资料。自动测试覆盖状态交接和合成 PPTX，不证明模型生成质量、全部宿主兼容性或客户内容正确。新主题以所选输出模式的实际代表页验证；图片版通过不等于该主题的可编辑重建通过。

2026-10-11已在WorkBuddy 5.6.2完成一页蓝色咨询样稿的真实生图、图片版与可编辑版导出、字号/内容/备注回读及LibreOffice渲染。具体发现方式、重试记录和未测范围见[宿主实测边界](references/host-tools.md)。
