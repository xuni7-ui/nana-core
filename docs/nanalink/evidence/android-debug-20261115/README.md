# Android debug 构建证据

[本地实测 2026-11-15] 源码输入 `0554f4700a9181e08a6ce81ba94cb3e9849218a4`，在独立工作目录安装 Android SDK platform 35、build-tools 34.0.0/35.0.0，Temurin JDK 21.0.8+9（SHA256 `f2dc5418092c43003db8f9005c4a286e1c0104fea96ccdd49e8ebd037cac9219`）和仓库锁定 Gradle 8.11.1（SHA256 `f397b287023acdba1e9f6fc5ea72d22dd63669d59ed4a289a29b1a76eee151c6`）。现有 npm 锁与 `npm run android:sync` 后，`gradle assembleDebug --no-daemon --max-workers=2` 成功（13秒，24执行/61复用），构建后 Git 工作树干净。

APK：`/workspace/work/nanalink-delivery/0554f47/nana-space-debug.apk`，SHA256 `07315406357de665baff961b9c6c04677bb2f85f175df5637b1fed1a671793f4`，约4.7MiB；包名 `life.nana.space.dev`、versionCode 409、versionName `4.0.9-next-debug`、最低 SDK 23、目标 SDK 35。`apksigner verify --verbose` 验证 v1/v2 签名。使用本机 debug 签名，不是生产发布密钥；未证明独立重新构建字节一致。

初次尝试的系统 Java 是无编译器 JRE，Gradle 构建失败；安装独立 JDK 后重试成功。无 `/dev/kvm`，未连接或操作真实设备；APK 构建不证明实际 Android UI、平台登录或生产运行。此文件是本地开发产物，工作区清理后不保证持久存在。

后继重建 [源码 `80e11452e0a3c08e9ee70301bdd0fc2b68d4d8b6`]：同步新增平台能力说明后重建，12秒、24任务执行/61复用；本地文件 `/workspace/work/nanalink-delivery/80e1145/nana-space-debug.apk`，SHA256 `062b4c8f2a3c27fd123555e97fa95d325cdcb212810a4c2f5897530f1a4fa15c`。包名及 SDK 同上，v1/v2签名验证通过；未进行独立双构建、实机或发布签名验收。

同一 `80e1145` 的 Git 归档在独立目录完整重建：第二 APK SHA256 `a07c1f62bb333558b9558dda675bacd11ea8df4bbcb98564dcf22d7de5a34d6d`，与首包不同；两个 APK 的所有 ZIP 条目名称和解压内容哈希逐一相同，条目顺序/偏移不同。两次共享已安装依赖、Gradle 缓存和本机 debug 签名，故这不是独立供应链重建，也不宣称最终字节可复现。保留两份差异，后续应消除打包顺序差异。

同一归档 wheel 固定 SOURCE_DATE_EPOCH 双构建 SHA256 均为 `4a1e30f86f88205d788c24215ea6397a693a8ccc942af62d215631348e8f2238`；离线 `--no-index --no-deps` 安装后 308 个 Core Python 文件与源码输入逐一一致，侧车 `--check` 成功且未解析凭据、联网或登录。依赖来自已准备的独立环境；该检查不代表真实平台或生产运行。
