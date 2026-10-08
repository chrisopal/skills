"""Explicit TEST ONLY raw artifacts for gate regression; never real approval."""
from pathlib import Path
import copy
import bidkit
import review_checks


def populate(project):
    project = Path(project)
    raw = {'tender.txt': 'TEST ONLY 招标样例\n投标须提供有效营业执照，否则否决。\n类似合同每项1分，最多2项。',
           'license.txt': 'TEST ONLY 营业执照\n主体 测试公司\n有效期 2025至2030\n盖章齐全',
           'contract-a.txt': 'TEST ONLY 合同A\n主体 测试公司\n合同金额10万元\n双方签章齐全',
           'contract-b.txt': 'TEST ONLY 合同B\n主体 测试公司\n合同金额20万元\n双方签章齐全'}
    sources = {}
    for name, body in raw.items():
        source_file = project/'work'/name
        source_file.write_text(body, encoding='utf-8')
        registered = bidkit.register_source(project, source_file,
                                            'main' if name=='tender.txt' else 'supplier')
        sources[name] = {k:registered[k] for k in ('source_id','revision','sha256')}
        sources[name].update(location='full_text', quote=body,
                              kind='tender' if name=='tender.txt' else 'supplier')
    scoring = {'project_id':bidkit.project_id(project), 'data':{'items':[
        {'id':'S1','node_type':'scored','title':'类似业绩','max_score':2,
         'sources':[sources['tender.txt']]}]}}
    compliance = {'project_id':bidkit.project_id(project), 'data':{'rules':[
        {'id':'C1','kind':'qualification','fatal':True,'condition':'有效执照',
         'sources':[sources['tender.txt']]}]}}
    evidence = {'project_id':bidkit.project_id(project),'data':{
        'materials':[{'id':mid,'independent_evidence_id':file,'sources':[sources[file]]} for mid,file in
                     [('M1','license.txt'),('M2','contract-a.txt'),('M3','contract-b.txt')]],
        'selections':[
            {'id':'SEL1','target_ids':['C1'],'material_ids':['M1'],
             'required_count':1,'independent_count':1,'state':'accepted'},
            {'id':'SEL2','target_ids':['S1'],'material_ids':['M2','M3'],
             'required_count':2,'independent_count':2,'state':'accepted'}]}}
    writing = {'project_id':bidkit.project_id(project), 'data':{'chapters':[
        {'id':'CH1','body':'测试主体提交营业执照。类似业绩附合同A和合同B。'}]}}
    for name, payload in [('04-scoring.json',scoring),('05-compliance.json',compliance),
                          ('09-evidence-selection.json',evidence),('11-technical-content.json',writing)]:
        bidkit.atomic(project/'artifacts'/name, payload)
    matrix = review_checks.prepare(project)['core_matrix']
    reference = {'relative_path':'artifacts/11-technical-content.json',
                 'sha256':bidkit.digest(project/'artifacts/11-technical-content.json'),
                 'location':'/data/chapters/0/body','quote':writing['data']['chapters'][0]['body']}
    for area, rows in matrix.items():
        for row in rows:
            row.update(conclusion='satisfied',rationale='TEST ONLY 已回读所有原件和实际正文。',
                       bid_refs=[copy.deepcopy(reference)])
            if area == 'materials':
                row['dimensions']={d:'passed' for d in review_checks.MATERIAL_DIMENSIONS}
    return matrix


def review(project, matrix, snapshot):
    value = bidkit.read(Path(__file__).resolve().parents[1]/
                        'skills/bid-review-remediation/assets/output.template.json')
    value.update(project_id=bidkit.project_id(project),artifact_id='TEST-REVIEW',
                 status='ready',warnings=[],summary='TEST ONLY mechanical gate fixture')
    value['inputs']=[{'artifact_id':p.stem,'revision':1,
                      'relative_path':p.relative_to(project).as_posix(),'sha256':bidkit.digest(p)}
                     for p in sorted((project/'artifacts').glob('*.json'))]
    value['data'].update(core_matrix=matrix,reviewed_inputs_sha256=snapshot['fingerprint'],
                         review_scope='full',findings=[],checks=[{
                             'area':'TEST ONLY','state':'passed','note':'Hand-written gate fixture'}],
                         human_approval_ref='TEST ONLY',release_recommendation='eligible_for_user_release')
    return value
