# License review — 本轮 BORROW_CODE = NONE

所有业务实现建议均为独立重写的模式；没有vendoring、装依赖、copy上游模块。许可证允许不等于适合纳入Core。此表是源码级初审，不是法律意见或transitive依赖合规认证。

| Snapshot | LICENSE/header | 代码借用义务/本轮决定 |
|---|---|---|
| yuri-os/YuriOS `cd4d1f16ae09` | [LICENSE](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/LICENSE#L1) · Apache-2.0 | 保留copyright/license；实质改动需说明，NOTICE如适用保留；依赖/模型资产另审；本轮不copy。 |
| getzep/graphiti `d50741d1bf46` | [LICENSE](https://github.com/getzep/graphiti/blob/d50741d1bf463cbe3859eb73914cbff1b66839e6/LICENSE#L1) · Apache-2.0 | 保留copyright/license；实质改动需说明，NOTICE如适用保留；依赖/模型资产另审；本轮不copy。 |
| letta-ai/letta `5bcdd177d70f` | [LICENSE](https://github.com/letta-ai/letta/blob/5bcdd177d70fa2b31a754cfcd801e77b2e1ab16a/LICENSE#L1) · Apache-2.0 | 保留copyright/license；实质改动需说明，NOTICE如适用保留；依赖/模型资产另审；本轮不copy。 |
| letta-ai/letta-code `1297870b0aa6` | [LICENSE](https://github.com/letta-ai/letta-code/blob/1297870b0aa6662d6c70729d273f5073c1bcbdea/LICENSE#L1) · Apache-2.0 | 保留copyright/license；实质改动需说明，NOTICE如适用保留；依赖/模型资产另审；本轮不copy。 |
| mem0ai/mem0 `0724291bd864` | [LICENSE](https://github.com/mem0ai/mem0/blob/0724291bd864cf807e88ee8981c8226644e8fb42/LICENSE#L1) · Apache-2.0 | 保留copyright/license；实质改动需说明，NOTICE如适用保留；依赖/模型资产另审；本轮不copy。 |
| langchain-ai/langgraph `4e2dfe4a247a` | [LICENSE](https://github.com/langchain-ai/langgraph/blob/4e2dfe4a247abfc0d001f3ef8242cbbbba400d2c/LICENSE#L1) · MIT | 复制实质部分需保留copyright/permission；子目录/资产条款另审；本轮不copy。 |
| temporalio/sdk-python `346d4dcd0863` | [LICENSE](https://github.com/temporalio/sdk-python/blob/346d4dcd0863657c3a33283c952a296762059339/LICENSE#L1) · MIT | 复制实质部分需保留copyright/permission；子目录/资产条款另审；本轮不copy。 |
| mindverse/Second-Me `d0e40251d9de` | [LICENSE](https://github.com/mindverse/Second-Me/blob/d0e40251d9de61b3340b8d0d7d83150669f1885a/LICENSE#L1) · Apache-2.0 | 保留copyright/license；实质改动需说明，NOTICE如适用保留；依赖/模型资产另审；本轮不copy。 |
| AFK-surf/Comma `ba4f55db1bf0` | [LICENSE](https://github.com/AFK-surf/Comma/blob/ba4f55db1bf038a9246a9f71a7b5059cd91853f1/LICENSE#L1) · AGPL-3.0-only | 强copyleft；修改并网络提供服务可能触发对应源码义务，必须单独法律/分发审查；只BORROW_PATTERN，不copy。 |
| OpenHands/OpenHands `9d02893bc96a` | [LICENSE](https://github.com/OpenHands/OpenHands/blob/9d02893bc96aa256a4c0ece316bdb992247bc918/LICENSE#L1) · MIT | 复制实质部分需保留copyright/permission；子目录/资产条款另审；本轮不copy。 |
| max286674-cpu/OpenWatari-Jarvis `b6a1924bc35d` | [LICENSE](https://github.com/max286674-cpu/OpenWatari-Jarvis/blob/b6a1924bc35daaf9520ac6e9fc8ee8c7ef7b4c10/LICENSE#L1) · MIT | 复制实质部分需保留copyright/permission；子目录/资产条款另审；本轮不copy。 |
| shuaiyuan17/tomo `a6ee1bec12be` | [LICENSE](https://github.com/shuaiyuan17/tomo/blob/a6ee1bec12bee2d59cd5015bf86208710aaf6915/LICENSE#L1) · MIT | 复制实质部分需保留copyright/permission；子目录/资产条款另审；本轮不copy。 |
| huodebing-alt/anima `ba215ce72bca` | [LICENSE](https://github.com/huodebing-alt/anima/blob/ba215ce72bcaedd147d5d08de6e54555a62952c1/LICENSE#L1) · MIT | 复制实质部分需保留copyright/permission；子目录/资产条款另审；本轮不copy。 |
| letta-ai/letta-archive `56ba9c255526` | [LICENSE](https://github.com/letta-ai/letta/blob/56ba9c25552605eec89de8ed3dc6394b625c1993/LICENSE#L1) · Apache-2.0 | 保留copyright/license；实质改动需说明，NOTICE如适用保留；依赖/模型资产另审；本轮不copy。 |
| OpenHands/software-agent-sdk `12e967664c23` | [LICENSE](https://github.com/OpenHands/software-agent-sdk/blob/12e967664c2353f4cb85dd27da04ade035ff078c/LICENSE#L1) · MIT | 复制实质部分需保留copyright/permission；子目录/资产条款另审；本轮不copy。 |

## File/header/NOTICE审查范围

Graphiti datetime_utils/edges 等保留Apache file notice；YuriOS、Letta、Mem0所读文件没有发现替换root license的声明，不代表整个依赖树已审完。LangGraph子包各有LICENSE，不能只凭root判断未来单独copy。OpenHands SDK与Canvas是两个repo，分别登记。

OpenWatari同时有NOTICE、THIRD_PARTY_NOTICES.md、ACCEPTABLE_USE.md；读到optional LGPL音频依赖及CC BY-NC-SA声音素材提示。root MIT不覆盖模型、voice packs、商标或云服务条款。Second-Me vendored gguf-py另LICENSE；本轮不借训练/模型资产。Letta部分builtin技能另附LICENSE，未借其代码。

如果未来改为BORROW_CODE，必须新增source file+exact SHA/header hash+LICENSE/NOTICE+依赖锁+改动面+归属说明，再审核。当前没有用“无LICENSE”项目源码，也没有用模式名规避复制义务。研究文档只包含机制描述、标识符和短语义引用；不是上游实现复制。
