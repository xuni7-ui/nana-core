# 本地 Ollama 最小适配

直接复用官方 Python SDK，不加载 Nana Core、不创建模型管理器，也不下载或启动模型。环境需已有运行中的 Ollama 服务和模型，安装 `ollama==0.6.3`。示例：

```python
from tools.nana_next_experience.experiments.local_ollama import LocalOllama

with LocalOllama('http://127.0.0.1:11434', timeout=120) as client:
    names = client.models()                 # 服务实际返回的模型名
    print(names)
    model = names[0]                        # 调用方明确选择，空列表需自行处理
    reply = client.chat(model, '你好')
    print(reply.message.content)
    for part in client.chat(model, '再说一句', stream=True):
        print(part.message.content or '', end='', flush=True)
        if part.done:
            print('\n完成')
```

`chat` 返回 SDK 原生响应或响应迭代器，调用方须检查 `done`，流中断不是完成，也不自动重发。超时为 SDK/HTTP 超时，不是整个生成过程的硬时限。服务地址必须是显式本地回环 HTTP origin 且带端口；不跟随重定向或使用代理环境，并在实际发请求前移除 SDK 可能继承的 `OLLAMA_API_KEY`，避免向本地进程泄露无关凭据。回环地址**不能认证进程身份**，端口可被其他进程复用，宿主自行决定信任对象和权限；本实验不宣称解决 PR #29 的身份/授权问题，不修改生产 Provider 配置。

验证：安装官方 SDK 0.6.3，以本地 HTTP 测试替身验证目录、指定名称请求、非流式/流式响应和不发送环境密钥。另从 [Ollama 官方发行页](https://github.com/ollama/ollama/releases/tag/v0.1.32) 取得历史独立 Linux 二进制，在隔离目录和 `127.0.0.1:19134` 启动一次性服务。实测 `/api/version` 返回 `0.1.32`，`LocalOllama.models()` 返回空目录，随后关闭服务。下载二进制实测 SHA-256 为 `539e8e1df2f74263fc56e0939cfc3f014a1addf02b07a06cae5cb42d810eb746`，用于复现该次测试。

模型注册表与 Hugging Face 的出站访问返回 403，未下载权重。真实服务已验证目录读取，非流式和流式仍需已有权重后各实际执行一次并核对 `done`。预计运行验证约 0.5–1 小时，不包括模型下载及授权时间。
