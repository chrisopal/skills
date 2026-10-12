# 工作台、评分证据与真实售前联动

## 同一主账

以下 RUN 是本 Skill 的 `scripts/run.py` 绝对路径，DB 是用户项目数据库的绝对路径。需要 Python 3.10+，不新增依赖。

```bash
python3 "$RUN" serve --db "$DB" --port 18768
```

打开 `http://127.0.0.1:18768/`。当前支持首次拜访、新增反馈、评分确认、竞争情报新增/更新、行动新增/完成、客户评审新增/解决/重开及正式阶段推进。图表和表单读写同一 SQLite。事实、成果文件和签署材料的登记仍使用 CLI；工作台不伪造审批或签约操作。

每次写入提交当前修订号及稳定请求 ID；过期表单返回冲突，刷新当前主账后重新填写。重复提交同一请求不重复记账。已有证据不可用相同 ID 覆盖；新增材料用新 ID。表单中的 actor 是记录人，不是已认证身份。

服务仅监听 loopback，限制精确 Host/Origin、会话随机令牌、请求大小和可写字段。浏览器不得读取任意服务器文件或登记文件成果；没有目录文件浏览、CORS 或远程用户登录。仅用于受信任本机用户，不能经反向代理暴露为多用户 CRM。停止服务用 Ctrl+C，数据库保留。

## 评分与竞争

`detail.assessment_history` 按存储顺序保存每次评估的答案、维度、来源和相邻变化；汇总分与维度差值分别记录。旧历史不会因为新算法而改写。显式评分答案引用 `sales_confirmation_answers[].evidence_refs` 中属于本商机的证据；这些引用替换推断来源。没有来源时评级仍可用于启发式运算，但状态为 `needs_sales_confirmation`。来源 ID 证明可追溯，不证明人的语义判断正确。

三个雷达类别展开到18个维度，未知40表示信息缺口。页面中的赢单可能性是启发式参考分，不是经过统计校准的成交概率。竞争情报更新不自动改变评分。

管理竞争记录示例（放入标准 manage envelope 的 operations）：

```json
{
  "type": "record_competitor",
  "competitor_id": "COMP-A",
  "name": "竞品甲",
  "position": "客户正在接触",
  "strengths": ["客户转述价格较低，范围未核实"],
  "weaknesses": ["接口与离线覆盖未知"],
  "response": "按相同账号、范围、税费和交付责任逐项核对",
  "status": "reported",
  "price_amount": 320000,
  "currency": "CNY",
  "evidence": ["EV-07"]
}
```

相同 competitor_id 更新当前版本并追加历史。`confirmed`、`reported`、`unknown` 保留来源状态；价格必须为非负有限数，报价范围不完整时不能推断胜负。

## 导出到已有售前 Skill

先读取当前主账，人工整理 requirements JSON 数组。每项包含 id、statement、evidence_ids，可加 original_quote、type、stakeholder、conditions、priority、success_standard；只允许引用本次选中的证据。需求中的方案建议和待确认条件应明确写出，不能当作客户事实。

```bash
python3 "$RUN" presales-export --db "$DB" --opportunity-id "$OPP" \
  --project /absolute/project/presales --project-id SALES-001 \
  --evidence EV-02 --evidence EV-06 \
  --requirements /absolute/project/requirements.json \
  --audience 客户业务与IT组 --purpose internal-draft
```

目标必须是新项目；不覆盖已有售前文件。桥接调用已安装或同仓库的 presales-orchestrator runtime，创建真实 SRC-OPPORTUNITY、BRIEF、EV、REQ 和 `work/opportunity-handoff.json`。可用 `--runtime` 指定受信任的实际 runtime.py。未安装时明确报错，不虚报方案完成。

仅导出选定原始证据、需求、受众、用途及商机标识；不自动附带销售评分、内部竞争台账或所有附件；选定原文是否包含内部信息仍需在导出前检查。交接记录选定证据摘要与初始项目配置摘要。权限依然是本地草稿，`customer-review` 用途不等于发送授权。

售前总控继续组织澄清、资料匹配、方案、逐页内容、独立内容审核、PPT Skill 制作和实际文件审核。沿用售前自身的 envelope、版本与 hash，不在商机套件复制这些阶段。

## 回收实际交付版本

先在售前项目登记当前 DELIVERY、内容独立通过审核，以及绑定同一交付版本的文件审核。实际 PPTX、PDF、页渲染证据应存在并经过回读。随后：

```bash
python3 "$RUN" presales-receive --db "$DB" --opportunity-id "$OPP" \
  --project /absolute/project/presales --delivery-id DELIVERY \
  --artifact-id SOL-PPT-3 --document-id solution --version 3 \
  --request-id receive-ppt-3 --expected-revision 18 --actor 售前负责人
python3 "$RUN" lifecycle --db "$DB" --opportunity-id "$OPP"
```

版本号应大于同 document_id 已有版本，expected_revision 使用当前回读值。接收要求交付消费原始交接、选定证据仍属于同一商机、项目用途及配置未变、当前内容独立审核通过、当前交付审核通过。检查并登记 PPT/PDF/页图、内容、来源、审核、索引及配置的摘要。

文件缺失/变化或上游版本变化后，方案会显示 `dependency_invalid`，报价等下游随依赖失效；历史客户意见可能需要对新版重评。索引使用整体摘要，新增无关售前产物也可能使已接收方案失效，当前采用保守复核策略。不要接收后再向该售前索引追加无关内容；需要变化时制作并接收新版。

相同接收请求返回原始收据和当前主账有效性，即使上游后来变化；换 actor、目标、版本或其他调用参数时必须使用新请求 ID。内部制作/审核通过不自动关闭客户意见、不推进阶段，也不表示真实客户批准、生产验收、外发、合同签署或回款。

## 分时案例验证

```bash
python3 /absolute/opportunity-orchestrator/scripts/case_study.py \
  --output /absolute/new-case
python3 /absolute/opportunity-orchestrator/scripts/case_study.py \
  --output /absolute/new-editable-case --through 6
```

完整案例12个时间点直到模拟签单；第6点截取保留方案共创供表单演练。两者均在新目录运行真实 CLI 与 SQLite；模拟客户、签署文件和竞争转述不能作为真实业务事实。案例原有方案工作稿不是 PPT；实际 PPT 联动应按上述流程另外完成并核验。
