# 受控 PaddleOCR 补读

本套件的 OCR 是一个显式启用的补读路径。`extract_sources.py` 默认只做本地原生提取，不访问网络；只有传入 `--ocr paddle-service` 时，才会把选定的扫描页或图像页渲染为 PNG，逐页提交给已部署的 PaddleOCR `/ocr` 服务。OCR 结果仍是 `needs_review` 范围内的证据，不构成业务验收或真实材料认证。

## 服务协议

脚本按 PaddleOCR Serving Pipeline 的 OCR 接口提交 JSON：

```json
{"file":"<base64 PNG>","fileType":1}
```

响应必须包含 `result.ocrResults`，且每次逐页提交只能有一个结果。结果中必须有 `prunedResult.rec_texts`、`rec_scores` 和 `rec_polys`，三个数组长度必须一致且不能为空。异常、空结果、数量不匹配和字段不完整都会将本次产物保存为 `blocked`；已成功读取的页仍会保留，方便人工续查。低于最低置信度的页保留 OCR 文字并标记 `needs_review`。

官方协议参考：[PaddleOCR OCR pipeline serving usage](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md)。本套件只依赖 HTTP 协议，不在项目环境安装 PaddleOCR 模型或 Python 推理依赖。

## 自托管与远程服务

需要本地部署时，按 PaddleOCR 官方文档安装匹配版本的 PaddleOCR、模型和 serving 组件，再启动一个由宿主配置的 `/ocr` HTTP 服务。模型下载、GPU/CPU 选择、端口和进程托管属于宿主运维范围，不能由本脚本推断或自动安装。请先用协议测试服务确认请求和响应结构，再接入真实资料。

在独立推理环境完成对应操作系统的 [PaddlePaddle / PaddleOCR 安装](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/installation.md) 后，官方基础服务启动命令为：

```bash
paddlex --install serving
paddlex --serve --pipeline OCR
```

服务默认监听 8080；客户端配置 `BID_OCR_API_URL=http://127.0.0.1:8080/ocr`。设备、模型目录和监听配置按 [官方服务部署说明](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/inference_deployment/serving/serving.en.md) 调整。开源自建服务本身不要求购买 Key；远端托管或有鉴权的部署才配置提供方签发的 Key。本轮未安装或启动推理服务。

也可以使用用户已经部署的 PaddleOCR `/ocr` 服务。服务地址、鉴权名称和密钥由服务提供方确认；不要把通用官方托管作业接口推断为本协议的 `/ocr` 接口。远程服务必须使用 HTTPS，并且必须显式传入 `--allow-remote-ocr`；本机 `localhost`、`127.0.0.1` 和 `::1` 回环地址可以使用 HTTP，且不强制密钥。URL 不得包含用户名、密码、查询参数或片段，重定向会被拒绝。

## 配置与命令

```bash
export BID_OCR_API_URL=http://127.0.0.1:8080/ocr
export BID_OCR_API_KEY='宿主提供的密钥'       # 可选，不要写进 URL
export BID_OCR_API_AUTH_SCHEME=bearer        # bearer 或 token；默认 bearer
export BID_OCR_MIN_CONFIDENCE=0.80           # 可选，默认 0.80

python scripts/extract_sources.py \
  --project ./my-bid \
  --project-id BID-001 \
  --source-id SRC-003 \
  --ocr paddle-service \
  --out my-bid/artifacts/01-source-intake-r2.json
```

远程服务示例：

```bash
export BID_OCR_API_URL=https://ocr.example.test/ocr
python scripts/extract_sources.py --project ./my-bid --project-id BID-001 \
  --ocr paddle-service --allow-remote-ocr \
  --out my-bid/artifacts/01-source-intake-r2.json
```

`--source-id` 可重复，适合只补读已登记的供应商材料。PDF 对文字稀少、编码异常或图像页执行强制 OCR；原生文字充分但带有图片（例如小 logo）的数字 PDF 会执行补充 OCR。强制 OCR 失败会阻塞产物并保留已成功页；补充 OCR 失败会保留完整原生文字，将来源和页面标为 `needs_review`、coverage 设为 `partial` 并写入 warning，不能把图像区域当成已验证。PNG/JPEG 在显式 OCR 模式下作为第 1 页提交。完整原件路径、字节数和 SHA256 会继续保存在文档与 `inputs` 中，页码和 OCR 方法、置信度会保存在 `data.page_audit`，OCR 文本块的 `method` 为 `ocr`。

如果筛选结果为空（例如 `--source-id` 没有匹配待登记材料），脚本仍会在显式 OCR 模式下本地校验服务配置，但不会提交任何图像，会保存空范围的 `blocked` 结果且不会发起网络请求。

每次输出必须使用不存在的新文件名。脚本只在当前项目的 `artifacts/` 中查找同一 `project_id` 和 `artifact_id` 的 JSON 历史，拒绝跨项目、无效或重复 revision。默认使用最高 revision 加一；也可以用大于当前最高值的 `--revision N` 明确指定，或用当前项目内的 `--previous path/to/old.json` 绑定一份有效旧产物。仅更换文件名不会把同一产物伪装成新版本。

## 验证边界

`tests/test_ocr.py` 使用本地协议测试服务器，覆盖 URL/auth、无重定向、超时和错误信息脱敏、PNG 载荷、真实 PyMuPDF 渲染页、数字 PDF 小图补充 OCR 失败、来源过滤、hash/revision、低置信度和部分失败保留。它验证的是本地协议和证据状态；真实 PaddleOCR 模型识别质量、字体/语言效果、吞吐和远程部署可用性在配置真实服务前均为 `NOT_RUN`。
