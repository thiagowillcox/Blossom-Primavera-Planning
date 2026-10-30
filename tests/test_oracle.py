import io
import json
import urllib.error
from urllib.parse import parse_qs,urlparse
import pytest
from blossom.oracle.client import check_connection, ConnectionFailure, NoRedirect


class Response(io.BytesIO):
    def __init__(self,data,status=200,content_type='application/json'):
        super().__init__(data)
        self.status=status
        self.headers={'Content-Type':content_type}


class FakeOracle:
    def __init__(self,token=None,html=False,error=None):
        self.calls=[];self.token=token or {'access_token':'fictional-test-token'}
        self.html=html;self.error=error

    def open(self,request,timeout):
        self.calls.append(request)
        assert timeout==25
        if self.error:
            raise urllib.error.HTTPError(request.full_url,self.error,'not exposed',{},None)
        if len(self.calls)==1:
            return Response(json.dumps(self.token).encode())
        return Response(b'OK',content_type='text/html' if self.html else 'text/plain')


@pytest.mark.parametrize('field',['access_token','accessToken'])
def test_documented_flow_has_only_authentication_and_connection_probe(field):
    oracle=FakeOracle({field:'fictional-test-token'})
    assert check_connection('test@example.org','fictional-password',opener=oracle)
    auth,probe=oracle.calls
    assert auth.get_method()=='POST'
    assert urlparse(auth.full_url).path=='/primediscovery/apitoken/request'
    assert parse_qs(urlparse(auth.full_url).query)=={'scope':['http://primavera-us2.oraclecloud.com/api']}
    assert auth.get_header('Authorization').startswith('Basic ')
    assert probe.full_url=='https://primavera-us2.oraclecloud.com/api/restapi/util/testConnection'
    assert probe.get_method()=='GET'
    assert probe.get_header('Authorization')=='Bearer fictional-test-token'


@pytest.mark.parametrize('code',[401,403,404,429,500])
def test_http_failure_does_not_expose_credentials(code):
    with pytest.raises(ConnectionFailure) as error:
        check_connection('test@example.org','fictional-password',opener=FakeOracle(error=code))
    assert 'fictional-password' not in str(error.value)
    assert 'test@example.org' not in str(error.value)


def test_unrecognized_token_stops_before_probe():
    oracle=FakeOracle({'unexpected':'secret-must-not-be-shown'})
    with pytest.raises(ConnectionFailure,match='Formato do token'):
        check_connection('test','pw',opener=oracle)
    assert len(oracle.calls)==1


def test_redirect_is_not_followed_with_credentials():
    with pytest.raises(ConnectionFailure,match='redirecionou'):
        NoRedirect().redirect_request(None,None,302,'',{},'https://other.example.org')


def test_html_login_page_is_not_connection_success():
    with pytest.raises(ConnectionFailure,match='não confirmou'):
        check_connection('test','pw',opener=FakeOracle(html=True))
