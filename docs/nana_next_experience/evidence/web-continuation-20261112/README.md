# S7/S1/S2：生成期间真实接续，原C双源回复

基线0ee0d2b后继。Web收到认证进度后可发一个同scope未保留补充输入，父/子各自有回执，等待两者结束才排后续；移除旧草稿预览，原C决定是否重组，成功只显示实际联合措辞。逆序回执/UNKNOWN/首条断流不误作已发送，不抹去其他核验回复；保留/私人范围变化仍普通排队，原20分钟本地过期/取消保留。关闭逐字预览仍可接纳补充输入，但不显示草稿。只有明确reserve前的WINDOW_CLOSED/REVISION_CONFLICT可保原ID回普通队列，UNKNOWN不重发。

原Core在发送前有界读取已到socket的输入，复用既有urgent lane，不重入C，不创建Store/Loop或新模型计时器。真实TLS首轮4失败是DevTools在SDK终帧cancel后无响应正文；改为独立原receipt GET+UI必须已接受严格stream回执，保留所有原断言效果。继而4真实失败揭示模型最后tick与接续到达间的空隙：旧Root实际仍生成独立回复。确定性禁用额外model tick对照1fail/1pass；修复safe-point读取后53相关50.50s通过。没有放宽断言/加sleep掩盖。

真实HTTPS localhost→Web/V2 SDK→BFF→UDS/独占DEV原Core/C→合成stream provider，desktop/360/390/412四场景16.2s通过：旧草稿仅review未回复，child两原始source IDs/真实response ID，一次联合回复。停机实核1主体、8输入/16真实fixture请求、purpose counts[1,2]重复4次、0actions/grants、runtime inactive、0真实provider。此前失败DEV报告32fixture/16输入/purpose均1同样保留，不退款/不改账/不隐藏。

Web编译/Vite3.43s、93unit4.16s（含5SDK native-port合约，非Android运行）、既有及接续56browser1.2m、补充边界/关闭预览/先排队后进度12browser22s；41原Supervisor进程/HTTP/stream/授权45.98s通过。Native Java已有单stream专用worker+普通Bridge executor；修SDK将call.reject有限message归一V2Error，窗口关闭可识别，session撤销可清理，未打APK或动设备。正常原CLI已显式启用已有coalescing；直接ControlServer类默认仍False以保护旧调用/对照。managed实际start/pause/stop/restart/sigkill原测试核对capabilityTrue，无新正式genesis。新鲜隔离DEV初始化不冒充生产初始化。

0ee独立CI43020960495实读SUCCESS168Core141.28s/88unit/120browser1.7m/Vite2.67s，是基线，不是本批全仓。当前未做新最终匹配安装/真实模型/手机/真人自然度/跨日成长/生产切换，CURRENT266+409。原A–H继续；下一优先原C取舍/实际因果、完整Token/成本/超时与剩余产品闭包，不重建旧V4包或重复artifact403。2026-11-12环境重建丢失/tmp过程，源码/Git保留，旧临时安装/缓存路径不能再假定存在；旧浏览器夹具缺两字段8fail/8pass仅有tool观察，单列非重造rawlog。
