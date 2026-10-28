"""Do not claim reference reproduction with different source workbooks."""
from .common import digest


def verify_sources(ld, manual, config):
    for name,path in [('ld',ld),('manual',manual)]:
        expected=config.get('fontes_esperadas',{}).get(name)
        if expected:
            actual=digest(path)
            if actual!=expected:
                raise ValueError(f'{name.upper()} diferente da referência: recebido {actual[:12]}, esperado {expected[:12]}. Envie o arquivo exato usado na geração de referência; não é possível reproduzir seus dados alterando apenas o código.')
