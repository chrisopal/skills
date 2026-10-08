# 技术图工具与布局模板

13负责选择和实际调用工具，14负责入稿，15/16按当前版本复核。绘图引擎与输出格式分开：Enterprise Diagrams、Draw.io、PlantUML、Mermaid是工具；SVG、PNG是成图格式。程序渲染成功仅能标rendered，语义和实际页面检查后才能标reviewed。

## 按图型执行

| 图型 | auto优先工具 | 模板与检查 |
|---|---|---|
| 总体/功能/部署架构、网络和配置图 | Draw.io | 从确认方案确定1—12层或非分层结构；检查系统边界、组件归属、接口与箭头 |
| 时序图 | PlantUML | 参与者、消息顺序、alt异常分支、返回/重试、编号；长图拆页 |
| 简单流程 | Mermaid | 开始/结束、条件和异常；节点过多时拆分 |
| 多角色复杂流程、泳道 | Draw.io | 明确泳道责任、退回、超时、关闭条件；PlantUML可按实际可用能力替代 |
| 系统界面示意、效果图 | 当前宿主生图Skill | Codex加载Imagegen并调用实际工具；其它宿主发现实际注册能力；标明示意 |

优先级是逐图明确指令→保存的项目偏好→auto图型规则。显式不可用引擎保持blocked，不静默替换；auto可选择已安装工具，记录替代原因并重新生成该工具的原生源，不把.drawio传给Mermaid。所有工具均未可用时保留specified源和缺口。doctor仅检查可执行文件位置，Java、浏览器和具体图型能否渲染要实际调用验证。

布局模板目录为`assets/diagram-templates/catalog.json`。层数是表达选择，不能为了填满模板发明系统。采用1—12层时写出每层目的和已有组件；客户未指定层数时按方案决定。超过单页版心可读范围应拆成总体图和局部图。模板约束颜色、字号、留白、分组和连线；图中文字、实体和数据始终来自本项目10/11。

## Enterprise Diagrams：参考版式与可选主题

新增独立 enterprise-diagrams Skill。选择 `visuals.diagram_engine=blueprint` 后，宿主加载该 Skill，或读取独立 bid-visuals 自带的[规格说明](ENTERPRISE_DIAGRAMS.md)并运行相同渲染器。Draw.io 仍可选，既有 auto 路由不变。新引擎支持八种结构：layered、flow、pipeline、swimlane、network、parallel、sequence、matrix；颜色主题为 reference（参考多色）、blue、teal、green、slate、monochrome。主题只影响此引擎；系统界面示意仍用当前宿主生图 Skill。

执行步骤：读设置 → plan → 根据已确认的10/11设计写 `.diagram.json` → render → 逐图语义与视觉检查 → A4检查 → 更新13并推进14/15/16。**设置不会自行生成图**。宿主必须把 plan 的 `diagram_theme` 写入源的 `theme`，把 `layout_template` 写入 `layout`，按 `architecture_layers` 组织已有组件；图中文字和关系由当前项目设计决定。层数只是偏好，发生语义冲突时与用户对话调整，不能发明组件。逐图明确指令优先于设置，覆盖原因记入 specification。

JSON 的 row/col/span 控制语义顺序与组合，渲染器自动调整节点大小、换行和正交连接；不是将任意图交给自动语义布局。分层、编号步骤、分支/汇聚、虚线反馈、平行工艺、多角色泳道、并行任务、分区网络、简单时序/自消息和矩阵均有可编辑规格。时序含复杂 alt/loop 嵌套时用保留的 PlantUML/Draw.io；大图按正文版心拆成总览与局部，不以缩小字号掩盖信息拥挤。

```bash
python scripts/diagram_tools.py plan --settings /project/work/writing-settings.json --kind architecture
python scripts/diagram_tools.py render --project /project --source assets/architecture-r3.diagram.json --engine blueprint --expected-theme reference --out assets/architecture-r3.svg --base-sha256 "$SOURCE_SHA256"
python scripts/diagram_tools.py render --project /project --source assets/architecture-r3.diagram.json --engine blueprint --expected-theme reference --out assets/architecture-r3.png --base-sha256 "$SOURCE_SHA256"
```

宿主从 plan 取 `diagram_theme` 传给 `--expected-theme`；逐图覆盖时传该图确认的主题。参数与源主题不一致会在调用渲染器前阻断，receipt 同时保存期望主题与实际样式。调用记录和哈希用于绑定文件版本，不能作为不可伪造的执行证明；实际执行与视觉检查仍须分别提供。

SVG 使用 Python 标准库，保留纯文本矢量和 JSON 源。PNG 仅调用宿主**已有** CairoSVG，缺失时显式失败并保留源，可改用 SVG；不自动安装。字体使用宿主已安装字体，中文必须在实际浏览器与 PNG/Word 中检查。receipt 的 `diagram_style` 记录实际主题、布局和几何；主题改变须保存新源并重新渲染，旧图的源 SHA 校验会失效。使用新引擎的 rendered/reviewed 图与 Draw.io 同样要求完整 render_record；源、成图和调用记录都不能只填路径。

## Draw.io Skill与本地运行

