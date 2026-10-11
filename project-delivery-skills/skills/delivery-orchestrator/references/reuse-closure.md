# 收尾与复用契约

版本 0.3.0。继承[共享产物契约](artifact-contract.md)的 Envelope、精确引用和不可变修订；第一、二批契约继续有效。本文适用于 `closure`、`profile`、`template_mapping`、`exchange` 及只读组合视图。所有行使用非空、唯一、稳定的 `id`；引用含 `artifact_id/revision/sha256`，并在 `inputs` 的传递依赖范围内。

## 收尾与质保：closure

同项目只有一个收尾主账。data 字段如下；日期用 `YYYY-MM-DD`，未知用 null，不能以今天替代未知。

| 字段 | 内容 |
|---|---|
| origin、as_of | actual/simulation；真实截止日不得晚于当前 UTC 日期，模拟来源仅用于 simulation 项目 |
| obligations | id/title/category/owner/state/due_date/evidence_refs/recipient/receipt_refs；state=open/transferred/closed |
| warranty | applicable/reason/owner/start_date/end_date/terms_refs/transfer_refs/items；items 每行 id/title/owner/state(open/closed)/evidence_refs |
| administration | state=open/closed、decision_refs |
| settlement | state=open/reconciled、evidence_refs；不执行付款、开票或确认收入 |
| resources | id/owner/state(retained/released)/reason/evidence_refs |
| archive | id/artifact_ref/owner/classification/retention_until；绑定真实业务产物 |
| lessons | id/observation/action/owner |

closed 义务和质保事项须有 evidence_refs；transferred 义务须有 recipient 和 receipt_refs。administration.closed 须有决定证据，settlement.reconciled 须有核对证据。retained 资源须说明原因，released 须有交还/释放证据。适用质保须有主责人和合同条款；不适用质保同样须有 reason 和 terms_refs，不能用“无质保”文字豁免合同义务。

引用种类：terms_refs 接受 contract/change/milestone；decision_refs 接受 minutes/change/review/confirmation/kickoff/weekly；receipt_refs、transfer_refs 接受 evidence/confirmation/milestone/handover/minutes。普通 evidence_refs 接受 source/evidence/minutes/milestone/confirmation/review/testing/release/handover/contract/change。归档绑定合同、需求、设计、计划、工程工作包、测试、上线、培训移交等业务产物，不能用任意 source 代替成果归档。

snapshot.gates 按收尾 artifact_id 返回四个独立结果：

| 结果 | 含义 |
|---|---|
| administrative_closed | 行政决定和结算核对完成，无 open 遗留义务；已移交义务仍可存在 |
| warranty_transferred | 适用质保有移交证据；不适用须已通过合同依据检查 |
| warranty_ended | 适用质保日期明确且已到期，无开放质保事项；未来截止日不制造真实结束事实 |
| fully_discharged / ready | 同时满足行政、质保及全部义务解除条件，无 transferred 遗留义务/保留资源，期限与非空归档完整 |

Envelope 的 status=ready 表示底稿可用；gate.ready 表示登记的全部解除条件通过，仍不认证事实真实性。依赖须 current，才能给出肯定门槛。行政结项不等于全部义务解除；验收签署不替代质保到期或财务执行。修订不得删除既有义务、质保、资源与归档行；closed→非closed 须有 correction_reason 与 evidence_refs。质保 applicable=true→false 须有 correction_reason 和新的 terms_refs；保留原修订供追溯。

正向完成依据必须 ready。confirmation 须 accepted 且无未决条件，review 须 pass，change 须 approved，handover 须 operations.accepted 且无 open_items；拒绝/有条件/未完成记录不能证明关闭或成功移交。原件、纪要及自然语言内容仍由业务审核，工具不能从文本认证实际签收或财务结清；缺主账/凭据或有已知结算差异时须保持 settlement.open。

## 项目配置：profile

data 必含 billing_mode(fixed/time/mixed)、delivery_mode(staged/iterative/mixed)、streams、terms_refs、open_items。stream 每行含 id/mode(fixed/time)/scope_ids/currency/amount/hours/rate/cap/basis/terms_refs。项目与计费流均须条款/有效决定依据，scope_ids 跨流不得重复，币种为三位大写代码。fixed 流的 hours/rate 为 null；time 流的 amount 为 null。未知金额/工时/费率保留 null。

billing_summary 按流计算 fixed amount 或 time hours×rate，存在 cap 时封顶，按币种分别输出 estimates_by_currency。open_items 或未知计算输入使 complete=false；revenue_recognized=false、invoice_created=false。配置不改变成本预算基线，不执行结算、开票或收入确认。

## 客户模板：template_mapping

data 必含 form_ref、mappings、omissions、audience(internal/customer)。form_ref 必须绑定一个实际登记的 UTF-8 JSON 字段规格 source，格式为：

```json
{"fields":[{"id":"project_title","type":"string","required":true},{"id":"note","type":"string","required":false}]}
```

