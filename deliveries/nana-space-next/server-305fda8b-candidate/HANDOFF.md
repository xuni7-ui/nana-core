# Nana Core 305fda8b 集成候选

固定 Core/BFF 源码 `305fda8b98ae0ae1040301eb758d91a27497f442`。两次构建一致，Core SHA256 `9131670899f88cf602fc70fb3d488889c3ab3876cdf5d447dfb21ca72d627303`，312 文件、263 原运行文件与 19 离线依赖。Web SHA256 `5963d5948fa51823541f4692f529efbbba4345b9ac075bef7af2abbd9de21243`，复用 B24 实际构建。固定提交与历史构建的 237 个客户端输入具有相同 Git blob。现役客户端选择仍为 409。

这次安装用 CPython 3.12.14 与 SQLite 3.53.1。33 项定向测试实际从安装槽运行，验证关系取舍、G 当前策略来源、视频时间戳与来源复用。另一个连续 DEV 场景使用同一身份依次通过原 BFF 反馈、笔记纠错重启撤回、原 C 私创作与探索、独立学习进入后续流式回复、虚拟 72 小时后的巩固召回与撤回。停机后 305fda8b → b196f5d → 305fda8b 的身份、谱系、未公开私念、边界与请求计数一致。该回退对应上述 DEV 场景与两个固定槽；读回过程不执行待办。测试使用 7 次本地合成认知，真实模型、手机、账号、真人自然度和实际跨日验收仍待。

```sh
sha256sum -c SHA256SUMS
PYTHON312=/absolute/path/to/qualified-python3.12
"$PYTHON312" nana-unpack.py nana-core-305fda8b-portable.tar.gz --sha256 9131670899f88cf602fc70fb3d488889c3ab3876cdf5d447dfb21ca72d627303 --destination /tmp/n305slot
/tmp/n305slot/install.sh "$PYTHON312"
/tmp/n305slot/.venv/bin/python -I -B installed_gateway_probe.py --bundle /tmp/n305slot --work /tmp/n305dev --output /tmp/n305-gateway.json --check-memory-notes
/tmp/n305slot/.venv/bin/python -I -B integrated_setup_probe.py --bundle /tmp/n305slot --work /tmp/n305dev --gateway /tmp/n305-gateway.json --output /tmp/n305-setup.json
/tmp/n305slot/.venv/bin/python -I -B installed_note_recall_probe.py --bundle /tmp/n305slot --work /tmp/n305dev --continue-gateway-result /tmp/n305-gateway.json --output /tmp/n305-growth.json --check-wire-reservations --check-retrieval-growth --check-streaming --report-usage
/tmp/n305slot/.venv/bin/python -I -B installed_living_memory_probe.py --bundle /tmp/n305slot --work /tmp/n305dev --prior /tmp/n305-growth.json --output /tmp/n305-living.json
```

在另一新槽离线安装固定 b196f5d 后，对上述已停机合成 DEV 用 `continuity-reader.py --bundle SLOT --work /tmp/n305dev --gateway /tmp/n305-gateway.json --setup /tmp/n305-setup.json --output REPORT` 分别读取新版、旧版和返回新版。包含原隐私与身份断言。备份与停机窗口按正式宿主合同核验后才能用于真实升级。CURRENT 的 Core 仍为 266272a，正式部署与真实验收记录在 PROJECT_BRAIN。
