"""Inventário rastreável das figuras e dos títulos FEL; sem inferência de setas."""
import hashlib
import json
import posixpath
import zipfile
import xml.etree.ElementTree as ET
import openpyxl
from .common import stable_id, digest, issue

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'x': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}


def resolve(base, target):
    return target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(base), target))


def relationships(z, base):
    name = posixpath.join(posixpath.dirname(base), '_rels', posixpath.basename(base)+'.rels')
    if name not in z.namelist():
        return {}
    return {r.attrib['Id']: resolve(base, r.attrib['Target']) for r in ET.fromstring(z.read(name)) if r.attrib.get('TargetMode') != 'External'}


def extract_manual(path, assets_dir, reviewed_path=None):
    assets_dir.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rules, issues = [], []
    manual_hash = digest(path)
    reviewed = json.loads(reviewed_path.read_text()) if reviewed_path else {'regras': []}
    with zipfile.ZipFile(path) as z:
        book_rels = relationships(z, 'xl/workbook.xml')
        sheets = ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets', NS)
        for entry, sheet in zip(sheets, workbook):
            if 'FEL' not in sheet.title:
                continue
            base = book_rels[entry.attrib['{'+NS['r']+'}id']]
            rels = relationships(z, base)
            tree = ET.fromstring(z.read(base))
            drawing = tree.find('s:drawing', NS)
            if drawing is None:
                continue
            drawing_path = rels[drawing.attrib['{'+NS['r']+'}id']]
            image_rels = relationships(z, drawing_path)
            titles = []
            for i, row in enumerate(sheet.values, 1):
                if row[1] == 'DOCUMENTO:':
                    titles.append((i, row[3]))
            for anchor in ET.fromstring(z.read(drawing_path)):
                blip = anchor.find('.//a:blip', NS)
                if blip is None:
                    continue
                media = image_rels[blip.attrib['{'+NS['r']+'}embed']]
                data = z.read(media)
                sha = hashlib.sha256(data).hexdigest()
                start = anchor.find('x:from', NS)
                row = int(start.find('x:row', NS).text)+1 if start is not None else 1
                col = int(start.find('x:col', NS).text)+1 if start is not None else 1
                name = sha + posixpath.splitext(media)[1]
                (assets_dir/name).write_bytes(data)
                preceding = [t for r,t in titles if r <= row]
                title = preceding[-1] if preceding else 'Fluxo geral da disciplina/fase'
                rid = stable_id('MAN', sheet.title, sha, title)
                rule = {'id': rid, 'versao': 'manual-rev02-preliminar-v1',
                        'manual_sha256': manual_hash, 'fase': sheet.title,
                        'documento': title, 'origem': f'{sheet.title}!R{row}C{col}',
                        'imagem': name, 'imagem_sha256': sha,
                        'classe': 'a_validar', 'predecessora': None, 'sucessora': title,
                        'status': 'revisao_humana', 'evidencia': 'Figura incorporada: leitura visual requerida; nenhuma relação obrigatória inferida.'}
                existing = next((r for r in rules if r['id'] == rid), None)
                if existing:
                    existing['origem'] += '; ' + rule['origem']
                    continue
                rules.append(rule)
                issues.append(issue('REGRA_EM_IMAGEM', rid, f'{rule["origem"]}: revisar figura {name}; mapear aos registros LD.'))
    workbook.close()
    # Reviewed visual observations apply only to the exact immutable input file.
    for observation in reviewed.get('regras', []):
        if observation['manual_sha256'] != manual_hash:
            issues.append(issue('REGRA_DESATUALIZADA', observation['id'], 'Hash do manual diferente; observação não aplicada.'))
        else:
            rules.append(observation)
            issues.append(issue('REGRA_SEM_MAPEAMENTO', observation['id'], 'Observação preliminar não cria vínculo obrigatório; validar e mapear IDs.'))
    return rules, issues
