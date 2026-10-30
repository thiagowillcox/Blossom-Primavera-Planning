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
from .source_audit import reconcile_ld
from .fixed_manual import FIXED_MANUAL
from .manual_rules import map_manual_rules, confirm_applied_rules, mark_pending_inputs, RULES_PATH


def run(ld, manual, config_path, output, reviewed=None):
    config=json.loads(config_path.read_text(encoding='utf-8'))
    validate_config(config)
    records,wbs,issues=read_ld(ld,config.get('identidades'),config.get('ajustes_wbs'))
    rules,manual_issues=extract_manual(manual,output/'manual_figuras',reviewed)
    activities,assignments,audit,hour_issues=distribute(records,config)
    rules,automatic_links,rule_issues=map_manual_rules(rules,records,wbs,activities,config)
    links=build_links(activities,config,rules,automatic_links)
    rule_issues=confirm_applied_rules(rules,links,activities,rule_issues,config)
    mark_pending_inputs(rules,links,activities)
    estimate(activities,links)
    issues+=manual_issues+hour_issues+rule_issues
    issues.append(issue('IDENTIFICACAO_PROJETO','LD', 'Confirmar a identificação do projeto configurada para esta LD.'))
    issues.append(issue('SEM_NIVELAMENTO','motor','Não há nivelamento global de recursos nem calendário/data-base.'))
    params=[{'parametro':k,'valor':v} for k,v in config.items()]
    metadata={'ld_sha256':digest(ld),'manual_sha256':digest(manual),'config_sha256':digest(config_path),'versao_motor':'0.5.0','regras_revisadas_sha256':digest(RULES_PATH)}
    if reviewed:metadata['observacoes_sha256']=digest(reviewed)
    params += [{'parametro':k,'valor':v} for k,v in metadata.items()]
    # WBS contains hierarchy only. Traceability belongs with effort and
    # unresolved records, not with additional hierarchy nodes.
    by_id = {r['id']: r for r in records}
    by_source = {r['origem']: r for r in records}
    def trace(record):
        return {'codigo_ld': record['codigo'], **{key: record.get(key) for key in (
            'nome', 'wbs_id', 'eap_original', 'quantidade',
            'unidade', 'a1_equivalente', 'identidade_semantica', 'originais', 'cache')}}
    source_checks={r['registro_id']:r for r in reconcile_ld(records,audit)}
    for row in audit:
        row.update(trace(by_id[row['registro_id']]))
        row.update({k:v for k,v in source_checks[row['registro_id']].items() if k not in ('nome','origem','registro_id')})
        if row['conferencia_total_ld']=='divergente':
            raise ValueError('Horas calculadas divergem do total original da LD')
    for row in issues:
        record = by_source.get(row['origem'])
        if record is not None:
            row['registro_id'] = record['id']
            row.update(trace(record))
    for row in activities:
        record = by_id[row['registro_id']]
        row.update({key: record.get(key) for key in (
            'codigo', 'eap_original', 'quantidade', 'unidade', 'a1_equivalente')})
    tables={'WBS':wbs,'Atividades':activities,'Atribuicoes_Funcoes':assignments,
            'Relacionamentos':links,'Matriz_Regras':rules,'Parametros':params,
            'Pendencias':issues,'Auditoria_HH':audit}
    metadata['status_entrega'] = 'preliminar_requer_validacao_tecnica'
    validate_result(tables)
    save(tables,records,metadata,output)
    return tables


def main():
    parser=argparse.ArgumentParser(description='Pré-cronograma Blossom; sem integração Oracle')
    parser.add_argument('--ld',type=Path,default=Path('input/LD.xlsm'))
    parser.add_argument('--manual',type=Path,default=FIXED_MANUAL)
    parser.add_argument('--config',type=Path,default=Path('config/parametros.json'))
    parser.add_argument('--observacoes',type=Path,default=Path('config/observacoes_manual.json'))
    parser.add_argument('--output',type=Path,default=Path('output'))
    args=parser.parse_args()
    tables=run(args.ld,args.manual,args.config,args.output,args.observacoes)
    print(json.dumps({name:len(rows) for name,rows in tables.items()},ensure_ascii=False))

if __name__=='__main__':main()
