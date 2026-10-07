# image-to-editable-ppt 上游选择性同步审查（2026-10-07）

本次只回移兼容的执行契约、文档和测试。`skills/image-to-editable-ppt/cli/` 的所有文件均保持 PR #3 基线字节不变；没有更换后端、模型默认值、视觉门禁或状态机。审查结论按 A「应同步的上游变化」、B「明确保留的本地定制」、C「需人工判断的冲突或范围选择」组织。C 项均明确暂缓，不代表已合并或自动选择了上游行为。

## 版本与集成边界

| 对象 | 固定提交 / 事实 |
| --- | --- |
| `chrisopal/skills` 当前 `main` | `f95bc08516c44c9fa79597b39d1d981f30ec7f5e`，通过 `git ls-remote` 与 fetch 核实 |
| PR #3 工作基线 | `39be6e8c5641c7a5deb5d585992655bdbca831b3`，分支 `codex/image-to-editable-ppt-visual-qa`；PR open、未合并 |
| 比较上游 `ningzimu/image-to-editable-ppt-skill@main` | `b7be494e31a0ed56ef98716891db5474606b8cdf` |
| 初始导入 | monorepo `06ac6e1`；`STATUS.md` 记录来自 `chrisopal/image-to-editable-ppt-skill`，源版本 `fb869763127fd31ba7288d905671ffc4ea542f60` |
| 本地专项提交 | `c23a4d0` visual QA、`122c18b` 后端边界文档、`16c7e35` portable backend |
| 本次变更分支 | `codex/image-to-editable-ppt-contract-sync`，从 PR #3 head 建立，供增量审查 |

当前 `main` 尚未包含 PR #3 的本地功能，不能把它当成保留定制的安装源。PR #3 还包含其他技能的大量改动，因此本次既不合并整个 PR #3 到 `main`，也不改写 PR #3 的 head。本次 PR 应以 `codex/image-to-editable-ppt-visual-qa` 为 base，后续进入 `main` 的方式需单独审查。GitHub PR 元数据中的 `base_sha=380f1c6` 是 PR 快照；本报告的当前 main 使用实际 Git ref `f95bc08`。

映射为 fork `image-to-editable-ppt/<path>` ↔ upstream `<path>`。通过 `git ls-tree -r` 的文件模式与 blob 哈希逐一比较，排除 `.git`、缓存和临时输出。基线共有 **109 个路径：54 相同、41 修改、10 上游独有、4 本地独有**。下表同时标明 PR #3 路径相对当前 main 是否不同，避免把本地定制误认为上游新增。

## A. 应同步且本次已处理

| 编号 | 行为 / 来源 | 处理和验证 |
| --- | --- | --- |
| A1 | Entry Contract 的 OCR/图片调用授权、任务数据范围、local-only/保密例外、受限网络审批；`run hints`；已派发 worker 的 active lease | PR #3 已具有这些上游条款，逐段核实后保留，不重复粘贴；新增契约回归与只读/租约运行时测试。审批要求仍以运行时为准。 |
| A2 | 较新的仅图片编辑说明，上游示例为 `gpt-image-2.5-sunburst` | 同步中/英/韩 README、文档首页和 FAQ 共 9 处；明确这是图片结果示例、需核实工具可用性，本 fork CLI 默认仍是 `gpt-image-2`。没有执行新模型 API 请求。 |
| A3 | `npx -y skills@latest add` → 刷新 editable CLI → doctor；`python3` | SKILL 已有 npx 流程但指向上游，会覆盖定制；改用 `chrisopal/skills` 已审查提交的准确安装包子目录，补全 3 种语言的安装/更新说明及 `agent-image-tool`、visual-QA、extract-source 可用性检查。源码保持上游目录结构。 |
| A4 | `7e86fb3` 自主执行与测量纠偏；标识性文字例外 | 只回移 routine steps 不额外确认、可靠测量优先并核对异常测量、素材板保留 logo wordmark 例外。这些不依赖新 runtime，不放宽任一视觉 QA 门禁。 |
| A5 | `7e86fb3` 中可兼容的拒绝录入回归 | 验证失败时 page jobs 和现存产物不变；通过真实 `page validate` 产生新报告再 record，取代测试直接写 `passed:true`。未复制要求新恢复提示或 asset_hashes 的断言。 |

