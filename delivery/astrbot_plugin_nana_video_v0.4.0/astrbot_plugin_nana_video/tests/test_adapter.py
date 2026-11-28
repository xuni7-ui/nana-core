"""Host contract tests with mocked AstrBot and engine, real FFmpeg media checks."""
import asyncio
import importlib
import logging
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

PACKAGE='astrbot_plugin_nana_video'

class Video:
    def __init__(self,path):self.path=path
    async def convert_to_file_path(self):return str(self.path)
class Reply: pass
class Image: pass
class Event:
    def __init__(self,text,video=None,sender='u1',scope='chat'):
        self.message_str=text;self.video=video;self.sender=sender;self.unified_msg_origin=scope
    def get_messages(self):return [self.video] if self.video else []
    def get_sender_id(self):return self.sender
    def is_private_chat(self):return True
    def get_group_id(self):return ''
class Request:
    def __init__(self):self.prompt='original'
class Star:
    def __init__(self,context):pass
class Provider:
    provider_config={'modalities':['image']}
    def __init__(self):self.calls=[]
    def meta(self):return types.SimpleNamespace(id='vision')
    def get_model(self):return 'mock'
    async def text_chat(self,**kw):
        assert all(Path(p).read_bytes()==b'fake-png' for p in kw['image_urls'])
        self.calls.append(kw['prompt']);return types.SimpleNamespace(completion_text='mock visual')
class Context:
    def __init__(self):self.provider=Provider()
    async def get_using_provider_async(self,_):return self.provider
    def get_provider_by_id(self,_):return self.provider

def identity(*_,**__):return lambda fn:fn

def mock_perceive(path,**kw):
    assert Path(path).exists()
    return {'model_content':{'items':[{'type':'text','text':'context '+str(kw['question'])},{'type':'text','text':'frame label'},{'type':'image_url','image_url':{'url':'mock'}}]},'frames':[{'png':b'fake-png','time_seconds':0.0}], 'audio':{'state':'NO_AUDIO'}, 'subtitles':{'state':'NO_EMBEDDED_SUBTITLE'},'errors':[],'warnings':[]}

def mock_run(args,**kwargs):return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=kwargs['timeout'])

def module(name,**attrs):
    m=types.ModuleType(name);m.__dict__.update(attrs);return m

