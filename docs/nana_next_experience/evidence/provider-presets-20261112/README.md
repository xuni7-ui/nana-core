# Codex B · 同一份供应商预设用于简易和高级配置

[源码/实测，2026-11-12 Asia/Shanghai] 原总任务 B-P/P1，DOMAIN S5-C03 / Platform axis Advanced。独立分支基线 A `071669bd62a1a8f5fa812775ae8518c12b727ebc`；未修改原 C、Store、记忆、G 或 SubjectLoop。

原简易向导另写一份四项预设，而高级编辑器的 `newProviderDraft` 总给空地址。用户在高级配置选择同一 OpenAI/Anthropic/DeepSeek 后仍需手填本来已知的地址，两个入口也可能出现协议/字段漂移。现在两者复用 `providerPresets` 与同一 factory；沿用原向导已有的三个地址和 DeepSeek 模型建议，不引入新供应商协议或外部 SDK。

简易入口以稳定 preset ID 选择已有兼容协议项，共9项；未接通的 Gemini native、LOCAL 仍只作高级草稿。需要地域/部署信息的项保持空地址，显式手填，不能假定 endpoint。选择其他预设会清掉旧端点/模型，用户仍可改写地址；suggested model 是可修改的预填，不是自动检测或能力证明。向导标题改为中性“配置对话模型”，不将平台或开发者的角色名称写入本表单。

结果与复现：

```sh
cd apps/nana-space
npm test -- --run tests/provider-center.test.ts tests/provider-commands.test.ts
npm run build:live
npx playwright test --config playwright.v3.config.ts --grep 'provider presets:|model setup: numeric UUID|model setup resumes original steps:'
```

`unit20.txt`：20单测通过/884ms。`browser36.txt`：桌面/360/390/412共36通过/1.1m，包含双编辑器地址一致、手填地域/切换清空、原保存/Anthropic协议、Qwen自定义端点、丢ACK/明确拒绝与原回执续配、不误改默认路由、无横向溢出；为明确HTTP fixture，不是实际provider或手机。`build.txt`：TypeScript/Vite通过/3.90s。没有改动API/授权路径，相关后端及APK不重复构建。

每次页面仅从既有11项元数据筛选协议预设；没有新增网络、模型调用、持久化、依赖或审批层。原Web/native凭据路径、预算、CAS/UNKNOWN和实际运行状态保持；完整连接测试、普通Web密钥输入、模型能力发现及通用显示配置仍有独立差额。本批不声明整体模型向导完成、真实服务商资格、native编译、最终安装或生产部署。

回退只需撤销本批UI/factory/测试，无配置或主体数据迁移；旧接口、现有Provider ID和签名/package ID不改。源码表SHA256 `4dd8790ff9922b2b9c5c3239d04882265ebedd3ada7adfa24a5d055d5d834db6`，不自指。原代码修改，零第三方源码复制，许可现状不变。

集成候选更新：正常合入A bd48d40，保留其自身认知来源代码和完整账本；本批客户端源码指纹保持，未重复前端/发行验证。共享开发分支未修改。
