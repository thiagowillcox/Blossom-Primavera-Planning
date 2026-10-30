"""Interactive local draft upload, with destination and content visible before writes."""
from getpass import getpass
import json
from pathlib import Path
from .client import ConnectionFailure
from .draft import build_draft, DraftSession, upload_draft, durable_write


def send_draft():
    session=None
    journal=None
    try:
        print('RASCUNHO Oracle — grupos, atividades e ligações. Sem envio de HH ou prazos.')
        filename=input('Arraste o mesmo Excel usado na prévia e pressione Enter: ').strip().strip('"')
        plan=build_draft(filename,'output/consulta_primavera_local.json','output/previa_envio_primavera.json')
        project=plan['projeto'];pid=project['projectId']
        journal=Path(f'output/envio_rascunho_{pid}.json')
        if journal.exists():
            raise ConnectionFailure('Já existe registro de envio para esse projeto. Não repita nem apague o registro; precisamos conferir o Oracle.')
        durable_write(Path('output/plano_rascunho_primavera.json'),plan)
        print('Destino: '+str(project['projectName'])+' | ID: '+str(pid))
        print(f"Criar: {len(plan['wbs'])} grupos, {len(plan['activities'])} atividades e {len(plan['relationships'])} ligações.")
        print('As HH e atribuições NÃO serão enviadas. Datas, durações e calendário NÃO serão definidos pelo programa.')
        print('O Oracle poderá preencher valores padrão. O cronograma será um rascunho, com pendências técnicas para revisão.')
        print('Plano salvo em output/plano_rascunho_primavera.json. O envio exige projeto de teste vazio.')
        username=input('Seu usuário/email Oracle: ')
        password=getpass('Sua senha Oracle (não aparece ao digitar): ')
        session=DraftSession(username,password)
        password=None
        session.test_connection()
        root=session.inspect_empty_project(project)
        print('Projeto conferido: sem atividades e apenas com a WBS raiz.')
        confirmation=input(f'Para criar essa estrutura no Oracle, digite ENVIAR {pid} (Enter cancela): ').strip()
        if confirmation!=f'ENVIAR {pid}':
            print('Envio cancelado. Nenhuma alteração realizada.');return 0
        # Recheck after confirmation in case the project changed while reviewing.
        if session.inspect_empty_project(project)!=root:
            raise ConnectionFailure('A raiz do projeto mudou; consulte novamente antes de enviar.')
        result=upload_draft(session,plan,root,journal)
        print('Estrutura criada e conferida por nova leitura da API.')
        print('Grupos: '+str(len(result['wbs']))+' | Atividades: '+str(len(result['atividades']))+' | Ligações: '+str(len(result['relacionamentos'])))
        print('HH, recursos, durações e revisão técnica continuam pendentes. Nenhum agendamento foi executado.')
        print('Registro local: '+str(journal))
        return 0
    except (ConnectionFailure,ValueError,OSError,KeyError,TypeError,EOFError,KeyboardInterrupt) as exc:
        print('Envio não concluído: '+(str(exc) if isinstance(exc,ConnectionFailure) else 'Confira o Excel, a prévia, a seleção e os arquivos locais.'))
        if journal and journal.exists():
            print('Pode haver dados já criados no Oracle. NÃO repita o envio nem apague o registro: '+str(journal))
        return 1
    finally:
        if session:session.close()