## B. 明确保留的本地定制

| 编号 | 保留语义 | 保护范围 |
| --- | --- | --- |
| B1 | `builtin-imagegen` → 经能力核验的 `agent-image-tool` → CLI（Codex OAuth → 用户配置的 API）；文生图、参考图编辑、有效本地输出三能力齐备 | 保留 `runtime_id`、`producer_id`/`producer_model`、fallback 事件与 provenance；视觉理解工具不等于图片生成后端；worker 必须可调用同一工具。上游替换会删除这一层。 |
| B2 | 运行时视觉 QA、`visual-qa.json`、`visual-diff.png`、`visual_qa_passed` | 保留 page validate 和 record 重算证据、finalize 对页面结构/视觉通过标志的检查；碰撞、形状色彩、结构几何、已配置 diff 阈值都不能变成普通 warning。新增测试验证伪造通过标志会被覆盖并拒绝。 |
| B3 | `image extract-source` 与 `source-faithful-extraction` | 只允许完整、无遮挡、均匀局部背景的对象；不扩展到任意源图裁切。保持全部实现、字段、决策和回归。 |
| B4 | 完整阅读 page references、原有失败重建边界、单页 local claim / 多页 worker | 不用上游短 prompt 替换本地高风险提醒。原生工具记录、视觉产物和 dispatch claim 限制不变。 |

## C. 需要人工判断，未自动回移

| 编号 | 上游变化 | 不可直接合并的原因 | 后续决策与验收要求 |
| --- | --- | --- | --- |
| C1 | `d3ac8c5` 将 CLI 默认改为 `gpt-image-2.5-sunburst`，新增 flare/sunburst、xhigh/max 与模型名称校验 | 本地 `configure_image_backend.py` 写有 fallback_model，配置默认值、CLI 默认值、文档和 producer 记录必须一致；仅改 README 会误导，直接替换则可能删除 portable 字段 | 决定是否升级默认值，并验证所用 OAuth/API 服务的模型/质量支持；同步 image_gen、runtime_env、backend contract 和模型测试。本次保留 gpt-image-2。 |
| C2 | `7e86fb3` 原 owner 原地修复、只修受影响产物、复用已核验素材、终态才 reset | 本地 SKILL/worker 明确失败后重建，record 的两条错误提示仍建议 reset；文档单独改会与 CLI 和 worker 指令矛盾 | 设计 owner 可达/终态的统一恢复矩阵，原子修改 parent/worker/CLI 错误提示和测试，同时保持视觉 QA 重算；本次只回移不改变行为的测试部分。 |
| C3 | `7e86fb3` record 记录 asset_hashes；finalize 校验全部已记录产物和资产哈希 | 本地现存 run 没有 asset_hashes，QA 文件在 record 时重算；照搬可能拒绝旧 run，也不能遗漏本地视觉证据 | 明确旧记录重验/重录迁移方式，验证 manifest、图片、QA 报告及输出任意篡改/缺失都阻止 finalization；不得用放松视觉验证解决迁移。 |
| C4 | `7e86fb3` 结构化 role/object_type/source_type、来源链接、词边界和否定语句识别 | 上游允许集不含本地 source-faithful-extraction，且替换同一 validator 会移除视觉门禁；本地仍可能误判 benchmark/trademark 或 no crop | 保留本地合法抽取来源，合并结构化来源核验与负例；同时验证旧 manifest 兼容。现有误判风险明确留存，未伪称修复。 |
| C5 | `9e55ef7` 曲线/箭头/虚线、`0d60c8e` 原生表格；screen16x9 和 theme style-list OOXML 修正 | 新对象要扩展 build、preview、manifest、record/finalize 校验；本地视觉 QA 当前遍历 text_boxes/images/shapes，不可直接认为能覆盖 tables/path。OOXML 修正本身可独立，但属于本次未授权扩展的运行时代码范围 | 建议将 OOXML 兼容修复优先拆成后续专项；表格/曲线必须补视觉 QA 覆盖、独立 PPT 读取与实际 Office 打开验收。当前文件可打开性未以真实 Office 验证。 |
| C6 | `bda295e` 与 `7e86fb3` 整对象 region 切分、原始 Alpha 保留、微弱残留警告、组件合并/过滤次序 | 新 --regions 和 JSON 契约当前不存在；切分输出/命名/Alpha 行为会变，直接导入文档会调用不存在的能力；微弱残留容差需与视觉门禁对齐 | 联合移植处理链与 region/Alpha 回归，保留本地精确 source extraction 为另一条来源；审核边界触碰、碎片、覆盖率及 provenance。 |
| C7 | 按需读取 references、精简 hard rules、减少重复 QA、接受轻微边缘残留 | 上游文本会删除本地视觉产物和 source extraction 条款；本地 AGENTS 明确完整读取与约束不得无证据删除 | 如需要降上下文开销，逐条映射本地红线、前向测试再改；对 minor warnings 的放宽不能豁免 runtime 失败。 |
| C8 | 赞助商/推广资源、版本元数据、/data ignore、上游发布记录 | 与本次执行契约同步无关；同步版本号/发行说明可能声称具备尚未移植功能 | 明确保留本地版本/品牌与 release 状态；推广内容及布局治理由维护者选择。本次不添加 3 个宣传图片。 |

