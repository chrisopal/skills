# 商机后续重点：方案联动、评分溯源、竞争台账与录入

## 范围与决策
继续已确认的四项重点，沿用七个Skills和SQLite主账，不增加依赖，不扩展成独立CRM。先让同一个案例的资料、判断、评审和方案版本可操作、可回读。

- 评分保留既有算法，开放持久化assessment历史及逐维依据、来源、评级变化；未知值不冒充证据，不将启发式分值称为统计赢率。旧记录可读，不补造旧证据。
- `record_competitor`写入`lifecycle.competitors`：competitor_id/name/position/strengths/weaknesses/response/status(confirmed|reported|unknown)/evidence，附可选price_amount/currency。更新同ID追加历史；价格传闻与已确认报价分开。录入竞争情报不会直接改变评分，须带来源重分析。
- 售前桥接导出明确白名单材料到真实presales项目；回收仅接受当前有效delivery及其实际PPTX和绑定审核，作为商机solution版本登记，保留内容/交付hash与用途。生成、文件审核、客户认可仍分开。使用既有ppt-master-plus制作，不另造渲染器。
- 本地录入采用Python标准库HTTP服务和原生HTML/CSS/JS，绑定127.0.0.1。复用run_analyze/run_manage/get_opportunity_detail，写入沿用request_id/expected_revision。会话令牌、Origin/Host检查、有限请求体、禁止任意文件读取；无远程多用户或身份认证声明。冲突显示并要求刷新，不自动覆盖。

## 接口与分工
运行层负责storage/lifecycle/schemas/详情报告及测试：`detail.assessment_history`按时间含维度及相邻变化；`lifecycle.competitors`含稳定记录及history。
工作台负责独立`workbench.py`与assets及HTTP测试；父任务接CLI `serve`、桥接脚本、案例/文档/整体验证。并行编辑不修改他人文件。

## UI Blueprint
工作台入口为商机列表→商机详情。页首客户/商机、正式阶段、修订号，展示最新评分与三组雷达沿用现有报告。主要操作“新增拜访/反馈”；详情操作区为资料、竞争情报、跟进行动、客户评审、阶段变更。评分历史及竞争台账读真实主账。表单始终有标签、来源/责任人/期限，成功刷新主账，失败保留填写，冲突不覆盖。无虚构搜索、审批、通知。

沿用enterprise蓝色语义和亮暗主题，扁平连续表格，主按钮实心蓝、次按钮有边框。长标识符折叠，表格在容器内滚动，390px单列。支持键盘、loading/empty/error/success/disabled状态。此服务仅本机编辑，历史静态案例仍可查看。

## 验证与交付
先保持79项既有测试，再覆盖评分重启回读/证据与变化、竞争历史/错误来源回滚、HTTP写入回读/冲突/恶意Origin和路径、售前实际项目导出与PPT回收/上游变化拒绝。完整12点案例改为主账竞争记录；实际PPT回读及渲染和真实浏览器亮暗/桌面/390操作验证分开记录。截图/DB/PPT/临时成果留本地，源码与文档Lore提交推送并合入main，同步已安装Skill源。
