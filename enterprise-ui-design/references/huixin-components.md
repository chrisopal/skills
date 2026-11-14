# Huixin · 组件与交互固定层

显式Huixin Profile使用本层配合[框架](huixin-framework.md)与[主题](huixin-themes.md)。先按[业务组件目录](business-component-patterns.md)选择模式，保留宿主组件库、事件、校验与状态机。本层定义视觉映射，不重新实现审批、查询、上传或权限。

## 尺寸与结构

| 对象 | 标准基线 | 状态与限制 |
|---|---|---|
| Button / Input / Select / Date | 高40px、圆角8px、横12px | 紧凑控件32px；同一查询行同高 |
| 图标操作 | 命中区36px，图标18px | 有可访问名称；窄屏保证可操作 |
| Checkbox / Radio | 图形16px、label间8px | 真实label；含indeterminate/disabled |
| Tabs / Segmented | 项高至少40px、横16px | 一种选中表达，不追加第二条色条 |
| Panel | 圆角16px、inset24px、1px边 | 嵌套层避免重复边框/投影 |
| Table | 正文14px、表头13px | 最小行高56px/compact44px，多行可增高 |
| Query / Pagination | 横安全边距28px | 查询wrapper/input以256px为基准、最大320px（最小200px）；select160px；查询控件不flex-grow；操作右对齐、gap12px；表格内横滚 |
| Status tag | 最小24px、字12px、圆角6px | 文字/图形+颜色，不仅靠色 |
| Dialog | 圆角18px；header 20×24px、body24px、footer16×24px | 仅body滚动；字段组gap20px、label gap8px；标题/正文/操作分区 |
| Popover / Tooltip | 圆角8px、1px边 | hover/focus可获得必要信息 |
| Drawer / Detail | 独立表面；与列表gap20px为本Profile基线 | 对象与选中行一致；关闭入口可达；按宿主空间责任映射，不作为所有主从布局的固定间距 |
| Chart | 趋势区260px预算、环图200px | 真实系列/单位/缺失值，含数据替代入口 |

表格规范键为 `table-row-height`：56px取代来源`row-height:52px`；紧凑44px。普通行的上下padding预算上限为12px，紧凑行收至4px；行内操作32px，不与40px查询/弹窗操作混用。多行对象按内容自然增高，不能用固定min-height额外预留空白。环图规范键为 `chart-donut-size:200px`，来源128px别名不再提供。不要为了锁死截图而固定所有数据行高度。compact只更改已声明密度值，正文不变，手机不自动compact。

## v1.6 实现一致性规则（HX-P01–HX-P12）

| ID | 走查要求 |
|---|---|
| HX-P01 | 仅查询输入设256px基准、200px可读下限、320px上限；wrapper与控件都禁止flex-grow，弹窗字段仍按自身布局填满。 |
| HX-P02 | 行高由内容+padding预算决定：普通12px、紧凑4px；多行自然增高，不叠加40px控件和大padding。 |
| HX-P03 | 读取最终computed `border`/`box-shadow`及胜出样式来源；Element Plus内阴影描边也必须消费控件边色。 |
| HX-P04 | 查询行的可见输入、select和按钮外框均为40px；32px仅限行操作等独立紧凑密度。 |
| HX-P05 | 盘点完整权限菜单和弹窗图标；业务图形使用单色实心SVG/currentColor，控制符号可统一细线。 |
| HX-P06 | 共享组件/Provider必须实际消费新Token，变量声明或构建通过不算接入完成。 |
| HX-P07 | 行操作组gap12px、整体右对齐，末列保留28px安全内距；sticky列不得覆盖内边距。 |
| HX-P08 | Dialog按header20×24、body24、footer16×24和字段20/label8走查；只允许body滚动，日期/下拉/tooltip同步主题。 |
| HX-P09 | 区分表面留白与行高/重复padding；不以全局归零padding修复空白。 |
| HX-P10 | 仅迁移视觉结构，不复制来源系统的业务筛选、字段、入口或状态规则。 |
| HX-P11 | 单独记录browser zoom、presentationScale和devicePixelRatio；computed样式与物理截图不能互相替代。 |
| HX-P12 | 资产校验、组件fixture浏览器测试、宿主UI走查和业务E2E分别报告；一个通过不推定其它通过。 |

走查记录至少包含：route、role、theme、profile、viewport、browserZoom、presentationScale、devicePixelRatio、token、computedValue、renderedBox、winningStyleSource和actualEvidence。资产/fixture只能证明声明范围，不能证明宿主合规。

## 限定材质例外

