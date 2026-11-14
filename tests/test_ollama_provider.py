"""No model/provider secrets, costs, remote calls or self-approval in local-only mode."""
from __future__ import annotations
import json
import urllib.request
from unittest.mock import Mock
import pytest
from autopilot.llm import LLM, OllamaProvider, providers_from_env
from scripts import network_supervisor as supervisor


def test_local_only_ignores_ambient_remote_credentials(monkeypatch):
    monkeypatch.setenv('CONTINUUM_LLM_LOCAL_ONLY','1')
    monkeypatch.setenv('OLLAMA_MODEL','qwen3.5:4b')
    monkeypatch.setenv('GEMINI_API_KEY','must-not-be-sent')
    monkeypatch.setenv('GROQ_API_KEY','must-not-be-sent')
    p=providers_from_env()
    assert len(p)==1 and p[0].name=='ollama'
    assert p[0].base=='http://127.0.0.1:11434'
    assert p[0].key==''


def test_ollama_native_json_disables_thinking_and_uses_localhost(monkeypatch):
    captures=[]
    class LocalResponse:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self):return json.dumps({'message':{'content':'{"topics":["a"]}'}}).encode()
    class FakeOpener:
        def open(self, request, timeout):
            captures.append((request.full_url, json.loads(request.data), timeout))
            return LocalResponse()
    monkeypatch.setattr(urllib.request,'build_opener',lambda *a,**kw:FakeOpener())
    o=OllamaProvider('qwen3.5:4b')
    assert o.chat('qwen3.5:4b','system','user',0.2,999,True)=='{"topics":["a"]}'
    url,body,timeout=captures[0]
    assert url=='http://127.0.0.1:11434/api/chat'
    assert body['think'] is False
    assert body['stream'] is False
    assert body['format']=='json'
    assert body['options']['num_predict']==999
    assert timeout==240


def test_no_local_model_blocks_without_ever_using_remote(monkeypatch):
    monkeypatch.setenv('CONTINUUM_LLM_LOCAL_ONLY','1')
    monkeypatch.delenv('OLLAMA_MODEL',raising=False)
    monkeypatch.setenv('GEMINI_API_KEY','unused')
    assert providers_from_env()==[]
    assert supervisor.allowed_planner()[0] is False


def test_local_health_requires_installed_model(monkeypatch):
    monkeypatch.setenv('CONTINUUM_LLM_LOCAL_ONLY','1')
    monkeypatch.setenv('OLLAMA_MODEL','qwen3.5:4b')
    class Resp:
        def __init__(self,data):self.data=data
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self):return json.dumps(self.data).encode()
    class Fake:
        def __init__(self,models):self.models=models
        def open(self,*args,**kw):return Resp({'models':[{'name':n} for n in self.models]})
    monkeypatch.setattr(urllib.request,'build_opener',lambda *args:Fake(['other:2b']))
    assert supervisor.allowed_planner()[0] is False
    monkeypatch.setattr(urllib.request,'build_opener',lambda *args:Fake(['qwen3.5:4b']))
    assert supervisor.allowed_planner()[0] is True


def test_ollama_rejects_uninstalled_model_in_invocation():
    with pytest.raises(Exception, match='Unknown local model'):
        OllamaProvider('qwen3.5:4b').chat('different','x','y',0.3,100,True)


def test_native_ollama_accepts_only_local_structured_schema(monkeypatch):
    from autopilot import schemas
    records = []
    class LocalResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps({'message': {'content': '{"topics":[]}'}}).encode()
    class FakeOpener:
        def open(self, request, timeout):
            records.append((request.full_url, json.loads(request.data)))
            return LocalResponse()
    monkeypatch.setattr(urllib.request, 'build_opener', lambda *a,**k: FakeOpener())
    llm = LLM([OllamaProvider('qwen3.5:4b')],log=lambda *a:None)
    assert llm.complete('system','topic ideas',schema=schemas.TOPICS,max_calls=1)=={'topics':[]}
    assert len(records)==1
    url, body = records[0]
    assert url=='http://127.0.0.1:11434/api/chat'
    assert body['format']==schemas.TOPICS
    assert body['think'] is False and body['stream'] is False


def test_other_providers_keep_original_chat_contract_when_schema_is_present():
    from autopilot import schemas
    class NonlocalFake:
        name='fake'; models=['fixture'];best=['fixture']; dead=set();cool_until=0
        def chat(self, model, system, user, temperature, max_tokens, want_json):
            assert model=='fixture' and want_json
            return '{"topics":[]}'
    llm=LLM([NonlocalFake()],log=lambda *a:None)
    assert llm.complete('system','topic ideas',schema=schemas.TOPICS,max_calls=1)=={'topics':[]}


def test_schema_says_not_just_visual_fields_and_limits_short_run_length():
    from autopilot import schemas
    from engine.scenes import SCENES
    shape=schemas.short_script('10SecScientist')
    scenes=shape['properties']['scenes']
    assert scenes['minItems']==scenes['maxItems']==4
    assert scenes['items']['required']==['say','show']
    assert 'text' not in scenes['items']['properties']
    types = set(scenes['items']['properties']['show']['properties']['type']['enum'])
    assert types == set(schemas.allowed_scene_types('10SecScientist'))
    assert 'orbit' not in types and 'foundbeam_flow' not in types
    assert 'orbit' in schemas.allowed_scene_types('Counterfactual Atlas')
    assert 'pip' in schemas.allowed_scene_types('The Low Battery Show')
    assert 'pixel_map' in schemas.allowed_scene_types('Pixel Fables') or 'b3d' in schemas.allowed_scene_types('Pixel Fables')
    assert schemas.short_script('Pixel Fables')['properties']['scenes']['minItems']>=6
    hindi = schemas.short_script('Samjho System')['properties']['scenes']['items']
    assert hindi['properties']['say']['pattern']=='[\u0900-\u097f]'
    assert set(hindi['properties']['show']['properties']['scene']['enum'])=={'clay','title3d','panels'}
    assert 'pattern' not in schemas.short_script('Pixel Fables')['properties']['scenes']['items']['properties']['say']
    assert schemas.chapter('Samjho System')['properties']['scenes']['items']['required']==['say','show']
