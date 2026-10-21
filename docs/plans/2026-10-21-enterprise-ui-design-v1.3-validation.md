# Enterprise UI Design v1.3 本地验证与交付记录

2026-10-21；基线 `165d6d01ea1daf9cb021ffbc0f57a71516be3eb9`，分支 `codex/enterprise-dtx-skill-suite-runtime`。本轮只更新 Skill 源码；未安装覆盖个人 Skill；按仓库规范创建本地提交，不推送、合并或部署，未修改 LIMS。无新增依赖、框架或组件库。生成的验证截图/日志留在 `projects/enterprise-ui-v13-20261021/`，不作为可复用源码发布。

## 实际交付与复用

- 复用 v1.2 的 Create/Upgrade/Audit、Blueprint、空间责任、业务组件/流程/文案指南、工单数据/筛选/分页/本地编辑、订单阶段样板和 Token 生成器。冻结的 `tests/fixtures/v1-token-contract.json` 无改动，旧 Foundation/明暗值保留。
- `assets/tokens.json` 是唯一值来源：新增独立品牌 blue/teal、Precision Profile、12 个完整字体角色、语义/组件/布局映射。生成 `tokens.css`、`design-config.json` 和同步引导 JS。Enterprise/Precision 支持明暗；Analytics 保持深色及浅色回退 Enterprise。
- `scripts/resolve_tokens.py` 校验配置所有权、别名、缺失引用和循环，解析完整有效配置；`assets/design-system.js` 是共享入口。删除订单样板中重复的配置监听，页面不另存一套主题状态。
- 扩展原工作台为概览、列表、详情、配置、分析、组件/状态，与原多阶段订单页及编辑浮层组成 8 个登记 surface、33 个状态。全部是明确标识的本机模拟数据；保存仅指当前浏览器 localStorage。
- 新增 opt-in `layout-recipes.css`、全站规划、配置/迁移契约、SYS-01～08 规则、JSON 审查模板、候选扫描及覆盖检查器。扫描是文本候选定位，不是 AST、路由发现或视觉验收。

关键入口：[Skill](../../enterprise-ui-design/SKILL.md)、[配置契约](../../enterprise-ui-design/references/design-system-contract.md)、[全站规划](../../enterprise-ui-design/references/site-planning.md)、[范围账](../../enterprise-ui-design/assets/reference-workbench/surfaces.json)、[字体清单](../../enterprise-ui-design/references/typography.md)、[外部方法阅读与取舍](../../enterprise-ui-design/references/external-skill-references.md)。

## 三类结论

| 类别 | 本轮结论 | 直接证据与边界 |
|---|---|---|
| 技术审计 | Pass，限本地参考范围 | 32 项单元测试；冻结值、全组合对比度/所有权/引用、生成一致性、JS/Python 语法、Skill Creator、111 个本地文档链接、空候选扫描、真实计算样式和无运行异常。不是完整 WCAG/屏幕阅读器/跨浏览器认证。 |
| 视觉与任务 | Pass，模型启发式复查 | 比较相同蓝色下 Enterprise/Precision；检查窄屏概览、列表、详情、表单、分析、组件、办理与低高弹窗。标题、可读字段、数字/单位、所属 inset、错误分组、动作层级可辨；不按像素相似度或留白率打分。不是实际用户研究。 |
| 行为回归 | Pass，限模拟本地行为 | 578 条浏览器断言；筛选/分页/选中、草稿和焦点保持、表单校验、存储失败保留草稿、本地保存回读、恢复已保存、键盘 Tabs/Tooltip/Drawer、六种办理状态与实际弹窗。不是后端保存、授权或客户业务 E2E。 |

实际覆盖 JSON：`projects/enterprise-ui-v13-20261021/coverage-report.json`；检查输出 `coverage-check.json`。每条状态记录请求/有效配置、视口及观察证据；没有用缺失状态填 Pass。检查器拒绝重复和未知状态，失败记录不能被后一条 Pass 覆盖。覆盖器验证账与证据字段，不认证证据内容真实性。

## 浏览器矩阵与配置证明

Chromium 156.0.8078.47 / macOS；本地 HTTP `127.0.0.1:8767`。浏览器结果 `browser-results.json` 包含 94 条矩阵记录、33 条状态记录、578 次断言和零 pageerror。

