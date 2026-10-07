# 可选命令行工作流

这些命令提供文件层辅助，默认不调用模型。显式启用 PaddleOCR 时会请求已配置 OCR 服务；其他模型理解、宿主检索、视觉、专业判断与真实人工确认仍由宿主和用户完成。以下示例从套件根目录执行，路径按本机替换。

## 1. 初始化，不覆盖现有目录

```bash
python scripts/bidkit.py init --project ./my-bid --project-id BID-001
python scripts/bidkit.py register-source --project ./my-bid --file /absolute/path/tender.pdf --role main
```

注册会复制原件到项目inputs并计算SHA256。不要把实际客户目录直接当空项目目录初始化。

## 2. 配置与原生解析

```bash
python scripts/bidkit.py compose-profiles --packs profiles/procurement/enterprise-procurement.json profiles/domain/smart-factory.json --out my-bid/profiles/selected.json
python scripts/extract_sources.py --project ./my-bid --project-id BID-001 --out my-bid/artifacts/01-source-intake-r1.json
```

默认只做本地原生提取；扫描、图像和复杂DOCX会明确标需复核。配置 [PaddleOCR 服务](OCR_SETUP.md) 后，可加 `--ocr paddle-service` 补读扫描 PDF 和 PNG/JPEG。远端服务仅在已有授权范围内加 `--allow-remote-ocr`。新结果保存新文件；脚本补全输入哈希并按既有结果递增 revision，保留真实页与来源。完成机器提取仍需核验业务内容。

## 2.1 项目知识与 Wiki

```bash
python scripts/knowledge.py add-local --project ./my-bid --file /path/to/supplier.md
python scripts/knowledge.py import-host --project ./my-bid --file /path/to/host-results.json
python scripts/knowledge.py search --project ./my-bid --query "设备运维"
python scripts/knowledge.py validate --project ./my-bid
```

根据实际来源选择 add-local 或 import-host，不要求两者都有输入。宿主检索由 Agent 先执行真实工具调用，快照格式见 [知识接入](KNOWLEDGE.md)。项目 Wiki 自动生成到 `artifacts/knowledge/wiki/`；知识查询不会自动接受资质或业绩。扫描的企业资料在 add-local 时也可显式启用相同 OCR 选项。

## 3. 校验模型填好的产物

```bash
python scripts/validate_output.py my-bid/artifacts/03-requirements.json --schema skills/bid-requirements/assets/output.schema.json
```

可对合成演示运行：

```bash
python scripts/bidkit.py scoring-check --file examples/smart-factory-demo/artifacts/04-scoring.json
python scripts/bidkit.py coverage-check --requirements examples/smart-factory-demo/artifacts/03-requirements.json --scoring examples/smart-factory-demo/artifacts/04-scoring.json --compliance examples/smart-factory-demo/artifacts/05-compliance.json --outline examples/smart-factory-demo/artifacts/08-outline.json
```

映射检查不判断正文是否满足；评分检查只处理声明为简单加和的结构，不认证原文抽取完整或真实得分。

## 4. 冻结评审输入

确认应评审的版本已全部写入inputs/artifacts/assets/profiles后：

```bash
python scripts/bidkit.py snapshot --project ./my-bid --out reviews/input-snapshot.json
python scripts/bidkit.py verify-snapshot --project ./my-bid --snapshot my-bid/reviews/input-snapshot.json
```

随后让15技能把快照fingerprint写入reviewed_inputs_sha256，评审结果存reviews。正式核验覆盖新增加的文件，因此新增补遗也会让快照失效。脚本不会自动批准评审，也不替代并发事务控制。

## 5. 文档工具演练

```bash
python -m pip install -r requirements.txt
python scripts/build_docx.py --spec assets/document-spec.example.json --out ./draft-demo.docx
python scripts/convert_pdf.py --input ./draft-demo.docx --out ./draft-demo.pdf
python scripts/inspect_artifact.py ./draft-demo.docx
python scripts/inspect_artifact.py ./draft-demo.pdf
```

基础DOCX生成器只生成有明显内部标识的可编辑工作稿，不保真填充所有客户固定模板，也不自动创建目录或完成证明材料插页。正式项目应由14技能使用宿主合适的文档工具落实格式。转换与机器检查之后仍须逐页视觉检查。

## 6. 交付门禁

复制assets/human-confirmation.template.json到项目confirmations，由真实用户／审批系统补充实际确认记录；不得让AI自动签批。记录project_id为项目work/project.json中的值，review_sha256为评审文件字节哈希，snapshot_fingerprint为快照fingerprint，authorization_ref为真实授权凭据引用。快照、评审、确认记录与交付清单的project_id必须与项目一致；旧记录缺此字段时需重新核验并由真实授权人补充确认。

```bash
python scripts/bidkit.py check-release --project ./my-bid --review my-bid/reviews/15-review.json --snapshot my-bid/reviews/input-snapshot.json --approval my-bid/confirmations/release.json
```

此门禁检查文件一致性与确认记录形状，不认证签批人。完成实际文本和视觉验收后，按16技能生成交付manifest并运行：

```bash
python scripts/bundle_delivery.py --project ./my-bid --review my-bid/reviews/15-review.json --snapshot my-bid/reviews/input-snapshot.json --approval my-bid/confirmations/release.json --manifest my-bid/deliverables/16-delivery-manifest.json --out ./bid-delivery.zip
```

只打包manifest明确列出的deliverables内DOCX/PDF及公开文件哈希表，不混入内部证据、报价策略或全部项目文件夹。脚本既不外发也不提交交易平台。