既有指令张力（非本次新引入）：Phase 1 的 OCR 询问文字若无条件执行，会与用户已选择 local-only 冲突；当前 CLI 没有全面的 no-egress 开关，local-only 是 agent 契约，不是强制网络隔离。只读场景检查正确选择了 `prepare --no-text-hints` 和逐页离线 `page hints`，但多 worker 的限制传达仍需谨慎。另有 worker 泛化的缺工具失败规则与 decision tree 对缺 TeX 的公式 warning 例外；应以具体例外为准。两者都没有在本次静默重写运行时或扩大授权。

## 逐文件审查：55 个差异路径

下列路径相对于嵌入目录；blob 为 Git 内容标识前 10 位，完整提交已固定。`PR≠main` 表示 PR #3 与本次检查到的 main 的该路径不同。A/B/C 的同一行可并存，表示只合并特定 hunk，绝不整文件覆盖。

| 路径 | 基线差异 | PR≠main | fork / upstream blob | 分类与逐文件处理 |
| --- | --- | --- | --- | --- |
| `.gitignore` | 修改 | 否 | `17354859e4` / `b3e5722524` | **C8**：上游新增 /data 忽略项；无本次契约依赖，保留。 |
| `AGENTS.md` | 修改 | 否 | `1eff8de5d9` / `0e9f18f810` | **B4 / C7**：上游允许有证据地退役规则并改为按需阅读；本地仍要求完整读取与约束保留。 |
| `CHANGELOG.md` | 修改 | 是 | `dcd9af426b` / `d40e77c86e` | **A / B / C8**：只追加本次回移记录；保留本地 unreleased 条目，不宣称已具备上游 0.3.3/0.4.0 功能。 |
| `README.md` | 修改 | 是 | `06e7a120be` / `211c6a8e3a` | **A2,A3 / B1 / C1,C5,C8**：同步仅图片编辑示例及 fork 安装更新说明；保留 portable 后端描述，不加入未实现能力或推广内容。 |
| `README_en.md` | 修改 | 是 | `69af161942` / `5c6e8665f8` | **A2,A3 / B1 / C1,C5,C8**：同步仅图片编辑示例及 fork 安装更新说明；保留 portable 后端描述，不加入未实现能力或推广内容。 |
| `README_ko.md` | 修改 | 是 | `d74f28b8d3` / `6577de102e` | **A2,A3 / B1 / C1,C5,C8**：同步仅图片编辑示例及 fork 安装更新说明；保留 portable 后端描述，不加入未实现能力或推广内容。 |
| `assets/codia-noteslide-logo.png` | 上游独有 | 否 | `—` / `202f5903f3` | **C8**：上游赞助/推广资源；不是执行契约依赖，不自动导入。 |
| `assets/image-to-editable-ppt-promo-poster.png` | 上游独有 | 否 | `—` / `704c66cfc4` | **C8**：上游赞助/推广资源；不是执行契约依赖，不自动导入。 |
| `assets/spire-presentation-logo.png` | 上游独有 | 否 | `—` / `c175d53f82` | **C8**：上游赞助/推广资源；不是执行契约依赖，不自动导入。 |
| `docs/README.md` | 修改 | 是 | `b752fb6294` / `4a448feea4` | **A2 / B1 / C5,C8**：同步轻量替代示例并区分 CLI 默认值；保留后端定制，不导入 tables 宣称或推广卡。 |
| `docs/en/README.md` | 修改 | 是 | `e7a6277c8f` / `92b4eb5178` | **A2 / B1 / C5,C8**：同步轻量替代示例并区分 CLI 默认值；保留后端定制，不导入 tables 宣称或推广卡。 |
| `docs/en/faq.md` | 修改 | 是 | `b0f8c89ea5` / `12b499188e` | **A2,A3 / B1 / C1**：同步替代方式和 fork 更新指引；保留实际默认模型和后端门槛。 |
| `docs/en/installation.md` | 修改 | 是 | `788839a9af` / `af1d9542fd` | **A3 / B1 / C1**：改用 commit-pinned 子目录安装、CLI 刷新与本地能力检查；保留 backend 语义。 |
| `docs/en/workflow.md` | 修改 | 是 | `39c42317f4` / `83ab050c47` | **B1 / C2,C5**：保持已实现流程；不宣称新的局部恢复与原生表格功能。 |
| `docs/faq.md` | 修改 | 是 | `c0760ddafd` / `b9bf36d14b` | **A2,A3 / B1 / C1**：同步替代方式和 fork 更新指引；保留实际默认模型和后端门槛。 |
| `docs/installation.md` | 修改 | 是 | `4b541f31a4` / `611fcd076d` | **A3 / B1 / C1**：改用 commit-pinned 子目录安装、CLI 刷新与本地能力检查；保留 backend 语义。 |
| `docs/ko/README.md` | 修改 | 是 | `82cfb4e4f0` / `2c8c2ee1da` | **A2 / B1 / C5,C8**：同步轻量替代示例并区分 CLI 默认值；保留后端定制，不导入 tables 宣称或推广卡。 |
| `docs/ko/faq.md` | 修改 | 是 | `fdfdfa699d` / `648ca0a5a3` | **A2,A3 / B1 / C1**：同步替代方式和 fork 更新指引；保留实际默认模型和后端门槛。 |
| `docs/ko/installation.md` | 修改 | 是 | `a5f4190c3e` / `9c8bab9fe8` | **A3 / B1 / C1**：改用 commit-pinned 子目录安装、CLI 刷新与本地能力检查；保留 backend 语义。 |
| `docs/ko/workflow.md` | 修改 | 是 | `a7706c66f9` / `a270382929` | **B1 / C2,C5**：保持已实现流程；不宣称新的局部恢复与原生表格功能。 |
| `docs/workflow.md` | 修改 | 是 | `f44b5c8e69` / `61117f163f` | **B1 / C2,C5**：保持已实现流程；不宣称新的局部恢复与原生表格功能。 |
| `skills/image-to-editable-ppt/SKILL.md` | 修改 | 是 | `c11a6930df` / `5d4fcc0a7b` | **A1–A3 / B1–B3 / C2,C7**：保留已有授权/租约与本地门禁；回移自主执行、python3 和适配 fork 的更新契约；不覆盖整份文件。 |
| `skills/image-to-editable-ppt/cli/editppt/__init__.py` | 修改 | 否 | `3dc1f76bc6` / `f38884b647` | **C8**：上游新增 __version__；不冒充已同步对应发布版本。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/_page_artifacts.py` | 修改 | 否 | `999112fbfd` / `4a1c3a5b15` | **C6**：上游改为检查/保留输入 Alpha 并传递 regions；与素材处理链一起评估。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/build_pptx_from_manifest.py` | 修改 | 否 | `20d3d2e72d` / `8b724cf378` | **C5**：原生 tables/path、dash/arrow、线宽预览、screen16x9 和主题样式列表修正；不单独声称已支持。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/configure_image_backend.py` | 修改 | 是 | `3ed5122e5e` / `66cef4ed65` | **B1**：保留 agent-image-tool、runtime_id、能力发现和固定 fallback_model；上游整体替换会移除。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/extract_source_asset.py` | 本地独有 | 是 | `70ff72a26d` / `—` | **B3**：本地独有：均匀背景完整对象精确像素抽取；保持文件和限制。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/finalize_deck_run.py` | 修改 | 否 | `340a723c52` / `0090807256` | **C3**：上游新增录入输出/资产哈希复核；与本地视觉证据、历史 run 的迁移需联合设计。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/image_gen.py` | 修改 | 否 | `c9f66ebb25` / `fd55432ec9` | **C1**：上游更换默认模型、增加 xhigh/max 及严格模型名称匹配；保持本地请求行为。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/main.py` | 修改 | 是 | `c07653397c` / `20260d073d` | **B1–B3 / C1,C6**：保留 backend/runtime-id、visual-qa、extract-source 和默认 validation.json；不引入 regions 或新模型示例。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/native_tables.py` | 上游独有 | 否 | `—` / `91c1f0caa3` | **C5**：上游独有：原生表格归一化、合并、OOXML 与文本预览；需适配本地 QA。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/path_geometry.py` | 上游独有 | 否 | `—` / `889c854ab3` | **C5**：上游独有：路径校验、贝塞尔曲线、虚线/箭头预览；需适配本地 QA。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/prepare_deck_run.py` | 修改 | 是 | `bdace6bfdc` / `f90f530c9a` | **B2**：保留 page request 所需的 visual-qa.json 与 visual-diff.png 输出。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/process_asset_sheet.py` | 修改 | 否 | `d3270b46d2` / `de92d4b771` | **C6**：上游新增 --regions 参数与传递；当前运行时不支持，不能只复制文档。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/record_imagegen_result.py` | 修改 | 是 | `60c4a02eb3` / `13f7edc266` | **B1**：保留 agent-image-tool 生产者、producer_id/model、fallback 事件校验和可读输出校验。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/record_page_result.py` | 修改 | 是 | `8010697468` / `8f612a0678` | **B2 / C2,C3**：保留重算视觉 QA；上游原 owner 修复提示与 asset_hashes 要联合移植，不能覆盖。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/reset_page_job.py` | 修改 | 否 | `34f0c919dc` / `8cff9e1f4a` | **C2**：上游收紧 help/error 的终止与取消措辞；当前两道参数校验保持，整套恢复语义另议。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/runtime_env.py` | 修改 | 否 | `cedba39bba` / `5fe1d01640` | **C1**：上游配置默认模型变化；本次保留 gpt-image-2，与配置和文档保持一致。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/split_alpha_components.py` | 修改 | 否 | `d0745595bc` / `4638fbbd9b` | **C6**：上游新增 region 完整对象切分、残留容差、合并后面积筛选及输入保护。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/validate_pptx.py` | 修改 | 是 | `a62e0b71cb` / `abcc4b3493` | **B2,B3 / C4,C5**：保留视觉门禁和 source-faithful-extraction；上游结构化 provenance、表格/曲线检查不能整体替换。 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/visual_qa.py` | 本地独有 | 是 | `3c212e92ab` / `—` | **B2**：本地独有：重叠、颜色、结构几何、可选 diff 阈值与带原因的精确例外；完整保留。 |
| `skills/image-to-editable-ppt/prompts/page-worker.md` | 修改 | 是 | `92e8071a0e` / `76cd6e05ea` | **B1–B4 / C2,C7**：保留完整必读、原生工具记录、视觉产物和失败后重建契约；不采纳上游缩短版整体覆盖。 |
| `skills/image-to-editable-ppt/references/agent-image-backends.md` | 本地独有 | 是 | `98c324a907` / `—` | **B1**：本地独有：各 agent 的发现与三能力检查指南；完整保留。 |
| `skills/image-to-editable-ppt/references/cli-helper.md` | 修改 | 是 | `73589404f4` / `7600d10aff` | **A3 / B1–B3 / C1,C2,C6**：仅同步 python3；保留本地命令与验证默认值，不展示尚不支持的 regions/新质量参数。 |
| `skills/image-to-editable-ppt/references/manifest-schema.md` | 修改 | 是 | `015e6792fc` / `5266190e59` | **B1–B3 / C3–C6**：保留本地字段契约；上游新增资产哈希、tables/path、结构化来源和 regions 暂不导入。 |
| `skills/image-to-editable-ppt/references/page-decision-tree.md` | 修改 | 是 | `dd737e3c6a` / `df0b37b202` | **A4 / B2,B3 / C2,C5–C7**：只同步可靠测量优先与标识性文字例外；保持抽取、视觉门禁及其他决策不变。 |
| `tests/test_alpha_regions.py` | 上游独有 | 否 | `—` / `44f2025453` | **C6**：依赖尚未回移的 Alpha/regions 运行时，不复制或跳过伪装为通过。 |
| `tests/test_image_models.py` | 上游独有 | 否 | `—` / `ce5c726b3e` | **C1**：预期新的默认值及质量参数，与保留的 CLI 行为不兼容，明确暂缓。 |
| `tests/test_multi_agent_backend.py` | 修改 | 是 | `a0237e03f5` / `a264d71e9b` | **A5 / B1,B2 / C2,C3,C6**：回移拒绝录入不改写状态/产物、真实重验再录入断言；保留本地 backend/QA/extraction 测试。 |
| `tests/test_native_tables.py` | 上游独有 | 否 | `—` / `157f3bdf8a` | **C5**：依赖原生表格实现与合并语义，暂缓。 |
| `tests/test_path_geometry.py` | 上游独有 | 否 | `—` / `71d485eef4` | **C5**：依赖新 path/line geometry 校验，暂缓。 |
| `tests/test_quality_contracts.py` | 修改 | 是 | `91065237b3` / `060b1ebbc7` | **B3 / C4**：保留精确抽取通过/非法裁切拒绝测试；结构化 provenance 的新预期暂缓。 |
| `tests/test_slide_layout.py` | 修改 | 否 | `1de20bc153` / `494f8db4e5` | **C5**：上游 screen16x9/theme 样式列表与实际 OOXML 检查依赖 builder 修正，暂缓。 |
| `tests/test_table_validation.py` | 上游独有 | 否 | `—` / `af66f95550` | **C5**：依赖 table-only 页面与单元格/合并校验，暂缓。 |
| `tests/test_visual_qa.py` | 本地独有 | 是 | `cacc4c6b6f` / `—` | **B2,B3**：本地独有：碰撞、颜色/几何偏差、干净页与精确抽取回归全部保留。 |

