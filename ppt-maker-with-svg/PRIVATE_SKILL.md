# PPT Master Plus 已迁移至私有仓库

自 2026-10-12 起，`ppt-master-plus` 由独立私有仓库维护：
[https://github.com/chrisopal/ppt-master-plus](https://github.com/chrisopal/ppt-master-plus)。
访问和克隆需要该仓库的 GitHub 权限；公开 Skills 仓库的权限不会自动授予访问权。

## 安装并保留原路径

在本 Skills 仓库根目录运行以下命令，目标目录必须尚不存在：

```bash
gh repo clone chrisopal/ppt-master-plus ppt-maker-with-svg/skills/ppt-master-plus
python3 ppt-maker-with-svg/skills/ppt-master-plus/scripts/attribution_guard.py
```

阅读私有目录内的 `INSTALL.md` 和 `SKILL.md`，使用 Python 3.10+ 与实际功能所需依赖。
若该路径已有本地副本，先保留项目输出与自有修改，再选择迁移或更新，不要直接覆盖。
本次迁移保留已有本地副本，公开仓库通过 `.gitignore` 忽略整个目录。
此目录应作为独立 Git 仓库更新和提交；不要使用 `git add -f` 将其重新纳入公开仓库。

## 版本与可见性

私有仓库 `main` 保留原公开默认分支的完整 Skill 内容；
`archive/pre-split-workspace` 保留迁移时另一种开发版本。两个初始提交的根树分别
与原目录 Git 子树一致，未导入无关 Skills 的历史。

迁移从公开分支的最新版本移除该目录，并添加忽略规则；不会改写过去的公开提交。
旧提交、已有分叉和下载副本仍可能访问，不能将本次迁移描述成历史内容已撤回。
如需清理公开历史，应单独评估所有引用、分叉与缓存的处理范围。
