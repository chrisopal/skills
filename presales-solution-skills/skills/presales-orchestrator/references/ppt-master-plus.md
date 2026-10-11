# 本地 ppt-master-plus 接入

本参考描述售前与PPT之间的接口；制作步骤以当前安装的 `ppt-master-plus/SKILL.md` 为准。首轮验证环境为4.5.0，不把本机路径、模板或Python版本写成全局硬依赖。

## 准备输入

先定位并读取本地技能入口，检查它要求的已有运行环境；不要为了猜测的依赖自动安装整套工具。用户改选PPT技能时保持同一内容交接边界，读取实际新入口。

```bash
python3 "$RUNTIME" prepare-ppt "$PROJECT" CONTENT --out "$PROJECT/ppt-handoff"
```

此命令只在当前内容及其依赖有效、独立内容审核pass时生成白名单Markdown和handoff.json。保留上屏文字、讲稿、来源、锁定陈述、可见限定与图规格；不转发内部销售判断、联系方式或完整内部台账。**以命令实际输出路径为准**，不要猜文件名。

制作方接收：上述Markdown、实际授权素材、受众/用途/时长、页数和明确的制作授权。缺素材用显式待补标记，不能让PPT Skill补业务事实。

## 执行本地技能

1. 在PROJECT中独立建PPT工作目录；不要向安装目录写项目输出。
2. 按本地skill完成规格、执行锁、模板/素材选择、页面、备注及质量门槛。用户已有明确授权时沿用，不构造虚假UI确认结果。
3. 遵守其页面编写和导出要求；本套件不绕过检查器，也不替它批量生成SVG。
4. 修改排版可以自主进行；改事实、范围、关键论点、页数或限定须返回内容包更新修订并重审。
5. 实际生成PPTX后，用可用Office/PDF渲染能力打开检查全部页。原生对象、SVG、整页图片是不同编辑性，按实际结果报告。

本机曾遇默认Python无Flask、LibreOffice替代微软雅黑并引入换行。选择已有可运行环境和PowerPoint原生导出解决了该次验证；不能据此保证所有机器/文件都兼容。没有可用渲染器时，保留PPT与结构检查，delivery审核不能谎称视觉pass。

## 登记真实交付

将实际PPTX、PDF和渲染检查记录放入PROJECT（路径相对PROJECT，无越界）。review证据文件应列出渲染器、全部实际页图路径/hash、检查人、每页观察及未检查项；截图路径本身不等于看过图。

渲染记录必须使用以下字段，每页一项；image_path相对PROJECT，sha256从实际页图计算。所有页verdict为pass且native_review为pass时，交付审核才允许pass。

```json
{
  "renderer": "实际应用与版本",
  "reviewer": "实际检查人",
  "pages": [{
    "page": 1,
    "image_path": "reviews/render/page-01.png",
    "sha256": "真实完整hash",
    "verdict": "pass",
    "observations": "已实际查看的内容、限定、布局与备注核对结果"
  }]
}
```

delivery envelope的inputs绑定内容包，data如下：

```json
{
  "pptx_path": "deliverables/solution.pptx",
  "pdf_path": "deliverables/solution.pdf",
  "input_content_id": "CONTENT",
  "input_content_sha256": "真实完整hash",
  "page_map": [{"slide_id": "SLIDE-01", "page": 1}],
  "render_evidence_path": "reviews/render-review.json",
  "native_review": {"status": "pass", "method": "实际渲染器及检查方法", "reviewer": "实际检查人"}
}
```

runtime登记时读取实际PPTX的页数和文件hash；语义审核还要核对页序、文字、图形、锁定口径、可见限定、备注及使用范围。页数一致不能证明内容一致。

之后用 `presales-solution-review` 的delivery模式审阅。review inputs绑定DELIVERY，data附与delivery一致的file_hashes；若实际文件或渲染记录变更，旧审核失效。报告真实编辑性、输入内容包版本、模板、文件位置与剩余限制。输出本地文件不代表已外发或客户验收。
