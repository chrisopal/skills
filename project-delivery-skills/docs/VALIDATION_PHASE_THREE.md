# 第三批验证记录

2026-10-11，版本 0.3.0。第三批新增 `delivery-closure-warranty` 和 11 套模板，累计 25 个 Skill、58 套模板。客户模板、计费配置、多项目和系统交换复用总控，沿用既有主账；无新增依赖。

| 检查 | 结果与实际范围 |
|---|---|
| 全量回归 | Codex 内置 Python 执行 176 项 unittest，全部通过、无跳过；较第二批新增 50 项 |
| 分段验证 | 计费固定/工时/混合、封顶/未知；实际字段规格与 JSON Pointer 映射、必填/类型/敏感路径；交换回执身份/内容/来源及重复操作；组合币种/共享容量/未知工时；四个收尾结果、日期、拒绝签收与跨修订删除 |
| 技能结构 | suite validator 25/58 通过；25 个 Skill Creator 检查与 agents/openai.yaml 解析通过 |
| 独立复核 | 两个可复现问题修复后 APPROVE；针对收尾、复用和运行集成，非客户验收 |
| 独立使用演练 | 新上下文 Agent 在未结缺陷、未对齐结算、保留投入和持续质保场景中保留开放事项；不把阶段验收解释为全部义务解除 |
| 文件流案例 | `verify_phase_three.py` 创建 10 个可回读登记对象；精确版本及输入校验通过；本地 JSON 映射/交换文件回读与内容哈希一致 |
| Word | 29 份可编辑 DOCX 全部原生文本/表格回读；本机 LibreOffice 渲染第三批 5 份文档共 10 页，中文可读、表格完整 |
| Excel | 29 张台账的表头、空白行、冻结、筛选与蓝色样式回读；第三批 6 张表用已有 artifact-tool 实际渲染并检查 |
| 审阅页 | 沿用 Enterprise UI Design 蓝色系统；实际浏览器显示新增阶段与四个收尾结果，搜索 3 条/空结果 0 条、导航复位 68 条；桌面和 390px 无页面横向溢出 |
| 安装 | 升级前 24 个本机目录与 Git 基线哈希一致；全部备份后仅替换总控并新增收尾 Skill；25 个安装目录与源一致，重复安装无改写，安装版 validate 通过 |

## 已修复并复测

- 真实收尾不能使用未来 UTC 截止日；质保不适用也需条款依据，质保未结束或存在开放事项时不予全部解除。
- 拒绝、带条件、未就绪的 confirmation 不能证明已签收；正向引用同时检查 review/change/handover 的结构化结论。自然语言及原件真实性仍由业务审核。
- 既有义务、质保、资源和归档行跨修订保留；不能删除 retained 资源绕过释放证据。已关闭义务改为非关闭须有纠正理由和证据。
- 客户映射在类型转换前核验嵌套敏感字段；改名或转成字符串不能掩盖敏感来源。普通财务金额可以作为已选交换内容，发送前仍需检查实际接收权限。
- 回执绑定 operation_id/system/entity/direction/record_id/external_id 和 payload_sha256；模拟回执不能用于真实项目。已核对操作不可改写，旧映射漂移使后续准备失效。
- 跨项目未知工时使合计和超载判断保持未知；不同币种分开汇总，人员身份和共享容量显式提供，只支持当前 UTC 提取日。

## 案例结果与限制

模拟固定费用 100000 元，加按工时服务 20×500 元并封顶 8000 元，估算为 CNY 108000.00；不是确认收入、发票或收款。收尾案例返回行政收尾完成、质保已移交，同时质保未结束、全部义务未解除。交换从 prepared 到 reconciled 使用显式模拟回执；`dispatched_by_tool=false`。

案例使用 purpose=simulation，合同、决定、签收和财务内容均为模拟。成本/工时主账缺失在摘要中明确显示；案例的行政结果只验证声明与引用机制，不证明真实财务对账。独立使用演练要求缺主账、凭据或存在已知差异时保持 settlement.open。

系统对接本轮是本地入站/出站候选及回执核对，没有飞书、代码或财务系统的真实网络写入和自动主账回写。客户模板工具读取实际 JSON 字段规格、输出本地 JSON 草稿；客户专用 Word 原版式另需文档排版与回读。尚无真实客户全过程、生产环境、身份认证、财务执行、Microsoft Word/Excel 原生操作或跨机器分页验收。Python AST/编译和运行测试通过，仓库未配置额外 Python 静态类型门。

## 本地证据与复现

生成物保留在 `output/project-delivery-phase-three-validation-20261011/`，不纳入 Git：`full-tests.log`、`case/`、`template-kit/`、`office-readback.json`、`office-render/`、`spreadsheet-render/`、`ui-desktop.png`、`ui-mobile.png`、`installation.json`、旧版安装备份及模板 ZIP。

```bash
python3 project-delivery-skills/scripts/validate_suite.py
python3 -m unittest discover -s project-delivery-skills/tests -v
python3 project-delivery-skills/scripts/verify_phase_three.py --out /absolute/path/to/new-case
```

全量测试使用已有 python-docx/openpyxl 的内置 Python，避免 Office 检查跳过。Office、浏览器和独立使用演练与自动单测是不同证据；代码测试不代替真实客户或合同履约确认。
