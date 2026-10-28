from decimal import Decimal


def duration(hours, config, stage):
    if stage in (2, 4):
        value = config['duracao_cliente_dias'].get(str(stage))
        return Decimal(str(value)) if value is not None else None
    if config.get('metodo_duracao', 'capacidade_funcoes') == 'equivalente_hh':
        return sum(hours.values(), Decimal(0)) / Decimal(str(config['jornada_hh_dia']))
    capacities = config['capacidade_profissionais']
    if any(role not in capacities for role in hours):
        return None
    daily = Decimal(str(config['jornada_hh_dia']))
    # Functions work in parallel on one activity. Shared-resource leveling is
    # deliberately separate and is not claimed by these lower-bound estimates.
    return max((hh / (daily * Decimal(str(capacities[role]))) for role, hh in hours.items()), default=Decimal(0))
