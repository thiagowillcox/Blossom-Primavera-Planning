"""Inventário rastreável das figuras e dos títulos FEL; sem inferência de setas."""
import hashlib
import json
import posixpath
import zipfile
import xml.etree.ElementTree as ET
from bisect import bisect_right
import openpyxl
from .common import stable_id, digest, issue
from .manual_rules import load_text_rules

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
    reviewed = json.loads(reviewed_path.read_text(encoding='utf-8')) if reviewed_path else {'regras': []}
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
            source_rows=list(sheet.values)
            disciplines={source_rows[i-1][1] for i,row in enumerate(source_rows)
                         if i>0 and row[1]=='DOCUMENTO:' and isinstance(source_rows[i-1][1],str)}
            contexts=[];discipline=None
            for i,row_values in enumerate(source_rows,1):
                label=row_values[1]
                if label in disciplines:
                    discipline=label
                    contexts.append((i,'Fluxo geral — '+discipline,discipline,'fluxo_disciplina'))
                elif isinstance(label,str) and label.startswith(('PROJETO CONCEITUAL -','PROJETO BÁSICO -','PROJETO DETALHADO -')):
                    discipline=label.split(' - ',1)[-1]
                    contexts.append((i,'Fluxo geral — '+discipline,discipline,'fluxo_disciplina'))
                if label=='DOCUMENTO:':
                    contexts.append((i,row_values[3],discipline,'sipoc_documento'))
            context_rows=[c[0] for c in contexts]
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
                index=bisect_right(context_rows,row)-1
                _,title,discipline,context_type=contexts[index] if index>=0 else (0,'Fluxo geral da disciplina/fase',None,'fluxo_disciplina')
                rid = stable_id('MAN', sheet.title, sha, title)
                rule = {'id': rid, 'versao': 'manual-rev02-preliminar-v1',
                        'manual_sha256': manual_hash, 'fase': sheet.title,
                        'natureza': 'evidencia_nao_interpretada',
                        'documento': title, 'disciplina':discipline,'contexto_imagem':context_type,
                        'origem': f'{sheet.title}!R{row}C{col}', 'arquivo_embutido':media,
                        'imagem': name, 'imagem_sha256': sha,
                        'classe': 'a_validar', 'predecessora': None, 'sucessora': None,
                        'status': 'revisao_humana', 'evidencia': 'Figura incorporada: leitura visual requerida; nenhuma relação obrigatória inferida.'}
                existing = next((r for r in rules if r['id'] == rid), None)
                if existing:
                    existing['origem'] += '; ' + rule['origem']
                    continue
                rules.append(rule)
                issues.append(issue('REGRA_EM_IMAGEM', rid, f'{rule["origem"]}: revisar figura {name}; mapear aos registros LD.'))
    try:
        text_rules,text_issues=load_text_rules(workbook,manual_hash)
        rules.extend(text_rules);issues.extend(text_issues)
    finally:
        workbook.close()
    # Reviewed visual observations apply only to the exact immutable input file.
    for observation in reviewed.get('regras', []):
        if observation['manual_sha256'] != manual_hash:
            issues.append(issue('REGRA_DESATUALIZADA', observation['id'], 'Hash do manual diferente; observação não aplicada.'))
        else:
            observation = dict(observation, natureza='observacao_preliminar')
            rules.append(observation)
            issues.append(issue('REGRA_SEM_MAPEAMENTO', observation['id'], 'Observação preliminar não cria vínculo obrigatório; validar e mapear IDs.'))
    return rules, issues
