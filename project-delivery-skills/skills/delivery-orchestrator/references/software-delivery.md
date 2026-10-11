# 软件实施专项契约 v0.2.0

各 Skill 按本契约把模板内容映射到 JSON，模板台账不自动双向同步。所有精确引用均须出现在 inputs 的传递闭包；register 返回实际 sha256。`ready` 只表示整理完毕，可包含未执行项；门槛决定该阶段是否达标，客户签署另用 confirmation。

## 七类对象

| kind | data 必填字段 | 行内字段与判断 |
|---|---|---|
| solution | components、decisions、requirement_ids | components: id/purpose/requirement_ids/deployment/security/nonfunctional；decisions: id/question/options/selected/rationale/status/evidence_refs。status=proposed/decided/blocked，decided 必须有选择、理由与证据。目标不是测量结果。 |
| ui_design | pages、fields、permissions、states、requirement_ids | pages: id/title/requirement_ids/states；fields: id/page_id/type/length/precision/unit/required/default/enum/validation/source/sensitivity；permissions: id/page_id/field_ids/role/action/condition/effect(allow/deny)；states: id/page_id/from/action/to/allowed_roles/error。适用性未知填 null 或解释，不能省略字段。跨页面权限/未知状态拒绝。 |
| integration | interfaces、mappings、migration、reconciliations、requirement_ids | interfaces: id/owner/source_system/target_system/direction/trigger/protocol/auth_method/environment/status/idempotency/timeout/retry/compensation。status=unknown/blocked/designed/verified。mappings: id/interface_id/source_field/target_field/type/unit/transform/business_key。 |
| work_package | plan_work_package_id、requirement_ids、design_refs、completion_rule、build_ref、evidence_refs | 必须对应输入计划中的工作包及需求范围；design_refs 指向蓝图/专项设计。state=planned/in_progress/completed/blocked；completed 必须有实际构建及证据，未实现时 build_ref=null。此门槛只说明工作包完成记录，测试/UAT 是独立门槛。 |
| testing | requirement_ids、environment、build_ref、cases、defects、uat | cases: id/requirement_ids/steps/expected/actual/state/evidence_refs，state=not_run/pass/fail/blocked；pass/fail 必须有实际记录。defects: id/case_id/severity/state/owner/retest_case_id/retest_refs，severity=blocking/major/minor，state=open/fixed/closed；closed 必须对应本构建 passing 复测。 |
| release | environment、build_ref、testing_ref、readiness、execution、rollback | testing_ref 必须指向本构建 testing。readiness: id/title/state/owner/evidence_refs，state=pass/fail/not_checked；核心 id 为 backup/rollback/window/monitoring/authorization，均通过才具备执行条件，项目可增加检查。 |
| handover | audiences、training、operations、assets、open_items | audiences: id/role/owner；training: id/audience_id/attendance/competency/evidence_refs，competency=not_checked/pass/fail；operations: owner/state/runbook_refs/receipt_refs；assets: id/owner/version/evidence_refs。接收密码/令牌只给受控凭据位置，禁止直接写入客户包。 |

requirement_ids 为非空唯一数组，必须来自精确绑定的需求主账。solution/ui_design 要覆盖声明范围；模块范围外需求不能隐式算完成。需求已覆盖不证明详细设计合理，Agent 仍检查规则、例外、字段显隐、只读、单位、性能/安全和实际来源。

UI 门槛逐页检查 fields、permissions、states，不能用其他页面的完整记录抵消本页缺项。确实不适用时，可在 data.not_applicable[page_id][group] 写明理由，group 为上述三个数组名；空理由不豁免，人工评审仍需核实适用性。

## 构建、接口与迁移

build_ref 是工程引用，不是登记对象引用：`{"repository":"仓库或受控制品位置","revision":"精确提交/构建号","sha256":"实际制品的64位SHA-256"}`。工具检查完整性和对象间一致性，不能仅凭此证明远端制品存在。实际制品/代码、原始运行日志由 Agent 回读，再用 source/evidence 登记。

reconciliations 每行包含 id/interface_id/state/build_ref/environment/counts/business_keys/evidence_refs。state=not_run/pass/fail；执行后必须有构建、环境、数量与业务键结果及证据。counts/business_keys 各行含 expected/actual/state（可附 name），pass 不允许数量/键不一致或环境不一致。verified 接口必须有 passing 对账；HTTP 200/ping 不等于业务一致。不同构建/环境的记录不能作为本次联调结论。

当前修订中，同一接口的对账记录须全部通过、使用该接口环境及同一构建；存在 fail/not_run、环境不符或混合构建时门槛不通过。旧执行记录保留在历史不可变修订中，不能把旧成功与当前失败混在一起后仅选成功结论。

migration.applicable 为 boolean。不适用给 reason；适用必填 owner/state/backup_refs/rollback_plan/freeze_window/rehearsal_refs/reconciliation_refs，state=planned/rehearsed/completed/failed。rehearsed/completed 需要备份、回滚方案、冻结窗口、演练与对账证据。Agent 核对备份可恢复、全量/增量边界、记录数/金额/业务键一致性、权限和实际执行阶段，工具不执行迁移。

## 测试、上线与移交门槛

uat 包含 state(pending/accepted/conditional/rejected)、scope_requirement_ids、actor、role、origin(actual/simulation)、evidence_refs、open_items。accepted 必须覆盖当前测试全部范围且没有待决条件；真实项目不接受 simulation。所有测试通过、需求有 passing 用例、缺陷关闭且 UAT accepted 时，testing 门槛才通过。残余风险接受须保留实际授权与范围，首版自动门槛仍保守显示未完全通过，由人工评审判断局部可推进范围。

release.execution: state(planned/succeeded/failed/rolled_back)、evidence_refs、verification_refs。实际执行必须有依据；succeeded 必须有业务验证且 rollback.state=not_needed。rollback: state(planned/not_needed/succeeded/failed)、plan、evidence_refs、restore_refs；succeeded 必须有实际动作及恢复验证；rolled_back 必须对应成功回滚。

snapshot.gates[artifact_id] 返回 ready/reasons/kind；release 额外返回 ready_to_execute。就绪只适用于尚未执行、回滚方案已准备、全部核心检查及同构建测试/UAT 通过的版本；失败后不能凭旧准入自动授权重试。release.ready 只在执行成功且质量/就绪均达标时为 true。回滚恢复成功仍不是交付成功。此处的“授权”检查绑定来源，不认证审批人，不执行生产动作。

handover 只有每类培训对象均有能力验证通过、运维 accepted 且负责人/手册/接收证据完整、有移交资产且无 open_items 才达标。签到不代表能力；项目阶段移交不代表质保结束。

## 模板映射与实际回读

Markdown/CSV 用于人读、编写和办公系统流转；上述 JSON 是运行记录。模板中的组件/页面/用例等 ID 对应行内 id，文档 ID 对应 artifact_id，输入版本清单对应 inputs，工程版本对应 build_ref。混合 CSV 的行类型必须先拆为相应数组；空白单元格只能在契约允许未知时用 null，不能默认完成。模板与 JSON 均回读后才报告一致。

当单独调用专项 Skill 时只要求当前任务实际输入；不补造缺失的合同、确认或工程历史。未拿到第三方环境、客户回应、真实测试或生产权限时保留受阻/未执行，输出可评审草稿及明确下一责任人。
