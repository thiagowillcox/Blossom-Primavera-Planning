import hashlib
import json
import re
from decimal import Decimal


def stable_id(prefix, *parts):
    key = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return prefix + '-' + hashlib.sha256(key.encode()).hexdigest()[:20]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_text(value):
    """Normalize labels without modifying the preserved original Excel cells."""
    if not isinstance(value, str):
        return value
    return value.replace('\u200b', '').replace('\ufeff', '').strip()


def number(value):
    # Some LD templates store an escaped non-breaking space as literal text.
    # Treat only blank cells/that placeholder as missing, never arbitrary text.
    if isinstance(value, str):
        value = clean_text(value)
    if value is None or (isinstance(value, str) and value in ('', r'\xa0')):
        return None
    if isinstance(value, str):
        # Both decimal conventions are accepted only when unambiguous.
        # "1,234" / "1.234" could mean a decimal or a thousands separator.
        if re.fullmatch(r'\+?\d+', value):
            value = Decimal(value)
        elif re.fullmatch(r'\+?\d+[.,]\d+', value):
            if len(re.split(r'[.,]', value)[1]) == 3:
                raise ValueError(f'Separador numérico ambíguo: {value!r}; salvar como número no Excel')
            value = Decimal(value.replace(',', '.'))
        elif re.fullmatch(r'\+?\d{1,3}(?:\.\d{3})+,\d+', value):
            value = Decimal(value.replace('.', '').replace(',', '.'))
        elif re.fullmatch(r'\+?\d{1,3}(?:,\d{3})+\.\d+', value):
            value = Decimal(value.replace(',', ''))
    if isinstance(value, bool) or not isinstance(value, (float, int, Decimal)):
        raise ValueError(f'Valor numérico não resolvido: {value!r}')
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError('Valor negativo ou não finito')
    return result


def issue(code, source, detail):
    return {'codigo': code, 'origem': source, 'descricao': detail}
