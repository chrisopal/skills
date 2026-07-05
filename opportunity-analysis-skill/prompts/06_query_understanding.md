# 自然语言查询转Query JSON Prompt

将用户查询转换成受控Query JSON，不得直接输出SQL。

例：
用户：查询最近需要跟进的高分商机。
输出：
{
  "query_type": "opportunity_search",
  "filters": {"min_score": 70, "next_action_status": "open"},
  "sort": {"field": "score", "order": "desc"},
  "limit": 20
}
