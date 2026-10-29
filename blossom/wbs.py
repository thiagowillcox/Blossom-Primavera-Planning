from .common import stable_id


def node(code, name, row):
    parts = code.split('.')
    parent = None if len(parts)==2 and parts[-1]=='0' else ('.'.join(parts[:-1]) if len(parts)>2 else parts[0]+'.0')
    return {'id': stable_id('WBS', code), 'codigo': code, 'nome': name,
            'pai': stable_id('WBS', parent) if parent else None,
            'origem': f'LD!B{row}:D{row}'}
