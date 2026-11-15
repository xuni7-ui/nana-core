# Android debug 构建证据

[本地实测 2026-11-15] 源码输入 `0554f4700a9181e08a6ce81ba94cb3e9849218a4`，在独立工作目录安装 Android SDK platform 35、build-tools 34.0.0/35.0.0，Temurin JDK 21.0.8+9（SHA256 `f2dc5418092c43003db8f9005c4a286e1c0104fea96ccdd49e8ebd037cac9219`）和仓库锁定 Gradle 8.11.1（SHA256 `f397b287023acdba1e9f6fc5ea72d22dd63669d59ed4a289a29b1a76eee151c6`）。现有 npm 锁与 `npm run android:sync` 后，`gradle assembleDebug --no-daemon --max-workers=2` 成功（13秒，24执行/61复用），构建后 Git 工作树干净。

APK：`/workspace/work/nanalink-delivery/0554f47/nana-space-debug.apk`，SHA256 `07315406357de665baff961b9c6c04677bb2f85f175df5637b1fed1a671793f4`，约4.7MiB；包名 `life.nana.space.dev`、versionCode 409、versionName `4.0.9-next-debug`、最低 SDK 23、目标 SDK 35。`apksigner verify --verbose` 验证 v1/v2 签名。使用本机 debug 签名，不是生产发布密钥；未证明独立重新构建字节一致。

初次尝试的系统 Java 是无编译器 JRE，Gradle 构建失败；安装独立 JDK 后重试成功。无 `/dev/kvm`，未连接或操作真实设备；APK 构建不证明实际 Android UI、平台登录或生产运行。此文件是本地开发产物，工作区清理后不保证持久存在。
