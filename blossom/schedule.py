from collections import defaultdict
from decimal import Decimal
from .validation import topology


def estimate(activities, links):
    by_id={a['id']:a for a in activities}
    incoming=defaultdict(list)
    for r in links:
        incoming[r['sucessora']].append(r)
    for aid in topology(activities, links):
        a=by_id[aid]
        predecessors=incoming[aid]
        if a.get('prerequisitos_tecnicos_pendentes') or any(by_id[r['predecessora']]['fim_dia'] is None for r in predecessors):
            start=None
        else:
            start=max((by_id[r['predecessora']]['fim_dia']+Decimal(str(r['defasagem_dias'])) for r in predecessors),default=Decimal(0))
        a['inicio_dia']=start
        a['fim_dia']=start+a['duracao_dias'] if start is not None and a['duracao_dias'] is not None else None
