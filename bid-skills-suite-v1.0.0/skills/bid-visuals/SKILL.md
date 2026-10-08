---
name: bid-visuals
description: 制作说明方案的准确图表，确保每张图有任务、数据依据、正文对应和可编辑源。 适用于：架构图、流程图、网络图、实施计划图、配置示意、标书配图、数据图表。
metadata:
  version: "1.12.0"
  language: zh-CN
  sequence: '13'
  suite: bid-skills-suite
  title: 标书配图与图表制作
---

# 13｜标书配图与图表制作

制作说明方案的准确图表，确保每张图有任务、数据依据、正文对应和可编辑源。

运行条件：需支持读取项目文件；可选脚本需要 Python 3.10+，文档、视觉/OCR 与绘图能力由宿主提供。

## 触发与边界

当用户提出“架构图、流程图、网络图、实施计划图、配置示意、标书配图、数据图表。”时使用。不制造证书、检验报告、现场实施照片或实际业绩证据；不以装饰图替代方案。

## 开始前

先读 [共同证据与安全约定](references/evidence-and-safety.md)。仅当需要细化操作时读 [专项操作手册](references/playbook.md)；输出字段与示例参见 [产物契约](references/output-contract.md)。

输入：08图表任务、10确认方案、11正文、06格式与暗标限制、已授权图片或数据。

先读取`work/writing-settings.json`中的`visuals`，缺省按[配置示例](assets/writing-settings.example.json)与当前用户指令。`enabled`决定可选配图，`diagram_engine`决定技术图引擎（默认auto按图型路由Draw.io、PlantUML或Mermaid），`diagram_format`决定SVG（默认）或PNG输出，`layout_template`决定auto、layered、flow、pipeline、swimlane、network、parallel、sequence或matrix布局，`architecture_layers`可指定1—12层；`image_mode`决定宿主界面示意、概念生图或关闭；`tool/model`是可用工具和模型偏好，`style/aspect_ratio/max_images`是风格、比例与本次最多概念图数。`diagram_engine=blueprint`选择新增 Enterprise Diagrams 参考版式；`diagram_theme`可选reference、blue、teal、green、slate、monochrome，按[图表规格](references/ENTERPRISE_DIAGRAMS.md)写入JSON图源并渲染。Draw.io保持可用，auto路由不变。仅保存偏好不算已生成；实际参数映射和不可用项按[写作流程](references/WRITING_WORKFLOW.md)记录。旧`diagram_renderer`仅在读写已保存设置时一次性迁移，新保存不接受该字段。必要图表与关闭配置冲突时保留待处理项，不能省略后宣称符合要求。

上游技能：`bid-format-extraction, bid-outline-planning, bid-solution-design, bid-technical-writing`。独立使用时接收用户提供的等价文件，记录实际输入，不要求虚构完整流程状态。检查原件和产物版本；缺关键信息时给出范围受限的草稿及缺口。

## 执行步骤

图文交接和实际入稿检查见[写作流程](references/WRITING_WORKFLOW.md)。源码、实际渲染文件和已插入工作稿分别核验；正文或方案更新后重新核对图，不用旧图状态证明新版一致。招标原图属于需求来源，不能自动转成供应商已实施证据。

宿主Agent可通过自然对话接收图表修改；必须保留受影响章节/需求/`FIG-ID`、`base_revision`和hash CAS结果，并在目录或正文变化后重做受影响图表与入稿核对。界面概念图始终标示为示意，不得当作真实系统截图；遵循既有visuals配置。

本技能负责驱动实际生图：先区分界面设计示意、技术结构图与真实证据图片，再发现当前宿主已开放的工具并执行。Codex有Imagegen时加载其技能并调用实际工具；WorkBuddy等宿主使用该Agent实际提供的生图技能/插件/工具，不写死Codex接口或模型。软件核心操作需要界面示意时，不用流程图替代；生成画面标注“界面设计示意，非实际系统截图”。允许用户选择配图方式，优先级为逐图明确指令、已保存的项目偏好、默认规则。技术图默认auto路由：分层架构、网络和复杂流程优先Draw.io，时序和泳道优先PlantUML，简单流程优先Mermaid，输出默认SVG；系统界面示意默认使用当前宿主实际生图能力。宿主能力、调用、实际文件、章节预览与入稿都要核验，只有偏好/提示词不能标已生成。

1. **步骤1**

   为每个FIG-ID明确要回答的问题、目标章节、图型、信息来源和是否必须；没有解释作用的配图不生成。每张图规格保留source/evidence、输入revision、`base_revision`、源文件哈希和CAS结果。

