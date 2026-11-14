# 隔离复核入口

只操作全新owned DEV目录；不对生产/私人Store运行。依赖CPython3.12/Linux x86_64且SQLite>=3.51.3，保持系统库不动。

从固定d39 checkout，用原构建器与已核验wheelhouse：

```sh
python -m tools.nana_portable_cloud.build --revision d39c4e171fb162e30964d29e0b68cf0840499ea7 --output /tmp/nana-d39-rebuild --wheels /path/to/verified-wheelhouse --feature HOST_VAULT --feature PUBLIC_VIDEO_FRAMES
python -m tools.nana_portable_cloud.unpack /path/to/core.tar.gz --destination /tmp/nana-d39-fresh --sha256 8ab9a36b90066d1bf0b0b7272d9a4a64dfb8f4efa74f6a89f7e46004c04ee85f
/qualified/python3.12 -I -B /tmp/nana-d39-fresh/bootstrap.py install
/tmp/nana-d39-fresh/.venv/bin/python -I -B tools/nana_first_life_android_v2/installed_gateway_probe.py --bundle /tmp/nana-d39-fresh --work /tmp/nana-d39-fresh-probe --output /tmp/nana-d39-fresh-report.json --check-memory-notes
```

新startup probe路径位于同证据包installed-startup.py，参数--bundle新安装路径、--work全新owned路径、--output新JSON。回退前用当前版本关闭并保存后台模型选项、明确停机、保留原Store；不把true字段交旧严格reader。上文真实停机往返仅DEV实测，尚未作为生产升级命令资格。
