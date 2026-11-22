# Nana Core 2864240 集成候选

固定 Core/BFF 源码 `2864240b50a86caa49441663a1775ce69019a9b8`。两次构建一致，Core SHA256 `9cd4b6a136c8e0c6cfb9fac5c24bc4ad6d6ad86e5285343374dbe1620eca9cba`，313 文件、264 原运行文件与 19 离线依赖。Web SHA256 `83e8015a0c55024480d11a49793e5c0a894b252cd6e6dfac02b0655265a3ea9f`，采用 B26 已合入源码的实际 TypeScript/Vite 构建。固定提交与历史构建的 237 个客户端输入具有相同 Git blob。现役客户端选择仍为 409。

这次安装用 CPython 3.12.14 与 SQLite 3.53.1。39 项定向测试实际从安装槽运行，验证关系取舍、G 当前策略与迁移、视频时间覆盖与当前来源。另一个连续 DEV 场景使用同一身份依次通过原 BFF 反馈、笔记纠错重启撤回、原 C 私创作与探索、独立学习进入后续流式回复、虚拟 72 小时后的巩固召回与撤回。停机后 2864240 → 305fda8b → 2864240 的身份、谱系、未公开私念、边界与请求计数一致。该回退对应上述 DEV 场景与两个固定槽；读回过程不执行待办。测试使用 7 次本地合成认知，真实模型、手机、账号、真人自然度和实际跨日验收仍待。

```sh
sha256sum -c SHA256SUMS
PYTHON312=/absolute/path/to/qualified-python3.12
"$PYTHON312" nana-unpack.py nana-core-2864240-portable.tar.gz --sha256 9cd4b6a136c8e0c6cfb9fac5c24bc4ad6d6ad86e5285343374dbe1620eca9cba --destination /tmp/n286bslot
/tmp/n286bslot/install.sh "$PYTHON312"
/tmp/n286bslot/.venv/bin/python -I -B installed_gateway_probe.py --bundle /tmp/n286bslot --work /tmp/n286bdev --output /tmp/n286b-gateway.json --check-memory-notes
/tmp/n286bslot/.venv/bin/python -I -B integrated_setup_probe.py --bundle /tmp/n286bslot --work /tmp/n286bdev --gateway /tmp/n286b-gateway.json --output /tmp/n286b-setup.json
/tmp/n286bslot/.venv/bin/python -I -B installed_note_recall_probe.py --bundle /tmp/n286bslot --work /tmp/n286bdev --continue-gateway-result /tmp/n286b-gateway.json --output /tmp/n286b-growth.json --check-wire-reservations --check-retrieval-growth --check-streaming --report-usage
/tmp/n286bslot/.venv/bin/python -I -B installed_living_memory_probe.py --bundle /tmp/n286bslot --work /tmp/n286bdev --prior /tmp/n286b-growth.json --output /tmp/n286b-living.json
```

在另一新槽离线安装固定 305fda8b 后，对上述已停机合成 DEV 用 `continuity-reader.py --bundle SLOT --work /tmp/n286bdev --gateway /tmp/n286b-gateway.json --setup /tmp/n286b-setup.json --output REPORT` 分别读取新版、旧版和返回新版。包含原隐私与身份断言。备份与停机窗口按正式宿主合同核验后才能用于真实升级。CURRENT 的 Core 仍为 266272a，正式部署与真实验收记录在 PROJECT_BRAIN。
