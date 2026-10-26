# 原合格镜像交接（不是重建）

Image ID: `sha256:0d8426762cef4bc19b12a7930361fbc9a9c4096628ffb0ee4024407ec5a1a5ee`

Platform: linux/amd64; Config.User: 999:999
Original docker-save tar: 589073920 bytes
SHA256: `4ef8918a75db986c5c4dd63b8e9c9fc585308be9a8414159aaa8f92c855dae17`
Gzip transport: 255800659 bytes;9 parts<=28MiB

下载此目录所有9片及image-transfer.json；清单SHA256：
`a81d5e1f6b69a3397bc7b9029aa0ebd6a494c9c80b64f3d0df3f3c4676a18dc9`

每片直接下载：

- [nana-firstlife-0d842676.tar.gz.part001](nana-firstlife-0d842676.tar.gz.part001?raw=true) — 29360128 bytes; SHA256 `d0729977f2d03e5641705c30fba440606f39781a6225ff87f9c217b8521b3baa`
- [nana-firstlife-0d842676.tar.gz.part002](nana-firstlife-0d842676.tar.gz.part002?raw=true) — 29360128 bytes; SHA256 `94aeea3bef2adb85cb2e6a0a2a05174c66513ec31c4f55d363ce7d97d2bab88d`
- [nana-firstlife-0d842676.tar.gz.part003](nana-firstlife-0d842676.tar.gz.part003?raw=true) — 29360128 bytes; SHA256 `8910c1689550e8dc61abc985a8f04320a772078ff52ae1d60025563b52eed5c1`
- [nana-firstlife-0d842676.tar.gz.part004](nana-firstlife-0d842676.tar.gz.part004?raw=true) — 29360128 bytes; SHA256 `c4245eea6a8f463702062a79b92f5e3b76bc5cf5f2d6d18cb9302822cf3c7291`
- [nana-firstlife-0d842676.tar.gz.part005](nana-firstlife-0d842676.tar.gz.part005?raw=true) — 29360128 bytes; SHA256 `e8d633695e9ff41893731c52275bdc66a776f1f1e01083c9286c6ed33d7b54f2`
- [nana-firstlife-0d842676.tar.gz.part006](nana-firstlife-0d842676.tar.gz.part006?raw=true) — 29360128 bytes; SHA256 `48a05e04a1bc4e99a486c1b080f488eaa4893abb8a2f01d298768efadf94b4b9`
- [nana-firstlife-0d842676.tar.gz.part007](nana-firstlife-0d842676.tar.gz.part007?raw=true) — 29360128 bytes; SHA256 `33c222a110b3a3994563875673d54cee987cc6697c3f3b1b700af0fe06fac9c6`
- [nana-firstlife-0d842676.tar.gz.part008](nana-firstlife-0d842676.tar.gz.part008?raw=true) — 29360128 bytes; SHA256 `165f3017e8446c5a7855bcede8fde005b927f9116dd6469a5ee2ec84d1b69ebb`
- [nana-firstlife-0d842676.tar.gz.part009](nana-firstlife-0d842676.tar.gz.part009?raw=true) — 20919635 bytes; SHA256 `6c4aea2bae0e23674062bcdc02166b4a95a508b3db108e6bac312efc6c2fa2c9`

用tools/nana_first_life_android_v2/receive_image.py重组；默认不load，显式--load才导入，绝不自动启动。详见docs/nana_first_life_android_v2/REV3_DEPLOYMENT_RUNBOOK.md。
私有GitHub需要用户登录；不把认证令牌写在下载URL。原SDK已在镜像中，勿因缺文件而重新build冒充此ID。
