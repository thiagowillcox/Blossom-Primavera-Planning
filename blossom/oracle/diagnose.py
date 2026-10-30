"""Read-only comparison after an interrupted structural upload."""
import hashlib
import json
from pathlib import Path
from .client import SERVER, ConnectionFailure


def diagnose_groups(session, plan_path, journal_path, destination):
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'))
    journal=json.loads(Path(journal_path).read_text(encoding='utf-8'))
    digest=hashlib.sha256(json.dumps(plan,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    pid=plan.get('projeto',{}).get('projectId')
    if (type(pid) is not int or pid<=0 or journal.get('projectId')!=pid
        or plan.get('servidor')!=SERVER or journal.get('servidor')!=SERVER
        or journal.get('plan_sha256')!=digest):
        raise ConnectionFailure('O plano e o registro não correspondem. Preserve os arquivos originais do envio.')
    def read(path):
        raw=session._get(path,'Diagnóstico somente leitura',limit=16777216,allow_empty=True)
        from .client import _json
        return _json(raw,'Diagnóstico somente leitura') if raw else []
    project=read('project/'+str(pid))
    selected=plan['projeto']
    if not isinstance(project,dict) or project.get('projectId')!=pid or any(
        project.get(k)!=selected.get(k) for k in ('projectName','projectCode','workspaceId') if selected.get(k) is not None):
        raise ConnectionFailure('O projeto consultado difere do plano. Nenhuma alteração realizada.')
    groups=read('wbs/project/'+str(pid));activities=read('activity/project/'+str(pid))
    if (not isinstance(groups,list) or not isinstance(activities,list)
        or any(not isinstance(w,dict) or w.get('projectId')!=pid for w in groups)):
        raise ConnectionFailure('Resposta da consulta não reconhecida. Nenhuma alteração realizada.')
    pending=journal.get('solicitacao_pendente') or {}
    keys=pending.get('chaves',[]) if pending.get('rota')=='wbs' else []
    comparisons=[]
    for row in plan['wbs']:
        key=row['local_id']
        if key not in journal.get('wbs',{}) and key not in keys:continue
        parent=row['local_parent']
        parent_id=journal.get('wbs',{}).get(parent) if parent else None
        if parent is None:
            roots=[w.get('wbsId') for w in groups if w.get('parentId') in (None,0)]
            if len(roots)==1:parent_id=roots[0]
        expected=dict(row['payload'],parentId=parent_id)
        recorded=journal.get('wbs',{}).get(key)
        matches=[w for w in groups if (recorded is not None and w.get('wbsId')==recorded)
            or (w.get('wbsCode')==expected['wbsCode'] and w.get('parentId')==parent_id)]
        comparisons.append({'local_id':key,'confirmado_no_registro':recorded is not None,
            'solicitacao_pendente':key in keys,
            'esperado':{k:expected[k] for k in ('projectId','wbsCode','wbsName','parentId')},
            'encontrados':[{k:w.get(k) for k in ('projectId','wbsId','wbsCode','wbsName','parentId')} for w in matches],
            'diferencas':[{k:{'esperado':expected[k],'oracle':w.get(k)} for k in ('projectId','wbsCode','wbsName','parentId') if w.get(k)!=expected[k]} for w in matches]})
    report={'modo':'somente_leitura','projectId':pid,'plano_sha256':digest,
        'estado_registro':journal.get('estado'),'solicitacao_pendente':pending,
        'grupos_retornados':len(groups),'atividades_retornadas':len(activities),
        'grupos_confirmados_no_registro':len(journal.get('wbs',{})),
        'comparacoes':comparisons,
        'wbs_encontradas':[{k:w.get(k) for k in ('projectId','wbsId','wbsCode','wbsName','parentId')} for w in groups],
        'aviso':'Nenhuma escrita realizada. Não apague o registro nem repita o envio antes de conferir este diagnóstico.'}
    target=Path(destination);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    from getpass import getpass
    from .client import ReadSession
    session=None
    try:
        plan_path=Path('output/plano_rascunho_primavera.json')
        plan=json.loads(plan_path.read_text(encoding='utf-8'))
        pid=plan['projeto']['projectId']
        if type(pid) is not int or pid<=0:raise ConnectionFailure('Projeto inválido no plano local.')
        journal=Path(f'output/envio_rascunho_{pid}.json')
        target=Path('output/diagnostico_rascunho_primavera.json')
        print('Diagnóstico SOMENTE LEITURA — nenhum grupo ou atividade será alterado.')
        username=input('Seu usuário/email Oracle: ')
        password=getpass('Sua senha Oracle (não aparece ao digitar): ')
        session=ReadSession(username,password);password=None
        session.test_connection()
        result=diagnose_groups(session,plan_path,journal,target)
        print('Grupos retornados: '+str(result['grupos_retornados'])+' | Atividades retornadas: '+str(result['atividades_retornadas']))
        for row in result['comparacoes']:
            if row['solicitacao_pendente']:
                print('Conferência do grupo interrompido: '+json.dumps(row,ensure_ascii=False))
        print('Diagnóstico salvo em '+str(target))
        print('Nenhum dado foi criado, alterado ou excluído. Preserve também o registro do envio.')
        return 0
    except (ConnectionFailure,ValueError,OSError,KeyError,TypeError,EOFError,KeyboardInterrupt) as exc:
        print('Diagnóstico não concluído: '+(str(exc) if isinstance(exc,ConnectionFailure) else 'Confira os arquivos locais do envio interrompido.'))
        return 1
    finally:
        if session:session.close()


if __name__=='__main__':raise SystemExit(main())
