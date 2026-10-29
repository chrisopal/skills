# Huixin 三层合并与本地验收

日期：2026-10-29。基线：`f84245a07eeb914049fe0c5bdee2f967e844fe87`。用户授权：合并三层方案、修正对比度/重复 Token、提供换主题示例、验证后同步本机并合入 main 推送。

## 结果与变更

Enterprise UI Design 升级至1.4.0。`assets/tokens.json`仍为唯一维护源；新增显式Huixin Profile及慧新青/靛蓝/紫色品牌，保持原有四轴配置和Enterprise默认值。框架尺寸/材质配方、组件规则和颜色职责分开；没有第二套主题API或运行时依赖。

- `profiles.huixin.common`固定14px正文、28px标题、232px侧栏、70px顶栏、28px页面边距、24px卡片内距、40px标准/32px紧凑控件。模式层只含颜色/透明度，品牌只控制动作、导航与选中色。
- 统一表格`table-row-height=56px`、compact44px，环图`chart-donut-size=200px`，拒绝来源包的竞争别名；JSON重复键直接报错。保留v1冻结契约和blue/teal兼容性。
- 修正辅助文字、控件边界、状态字、7个系列及主按钮渐变两端的对比度；新增品牌焦点环引用固定几何。修正旧`.dark`紧凑选择器优先级、实际表格密度消费、手机菜单显隐、深色原生日期图标及选填标签对齐。
- 新增`huixin-framework.css`、`huixin-components.css`和35个SVG符号；三份聚焦参考接入Skill入口、风格、检查表及运行时契约。不迁入旧版样式、重复导出器或来源业务。
- `assets/reference-huixin/`包含工作概览、检测与资源、样品签收三个可操作页面。共享DOM和框架，可一键切换三种配色及浅深色。表单有条件校验、本机草稿、替换保护、确认弹窗、模拟失败与重试。

## 已执行验证

| 层次 | 命令/证据 | 实际结果 |
| --- | --- | --- |
| 源码回归 | `python3 -m unittest discover -s enterprise-ui-design/tests` | 63通过，含8项三层行为约束 |
| 验收工具回归 | `python3 -m unittest discover -s ui-regression-acceptance/tests` | 25通过 |
| Token生成/对比度 | `python3 enterprise-ui-design/scripts/generate_tokens.py --check` | 80组合一致；原24组合保留 |
| Skill元数据 | 系统Python执行skill-creator的`quick_validate.py enterprise-ui-design` | 通过 |
| 新页面真实浏览器 | `tests/run-huixin-browser.cjs`，Chrome156.0.8078.49 | 18,472断言；108组合；无JS运行错误 |
| Provider/浮层/故障 | `tests/huixin-runtime-check.js` | 178断言；模态配色/焦点/几何、紧凑尺寸、原生控件主题和模拟存储故障恢复通过 |
| 旧工作台回归 | 原`tests/browser-check.js`，扩展采样随配置注册表增长 | 1,684断言；60/60配置轴配对覆盖；234多页面样本 |
| 独立范围与台账 | `check_coverage.py coverage.json --scope scope.json` | 6上下文、49控件；190/190适用检查通过，6项N/A；无遗漏/失败 |
| 静态检查 | 90个本地文档链接、JSON/SVG、5份JS语法、`git diff --check` | 通过 |
| 安装后回读 | 77个维护文件逐文件SHA-256；安装目录生成检查及63测试 | 一致且通过；已有缓存保留 |

浏览器矩阵：3页面×3配色×2模式×6视口，宽度390/683/1366/1440/1600/1920。683×384仅模拟1366×768窗口200%时的可用内容空间，没有声称实际浏览器缩放验收。对同视口换主题逐项比较几何、草稿、筛选、所选方法、焦点及DOM身份。合成玻璃背景采样的文字最小对比5.02:1，控件边界最小3.75:1；这些数值仅覆盖声明角色及背景。

视觉复核查看了桌面慧新青浅色、紫色深色和390px签收页截图；对照来源v2的导航、字阶、卡片、边距与材质语法，修正日期图标和标签对齐后通过。此为启发式风格复核，无像素相似度或真人研究结论。先前测试设置/定位及旧配对清单错误的日志保留；范围未缩减，两次源码修正后保留旧scope/result并重跑最终108组合。

## 复跑与本机证据

从仓库根目录启动静态服务：

```sh
python3 -m http.server 8891 --bind 127.0.0.1 --directory enterprise-ui-design
```

使用本机已有Playwright模块和Chrome，无下载/新增依赖：

```sh
PLAYWRIGHT_MODULE=/Users/guojiexie/.npm/_npx/31e32ef8478fbf80/node_modules/playwright node enterprise-ui-design/tests/run-huixin-browser.cjs http://127.0.0.1:8891/assets/reference-huixin/ /absolute/new-evidence-directory
```

本轮证据目录：`/Users/guojiexie/.codex/artifacts/huixin-three-layer-20261029/`。含冻结`scope.json`、`coverage.json`、`coverage-result.json`、浏览器原始断言、11份资产的起止HTTP摘要回读、旧工作台结果、单测日志、安装摘要和7张最终展示截图；均为本机产物，不提交仓库。最终受测指纹：`2291b601c8c0d7c7872decffce76185fad9336a01fb009fc435072d6fb4cfbc8`。

同步前完整备份：`/Users/guojiexie/.codex/skill-backups/20261029-112521-huixin-three-layer/enterprise-ui-design/`。同步至`/Users/guojiexie/.codex/skills/enterprise-ui-design/`；逐文件回读77文件一致。主开发工作树的无关WIP不参与提交。

Git采用Lore提交，推送功能分支后在已检出的干净main工作树快进合并、普通推送；最终SHA与远端回读在交付消息及本机`git-delivery.json`记录，避免文档自引用提交号。

## 适用边界

上述仅验证可复用Skill和本地模拟页面。没有修改/部署LIMS，没有接通真实后端、权限、上传或第三方组件库；模拟提交与存储故障不能证明真实业务成功。未做跨浏览器、屏幕阅读器、真人可用性或实际200%缩放认证。HarmonyOS字体为请求及系统回退栈，未捆绑或宣称安装该字体。宿主接入须另有业务与部署验收。
