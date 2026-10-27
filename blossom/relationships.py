from collections import defaultdict
from .common import stable_id


def build_links(activities, config, rules=None):
    groups = defaultdict(dict)
    for a in activities:
        groups[a['registro_id']][a['etapa']] = a['id']
    links = []
    for stages in groups.values():
        if 0 in stages:
            continue
        for before, after in config['encadeamento']:
            links.append({'predecessora': stages[before], 'sucessora': stages[after],
                          'tipo': 'FS', 'defasagem_dias': 0, 'origem': 'parametros:encadeamento'})
    rule_ids = {r['id'] for r in rules} if rules is not None else None
    for r in config['relacionamentos_aprovados']:
        if r.get('classe') == 'obrigatoria' and r.get('aprovada') is True:
            if rule_ids is not None and r['regra_id'] not in rule_ids:
                raise ValueError('Relacionamento obrigatório sem regra rastreável no manual')
            links.append({'predecessora': r['predecessora'], 'sucessora': r['sucessora'],
                          'tipo': 'FS', 'defasagem_dias': r.get('defasagem_dias', 0),
                          'origem': r['regra_id']})
    for r in links:
        r['id'] = stable_id('REL', r['predecessora'], r['sucessora'])
    return links
