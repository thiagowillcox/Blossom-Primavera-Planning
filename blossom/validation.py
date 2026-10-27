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
    topology([{'id': w['id']} for w in tables['WBS']],
             [{'predecessora': w['pai'], 'sucessora': w['id']}
              for w in tables['WBS'] if w['pai']])
    totals=defaultdict(Decimal)
    per_role=defaultdict(Decimal)
    for a in tables['Atribuicoes_Funcoes']:
        if a['atividade_id'] not in aids:
            raise ValueError('Atribuição sem atividade')
        if a['registro_id'] != aids[a['atividade_id']]['registro_id']:
            raise ValueError('Atribuição vinculada ao registro errado')
        if a['hh'] <= 0:
            raise ValueError('Atribuição sem HH positivas')
        totals[a['atividade_id']]+=a['hh']
        per_role[(a['atividade_id'], a['funcao'])]+=a['hh']
    for a in aids.values():
        if a['wbs_id'] not in wids or totals[a['id']] != a['hh']:
            raise ValueError('WBS ou soma de atribuições inválida')
    grouped=defaultdict(list)
    for activity in aids.values():
        grouped[activity['registro_id']].append(activity)
    audit_keys=set()
    audited_roles=defaultdict(set)
    for r in tables['Auditoria_HH']:
        key=(r['registro_id'], r['funcao'])
        if key in audit_keys:
            raise ValueError('Auditoria duplicada por registro/função')
        audit_keys.add(key)
        audited_roles[r['registro_id']].add(r['funcao'])
        activities=grouped[r['registro_id']]
        document=r['tipo']=='documento'
        factors={1:Decimal('.8'),2:Decimal('.1'),3:Decimal('.2'),4:Decimal('.1')} if document else {0:Decimal(1)}
        if sorted(a['etapa'] for a in activities)!=sorted(factors):
            raise ValueError('Etapas incompletas ou duplicadas')
        actual=Decimal(0)
        for activity in activities:
            hh=per_role[(activity['id'], r['funcao'])]
            if hh != r['hh_original']*factors[activity['etapa']]:
                raise ValueError('Distribuição de HH por etapa/função inválida')
            actual+=hh
        expected=r['hh_original']*(Decimal('1.2') if document else Decimal(1))
        if (actual != expected or r['hh_planejada'] != actual or
                r['hh_esperada'] != expected or r['diferenca'] != actual-expected):
            raise ValueError('Falha de conservação de HH por função')
    for assignment in tables['Atribuicoes_Funcoes']:
        if assignment['funcao'] not in audited_roles[assignment['registro_id']]:
            raise ValueError('Função atribuída sem original auditável')
    topology(tables['Atividades'],tables['Relacionamentos'])
