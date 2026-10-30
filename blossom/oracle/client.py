"""Local, read-only Primavera API access. No scheduling write operations."""
import base64
import json
import urllib.error
import urllib.parse
import urllib.request

SERVER = 'https://primavera-us2.oraclecloud.com'


class ConnectionFailure(Exception):
    """User-facing error without credentials or server response bodies."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ConnectionFailure('O Oracle redirecionou a chamada. Precisamos conferir a configuração de acesso à API.')


def _exchange(opener, request, stage, limit=1048576, allow_empty=False):
    try:
        with opener.open(request, timeout=25) as response:
            if response.status not in ((200,204) if allow_empty else (200,)):
                raise ConnectionFailure(stage+': o Oracle não confirmou a solicitação.')
            if 'text/html' in response.headers.get('Content-Type','').lower():
                raise ConnectionFailure(stage+': o Oracle não confirmou uma resposta de API; recebeu uma página HTML.')
            payload=response.read(limit+1)
            if len(payload)>limit:
                raise ConnectionFailure(stage+': resposta maior que o limite local; precisamos de uma consulta filtrada.')
            return payload
    except urllib.error.HTTPError as exc:
        messages={401:'Autenticação recusada. Confira as credenciais e se esse método está habilitado para sua conta.',
                  403:'Acesso negado. Confira as permissões da API e a configuração de segurança da conta.',
                  404:'Endpoint não encontrado. Precisamos conferir a rota na documentação do ambiente.',
                  405:'Método não aceito nessa rota. Precisamos conferir a consulta na documentação do ambiente.',
                  429:'Limite de chamadas atingido. Aguarde antes de tentar novamente.'}
        raise ConnectionFailure(stage+': '+messages.get(exc.code,f'O Oracle retornou HTTP {exc.code}.')) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ConnectionFailure(stage+': falha de rede/HTTPS. Confira rede e certificados; não desative a verificação TLS.') from None


def _json(payload,stage):
    try:return json.loads(payload)
    except (ValueError,UnicodeError):
        raise ConnectionFailure(stage+': formato de resposta não reconhecido; o conteúdo não será exibido.') from None


class ReadSession:
    def __init__(self, username, password, *, opener=None):
        if not username.strip() or ':' in username or not password:
            raise ConnectionFailure('Informe um usuário válido e a senha no seu computador.')
        self._opener=opener or urllib.request.build_opener(NoRedirect())
        credentials=base64.b64encode((username.strip()+':'+password).encode('utf-8')).decode('ascii')
        scope=urllib.parse.urlencode({'scope':'http://primavera-us2.oraclecloud.com/api'})
        request=urllib.request.Request(SERVER+'/primediscovery/apitoken/request?'+scope,data=b'',method='POST',
                                       headers={'Authorization':'Basic '+credentials,'Accept':'application/json'})
        result=_json(_exchange(self._opener,request,'Geração do token'),'Geração do token')
        token=(result.get('access_token') or result.get('accessToken')) if isinstance(result,dict) else None
        if not isinstance(token,str) or not token or len(token)>16384 or any(not 33<=ord(c)<=126 for c in token):
            raise ConnectionFailure('Formato do token não reconhecido. Confira o exemplo da documentação; não compartilhe o token real.')
        self._token=token

    def close(self):
        self._token=None

    def _get(self,path,stage,*,limit=1048576,allow_empty=False):
        if not self._token:raise ConnectionFailure('Sessão encerrada. Execute a autenticação novamente.')
        request=urllib.request.Request(SERVER+'/api/restapi/'+path,method='GET',
                                       headers={'Authorization':'Bearer '+self._token,'Accept':'application/json'})
        return _exchange(self._opener,request,stage,limit,allow_empty)

    def test_connection(self):
        self._get('util/testConnection','Teste de conexão',allow_empty=True)
        return True

    def projects_by_name(self, project_name):
        # Oracle Project REST Endpoints: View all Projects by Name (GET).
        # Encode the name as one path segment; never interpret it as a URL.
        name=_project_name(project_name)
        path='project/name/'+urllib.parse.quote(name,safe='')
        result=_json(self._get(path,'Consulta de projetos',limit=4194304),'Consulta de projetos')
        if isinstance(result,dict):
            result=next((result[k] for k in ('items','data','projects','result') if isinstance(result.get(k),list)),None)
        if not isinstance(result,list):
            raise ConnectionFailure('Consulta de projetos: formato não reconhecido. Precisamos confirmar o endpoint e seu exemplo de resposta na documentação.')
        projects=[]
        for item in result:
            if not isinstance(item,dict):
                raise ConnectionFailure('Consulta de projetos: item não reconhecido.')
            identifier=item.get('projectId')
            if isinstance(identifier,str) and identifier.isascii() and identifier.isdecimal():identifier=int(identifier)
            if type(identifier) is not int or identifier<=0 or not isinstance(item.get('projectName'),str) or not item['projectName'].strip():
                raise ConnectionFailure('Consulta de projetos: campos projectId/projectName não reconhecidos. Nenhum projeto será alterado.')
            if item.get('projectCode') is not None and not isinstance(item['projectCode'],str):
                raise ConnectionFailure('Consulta de projetos: código do projeto com formato inesperado.')
            if item.get('workspaceId') is not None and (type(item['workspaceId']) is not int or item['workspaceId']<=0):
                raise ConnectionFailure('Consulta de projetos: identificador do workspace com formato inesperado.')
            projects.append({k:item.get(k) for k in ('projectId','projectCode','projectName','workspaceId')})
            projects[-1]['projectId']=identifier
        return projects


def check_connection(username,password,*,opener=None):
    session=ReadSession(username,password,opener=opener)
    try:return session.test_connection()
    finally:session.close()


def _project_name(value):
    if not isinstance(value,str) or not value.strip() or any(ord(c)<32 or 127<=ord(c)<=159 for c in value):
        raise ConnectionFailure('Informe o nome completo do projeto para consultar. Nenhum projeto será alterado.')
    return value.strip()


def list_projects(username,password,project_name,*,opener=None):
    name=_project_name(project_name)
    session=ReadSession(username,password,opener=opener)
    try:
        session.test_connection()
        return session.projects_by_name(name)
    finally:session.close()
