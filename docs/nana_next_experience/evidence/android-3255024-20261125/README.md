# 固定 3255024 匹配 Android 调试包

同源交付增量。以固定 `325502482afd18f1e3137ea183d3927c2c02bce4` 的原生输入及已校对 Web 输出编译。官方校验后的 Temurin 21.0.13.1+2、Android SDK 平台 35 r02、Build Tools 34.0.0 与 Gradle 8.11.1 隔离构建。首构建的系统 Java 只有运行时，且 Gradle 直连未解析仓库；改用校验过的 JDK 和原环境 HTTP 代理及 CA 之后成功。

Android 应用 ID `life.nana.space.dev`、版本码 409，min SDK 23 及 target SDK 35，v2 验签通过。APK SHA-256 `19f1a3cb383ec65351509bdc3bafa58df85cccf9761ce4061e4c8cc9412f5482`。从固定 GitHub 提交独立重取所有新变更，结合此前独立取回的文件校验整套 34 项，并重新验证 APK 签名和 42 个同源 Web 文件逐字节相等。 [Core、Web、Android 和 NanaLink 固定候选](https://github.com/xuni7-ui/nana-core/tree/dc3806ecfe581695f3d855ecc33f8364bce08448/deliveries/nana-space-next/server-3255024-candidate)

调试证书与上一固定候选的历史测试包不同，无法原地升级该包。正式选择仍为 Core 266272a 及 Android 409。实际安装、真机、真实账号、真实模型、实际跨日以及生产待验。
