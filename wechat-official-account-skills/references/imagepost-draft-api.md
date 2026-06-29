# WeChat 图片消息草稿接口笔记

本文件只记录当前闭环需要的高价值约束，避免每次重读整套微信文档。

## 目标

把 `工业AI日报` 的重点案例保存成微信公众号待审核草稿，优先支持：

- `图片消息`（`article_type=newspic`）
- 必要时补一份 `图文消息`（`article_type=news`）用于保留更丰富的链接和说明

## 官方接口

以下均来自微信官方服务号文档：

- 新增草稿：`POST https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN`
- 上传图文消息图片：`POST https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=ACCESS_TOKEN`
- 上传永久素材：`POST https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=ACCESS_TOKEN&type=image`

官方文档页：

- [新增草稿](https://developers.weixin.qq.com/doc/service/api/draftbox/draftmanage/api_draft_add)
- [上传图文消息图片](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_uploadimage)
- [上传永久素材](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial)

## 已确认的关键约束

### 1. 草稿类型

`article_type` 支持：

- `news`：图文消息
- `newspic`：图片消息

不填默认 `news`。

### 2. `newspic` 能力边界

官方文档明确写到：

- 图片消息正文仅支持纯文本和部分特殊功能标签
- 不应按普通 HTML 图文文章能力来假设

这意味着：

- `newspic` 不适合作为“多段富文本 + 多个内嵌可点击外链”的完整替代
- 如果业务上必须保留完整来源链接和 richer copy，应同时保留 review bundle 或 companion `news` draft

本地接口实验：

- 2026-06-21 用 `article_type=newspic` 测试提交 `<strong>` 和 `<a href="...">` 到 `content`
- `draft/add` 返回 `errcode=45166`，`errmsg=invalid content`
- 结论：`newspic` 不能用普通 HTML 链接或 HTML 加粗来模拟后台编辑器里的富文本效果
- 后台编辑器的“内容链接”按钮可能是微信后台私有的特殊组件；除非通过 `draft/get` 反查到保存后的真实结构，否则不要在 API 侧假设其格式

### 3. `newspic` 图片结构

图片消息使用：

- `image_info.image_list[]`
- 每项需要 `image_media_id`
- 图片最多 20 张
- 首张图默认作为封面图

所以闭环里最稳的路径是：

1. 本地生成图片
2. 上传为永久图片素材，拿到 `media_id`
3. 组装进 `image_info.image_list`
4. 调 `draft/add`

### 4. `news` 封面图要求

普通图文消息需要：

- `thumb_media_id`
- 且它必须是永久素材 `MediaID`

### 5. `news` 正文图片要求

普通图文正文中如果嵌图，图片 URL 需要来自：

- `media/uploadimg`

外部图片 URL 会被过滤。

## 对本 skill 的设计影响

### 推荐默认策略

当用户说“发贴图”时：

1. 主产物：单篇 `newspic` 草稿，一次挂载多张案例图
2. 辅助产物：本地 `case-review.md`，保留完整链接和审稿说明
3. 如明确需要可点击链接版本，再额外生成 `news` 草稿
4. 标题必须控制在 20 字以内，默认用 `工业AI日报 MM-DD` 或 `每日工业AI MM-DD`

### 为什么这样设计

- `newspic` 更符合“像小红书一样的贴图内容”
- 但链接能力更弱
- `news` 更适合承载完整说明和链接
- 双产物最稳，不牺牲用户审核体验

## 建议的 bundle schema

传给 `wechat_imagepost_draft_api.py` 的 bundle 可使用：

```json
{
  "draft_type": "newspic",
  "articles": [
    {
      "article_type": "newspic",
      "title": "工业AI日报 06-21",
      "author": "智能体架构笔记",
      "digest": "AI 不只在办公提效，正在进入制造、机器人、能源平台、服装装备和矿业研发。",
      "content": "工业AI日报 06-21\n\n【今日概览】\n今日概览......\n\n【01｜Coherent × NVIDIA】\n案例短评......\n来源：\nCoherent 公告：https://...\n\n【我的观点】\n......",
      "image_paths": [
        "assets/wechat/2026-06-21-case-01.png",
        "assets/wechat/2026-06-21-case-02.png",
        "assets/wechat/2026-06-21-case-03.png"
      ],
      "need_open_comment": 0,
      "only_fans_can_comment": 1
    }
  ]
}
```

脚本负责把：

- `image_paths` -> 上传永久图片 -> `image_info.image_list`
- `content` 中误写成字面量的 `\\n` -> 真实换行，避免微信编辑器显示乱码

正文建议：

- 图片消息正文按纯文本处理，不依赖 Markdown 或 HTML 渲染；后台预览会按正文原样显示
- 案例序号使用可见纯文本分隔：`【01｜企业 / 案例名】`
- 来源使用命名 URL 行：`来源名：https://example.com`
- 如果必须保留可点击链接，应额外生成 companion `news` 草稿或在本地 review bundle 保留完整链接清单

## 当前机器上的已知凭证入口

当前你给出的可复用公众号凭证位置是：

- `/Users/guojiexie/content-mgmt/.env`

已确认字段名：

- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`

因此 image-post helper 应优先兼容这两个字段名，不要强行要求另一套 `WECHAT_OA_*` 命名。

## 当前机器上的已知现成脚本

`/Users/guojiexie/content-mgmt/scripts/wechat_draft_api.py`

这套脚本已经覆盖：

- `check-token`
- `upload-cover`
- `create-draft`
- `update-draft`

定位：

- 它更适合普通 `news` 图文草稿
- 本 skill 新增的 `wechat_imagepost_draft_api.py` 更适合 `newspic` 图片消息草稿

推荐做法：

1. `news` 复用 `content-mgmt/scripts/wechat_draft_api.py`
2. `newspic` 使用本 skill 的 `wechat_imagepost_draft_api.py`
3. 两者共用 `content-mgmt/.env`

## 审核输出建议

至少返回：

- 草稿类型
- 草稿 `media_id`
- 每个案例标题
- 每个案例图片路径
- 每个案例来源链接
- 是否只保存草稿未发布

## 未确认项

- 某些账号能力、白名单、内容安全策略，可能影响图片消息字段兼容性
- 当前账号是否允许所有 `newspic` 扩展能力，需以真实接口返回为准
- `newspic` 中是否存在当前账号专属可点击能力，未在本轮核验

遇到这些情况时，要在结果里明确写 `未确认`，不要自行脑补。
