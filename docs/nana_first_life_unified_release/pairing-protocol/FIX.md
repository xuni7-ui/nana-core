# 紧急配对协议核验与签发入口修正

[源码核验] 当前原 BFF AuthService.offer 使用 secrets.token_urlsafe(32)：32字节
CSPRNG随机量，256bit熵，43个ASCII URL-safe字符 [A-Za-z0-9_-]，不带padding。
服务端PairRequest、Android原生NanaHostPlugin、V3前端都要求24–128字符；
手机名称最多64字符且必须与签发时完全一致；默认120秒、单次使用。

19字符不可能是此官方生成器的完整输出；可能为另一生成入口或显示截断，具体
云端工具/版本仍未取得，不能伪称已定位其源码。不要把19字符码补长、拼接或降低
原生/服务端校验。仅在进程外随机生成43字符也不行：它必须由**当前运行的同一
BFF**登记在内存pending offers中，否则仍会拒绝。重启BFF会丢失旧pending码。

## 最短修正：使用当前BFF的官方签发入口，不换APK

在同一私有HTTPS地址打开现有Web，使用HOST_ADMIN会话，进入设备页，对手机名称
“这台安卓手机”生成最小权限一次性配对码。应取得完整43字符，然后在现有APK
输入。旧V3/3.0.2原生端都接受该长度，不需为本协议核验再次装APK。
必须是devices/offers的返回值，不是登录验证码、旧cmdserver口令、邀请码或外部
脚本自造字符串。不要把码发回聊天/日志；不要记录浏览器network response正文。

如果云端原操作器的19字符生成路径无法立即修复，使用本次交付的issue_pairing.py
替换它的**签发动作**。工具不生成本地码，而是认证原Web会话→CSRF→调用原
/api/nana-space/v2/devices/offers→校验43字符→在可信未录制终端显示→注销临时Web
会话。保留同Subject及默认READER/CONVERSATION角色，不读写Subject Store，不碰Genesis。
这不是第二认证服务、第二BFF或直接编辑auth.json；不放宽原服务器权限。

宿主操作者收取该脚本后，用匹配宿主的标准Python（不要在Ubuntu宿主裸用Debian
私有Python前缀）在可信交互终端执行：

```sh
python3 issue_pairing.py \
  --base https://nana-core-host.tail62e848.ts.net:8443 \
  --subject-id 8acff4fb-2532-4a97-a4b7-e59e2ae2f797 \
  --device-name '这台安卓手机'
```

Web管理口令仅通过隐藏终端输入；已有安全FD可用--password-fd <number>，不在argv/
env/文件传递口令。终端输出默认fd1，若不是TTY则在认证前拒绝，禁止tee/重定向到
日志/交接文件；使用现有Web是推荐路径。没有真实HOST_ADMIN凭据/私有网络通道
时停止，不搜索历史Key，不创建新密码或身份。服务器返回19字符时明确拒绝并报
BFF_GENERATOR_PROTOCOL_MISMATCH；这时需云端提供原生成工具名称/版本/脱敏命令，
或核对该URL是否确实路由到原BFF，不能通过调整客户端掩盖它。

连接异常后不重发原offer；若签发状态UNKNOWN，先核设备/等待旧offer自然过期，
不要把同一请求自动再发一次。HTTP重定向被拒绝，HTTPS证书校验保留。

## 本轮实际验证

原真实HTTP BFF+隔离DEV Subject：签发43字符→19字符输入400拒绝→完整码配对200→
重复消费403→native session→bootstrap200→原管理员撤销→bootstrap401。
另外验证签发timeout仅尝试一次，错误19字符返回不补长、不接受。相关原auth
边界合计8项通过。随机合成凭据只在进程内存中，不写入证据或测试常量。
正式host未访问、无真实配对码/模型调用/生产Subject写入；真实手机闭环未假称通过。

## 转发云端奈奈的只读核查命令

在Ubuntu宿主执行（不是AstrBot容器）；只选现有独立Core Compose服务，0或多容器
时命令失败，不自动选旧QQ容器。只读源码/公开release选择器，不读auth.json、
数据库、环境密钥或pending码，不调用签发接口，不停止/重启服务：

```sh
docker exec "$(docker ps -qf label=com.docker.compose.project=nana-core-independent -f label=com.docker.compose.service=core)" /usr/bin/python3 -IB -c 'import os,re,json;from pathlib import Path;r=Path(os.environ["NANA_CORE_RELEASE"]);n=int(re.search(r"code = secrets.token_urlsafe\((\d+)\)",(r/"src/nana_core/life/live_api/auth.py").read_text()).group(1));print(json.dumps({"release":r.name,"random_bytes":n,"expected_chars":(4*n+2)//3}))'
```

正常结果random_bytes=32、expected_chars=43。这只能证明所选镜像的源码规则，
不冒充已查到另一个19字符生成工具或BFF内存状态；云端奈奈应继续定位自己签发
19字符时实际调用的入口，并改为上述原BFF签发路径。若Compose项目名已变更，
先核对实际独立Core服务标签，不能去掉过滤器随便选一个容器。