## 逐文件审查：54 个相同路径

以下逐文件 blob/文件模式相同，无需同步；保留路径与内容。行为包括输入归一化、notes、文字测量、dispatch 状态管理、prompt builder、公式工具及其他不受此次上游增量影响的辅助能力。相同不等于已经验证所有端到端场景。

| 路径 | 共用 blob | 本次处理 |
| --- | --- | --- |
| `.github/pull_request_template.md` | `4860609b97` | 保持；无需同步 |
| `.github/workflows/changelog-check.yml` | `1ba161a6cc` | 保持；无需同步 |
| `.github/workflows/ci.yml` | `c46fb535a0` | 保持；无需同步 |
| `.github/workflows/pr-title.yml` | `65fabc62cb` | 保持；无需同步 |
| `.github/workflows/release.yml` | `33ed61251e` | 保持；无需同步 |
| `LICENSE` | `f769fc5582` | 保持；无需同步 |
| `assets/codex-full-access-permission.png` | `b71d80db95` | 保持；无需同步 |
| `assets/image-to-editable-ppt-overview.png` | `8a5f947484` | 保持；无需同步 |
| `assets/showcase-editable-ppt-result-investment-platform.png` | `70922711aa` | 保持；无需同步 |
| `assets/showcase-editable-ppt-result-market-snapshot.png` | `dca3c707cb` | 保持；无需同步 |
| `assets/showcase-editable-ppt-result-mdt-kidney-cancer.png` | `9dc2cfeba9` | 保持；无需同步 |
| `assets/showcase-editable-ppt-result-status-report.png` | `bca9d6efdd` | 保持；无需同步 |
| `assets/showcase-origin-investment-platform.png` | `ba74087a82` | 保持；无需同步 |
| `assets/showcase-origin-market-snapshot.png` | `ff82a946e3` | 保持；无需同步 |
| `assets/showcase-origin-mdt-kidney-cancer.jpg` | `cbf6bc7f42` | 保持；无需同步 |
| `assets/showcase-origin-status-report.png` | `50590ce3e9` | 保持；无需同步 |
| `assets/skill_duo_intro.pdf` | `9aad9fad09` | 保持；无需同步 |
| `docs/.nojekyll` | `8b13789179` | 保持；无需同步 |
| `docs/_navbar.md` | `4f664240d9` | 保持；无需同步 |
| `docs/_sidebar.md` | `6fe3373882` | 保持；无需同步 |
| `docs/design.md` | `c418390dfe` | 保持；无需同步 |
| `docs/en/_navbar.md` | `67cbfc9354` | 保持；无需同步 |
| `docs/en/_sidebar.md` | `d5361eb9b7` | 保持；无需同步 |
| `docs/en/design.md` | `61097d0869` | 保持；无需同步 |
| `docs/en/prompts.md` | `1189e4251f` | 保持；无需同步 |
| `docs/en/quickstart.md` | `9f498710aa` | 保持；无需同步 |
| `docs/index.html` | `112cb592a7` | 保持；无需同步 |
| `docs/ko/_navbar.md` | `7ebd396497` | 保持；无需同步 |
| `docs/ko/_sidebar.md` | `793ff861da` | 保持；无需同步 |
| `docs/ko/design.md` | `2eb0365f21` | 保持；无需同步 |
| `docs/ko/prompts.md` | `9a0dbb61fb` | 保持；无需同步 |
| `docs/ko/quickstart.md` | `170d414519` | 保持；无需同步 |
| `docs/prompts.md` | `89e02d6e11` | 保持；无需同步 |
| `docs/quickstart.md` | `f63ea2600f` | 保持；无需同步 |
| `skills/image-to-editable-ppt/agents/openai.yaml` | `2b14bcd1bc` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/cli.py` | `8e2018180c` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/__init__.py` | `134b39f08e` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/_input_normalization.py` | `fec6411303` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/deck_run_state.py` | `98a5406f11` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/deck_text_hints.py` | `5c1b41d3b8` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/formula_renderer.py` | `f38babf5b9` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/make_page_contact_sheet.py` | `c666dc7392` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/paddle_text_hints.py` | `db2eb2d0ae` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/page_job_status.py` | `6c10586fcc` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/page_text_metrics.py` | `6013392969` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/record_page_dispatch.py` | `4ef55f9549` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/remove_chroma_key.py` | `4f7d078029` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/editppt/runtime/text_hints.py` | `8f7cd5568c` | 保持；无需同步 |
| `skills/image-to-editable-ppt/cli/pyproject.toml` | `b6f3a2671a` | 保持；无需同步 |
| `skills/image-to-editable-ppt/scripts/build-page-worker-prompt.py` | `365b5f79b9` | 保持；无需同步 |
| `tests/test_dispatch_concurrency.py` | `90d6253811` | 保持；无需同步 |
| `tests/test_formula_renderer.py` | `a93a396c64` | 保持；无需同步 |
| `tests/test_page_hints.py` | `0a43205cd4` | 保持；无需同步 |
| `tests/test_script_inventory.py` | `56a18989f0` | 保持；无需同步 |

## 测试与验证

- 基线 95 项测试：最初环境缺少已声明依赖 `requests`/`openai`，出现 4 failures + 1 error；在独立 venv 安装仓库声明的 editable CLI 依赖后，95/95 通过。没有修改测试以掩盖依赖问题。
- 修改后完整测试：`python -m unittest discover -s tests`，103/103 通过（含 8 项新增测试和 1 项强化的原测试）。既有 portable backend、visual QA、source extraction 回归全部保留。
- Skill Creator `quick_validate.py skills/image-to-editable-ppt` 通过；agent metadata 仍对应相同技能用途。
- CLI `doctor --json` 返回 `ok: true`，六个声明的依赖可导入；只做本地健康检查，未探测服务可用性。
- Python compileall、`git diff --check` 通过；整个 CLI 子树对 PR #3 的 diff 为空。
- 独立只读技能使用检查覆盖 local-only/配置 OCR、多页慢 worker、保留 fork 的更新三个场景，正确识别限制；该检查不是完整模型转换验收。
- 新增测试检查：授权数据范围与用户例外、受限网络审批/常规自治、三语言安装源与 CLI 刷新、模型说明/默认值分离、worker 保留 portable/QA、慢 worker 租约及 reset 参数、run hints 不改编排/后端/源图、伪造视觉通过标志被拒。
- 未执行：真实 PaddleOCR 上传、真实图片生成/编辑、live 多 worker 转换、新模型服务兼容、真实 PowerPoint 打开、对用户现有安装运行 npx 更新。不声称这些已验证。

所有测试图片/临时产物和日志留在临时工作区，未纳入提交。差异报告与新增测试位于 monorepo 文档/测试目录，未改变上游安装包目录布局；没有自动安装或替换用户现有技能。

## 复核入口

- [上游固定快照](https://github.com/ningzimu/image-to-editable-ppt-skill/tree/b7be494e31a0ed56ef98716891db5474606b8cdf)
- [PR #3 固定快照](https://github.com/chrisopal/skills/tree/39be6e8c5641c7a5deb5d585992655bdbca831b3/image-to-editable-ppt)
- [当前 main 固定快照](https://github.com/chrisopal/skills/tree/f95bc08516c44c9fa79597b39d1d981f30ec7f5e/image-to-editable-ppt)
- [skills CLI 的官方源格式说明](https://github.com/vercel-labs/skills#source-formats)：支持完整 GitHub tree 子目录 URL 与本地路径；这里刻意使用提交 SHA，避免分支名和路径的歧义。

重新生成基线比较时使用上述提交的 `git ls-tree -r`，对 fork 路径去掉 `image-to-editable-ppt/` 前缀，再按路径、mode、blob 比较即可得到 109 行清单。本次新增 `tests/test_entry_contract.py`、本报告和 `STATUS.md` 记录不属于这份“修改前基线”清单。
