# Huixin · 独立颜色主题层

仅在Huixin采用或换色任务中读取。配合[框架](huixin-framework.md)、[组件](huixin-components.md)和[运行时契约](design-system-contract.md)使用。三层共享一个 `assets/tokens.json`；不复制来源包的theme.tokens.json、独立导出脚本或`data-hx-theme`运行时。

## 颜色职责与解析

| 所在位置 | 职责 | 不拥有 |
|---|---|---|
| `profiles.huixin.common` | 字体/尺寸/材质几何及语义配方引用 | 颜色字面量 |
| `profiles.huixin.modes.light/dark` | 画布、表面、文字、边界、状态、图表等颜色/alpha | 字号、行高、间距、圆角、blur、shadow偏移、gradient角度 |
| `brands.huixin/indigo/violet` | 现有品牌轴上的动作/导航/选中/焦点配色 | 组件几何、状态机与第二套主题API |

解析继续采用Foundation → Theme → 支持的Profile → 显式Brand → Density，再解别名/组件/布局配方。Enterprise/blue/light/standard仍是默认；原blue/teal组合保持兼容。Huixin Profile与huixin品牌是不同维度：一次初始采用可同时指定两者，之后换品牌不重新选Profile或密度。

```js
EnterpriseDesign.apply({ profile: 'huixin', brand: 'violet', theme: 'dark', density: 'standard' });
// 已采用后的颜色切换只传这两个维度；省略的活动配置保持不变。
EnterpriseDesign.apply({ brand: 'huixin', theme: 'light' });
```

已有 `data-ui-profile`、`data-ui-brand`、`data-theme`、`data-density`由同一个适配器更新。不同Profile可采用同一品牌；不要把Huixin颜色扩展当作替换全站默认的授权。公共focus-ring兼容值固定2px/solid；新品牌使用引用固定几何的配方，不得以换色扩大焦点环。新增颜色只能经Token验证/生成进入配置，不把任意hex直接写到页面或运行时。

## 语义角色与材质

使用canvas、surface、glass-surface、surface-muted/hover、text/secondary/tertiary、border/control、action-text、action-solid/on-action、selected-bg和focus-ring等现有语义角色。标题、侧栏、导航选中、表头与浮层完整映射，不能只给按钮换色。品牌识别色不等于可读的小字颜色，浅色动作背景必须有经过验证的文字配对。

success/warning/danger/info及其浅底是业务状态；data-series-*是数据分类。品牌切换不能把成功、危险或所有系列刷成主色；减少不一定危险，零值也不等于失败。同一系列保持稳定含义，必要时加符号/线型。预警类型的玻璃底与普通状态浅底为不同组件语义。

颜色层提供渐变端点、阴影色/alpha与玻璃表面alpha；固定层配方提供角度、偏移、模糊范围、轮廓。light/dark共享材质几何，禁止把来源浅/深不同阴影尺寸原样塞入mode。复杂背景按实际合成表面判断对比；冻结列继续使用实体surface。文档/PDF白纸和真实照片不受主题滤镜改色。

## 一致切换与边界

换色只更新变量/现有Provider配置，不替换业务DOM、不reload路由，不清空输入、焦点、草稿、筛选、选择或业务存储。使用既有同步bootstrap避免首屏闪错主题；不新增Huixin独立存储键。body浮层从根继承；局部深色Provider的跨层浮层必须transfer该Provider的有效值，不能只复制属性。Shadow/iframe按宿主契约单独集成，不声称天然支持。

SVG消费语义变量，Canvas通过现有 `EnterpriseDesign.bridge` 重绘图形、坐标、tooltip与选中。原生fixture支持该路径不等于Element Plus/Ant Design等已实际集成；按宿主当前版本提供的API映射并记录运行证据。

## 换色验收

1. 生成与单测：运行 `python3 scripts/generate_tokens.py`、`python3 scripts/generate_tokens.py --check`、`python3 -m unittest discover -s tests -v`。确认modes无几何覆盖、common无字面颜色、引用可解析、frozen v1与默认blue/teal兼容。脚本结果只覆盖其断言。
2. 对比度：按light/dark及各品牌测量正文/辅助文字、action default/hover、渐变起止两端、状态字/状态底、错误、选中、focus和控件边界，在canvas/surface/glass及浮层的实际背景上检查。普通文本4.5:1、关键非文本边界/状态3:1；半透明色先合成，不能只测渐变起色或默认主按钮。
3. 同一数据/视口/密度换色，比较sidebar232、header70、page28、card24、body14、title28、control40/32、table56/44、donut200等有效计算值及材质几何。品牌/theme控制只传颜色维度，逐项验证DOM/输入/焦点/查询/选择/草稿保留。
4. 实走390px菜单、表格局部横滚、Tabs键盘与弹窗Esc/焦点恢复，检查body及嵌套浮层和Canvas。覆盖当前任务声明的状态，未测保持Not tested。

[Huixin模拟参考](../assets/reference-huixin/index.html)可复用为本轮本地测试入口；来源包的截图、外部演示及12种桌面组合是历史参考，不继承其“已通过”结论。不把对比度单测、CSS不变或模拟保存当作视觉/无障碍/宿主业务E2E整体通过。
