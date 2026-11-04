"""Session-only structure workflow. Oracle is consulted before adopting or creating data."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
from .client import SERVER,ConnectionFailure
from .draft import DraftSession,build_draft,positive_id,field_equal,durable_write
from .effort import EffortSession
from .preview import prepare_preview,amount


class IntegrationSession(DraftSession,EffortSession):
    """Existing authenticated read/create operations, shared by the web workflow."""


def prepare_structure(excel,project):
    with TemporaryDirectory(prefix='blossom-plan-') as folder:
        root=Path(folder);path=root/'pre_cronograma.xlsx';path.write_bytes(excel)
        selection=root/'selection.json';selection.write_text(json.dumps({'servidor':SERVER,'projeto_selecionado':project}))
        report=prepare_preview(path,selection,root/'preview.json')
        plan=build_draft(path,selection,root/'preview.json')
    return plan,report


def identity(plan):
    return hashlib.sha256(json.dumps(plan,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def relation_key(predecessor,successor):return predecessor+'|'+successor


def inspect_structure(session,plan):
    """Read-only, exact matching; do not infer that unrelated objects belong to this plan."""
    selected=plan['projeto'];pid=positive_id(selected['projectId'])
    if plan.get('servidor')!=SERVER or not str(selected.get('projectName','')).strip().upper().startswith('TESTE'):
        raise ConnectionFailure('Este fluxo aceita apenas projetos de teste no ambiente configurado.')
    project=session._read_json('project/'+str(pid))
    if not isinstance(project,dict) or any(project.get(k)!=selected.get(k) for k in ('projectId','projectName','projectCode','workspaceId') if selected.get(k) is not None):
        raise ConnectionFailure('O destino mudou desde a escolha do projeto. Consulte novamente.')
    if not project.get('projectCode') or not project.get('workspaceCode'):
        raise ConnectionFailure('Não foi possível conferir o código do projeto e do workspace.')
    groups=session._read_json('wbs/project/'+str(pid))
    activities=session._read_json('activity/project/'+str(pid))
    if not isinstance(groups,list) or not isinstance(activities,list) or any(not isinstance(r,dict) for r in groups+activities):
        raise ConnectionFailure('A consulta da estrutura não retornou o formato documentado.')
    roots=[w for w in groups if w.get('parentId') in (None,0)]
    if len(roots)!=1:raise ConnectionFailure('O projeto precisa de uma WBS raiz reconhecida.')
    root_id=positive_id(roots[0].get('wbsId'))
    if any(w.get('projectId')!=pid for w in groups):raise ConnectionFailure('WBS de outro projeto na resposta.')
    mapping={};used={root_id}
    for w in plan['wbs']:
        parent=mapping.get(w['local_parent']) if w['local_parent'] else root_id
        if parent is None:continue
        matches=[g for g in groups if g.get('wbsCode')==w['payload']['wbsCode'] and g.get('parentId')==parent]
        if len(matches)>1:raise ConnectionFailure('Há mais de uma WBS com o mesmo código e pai.')
        if not matches:continue
        actual=matches[0]
        if not field_equal('wbsName',actual.get('wbsName'),w['payload']['wbsName']):
            raise ConnectionFailure('O nome de uma WBS existente difere do pré-cronograma. Nada será sobrescrito.')
        rid=positive_id(actual.get('wbsId'))
        if rid in used:raise ConnectionFailure('A consulta repetiu um ID de WBS.')
        used.add(rid);mapping[w['local_id']]=rid
    if len(groups)!=len(used) or {g.get('wbsId') for g in groups}!=used:
        raise ConnectionFailure('Há WBS fora desta estrutura ou a consulta está incompleta. Confira o projeto escolhido.')
    expected={a['local_id']:a for a in plan['activities']};activity_map={}
    for actual in activities:
        key=actual.get('activityCode');source=expected.get(key)
        if not source or key in activity_map:raise ConnectionFailure('Há atividade diferente ou duplicada no projeto. Nenhuma será alterada.')
        if (actual.get('projectId')!=pid or source['local_wbs'] not in mapping
            or actual.get('wbsId')!=mapping[source['local_wbs']]
            or not field_equal('activityName',actual.get('activityName'),source['payload']['activityName'])
            or actual.get('activityStatus')!='NOT_STARTED' or actual.get('activityType')!=source['payload']['activityType']):
            raise ConnectionFailure('Uma atividade foi alterada, iniciada ou está em outra WBS. Confira antes de continuar.')
        rid=positive_id(actual.get('activityId'))
        if rid in activity_map.values():raise ConnectionFailure('A consulta repetiu um ID de atividade.')
        activity_map[key]=rid
    pairs={};relation_ids=set()
    if activities:
        query=urlencode({'workspaceCode':project['workspaceCode'],'projectCode':project['projectCode']})
        relations=session._read_json('relationship/projectRelationshipCode?'+query)
        if not isinstance(relations,list) or any(not isinstance(r,dict) for r in relations):raise ConnectionFailure('Consulta de ligações não reconhecida.')
        source_pairs={(activity_map[r['predecessor']],activity_map[r['successor']]):r for r in plan['relationships'] if r['predecessor'] in activity_map and r['successor'] in activity_map}
        for row in relations:
            pair=(row.get('predActivityId'),row.get('succActivityId'));source=source_pairs.get(pair)
            if (not source or row.get('predProjectId')!=pid or row.get('succProjectId')!=pid
                or row.get('relationshipType')!='FINISH_TO_START' or amount(row.get('lagHours'))!=0):
                raise ConnectionFailure('Há ligações diferentes do pré-cronograma. Nenhuma será apagada ou substituída.')
            key=relation_key(source['predecessor'],source['successor']);rid=positive_id(row.get('relationshipId'))
            if key in pairs or rid in relation_ids:raise ConnectionFailure('Ligações repetidas na resposta Oracle.')
            pairs[key]=rid;relation_ids.add(rid)
    session._project=project
    state={'servidor':SERVER,'projectId':pid,'origem':plan['origem'],'plan_sha256':identity(plan),
        'estado':'estrutura_conferida_prazos_e_hh_pendentes','wbs':mapping,'atividades':activity_map,
        'relacionamentos':list(pairs.values()),'relacionamentos_por_par':pairs,'solicitacao_pendente':None}
    complete=(len(mapping)==len(plan['wbs']) and len(activity_map)==len(plan['activities']) and len(pairs)==len(plan['relationships']))
    if not complete:state['estado']='estrutura_parcial_conferida'
    return root_id,state


def guard_previous(previous,state):
    """An uncertain request is never blindly repeated while its objects are absent."""
    if previous.get('plan_sha256')!=state['plan_sha256'] or previous.get('projectId')!=state['projectId']:
        raise ConnectionFailure('O registro desta sessão pertence a outra prévia. Confira o projeto e o arquivo.')
    for name in ('wbs','atividades'):
        if any(state[name].get(key)!=rid for key,rid in previous.get(name,{}).items()):
            raise ConnectionFailure('Uma entidade já confirmada foi alterada ou não retornou na consulta.')
    if not set(previous.get('relacionamentos',[]))<=set(state['relacionamentos']):raise ConnectionFailure('Uma ligação confirmada não retornou na consulta.')
    pending=previous.get('solicitacao_pendente') or {}
    keys=pending.get('chaves',[]);route=pending.get('rota')
    found=(all(k in state['wbs'] for k in keys) if route=='wbs' else
        all(k in state['atividades'] for k in keys) if route=='activity/batch' else
        all(relation_key(*k) in state['relacionamentos_por_par'] for k in keys) if route=='relationship/batch' else not pending)
    if not found:raise ConnectionFailure('Uma solicitação desta sessão ainda tem resultado incerto. Consulte o diagnóstico; ela não será repetida automaticamente.')


def sync_structure(session,plan,journal_path,progress=lambda message:None):
    root,state=inspect_structure(session,plan)
    path=Path(journal_path)
    if path.exists():guard_previous(json.loads(path.read_text()),state)
    state['estado']='em_andamento';durable_write(path,state)
    def request(route,payload,keys):
        state['solicitacao_pendente']={'rota':route,'chaves':keys};durable_write(path,state)
        return session.create(route,payload)
    def save():state['solicitacao_pendente']=None;durable_write(path,state)
    try:
        for w in plan['wbs']:
            if w['local_id'] in state['wbs']:continue
            parent=state['wbs'][w['local_parent']] if w['local_parent'] else root
            payload=dict(w['payload'],parentId=parent)
            result=request('wbs',payload,[w['local_id']])
            if not isinstance(result,dict) or any(not field_equal(k,result.get(k),payload[k]) for k in ('projectId','wbsCode','wbsName','parentId')):
                raise ConnectionFailure('A resposta de criação da WBS difere da prévia. Consulte antes de repetir.')
            rid=positive_id(result.get('wbsId'))
            if rid in state['wbs'].values() or rid==root:raise ConnectionFailure('ID de WBS repetido na resposta.')
            state['wbs'][w['local_id']]=rid;save();progress('Grupos conferidos: '+str(len(state['wbs'])))
        missing=[a for a in plan['activities'] if a['local_id'] not in state['atividades']]
        for start in range(0,len(missing),50):
            rows=missing[start:start+50]
            payloads=[dict(a['payload'],wbsId=state['wbs'][a['local_wbs']]) for a in rows]
            result=request('activity/batch',payloads,[a['local_id'] for a in rows])
            if not isinstance(result,list) or len(result)!=len(rows):raise ConnectionFailure('Resposta de atividades incompleta. Consulte antes de repetir.')
            expected={a['activityCode']:a for a in payloads};seen=set()
            for item in result:
                if not isinstance(item,dict):raise ConnectionFailure('Resposta de atividade não reconhecida.')
                key=item.get('activityCode');source=expected.get(key)
                if not source or key in seen or any(not field_equal(k,item.get(k),source[k]) for k in ('projectId','wbsId','activityName')):
                    raise ConnectionFailure('Uma atividade retornada difere da prévia.')
                rid=positive_id(item.get('activityId'))
                if rid in state['atividades'].values():raise ConnectionFailure('ID de atividade repetido na resposta.')
                state['atividades'][key]=rid;seen.add(key)
            save();progress('Atividades conferidas: '+str(len(state['atividades'])))
        missing=[r for r in plan['relationships'] if relation_key(r['predecessor'],r['successor']) not in state['relacionamentos_por_par']]
        for start in range(0,len(missing),50):
            rows=missing[start:start+50]
            payloads=[dict(r['payload'],predActivityId=state['atividades'][r['predecessor']],succActivityId=state['atividades'][r['successor']]) for r in rows]
            expected={(p['predActivityId'],p['succActivityId']):(p,r) for p,r in zip(payloads,rows)}
            result=request('relationship/batch',payloads,[[r['predecessor'],r['successor']] for r in rows])
            if not isinstance(result,list) or len(result)!=len(rows):raise ConnectionFailure('Resposta de ligações incompleta. Consulte antes de repetir.')
            seen=set()
            for item in result:
                if not isinstance(item,dict):raise ConnectionFailure('Resposta de ligação não reconhecida.')
                pair=(item.get('predActivityId'),item.get('succActivityId'));value=expected.get(pair)
                if not value or pair in seen or any(item.get(k)!=v for k,v in value[0].items()):raise ConnectionFailure('Ligação retornada diferente da prévia.')
                rid=positive_id(item.get('relationshipId'))
                if rid in state['relacionamentos']:raise ConnectionFailure('ID de ligação repetido na resposta.')
                source=value[1];state['relacionamentos_por_par'][relation_key(source['predecessor'],source['successor'])]=rid
                state['relacionamentos'].append(rid);seen.add(pair)
            save();progress('Ligações conferidas: '+str(len(state['relacionamentos'])))
        session.verify_created(plan,state,root)
        state['estado']='estrutura_conferida_prazos_e_hh_pendentes';save();return state
    except BaseException as exc:
        state['estado']='interrompido_conferir_oracle'
        state['erro']=str(exc) if isinstance(exc,ConnectionFailure) else 'Operação interrompida. Consulte o Oracle antes de repetir.'
        durable_write(path,state);raise
