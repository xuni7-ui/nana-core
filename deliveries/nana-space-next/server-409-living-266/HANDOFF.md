# Nana Next Experience 后端开发交接

实际Core源码266272a，原有409客户端b873a4a的前端树完全一致。验证为隔离开发环境，不是云端生产部署或真人体验。请使用本目录的Core包；client-409中b873旧Core仅为兼容核对，不是新后端。

下载完整目录后先运行：

```sh
python3 verify-delivery.py --root .. --current CURRENT-DELIVERY.json
python3 nana-unpack.py nana-core-266272a-portable.tar.gz --destination /path/to/new-dev-slot --sha256 94684d933480e195a93493863ac8b73abd3b75b548e53543c3db3997c55a6963
/opt/nana-core/runtime/bin/python3 -I /path/to/new-dev-slot/bootstrap.py install
```

以上Python路径是既有独立Core容器内路径；目标新槽必须由宿主操作者依已授权的持久卷实际布局选择，且不得覆盖现役槽。安装需Python 3.12及实际sqlite3绑定至少3.51.3，离线wheel在包内。以上不触碰现役主体或执行Genesis。正式接入须由既有运行负责人依照原授权、身份绑定和回滚步骤进行。

当前包内新能力包括软48h来源选择、原C记忆巩固及可暂停周回看、受管冷备份回读、磁盘余量规划和不含正文的用量记录。冷副本未删主库，无法声称节省总存储；usage来自上游报告，缺失为未知，模拟调用不代表真实模型。未重编APK。

266补充冷备份多态来源完整性检查；b25全仓2043通过12跳过，266补丁16项定向通过。旧6a DEV主体实际在266包内保持身份/谱系并完成回读与撤回；266 BFF另在隔离DEV主体验证，不将其称为云端验收。
