import asyncio,json,os,pathlib,tempfile,errno
from aiohttp import ClientSession
from nana_core.life.provider_vault import DurableSecretResolver
from nana_core.nanalink.sidecar import SidecarConfig,SessionConfig,OneBotSidecar
async def run():
    assert os.getuid()==999
    with tempfile.TemporaryDirectory(prefix='nanalink-smoke-') as directory:
        os.chmod(directory,0o700)
        resolver=DurableSecretResolver(pathlib.Path(directory)/'vault',initialize=True)
        resolver.bind('test.upstream','FIXTURE_ONLY_UPSTREAM_NOT_REAL_ACCOUNT')
        resolver.bind('test.core','FIXTURE_ONLY_CORE_NOT_REAL_ACCOUNT')
        config=SidecarConfig(sessions=(SessionConfig(alias='fixture',account_id='42',mode='reverse-websocket',port=18790,
                           upstream_secret_ref='test.upstream',core_api_secret_ref='test.core'),))
        sidecar=OneBotSidecar(config,resolver)
        await sidecar.start()
        try:
            async with ClientSession() as client:
                async with client.get('http://127.0.0.1:18790/nanalink/status',headers={'Authorization':'Bearer FIXTURE_ONLY_CORE_NOT_REAL_ACCOUNT'}) as response:
                    value=await response.json();assert response.status==200
                    assert value['health']['login']=='UNKNOWN' and not value['external_delivery']
                    assert 'FIXTURE_ONLY' not in json.dumps(value)
            try:pathlib.Path('/app/src/nana_core/_nanalink_write_probe').write_text('must fail')
            except OSError as exc:assert exc.errno==errno.EROFS
            else:raise AssertionError('root filesystem writable')
            rows=pathlib.Path('/proc/self/status').read_text().splitlines()
            fields={r.split(':',1)[0]:r.split(':',1)[1].strip() for r in rows if ':' in r}
            assert int(fields['CapEff'],16)==0 and fields['NoNewPrivs']=='1'
            print(json.dumps({'uid':os.getuid(),'read_only_rootfs':True,'effective_capabilities':0,'no_new_privileges':True,
                              'loopback_status':'PASS','vault':'ISOLATED_SYNTHETIC_ONLY','raw_body_persisted':False,
                              'account_login':'NOT_RUN','real_social_send':0,'core_store_mounted':False}))
        finally:await sidecar.close();resolver.clear()
asyncio.run(run())
