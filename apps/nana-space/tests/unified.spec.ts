import { test, expect } from "@playwright/test";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
test("V4 real connection rejects undispatched model calls and respects a topic boundary", async ({ page }, info) => {
  const target = JSON.parse(await readFile(process.env.NANA_V2_TARGET!, "utf8"));
  await page.goto("/index.html?source=live#chat");
  await page.getByLabel("Subject ID", { exact: true }).fill(target.subject_id);
  await page.getByLabel("会话口令", { exact: true }).fill("TEST_ONLY_NOT_SECRET_web_password");
  await page.getByRole("button", { name: "安全连接", exact: true }).click();
  const remember = page.getByLabel("记住这次共同经历", { exact: false });
  await expect(remember).not.toBeChecked();
  await page.getByLabel("和奈奈说点什么", { exact: true }).fill("PROJECT: source-backed current progress please");
  const receipt = page.waitForResponse(r => r.url().endsWith("/messages") && r.request().method() === "POST");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  const rejected = await (await receipt).json();
  expect(rejected.data.state).toBe("REJECTED");
  expect(rejected.data.dispatch_happened).toBe(false);
  await expect(page.getByText("这次未提交", { exact: false })).toBeVisible();
  await page.getByLabel("和奈奈说点什么", { exact: true }).fill("先不聊这个话题");
  const boundary = page.waitForResponse(r => r.url().endsWith("/messages") && r.request().method() === "POST");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  const respected = await (await boundary).json();
  expect(respected.data.state).toBe("VERIFIED");
  expect(respected.data.result.mode).toBe("RESPECT_BOUNDARY");
  await mkdir("test-results/unified-screens", { recursive: true });
  await page.screenshot({ path: `test-results/unified-screens/${info.project.name}-v4-chat.png`, fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
});
test("V3 real Core provider configuration, model route and backup receipt projection", async ({
  page,
}, info) => {
  const target = JSON.parse(
    await readFile(process.env.NANA_V2_TARGET!, "utf8"),
  );
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const results: any[] = [];
  page.on("response", async (r) => {
    if (r.url().endsWith("/providers/commands")) results.push(await r.json());
  });
  await page.goto("/index.html?source=live#models");
  await page.getByLabel("Subject ID", { exact: true }).fill(target.subject_id);
  await page
    .getByLabel("会话口令", { exact: true })
    .fill("TEST_ONLY_NOT_SECRET_web_password");
  await page.getByRole("button", { name: "安全连接", exact: true }).click();
  await expect(
    page.getByText("宿主已开放配置", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "添加供应商草稿", exact: true })
    .click();
  const suffix = info.project.name.replaceAll("-", "");
  await page
    .getByLabel("供应商配置 ID", { exact: true })
    .fill(`provider.${suffix}`);
  await page.getByLabel("模型配置 ID", { exact: true }).fill(`model.${suffix}`);
  await page
    .getByLabel("已确认的 Base URL", { exact: true })
    .fill("https://provider.example/v1");
  await page
    .getByLabel("远端 Model ID", { exact: true })
    .fill("synthetic.declared.not.called");
  await page.getByRole("button", { name: "应用新供应商", exact: true }).click();
  await expect.poll(() => results.length).toBe(1);
  expect(results[0].data.state).toBe("VERIFIED");
  await expect(
    page.getByRole("button", { name: "注册模型配置", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "注册模型配置", exact: true }).click();
  await expect.poll(() => results.length).toBe(2);
  expect(results[1].data.state).toBe("VERIFIED");
  await page.getByLabel("关闭供应商草稿", { exact: true }).click();
  const panel = page
    .locator(".v3-capability-card")
    .filter({
      has: page.getByRole("heading", { name: "文本与推理", exact: true }),
    });
  await panel.locator("summary").click();
  await panel
    .getByLabel("文本与推理 Primary", { exact: true })
    .selectOption(`model.${suffix}`);
  await panel.getByRole("button", { name: "应用此路由", exact: true }).click();
  await expect.poll(() => results.length).toBe(3);
  expect(results[2].data.state).toBe("VERIFIED");
  expect(
    results.every(
      (r) =>
        r.data.result.network_calls === 0 &&
        r.data.result.live_permission_granted === false,
    ),
  ).toBe(true);
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    )
    .toBe(true);
  await mkdir("test-results/unified-screens", { recursive: true });
  await page.screenshot({
    path: `test-results/unified-screens/${info.project.name}-models.png`,
    fullPage: true,
  });
  await page.goto("/index.html?source=live#backup");
  await expect(
    page.getByText("服务端回执投影", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("NOT_OBSERVED", { exact: false }).first(),
  ).toBeVisible();
  expect(errors).toEqual([]);
  expect(
    await page.evaluate(() =>
      Object.entries(localStorage).some(([k, v]) =>
        /token|password|secret|refresh/i.test(k + v),
      ),
    ),
  ).toBe(false);
});

test("explicit private context uses the real Core and current device scope", async ({ page }, info) => {
  const target = JSON.parse(await readFile(process.env.NANA_V2_TARGET!, "utf8"));
  test.skip(!target.private_context_qualification, "Explicit synthetic private-context harness required");
  await page.goto("/index.html?source=live#chat");
  await page.getByLabel("Subject ID", {exact: true}).fill(target.subject_id);
  await page.getByLabel("会话口令", {exact: true}).fill("TEST_ONLY_NOT_SECRET_web_password");
  await page.getByRole("button", {name: "安全连接", exact: true}).click();
  const personal = page.getByLabel("本次包含个人内容", {exact: false});
  await expect(personal).not.toBeChecked();
  await personal.check();
  await page.getByLabel("记住这次共同经历", {exact: false}).check();
  await page.getByLabel("和奈奈说点什么", {exact: true}).fill("先不聊这个话题");
  const request = page.waitForResponse(r => r.url().endsWith("/messages") && r.request().method() === "POST");
  await page.getByRole("button", {name: "发送", exact: true}).click();
  const response = await request, result = await response.json();
  expect(response.request().postDataJSON().privacy_class).toBe("PERSONAL");
  expect(result.data.state).toBe("VERIFIED");
  expect(result.data.result.raw_body_persisted).toBe(true);
  const projected = page.waitForResponse(r => r.url().endsWith("/views/memories"));
  await page.goto("/index.html?source=live#memories");
  const projection = await projected;
  const data = await projection.json();
  expect(data.privacy_scope).toContain("PERSONAL");
  expect(data.data.memories.some((m: any) => m.memory_id === result.data.result.message_memory_id && m.privacy_class === "PERSONAL")).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await mkdir("test-results/private-screens", {recursive: true});
  await page.screenshot({path: `test-results/private-screens/${info.project.name}-private-memory.png`, fullPage: true});
});

test("V4 real Core runtime budget saves through TLS Web without a model call or restart",async({page},info)=>{
  const target=JSON.parse(await readFile(process.env.NANA_V2_TARGET!,"utf8"));
  expect(target.runtime_budget_qualification).toBe(true);
  const errors:string[]=[],writes:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{if(request.method()!=='GET')writes.push(new URL(request.url()).pathname);});
  await page.goto('/index.html?source=live#models');
  await page.getByLabel('Subject ID',{exact:true}).fill(target.subject_id);
  await page.getByLabel('会话口令',{exact:true}).fill('TEST_ONLY_NOT_SECRET_web_password');
  await page.getByRole('button',{name:'安全连接',exact:true}).click();
  await expect(page.locator('.next-setup')).toBeVisible();
  const before=await(await page.request.get('/api/nana-space/v2/providers/runtime')).json();
  expect(before.subject_id).toBe(target.subject_id);
  expect(before.data.network_calls).toBe(0);
  const cookie=(await page.context().cookies()).find(c=>c.name==='__Host-nana_v2');
  expect(cookie?.httpOnly).toBe(true);expect(cookie?.secure).toBe(true);expect(cookie?.sameSite).toBe('Strict');
  const setup=page.locator('.next-setup');
  const providerSaved=page.waitForResponse(response=>response.url().endsWith('/providers/commands')
    && response.request().method()==='POST' && response.request().postDataJSON().command.operation==='UPSERT_PROVIDER');
  await setup.getByRole('button',{name:'保存模型配置',exact:true}).click();
  const profileResponse=await providerSaved;
  expect((await profileResponse.json()).data.state).toBe('VERIFIED');
  const pid=profileResponse.request().postDataJSON().command.provider.provider_profile_id;
  await expect(setup).toContainText('供应商与模型已保存');
  const panel=page.getByLabel('模型运行预算',{exact:true});
  await expect(panel).toBeVisible();
  await panel.getByLabel('连接服务商',{exact:true}).selectOption(pid);
  const day=7+['desktop','phone-360','phone-390','phone-412'].indexOf(info.project.name);
  await panel.getByLabel('每日请求上限',{exact:true}).fill(String(day));
  const save=panel.getByRole('button',{name:'保存运行预算',exact:true});
  await expect(save).toBeDisabled();
  await panel.getByRole('checkbox',{name:/我允许向 api.deepseek.com/}).check();
  const changed=page.waitForResponse(response=>response.url().endsWith('/providers/runtime') && response.request().method()==='POST');
  await save.click();
  const response=await changed,value=await response.json();
  expect(value.subject_id).toBe(target.subject_id);
  expect(value.lineage_binding).toBe(target.lineage_binding);
  expect(value.data.state).toBe('VERIFIED');
  expect(value.owner_epoch).toBe(before.owner_epoch);
  expect(value.data.result).toMatchObject({provider_profile_id:pid,provider_host:'api.deepseek.com',
    runtime_applied:false,restart_required:true,network_calls:0,credential_resolved:false,subject_history_changed:false,
    existing_mission_caps_preserved:true,live_model_test:'NOT_RUN'});
  await expect(page.getByText('运行预算与连接域名已保存。请明确重启以应用；尚未调用模型。',{exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('模型运行预算',{exact:true}).getByLabel('每日请求上限',{exact:true})).toHaveValue(String(day));
  const current=await(await page.request.get('/api/nana-space/v2/providers/runtime')).json();
  expect(current.subject_id).toBe(target.subject_id);expect(current.lineage_binding).toBe(target.lineage_binding);
  expect(current.data.provider_hosts).toContain('api.deepseek.com');
  expect(current.data.limits.total_calls).toBe(before.data.limits.total_calls);
  expect(current.data.limits.total_reserved_cost_micro).toBe(before.data.limits.total_reserved_cost_micro);
  expect(current.data.network_calls).toBe(0);
  expect(writes.filter(path=>path.endsWith('/providers/runtime'))).toHaveLength(1);
  expect(writes.some(path=>['/messages','/providers/credential','/host/confirmations','/host/operations'].some(end=>path.endsWith(end)))).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  expect(errors).toEqual([]);
});

test("V4 real Core model setup resumes its original receipt after lost ACK",async({page})=>{
  const target=JSON.parse(await readFile(process.env.NANA_V2_TARGET!,"utf8"));
  const errors:string[]=[],commands:Record<string,any>[]=[],writes:string[]=[];
  let receiptId='',receiptReads=0;
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{
    const path=new URL(request.url()).pathname;
    if(request.method()==='GET' && path.endsWith('/receipts/'+receiptId))receiptReads++;
    if(request.method()!=='GET')writes.push(path);
  });
  // Fault injection only: each POST reaches the actual TLS BFF/Core and its
  // real ledger. Drop exactly the first successful ACK; fabricate no result.
  await page.route('**/api/nana-space/v2/providers/commands',async route=>{
    commands.push(route.request().postDataJSON());
    const response=await route.fetch(),value=await response.json();
    expect(value.data.state).toBe('VERIFIED');
    if(commands.length===1){receiptId=value.data.receipt_id;return route.abort('failed');}
    return route.fulfill({response});
  });
  await page.goto('/index.html?source=live#models');
  await page.getByLabel('Subject ID',{exact:true}).fill(target.subject_id);
  await page.getByLabel('会话口令',{exact:true}).fill('TEST_ONLY_NOT_SECRET_web_password');
  await page.getByRole('button',{name:'安全连接',exact:true}).click();
  const setup=page.locator('.next-setup');await expect(setup).toBeVisible();
  const before=await(await page.request.get('/api/nana-space/v2/views/settings')).json();
  await setup.getByRole('button',{name:'保存模型配置',exact:true}).click();
  await expect(setup.getByRole('button',{name:'核验并继续配置',exact:true})).toBeEnabled();
  expect(commands).toHaveLength(1);
  await setup.getByRole('button',{name:'核验并继续配置',exact:true}).click();
  await expect(setup).toContainText('供应商与模型已保存');
  expect(receiptReads).toBe(1);expect(commands).toHaveLength(2);
  expect(commands.map(body=>body.command.operation)).toEqual(['UPSERT_PROVIDER','UPSERT_MODEL']);
  const pid=commands[0].command.provider.provider_profile_id,mid=commands[1].command.model.model_profile_id;
  expect(commands[1].command.model.provider_profile_id).toBe(pid);
  const after=await(await page.request.get('/api/nana-space/v2/views/settings')).json();
  expect(after.subject_id).toBe(target.subject_id);expect(after.lineage_binding).toBe(target.lineage_binding);
  expect(after.owner_epoch).toBe(before.owner_epoch);
  const settings=after.data.provider_settings,prior=before.data.provider_settings;
  expect(settings.providers.length).toBe(prior.providers.length+1);
  expect(settings.models.length).toBe(prior.models.length+1);
  expect(settings.providers.filter((p:any)=>p.provider_profile_id===pid)).toHaveLength(1);
  expect(settings.models.filter((m:any)=>m.model_profile_id===mid)).toHaveLength(1);
  expect(settings.routes).toEqual(prior.routes);
  expect(writes.some(path=>['/messages','/providers/credential','/providers/models','/host/operations','/host/confirmations'].some(end=>path.endsWith(end)))).toBe(false);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  expect(errors).toEqual([]);
});

test("V4 real TLS queued sequence preserves three original C inputs in one reply",async({page})=>{
  const target=JSON.parse(await readFile(process.env.NANA_V2_TARGET!,"utf8"));
  expect(target.synthetic_sequence_qualification).toBe(true);
  const marker=join(dirname(process.env.NANA_V2_TARGET!),'release.fixture');
  expect(target.synthetic_release_marker).toBe(marker);
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/index.html?source=live#chat');
  await page.getByLabel('Subject ID',{exact:true}).fill(target.subject_id);
  await page.getByLabel('会话口令',{exact:true}).fill('TEST_ONLY_NOT_SECRET_web_password');
  await page.getByRole('button',{name:'安全连接',exact:true}).click();
  const input=page.getByLabel('和奈奈说点什么');await expect(input).toBeEnabled();
  const before=await(await page.request.get('/api/nana-space/v2/bootstrap')).json();
  expect(before.capabilities.conversation_sequence).toBe(true);
  expect(before.data.host.owner_managed).toBe(false); // Explicit in-process qualification owner.
  await input.fill('SYNTHETIC first stream held for queued inputs');
  await page.getByRole('button',{name:'发送',exact:true}).click();
  await expect(page.getByLabel('生成中的临时回复',{exact:true})).toBeVisible();
  for(const text of ['SYNTHETIC first additional fact','SYNTHETIC second additional fact','SYNTHETIC third additional fact']){
    await input.fill(text);await page.getByRole('button',{name:'发送',exact:true}).click();
  }
  await expect(page.getByRole('button',{name:'取消这条待发消息'})).toHaveCount(3);
  const completed=page.waitForResponse(response=>response.url().endsWith('/messages/sequence') && response.request().method()==='POST');
  await writeFile(marker,'release');
  const response=await completed,value=await response.json(),body=response.request().postDataJSON();
  expect(response.status()).toBe(200);expect(value.data.state).toBe('VERIFIED');
  expect(value.subject_id).toBe(target.subject_id);expect(value.lineage_binding).toBe(target.lineage_binding);
  expect(value.owner_epoch).toBe(before.owner_epoch);
  expect(body.messages).toHaveLength(3);
  expect(value.data.result.coalesced).toBe(true);expect(value.data.result.external_delivery).toBe(false);
  const rows=value.data.result.results;
  expect(rows.map((r:any)=>r.client_message_id)).toEqual(body.messages.map((r:any)=>r.client_message_id));
  expect(rows.slice(0,2).every((r:any)=>r.text===null && r.render_state==='DEFERRED_TO_CONTINUATION')).toBe(true);
  expect(rows[2].respond_to_memory_ids).toEqual(rows.map((r:any)=>r.message_memory_id));
  await expect(page.locator('.live-reply').filter({hasText:'SYNTHETIC combined response to 3'})).toHaveCount(1);
  await expect(page.locator('.live-reply')).toHaveCount(2);
  await expect(page.getByText('回应见下方',{exact:true})).toHaveCount(2);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  expect(await page.evaluate(()=>JSON.stringify(Object.entries(localStorage)))).not.toContain('SYNTHETIC first additional fact');
  expect(errors).toEqual([]);
});

test('V4 real TLS concurrent continuation replaces an unsent draft using original C sources',async({page})=>{
  const target=JSON.parse(await readFile(process.env.NANA_V2_TARGET!,'utf8'));
  expect(target.synthetic_continuation_qualification).toBe(true);
  const marker=join(dirname(process.env.NANA_V2_TARGET!),'release.fixture');
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/index.html?source=live#chat');
  await page.getByLabel('Subject ID',{exact:true}).fill(target.subject_id);
  await page.getByLabel('会话口令',{exact:true}).fill('TEST_ONLY_NOT_SECRET_web_password');
  await page.getByRole('button',{name:'安全连接',exact:true}).click();
  const input=page.getByLabel('和奈奈说点什么');await expect(input).toBeEnabled();
  const before=await(await page.request.get('/api/nana-space/v2/bootstrap')).json();
  expect(before.capabilities.conversation_continuation).toBe(true);
  expect(before.data.host.owner_managed).toBe(false);
  const rootResponse=page.waitForResponse(r=>r.url().endsWith('/messages/stream') && r.request().method()==='POST');
  await input.fill('SYNTHETIC TLS original thought before a new fact');
  await page.getByRole('button',{name:'发送',exact:true}).click();
  await expect(page.getByLabel('生成中的临时回复',{exact:true})).toBeVisible();
  const rootHttp=await rootResponse,rootBody=rootHttp.request().postDataJSON();
  const childRequest=page.waitForRequest(r=>r.url().endsWith('/messages') && r.method()==='POST');
  const childResponse=page.waitForResponse(r=>r.url().endsWith('/messages') && r.request().method()==='POST');
  await input.fill('SYNTHETIC TLS added fact while the draft is still unsent');
  await page.getByRole('button',{name:'发送',exact:true}).click();
  const childBody=(await childRequest).postDataJSON();
  expect(childBody.continuation_of).toBe(rootBody.client_request_id);
  expect(childBody.client_request_id).not.toBe(rootBody.client_request_id);
  await expect.poll(async()=>{
    const response=await page.request.get('/api/nana-space/v2/receipts/'+childBody.idempotency_key);
    return response.ok()?(await response.json()).data.state:null;
  }).toBe('RUNNING');
  await expect(page.getByLabel('生成中的临时回复',{exact:true})).toHaveCount(0);
  await writeFile(marker,'release');
  const childHttp=await childResponse,child=(await childHttp.json()).data;
  // The SDK cancels its NDJSON reader after the terminal frame. Chromium then
  // need not retain that response body for DevTools; independently read the
  // same original receipt, and require the UI to have accepted its stream below.
  await expect.poll(async()=>{
    const row=await page.request.get('/api/nana-space/v2/receipts/'+rootBody.idempotency_key);
    return row.ok()?(await row.json()).data.state:null;
  }).toBe('VERIFIED');
  const root=(await(await page.request.get('/api/nana-space/v2/receipts/'+rootBody.idempotency_key)).json()).data;
  expect(rootHttp.status()).toBe(200);expect(childHttp.status()).toBe(200);
  expect(root.state).toBe('VERIFIED');expect(child.state).toBe('VERIFIED');
  expect(root.result.text).toBeNull();expect(root.result.reply_response_id).toBeNull();
  expect(root.result.render_state).toBe('DEFERRED_TO_CONTINUATION');
  expect(child.result.respond_to_memory_ids).toEqual([root.result.message_memory_id,child.result.message_memory_id]);
  expect(child.result.reply_response_id).toBeTruthy();expect(child.result.external_delivery).toBe(false);
  await expect(page.locator('.live-reply').filter({hasText:'SYNTHETIC combined response to 2'})).toHaveCount(1);
  await expect(page.locator('.live-reply')).toHaveCount(1);
  await expect(page.getByText('回应见下方',{exact:true})).toHaveCount(1);
  const saved=(await(await page.request.get('/api/nana-space/v2/receipts/'+childBody.idempotency_key)).json()).data;
  expect(saved.result).toEqual(child.result);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  expect(await page.evaluate(()=>JSON.stringify(Object.entries(localStorage)))).not.toContain('SYNTHETIC TLS added fact');
  expect(errors).toEqual([]);
});
