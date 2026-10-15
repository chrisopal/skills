# GTM 运行契约

共享入口 `../opportunity-orchestrator/scripts/run.py`；同一 DB。location仅为经纬度对象，场馆名称放入fit_reason或audience；不把场馆字符串当坐标。`gtm-manage --input change.json --db DB`；`gtm-query --db DB [--campaign-id ID] [--as-of YYYY-MM-DD]`；`gtm-brief --input brief.json`输出检索任务（不访问网络）。数据放用户项目目录。

包络：`{campaign_id,request_id,expected_revision:0,actor,operations:[...]}`。所有写入原子提交、修订号＋1；同请求同正文返回原收据并附当前detail，不同正文拒绝。记录id由调用方提供，最多80字符。来源/对象引用必须属于同计划。复用已有生命周期请求日志，但不改变商机正式状态。

## 操作

- `create_campaign`：`name,product,target_customer,regions:[string],owner,simulation:boolean,currency`。仅新ID；product/target_customer为可读文本。可选`value_proposition,proof_points:[string]`。simulation必须明确，演示互动只能建在模拟计划。
- `upsert_source`：`record:{id,title,url,publisher,accessed_on,claim,verification:official|unverified}`；可选published_on。仅http/https，无凭证链接。official只表示来源类型，不证明需求。
- `upsert_target`：`record:{id,name,region,city,industry,source_ids:[id],fit_reason,fit:{industry:null|0..5,pain:null|0..5,access:null|0..5,evidence:null|0..5}}`；可选`location:{lon,lat,precision:city|site},website,roles:[string],hypothesis`。有引用的目标企业名称不可改为另一企业；修改使用新目标id。城市点位近似标记。
- `upsert_event`：`record:{id,name,kind:exhibition|forum|channel,region,city,source_ids:[id],fit_reason}`；可选`starts_on,ends_on,organizer,location,url,audience`。日期必须成对且有序；渠道可无日期；未知日期保持空。活动有效期按查询as_of派生past/ongoing/upcoming/unknown，channel为ongoing。
- `upsert_message`：`record:{id,title,target_id,channel,role,opening,value,proof,cta,objection,source_ids:[id]}`。只存草稿，不发送。允许target_id为空表示分群话术。
- `record_touch`：`record:{id,target_id,event_id?,channel,occurred_on,outcome:planned|contacted|responded|meeting|qualified|no_fit,summary,evidence,next_action,due_on?,owner,actual_cost?:number,currency?:string}`。实际结果必须有evidence；planned不能有actual_cost。occurred_on/due_on为ISO日期。未来结果会显示但不计实际漏斗、不允许关联；实际统计截至min(as_of,今天)，查询未来截止日也不能把未来结果当实际；历史按实际发生日排序。跟进不可覆盖，同id拒绝。
- `link_opportunity`：`target_id,opportunity_id,touch_id`；touch必须是本目标已经发生、有证据的qualified。商机account.company_name必须与target.name规范化相等（不可自动猜集团/子公司）；允许同企业多商机，一条商机在该计划只能归于同一目标，重复不同来源不覆盖归因。关联保留该touch.event_id为origin_event_id；不创建客户确认或跳阶段。非模拟计划不可使用明确含“模拟”的跟进证据去冒充实际。

## 查询

列表返回`{campaigns:[{id,name,product,target_customer,regions,owner,simulation,currency,revision,...}]}`。

详情返回`{campaign:{...},revision,as_of,sources:[],targets:[],events:[],messages:[],touches:[],links:[],history:[],analytics,search_brief}`。

target派生`fit_score:number|null,fit_coverage:number(0..1),status:candidate|contacted|responded|meeting|qualified|no_fit|opportunity`。不全的评分不输出满分推测；优先分权重industry35%、pain30%、access20%、evidence15%。status根据as_of内最新实际跟进（日期＋登记顺序）或已关联商机；历史漏斗不因no_fit抹掉已发生触达。

link派生`opportunity:{id,company_name,name,current_stage_id,current_stage_name,status,score,signed_amounts:[{amount,currency}],verification_status}`。金额只来自当前有效双方签署记录，不把报价/意向当收入。缺失/损坏原商机返回link_error而不隐藏关联。

analytics：`funnel:{candidates,contacted,responded,meeting,qualified,opportunities,won}`均按目标企业去重，前五项实际里程碑累积；`regions:[{name,candidates,contacted,qualified,opportunities,won}]`；`channels:[{name,touches,contacted,responded,qualified,costs:{CNY:number},missing_cost_count}]`按触达记录与企业去重；`events:[{id,name,targets,qualified,opportunities,costs,missing_cost_count}]`仅已记录活动关联；`costs:{currency:number},missing_cost_count,signed_amounts:{currency:number},unmapped_targets`。成本按实际结果记录，不分摊其他活动，不计算不可证明ROI。无成本记录显示未知而非0，币种分组。

`search_brief:{queries:[{kind:company|event|channel,query,checks:[string]}],missing_inputs:[string]}`依据产品/ICP/区域编写官方资料搜索任务；实际采集由Skill调用可用搜索工具后回写，HTTP不后台调用搜索。

## HTTP

`GET /gtm`；静态`/assets/gtm.js`、`/assets/gtm.css`；复用`/css/default.css`。页面注入`window.WORKBENCH_TOKEN`。

`GET /api/gtm/campaigns` → `{ok:true,campaigns:[...]}`；`GET /api/gtm/campaign/ID?as_of=...` → `{ok:true,detail:...}`；`POST /api/gtm/manage` → `{ok:true,campaign_id,revision,detail,...}`，需当前Origin、Host、X-Workbench-Token；400中文业务错误，409修订冲突。浏览器不可传本机路径。现有`GET /api/opportunities`可选关联目标商机，现有`/?opportunity_id=ID`打开原商机（若原页面不处理query，需由导航入口补齐）。

## 中国省市沙盘

本地 `/assets/china-map.json` 保存34省级区域、多边形与南海边界细节、475个下辖单位名称/近似中心点及来源日期。`gtm-map.js`只负责投影、行政区导航、城市筛选与对象显示；不改商机事实。全国标省名，省内标地级市/自治州/盟/地区/省直辖单位，直辖市和港澳显示区；台湾市县点位暂无来源。未知坐标仍在列表。城市匹配先用主体区域/城市名称，必要时以坐标落区，不能推导完整行政地址。

`opportunity-analysis-skill/scripts/sync_china_map.py` 可显式刷新公开来源；下载/范围异常应保留已有本地资产，审阅数据后再发布。运行工作台无需访问外部地图服务。
