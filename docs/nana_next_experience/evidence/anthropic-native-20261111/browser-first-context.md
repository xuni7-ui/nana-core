# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: v3.spec.ts >> SYNTHETIC model setup: numeric UUID ANTHROPIC
- Location: tests/v3.spec.ts:1350:78

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.selectOption: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('.next-setup').getByLabel('服务商', { exact: true })

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - link "跳到主要内容" [ref=e4] [cursor=pointer]:
    - /url: "#v3-content"
  - complementary "Nana Space 页面" [ref=e5]:
    - button "✧ Nana Space A LITTLE LIFE TOGETHER" [ref=e6] [cursor=pointer]:
      - generic [ref=e7]: ✧
      - generic [ref=e8]:
        - text: Nana Space
        - generic [ref=e9]: A LITTLE LIFE TOGETHER
    - generic [ref=e10]:
      - img "奈奈 · 原创静态形象" [ref=e11]
      - generic [ref=e12]:
        - strong [ref=e13]: 奈奈的小宇宙
        - generic [ref=e14]: 同一个主体，许多种相遇
    - navigation [ref=e16]:
      - generic [ref=e17]:
        - generic [ref=e18]: 日常相伴
        - button "生活空间" [ref=e19] [cursor=pointer]
        - button "和奈奈聊聊" [ref=e24] [cursor=pointer]
        - button "记忆与我们" [ref=e28] [cursor=pointer]
        - button "奈奈的小房间" [ref=e32] [cursor=pointer]
      - generic [ref=e36]:
        - generic [ref=e37]: 她的世界
        - button "生活动态" [ref=e38] [cursor=pointer]
        - button "世界探索" [ref=e42] [cursor=pointer]
        - button "B站与看世界" [ref=e50] [cursor=pointer]
        - button "小小计划" [ref=e55] [cursor=pointer]
        - button "成长足迹" [ref=e60] [cursor=pointer]
      - generic [ref=e65]:
        - generic [ref=e66]: 空间管理
        - button "模型中心" [ref=e67] [cursor=pointer]
        - button "设备与连接" [ref=e72] [cursor=pointer]
        - button "备份与连续性" [ref=e76] [cursor=pointer]
        - button "运行与边界" [ref=e80] [cursor=pointer]
        - button "设置中心" [ref=e84] [cursor=pointer]
    - generic [ref=e89]:
      - text: ✦
      - paragraph [ref=e90]: 一起看世界，也拥有自己的光。
      - text: ONE NANA · MANY WINDOWS
  - main [ref=e91]:
    - generic [ref=e92]:
      - generic [ref=e93]:
        - generic [ref=e94]: Nana Space /
        - generic [ref=e95]: 模型中心
      - generic [ref=e96]:
        - generic [ref=e97]: 测试连接
        - button "打开通知信箱" [ref=e99] [cursor=pointer]
        - button "切换晨雾与月光" [ref=e103] [cursor=pointer]
        - button "退出并清除本机视图" [ref=e106] [cursor=pointer]
        - button "刷新真实状态" [ref=e110] [cursor=pointer]
        - button "打开设置中心" [ref=e116] [cursor=pointer]:
          - img "奈奈 · 原创静态形象" [ref=e117]
    - generic [ref=e118]: 明确的开发主体 · 不是云端正式奈奈
    - generic [ref=e122]:
      - generic [ref=e123]: AI RESOURCES & CAPABILITY ROUTING
      - heading "模型中心 ✧" [level=1] [ref=e124]
      - paragraph [ref=e125]: 认知资源可以更换，奈奈始终是奈奈。
    - generic [ref=e126]:
      - generic [ref=e127]: MAKE IT YOURS
      - heading "把你喜欢的模型，带给奈奈" [level=2] [ref=e128]
      - paragraph [ref=e129]: 选择服务商，填写模型名称。先保存配置；凭据需在已授权手机上绑定，当前默认模型不会改变。
      - generic [ref=e130]:
        - generic [ref=e131]:
          - text: 服务商
          - combobox "服务商" [ref=e132]:
            - option "DeepSeek" [selected]
            - option "OpenAI"
            - option "Anthropic"
            - option "自定义 OpenAI-compatible"
        - generic [ref=e133]:
          - text: API 地址
          - textbox "API 地址" [ref=e134]: https://api.deepseek.com
        - generic [ref=e135]:
          - text: 模型名称
          - textbox "模型名称" [ref=e136]:
            - /placeholder: 填写服务商提供的模型名称
            - text: deepseek-chat
        - button "保存模型配置" [ref=e137] [cursor=pointer]
      - status
      - text: 续配进度仅保留在当前连接，不保存到设备。不会自动调用付费模型。更多能力、备用模型和高级参数仍在下方。
    - generic [ref=e138]:
      - generic [ref=e139]:
        - generic [ref=e140]:
          - generic [ref=e141]: INTELLIGENCE, YOUR WAY
          - heading "能力各有所长，奈奈始终是奈奈。" [level=2] [ref=e142]
          - paragraph [ref=e143]: 为每一种能力选择合适的资源。模型可替换，身份与经历持续。
        - button "添加供应商草稿" [ref=e144] [cursor=pointer]
      - generic [ref=e146]: 宿主配置 · revision 4。宿主已开放配置，提交结果以真实回执为准；配置不会授权模型调用。
      - generic [ref=e151]:
        - generic "模型中心分类" [ref=e152]:
          - button "能力路由" [pressed] [ref=e153] [cursor=pointer]
          - button "供应商" [ref=e154] [cursor=pointer]
          - button "模型库" [ref=e155] [cursor=pointer]
        - textbox "搜索模型与能力" [ref=e160]:
          - /placeholder: 搜索供应商、模型、能力…
      - generic [ref=e161]:
        - generic [ref=e162]:
          - generic [ref=e163]: 已配置路由
          - heading "文本与推理" [level=3] [ref=e170]
          - paragraph [ref=e171]: TEXT / REASONING · 原 CognitionSession
          - generic [ref=e176]:
            - strong [ref=e177]: fixture-text
            - generic [ref=e178]: SYNTHETIC Text Resource
          - generic [ref=e179]:
            - generic [ref=e180]: 备用 0 个
            - generic [ref=e181]: 超时上限 15000 ms
          - group [ref=e182]:
            - generic "› 准备路由调整" [ref=e183] [cursor=pointer]
            - option "选择已启用且支持此能力的模型"
            - option "SYNTHETIC Text Resource / fixture-text · a-text" [selected]
            - option "添加备用模型…" [selected]
        - generic [ref=e187]:
          - generic [ref=e188]: 尚未配置
          - heading "图片理解" [level=3] [ref=e195]
          - paragraph [ref=e196]: VISION · 保留 H1 来源与语义契约
          - generic [ref=e201]:
            - strong [ref=e202]: 等待明确配置
            - generic [ref=e203]: 没有已配置的供应商
          - group [ref=e204]:
            - generic "› 准备路由调整" [ref=e205] [cursor=pointer]
            - option "选择已启用且支持此能力的模型" [selected]
            - option "SYNTHETIC Vision Resource / fixture-vision · b-vision"
            - option "添加备用模型…" [selected]
            - option "SYNTHETIC Vision Resource / fixture-vision · b-vision"
        - generic [ref=e209]:
          - generic [ref=e210]: 尚未配置
          - heading "视频理解" [level=3] [ref=e217]
          - paragraph [ref=e218]: VIDEO_UNDERSTAND · 采样帧语义
          - generic [ref=e223]:
            - strong [ref=e224]: 等待明确配置
            - generic [ref=e225]: 没有已配置的供应商
          - group [ref=e226]:
            - generic "› 准备路由调整" [ref=e227] [cursor=pointer]
            - option "选择已启用且支持此能力的模型" [selected]
            - option "添加备用模型…" [selected]
        - generic [ref=e231]:
          - generic [ref=e232]: 尚未配置
          - heading "语音转文字" [level=3] [ref=e239]
          - paragraph [ref=e240]: STT / ASR · 不等于麦克风权限
          - generic [ref=e245]:
            - strong [ref=e246]: 等待明确配置
            - generic [ref=e247]: 没有已配置的供应商
          - group [ref=e248]:
            - generic "› 准备路由调整" [ref=e249] [cursor=pointer]
            - option "选择已启用且支持此能力的模型" [selected]
            - option "添加备用模型…" [selected]
        - generic [ref=e253]:
          - generic [ref=e254]: 尚未配置
          - heading "文字转语音" [level=3] [ref=e261]
          - paragraph [ref=e262]: TTS · 独立能力端口
          - generic [ref=e267]:
            - strong [ref=e268]: 等待明确配置
            - generic [ref=e269]: 没有已配置的供应商
          - group [ref=e270]:
            - generic "› 准备路由调整" [ref=e271] [cursor=pointer]
            - option "选择已启用且支持此能力的模型" [selected]
            - option "添加备用模型…" [selected]
        - generic [ref=e275]:
          - generic [ref=e276]: 尚未配置
          - heading "向量嵌入" [level=3] [ref=e283]
          - paragraph [ref=e284]: EMBED · 可重建缓存，不是记忆真相
          - generic [ref=e289]:
            - strong [ref=e290]: 等待明确配置
            - generic [ref=e291]: 没有已配置的供应商
          - group [ref=e292]:
            - generic "› 准备路由调整" [ref=e293] [cursor=pointer]
            - option "选择已启用且支持此能力的模型" [selected]
            - option "添加备用模型…" [selected]
        - generic [ref=e297]:
          - generic [ref=e298]: 尚未配置
          - heading "音频理解" [level=3] [ref=e305]
          - paragraph [ref=e306]: AUDIO_UNDERSTAND · 独立能力端口
          - generic [ref=e311]:
            - strong [ref=e312]: 等待明确配置
            - generic [ref=e313]: 没有已配置的供应商
          - group [ref=e314]:
            - generic "› 准备路由调整" [ref=e315] [cursor=pointer]
            - option "选择已启用且支持此能力的模型" [selected]
            - option "添加备用模型…" [selected]
        - generic [ref=e319]:
          - generic [ref=e320]: 尚未配置
          - heading "图片生成" [level=3] [ref=e327]
          - paragraph [ref=e328]: IMAGE_GENERATE · 独立能力端口
          - generic [ref=e333]:
            - strong [ref=e334]: 等待明确配置
            - generic [ref=e335]: 没有已配置的供应商
          - group [ref=e336]:
            - generic "› 准备路由调整" [ref=e337] [cursor=pointer]
            - option "选择已启用且支持此能力的模型" [selected]
            - option "添加备用模型…" [selected]
        - generic [ref=e341]:
          - generic [ref=e342]: 尚未配置
          - heading "音频生成" [level=3] [ref=e349]
          - paragraph [ref=e350]: AUDIO_GENERATE · 独立能力端口
          - generic [ref=e355]:
            - strong [ref=e356]: 等待明确配置
            - generic [ref=e357]: 没有已配置的供应商
          - group [ref=e358]:
            - generic "› 准备路由调整" [ref=e359] [cursor=pointer]
            - option "选择已启用且支持此能力的模型" [selected]
            - option "添加备用模型…" [selected]
        - generic [ref=e363]:
          - generic [ref=e364]: 未来扩展
          - heading "检索重排" [level=3] [ref=e371]
          - paragraph [ref=e372]: 未来扩展位 · 当前 Core 无对应 operation
          - generic [ref=e377]:
            - strong [ref=e378]: 等待明确配置
            - generic [ref=e379]: 没有已配置的供应商
        - generic [ref=e380]:
          - generic [ref=e381]: 未来扩展
          - heading "实时音视频" [level=3] [ref=e388]
          - paragraph [ref=e389]: 未来扩展位 · 不假定统一协议已经支持
          - generic [ref=e394]:
            - strong [ref=e395]: 等待明确配置
            - generic [ref=e396]: 没有已配置的供应商
      - generic [ref=e397]: UNKNOWN 请求不会因切换路由而重发。已 dispatch 的失败或无效响应不会在 V1 自动换模型。预算显示上限，不是实际账单。
    - generic [ref=e402]:
      - generic [ref=e403]: ✧ 同一个奈奈 · 许多种相遇
      - button "空间设置" [ref=e404] [cursor=pointer]
    - group [ref=e407]:
      - generic "› 身份与来源信息" [ref=e408] [cursor=pointer]