type 仅为 string/number/boolean/array/object。每个目标字段恰有一个 mapping 或 omission；required 字段不能省略或为空。mapping 含 id/target_field/source_ref/source_pointer/transform；取 source 时读取实际 JSON 内容，取业务产物时从 data 开始。source_pointer 使用 RFC 6901 JSON Pointer（例如 `/completed/0`，`~1` 表示斜线、`~0` 表示波浪号）；transform 仅 identity/string/number，不执行表达式或脚本。omission 含 id/target_field/reason，必须说明未填原因。

customer 映射只消费 customer 可见且允许的业务来源；内部成本、工时、profile/exchange/closure 以及敏感字段不能通过改名、嵌套取值或先转字符串绕过。自然语言仍须人工审核。`prepare-mapped` 写新文件并回读，拒绝覆盖、符号链接和控制目录；产物是 JSON 草稿，不生成客户专用 Word 版式，也不能直接成为 customer 包。结果含 payload、payload_sha256、source_ref、purpose，以及 sent=false、applied=false、customer_package_eligible=false、status=local_mapping_draft。

## 本地系统交换：exchange

data 必含 operation_id/system/entity/direction/record_id/external_id/mapping_ref/state/receipt_ref/conflicts。entity=task/code/finance/document；direction=inbound/outbound；state=prepared/reconciled。prepared 的 receipt_ref=null。mapping_ref 绑定 template_mapping，输出仍是本地候选 JSON；inbound 也不会自动应用需求、任务、成本或其他主账。

reconciled 须无 conflicts，并绑定实际 JSON source 收据。收据精确包含相同的 operation_id、system、entity、direction、record_id、external_id、payload_sha256，加 state=applied、origin=actual/simulation。payload_sha256 是映射 payload 的 UTF-8、sort_keys=true、无空白 JSON 的 SHA-256（ensure_ascii=false、allow_nan=false）；不是外层候选文件哈希。真实项目只接受 actual；模拟收据不能证明外部真实执行。状态通过只说明字段/哈希与来源核对通过，工具不认证执行方身份。

operation_id、系统/实体/方向、内部/外部 ID 与 mapping_ref 跨修订不可改；需要新载荷或映射时创建新操作。reconciled 的 data 不能重写。敏感字段在交换输出前检查，正常财务金额可按字段规格准备。运行工具不网络发送、不创建外部任务、不执行财务动作、不自动回写业务主账；外部动作与授权由专业工具负责。

## 可运行 JSON 与 CLI 示例

以下从仓库根目录执行，仅在新临时目录创建显式模拟底稿。脚本把实际登记返回的哈希写入 JSON；不要手填虚构哈希。安装后可把 RUNTIME 改为 `$HOME/.codex/skills/delivery-orchestrator/scripts/runtime.py`。