class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        mocks={'astrbot':module('astrbot'),'astrbot.api':module('astrbot.api',logger=logging.getLogger('test')),
          'astrbot.api.event':module('astrbot.api.event',filter=types.SimpleNamespace(on_llm_request=identity,command=identity),AstrMessageEvent=Event),
          'astrbot.api.star':module('astrbot.api.star',Context=Context,Star=Star,StarTools=types.SimpleNamespace(get_data_dir=lambda _:Path(self.tmp.name)),register=identity),
          'astrbot.api.message_components':module('astrbot.api.message_components',Video=Video,Reply=Reply,Image=Image),
          'astrbot.core':module('astrbot.core'),'astrbot.core.provider':module('astrbot.core.provider'),
          'astrbot.core.provider.entities':module('astrbot.core.provider.entities',ProviderRequest=Request),
          PACKAGE+'.engine.video_perception':module(PACKAGE+'.engine.video_perception',perceive_video=mock_perceive),
          PACKAGE+'.engine.video_audio_probe':module(PACKAGE+'.engine.video_audio_probe',_run_bounded=mock_run)}
        self.patcher=patch.dict(sys.modules,mocks);self.patcher.start()
        sys.modules.pop(PACKAGE+'.main',None)
        self.main=importlib.import_module(PACKAGE+'.main'); self.ctx=Context();self.plugin=self.main.NanaVideo(self.ctx,{'route_mode':'standalone','min_call_interval':0})
        self.path=Path(self.tmp.name)/'clip.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=160x90:r=2:d=2','-c:v','mpeg4','-y',str(self.path)],check=True,timeout=20)
    async def asyncTearDown(self):
        await self.plugin.terminate(); self.tmp.cleanup();sys.modules.pop(PACKAGE+'.main',None);self.patcher.stop()
    async def ask(self,text,video=None,sender='u1',scope='chat'):
        r=Request();await self.plugin.inject_video(Event(text,video,sender,scope),r);return r.prompt
    async def test_capture_followup_focus_and_isolation(self):
        out=await self.ask('看视频',Video(self.path));self.assertIn('mock visual',out)
        self.assertEqual(len(self.ctx.provider.calls),1)
        self.assertEqual(await self.ask('那个视频怎么样'),'original')
        self.assertEqual(len(self.ctx.provider.calls),1)
        self.assertIn('重新采样',await self.ask('回看第1秒发生了什么'))
        self.assertEqual(len(self.ctx.provider.calls),2);self.assertIn('第1秒',self.ctx.provider.calls[-1])
        self.assertEqual(await self.ask('那个视频怎么样',sender='other'),'original')
        self.assertEqual(await self.ask('那个视频怎么样',scope='other'),'original')
        self.assertEqual(await self.ask('刚才吃饭了'),'original')
    async def test_no_cache_mode(self):
        self.plugin.cfg.update({'cache_seconds':0})
        self.assertIn('mock visual',await self.ask('看视频',Video(self.path)))
        self.assertFalse(self.plugin.sessions)
        self.assertEqual(await self.ask('那个视频怎么样'),'original')
    async def test_bad_source_retires_previous(self):
        await self.ask('看视频',Video(self.path));bad=Path(self.tmp.name)/'fake';bad.write_bytes(b'not video')
        self.assertIn('未完成有效观察',await self.ask('看视频',Video(bad)))
        self.assertEqual(await self.ask('那个视频怎么样'),'original')
    async def test_coexist_routes_away_direct_and_quotes(self):
        self.plugin.cfg['route_mode']='coexist_bv'
        self.assertEqual(await self.ask('看看',Video(self.path)),'original')
        self.assertEqual(len(self.ctx.provider.calls),0)
        r=Request()
        e=Event('看看 BV1234567890');e.get_messages=lambda:[Reply()]
        await self.plugin.inject_video(e,r)
        self.assertEqual(r.prompt,'original')
        self.assertEqual(len(self.ctx.provider.calls),0)

    async def test_group_denied_before_model(self):
        e=Event('看看视频',Video(self.path));e.is_private_chat=lambda:False;e.get_group_id=lambda:'123'
        r=Request();await self.plugin.inject_video(e,r)
        self.assertEqual(r.prompt,'original')
        self.assertEqual(self.plugin.budget.total(),0)
        self.plugin.cfg['allowed_groups']='123'
        r=Request();await self.plugin.inject_video(e,r)
        self.assertIn('mock visual',r.prompt)
        self.assertEqual(self.plugin.budget.total(),1)

    async def test_persistent_daily_limit(self):
        self.plugin.cfg['daily_calls']=1
        self.assertIn('mock visual',await self.ask('看视频',Video(self.path)))
        self.assertIn('额度',await self.ask('回看第1秒发生了什么'))
        self.assertEqual(len(self.ctx.provider.calls),1)
        self.assertEqual(self.main.Budget(self.plugin.budget.path).total(),1)

    async def test_parallel_admission(self):
        a=('a','u');b=('b','v');c=('c','w')
        self.assertTrue(self.plugin.admit(a))
        self.assertFalse(self.plugin.admit(a))
        self.assertTrue(self.plugin.admit(b))
        self.assertFalse(self.plugin.admit(c))
        self.plugin.release(a);self.plugin.release(b)
        self.assertTrue(self.plugin.admit(c));self.plugin.release(c)

    async def test_material_and_container(self):
        result=mock_perceive(self.path,question='question'); prompt,images=self.main.model_material(result,Path(self.tmp.name))
        self.assertIn('图1：frame label',prompt); self.assertEqual(Path(images[0]).read_bytes(),b'fake-png')
        duration,size=self.main.inspect(self.path,600,640);self.assertEqual(size,(160,90));self.assertEqual(duration,2.)
        self.assertEqual(len(self.main.snapshot(self.path,Path(self.tmp.name)/'copy',1000000)),64)

if __name__=='__main__': unittest.main()
