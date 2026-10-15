# 商机范围和商业内容复核验证

## 实现

- lifecycle.py：solution_scope 显式方案+摘要绑定；商业 scope_review 绑定实际范围事实及版本；范围重确认、文件变更和版本替换派生失效，所有商业目标重新核验。未知/旧记录不补造确认，保留回退、重开、幂等和原子事务。
- 两份 schema：表达范围文本/绑定、商业复核及合同交接条件；派生状态字段保留旧数据可读性。
- workbench.js：真实范围确认表单、当前/原范围版本及复核细节；过期范围不作当前标题；中文化签署、前提、依赖错误并将 alert 带入视口。
- 七Skill仍共享同一运行层；更新总控、方案、报价、谈判、关闭指引及案例调用，不新增审批平台、数据库迁移或依赖。

## 自动验证

- 98 analysis/runtime 测试和12 orchestration 测试通过。新9项覆盖范围缺绑定/错属/版本替换、多方案串用、未知和文件篡改、内容复核缺失/错版、同文件范围重确认、旧数据、事务重放，以及实际JS错误翻译和公开Schema校验（使用本机现有jsonschema，运行层不增加依赖）。
- 完整12时点华辰案例实际调用CLI，综合分52、52、62、64、63、75、82、82、79、84、84、84；最终模拟合同358000 CNY，客户意见、范围版本、商业依赖和签署回读有效。
- 共享运行层 portable validator、7入口检查、suite本地链接/运行层检查、Python语法、Node语法与git diff --check通过。
- 独立review发现并修复：Schema非文本/未绑定范围与合同交接缺复核仍通过；UI旧范围错误回退到未确认方案。最终APPROVE。Python LSP与代码诊断服务不可用，未宣称静态类型检查通过。

## 浏览器验证

隔离本地虚构数据：output/opportunity-scope-review-20261015/browser-case/opportunity.db，商机opp_845822b5de5a；原演练主账不改。

1. 第11事件合同草稿，revision22；实际浏览器点击赢单，收到中文“需要先登记一份已签署合同”，正式状态不变。
2. CLI增量记录EV-SCOPE-3并注册SOL-3，revision24。旧范围需复核、客户意见需复核、旧商业链失效；阶段仍contract_signing。浏览器赢单再次拒绝，中文逐项指出原因且revision不变。
3. 真实范围确认表单绑定SOL-3、实际范围文本和已有证据；保存revision25，scope fact v3当前有效；键盘Tab可到达确认按钮。
4. 实际回读并修订报价/谈判/合同工作稿；CLI复核客户意见、登记Q-3/N-2/C-3及当前范围阅读声明，重新授权Q-3。revision29；浏览器仍拒绝未登记签署。
5. 登记模拟签署稿C-4及双方签署记录revision30；浏览器实际赢单并刷新，revision31/status won，评分84。独立新进程回读范围、三条关闭意见、实际文件摘要、Q-3→N-2→C-4及签署绑定一致，verification_status current。
6. 亮/暗1440和390、亮1366/1920：截图已实际查看、页面scrollWidth等于clientWidth。表格内部滚动保留；console error为空。scope form窄屏和实际358000 CNY签署表已查看。visual-verdict93/pass（.omx/state/opportunity-scope-review/ralph-progress.json）。

证据：本地proof截图、browser-acceptance.json、full-case/acceptance.json及CLI请求/回读；这些均不提交。此路径只验证范围换版及签署门禁；浏览器分支保留原第11事件的后续行动，未冒称所有交付行动完成。完整12事件案例另验证模拟交接。

## 限制与兼容

阅读结论属于记录人声明；运行层不自动理解任意文件正文，不认证actor，不证明真实客户批准、生产POC、签章真实性、回款或收入。旧数据需要先回读原件，显式确认范围并逐级登记新商业版本，重新授权；已won更正先显式重开，旧签署不得挪到新合同。没有改写旧历史或自动认证迁移。
