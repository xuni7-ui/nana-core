# 显式目录续页与原生草稿一致性 — 2026-11-14

[实测 Advanced S7/多端产品，原A范围] 起点ce603d2（业务源f93后继）。原目录在8页/256个ID/256KiB/10秒机会用尽后只提示partial，无法继续。沿原provider_models.read_catalog/discover与已认证GET新增可选after_id，返回已校验next_after_id。保留原全部边界/NoRedirect/host allowlist/HOST_ADMIN/凭据清理/配置CAS与10秒读取节流，不自动重试，不调用模型、不改路由或注册。

每批仍只保留当前最多256ID；用户明确点击下一批，从同provider/profile_revision的真实last_id继续。旧SDK首轮GET兼容。无效/重复/凭据/非末行cursor不返回续页；一页超过可见上限时不凭last_id跳过未显示模型，仍partial+手填，非虚假完整目录。OpenAI-compatible不冒充支持原生cursor。

原V2 SDK/Web及Java有限分支同源传递参数；BFF回continued_after_id，SDK要求匹配：旧native桥若吞参数而重读第一页，明确unsupported并保留旧列表。Web按服务端retry_after_ms等待，仅手动读取，不阻塞聊天或轮询vendor。目录选择同步真实供应商协议；Anthropic草稿只开放现有COGNITION，避免沿用OpenAI草稿校验。选模不写配置，明确注册/路由/预算/付费授权仍独立。catalog/cursor仅当前页内存，无localStorage/Subject记忆或JS Key。

原缺口定向旧1fail/17deselected0.61s保留。新103后端相关45.05s，覆盖21目录/实际本地HTTP、原鉴权/配置/路由/timeout/native文字；vendor网络为fixture，真实API未调用。8页后显式再读2页正确结束，坏cursor无network、失配profile/unauth/节流与配置文件不变，oversized不跳漏。一次命令误写不存在测试路径0tests保留后纠正，不计能力失败或通过。

TS/Vite实际build，93单测；桌面1440及360/390/412的4场景各4视口共16pass20.8s，涵盖初始注册、partial手填、cooldown+手动续页+原生draft、旧桥丢cursor不假成功。首轮16pass23.6s亦保留。后续严格响应格式要求truncated明确bool，模拟下一页补false以匹配真实BFF，不放宽Core或断言。一次追加测试用错相对路径在工具回执报错，纠正后才真正运行新场景。

官方只读核对：[List Models](https://platform.claude.com/docs/en/api/models/list)定义after_id及默认20项/页；[API versions](https://platform.claude.com/docs/en/api/versioning)确认2026-10-21。沿用原生header，不改版本，不把文档读取算真实账号目录/模型资格。未读取聊天Key或私人数据。

Node24.19/npm11.9开发依赖按原lock恢复，无新依赖。Java桥仅源码映射，本环境未资格JDK编译器/Android平台，未Java/Gradle构建或手机验收；已安装旧409不因此升级。未新APK/匹配Core/Web包/CURRENT/发布/生产；原接口兼容和受控流程不是最终交付，真实自然度/长期成长未新增。

下一回原C情感/多动机与可靠结果反向学习主链；模型目录本轮不再重复大型回归。最终客户端确需更新时统一构建/核appId签名及同主体升级，保留Java/手机差额；原A–H全部未完成项继续。主入口README补最新分支与当前实现说明，旧V3只读草稿文字不再冒充现役状态。

复跑：tests/first_life_android_v2/test_provider_models.py、test_http_integration.py、test_provider_runtime_settings.py及tests/provider_routing（合103）；apps/nana-space npm run build / npm test / npx playwright test --config playwright.v3.config.ts --grep 'model catalog'。原TMPDIR=/dev/shm/PYTHONPATH=$PWD:$PWD/src。浏览器是受控HTTP fixture，不是实际手机或vendorAPI。
