# 固定源码Web构建的公共输入与依赖元数据

基线8bec062a7d57e1b3a84d73a060a321ed9f4b98c1/Brain253已推干净。该Core草稿两次构建SHA相同d1d1de6…、首槽n8b离线BFF/49安装测试157模块通过；Web草稿未发布，生产/CURRENT未动。

新草稿重建从旧70输入白名单复制，遗漏已提交的.env.live（实际仅VITE_NANA_DELIVERY=live），虽然TS/Vite编译成功，模式配置不完整，因此不归档/交付此草稿。旧9a Web与原B合并构建目录42文件全SHA一致，旧目录的公共live配置与固定Git源码一致；不把新复制错误误称旧9a源不匹配。后续输入清单显式加入这一个已核验非密钥配置，保留失败草稿日志，不读取其他本地.env/凭据。

锁文件@types/deep-eql/parse-entities/through2的version标4.0.3，而原resolved地址、原integrity及现有真实包都是4.0.2。拟只纠正三条version元数据，不更改resolved/integrity/依赖选择/应用版本，不升级包；普通A集成兼容修复，不重复B产品开发。回退package-lock.json本锚即可。Core源码263模块与上一冻结源不变，后继统一重新封签，不冒称已发布8bec草稿或重打APK。
