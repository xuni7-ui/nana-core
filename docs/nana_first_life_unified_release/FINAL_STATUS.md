# Unified First-Life V3 · 实际交付状态

本轮延续唯一 `dev/nana-core-first-life-unified-release-v1-codex`，不是新开的Release。
Core运行源码固定3665d39fe0aeff9831721d4bfd1bfba0b8386a2b；完整继承9217e3f /
7a1bce9 / a07e906，并真实merge完整ea1e225。其后仅增加交接工具/测试/证据/账本。
状态：`UNIFIED_DEPLOYABLE_DELIVERY_EXTERNAL_HOST_GATES_PENDING`。

| 交付 | SHA256 / 实际内容 |
|---|---|
| 镜像ID | 6581d9e0cb7e686511aa704f77546cae508fc2911792753ed3a9bd3bf3cdb18b |
| 镜像gzip | 6974cec541039290d6ddf100be1834b6a51d3dec5299adc52331a33a1de80923；307509301bytes /11片 |
| Core | f87c461f84804272f670bd8a675e8f93c9dde85af73e39f9118fc33a2f706b58；249files /双构建一致 |
| V3 Web | 7b2d9cc713928edcff8e20486c3c951124dc698c2c7e057788c5a3c360e4f008 |
| Android3.0.1 Debug | e1c250b9ebb4e84092b56641c6ab71dbd248697b1e52ebd7a16c94a1831b90b4；4709981bytes；life.nana.space.dev /301 |
| 完整交接清单锚点 | 46d009c14f82f23b9448c9d26bc48f71dfd90363007e8c9a469f1c38e6b6b41b |

所有最终文件位于仓库根CLOUD_DEPLOY_HANDOFF，自含脚本、镜像分片、Core/Web/APK/
新完整封条8149项/原plan引用，不依赖本Codex工作区或宿主已有新分支。README为真实
路径命令。APK保持原签名指纹b2fec5a0…，原Keystore/配对/权限/CSRF/UNKNOWN不替换。

## 已实际执行

- 最终镜像：Debian13/linux-amd64，Python3.12.14、SQLite3.51.3、OpenSSL3.5.7、
  pydantic2.13.4、UID999；ssl/loader/RUNPATH/venv/动态库实际核验。相同镜像的独立
  runtime提取、规范化树校验/原子安装/所有权/0555及只读原前缀挂载后再次通过ABI。
- Host stdlib adapter→同容器私有Python；不升级Ubuntu全局OpenSSL，不改旧SDK，
  不LD_PRELOAD。合成原互斥parser只收到dry-run、只读写入被拒绝，未造13项门。
- 该最终镜像的DEV同Subject：原十页API、V3Web、原C离线chat；杀BFF后自动重启，
  容器重建身份不变epoch2→3→4；safe-point备份、B8恢复、旧源fence、旧Grant撤销。
  源与所有服务在限定DEV目录，不是正式Genesis/真实云host。
- 新V3配置：真实Core HTTP注册Provider/Model/Route/禁用、角色/配置revision冲突、
  实际回执；原typed contract和有限native映射；配置network_calls0/livepermissionfalse。
  backup/status仅原回执投影，PC/恢复未观察时NOT_OBSERVED。
- Python相关62PASS/14.73s；部署复核21PASS/1.52s（与前者重叠，不合计81个不同测试）。
  前端44PASS、TS构建；实际Core浏览器4PASS/11.9s（desktop/360/390/412），原V2边界
  浏览器3PASS/10.2s。APK真实构建、原生1test通过、签名校验通过。工具Ruff通过。
- 最终11分片/gzip/tar校验与重新docker load同ID；标准/优化模式核验通过。Core源码
  独立再次构建一致。没有声称Docker镜像bit-for-bit重建相同或手机已安装。

## 仍未执行与真实宿主下一步

1. 真实宿主安装及Docker29运行：目标Ubuntu24.04/Docker29来自用户报告；实际本机
   Docker28.4.0/vfs。按README载入、stage新slot、只读部署verify/ABI即可继续核验，
   不覆盖/srv原runtime或canonical home；旧镜像/6565项封条保留。
2. 原Host Operator checker/13项具体定义和真实命令尚未提供。原12/13属于用户报告。
   已交付匹配环境调用和字面argv最小评审补丁，但**原13/13仍NOT_RUN**，不能把上述
   ABI/合成parser或自行列13项改称原checker通过。按README显式绑定其原脚本SHA/
   原批准输入，在真实host继续；适配器无create/activate模式。
3. 实体Android、tailnet HTTPS8443证书/ACL/配对需真实host与手机；开发自签浏览器
   测试不能证明该点。原6199/AstrBot不动，不开Funnel。
4. 正式Genesis/生产激活/B1首份真实加密异机备份及恢复、私人历史/旧writer切换/
   真实Provider与真人评审均未执行，保留原权限和C-only摘要。bwrap保持BLOCKED；
   不因此收回其他合法能力。First-Life NOT_READY、Beta NO。

首次失败均保留：磁盘不足/归档前缀拒绝/离线Gradle缓存URL/严格DTO JSON模式/
合成夹具0700，修正后重验；未删测试或弱化门槛。未重复无关千项完整回归，旧完整
回归只按其源码保留。无新付费、社交、生产或私人数据；Master/Matrix字节不变，
S1–S10/63criteria、schema13/43表、One Subject/Store/Loop、Manager/Grant不变。
