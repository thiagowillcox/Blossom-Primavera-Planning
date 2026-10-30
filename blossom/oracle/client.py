"""Small connection probe following Oracle's documented Basic → Bearer flow."""
import base64
import json
import urllib.error
import urllib.parse
import urllib.request

SERVER = 'https://primavera-us2.oraclecloud.com'


class ConnectionFailure(Exception):
    """User-facing error that never includes credentials or server response bodies."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ConnectionFailure('O Oracle redirecionou a chamada. Precisamos conferir a configuração de acesso à API.')


def check_connection(username, password, *, opener=None):
    if not username.strip() or ':' in username or not password:
        raise ConnectionFailure('Informe um usuário válido e a senha no seu computador.')
    opener = opener or urllib.request.build_opener(NoRedirect())
    credentials = base64.b64encode((username.strip()+':'+password).encode('utf-8')).decode('ascii')
    scope = urllib.parse.urlencode({'scope': 'http://primavera-us2.oraclecloud.com/api'})
    request = urllib.request.Request(SERVER+'/primediscovery/apitoken/request?'+scope,
                                     data=b'', method='POST',
                                     headers={'Authorization': 'Basic '+credentials, 'Accept': 'application/json'})
    try:
        with opener.open(request, timeout=25) as response:
            if response.status != 200:
                raise ConnectionFailure('O Oracle não confirmou a geração do token.')
            payload = response.read(1048577)
            if len(payload)>1048576:
                raise ConnectionFailure('Resposta de autenticação inesperada. Precisamos conferir o formato documentado.')
        try:
            result = json.loads(payload)
        except (ValueError, UnicodeError):
            raise ConnectionFailure('O Oracle não retornou um token em JSON. Confira se a API aceita esse método de autenticação.') from None
        # Accommodate conventional OAuth and camelCase token response formats.
        token = (result.get('access_token') or result.get('accessToken')) if isinstance(result, dict) else None
        if not isinstance(token, str) or not token or len(token)>16384 or any(not 33<=ord(c)<=126 for c in token):
            raise ConnectionFailure('Formato do token não reconhecido. Confira o exemplo de resposta na documentação; não compartilhe o token real.')
        request = urllib.request.Request(SERVER+'/api/restapi/util/testConnection',
                                         headers={'Authorization':'Bearer '+token, 'Accept':'application/json'})
        with opener.open(request, timeout=25) as response:
            if response.status not in (200,204) or 'text/html' in response.headers.get('Content-Type','').lower():
                raise ConnectionFailure('A API não confirmou a conexão. Precisamos conferir a resposta do serviço.')
    except urllib.error.HTTPError as exc:
        messages = {401:'Autenticação recusada. Confira as credenciais e se esse método está habilitado para sua conta.',
                    403:'Acesso negado. Confira as permissões da API e a configuração de segurança da conta.',
                    404:'Endpoint não encontrado. Confira o endereço e a documentação do ambiente.',
                    429:'Limite de chamadas atingido. Aguarde antes de tentar novamente.'}
        raise ConnectionFailure(messages.get(exc.code, f'O Oracle retornou HTTP {exc.code}.')) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ConnectionFailure('Não foi possível acessar o Oracle por HTTPS. Confira a rede e os certificados; não desative a verificação TLS.') from None
    return True
