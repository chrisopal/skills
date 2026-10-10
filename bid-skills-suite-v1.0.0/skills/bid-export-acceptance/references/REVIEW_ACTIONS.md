# 评审未通过后的修复、重写与提升

## 用户入口

在宿主对话中说“修复本轮未通过项”“重写9.3章”或“提升评分相关技术章节”，总控直接执行已有授权内的修改，无须再次询问是否继续。

本地写作编辑器提供三个按钮及“本轮未通过项／当前章节”范围选择。按钮创建绑定当前评审的任务；没有宿主唤醒接口时显示**待宿主执行**，展开“交给当前 Agent 执行”复制交接指令。网页不直接调用模型，不假装已启动 Agent。Codex、WorkBuddy 等宿主负责实际写作与生图调用。

| 动作 | 修改方式 | 必须保留 |
|---|---|---|
| 一键修复 | 补齐具体缺项的机制、步骤、异常处置与响应 | 合格内容、固定表单、事实与来源 |
| 一键重写 | 按当前任务卡重构所选章节 | 强制标题／格式、需求及评分映射、有效证明 |
| 一键提升 | 强化评分响应、专业细节、可核验输出及验收方法 | 承诺边界；不以增加字数代替质量 |

动作产生候选稿，不等于评审通过。缺少资质原件、真实业绩、人员证明、签章、报价授权、保证金或真实演示，应列出所需材料及用途；招标条件冲突时列出需确认的原文位置。生成文字／图片不能关闭这些问题。模拟测试材料仍标注 TEST，不能认证真实投标资格。

## 宿主执行规程

1. 回读 `work/review-actions/` 中任务及当前评审，核对项目身份、正文版本和输入哈希。先领取请求；过期任务不得重新绑定。
2. 按任务的原文条件、章节、评分项和证据定位回读。分开可改正文与待补材料／待确认事项；只改受影响章节，不扩大未经授权的承诺。
3. 调用 bid-technical-writing、bid-commercial-documents、bid-evidence-matching 或 bid-visuals。知识检索以章节需求与评分条件构造查询，并核验原始材料；没查到就留缺口。并行时沿用 writing_batch 独立提案、统一合并；保存遵守冲突检查与历史备份。
4. 回读修改，记录任务ID、实际宿主／工具、执行动作、章节和证据。先检查篇幅、必配图、响应覆盖和引用，再由评审者读取新正文复核。不能只更换旧评审 SHA 或直接关闭问题。
5. 更新质量评审及15核心评审的当前版本与引用，重新冻结快照。完成检查展示修复前后、仍待处理项和材料缺口。旧导出只保留历史；重新导出后再次核验 Word／PDF。
6. 默认最多两轮整改；仍未通过则展示具体原因与下一步，不无限改写。新材料或新的明确要求可创建新版本任务，保留历史。

## 本地工具

```sh
python scripts/review_actions.py status --project /path/to/project
python scripts/review_actions.py request --project /path/to/project --request work/action-request.json
python scripts/review_actions.py claim --project /path/to/project --request-id UUID
python scripts/review_actions.py finish --project /path/to/project --request-id UUID --evidence work/action-evidence.json
```

请求 JSON：`action` 为 repair／rewrite／improve，`scope` 为 failed／chapter，chapter 需 `section_id`；同时提供 UUID `request_id`、`expected_revision` 与 `expected_sha256`。执行证据记录 `project_id`、`request_id`、实际 `tool_or_agent` 及非空 `performed_actions`。缺少前提时不得自行填成功。

服务只监听本机，同源校验不等于企业身份认证。它没有远端权限／租户模型，也没有自动唤醒宿主的通用接口。任务状态和确定性检查不证明专业评审通过、真实材料有效或正式交付就绪。
