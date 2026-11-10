# Portable inputs trigger the existing source qualification

[源码与静态验证，2026-11-11 Asia/Shanghai] Codex B在独立治理分支继承`718df771cd4ace5e993ac9932f456ca98676d511`。DOMAIN S7 / Governance axis，工程交付验证范围；不修改Foundation标准或主体行为。

现有构建器从指定Git提交复制`packaging/portable/`全部文件，并另取`tools/nana_portable_cloud/unpack.py`；既有source qualification使用`requirements-core-dev.lock`安装资格环境。但push路径原先只覆盖`packaging/portable/runtime-files.txt`。对本次有界核对的26份打包文件、解包器和开发锁共28个真实路径，原过滤器仅命中1个；例如单改bootstrap、host_gateway或unpack不会触发此工作流。未把这项静态观察说成曾有错误发行、未测试部署或GitHub运行失败。

最小修复将单一runtime清单路径扩成`packaging/portable/**`，补上原解包器及开发锁；保留原分支、workflow_dispatch和全部旧触发。原permissions及所有测试/双构建/离线安装jobs的字节完全不变。治理PR路径同时纳入该工作流，复用现有治理检查，没有新增工作流、业务测试框架、依赖或部署。

验证记录见`path-coverage.json`：28/28命中、当前Git树旧命中无丢失、分支/手动入口保留、permissions/jobs字节相同、YAML及原shell语法通过。这里的静态匹配只使用本次相关简单正向路径模式，不宣称实现了完整GitHub glob引擎或全仓触发审计。GitHub真实治理CI及合并后的source qualification各以其回执为准；静态命中不是CI通过，也不是构建/安装通过。

新增触发仍会执行原有Core/client整套资格，因此单独修改被打包的文档也可能产生同一资格运行；没有取消或抢占A的现有CI。Core业务、客户端、生产、selector与所有私人数据不动。集成时保留最新A两份账本全文，仅追加治理事实。

回退：仅撤销两个既有workflow的本批路径变更；无产物、数据或运行态迁移。该修复不解决artifact传输域的代理403，也不替代A现有Core/UNKNOWN与真实体验资格。

集成复核：正常合入A最新`63e4e323abb00f467484ee35d096f814f5585ffe`，保留其新增context_fit源码/测试触发路径及全部jobs；现役两份账本全文保留后追加，不覆盖其FOCUS主体验证。
