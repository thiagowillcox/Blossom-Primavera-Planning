"""Map reviewed source rules conservatively; never infer an FS from a SIPOC arrow."""
import json
import re
import unicodedata
from pathlib import Path
from .common import issue

RULES_PATH=Path(__file__).resolve().parents[1]/'config/regras_manual.json'
FEL={'DC':2,'DB':3,'DD':4}


def normalized(text):
    text=unicodedata.normalize('NFKD',str(text or '')).encode('ascii','ignore').decode().upper()
    text=re.sub(r'[^A-Z0-9]+',' ',text).strip()
    plurals={'LISTAS':'LISTA','RELACOES':'RELACAO','CRITERIOS':'CRITERIO','MEMORIAS':'MEMORIA',
             'DIAGRAMAS':'DIAGRAMA','FLUXOGRAMAS':'FLUXOGRAMA','PLANTAS':'PLANTA','ARRANJOS':'ARRANJO'}
    return ' '.join(plurals.get(word,word) for word in text.split())


def discipline_aliases(labels):
    groups=[['CONCRETO','CIVIL CONCRETO'],['ESTRUTURA METALICA','CIVIL ESTRUTURA METALICA'],
            ['AUTOMACAO INSTRUMENTACAO E TELECOMUNICACOES','AUTOMACAO','INSTRUMENTACAO','TELECOMUNICACOES']]
    names={normalized(d) for d in labels}
    for group in groups:
        if names.intersection(group):names.update(group)
    return names


def exact_document(rec,selector):
    return normalized(rec['nome']) in {normalized(name) for name in selector.get('documentos',[])}


def load_text_rules(workbook, manual_hash):
    data=json.loads(RULES_PATH.read_text(encoding='utf-8'))
    rules=[];issues=[];quotes={}
    for source in data['regras']:
        r=dict(source)
        if r['manual_sha256']!=manual_hash:
            issues.append(issue('REGRA_DESATUALIZADA',r['id'],'Regra textual não aplicada: manual diferente da fonte revisada.'))
            continue
        key=(r['fase'],r['celula_fonte'])
        if key not in quotes:
            quotes[key]=workbook[key[0]][key[1]].value
        if quotes[key]!=r['evidencia']:
            raise ValueError('Evidência textual não confere com o manual: '+r['origem'])
        rules.append(r)
    return rules,issues