Huixin明确选择才允许克制的卡片玻璃表面、浅阴影、画布/导航/主按钮渐变。这是对通用无玻璃/无日常渐变规则的局部Profile覆盖。不得外推到Enterprise/Precision/Analytics，不加入卡片上浮、呼吸光晕、夸张3D图表或重复透明层。

图表的浅渐变填充、端点或轨道装饰是显式 Huixin 下按任务选择的局部配方，不要求每张图采用，不新增全局默认。保留真实零线、缺口、比例、状态及文字；非 Huixin 回退使用宿主的平面数据表达。图表从最近有效 Provider/容器取得 Profile、主题与系列 Token，局部主题变化同步更新 SVG/Canvas；不可只监听全局根节点导致嵌套主题串色。

`profiles.huixin.common`保存模糊半径、阴影偏移/范围与渐变角度等配方几何，以语义角色引用颜色；`modes`/brand只提供颜色与alpha。浅深色不得使用不同偏移/模糊来冒充纯换色。冻结列使用不透明surface，避免下层文字透出；复杂背景下提高玻璃表面不透明度。遮罩保持中性，不染暖棕。渐变两端和合成后的实际背景都需要对比度验证。

主按钮突出真实主任务，次按钮保持边界，文字操作有持续可见的动作色与焦点，危险动作维持独立语义。状态标签可用语义浅底；预警类型标签可用玻璃底+语义文字，两者不能混为同一类。loading保留布局并阻止重复提交，disabled有清楚状态，pressed不改变几何。

## 交互和宿主映射

- Tabs采用tablist/tab/tabpanel语义，按宿主策略支持箭头、Home/End；页面路由导航使用aria-current。切换保留草稿、当前查询与原深链接，不把分段视图强改路由。
- 标签和错误关联真实控件；只读可复制，禁用遵守真实规则。日期用宿主日期控件，不用纯文本外壳伪装。上传逐项展示真实结果；未知提交结果先确认，不能重试伪造成功。
- 原生日期、下拉等浏览器控件的 `color-scheme` 跟随有效浅深主题；核对日历图标和弹出选择器，避免深色表面残留黑色原生图标。保持业务类型与组件尺寸不变。
- 原生dialog或宿主组件负责焦点进入/约束/恢复、Esc与关闭保护；样式表不提供这些能力。关闭、取消、返回保持原业务语义。
- Element Plus、Ant Design等通过宿主已有Provider/CSS变量与组件配置映射40px控件、8/16/18圆角和状态角色；不新增依赖，不全局覆盖button/svg/div/canvas。未实际接入与走查时只能报告映射方案。
- body浮层继承根有效变量；局部Provider浮层使用既有 `EnterpriseDesign.transfer` 携带有效值。禁止新增`data-hx-theme`状态源。Canvas经既有bridge在换色后重绘，CSS变量改变本身不是重绘证据。
- 图表使用稳定数据系列角色，与success/warning/danger/info分离；缺失不补零，未知不造趋势，不改业务计算。主题不污染PDF白纸、签章或富文本内容。

## 可复用资产与验收

`assets/huixin-components.css`与`assets/huixin-framework.css`是作用域样式，消费唯一Token源的生成值，不是生产组件库。`assets/huixin-icons.svg`与供应包v2 `icons.svg`字节一致，提供完整35个24×24单色实心/currentColor符号：`hx-history`、`hx-runs`、`hx-sliders`、`hx-refresh`、`hx-edit`、`hx-check`、`hx-home`、`hx-chart`、`hx-equipment`、`hx-materials`、`hx-laboratories`、`hx-members`、`hx-roles`、`hx-qualification`、`hx-plugins`、`hx-extensions`、`hx-samples`、`hx-file`、`hx-standards`、`hx-scenarios`、`hx-methods`、`hx-calculator`、`hx-filter`、`hx-workflow`、`hx-audit`、`hx-items`、`hx-regulationAssistant`、`hx-form`、`hx-settings`、`hx-commissions`、`hx-templates`、`hx-reports`、`hx-customerTemplates`、`hx-reportSettings`、`hx-move`。复用前核对完整导航语义；装饰图标aria-hidden，独立按钮有名称，不用emoji替代。

```html
<svg class="hx-icon" aria-hidden="true"><use href="../huixin-icons.svg#hx-file"></use></svg>
```

通过同源静态服务使用sprite；不要依赖file://外链行为。[概览](../assets/reference-huixin/index.html#overview)、[资源](../assets/reference-huixin/index.html#resources)与[样品签收](../assets/reference-huixin/index.html#receipt)是模拟交互组合，不携带宿主业务实现。验收须记录真实运行视口、profile/brand/theme/density、具体状态与截图/操作证据；覆盖默认、hover、active、focus、disabled、loading、错误/空态和390px。源码/单测不能替代键盘、焦点、移动导航与真实保存路径实测。
