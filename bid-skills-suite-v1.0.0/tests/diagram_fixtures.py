"""Synthetic reference-style corpus; no commercial claims or tender evidence."""
def node(id, title, row, col=0, *, desc='', span=1, role='process', badge='', shape='box'):
    return dict(id=id, title=title, row=row, col=col, description=desc,
                span=span, role=role, badge=badge, shape=shape)


def edge(a, b, label='', **kw):
    return dict({'from': a, 'to': b, 'label': label}, **kw)


def spec(title, layout, nodes, edges=(), groups=()):
    return dict(version='1.0', title=title, subtitle='参考版式测试  所有业务内容均为模拟',
                footer='图示用于版式与渲染验证  不代表已部署系统或真实性能承诺',
                layout=layout, theme='reference', width=900, nodes=nodes,
                edges=list(edges), groups=list(groups))


def corpus():
    out={}
    # Three columns allow centred steps with symmetric decision branches.
    ns=[node('data','实时采集数据与数据平台',0,0,span=3,role='data'),
        node('real','真实产线状态',1,0,desc='实测节拍  产能  在制品'),
        node('shadow','影子仿真',1,2,desc='同初始条件并行推演',role='primary'),
        node('compare','偏差对比引擎',2,0,span=3,desc='节拍  产能  在制品  物流强度'),
        node('decision','偏差大于阈值',3,1,shape='diamond',role='decision'),
        node('dashboard','精度看板更新',4,0,role='success'),
        node('alarm','告警与偏差事件记录',4,2,role='warning'),
        node('diagnose','触发校准诊断',5,2)]
    es=[edge('data','real'),edge('data','shadow'),edge('real','compare'),edge('shadow','compare'),
        edge('compare','decision'),edge('decision','dashboard','否'),edge('decision','alarm','是'),edge('alarm','diagnose')]
    out['flow-branch']=spec('偏差监测与条件分支','flow',ns,es)
    titles=['物理实体层','设备通信层','采集边缘层','数据平台层','仿真计算层','分析应用层','智能决策层','业务展示层']
    roles=['neutral','process','process','data','primary','primary','process','success']
    ns=[node(f'l{i}',t,7-i,desc=['设备  传感器  工业现场','协议  网关  消息通信','清洗  缓存  断点续传','存储  数据流  统一身份','计算引擎  并行推演','运行分析  方案评估','规则引擎  指令审批','综合看板  漫游展示'][i],span=2,role=roles[i],badge=f'L{i+1}') for i,t in enumerate(titles)]
    es=[edge(f'l{i}',f'l{i+1}') for i in range(7)]+[edge('l6','l1','反向控制',kind='feedback',route='left')]
    out['layered-eight']=spec('八层系统架构与反馈控制','layered',ns,es)
    ns=[node(str(i),t,i,desc=d,badge=str(i+1),role='primary' if i>2 else 'process') for i,(t,d) in enumerate([
        ('物流分析','从至表  搬运量统计'),('作业单位相互关系','工艺顺序  管理联系  安全隔离'),
        ('综合相互关系','物流强度与管理需求'),('位置相关图','无面积布置方案'),('面积与约束适配','柱网  消防  物流通道  预留'),
        ('候选布局方案','方案甲  方案乙  方案丙'),('仿真评估优选','物流距离  搬运成本  产能  在制品')])]
    ns[-1]['role']='success'
    out['flow-feedback']=spec('编号步骤与返回迭代','flow',ns,[edge(str(i),str(i+1)) for i in range(6)]+[edge('6','1','不满意则迭代',kind='feedback',route='right')])
    ns=[];es=[]
    for r,(name,steps) in enumerate([('SMT线',['锡膏印刷','贴片','回流焊','AOI检测']),('THT线',['插件','波峰焊','手工焊','ICT检测']),('装配线',['电缆装配','整机装配','点胶','气密测试']),('检测筛选',['老炼','温度循环','振动','电性能复测'])]):
        ns.append(node(f'r{r}',name,r,role='neutral'))
        for c,t in enumerate(steps,1):
            ns.append(node(f'p{r}{c}',t,r,c,role='process' if r%2==0 else 'primary'))
            es.append(edge(f'r{r}' if c==1 else f'p{r}{c-1}',f'p{r}{c}'))
    out['pipeline-rows']=spec('多条工艺链并排展示','pipeline',ns,es)
    ns=[node('design','实验设计',0,0,badge='1',desc='方案与随机种子'),node('queue','任务队列',0,1,badge='2'),
        *[node(f'w{i}',f'工作线程 W{i+1}',i+1,1,desc='独立模型副本与随机流',role='primary') for i in range(3)],
        node('join','结果汇聚',2,2,role='data',badge='3'),node('stats','统计分析',3,2,role='success',badge='4')]
    es=[edge('design','queue'),*[edge('queue',f'w{i}') for i in range(3)],*[edge(f'w{i}','join') for i in range(3)],edge('join','stats')]
    out['parallel-workers']=spec('并行任务与汇聚统计','parallel',ns,es)
    ns=[node('operator','事件登记',0,0),node('platform','核验与分派',1,1),node('responder','现场处置',2,2),node('review','复核与关闭',3,1,role='success')]
    groups=[dict(id=f'g{i}',title=t,members=ids,kind='lane',role='neutral') for i,(t,ids) in enumerate([('值班员',['operator']),('业务平台',['platform','review']),('处置人员',['responder'])])]
    out['swimlane-events']=spec('工单管理与事件闭环责任泳道','swimlane',ns,[edge('operator','platform'),edge('platform','responder'),edge('responder','review'),edge('review','responder','退回补充',kind='feedback',route='right')],groups)
    ns=[node('plc','生产设备与PLC',0,0,role='neutral'),node('gateway','边缘网关',1,0),node('terminal','现场终端',2,0,role='neutral'),
        node('app','应用服务器',0,1),node('sim','计算服务器',0,2,role='primary'),node('db','数据库',1,1,role='data'),node('store','存储与归档',1,2,role='data'),
        node('browser','办公客户端',2,1,span=2,role='neutral'),node('existing','现有管理系统',0,3,role='neutral'),node('gate','单向光闸与网闸',1,3,role='warning')]
    gs=[dict(id='production',title='生产网 数据采集区',members=['plc','gateway','terminal'],kind='zone'),dict(id='business',title='业务服务区',members=['app','sim','db','store','browser'],kind='zone'),dict(id='management',title='管理网',members=['existing','gate'],kind='zone')]
    es=[edge('plc','gateway'),edge('gateway','app'),edge('app','db'),edge('sim','store'),edge('existing','gate'),edge('gate','store','经审批交换',kind='dashed')]
    out['network-zones']=spec('分区网络与受控交换','network',ns,es,gs)
    ns=[node('user','值班员',0,0),node('workflow','工单服务',0,1,role='primary'),node('dispatch','处置人员',0,2),node('audit','审计服务',0,3,role='data')]
    es=[edge('user','workflow','提交事件'),edge('workflow','workflow','校验身份与去重'),edge('workflow','dispatch','分派工单'),edge('dispatch','workflow','反馈处置结果'),edge('workflow','user','复核确认'),edge('workflow','audit','记录关闭与变更'),edge('audit','workflow','审计回执',kind='dashed')]
    out['sequence-self']=spec('工单处置消息时序','sequence',ns,es)
    ns=[node(f'm{r}{c}',t,r,c,role=['process','primary','success'][c]) for r,ts in enumerate([['需求来源','方案机制','验收方法'],['事件采集','规则分派','样例工单验证'],['现场反馈','状态与权限控制','审计轨迹核验'],['资料归档','附件与版本管理','完整性抽检']]) for c,t in enumerate(ts)]
    out['matrix-response']=spec('需求机制与验证对应矩阵','matrix',ns)
    ns=[node('long','很长的中文标题需要完整保留并自动换行且不能省略关键技术名称和约束条件',0,0,desc='中文长描述与ASCII_Identifier_With_No_Whitespace_And_Version_v20261008连续内容混排。'*3),node('result','结果与校核',1,0,role='success')]
    out['long-text']=spec('长中文和英文标识混排','flow',ns,[edge('long','result','完成完整性校核')])
    out['layered-twelve']=spec('十二层密集结构拆图边界','layered',[node(f't{i}',f'第{i+1}层  模拟组件',i,badge=str(i+1)) for i in range(12)],[edge(f't{i}',f't{i+1}') for i in range(11)])
    return out
