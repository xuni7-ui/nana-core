# 目录读取的实际等待提示

[实测] S5-C03/S1-C04 Advanced，B模型配置候选的后续产品改进。原服务端已有10秒共享节流；原界面立即开放下一页，经新增行为测试确定仍可点（预期disabled、实际enabled）。现在成功目录响应附可选retry_after_ms，按原节流剩余时间计算0..10000ms，慢请求不重新施加固定10秒。客户端在组件内共享短暂倒计时，到期恢复按钮，无自动请求；已读选择/草稿不被阻止。旧服务端或未知元数据兼容原行为，服务端授权/节流继续为准。没有新增限制、网络读取、依赖、持久化、模型调用或Token节省声明。

验证命令：

```sh
cd apps/nana-space
npm run build:live
npm test -- --run tests/model-catalog.test.ts tests/v2-client.test.ts tests/native-continuation.test.ts
npx playwright test --config playwright.v3.config.ts --grep 'catalog cooldown:|native catalog:|catalog completion:'
# 测试时钟固定后的新增场景单独复验
npx playwright test --config playwright.v3.config.ts --grep 'catalog cooldown:'
cd ../..
PYTHONPATH=src:. python -m pytest tests/first_life_android_v2/test_provider_models.py -q
```

TS/Vite通过，19客户端测试通过/1.06s，24目录与真实本地认证HTTP测试通过/11.01s。浏览器原3组相关四视口12通过；新增倒计时场景初次3通过/1个测试clock.pauseAt竞态失败（模拟时刻已过去），固定确定性时钟后四视口4通过/11.1s。未修改产品断言。证明10秒前不发第二请求，10秒到期仅启用不自动重试，已读模型可继续填草稿，显式下一页再请求，移动无横向溢出。首次测试修改命令两次因工作目录错误未写文件；其后按绝对路径修正。初始HTTP2失败为缺少retry_after_ms，原断言/错误边界保留。本次不扩大重跑已通过的全部56配置场景或发行流程。

本地fixture与浏览器视口资格，非真实Provider/手机/生产；无APK。回滚仅去掉可选提示，不影响已存配置/Key/协议。源码指纹不代表已运行部署。

接续核对：A后继b016e6c仅前台/静默恢复及账本/任务增补，正常合并后本批6份源码指纹逐项一致，A完整账本为前缀；无新模型接口冲突，复用上述验证。
