from collections import defaultdict
from .common import stable_id


def build_links(activities, config, rules=None, automatic=None):
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
    rule_map = {r['id']:r for r in rules} if rules is not None else None
    activity_map={a['id']:a for a in activities}
    links.extend(automatic or [])
    for r in config['relacionamentos_aprovados']:
        if r.get('classe') == 'obrigatoria' and r.get('aprovada') is True:
            if rule_map is not None and r['regra_id'] not in rule_map:
                raise ValueError('Relacionamento obrigatório sem regra rastreável no manual')
            if rule_map is not None and rule_map[r['regra_id']].get('classe')!='obrigatoria':
                raise ValueError('Referência técnica, condição ou informação externa não pode virar obrigação sem regra obrigatória revisada.')
            if rule_map is not None and rule_map[r['regra_id']].get('natureza')=='regra_textual_revisada':
                source=rule_map[r['regra_id']]
                before=activity_map.get(r['predecessora']);after=activity_map.get(r['sucessora'])
                pair={'predecessora_registro':before['registro_id'],'sucessora_registro':after['registro_id']} if before and after else None
                if pair not in source.get('pares_candidatos',[]):
                    raise ValueError('Os documentos escolhidos não correspondem à regra nesta fase da LD.')
                for activity,field in [(before,'etapa_predecessora'),(after,'etapa_sucessora')]:
                    if source.get(field) is not None and activity['etapa']!=source[field]:
                        raise ValueError('A etapa escolhida contraria o marco explícito no manual.')
            links.append({'predecessora': r['predecessora'], 'sucessora': r['sucessora'],
                          'tipo': 'FS', 'defasagem_dias': r.get('defasagem_dias', 0),
                          'origem': r['regra_id']})
    names={a['id']:a['nome'] for a in activities}
    for r in links:
        r['id'] = stable_id('REL', r['predecessora'], r['sucessora'])
        r['predecessora_nome']=names.get(r['predecessora'])
        r['sucessora_nome']=names.get(r['sucessora'])
    return links
