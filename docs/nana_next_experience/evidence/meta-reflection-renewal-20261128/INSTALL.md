# S10 反思重新评审的独立 Core 安装

固定源码 `ccfb6d180001cd3420ad7d12d2e65ae90a9f2cdf`，313 文件，SHA256 `fdbbc7eb491df0c5f9cefd4cb2b2923ab6782703792e9aa6a7b407c376ad49d1`。复用缓存中已校验的离线 wheelhouse，完成摘要核对、单独安装槽和预检。 [构建](installed-build.json) · [安装](installed-offline.json) · [预检](installed-preflight.json)

实际从安装目录加载原 Runtime、C 反思与 S10 模块。CPython 3.12.14，SQLite 3.53.1。六个场景全部通过，含重启、候选记录提交后模拟中断、旧独立实验证据撤回、显式暂停或退役。真实模型调用为零。App、NanaLink 侧车及其依赖锁文件沿用既有候选，正式交付仍为 Core 266272a / Android 409。 [安装回归](installed-current.txt) · [源代码与对照](README.md)
