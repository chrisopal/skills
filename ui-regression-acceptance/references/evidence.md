# 台账与证据格式

coverage.json 最小例子（此例未执行，不能标为通过）：

```json
{
  "scope": "本体草稿页与公理来源表单",
  "environment": "实际 URL、浏览器、构建/工作树版本、角色、视口、主题；不含凭据",
  "pages": [{"id": "ontology-edit", "url": "/semantic/ontologies/:id/edit", "inventoryComplete": true}],
  "controls": [{"id": "source-axiom", "page": "ontology-edit", "name": "公理来源选择器", "locator": "稳定的可访问定位", "checks": ["select-blur-reopen"]}],
  "results": [{"control": "source-axiom", "check": "select-blur-reopen", "status": "NOT_RUN", "steps": ["选第二项", "点击知识库字段", "重新展开"], "expected": "失焦后选中标签仍可见，重开仍选中第二项", "actual": "", "evidence": [], "reason": "等待真实浏览器执行"}]
}
```

- `pages` 包括范围内所有页面/弹窗；`inventoryComplete` 是人工结合源码与界面盘点的结论，不是扫描器自证。
- `controls[].checks` 是本实例已分配的全部适用检查。需要排除的检查可保留为 N/A，并说明业务理由。
- 每个 control/check 恰好一条结果；状态 PASS / FAIL / BLOCKED / NOT_RUN / UNCONFIRMED / N/A。
- PASS/FAIL 要记录实际步骤、预期、实际和证据文件路径（相对 coverage.json；文件必须存在且非空）。截图、trace、运行输出、脱敏断言 JSON 或回读可组合；仅文件存在不代表证据充分。
- BLOCKED/NOT_RUN/UNCONFIRMED/N/A 要写理由。UNCONFIRMED 用于已报告但当前环境无法复现的问题。
- 各种视口/角色差异需要不同 check ID 或明确拆分；不得用一个主环境 PASS 掩盖未测组合。
- 报告执行覆盖率 = (PASS + FAIL) / (分配检查总数 - N/A)。通过率与覆盖率分开，未知项不算通过。
- 每轮记录失败与修复关联；最终结果可更新，但原失败证据保留。不得写 token、密码或完整个人/生产数据。
