# 质量闭环：预检、整改与当前版本复核

本规程用于新完整编标和新版质量回归。保留现有17个核心Skill，由宿主真正调用模型、知识库、生图和章节Agent；共享脚本不提供后台模型服务。

1. 总控先运行 `workflow_quality.py preflight --project /project --require docx --require pdf --require pdf_export --out work/preflight.json`。宿主发现的生图、子Agent、知识库、OCR能力写入 `work/host-capabilities.json`，字段为项目ID及 `capabilities.NAME={status,evidence}`，用 `--host-capabilities`绑定。`available`只是实际可发现，不等于已成功执行；必需能力未就绪先记录阻塞，不能用占位图冒充。
2. 评分Skill逐条回查原文，在 `profiles/quality-plan.json` 拆解每个计分叶子及共同事实；按[质量评审契约](QUALITY_REVIEW.md)保存04/05/09版本和实际来源。目录任务卡说明每章实际承担条件，不将父章全部分值重复分配。计划先于正文；正文变化后逐条重新读取并登记事实引用，不只重填哈希。
3. 写作按既有 `writing_batch.py` 派发和集中合并；绘图按已有配图Skill实际生成并插入，系统图明确示意属性。审阅者回读完整招标条款、正文和证明材料后保存 `reviews/quality-review.json`；`prepare`全部为unknown，不能自动填通过。
4. 运行 `quality_checks.py check --project /project` 和 `workflow_quality.py plan --project /project --max-attempts 2`。计划保存在 `work/remediation-plan.json`，缺字/缺图/条件缺口关联稳定章节ID，宿主只执行对应写作、配图或材料任务。保留未受影响章节。
5. 每轮实际执行后保存 `work/remediation-attempt-N.json`，包含 `project_id`、实际 `tool_or_agent` 和非空 `performed_actions`。运行 `workflow_quality.py record-attempt --project /project --evidence work/remediation-attempt-N.json`。项目输入必须真的变化；之后 `status`重新检查实际正文、图片及条件，存储的resolved不构成通过依据。次数用尽保留问题，不能降低标准。
6. 总控恢复时先回读整改status、章节批次status及实际宿主任务。运行中任务核实后使用既有fail/collect/merge恢复，不按等待时间自动释放可能仍在写入的Agent。版本冲突保留独立提案，不覆盖。
7. 15评审绑定质量评审当前文件；16按[实际导出检查](EXPORT_ACCEPTANCE_CHECKS.md)读取相同spec和实际DOCX/PDF生成收据。正文、材料、设置或图源变化，重评并重导出。目录必须在实际引擎刷新、保存、重开；逐页视觉证据与机器检查分别记录。

关键材料未知、资格不满足和明确否决条件继续阻塞。已查明的纯评分失分保留警告和整改动作；主观评分、企业真实性、授权人身份不由脚本认证。缺原件、未运行OCR/WorkBuddy、未测字体等按真实范围标记，不能因为本地回归通过宣称全部业务通过。

评标阶段的外部数据条件按 `phase=evaluation` 和 `deferred` 单独展示，不误报为正文缺失，也不算已经得分。恢复旧任务时，先运行当前版本绑定与质量检查；历史评审结果只是历史证据。实际PDF视觉回看发现的目录、文案或表格问题必须整改后重新导出、重新生成文件收据，不能沿用旧哈希。
