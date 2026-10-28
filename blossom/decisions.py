"""Explicit, source-bound WBS decisions; never renumber a source implicitly."""
import re
from collections import defaultdict
from .common import digest
from .wbs import node


class WBSDecisionRequired(ValueError):
    def __init__(self, groups):
        self.groups = groups
        details = '; '.join(f"{code}: " + ', '.join(n['origem'] for n in rows)
                            for code, rows in groups.items())
        super().__init__('Códigos WBS repetidos. Defina um código exclusivo para cada grupo: '+details)


def resolve_wbs(source_nodes, adjustments, path):
    changes = {}
    if adjustments:
        if not isinstance(adjustments, dict):
            raise ValueError('Decisões de WBS devem conter a identificação da LD e os códigos por origem.')
        if adjustments.get('ld_sha256') != digest(path):
            raise ValueError('As decisões de WBS pertencem a outra LD. Revise as escolhas para este arquivo.')
        changes = adjustments.get('codigos_por_origem', {})
        origins = {n['origem'] for n in source_nodes}
        if not isinstance(changes, dict) or set(changes)-origins:
            raise ValueError('Decisão de WBS aponta para uma origem inexistente na LD.')
    resolved = []
    for original in source_nodes:
        code = changes.get(original['origem'], original['codigo'])
        if not isinstance(code, str) or not re.fullmatch(r'\d+(?:\.\d+)+', code):
            raise ValueError('Código WBS inválido em '+original['origem']+'. Use números separados por pontos, como 4.5.')
        row = int(original['origem'].split('B')[1].split(':')[0])
        revised = node(code, original['nome'], row)
        if code != original['codigo']:
            revised['codigo_original'] = original['codigo']
            revised['decisao_usuario'] = 'Código definido pelo usuário; arquivo original preservado.'
        resolved.append(revised)
    grouped = defaultdict(list)
    for item in resolved:
        grouped[item['codigo']].append(item)
    duplicates = {code: rows for code, rows in grouped.items() if len(rows)>1}
    if duplicates:
        raise WBSDecisionRequired(duplicates)
    def depth(item):
        parts=item['codigo'].split('.')
        return 0 if len(parts)==2 and parts[-1]=='0' else len(parts)-1
    for index, original in enumerate(source_nodes):
        if original['codigo']==resolved[index]['codigo']:
            continue
        # A renamed branch must not silently leave its children under a different
        # group that happens to retain the old duplicate code.
        for child_index in range(index+1,len(source_nodes)):
            child=source_nodes[child_index]
            if depth(child)<=depth(original):
                break
            if child['pai']==original['id'] and resolved[child_index]['pai']!=resolved[index]['id']:
                raise ValueError('Revise também o código do subgrupo em '+child['origem']+
                                 ': ele deve continuar sob o grupo '+resolved[index]['codigo']+'.')
    ids = {n['id'] for n in resolved}
    for item in resolved:
        if item['pai'] is not None and item['pai'] not in ids:
            raise ValueError('O código '+item['codigo']+' não possui grupo pai na WBS. Revise também os códigos dos grupos relacionados.')
    return resolved