def map_manual_rules(rules,records,wbs,activities,config):
    nodes={n['id']:n for n in wbs}
    stages={(a['registro_id'],a['etapa']):a['id'] for a in activities}
    active={a['registro_id'] for a in activities}
    def ancestors(rec):
        path=[];current=rec.get('wbs_id')
        while current in nodes and current not in path:
            path.append(current);current=nodes[current]['pai']
        return path
    contexts={r['id']:ancestors(r) for r in records}
    def matches(rec,selector):
        if rec['tipo']!='documento':return False
        disciplines=discipline_aliases(selector.get('disciplinas',[]))
        if disciplines and not disciplines.intersection(normalized(nodes[n]['nome']) for n in contexts[rec['id']]):
            return False
        names={normalized(n) for n in selector.get('documentos',[])}
        if selector.get('outros_documentos'):
            return not any(label in normalized(rec['nome']) for label in ('CRITERIOS DE PROJETO','CRITERIO DE PROJETO'))
        title=normalized(rec['nome'])
        return title in names or any(title==normalized(prefix) or title.startswith(normalized(prefix)+' ')
                                     for prefix in selector.get('familias',[]))
    mapped=[];links=[];issues=[]
    for original in rules:
        r=dict(original)
        if r.get('natureza')!='regra_textual_revisada':
            mapped.append(r);continue
        phases=r['aplica_fel']
        pred=[rec for rec in records if FEL.get(rec['codigo']) in phases and matches(rec,r['seletor_predecessora'])]
        succ=[rec for rec in records if FEL.get(rec['codigo']) in phases and matches(rec,r['seletor_sucessora']) and rec['id'] in active]
        other_phases=[rec for rec in records if FEL.get(rec['codigo']) not in phases
                      and rec['id'] in active and matches(rec,r['seletor_predecessora'])]
        r['predecessoras_ld']=[p['id'] for p in pred]
        r['sucessoras_ld']=[s['id'] for s in succ]
        r['predecessoras_identificadas']='\n'.join(p['nome']+' ['+p['origem']+']'+(' — sem atividade com HH' if p['id'] not in active else '') for p in pred)
        r['sucessoras_identificadas']='\n'.join(s['nome']+' ['+s['origem']+']' for s in succ)
        r['entradas_em_outras_fases']='\n'.join(p['codigo']+' — '+p['nome']+' ['+p['origem']+']' for p in other_phases)
        if r['classe']=='obrigatoria':
            r['marco_predecessora_efetivo']=r.get('etapa_predecessora') or config.get('marco_informacao_consolidada')
            r['marco_sucessora_efetivo']=r.get('etapa_sucessora') or 1
            r['base_marcos']='manual_explicito' if r.get('etapa_predecessora') else 'premissa_do_projeto'
        r['pares_candidatos']=[{'predecessora_registro':p['id'],'sucessora_registro':s['id']}
                               for p in pred for s in succ if p['id']!=s['id']
                               and FEL[p['codigo']]==FEL[s['codigo']]]
        r['quantidade_ligacoes_aplicadas']=0
        r['status_mapeamento']='sem_sucessora_planejada'
        r['observacao_mapeamento']='Nenhum documento planejado corresponde ao seletor; nenhum vínculo criado.'
        if succ:
            if r['classe'] in ('referencia_tecnica','informacao_externa','condicional'):
                r['status_mapeamento']=r['classe']
                r['observacao_mapeamento']=r.get('condicao') or 'Sem vínculo temporal obrigatório automático.'
            elif (config.get('aplicar_regras_explicitas',True) and not r.get('requer_validacao_mapeamento')
                  and (r.get('automatica') or config.get('marco_informacao_consolidada') is not None)):
                unresolved=[]
                predecessor_stage=r.get('etapa_predecessora') or config['marco_informacao_consolidada']
                successor_stage=r.get('etapa_sucessora') or 1
                for target in succ:
                    local=[p for p in pred if FEL[p['codigo']]==FEL[target['codigo']]
                           and (not r.get('automatica') or p['wbs_id'] in contexts[target['id']])]
                    if (len(local)!=1 or (local[0]['id'],predecessor_stage) not in stages
                            or (not r.get('automatica') and (not exact_document(local[0],r['seletor_predecessora']) or not exact_document(target,r['seletor_sucessora'])))):
                        unresolved.append(target['id']);continue
                    links.append({'predecessora':stages[local[0]['id'],predecessor_stage],
                                  'sucessora':stages[target['id'],successor_stage],
                                  'tipo':'FS','defasagem_dias':0,'origem':r['id'],
                                  'base_etapas':'manual_explicito' if r.get('automatica') else 'parametro:marco_informacao_consolidada'})
                    r['quantidade_ligacoes_aplicadas']+=1
                r['status_mapeamento']=('parcial' if r['quantidade_ligacoes_aplicadas'] else 'revisar_mapeamento_e_etapas') if unresolved else ('aplicada_automaticamente' if r.get('automatica') else 'aplicada_por_premissa')
                r['observacao_mapeamento']=('Aprovação final dos critérios (4) antes do início dos demais documentos (1), na mesma fase e ramo Mecânica.' if r.get('automatica') else
                                           f'Premissa do projeto: informação disponível após etapa {predecessor_stage}; somente correspondências exatas e únicas. Famílias, documentos ausentes ou ambíguos continuam pendentes.')
                r['sucessoras_sem_predecessora_planejavel']=unresolved
            else:
                r['status_mapeamento']='revisar_mapeamento_e_etapas'
                r['observacao_mapeamento']='A regra exige precedência, mas os documentos e os marcos precisam de confirmação; não presumir aprovação final.'
            if r['status_mapeamento'] not in ('aplicada_automaticamente','aplicada_por_premissa'):
                if other_phases:
                    r['observacao_mapeamento']+=' Há entradas em outras fases; confirmar se podem ser reaproveitadas. Nenhum vínculo entre fases foi inferido.'
                issues.append(issue('REVISAO_RELACIONAMENTO',r['id'],r['origem']+': '+r['observacao_mapeamento']))
        mapped.append(r)
    priorities={'regra_textual_revisada':0,'observacao_preliminar':1,'evidencia_nao_interpretada':2}
    mapped.sort(key=lambda r:priorities.get(r.get('natureza'),3))
    return mapped,links,issues


def confirm_applied_rules(rules,links,activities,issues,config):
    """Report actual graph edges, including explicit project confirmations."""
    approved={r['regra_id'] for r in config['relacionamentos_aprovados']
              if r.get('aprovada') is True and r.get('classe')=='obrigatoria'}
    records={a['id']:a['registro_id'] for a in activities}
    completed=set()
    for rule in rules:
        if rule.get('natureza')!='regra_textual_revisada':continue
        actual=[r for r in links if r['origem']==rule['id']]
        rule['quantidade_ligacoes_aplicadas']=len(actual)
        if actual and rule['id'] in approved:
            targets={records[r['sucessora']] for r in actual}
            complete=set(rule['sucessoras_ld']).issubset(targets)
            rule['status_mapeamento']='confirmada_pelo_usuario' if complete else 'confirmada_parcialmente'
            rule['observacao_mapeamento']='Documentos e etapas confirmados na configuração do projeto; a evidência do manual permanece registrada.'
            if complete:completed.add(rule['id'])
    return [i for i in issues if not (i['codigo']=='REVISAO_RELACIONAMENTO' and i['origem'] in completed)]


def mark_pending_inputs(rules,links,activities):
    """Unknown required inputs keep dates pending without inventing graph nodes."""
    records={a['id']:a['registro_id'] for a in activities}
    for rule in rules:
        if rule.get('natureza')!='regra_textual_revisada' or rule['classe']=='referencia_tecnica':continue
        resolved={records[r['sucessora']] for r in links if r['origem']==rule['id']}
        unresolved=set(rule.get('sucessoras_ld',[]))-resolved
        for activity in activities:
            if activity['etapa']==1 and activity['registro_id'] in unresolved:
                activity.setdefault('prerequisitos_tecnicos_pendentes',[]).append(rule['id'])