- 核心组件：2 品牌 × 3 Profile × 2 明暗 × 2 密度 = 24 个请求，含 4 个 Analytics/light 回退请求；有效唯一组合 20 个。另比对 CSS-only 与运行时的品牌、表面、字体、圆角、密度等 13 项消费值。全部组件组合验证主要动作/hover/focus、选中行、SVG、错误、原生复选框和 body dialog。
- 默认 blue/Enterprise/light/standard：六个工作台页面和订单办理页面均检查 390、768、1440、1920px。表格允许自己的横向滚动；整页无横向溢出。
- 六个工作台页面另执行 7 组风险请求：teal/Precision/dark/compact，blue/Precision/light/compact，teal/Enterprise/dark/standard，blue/Analytics/dark/compact，teal/Analytics/light/standard，blue/Enterprise/light/compact，teal/Precision/dark/standard。compact 用 390px，standard 用 768px；连同默认配置，覆盖请求维度全部 30 种两两取值。**这不代表全部页面 × 状态 × 24 配置 × 4 视口的笛卡尔全覆盖。**
- 品牌单独 blue→teal：标题宽高/字号/字重不变；同一未提交配置、筛选 `WO-2026`、第 2 页、选中记录、焦点和滚动保持。
- 同一 teal 品牌 Enterprise→Precision：canvas `#F5F7FA`→`#F1F5F9`，panel radius 6→10px，section gap 24→28px，标题请求字重 600→700；品牌、草稿、业务结构不变。这个变化发生在 Profile 轴，不依靠改主题或业务页面代码。
- Canvas：切换后重绘；实际像素与有效 data-series-1 一致；有同值 4 行数据表。分类序列保留自己的蓝色，不随 teal 品牌替换。
- 200% 为原生浏览器缩放：在独立临时 profile 内，通过 [Chrome Tabs API](https://developer.chrome.com/docs/extensions/reference/api/tabs#method-setZoom) 设置并读回 factor=2；自动化窗口设为 1440×960，缩放后 CSS innerWidth=720、DPR=2、visualViewport.scale=1。7 个页面均无整页溢出，编辑弹窗提交按钮可达；未改用户浏览器配置。辅助源/结果为本地 `zoom-check.js`、`zoom-extension/`、`zoom-results.json`。
- 同步偏好引导：teal/Precision/dark/compact 在 performance 约 5.4ms 应用，首次绘制/FCP 为 16ms。此为本机一次测量，不是所有网络/SSR 环境的无闪变保证。畸形 JSON、primitive、array 均安全回退。

## 字体与资源实测

| 项目 | 实际证据 | 缺口/使用条件 |
|---|---|---|
| 中文正文 | CDP Rendered Fonts：PingFangSC-Regular | 系统字体，未复制二进制；其它平台待各宿主验证。 |
| 混合 Latin/数字/单位 | `.SFNS-Regular` + PingFang SC；样本含 μm、℃、±、≤、≥、m² | 不是仅根据 CSS family/`document.fonts.check` 推断。数字精度来自内容，不由字体属性改变。 |
| 中文标题 | Enterprise 请求600、Precision 请求700；两者实际报告 PingFangSC-Semibold | 已明确记录系统映射；没有已验证独立700字体文件，不声称两个平台字重完全相同或无合成。 |
| 代码/长 ID | Menlo-Regular | 只用于标识符/代码；未下载 JetBrains Mono。 |
| Inter / 自托管字体 | 未加载 Inter；无新增 @font-face、CDN、预加载或字体文件 | 若需跨平台固定字体，需项目提供授权、版本/哈希/完整字重、中文覆盖和文件；下载/缓存/加载位移仍须实测。 |
| 图形资源 | 现有本地原生字符图标、原作 SVG/Canvas；无外部媒体请求 | 不承诺系统字符图标跨平台像素一致；未复制截图中的广告、紫色品牌或图片。UI 与报告/打印字体分离。 |

网络 Resource Timing 仅含本站 8 个 JS/CSS 资源，没有字体下载。资源/字体原始记录：`capture-results.json`、`final-capture-results.json`。所有默认字体角色 tracking=0；拉丁光学校正只能作为有范围的宿主例外。

## 视觉复查与已关闭问题

| 实际发现 | 修复 | 复查证据 |
|---|---|---|
| Precision 选择器压过 compact 间距 | 生成器提高 density 覆盖 specificity，保留显式 light 语义 | CSS-only 全组合、specificity 回归 |
| 隐藏列表标题仍显示、数字行继承正文行高 | `[hidden]` 布局修复；metric 使用角色行高 | 概览截图、单一可见 h1 断言 |
| teal 配置页 checkbox / 返回办理链接仍蓝色 | 原生 accent、返回链接消费 action 语义 | 全组合 accent、窄屏表单/办理截图 |
| 错误与输入被 section gap 分离，未标红边框 | field 统一拥有 label/input/error；aria-invalid 消费状态色 | 组件截图、字段校验与恢复断言 |
| 重复覆盖记录可吞失败；偏好 primitive 中断 bootstrap | 拒绝重复/未知记录；偏好对象验证 | 负向单元测试与浏览器初始化测试 |
| `@`/mapping 别名冻结或循环未被拦截 | live CSS alias、atomic `$ref`、嵌套循环检测 | 缺失/循环/有效引用回归 |

可用截图：`before-v12.png` 与 `after-v13-list-1280.png` 是同类默认列表前后图；`enterprise-blue-overview.png` 与 `precision-blue-overview.png` 是相同品牌/主题/数据下的 Profile 对比。其余 `precision-teal-390-{overview,work-orders,record,configuration,analysis,components}.png`、`precision-workflow-390.png` / `-task.png` / `-1440.png`、`low-height-dialog.png`、`state-{empty,loading,error,denied,signed-out}.png`、`native-zoom-200.png` 支持范围内复查。首轮 fullPage 办理截图出现拼接重复、缩放 fullPage 截图出现裁切，均已弃用并以实际 viewport 截图替换；不把错误截图当通过证据。

## 可复现命令

从仓库根目录执行：

```sh
python3 enterprise-ui-design/scripts/generate_tokens.py
python3 enterprise-ui-design/scripts/generate_tokens.py --check
python3 -m unittest discover -s enterprise-ui-design/tests -v
python3 enterprise-ui-design/scripts/audit_ui.py scan enterprise-ui-design/assets/reference-workbench enterprise-ui-design/assets/reference-order-flow enterprise-ui-design/assets/layout-recipes.css
python3 enterprise-ui-design/scripts/audit_ui.py coverage --manifest enterprise-ui-design/assets/reference-workbench/surfaces.json --report projects/enterprise-ui-v13-20261021/coverage-report.json
python3 -m http.server 8767 --bind 127.0.0.1 --directory enterprise-ui-design
```

另一个终端，在已有 Playwright CLI 环境运行（不新增项目依赖）：

```sh
~/.codex/skills/playwright/scripts/playwright_cli.sh -s=enterprise-v13 open http://127.0.0.1:8767/assets/reference-workbench/
~/.codex/skills/playwright/scripts/playwright_cli.sh -s=enterprise-v13 run-code --filename enterprise-ui-design/tests/browser-check.js
```

此浏览器测试只清空其**专用隔离会话中的模拟数据存储**，不要指向真实业务站点。Skill Creator 用本机已有 PyYAML 的 `python3.13` 执行 `quick_validate.py`；没有给仓库加依赖。无应用构建/typecheck 管线；原生 JS 语法检查、Python 编译和单元测试是对应检查，不能伪写应用 build 成功。

## 未验证项与回退

没有宿主项目权限缺口阻碍本 Skill 验证；宿主迁移本来不在授权范围。真实组件库 Provider、iframe/Shadow/microfrontend/SSR、多窗口同步、跨操作系统/浏览器字体与布局、屏幕阅读器、报告/打印、自托管字体加载、真实授权/后端/客户 UAT 均未验证。参考实现没有这些架构时不能以空测试代替集成证据。外部 Skills 只固定提交阅读方法，未安装运行或认证安全；draw-ui 独立 LICENSE 文本未确认，未再分发其代码/素材。

视觉回退可选择 blue/Enterprise/light/standard；宿主迁移回退应恢复之前的 provider/资源及偏好映射，并保留业务存储。源级回退只撤本轮 Skill 变更或恢复基线对应文件；不得重置整个工作区或清理无关 WIP。回退 Token 不会撤销已保存的业务修改。
