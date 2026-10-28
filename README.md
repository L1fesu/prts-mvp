# PRTS MVP

自动汇总 [ZOOT-Plus/zoot-plus-store](https://github.com/ZOOT-Plus/zoot-plus-store) 中公开作业 JSON 的干员使用次数，并发布为静态 GitHub Pages 页面。页面支持按作业编号范围及一级目录类型筛选。

## 更新

GitHub Actions 每周一 00:00 UTC 查询上游默认分支的最新提交。发现提交 SHA 变化后，工作流会稀疏检出上游 `作业/` 目录，运行 Python 脚本生成 `public/index.html`，复制 favicon，并部署到 GitHub Pages。上游仓库无需配置 webhook 或授予本仓库权限。也可以从 **Actions** 手动触发检查。

为避免重复构建，工作流将最后处理的上游提交记录在 `state/upstream-sha.txt`。Actions bot 会在检测到上游更新时自动提交该文件的变更。定时检查本身会运行，但上游未变化时不会重新构建或部署。

## 说明

本仓库的统计脚本及工作流以 MIT License 发布。上游作业数据及相关名称、标识及内容的权利归其各自权利人所有；本项目与鹰角网络及《明日方舟》官方无关。统计结果仅供参考，数据准确性以来源仓库为准。
