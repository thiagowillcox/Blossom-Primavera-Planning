"""Presentation hierarchy; summary rows carry no effort or relationships."""
from collections import defaultdict
from .hours import STAGES


def activity_hierarchy(tables):
    nodes = {w['id']: w for w in tables['WBS']}
    children = defaultdict(list)
    for node in tables['WBS']:
        if node['pai'] is not None and node['pai'] not in nodes:
            raise ValueError('WBS pai inexistente na apresentação')
        children[node['pai']].append(node)
    activities = defaultdict(dict)
    for activity in tables['Atividades']:
        if activity['wbs_id'] not in nodes:
            raise ValueError('Atividade sem WBS na apresentação')
        activities[activity['wbs_id']].setdefault(activity['registro_id'], []).append(activity)
    rows, seen = [], set()

    def visit(node, depth, path):
        if node['id'] in seen:
            raise ValueError('WBS circular ou duplicada na apresentação')
        seen.add(node['id'])
        path = path + [node['nome']]
        rows.append({'id': node['id'], 'tipo_linha': 'fase' if depth == 0 else 'agrupador',
                     'nivel': depth, 'pai_id': node['pai'], 'codigo_wbs': node['codigo'],
                     'caminho_wbs': ' / '.join(path), 'nome': node['nome'],
                     'hh': None, 'origem': node['origem']})
        for record_id, group in activities[node['id']].items():
            first = group[0]
            document = first['tipo'] == 'documento'
            parent = node['id']
            if document:
                parent = record_id
                rows.append({'id': record_id, 'tipo_linha': 'documento', 'nivel': depth+1,
                             'pai_id': node['id'], 'codigo_wbs': node['codigo'],
                             'caminho_wbs': ' / '.join(path),
                             'nome': first['nome'].rsplit(' — ', 1)[0],
                             'registro_id': record_id, 'hh': None, 'origem': first['origem']})
            for activity in sorted(group, key=lambda a: a['etapa']):
                row = dict(activity)
                row.update(tipo_linha='atividade', nivel=depth+(2 if document else 1),
                           pai_id=parent, codigo_wbs=node['codigo'], caminho_wbs=' / '.join(path))
                row['nome'] = (STAGES[activity['etapa']-1] if document
                               else activity['nome'].rsplit(' — ', 1)[0])
                rows.append(row)
        for child in children[node['id']]:
            visit(child, depth+1, path)

    for root in children[None]:
        visit(root, 0, [])
    if len(seen) != len(nodes):
        raise ValueError('WBS sem raiz ou circular na apresentação')
    return rows
