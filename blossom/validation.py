from collections import defaultdict
from decimal import Decimal
import math


def validate_config(c):
    def positive(value, zero=False):
        return isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value) and (value>=0 if zero else value>0)
    if not positive(c['jornada_hh_dia']):
        raise ValueError('Jornada deve ser positiva')
    if [Decimal(str(x)) for x in c['percentuais']] != list(map(Decimal, ['0.8','0.1','0.2','0.1'])):
        raise ValueError('Distribuição obrigatória: 80/10/20/10')
    if any(not positive(v) for v in c['capacidade_profissionais'].values()):
        raise ValueError('Capacidades devem ser positivas')
    if any(v is not None and not positive(v, True) for v in c['duracao_cliente_dias'].values()):
        raise ValueError('Prazos devem ser não negativos ou null')
    if any(len(pair)!=2 or any(s not in (1,2,3,4) for s in pair) for pair in c['encadeamento']):
        raise ValueError('Encadeamento inválido')
    for link in c['relacionamentos_aprovados']:
        if link.get('tipo','FS') != 'FS' or not positive(link.get('defasagem_dias',0),True):
            raise ValueError('Versão inicial aceita somente FS com defasagem não negativa')


def topology(activities, links):
    ids = [a['id'] for a in activities]
    if len(ids) != len(set(ids)):
        raise ValueError('Atividades com IDs duplicados')
    incoming = dict.fromkeys(ids, 0)
    outgoing = defaultdict(list)
    seen = set()
    for r in links:
        p,s = r['predecessora'],r['sucessora']
        if p not in incoming or s not in incoming:
            raise ValueError('Predecessora/sucessora inexistente')
        if (p,s) in seen:
            raise ValueError('Relacionamento duplicado')
        seen.add((p,s)); incoming[s]+=1; outgoing[p].append(s)
    ready = sorted(k for k,v in incoming.items() if v==0)
    order = []
    while ready:
        current=ready.pop(0); order.append(current)
        for s in outgoing[current]:
            incoming[s]-=1
            if incoming[s]==0:
                ready.append(s); ready.sort()
    if len(order)!=len(ids):
        raise ValueError('Relação circular detectada')
    return order


def validate_result(tables):
    for table in ('WBS','Atividades','Atribuicoes_Funcoes','Relacionamentos','Matriz_Regras'):
        ids=[r['id'] for r in tables[table]]
        if len(ids)!=len(set(ids)):
            raise ValueError(f'IDs duplicados: {table}')
    aids={a['id']:a for a in tables['Atividades']}
    wids={w['id'] for w in tables['WBS']}
    for w in tables['WBS']:
        if w['pai'] and w['pai'] not in wids:
            raise ValueError('WBS pai ausente')
    totals=defaultdict(Decimal)
    for a in tables['Atribuicoes_Funcoes']:
        if a['atividade_id'] not in aids:
            raise ValueError('Atribuição sem atividade')
        totals[a['atividade_id']]+=a['hh']
    for a in aids.values():
        if a['wbs_id'] not in wids or totals[a['id']] != a['hh']:
            raise ValueError('WBS ou soma de atribuições inválida')
    for r in tables['Auditoria_HH']:
        if r['diferenca'] != 0:
            raise ValueError('Falha de conservação de HH por função')
    topology(tables['Atividades'],tables['Relacionamentos'])