[官方Codex插件](https://github.com/jgraph/drawio-mcp/blob/main/plugins/codex/drawio/README.md)提供drawio Skill；加载当前已安装版本，按实际CLI帮助调用。插件可选，独立bid-visuals包含本页和本地渲染脚本，可由宿主生成原生XML执行。PNG/SVG导出及ELK/libavoid布局需要Draw.io Desktop；Skill可加载不等于桌面工具就绪。

源为.drawio XML，组件和关系可在图形编辑器调整。固定分层/泳道布局优先保持节点位置；需要清理连线时可选择libavoid，但须先核对当前CLI实际支持；已知本机32.3.0拒绝该参数，不能根据插件文档声称可用。当前固定层/泳道模板使用原生正交连线与显式路径点。自由流程可选verticalFlow/horizontalFlow自动排布；ELK已经排线，不叠加libavoid。不要用自动布局打散已确认的层次。

即使上游插件建议删除中间源，本套件仍保留原生.diagram.json/.drawio/.mmd/.puml及文件哈希，避免丢失13的编辑与审计依据。工具可把XML嵌入SVG/PNG，但嵌入文件不代替本项目规范图源。图形编辑后将新源保存成新修订，再导出新文件；旧导出不能继续作为新版依据。

## 本地脚本

无新增Python依赖，不自动安装或调用云端图服务。当前宿主发现工具；PlantUML可使用plantuml命令，或Java加`PLANTUML_JAR`指定JAR；本机约定的可选位置为`~/.local/share/bid-diagrams/plantuml.jar`。脚本在SANDBOX安全配置下执行PlantUML；不依赖外部include、私有文件或远程图片。

```bash
python scripts/diagram_tools.py doctor
python scripts/diagram_tools.py plan --settings /project/work/writing-settings.json --kind architecture
python scripts/diagram_tools.py plan --settings /project/work/writing-settings.json --kind flow --complex-flow
python scripts/diagram_tools.py render --project /project --source assets/architecture-r2.drawio --engine drawio --layout none --out assets/architecture-r2.svg --base-sha256 "$SOURCE_SHA256"
python scripts/diagram_tools.py render --project /project --source assets/architecture-r2.drawio --engine drawio --layout none --out assets/architecture-r2.png --base-sha256 "$SOURCE_SHA256"
python scripts/diagram_tools.py render --project /project --source assets/events-r2.puml --engine plantuml --out assets/events-r2.svg --base-sha256 "$SOURCE_SHA256"
python scripts/diagram_tools.py render --project /project --source assets/events-r2.puml --engine plantuml --out assets/events-r2.png --base-sha256 "$SOURCE_SHA256"
```

SOURCE_SHA256必须为每次读取的对应图源实际64位小写SHA256，不能省略；渲染器使用不可变快照，并在校验及发布后复核原源，发现变化撤回输出和记录。Mermaid优先使用已有浏览器，可通过`MERMAID_BROWSER_EXECUTABLE`指定；macOS已安装Chrome时可直接使用，不自动下载浏览器。命令中的/project是用户项目根的示例，运行时替换成真实路径。渲染超时默认60秒，可用`--timeout`显式设置1—300秒；宿主仍应及时向用户更新进度。使用`--base-sha256`携带修改前实际源哈希；运行前或运行中源改变则拒绝发布。拒绝覆盖已有文件和越出项目的路径。每次成功生成旁置的`.receipt.json`，记录实际命令、源/输出hash、布局和visual_review=NOT_RUN。失败不发布成功文件、不推进13状态；模型、图片生成和人工审核由宿主执行。

## 对话修改与编辑保存

用户可说“改为四层”“增加退回路径”“把审计移到侧边”等。宿主定位FIG-ID、读取base_revision和源hash，先核对影响的10设计/11正文，再输出新源与新修订。未经解决的接口、品牌、容量不能靠修改图补齐。源hash冲突时读回并合并，不覆盖另一窗口的修改。

图形编辑使用本机Draw.io或用户宿主支持的编辑器。保存新源后核对实际字节与render receipt；重新预览、核对章节、生成Word/PDF，使受影响14/15/16重新检查。必要时可通过[官方嵌入接口](https://www.drawio.com/docs/reference/embed-mode/)把Draw.io编辑器接入现有宿主应用，但本套件不虚构已部署的iframe/MCP服务；在线端点与私有材料传输授权单独核对。

## 产物与验证

13沿用FIG-ID、section_id、specification、source_path、rendered_path、caption及evidence_ids。时序图用kind=sequence，泳道用kind=swimlane；多行工艺与并行任务按kind=flow，响应矩阵按kind=configuration，源中分别选择pipeline、parallel与matrix布局；不得把技术图标成concept来绕过图型检查。将工具、模板、设置版本/hash、工具调用receipt路径、SVG与PNG路径、输入10/11版本写入specification或项目执行记录。rendered_path指向实际入稿图；保留其它格式作为源或派生文件。

对于`rendered`或`reviewed`状态且源文件为`.diagram.json`/`.drawio`/`.puml`的图，13必须附带严格的`render_record`：`engine`（`blueprint`/`drawio`/`plantuml`/`mermaid`）、`source_sha256`、`output_sha256`、`receipt_path`、`receipt_sha256`、`base_source_sha256`以及`cas_result=matched`。`writing_checks.py`会读取源、成图和receipt并核对实际哈希；receipt内的`engine`、`source_path`、`output_path`、源/输出哈希、`base_source_sha256`和`cas_result`也必须与记录一致。源、成图、receipt任一缺失或篡改都会阻断结构检查。历史`.mmd`、`.svg`或Imagegen图没有新记录时可以保留，但只能说明没有CLI审计记录，不能声称已通过该审计。

逐图检查实体与关系是否支持正文，未确认接口要在图注说明；检查文字清晰、连接线避开节点、决策分支完整。再按A4版心缩放检查，Word只插入支持的PNG/JPEG，HTML可展示SVG。检查DOCX媒体关系、PDF页数/字体/图像与所有实际页面。缺文件、超时、语法错误、截图文字错误或无工具都保持问题；不把成功退出码等同于视觉或真实系统验收。界面图固定为“界面设计示意，非实际系统截图”。

模板和渲染工具均服务当前任务，不代表某宿主已有知识库/生图/绘图MCP。WorkBuddy的宿主执行和MCP接入未实际运行时明确Not run，不以Codex本地成功替代。
