# consulting-ppt-image v1.0.1
## 咨询型图片PPT制作 Skill

将批准的方案变成可持续续做、可查版本、可按原图交付的一页一图PPT。**不是只有一段风格提示词，也不是一台自带图像模型的生成器。**

本公开版包括：SKILL.md、固定纯白墨绿主题、内容契约、生产/证据/审校规范、本地脚本、回归测试、三页入门示例和35页通用目录示例。不包含客户项目资料或参考图片。

## 安装到本地Agent

解压得到 `consulting-ppt-image/`，放在以下任一位置：

```text
Codex：     ~/.agents/skills/consulting-ppt-image/
Claude Code：~/.claude/skills/consulting-ppt-image/
```

项目共享也可放在项目的 `.agents/skills/` 或 `.claude/skills/`。目录入口为 `SKILL.md`；无需改为大写目录或把所有文档合成一段长提示词。宿主加载机制的官方依据见 `references/platform-notes.md`。

这是可安装文件夹，**不会自动安装到任何账户或设备，也不覆盖其他PPT技能**。其他产品需使用其实际支持的导入入口；不能把聊天中上传ZIP等同于已安装。

## 使用语句

```text
使用 consulting-ppt-image。
依据附件已确认的咨询方案，先建立页级清单，不补未经核验的事实。
主题使用 consulting-white-inkgreen；16:9，纯白底、墨绿色，每页独立一张图。
先核对全稿故事线，确认后生成第1—10页。工厂章节连续，展厅不重复。
保留页ID与版本，后续批次不能改变总页数或章节安排。
```

已有内容包时直接指定它；已批准风格无需反复从零讨论。

```text
沿用当前内容包和已锁定风格，继续实际第21—30页。
只生成这一范围，每页独立保存；不要联系表，不要把31—35页的路线图提前加入。
```

```text
按manifest内已确认的版本汇总整套PPT，保持原图字节不变，不裁剪、不重绘、不补页脚。
检查总页数、顺序和每页单图；不要根据目录文件名或修改时间猜最终版本。
```

## 运行环境

需要Python 3.10+。在技能目录执行：

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

宿主还需要图像生成与图像理解能力；涉及外部案例需要真实检索与截图能力。以下命令不会调用模型、不会自动消耗图像额度。

## 本地生产控制

```bash
# 1. 初始化；工作目录必须为空。示例初始是draft。
python scripts/ppt_pipeline.py init \
  --pack examples/minimal/slide-content-pack.json --project work/demo

# 2. 先看草稿逐页任务；它们不能冒充批准的生产任务。
python scripts/ppt_pipeline.py plan --project work/demo --range 1-3 --draft

# 正式内容由上游确认：review_status=approved，approval_ref记录实际确认。
# 发布新版本内容包后，显式同步，不直接篡改工作区快照。
python scripts/ppt_pipeline.py sync --project work/demo \
  --pack /实际路径/已批准新版内容包.json --confirmation '实际用户确认消息或评审记录'

# 3. 输出每页独立生成任务，由宿主图像工具逐一执行。
python scripts/ppt_pipeline.py plan --project work/demo --range 1-3

# 4. 每张结果立即登记；path用工具实际返回的文件路径。
python scripts/ppt_pipeline.py register --project work/demo \
  --slide-id S001 --image /实际路径/生成结果.png --producer '实际宿主与工具名称'

# 5. 打开原图真实审阅，用模板填写真实哈希、审阅人、检查结果。
python scripts/ppt_pipeline.py review --project work/demo --file /实际路径/S001-review.json

# 6. 按用户确认/明确代审授权选择最终版本，绝不按最新mtime挑选。
python scripts/ppt_pipeline.py select --project work/demo --slide-id S001 \
  --version 1 --confirmation '实际图片确认消息或授权依据'

# 7. 完成全部页后审计、导出。
python scripts/ppt_pipeline.py audit --project work/demo --stage final
python scripts/ppt_pipeline.py assemble --project work/demo --output work/demo/output/deck-v001.pptx
```

路径中的“实际”不是可直接运行的示例文件；由执行Skill的Agent填入真实值，不能自造结果路径。为了节省用户操作，上述命令应由具备运行能力的Agent按工作流执行。

明确要导出部分稿时，在audit/assemble增加 `--range 1-10`。输出凭证会标 `explicit_partial:1-10`，PPT元数据包含PARTIAL；完整导出则不传range。

## 文件与状态

```text
work/project/
├── slide-content-pack.json      # 批准内容的快照
├── style-profile.json           # 锁定主题快照
├── deck-manifest.json           # 页ID、版本、哈希、QA、最终选版
├── prompts/                     # 每页独立任务
├── renders/                     # S001_v001.png、S001_v002.png…
├── reviews/                     # 实际审阅记录
├── history/                     # 内容变更前快照
└── output/                      # 队列、审计报告、PPTX与导出凭证
```

脚本能检查页数、章节中断、精确重复、引用ID、实体元数据、简单FS时间依赖、图片比例/尺寸、版本/哈希、选版完整性、导出单图和嵌入字节。

它不能自动判断画面是不是十页拼图、中文是否全对、白底是否纯净、案例是否真的发生、所有业务结论是否合理。此类必须通过视觉和证据审阅；审校字段是声明，不是已执行的识别算法。脚本亦不验证审批者身份，不是不可篡改的权限系统。

## 复用现有资产

本包专注图片工作流，不替代可编辑模式；与仓库已有PPT技能的分工见 `references/migration-from-v2.md`。内容交接契约已在包内给出，不依赖未附带的私有文件。

`examples/generic-35/slide-content-pack.outline.json` 含35页通用目录、结论和顺序，不含客户事实、完整正文或实际案例证据。它被标为needs_review/content_complete=false，不可直接生成正式稿。

视觉锚点由用户在私有工作区提供；优先选择已授权的架构、流程和场景三类参考页。不要将参考图里的项目标题、客户数据或示意值套入新方案。

## 隐私与发布

公开版已移除客户项目名称、原始案例包、故事线调整记录和三张客户参考图片，35页结构改为通用示例。不附字体文件、API密钥、客户PPT、生成样例或临时审校图片。项目工作区及运行产物保留在本地；额外上传客户资料前必须取得相应授权。

## 版本与验证

查看 `TEST_REPORT.md`。本次验证局限于本地脚本的合成用例，不代表已在所有Agent产品中安装成功或重新跑完35页图像生成。图片质量必须依赖真实宿主能力和最终审校。