```bash
set -e
RUNTIME="$(pwd)/project-delivery-skills/skills/delivery-orchestrator/scripts/runtime.py"
CASE="$(python3 -c 'import tempfile; from pathlib import Path; print(Path(tempfile.mkdtemp()).resolve())')"
export RUNTIME CASE
python3 - <<'PY'
import importlib.util, json, os
from datetime import datetime, timezone
from pathlib import Path
spec = importlib.util.spec_from_file_location('delivery_example', os.environ['RUNTIME'])
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
case = Path(os.environ['CASE'])
project = case / 'project'
r.init_project(project, 'SIM-REUSE', 'simulation', 'CNY')
today = datetime.now(timezone.utc).date().isoformat()
def save(name, value):
    path = case / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    return path
def artifact(aid, kind, data, inputs=(), visibility='internal', revision=1):
    value = dict(project_id='SIM-REUSE', artifact_id=aid, revision=revision,
                 kind=kind, visibility=visibility, status='ready', inputs=list(inputs), data=data)
    return r.register(project, save(aid + '.json', value))
raw = r.source(project, save('terms-source.json', {'simulation': True, 'terms': 'No warranty; fixed fee'}), 'SRC')
terms = artifact('CONTRACT', 'contract', {
    'obligations': [{'id': 'O1', 'statement': 'Simulated no-warranty fixed fee',
                     'source_id': 'SRC', 'locator': '/terms', 'acceptance': 'Simulation only'}],
    'scope_in': ['S1'], 'scope_out': [], 'customer_dependencies': []}, [raw])
evidence = artifact('EVID', 'evidence', {
    'items': [{'id': 'E1', 'source_id': 'SRC', 'locator': '/terms',
               'content': 'Simulated settlement and resource receipt', 'read_status': 'read'}],
    'unread_scope': []}, [raw])
minutes = artifact('MINUTES', 'minutes', {
    'meeting_date': today, 'participants': ['simulated-owner'], 'decisions': [],
    'actions': [], 'open_items': [], 'title': '模拟项目'}, visibility='customer')
artifact('PROFILE', 'profile', {
    'billing_mode': 'fixed', 'delivery_mode': 'staged', 'terms_refs': [terms], 'open_items': [],
    'streams': [{'id': 'B1', 'mode': 'fixed', 'scope_ids': ['S1'], 'currency': 'CNY',
                 'amount': 100, 'hours': None, 'rate': None, 'cap': None,
                 'basis': 'Simulation fixed fee', 'terms_refs': [terms]}]}, [terms])
artifact('CLOSURE', 'closure', {
    'origin': 'simulation', 'as_of': today,
    'obligations': [{'id': 'O1', 'title': 'Simulated settlement', 'category': 'settlement',
                     'owner': 'simulated-owner', 'state': 'closed', 'due_date': today,
                     'evidence_refs': [evidence], 'recipient': None, 'receipt_refs': []}],
    'warranty': {'applicable': False, 'reason': 'Simulation contract excludes warranty',
                 'owner': None, 'start_date': None, 'end_date': None,
                 'terms_refs': [terms], 'transfer_refs': [], 'items': []},
    'administration': {'state': 'closed', 'decision_refs': [minutes]},
    'settlement': {'state': 'reconciled', 'evidence_refs': [evidence]},
    'resources': [{'id': 'R1', 'owner': 'simulated-owner', 'state': 'released',
                   'reason': '', 'evidence_refs': [evidence]}],
    'archive': [{'id': 'A1', 'artifact_ref': terms, 'owner': 'simulated-owner',
                 'classification': 'simulation', 'retention_until': '2031-12-31'}],
    'lessons': [{'id': 'L1', 'observation': 'Simulation', 'action': 'Review evidence',
                 'owner': 'simulated-owner'}]}, [terms, evidence, minutes])
form = r.source(project, save('field-spec.json', {'fields': [
    {'id': 'project_title', 'type': 'string', 'required': True},
    {'id': 'note', 'type': 'string', 'required': False}]}), 'FORM')
mapping = artifact('MAP', 'template_mapping', {
    'form_ref': form, 'audience': 'customer',
    'mappings': [{'id': 'M1', 'target_field': 'project_title', 'source_ref': minutes,
                  'source_pointer': '/title', 'transform': 'identity'}],
    'omissions': [{'id': 'OM1', 'target_field': 'note', 'reason': 'No optional note'}]}, [form, minutes])
exchange = {'operation_id': 'SIM-OP-1', 'system': 'local-fixture', 'entity': 'document',
            'direction': 'outbound', 'record_id': 'MINUTES', 'external_id': 'SIM-EXT-1',
            'mapping_ref': mapping, 'state': 'prepared', 'receipt_ref': None, 'conflicts': []}
artifact('EXCHANGE', 'exchange', exchange, [mapping])
# Prepared candidate only; simulation receipt below is not external execution.
r.prepare_mapped(project, 'EXCHANGE', case / 'prepared.json')
receipt = {k: exchange[k] for k in ('operation_id', 'system', 'entity', 'direction', 'record_id', 'external_id')}
receipt.update(payload_sha256=r.reuse.payload_hash({'project_title': '模拟项目'}),
               state='applied', origin='simulation')
receipt_ref = r.source(project, save('receipt.json', receipt), 'RECEIPT')
exchange.update(state='reconciled', receipt_ref=receipt_ref)
artifact('EXCHANGE', 'exchange', exchange, [mapping, receipt_ref], revision=2)
print(project)
PY
python3 "$RUNTIME" validate "$CASE/project"
python3 "$RUNTIME" status "$CASE/project"
python3 "$RUNTIME" prepare-mapped "$CASE/project" MAP --out "$CASE/mapped.json"
```

例中的 source JSON、PROFILE.json、CLOSURE.json、MAP.json、EXCHANGE.json 均保存在 CASE 中；EXCHANGE.json 是第二修订，历史版本由运行工具保留。模拟数据只验证契约与候选文件机制，不证明合同、结算、行政批准或外部执行。

## 当前组合审查：portfolio

```bash
# resources.json 的精确结构；项目 ID、项目内人员名称、周期须匹配实际台账。
cat > "$CASE/resources.json" <<'JSON'
{"identity_map":{"CUSTOMER-001":{"张三":"EMP-001"},"CUSTOMER-002":{"张三":"EMP-001"}},"capacities":[{"person":"EMP-001","period":"2026-W41","available_hours":40}]}
JSON
python3 "$RUNTIME" portfolio /absolute/path/to/project-one /absolute/path/to/project-two \
  --as-of "$(date -u +%F)" --resources "$CASE/resources.json"
# 也可用上述模拟案例读取当前视图；无成本记录将明确报告不完整。
python3 "$RUNTIME" portfolio "$CASE/project" --as-of "$(date -u +%F)"
```

`--as-of` 只接受当前 UTC 提取日，拒绝过去/未来日期；不是历史回放。每个项目 ID 唯一，validate/effective_ok 通过且无快照 alerts；不能混合 simulation 与 internal。输出包含 extracted_at、historical_reconstruction=false、各项目 source_refs/cost_summary/gates、forecast_by_currency、resource_load、complete/gaps、external_actions=false。

金额分别按 CNY、USD 等币种汇总，不能自动汇率换算或跨币种合计。人员必须显式从项目内名称映射到共享身份；容量是该共享身份在周期内的总 available_hours，不能把各项目容量重复相加。缺映射、容量或 planned_hours 时报告缺口；未知工时的 planned_hours/overloaded 为 null，不能当零负荷。视图读取当前候选与有效状态，不代替各项目主账，也不把资源占用推断为完成度。
