# Enterprise UI 表单与 SaaS 信息流增强验证

日期：2026-10-28。隔离分支：`codex/enterprise-form-design-20261028`。从已 fetch 的 `origin/main` `c74460d8eae06f978f9233c4fdc40a7d22b66aea` 开始，提交前再 fetch 确认未移动。

## 交付与设计

- Skill 入口、forms-and-feedback、checklist 增补任务构图、标签轨道、字段/组/动作间距责任、编辑/只读分离、错误定位和恢复要求（FORM-06～11）。新增 saas-experience-patterns，把官方实践与本 Skill 适配分开，提供 SAAS-01～06。
- `assets/reference-forms/{index.html,forms.css,forms.js}` 提供五种可操作构图：分组签收、横排设置、依赖分步申请、主从明细、窄抽屉；第六个任务收件箱提供筛选/搜索、对象摘要、依据及时间、历史展开和办理入口。使用既有语义 Token，支持品牌、Profile、明暗、密度；版本仍是兼容 v1.3，未改变公开 Token。
- 按用户截图暴露的问题拆开对象、当前录入与历史；未复制截图里的业务状态，也未修改 LIMS。删除重复身份装饰及未使用样式，不新增依赖、业务 API 或通用表单引擎。
- 来源：Carbon/Fluent 表单指南、Linear 2026-03-12 design refresh 与 display options、GOV.UK check answers、Polaris React 表格用途（明确为旧 React 文档）；链接与来源边界见场景指南。

## 实际验证

| 检查 | 结果 |
|---|---|
| 源码及安装目录 Python unittest discover | 各 55 项通过 |
| 两处 Skill Creator quick_validate | 通过 |
| 两处 generate_tokens.py --check | 通过；生成内容/公共 Token 未改变 |
| Python/JSON/JS 静态解析 | 7 Python、7 JSON、9 JavaScript 通过 |
| 源码 Markdown 本地文件目标 | 153 条通过 |
| HTML ID/label/aria-describedby | 112 ID 唯一，引用目标存在 |
| 参考源码样式候选扫描 | Pass，0 个字面色/直接色板候选；不是视觉或对比度认证 |
| `tests/forms-browser-check.js` 真实 Chromium | 158 断言通过，0 pageerror |
| 布局矩阵与截图 | 6 构图 × 1440/390px × 浅/深色 = 24；无整页溢出、缺失字段名、非局部滚动字段裁切；人工查看代表截图 |
| Git diff whitespace | 通过 |

浏览器覆盖：首次不报未触碰错误、空数值与零值区分、字段错误和摘要定位、数量差异条件、保存刷新回读、模拟 quota 失败不误报；设置保存/恢复和 false 保留；步骤阻断、返回与核对；明细增删/全删恢复、空单价与零单价、汇总；抽屉 Esc/焦点返回、取消放弃/确认放弃及背景摘要回读；手机导航关闭 inert/隐藏与焦点恢复；任务筛选、选择对应摘要、无匹配时不残留详情、真实示例入口。表单页的打印动作未自动启动系统打印对话框。

发现并修复：装饰开关阻挡原生控件点击、移动侧栏切换遮挡、固定初始数量提示、hidden 被 display 覆盖、设置自动保存使恢复无效、抽屉保存背景仍旧、明细行数重复来源。最终模型启发式视觉评审为 93/pass；不是与问题反例的像素相似度或真人可用性结论。

## 本机同步与保护

- 安装目标 `/Users/guojiexie/.codex/skills/enterprise-ui-design`。同步前全量备份，比较 SHA256；四份既有本地增强文件以 origin 基线三方合入。checklist 的末尾追加冲突逐项核对后同时保留 DETAIL 与 SaaS 清单。
- 保留本机独有 `references/detail-layout-system.md`，未把本机未提交增强混入本轮 Git 提交。63 个预期文件逐一 SHA256 回读一致；安装目录 156 条 Markdown 本地文件目标存在，测试/元数据/生成检查通过。
- 原工作区 `/Users/guojiexie/Development/skills` 的 tracked binary diff SHA256 与 status 与开始时完全一致。本轮只在隔离 worktree 修改。
- 可复用源码、测试和记录已以 `4ec92d51` 推送功能分支。后续按用户明确要求进行 main 快进整合；合并前再次 fetch，远端基线仍为 `c74460d8`，55 项回归、Token 生成和 diff 检查再次通过。采用非强制推送并回读远端 SHA，运行收据记录实际发布结果。生成截图、日志及收据不提交。

## 证据与未测范围

本机证据：`/Users/guojiexie/Development/skills/projects/enterprise-form-design-20261028/` 中的 browser-results.json、24 张矩阵截图、preview-sample.png、preview-inbox.png、static-checks.json、source-tests-final.log、installed-tests.log、installed-receipt.json 和 receipt.json。临时预览：`http://127.0.0.1:8878/assets/reference-forms/`，需本机服务运行。

模拟数据与浏览器 localStorage 只证明参考交互；未验证宿主真实持久化、跨角色/跨端、服务端提交未知恢复、其他浏览器、完整可访问性、AI 能力或真人任务效率。原应用上线、正式验收与客户接受不在本轮结论中。
