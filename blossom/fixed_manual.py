"""The site's engineering reference is versioned with the application."""
from pathlib import Path
from .common import digest

MANUAL_NAME = 'Manual de Engenharia Blossom — Rev.02'
MANUAL_SHA256 = 'cbd1da49a5afb5f33baac8b32cb377f38ffaf6ff2d3deab5db4181515d1671ac'
FIXED_MANUAL = Path(__file__).resolve().parents[1]/'resources/manual_engenharia.xlsx'


def get_fixed_manual():
    try:
        actual = digest(FIXED_MANUAL)
    except OSError as exc:
        raise ValueError('O manual fixo não está disponível. Restaure os arquivos da versão atual do aplicativo.') from exc
    if actual != MANUAL_SHA256:
        raise ValueError('O manual fixo está diferente da versão aprovada. Restaure o arquivo original antes de gerar.')
    return FIXED_MANUAL
