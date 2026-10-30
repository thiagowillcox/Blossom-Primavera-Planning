from getpass import getpass
import argparse
import json
import re
from pathlib import Path
from .client import check_connection, list_projects, ConnectionFailure


def label(value):
    return re.sub(r'[\x00-\x1f\x7f-\x9f]',' ',str(value or ''))[:200]


def main():
    parser=argparse.ArgumentParser(description='Consulta, prévia e envio separado de rascunho estrutural ao Primavera.')
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--listar-projetos',action='store_true')
    group.add_argument('--preparar-envio',action='store_true')
    group.add_argument('--enviar-rascunho',action='store_true')
    group.add_argument('--retomar-rascunho',action='store_true')
    args=parser.parse_args()
    if args.enviar_rascunho or args.retomar_rascunho:
        from .draft_cli import send_draft
        return send_draft(resume=args.retomar_rascunho)
    if args.preparar_envio:
        from .preview import prepare_preview
        print('Prévia local do envio — nenhuma chamada ao Oracle será realizada.')
        try:
            filename=input('Arraste o pré-cronograma Excel para esta janela e pressione Enter: ').strip().strip('"')
            report=prepare_preview(filename,'output/consulta_primavera_local.json','output/previa_envio_primavera.json')
            print('Destino: '+label(report['projeto_destino'].get('projectName')))
            print('Contagens: '+json.dumps(report['contagens'],ensure_ascii=False))
            print('HH planejadas: '+report['hh_planejadas'])
            print('Atividades sem duração: '+str(report['atividades_sem_duracao']))
            print('Prévia salva em output/previa_envio_primavera.json. Nenhum envio realizado.')
            print('Rascunho estrutural separado: Enviar_Rascunho_Primavera.bat (sem HH e prazos).')
            return 0
        except (ConnectionFailure,ValueError,OSError,KeyError):
            print('Não foi possível preparar a prévia. Confira o Excel gerado e a seleção do projeto. Nenhum dado foi enviado.')
            return 1
    print(('Consulta de projetos' if args.listar_projetos else 'Teste de conexão')+' — Oracle Primavera Cloud')
    print('Destino: https://primavera-us2.oraclecloud.com')
    print('As credenciais são usadas nesta execução; não são salvas em arquivo.')
    print('Nenhum projeto, WBS ou atividade será alterado.\n')
    try:
        username=input('Seu usuário/email Oracle: ')
        password=getpass('Sua senha Oracle (não aparece ao digitar): ')
        if args.listar_projetos:
            Path('output/consulta_primavera_local.json').unlink(missing_ok=True)
            name=input('\nNome completo do projeto de teste, como aparece no Primavera: ').strip()
            projects=list_projects(username,password,name)
            matches=[p for p in projects if p['projectName'].strip().casefold()==name.casefold()]
            print(f'\nProjetos retornados nesta resposta: {len(projects)}. Correspondências: {len(matches)}.')
            print('A consulta pode estar paginada; esta resposta não garante uma lista completa.')
            for project in matches:
                print(f"ID: {project['projectId']} | Nome: {label(project['projectName'])} | Código: {label(project['projectCode'])} | Workspace: {label(project['workspaceId'])}")
            if not matches:
                print('Não foi encontrado nessa resposta. Precisamos conferir filtros/paginação; isso não prova que o projeto não existe.')
                return 1
            choice=input('\nID do projeto de teste para registrar localmente (Enter cancela): ').strip()
            selected=next((p for p in matches if str(p['projectId'])==choice),None)
            if selected is None:
                print('Nenhum destino selecionado. Nenhuma alteração realizada.')
                return 0
            destination=Path('output/consulta_primavera_local.json')
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(json.dumps({'servidor':'https://primavera-us2.oraclecloud.com',
                'projeto_selecionado':selected,'modo':'somente_leitura','paginacao_confirmada':False},
                ensure_ascii=False,indent=2),encoding='utf-8')
            print('\nDestino registrado apenas neste computador: '+str(destination))
            print('Nenhum cronograma foi enviado, criado ou alterado no Oracle.')
            return 0
        else:
            check_connection(username,password)
    except ConnectionFailure as exc:
        print('\nNão conectado: '+str(exc))
        return 1
    except (EOFError,KeyboardInterrupt):
        print('\nTeste cancelado.')
        return 1
    except OSError:
        print('\nNão foi possível acessar o arquivo de seleção local. Nenhuma alteração foi feita no Oracle.')
        return 1
    print('\nConexão confirmada pela API. Nenhum cronograma foi enviado.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
