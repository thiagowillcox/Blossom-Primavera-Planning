import json
import urllib.error
import pytest
from blossom.oracle.client import list_projects,ReadSession,ConnectionFailure
from test_oracle import FakeOracle,Response


class ProjectsOracle(FakeOracle):
    def __init__(self,payload,code=None):
        super().__init__();self.payload=payload;self.code=code

    def open(self,request,timeout):
        if len(self.calls)<2:return super().open(request,timeout)
        self.calls.append(request)
        if self.code:raise urllib.error.HTTPError(request.full_url,self.code,'never shown',{},None)
        return Response(json.dumps(self.payload).encode())


@pytest.mark.parametrize('wrapper',[None,'items','data','projects','result'])
def test_project_discovery_is_get_only_and_keeps_minimal_fields(wrapper):
    rows=[{'projectId':7,'projectName':'Projeto de teste','projectCode':'LAB','workspaceId':2,'other':'not retained'}]
    oracle=ProjectsOracle({wrapper:rows} if wrapper else rows)
    projects=list_projects('test','fictional-password',opener=oracle)
    assert len(projects)==1 and projects[0]['projectId']==7
    assert 'other' not in projects[0]
    assert [r.get_method() for r in oracle.calls]==['POST','GET','GET']
    assert oracle.calls[-1].full_url=='https://primavera-us2.oraclecloud.com/api/restapi/project'


def test_empty_result_does_not_invent_a_project():
    assert list_projects('test','password',opener=ProjectsOracle([]))==[]


def test_numeric_string_project_id_is_supported():
    assert list_projects('test','password',opener=ProjectsOracle([{'projectId':'7','projectName':'Test'}]))[0]['projectId']==7


@pytest.mark.parametrize('payload',[{'unknown':'body'},[{'name':'other_entity','id':7}],[{'projectId':True,'projectName':'bad'}]])
def test_unexpected_responses_are_not_treated_as_projects(payload):
    with pytest.raises(ConnectionFailure):list_projects('test','password',opener=ProjectsOracle(payload))


def test_project_error_identifies_stage_without_credentials():
    with pytest.raises(ConnectionFailure,match='Consulta de projetos') as error:
        list_projects('test','fictional-password',opener=ProjectsOracle([],code=405))
    assert 'fictional-password' not in str(error.value)


def test_closed_session_cannot_be_reused():
    session=ReadSession('test','password',opener=FakeOracle())
    session.close()
    with pytest.raises(ConnectionFailure,match='encerrada'):session.test_connection()
