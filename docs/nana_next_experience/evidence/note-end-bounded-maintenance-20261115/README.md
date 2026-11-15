# 原维护分片补旧笔记End键

S2/S4/S8受控增量，基线fee8业务源码（dev接续3eeb9ea/Brain238）。原MaintenanceService已对当前允许、经过Source/Owner/Scope/Privacy检查的原slice修旧gram索引；但只检查NOTE_GRAM_COMPLETE，故旧gram完整、仅缺新End键的笔记永远跳过。复用同一个服务/SCAN job/原游标及周回看，不新增scanner、启动重建、模型阶段或事实写入。

同一来源分片内检查既有Gram完成标记和由当前只读原文计算的尾键：缺Gram仍调用原完整_index；Gram已完整只INSERT OR IGNORE一个End键，避免重放大量已有gram插入。原始笔记/来源/时间/信任不改，错私域/实体/范围不补。已经位于增量游标之前的旧笔记，等待原bounded weekly review逐批补，不承诺升级瞬间补完整库。查找仍只读、保留安全回退；没重新跑大规模Native检索基准或改原20万库。

`old-final.txt`：同一最终输入/断言，使用/tmp/nfee8/src精确已安装fee8旧模块，2fail2pass0.51s：仅End缺失的增量和周回看失败；原Gram也缺失的两种情形仍通过，独立正对照。`new-final.txt`：4pass0.41s，每片最多2原始来源、6笔记各只补一次、同身份/游标重启恢复/私域等3条不改/无模型动作。仅End缺失共6条索引写语句；真正缺Gram时原完整恢复132条，不能把这两个不同缺损群称同预算旧新性能对照。最终单例行数/写量是实际测量，不是Token或物理回收。

`related-final.txt`：64passed27.24s，原维护前台优先/梦境、note recall/correction/withdrawal、privacy/registered-copy增量、G16/32及TEXT独立迁移。新增`runtime.txt`：正常Runtime.step1pass0.12s，原用户队列先处理且SCAN游标/缺键不动，之后原后台路径自动补键，Provider/fixture认知账项/动作都0。不是仅靠直接调用函数宣称主链已接。

首次旧2fail保留；第一个新夹具误假设“两条扫描来源必然都是笔记”，实际源元数据占一位，跨两片累计3笔记触发严格==2失败，`fixture-first.txt`/`related.txt`（61pass1该夹具失败）完整保留。未放宽任何分片/次数断言、未改cursor；在公开夹具前缀补普通来源使两行对齐，再用精确旧模块重跑同输入（old-aligned/old-final）并最终通过。最早reindex-prototype.py重放全部已有gram的实现未采用；最终只补必要一键。没有删/跳断言。

Fee8候选(交付4cb88e1/Core3b7e2d9e…/Web251bb84b…)的实际下载/两槽安装/291CI资格保持原范围，**不包含本后继维护补丁**，本批不再重打包/APK/CURRENT。真实模型/手机/生产/真人自然度/实际跨日0或NOT_RUN；原A–H全部继承。

下一已实际读取GitHub比较：B的dev/nana-core-universal-model-setup-b=d409a55f27f0d0b388d2ea01bde041d31a48038a，相对本批前3eeb为ahead13/behind59、merge-base45e7432。增量在通用提供商预设/目录分页/读取冷却、Web/Java有限映射与两个catalog后端消费者，没有B独立改写C/D/G的文件。应先读其CODEX_B_QUEUE和两份integration证据，逐块接入真正缺少的产品成果；保留本A当前09与C/D/G/原API新增cursor/CSRF/隐私/预算，合并前记录影响/回退，不直接覆盖文件或盲目接受旧Brain。旧B分支不是当前正式资格，Core/产品/完整原A–H继续。
