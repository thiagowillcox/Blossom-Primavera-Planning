import hashlib
import json
from decimal import Decimal


def stable_id(prefix, *parts):
    key = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return prefix + '-' + hashlib.sha256(key.encode()).hexdigest()[:20]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int, Decimal)):
        raise ValueError(f'Valor numérico não resolvido: {value!r}')
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError('Valor negativo ou não finito')
    return result


def issue(code, source, detail):
    return {'codigo': code, 'origem': source, 'descricao': detail}
