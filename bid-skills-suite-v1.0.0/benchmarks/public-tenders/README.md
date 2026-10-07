# 公开招标文件试点

本轮按工程施工、硬件供货、软件集成、服务外包、智慧化组合五个采样方向各取两份文件，实际采购类别允许交叉。智慧化不是独立的互斥类别。文件均为2024—2026年的历史公开样本，不表示仍在招标。

manifest.json 保存10份原件的公告/附件URL、标题、日期、SHA256、字节、页数与本地相对路径，共1068页。九份来自中国政府采购网公开附件，一份来自院校官网。采样分组不是分类答案；如“硬件”采样组的一份文件还采购独立软件许可与平台对接。

## 文件与标注

- manifest.json：可复查来源及文件身份。publication_date 是公告日期，document_issue_date 是采购文件日期，不混用；未确认日期保持 null。
- annotations.json：68个精选证据锚点，覆盖基础信息、需求、评分、资格与否决四轨；分类另有证据。标注经过AI来源复核，尚未由行业专家审定，不是完整真值集。
- annotations.json 的 annotation_revisions：记录试读后回看P11/P19软件报价行，修正智慧教室样本漏标软件组件；修订依据是原页，不是为了迎合模型。
- 运行结果保存在独立本地语料目录，不纳入源码。首轮 independent-run 与 corrective-run 不互相覆盖；修复复跑不是新的盲测。

本机原件目录：/Users/guojiexie/Development/skills/projects/public-tender-corpus-20261007/。raw 保存原PDF，text 保存逐页文本，projects 保存10个已登记项目及01原文产物，previews 保存关键表页渲染。搬到其他机器时设置自己的 corpus-root；不要使用套件源码目录存放客户材料。

复建语料时从 manifest 的 source_url 下载到 relative_path，然后用下面 audit 核对SHA256、字节和物理页数；远端内容变化时保留新版本并重做标注，不替换哈希冒充同一原件。部分附件来自结果公告，结果公告日期晚于文件编制日期是正常情况。

## 复跑

在套件根目录运行（Python 3.10+及现有requirements）：

~~~bash
python scripts/benchmark_tenders.py audit \
  --manifest benchmarks/public-tenders/manifest.json \
  --annotations benchmarks/public-tenders/annotations.json \
  --corpus-root /absolute/corpus

python scripts/benchmark_tenders.py evaluate \
  --manifest benchmarks/public-tenders/manifest.json \
  --annotations benchmarks/public-tenders/annotations.json \
  --corpus-root /absolute/corpus \
  --predictions /absolute/corpus/independent-run/predictions.json
~~~

独立执行者只读取原件、技能和分类模板，不读取 annotations 或评测输入。预测根字段为 model、run_id、scope、input_scope、samples；每份样本包含 sample_id、sha256、lots（categories、evidence）、facts（track、page、quote、meaning）与limitations。page使用从1开始的PDF物理页，不能混用页脚印刷页码。每个分类引用和事实引用均回查原页。

首次路由使用 docs/TENDER_ROUTING.md 的 brief → 宿主分类 → route，四轨输出继续遵守02—06原有产物契约。本次试点的简化facts格式只用于测试，不是生产需求矩阵的替代品。

## 评价边界

classification_labels_match 只比较分类与标包组合，classification_evidence_valid 单独检查引用；两者都满足才计入 classification_match。原文允许合并/分别授标且无法确定固定标包的样本仅比较采购组件，lot_grouping_scored=false，不声称标包预测通过。

锚点匹配要求同轨、同物理页及完整标注片段；同一事实使用另一处原文或另一合理片段可能不匹配，因此锚点覆盖既不是语义正确率，也不是全文召回率。未标注事实不计为误报。空语料、身份变化、伪造标注和缺运行元数据会拒绝；候选引用无效时单独计数，不删除错误来提高结果。

所有模型结果需要另外检查适用条件、表头/续表、复选框、权重与分值，以及“投标无效”“招标失败”“履约违约”的区别。原生文字解析保守保留图像/空页警告，实际OCR质量不在本次测试范围内。

此外本机保留一份中文映射损坏PDF和一份不完整技术附件作为人工诊断材料，未纳入10份计分集，不把它们算成分类成功或OCR成功。
