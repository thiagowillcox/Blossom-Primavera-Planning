from .common import stable_id


def node(code, name, row):
    parent = code.split('.')[0] + '.0' if not code.endswith('.0') else None
    return {'id': stable_id('WBS', code), 'codigo': code, 'nome': name,
            'pai': stable_id('WBS', parent) if parent else None,
            'origem': f'LD!B{row}:D{row}'}
