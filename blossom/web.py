"""Isolated web adapter: uploaded files never overwrite the project inputs."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from .__main__ import run

ROOT = Path(__file__).resolve().parents[1]
ROLES = ['Gerente','Especialista','ESênior','EPleno','EJúnior','PSênior','PPleno','PJúnior','Desenh.']


def generate(ld_bytes, manual_bytes, config):
    if not ld_bytes or not manual_bytes:
        raise ValueError('Envie a LD e o Manual de Engenharia.')
    with TemporaryDirectory(prefix='blossom-') as name:
        directory = Path(name)
        ld = directory/'LD.xlsm'; ld.write_bytes(ld_bytes)
        manual = directory/'Manual.xlsx'; manual.write_bytes(manual_bytes)
        params = directory/'parametros.json'
        params.write_text(json.dumps(config, ensure_ascii=False), encoding='utf-8')
        output = directory/'saida'
        tables = run(ld, manual, params, output, ROOT/'config/observacoes_manual.json')
        files = {filename: (output/filename).read_bytes() for filename in
                 ['pre_cronograma.xlsx', 'pendencias.json', 'matriz_regras.json']}
        return tables, files
