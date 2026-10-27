import argparse
import json
from pathlib import Path
from .common import digest, issue
from .ld import read_ld
from .manual import extract_manual
from .hours import distribute
from .relationships import build_links
from .schedule import estimate
from .validation import validate_config, validate_result
from .export import save


def run(ld, manual, config_path, output, reviewed=None):
    config=json.loads(config_path.read_text())
    validate_config(config)
    records,wbs,issues=read_ld(ld,config.get('identidades'))
    rules,manual_issues=extract_manual(manual,output/'manual_figuras',reviewed)
    activities,assignments,audit,hour_issues=distribute(records,config)
    links=build_links(activities,config)
    estimate(activities,links)
    issues+=manual_issues+hour_issues
    issues.append(issue('IDENTIFICACAO_PROJETO','LD', 'Confirmar que BL1120-0011_R03 corresponde ao Forno III; o arquivo não contém identificação inequívoca.'))
    issues.append(issue('SEM_NIVELAMENTO','motor','Durações consideram funções paralelas por atividade. Não há nivelamento global de recursos nem calendário/data-base.'))
    params=[{'parametro':k,'valor':v} for k,v in config.items()]
    metadata={'ld_sha256':digest(ld),'manual_sha256':digest(manual),'config_sha256':digest(config_path),'versao_motor':'0.1.0'}
    if reviewed:metadata['observacoes_sha256']=digest(reviewed)
    params += [{'parametro':k,'valor':v} for k,v in metadata.items()]
    # Preserve full original cell expressions and cached values in the WBS sheet
    # as record rows, with a parent linking each deliverable to its discipline.
    wbs_records=[{'id':r['id'],'codigo':r['codigo'],'nome':r['nome'],'pai':r['wbs_id'],
                  'origem':r['origem'],'tipo':r['tipo'],'eap_original':r['eap_original'],
                  'quantidade':r['quantidade'],'unidade':r['unidade'],
                  'a1_equivalente':r['a1_equivalente'],'hh_original':r['total_original'],
                  'originais':r['originais'],'cache':r['cache'],'identidade_semantica':r['identidade_semantica']} for r in records]
    tables={'WBS':wbs+wbs_records,'Atividades':activities,'Atribuicoes_Funcoes':assignments,
            'Relacionamentos':links,'Matriz_Regras':rules,'Parametros':params,
            'Pendencias':issues,'Auditoria_HH':audit}
    validate_result(tables)
    save(tables,records,metadata,output)
    return tables


def main():
    parser=argparse.ArgumentParser(description='Pré-cronograma Blossom; sem integração Oracle')
    parser.add_argument('--ld',type=Path,default=Path('input/LD.xlsm'))
    parser.add_argument('--manual',type=Path,default=Path('input/Manual.xlsx'))
    parser.add_argument('--config',type=Path,default=Path('config/parametros.json'))
    parser.add_argument('--observacoes',type=Path,default=Path('config/observacoes_manual.json'))
    parser.add_argument('--output',type=Path,default=Path('output'))
    args=parser.parse_args()
    tables=run(args.ld,args.manual,args.config,args.output,args.observacoes)
    print(json.dumps({name:len(rows) for name,rows in tables.items()},ensure_ascii=False))

if __name__=='__main__':main()
