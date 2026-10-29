from decimal import Decimal
from .common import stable_id, issue
from .duration import duration

STAGES = ['Emissão Inicial', 'Comentários do Cliente', 'Atendimento de Comentários', 'Aprovação Final']


def distribute(records, config):
    activities, assignments, audit, issues = [], [], [], []
    for rec in records:
        if not rec['hh'] or not rec['total_original']:
            continue
        stages = list(enumerate(zip(STAGES, config['percentuais']), 1)) if rec['tipo']=='documento' else [(0, ('Atividade auxiliar', 1))]
        for stage, (label, factor) in stages:
            aid = stable_id('ATV', rec['id'], stage)
            hours = {role: hh * Decimal(str(factor)) for role, hh in rec['hh'].items()}
            days = duration(hours, config, stage)
            activities.append({'id': aid, 'registro_id': rec['id'], 'wbs_id': rec['wbs_id'],
                               'nome': rec['nome']+' — '+label, 'tipo': rec['tipo'],
                               'etapa': stage, 'percentual': factor, 'hh': sum(hours.values()),
                               'duracao_dias': days,
                               'base_duracao': 'prazo_cliente' if stage in (2,4) else 'capacidade_funcoes',
                               'inicio_dia': None, 'fim_dia': None,
                               'origem': rec['origem']})
            if days is None:
                issues.append(issue('DURACAO_PENDENTE', aid, 'Definir prazo do cliente ou capacidade das funções no JSON.'))
            for role, hh in hours.items():
                assignments.append({'id': stable_id('ATR', aid, role), 'atividade_id': aid,
                                    'registro_id': rec['id'], 'funcao': role, 'hh': hh})
        for role, original in rec['hh'].items():
            planned = sum(a['hh'] for a in assignments if a['registro_id']==rec['id'] and a['funcao']==role)
            expected = original * (Decimal('1.2') if rec['tipo']=='documento' else Decimal(1))
            audit.append({'registro_id': rec['id'], 'origem': rec['origem'], 'tipo': rec['tipo'],
                          'funcao': role, 'hh_original': original, 'hh_planejada': planned,
                          'hh_esperada': expected, 'diferenca': planned-expected})
    return activities, assignments, audit, issues
