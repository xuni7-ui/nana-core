# Nana Core Phase III Entry 工程记录

基线 29872608b7b82fcca4a89a3be98fda8e8c65337f 与私有远端 dev/nana-core-v1-dev-validation 完全一致，原工作区干净。旧验收 final_junit.xml：227 pass/0fail/1skip，E12 NOT_RUN；main 18bc736d5e37fe3325e514a0e975403df2f97c9f。新分支 dev/nana-core-v1-phase3-entry；原生产/私有资料/凭据读取边界不变。

## M1 公网验收
[实测] 一次明确授权 https://example.com/ GET 经 Observation→ReadingCard Goal/Plan→Grant→ActionKernel→WebSourcePort→PublicHTTPTransport。新增 last_stage 可观察诊断，不放宽任何限制。DNS_FIRST / WEB_TIMEOUT，实际HTTP0、proxy连接0，read UNKNOWN、goal BLOCKED，未取得HTTP状态/正文/receipt。独立核验事件与Attempt持久存在；不自动重试。证据 public_probe.json。不是curl成功替代验收。未关闭TLS/绕过proxy/修改系统配置或使用生产代理。

[实测] 受影响公开传输41项及精确阶段测试1项共42 passed，协议夹具不算公网。当前DNS getaddrinfo 未能在5秒取得目标公共地址；代理TCP/TLS未运行，不能推断代理路径必然可用。

## M2 E12 就绪状态
待本节点核实与保存；不以fixture代替真实双模型。
