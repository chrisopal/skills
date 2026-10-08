# 评分、关键材料与否决条件逐项评审

评审矩阵是宿主Agent逐项读取后形成的判断，辅助脚本验证集合、证据和状态的一致性。`formal_release_ready`只描述核心检查；正式授权仍由bidkit.release_gate复核，离线脚本不认证真人身份。

## 三张表

- `compliance`覆盖05的全部条款，原文的资格／明确否决是关键门槛。履约、提交与条件性条款保持原类别。
- `materials`覆盖09的全部选用组。一个材料可以支撑多个目标，但每组选用要检查自己的条件。`subject/validity/scope/independent_count/required_pages/signature/inclusion/authenticity`逐维记录passed、failed、unknown或not_applicable。多份证明在09.materials上登记`independent_evidence_id`，取实际合同号／证书身份；同一合同不同文件使用同一个身份。哈希只能排除字节重复，身份和真实适用性仍需原件复核。
- `scoring`覆盖04的全部scored叶子，rollup不重复评分。对原文各档条件、限定次数、封顶、互斥和证明页给出理由；数值估计为null不会被当作零分。记录计算／假设而非保证主观分。

每行字段：target_id、conclusion、rationale、sources、bid_refs、material_ids、dimensions、dimension_exemptions、score_estimate、finding_ids。实际来源采用既有source_id/revision/sha256/location/quote/kind；正文引用relative_path/sha256/location/quote，JSON定位到具体正文文本，例如`/data/chapters/0/body`，Markdown定位`L10-L15`。原件引文与正文引文分别验证，不能用招标要求或响应表全文自证正文。

满足／部分满足必须有正文依据；非满足项关联FIND-ID及目标，理由必须区分未审、缺失、局部支撑和不适用。资格／明确否决与关联强制要求的材料缺失或未知阻止正式交付；单纯评分损失产生警告和具体失分说明。警告需要依既有门禁实际处理，不自动批准。

资格条款默认应有09材料选用组；原文明确要求证明的05条款或03强制需求可标记`material_required=true`，不可按关键词推断。丢失整组选用也会阻止交付。明确否决类别但fatal非true视为分类冲突，回查原文，不降级为普通警告。

材料维度采用not_applicable时，`dimension_exemptions`必须逐维提供reason、relative_path和sha256；复核文件实际存在且绑定15.inputs。整行不适用通过真实条件复核后才可豁免对应材料组；未审评分项unknown阻止正式交付，已核实的失分仍作为警告。

not_applicable不能自动通过：记录原文适用条件与实际情况，关联已复核发现及实际复核文件。模拟证照／合同只可用于显著标记的测试，不能使正式门禁通过。旧矩阵或文档变化后重审，不只更新哈希冒充复核。

## 宿主执行

首次`prepare`生成unknown计划；宿主逐条回查原件及最终候选正文，再填入15的data.core_matrix。PDF文本原件回读使用已有可选PyMuPDF依赖；缺少时明确保留核验错误，不自动安装或通过。对扫描证明、截图签章、电子签章、适用法规或真实性，使用宿主实际开放的OCR／视觉／专业核验能力；缺能力保留未知，不能拿文字存在替代。

先执行validate_output结构检查，再执行review_checks.check与冻结快照。任何漏审、重复行、未知ID、伪定位、来源变更或材料结果冲突都必须处理。检查回执区分errors、release_blockers和warnings；check命令发现errors或release_blockers返回非零；warnings单列。检查成功不意味着真实评标、真实性认证或正式可发。

导出16在生成前后再次调用核心检查和快照检查；封面、目录与版式配置在profiles内冻结。导出后读取实际Word/PDF，检查关键声明、报价、附件与证明页实际存在；扫描件或图片材料还需视觉核对，内部源文件齐全不证明最终附件齐全。

## 验证边界

工程负例验证漏审、来源／正文漂移、数量、检查结论矛盾、模拟正式发布拒绝；真正的错误主体、过期证照、独立合同或签章应再做宿主从原件阅读的盲测。脚本无法从自由文本或印章图像认证真实资格；自评表的passed仍是审阅者输入。

章节篇幅、详细程度与界面必配要求见[章节策略](CHAPTER_WRITING_POLICY.md)。明确字数/缺图由当前配置检查，设置变化使旧内容快照过期；推荐或结构检查不认证评分满足。
