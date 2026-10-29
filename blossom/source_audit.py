"""Reconcile every planned source record against Excel's original total R."""
from collections import defaultdict
from decimal import Decimal
from .common import number


def reconcile_ld(records, audit):
    per_record=defaultdict(Decimal)
    for row in audit:
        per_record[row['registro_id']]+=row['hh_original']
    checks=[]
    for record in records:
        calculated=per_record.get(record['id'])
        try: source=number(record.get('total_cache'))
        except ValueError: source=None
        difference=calculated-source if calculated is not None and source is not None else None
        if calculated is None:
            status='sem_hh_planejadas'
        elif source is None:
            status='total_ld_indisponivel'
        else:
            status='conferido' if abs(difference)<=Decimal('0.000001') else 'divergente'
        checks.append({'registro_id':record['id'],'nome':record['nome'],'origem':record['origem'],
                       'hh_total_ld':source,'hh_total_lido':calculated,
                       'diferenca_total_ld':difference,'conferencia_total_ld':status})
    return checks
