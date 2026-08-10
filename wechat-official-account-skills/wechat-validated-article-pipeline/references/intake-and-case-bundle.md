# 输入与 Case Bundle 合同

## 八项输入

| 字段 | 要回答的问题 | 最低要求 |
|---|---|---|
| 文章目标 | 这篇文章要解决什么问题？ | 一句话、可判断完成 |
| 目标读者 | 谁最应该读？ | 具体角色，不写“所有人” |
| 读者动作 | 读完后做什么？ | 一个判断或行动 |
| 核心观点 | 文章要证明什么？ | 可证伪，不写口号 |
| 底层逻辑 | 方法由哪些步骤和判断组成？ | 可执行 SOP 或逻辑链 |
| 真实场景 | 在什么工具和环境里验证什么？ | 有真实环境、步骤与结果 |
| 材料环境 | 有哪些来源、账号、工具和限制？ | 路径/URL、来源状态、敏感边界 |
| 验收边界 | 什么算验证完成，最终保存到哪里？ | 验收标准 + 只存微信草稿 |

## 默认文件

在内容工作区使用：

```text
operations/<slug>-case-bundle.json
```

不要把 AppSecret、access token、Cookie 或个人账号信息写进 bundle。

## 顶层字段

```json
{
  "schema_version": "1.0",
  "topic_id": "TOPIC-001",
  "request": {},
  "logic": {},
  "scenario": {},
  "materials": [],
  "evidence": {},
  "article": {},
  "wechat": {}
}
```

### request

```json
{
  "objective": "写一篇读者可照做的 AI PPT 实战文章",
  "target_reader": "需要交付产品介绍 PPT 的产品经理和顾问",
  "reader_action": "用统一 brief 和验收门完成一次真实生成",
  "core_claim": "质量差距首先来自 SOP 和验收，而不只是模型"
}
```

### logic

```json
{
  "methodology": ["主题", "观众", "材料", "大纲", "故事线", "内容契约", "生产", "验收"],
  "storyline": ["底层逻辑", "公开路线比较", "真实案例", "可复用 SOP"]
}
```

### scenario

`steps` 和 `acceptance_criteria` 在 intake 阶段允许使用 `pending`；进入 evidence 阶段时必须全部为 `passed`，且都要绑定已有 `evidence_ids`。

```json
{
  "name": "在真实工具里生成并验证一个产品介绍 PPT",
  "actual": true,
  "environment": "已配置模型的桌面环境",
  "steps": [
    {
      "id": "S01",
      "action": "安装或更新目标 Skill",
      "status": "pending",
      "evidence_ids": []
    }
  ],
  "acceptance_criteria": [
    {
      "id": "A01",
      "criterion": "输出文件可以重新打开，关键页面可读",
      "status": "pending",
      "evidence_ids": []
    }
  ]
}
```

### materials

长文在 evidence 阶段至少要有五条 `verified` 材料。材料可以是用户文件、真实操作观察、官方文档、官方仓库、接口回读或可复核截图。

```json
{
  "id": "M01",
  "kind": "user-material | official-doc | official-repo | observation | readback",
  "path_or_url": "/absolute/path/or/https-url",
  "status": "provided | verified | unverified"
}
```

### evidence

每条证据使用唯一 ID。截图必须完成隐私和错误检查。

```json
{
  "items": [
    {
      "id": "E01",
      "kind": "screenshot",
      "path": "/absolute/path/step-01-public.png",
      "verified": true,
      "privacy_checked": true,
      "error_checked": true
    },
    {
      "id": "E02",
      "kind": "artifact",
      "path": "/absolute/path/result.pptx",
      "verified": true
    },
    {
      "id": "E03",
      "kind": "readback",
      "path": "/absolute/path/result-readback.json",
      "verified": true
    }
  ]
}
```

### article

在微信保存前后补齐：

```json
{
  "markdown_path": "/absolute/path/article.md",
  "html_path": "/absolute/path/article.html",
  "cover_path": "/absolute/path/cover.png",
  "inline_image_paths": ["/absolute/path/step-01-public.png"],
  "review_status": "passed",
  "markdown_link_residue": false,
  "local_path_residue": false,
  "privacy_residue": false,
  "error_residue": false
}
```

### wechat

从 intake 开始就固定草稿边界：

```json
{
  "save_mode": "draft",
  "publish": false,
  "ip_whitelist_checked": false,
  "media_id": "",
  "draft_get_path": "",
  "draft_get_verified": false,
  "status": "READY_LOCAL"
}
```

成功回读后再改为：

```json
{
  "save_mode": "draft",
  "publish": false,
  "ip_whitelist_checked": true,
  "media_id": "MEDIA_ID",
  "draft_get_path": "/absolute/path/draft-get.json",
  "draft_get_verified": true,
  "status": "DRAFT_SAVED"
}
```

## 校验命令

```bash
python3 <skill-dir>/scripts/validate_case_bundle.py bundle.json --phase intake
python3 <skill-dir>/scripts/validate_case_bundle.py bundle.json --phase evidence
python3 <skill-dir>/scripts/validate_case_bundle.py bundle.json --phase draft
```

退出码：

- `0`：当前阶段通过
- `1`：合同或证据不满足
- `2`：文件读取或 JSON 输入错误
