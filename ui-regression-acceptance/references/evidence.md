# 范围、台账与证据格式

新门禁使用 **scope schemaVersion 1 + coverage schemaVersion 3**。旧 v2 不再直接 PASS；补建独立范围并核验原始执行、版本和复跑证据，缺项重新执行。元数据补齐本身不构成通过。

## 1. 独立范围 scope.json

先从源码/契约生成候选，再以真实界面核对，完成后冻结；不要从已执行结果反推范围。范围文件可以由项目原有独立清单转换得到。它与 coverage 分开维护，修改要保留旧文件/差异和原因，不能为失败缩减范围。

| 字段 | 约束 |
|---|---|
| schemaVersion | 整数 1 |
| scope | 非空的本轮业务范围，明确全部应用或指定子集 |
| build.fingerprint | 受测源码及相关规则输入的 SHA-256，由项目指纹命令产生；不是部署证明 |
| build.runtimeId | 本轮预期受测的运行版本，由构建产物/版本接口/部署记录确认；不能自行编造 |
| discovery.sourceRefs | 非空字符串数组：路由、菜单、组件、权限/开关等盘点入口的实际文件与位置 |
| discovery.runtimeEvidence | 非空证据引用数组：运行界面盘点、源码候选与运行差异的对照结果 |
| discovery.reconciled | 布尔 true 才可通过；不可达或未知范围不能宣称完成 |
| pages | 非空页面上下文数组，含 id、url、sourceRefs、inventoryComplete；弹窗/抽屉可以同 URL 不同 ID |
| controls | 控件实例数组，结构见下；每页必须有 kind=page 的整体布局实例及适用 layout 检查 |

页面和控件的 `sourceRefs` 都是非空字符串数组，指向其渲染/路由/业务绑定的实际文件与位置；运行时发现项补查来源并记录盘点过程。`inventoryComplete=false` 阻断通过。页面整体实例不代表子控件已测。

控件字段：

- `id`、`page`（页面 ID）、`name`（业务名）、`kind`（page/text/number/select/button 等实际类型）、`locator`（可复跑定位）都是非空字符串。
- `checks`：稳定且唯一的非空检查 ID 数组。角色、状态、主题和视口差异用不同 ID 或分别建台账，前置条件注明环境差异。
- `dimensions`：恰好 business、interaction、display、layout 四个键，各分配非空检查 ID 数组。四组互斥，并集恰为 checks；同一操作可共用截图/日志，各维度须有独立断言和结果。
- `notApplicable`：可选对象，键为检查 ID、值为明确 N/A 理由；其余检查一律适用。页面整体至少一条 layout 检查必须适用。

例如页面整体实例可以有 `business.na`，在 notApplicable 写明“静态布局容器不承载可写业务字段”；它仍须保留真实页面布局、显示和适用交互检查。不要给所有维度同一个通用 click 检查。

## 2. 执行台账 coverage.json

| 字段 | 约束 |
|---|---|
| schemaVersion | 整数 3 |
| scope | 与冻结范围相同 |
| scopeFingerprint | scope.json **原始文件字节**的 SHA-256；改空格同样改变摘要 |
| build.fingerprint | 与范围中的受测输入指纹相同 |
| build.runtimeId | 真实观察到的运行版本，必须与预期 runtimeId 相同 |
| build.runtimeEvidence | 非空证据引用数组：开始和结束时版本观察、与受测输入/构建的对应依据 |
| environment | url、browser（含版本）、role、theme，viewport.width/height 为正整数 |
| pages、controls | 从冻结范围复制身份与检查定义，不能漏掉未执行项或改写适用性；检查器精确对照 |
| replay.command | 实际准确复跑命令/工具入口，不能包含凭据；检查器不会执行它 |
| replay.prerequisites | 账号角色、数据准备/恢复、环境、工具/版本等运行前提，不含凭据 |
| replay.scripts、replay.logs | 非空证据引用数组：实际执行的脚本/等效可复跑工具操作文件，及执行日志 |
| results | 每个 control/check 恰好一个最终结果，不能少填，也不能重复填 |

每个结果含 `control`、`check`、`status`、`preconditions`、`contractRefs`。preconditions 是非空字符串，写实际角色、业务状态、数据与环境；contractRefs 是规则引用数组（文件+规则 ID、API operationId/JSON Pointer、规范版本+章节等），不能用页面当前表现作预期依据。

| status | 附加要求 |
|---|---|
| PASS / FAIL | 非空 steps 数组、expected、actual、evidence 数组；必须分别说明本检查的断言与观察 |
| BLOCKED | reason；规则缺失可用 missingContracts 非空数组明确缺项，此时允许 contractRefs 为空，禁止虚构引用 |
| NOT_RUN / UNCONFIRMED | reason；已有规则引用照实保留 |
| N/A | reason 必须与范围 notApplicable 中的理由相同；允许 contractRefs 为空；不计适用分母 |

修复后最终结果可以 PASS，但原失败证据引用保留为 `previousFailures`（非空证据数组），日志记录归因和复测。检查器不能知道有人删掉过历史，需审阅原始日志。模拟失败/慢网络检查在检查 ID、前置条件与证据中注明 SIMULATED；不能用它宣称真实后端业务成功。

## 3. 证据与调用

所有证据引用（含 runtimeEvidence、scripts、logs、previousFailures）统一格式：

```json
{"path": "本文件目录内相对路径", "sha256": "文件原始字节的64位SHA256"}
```

每个文件存在且非空。绝对路径、目录穿越及越界符号链接均不接受。范围的证据相对 scope.json 所在目录；台账的证据相对 coverage.json 所在目录。可以把两文件放同一轮目录。脱敏请求/响应、独立 GET 回读、浏览器 trace、截图/测量和执行日志可组合；不得保存令牌、完整认证头或无关个人数据。

```bash
python3 <技能目录>/scripts/check_coverage.py <run>/coverage.json --scope <run>/scope.json
python3 -m unittest discover -s <技能目录>/tests -v
```

退出码：0 仅为台账校验 PASS；1 为 FAIL/INCOMPLETE；2 为命令参数/输入解析错误。它核对独立范围、检查分配、适用性、版本字段、文件摘要和结果完整性，不运行浏览器或复跑命令。

执行覆盖率 = 冻结范围内已执行 PASS/FAIL 的**唯一适用检查数** / 冻结范围适用检查数；漏页/控件不会缩小分母。通过率另计：PASS / 已执行适用检查数；既不替代执行覆盖率，也不替代整体验收。页面/控件完成数需逐实例汇总：有 FAIL 则失败，有阻断/未测/未确认/缺记录则未完成，其他适用检查全通过才算完成；与检查项总数一起报告。

FAIL 表示仍有失败（同时列出未完成项）；INCOMPLETE 表示结构/范围/版本/证据不符或有阻断、未测、未确认；全部适用项通过且无缺口才可给台账 PASS。最终业务验收还须 Agent/人工实际查看脚本、运行结果、截图/测量和回读，核对预期与证据语义。文件存在、摘要正确、reconciled=true、版本字符串相同，都不能单独证明完整盘点或实际操作正确。
