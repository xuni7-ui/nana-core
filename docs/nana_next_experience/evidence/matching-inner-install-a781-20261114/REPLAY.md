# 新owned DEV复核

先从实际固定a781取得源码，所有--work/--destination/--output须全新，不操作生产或私人Store。wheelhouse须按requirements.lock核SHA；系统库不动。

```sh
python -m tools.nana_portable_cloud.build --revision a7815ce08d0664d9c6467b691fde5d7f2e11fd91 --output /tmp/nana-a781-fresh-build --wheels /path/to/verified-wheelhouse --feature HOST_VAULT --feature PUBLIC_VIDEO_FRAMES
python -m tools.nana_portable_cloud.unpack /path/to/core.tar.gz --destination /tmp/nana-a781-fresh --sha256 2125e65e0ee4a5ffb29282bbb4d671042922dc44a3c4ab1a8d0ac47226f0afad
/qualified/python3.12 -I -B /tmp/nana-a781-fresh/bootstrap.py install
/tmp/nana-a781-fresh/.venv/bin/python -I -B docs/nana_next_experience/evidence/matching-inner-install-a781-20261114/installed-inner-life.py --bundle /tmp/nana-a781-fresh --work /tmp/nana-a781-fresh-home --output /tmp/nana-a781-fresh-inner.json --keep-source
```

升级/回退原则与本批实际步骤一致：保留同一个DEV home，不genesis、不回滚DB、不覆盖封签源码；用当前版本显式关闭并保存后台模型选项，再停机，才允许旧严格reader打开。旧版本不支持V4的生活功能，本批只资格停止态附着/返回和原状态未丢；不能替生产宿主写未验证的升级命令。运行原stopped-host-return.py仅对本探针fresh DEV，--work传home，--prior传inner.json。随后installed-withdraw.py核真实ACTIVE状态再撤回；命令中的bundle/home/prior/report都必须保持同一绑定。原完整安装/回退资料见packaging/portable/docs/QUICKSTART.md及各匹配安装证据，不重下旧474MB V4包。