2. **步骤2**

   从10冻结方案提取节点、边、阶段或数值，形成结构化图表规格；未知接口、设备或参数不能靠美观补上。工具不可用、provider unavailable、超时或渲染失败时保留明确gap和复跑条件。

3. **步骤3**

   技术图由`scripts/diagram_tools.py`驱动，使用[DIAGRAM_TOOLS.md](references/DIAGRAM_TOOLS.md)中的doctor、plan、render流程；不要在本技能中臆造命令行参数。显式blueprint时加载独立enterprise-diagrams Skill，或用自带scripts/diagram_svg.py和[规格](references/ENTERPRISE_DIAGRAMS.md)，把实际主题/布局写入.diagram.json后调用同一render流程。auto按图型选择Draw.io、PlantUML或Mermaid，默认SVG输出；显式选用方式不可用时记录provider unavailable缺口，不擅自更换用户选择。保留引擎源和输出文件，并检查文字与连线。只有源码时状态为specified，实际渲染后才可标rendered；数据图表由给定数据生成并保留计算来源。

4. **步骤4**

   界面设计示意或概念图需要生成式视觉时，调用本次宿主实际开放的生图工具／模型，并标注示意属性；保存生成文件、提示词/规格、实际工具与模型（工具未返回则记未确认）、输入方案版本和图注到图表 specification 及本次执行记录。栅格图的生成规格可用于再生，不冒称对象可编辑。无生图工具或实际调用失败时保留规格与缺口；企业现场、资质、检测记录及已实现系统截图只能使用授权真实材料。

5. **步骤5**

   配色、字体和品牌服从06；暗标项目检查图中文字、logo、图层名与元数据，不添加识别投标主体的装饰。

6. **步骤6**

   逐一比对图中系统名、方向、数量、时间和责任与正文；概念边界图不能暗示未经确认的系统接入。

7. **步骤7**

   输出图注、替代文本、插入位置、文件路径、源文件和权限说明；宿主无绘图工具时输出图表源码，不冒充已渲染。

8. **步骤8**

   按最终版心尺寸检查可读性，交14编排、15内容复核、16成稿检查；图表内容变化应触发相关章节复审。

## 产物与交接

保存 `13-visuals.json`（机器可读）和同名 `.md`（可读报告），使用 [JSON模板](assets/output.template.json) 与 [报告模板](assets/report.template.md)。字段必须符合 [JSON Schema](assets/output.schema.json)。不要把模板空值直接当结果；详细演示见 [合成示例](assets/example.output.json)。

01—14产物放项目`artifacts/`，15放`reviews/`，16放`deliverables/`，17放`work/`。来源原件只读置于`inputs/`；图表置于`assets/`；规则配置置于`profiles/`。路径始终相对用户指定项目根，不写死本技能安装目录。

每个输出记录`project_id / artifact_id / revision / inputs / status`。`inputs`内SHA256从实际输入文件计算。缺依赖、未运行检查和待确认分别保留；不把模型产生结果等同于业务完成。

可选执行本技能目录内的校验器：

```bash
python scripts/validate_output.py /absolute/path/to/13-visuals.json
```

脚本只校验结构及部分一致性，不检查所有真实语义与授权。依赖不足可按清单人工检查，但必须写明“脚本未运行”。

## 验收检查

- [ ] 每张图对应明确章节任务。
- [ ] 节点与参数来自确认方案。
- [ ] 保留可编辑源与图注。
- [ ] 不伪造真实证据照片。
- [ ] 暗标与版权／传输范围被核对。

## 人工确认点

图中实体、接口、数量、品牌、照片来源和外部图像服务的数据授权需确认。

## 常见陷阱

- 箭头方向可能改变接口责任。
- 生成式图片中的文本和数字必须复核。
- 设备概念图不得标作实际交付型号照片。
- 图很清楚但插进A4后字可能不可读。

## 调用示例

> 请按章节任务制作必要图表，先给图表规格与节点关系，再生成可编辑源和插入文件，保证与方案和正文一致。

示例原件 `assets/synthetic-tender.md` 和 `assets/synthetic-supplier.md` 全为合成资料，不能用作真实投标证据。场景配置参考 `assets/profile-catalog.json`，所有条目只是待项目核验的种子，不是已通过业务验收的行业规则。

## 失败与恢复

先保存已完成的产物、失败范围和下一步；原件变更或输入哈希变化时重核受影响内容。不要自动覆盖人工新版本，不代签批，不上传资料，不声称已在后台继续运行。测试建议见 `tests/cases.json`；这些是待执行的业务评测用例，不是已通过记录。
