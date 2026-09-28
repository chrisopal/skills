# 中文 AI 实用书稿编辑 · v1.2.0

本版保留全书结构、事实、案例状态与教程可用性审读，增加作者指定的中文表达规则。默认减少“下一步最值得做的”“最值得记住的几点”等评价式铺垫，直接说明问题、检查对象、动作及条件；不把所有句子统一换成“重点聚焦”。

## 文件与使用

完整使用时，把整个 `ai-practical-book-editor` 文件夹提供给支持目录型Skill的宿主。入口是 `SKILL.md`，语言规则在 `references/neutral-professional-chinese.md`，逐章意见格式在 `templates/chapter-revision.md`。不提供模型、账号或连接器。本次没有在用户的任何客户端中安装或验证导入。

只支持附件输入时，可提供上述三个文件和书稿，要求先读规则再处理。主文件能说明核心要求，完整包还包含保真、长稿与教学参考。

### 只要逐章意见

```text
先读取 ai-practical-book-editor/SKILL.md 与 references/neutral-professional-chinese.md。
以 chapter-revision 模式处理本次书稿，先审不改。
采用自然、直接的专业讲解，减少评价式导语、心得模板和重复收尾。
逐章给原句位置、建议写法、理由与保持项；没有问题允许保留。
历史提示词、代码、数据与字段名不自动改写。
图片和练习附件未随稿提供，不评价未见内容，不断言原书缺少。
输出逐章修改意见，不覆盖原稿。
```

### 按意见修改指定章节

使用 `templates/revision-task.txt`，再附当前原稿、意见稿和需处理章节范围。该模板是本版新整理的任务写法，不是历史执行实录。原句不匹配时重新定位，不按过时行号直接修改。

## 配套检查

可选脚本仅盘点指定Markdown的章节、附录、块类型和字面词频，无需第三方依赖。命中不是错误，更不是AI作者概率；不自动替换任何文本。Python 3.10及以上：

```bash
python scripts/audit_inventory.py manuscript.md --output inventory.json
python -m unittest discover -s tests -v
```

输出已存在则拒绝覆盖。盘点不等于阅读。确定性测试和语义评测分开记录，当前执行范围见 `VALIDATION.md`。
