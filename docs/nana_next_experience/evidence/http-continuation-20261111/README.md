# 原 HTTP 生成中接续接纳 — S7/S1/S2，原 Advanced 主任务增量

基线26970a4，显式隔离 Core opt-in，真实两个独立认证HTTP→原BFF/ledger→UDS/原ControlServer/C/Store→localhost合成provider。不是两个客户端串行夹具，也不是第二主体。原C在首个理解请求仍阻塞时收到补充输入，审阅两条、双源下一回复，3实际fixture调用；Root仅审阅无speech/无response ID，child独立回执，有真实措辞编号，0真实模型/社交/生产动作。

MessageRequest新增可选continuation_of；None省略保持旧payload指纹，三生成契约同步。能力仅原当前身份/owner/source且Core显式开启时advertise；旧Core和默认关闭保持false。一个已认证parent允许一个同principal（含kind/device/roles/generation）/surface/thread/topic/privacy/run/owner的未保留child。先原ledger prior/CAS，重复只读回执；过期窗口/无父/已占槽/错误上下文/新身份/旧owner/过大wire拒绝在reserve前；显式保留消息不接续。正常写锁继续覆盖Root与已接纳child，child单独有界transport lane，原pause/revoke/stop priority lane不被其占用。child原Core自决、预算/权限逐次检查，不借parent授予权限或免费调用。

消息回执隐私锚捕获于整个dispatch及等待前，最终旧正文遇watermark改变被遮蔽；测试注入watermark改变，**非实际并发withdraw资格**，已有真实撤回在相关回归。第一次误将所有操作结束改为_receipt导致反馈UNKNOWN提前reconcile，原3失败保留，收窄为MESSAGE才隐私读取，原反馈时序恢复，无断言放宽。

证据：首capability缺失1fail；接通后显式空responseID1fail并补原Core投影；正向1pass2.17s；范围11pass10.44s；69相关63.22s（并发/序列/原队列/授权）通过；反馈3fail/19pass22.93s保留→最终auth/HTTP/stream22pass20.69s；最终并发13pass12.93s含duplicate无重发/只1pending/不同身份scope拒绝/priority pause/整个parent wait隐私锚。schema生成、TypeScript成功。operator错test_contract.py文件路径导致0测试，单独保留，不算源码失败/通过。基线269独立CI实核155Core126.98s、88unit、120browser1.6m、Vite2.46s SUCCESS；不冒充本批或最新全仓。

当前仅后端已实现/受控测试。Core默认opt-in FALSE，Web仍串行drain，故没有产品启用/TLS并发/新安装/native手机/自然度/长期成长资格。Java源码已核messageStream专用worker及单stream guard、普通request独立Bridge executor；仅证明下一步one stream+buffered child路径存在，不是设备证明。NEXT: Web接续来源绑定、one child lifecycle/UNKNOWN/过期/logout/安全fallback，仅确知reserve前关闭窗口才可转普通队列，后续真实TLS联调，再原CLI受控启用。原A–H全部未完继承；CURRENT266+409不变。