```

# Test source

```ts
  1286 | 
  1287 | test("SYNTHETIC local chat inbox expires unsent bodies while the original request is pending",async({page})=>{
  1288 |   const state=await installMock(page);state.delayMessage=true;
  1289 |   state.capabilities={conversation_sequence:true};
  1290 |   await page.clock.install();
  1291 |   await open(page,"chat");
  1292 |   const input=page.getByLabel("和奈奈说点什么");
  1293 |   await input.fill("SYNTHETIC active request stays pending");
  1294 |   await page.getByRole("button",{name:"发送",exact:true}).click();
  1295 |   await expect.poll(()=>Boolean(state.messageRoute)).toBe(true);
  1296 |   await input.fill("SYNTHETIC expired secret must disappear");
  1297 |   await page.getByRole("button",{name:"发送",exact:true}).click();
  1298 |   await expect(page.getByRole("button",{name:"取消这条待发消息"})).toBeVisible();
  1299 |   await page.clock.fastForward(5_000);
  1300 |   await input.fill("SYNTHETIC later body has its own deadline");
  1301 |   await page.getByRole("button",{name:"发送",exact:true}).click();
  1302 |   await expect(page.getByRole("button",{name:"取消这条待发消息"})).toHaveCount(2);
  1303 |   await page.clock.fastForward(20*60_000-5_000+1);
  1304 |   await expect(page.getByRole("button",{name:"取消这条待发消息"})).toHaveCount(1);
  1305 |   await expect(page.locator(".live-turn").filter({hasText:"SYNTHETIC expired secret must disappear"})).toHaveCount(0);
  1306 |   await expect(page.locator(".live-turn").filter({hasText:"SYNTHETIC later body has its own deadline"})).toHaveCount(1);
  1307 |   await page.clock.fastForward(5_000);
  1308 |   await expect(page.getByRole("button",{name:"取消这条待发消息"})).toHaveCount(0);
  1309 |   await expect(page.locator(".live-turn").filter({hasText:"SYNTHETIC later body has its own deadline"})).toHaveCount(0);
  1310 |   expect(state.messageBodies).toHaveLength(1);
  1311 |   const body=state.messageRoute!.request().postDataJSON();
  1312 |   await state.messageRoute!.fulfill({status:200,json:envelope(state,{receipt_id:body.client_request_id,
  1313 |     state:"VERIFIED",dispatch_happened:true,result:{text:"SYNTHETIC active reply survives expiry"}})});
  1314 |   await expect(page.getByText("SYNTHETIC active reply survives expiry",{exact:true})).toBeVisible();
  1315 |   expect(state.messageBodies).toHaveLength(1);
  1316 | });
  1317 | 
  1318 | test("SYNTHETIC long reply feedback binds full Unicode response without reposting its body",async({page})=>{
  1319 |   const state=await installMock(page);
  1320 |   const reply='🌙'.repeat(3000);
  1321 |   state.capabilities={conversation_history:true,conversation_feedback:true,long_reply_feedback:true};
  1322 |   state.history={items:[{exchange_record_id:'long-feedback-exchange',user_text:'SYNTHETIC long discussion',
  1323 |     reply_text:reply,created_at_us:1793026800000000}]};
  1324 |   let posts=0,checks=0,id='';
  1325 |   await page.route(`**${API}conversation/feedback`,async route=>{
  1326 |     posts++;const body=route.request().postDataJSON();id=body.idempotency_key;
  1327 |     expect(body.response_sha256).toBe(createHash('sha256').update(reply,'utf8').digest('hex'));
  1328 |     expect(body.sample.candidate_response).toBe('DEPENDENT_RECORD_BODY');
  1329 |     expect(body.sample.reason_tags).toEqual(['TOO_VERBOSE']);
  1330 |     expect(body.exchange_record_id).toBe('long-feedback-exchange');
  1331 |     expect(JSON.stringify(body)).not.toContain(reply);
  1332 |     await route.fulfill({status:200,json:envelope(state,{receipt_id:id,state:'UNKNOWN',dispatch_happened:true,result:{}})});
  1333 |   });
  1334 |   await page.route(`**${API}receipts/*`,async route=>{
  1335 |     checks++;expect(route.request().url()).toContain(id);
  1336 |     await route.fulfill({status:200,json:envelope(state,{receipt_id:id,state:'VERIFIED',dispatch_happened:true,
  1337 |       result:{state:'EXPLICIT_FEEDBACK_SAVED',delivery_proven:false}})});
  1338 |   });
  1339 |   await open(page,'chat');
  1340 |   await page.getByRole('button',{name:'评价这条回复'}).click();
  1341 |   await page.getByRole('button',{name:'保存：有点啰嗦'}).click();
  1342 |   await expect(page.getByText('保存结果待核验，不会重复提交',{exact:true})).toBeVisible();
  1343 |   await page.getByRole('button',{name:'核验这条评价'}).click();
  1344 |   await expect(page.getByText('评价已保存',{exact:true})).toBeVisible();
  1345 |   expect(posts).toBe(1);expect(checks).toBe(1);
  1346 |   expect(await page.evaluate(()=>JSON.stringify(Object.entries(localStorage)))).not.toContain(reply);
  1347 | });
  1348 | 
  1349 | 
  1350 | for (const scenario of ['SAVED','LOST_ACK','REJECTED','ANTHROPIC'] as const) test(`SYNTHETIC model setup: numeric UUID ${scenario}`, async ({page}) => {
  1351 |   const lostAck=scenario==='LOST_ACK';
  1352 |   const rejected=scenario==='REJECTED';
  1353 |   const state=await installMock(page);
  1354 |   state.capabilities={provider_configuration_write:true};
  1355 |   await page.addInitScript(()=>{
  1356 |     let next=0;
  1357 |     crypto.randomUUID=()=>`01234567-89ab-4cde-8fab-${String(++next).padStart(12,'0')}` as `${string}-${string}-${string}-${string}-${string}`;
  1358 |   });
  1359 |   const saved=structuredClone(providerSettings);
  1360 |   let configRevision=providerSettings.revision;
  1361 |   const commands:Record<string,unknown>[]=[];
  1362 |   let requestId='';let receiptReads=0;
  1363 |   await page.route(`**${API}views/settings`,route=>route.fulfill({status:200,json:envelope(state,
  1364 |     {...viewData(state,'settings'),provider_settings:{...saved,revision:configRevision}})}));
  1365 |   await page.route(`**${API}providers/commands`,async route=>{
  1366 |     const body=route.request().postDataJSON();
  1367 |     commands.push(body.command);requestId=body.client_request_id;
  1368 |     expect(body.command.expected_revision).toBe(configRevision);
  1369 |     if(rejected)return route.fulfill({status:200,json:envelope(state,{receipt_id:body.client_request_id,
  1370 |       state:'REJECTED',dispatch_happened:false,error:'PROVIDER_CONFIG_REVISION_CONFLICT'})});
  1371 |     if(body.command.provider)saved.providers.push({...body.command.provider,revision:1,secret_state:'MISSING'});
  1372 |     if(body.command.model)saved.models.push(body.command.model);
  1373 |     configRevision++;state.revision++;
  1374 |     if(lostAck)return route.abort('failed');
  1375 |     return route.fulfill({status:200,json:envelope(state,{receipt_id:body.client_request_id,state:'VERIFIED',
  1376 |       dispatch_happened:true,result:{configuration_revision:configRevision}})});
  1377 |   });
  1378 |   await page.route(`**${API}receipts/*`,route=>{
  1379 |     receiptReads++;
  1380 |     return route.fulfill({status:200,json:envelope(state,
  1381 |       {receipt_id:requestId,state:'VERIFIED',dispatch_happened:true,result:{configuration_revision:configRevision}})});
  1382 |   });
  1383 |   await open(page,'models');
  1384 |   const setup=page.locator('.next-setup');
  1385 |   if(scenario==='ANTHROPIC'){
> 1386 |     await setup.getByLabel('服务商',{exact:true}).selectOption({label:'Anthropic'});
       |                                                ^ Error: locator.selectOption: Test timeout of 30000ms exceeded.
  1387 |     await expect(setup.getByLabel('API 地址',{exact:true})).toHaveValue('https://api.anthropic.com/v1');
  1388 |     await setup.getByLabel('模型名称',{exact:true}).fill('synthetic-native-model');
  1389 |   }
  1390 |   await setup.getByRole('button',{name:'保存模型配置',exact:true}).click();
  1391 |   if(rejected){
  1392 |     await expect(page.getByText('最近操作 · 未执行',{exact:true})).toBeVisible();
  1393 |     expect(commands).toHaveLength(1);expect(configRevision).toBe(providerSettings.revision);expect(receiptReads).toBe(0);
  1394 |     await expect(page.getByText('最近操作 · 待确认',{exact:true})).toHaveCount(0);
  1395 |   }else if(lostAck){
  1396 |     await expect(page.getByText('最近操作 · 待确认',{exact:true})).toBeVisible();
  1397 |     await expect.poll(()=>commands.length).toBe(1);
  1398 |     await page.getByText('最近操作 · 待确认',{exact:true}).click();
  1399 |     await page.getByRole('button',{name:'核验当前回执',exact:true}).click();
  1400 |     await expect(page.getByText('最近操作 · 已完成',{exact:true})).toBeVisible();
  1401 |     expect(commands).toHaveLength(1);expect(receiptReads).toBe(1);
  1402 |   }else{
  1403 |     await expect(setup).toContainText('供应商与模型已保存');
  1404 |     expect(commands).toHaveLength(2);
  1405 |     expect(commands.map(c=>c.operation)).toEqual(['UPSERT_PROVIDER','UPSERT_MODEL']);
  1406 |     const provider=commands[0].provider as Record<string,unknown>;
  1407 |     const model=commands[1].model as Record<string,unknown>;
  1408 |     expect(provider.provider_profile_id).toMatch(/^provider\.[a-z][a-z0-9._-]+$/);
  1409 |     expect(model.model_profile_id).toMatch(/^model\.[a-z][a-z0-9._-]+$/);
  1410 |     expect(model.provider_profile_id).toBe(provider.provider_profile_id);
  1411 |     expect(provider.default_timeout_ms).toBe(120000);
  1412 |     expect(model.remote_model_id).toBe(scenario==='ANTHROPIC'?'synthetic-native-model':'deepseek-chat');
  1413 |     expect(provider.protocol).toBe(scenario==='ANTHROPIC'?'ANTHROPIC':'OPENAI_COMPATIBLE_CHAT');
  1414 |   }
  1415 |   expect(commands.some(c=>c.operation==='SET_CAPABILITY_ROUTE')).toBe(false);
  1416 |   expect(state.requests.some(r=>r.path==='providers/credentials/bind'||r.path==='providers/models')).toBe(false);
  1417 |   await noHorizontalOverflow(page);
  1418 | });
  1419 | 
  1420 | for(const outcome of ['MODEL_REJECTED','PROVIDER_UNKNOWN','MODEL_UNKNOWN'] as const) test(`SYNTHETIC model setup resumes original steps: ${outcome}`, async({page})=>{
  1421 |   const state=await installMock(page);state.capabilities={provider_configuration_write:true};
  1422 |   const saved=structuredClone(providerSettings);
  1423 |   const commands:Record<string,unknown>[]=[];
  1424 |   let pendingId='',reads=0,settled=false,loseRead=false;
  1425 |   await page.route(`**${API}views/settings`,route=>{
  1426 |     if(loseRead){loseRead=false;return route.abort('failed');}
  1427 |     return route.fulfill({status:200,json:envelope(state,{...viewData(state,'settings'),provider_settings:saved})});
  1428 |   });
  1429 |   await page.route(`**${API}providers/commands`,async route=>{
  1430 |     const body=route.request().postDataJSON(),command=body.command;commands.push(command);
  1431 |     expect(command.expected_revision).toBe(saved.revision);
  1432 |     if(outcome==='MODEL_REJECTED' && command.operation==='UPSERT_MODEL' && commands.length===2)
  1433 |       return route.fulfill({status:200,json:envelope(state,{receipt_id:body.client_request_id,state:'REJECTED',
  1434 |         dispatch_happened:false,error:'PROVIDER_CONFIG_REVISION_CONFLICT'})});
  1435 |     if(command.provider)saved.providers.push({...command.provider,revision:1,secret_state:'MISSING'});
  1436 |     if(command.model)saved.models.push(command.model);
  1437 |     saved.revision++;state.revision++;
  1438 |     const lost=outcome==='PROVIDER_UNKNOWN' && command.operation==='UPSERT_PROVIDER'
  1439 |       || outcome==='MODEL_UNKNOWN' && command.operation==='UPSERT_MODEL';
  1440 |     if(lost){pendingId=body.client_request_id;loseRead=outcome==='PROVIDER_UNKNOWN';return route.abort('failed');}
  1441 |     return route.fulfill({status:200,json:envelope(state,{receipt_id:body.client_request_id,state:'VERIFIED',
  1442 |       dispatch_happened:true,result:{configuration_revision:saved.revision}})});
  1443 |   });
  1444 |   await page.route(`**${API}receipts/*`,route=>{
  1445 |     expect(route.request().url().split('/').at(-1)).toBe(pendingId);reads++;
  1446 |     return route.fulfill({status:200,json:envelope(state,{receipt_id:pendingId,state:settled?'VERIFIED':'UNKNOWN',
  1447 |       dispatch_happened:settled?true:'UNKNOWN',...(settled?{result:{configuration_revision:saved.revision}}:{})})});
  1448 |   });
  1449 |   await open(page,'models');const setup=page.locator('.next-setup');
  1450 |   await setup.getByRole('button',{name:'保存模型配置',exact:true}).click();
  1451 |   if(outcome==='MODEL_REJECTED'){
  1452 |     await expect(setup.getByRole('button',{name:'继续配置',exact:true})).toBeVisible({timeout:1500});
  1453 |     await setup.getByRole('button',{name:'继续配置',exact:true}).click();
  1454 |     expect(reads).toBe(0);
  1455 |   }else{
  1456 |     if(outcome==='PROVIDER_UNKNOWN'){
  1457 |       await expect(setup).toContainText('已核验步骤保留');
  1458 |       await page.getByRole('button',{name:'刷新真实状态',exact:true}).click();
  1459 |       await go(page,'home');await go(page,'models','settings');
  1460 |     }
  1461 |     const resume=setup.getByRole('button',{name:'核验并继续配置',exact:true});
  1462 |     await expect(resume).toBeVisible({timeout:1500});
  1463 |     const count=commands.length;await resume.click();
  1464 |     await expect.poll(()=>reads).toBe(1);expect(commands).toHaveLength(count);
  1465 |     await expect(resume).toBeEnabled();settled=true;await resume.click();
  1466 |     await expect.poll(()=>reads).toBe(2);
  1467 |   }
  1468 |   await expect(setup).toContainText('供应商与模型已保存');
  1469 |   expect(commands.filter(c=>c.operation==='UPSERT_PROVIDER')).toHaveLength(1);
  1470 |   const modelCommands=commands.filter(c=>c.operation==='UPSERT_MODEL');
  1471 |   expect(modelCommands).toHaveLength(outcome==='MODEL_REJECTED'?2:1);
  1472 |   const provider=commands[0].provider as Record<string,unknown>;
  1473 |   expect(modelCommands.every(c=>(c.model as Record<string,unknown>).provider_profile_id===provider.provider_profile_id)).toBe(true);
  1474 |   if(modelCommands.length===2)expect((modelCommands[0].model as Record<string,unknown>).model_profile_id)
  1475 |     .toBe((modelCommands[1].model as Record<string,unknown>).model_profile_id);
  1476 |   expect(commands.some(c=>c.operation==='SET_CAPABILITY_ROUTE')).toBe(false);
  1477 |   expect(state.requests.some(r=>['messages','host/operations','providers/credential','providers/models'].includes(r.path))).toBe(false);
  1478 |   expect(await page.evaluate(()=>JSON.stringify(Object.entries(localStorage)))).not.toContain(String(provider.provider_profile_id));
  1479 |   await noHorizontalOverflow(page);
  1480 | });
  1481 | 
  1482 | for(const variant of ['VERIFIED','UNKNOWN','REJECTED','PROFILE_CHANGED','ANTHROPIC'] as const) test(`SYNTHETIC runtime budget: explicit consent and ${variant} receipt`,async({page})=>{
  1483 |   const outcome=variant==='ANTHROPIC'?'VERIFIED':variant;
  1484 |   const state=await installMock(page);
  1485 |   state.capabilities={provider_configuration_write:true,provider_runtime_configuration:true};
  1486 |   let configRevision=3,day=6,posts=0,receiptReads=0,requestId='',profileRevision=1;
```