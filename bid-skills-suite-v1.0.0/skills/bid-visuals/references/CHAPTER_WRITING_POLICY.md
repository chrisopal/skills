# 章节篇幅、详细程度与界面图

总控执行目录规划或分章写作时读取本规则。设置保存在项目work/writing-settings.json；可在编辑器“写作设置”保存，或由宿主对话定位真实章节ID后保存。设置本身不调用模型、生成图片或更新已有Word/PDF。

| 字段 | 默认 | 含义 |
|---|---|---|
| length_mode | auto_scoring | 按方案评分与需求复杂度推荐；fixed使用统一目标 |
| target_words | null | 基准字数；自动模式留空取1000，固定模式留空不设目标 |
| length_tolerance | 0.2 | 目标容差，0—0.5 |
| chapter_overrides | {} | 按08稳定section_id逐章覆盖；未知ID拒绝保存 |
| chapter_overrides.ID.target_words | null | 明确目标，例如500、1000、2000，优先于全局/推荐 |
| chapter_overrides.ID.detail_level | auto | auto、brief、standard、detailed |
| chapter_overrides.ID.ui_required | null | null继承、true要求界面图、false免除用户偏好；原文强制图仍需落实 |
| chapter_overrides.ID.min_ui_images | 继承 | 本章最低界面图数，1—8 |
| visuals.system_ui_policy | auto | auto遵守任务卡；all_system_sections识别系统功能章；off关闭自动追加 |
| visuals.min_ui_images | 1 | 每个适用章最低界面图数，1—8 |
| visuals.max_images | 2 | 每次生图上限1—8，整本分批；不是全书图片上限 |

```json
{
  "length_mode": "auto_scoring",
  "target_words": 1000,
  "length_tolerance": 0.2,
  "chapter_overrides": {
    "SEC-OVERVIEW": {"target_words": 500},
    "SEC-WORKORDER": {"target_words": 2000, "detail_level": "detailed", "ui_required": true, "min_ui_images": 2}
  },
  "visuals": {"system_ui_policy": "all_system_sections", "min_ui_images": 1, "image_mode": "host", "max_images": 2}
}
```

示例合并到已有设置，实际ID取08；保存带当前revision和sha256。宿主接收“9.3写2000字，各系统功能章至少1张界面示意”时先定位稳定ID再保存，不只放聊天记忆。修改设置重新冻结评审输入，旧审核不能复用。

## 推荐与执行

运行`scripts/writing_policy.py --project /absolute/project --out work/writing-policy.json`生成全部章节建议与实际检查。建议基于04的scored叶子、08绑定及父章继承，保留原规则与继承标记，不累计rollup，不把合同履约评分当投标评分。方案项至少20分或达到本项目方案类最高分的80%，以及本章至少8条需求时建议detailed；brief/standard/detailed分别取基准的0.5/1/2倍，普通方案评分章建议基准的1.5倍。未知评分条件由宿主回查。固定函件/表格不凑推荐字数；明确的用户目标单列检查，原文格式冲突交宿主解释处理。

资质/业绩/数量证明和价格评分优先检查有效材料与公式，高分不自动扩写。方案正文按对应条件展开机制、实施步骤、异常处理、证据、验收与边界；详细不等于重复背景。脚本不证明专业性或得分，15仍逐项读取原文、正文及材料。

workspace.state提供chapter_policy；每次分章task.json保存resolved_policy。子Agent依该章目标与展开要求写独立提案；协调者检查不足，按失败章限次整改/回收，成功章不全部重跑。字数是可见正文字符，剔除Markdown图片、链接地址、代码块、HTML属性和空白，包含标题及表格文字；不是token或Microsoft Word统计值。

## 界面图及门禁

all_system_sections结合标题、任务及绑定需求识别工单、告警、查询、处置等系统功能，排除纯架构、网络、部署、培训等章节。它是可覆盖的建议，不宣称完整语义识别；漏识别的功能需补任务卡。原文明确要求不得通过用户偏好免除。

13使用kind=interface登记界面设计示意，Codex由Imagegen Skill驱动实际工具，WorkBuddy使用该宿主真正开放的生图Skill。按每次上限分批，为适用章节生成页面；图注保留“界面设计示意，非实际系统截图”。真实截图只使用授权材料并交15核验。技术图继续SVG/Draw.io等路径，不能抵充界面图；已有concept且明确为界面示意的有效产物也可计入。

writing_checks检查当前正文、13章节绑定、图片解码、正文插图路径与独立图片哈希。未渲染、未插正文、损坏、重复或技术图替代不能满足最低张数；它不认证画面功能/真实性或Word/PDF入图，仍须13/14/16打开实际图与导出页。

草稿允许保存。推荐字数偏离只提示；明确章节/固定全局目标及必配图缺失进入blocking_issues，15及正式导出门禁复核。关闭生图与必配冲突保留缺口，不静默降级。字数/图片符合不等于评分满足或真实投标可递交。

## 编辑器检查展示

右侧检查按“需整改、建议调整、无缺口”分组，默认展开需整改章节。分组按实际blocking_issues和issues判断，章节数与必改项数分开；同一章可同时存在必改的缺图与建议的篇幅偏离，建议不计为必改项。每章分开显示实际可见字数、目标范围、需补/建议补/超出字数与已渲染并插入的界面图数量；章节标题可跳转，检查依据可用键盘展开。无缺口仅表示这两项检查，不代表评分、证据或正文审核通过；未设目标仍明确标注。

历史图源缺少CLI渲染记录时，显示图名、“记录待补”与图源入口，原始诊断完整保留在“查看原始提示”。改善展示不补造审计记录，也不将已有图源视为已通过工具执行审计。其他错误和警告继续显示原有内容与级别。
