# 原生模型目录：有界翻页与部分结果提示

基线53f0db9。原Anthropic仅一页返回has_more→truncated，客户端却忽略该标记；实际下一页模型不能被列出。冻结5个定向场景3fail/2pass。现在跟随经过模型ID格式/原凭据排除/末行一致性校验的last_id，以urlencode(after_id)只在已配置原HTTPS地址继续GET；原native x-api-key/anthropic-version与OpenAI Bearer分开，保留TLS验证/no redirect。无推理/模型调用/自动配置或付费测试。

同一次明确读取最多8页、累计256KiB、显示256个去重模型；后续open只使用十秒机会窗口的剩余时间，不重复已有cursor/不重试HTTP失败。窗口只限制发起后续页及socket timeout，不冒称DNS/网络滴流的严格端到端十秒截止已资格。缺/非法/含凭据/重复cursor、页数/时间/显示范围耗尽诚实truncated；总字节超限或后续401/403仍明确原错误，不把部分数据伪装完整成功。OpenAI-compatible仍按其原单页列表语义。未声称任意体量全目录一次读完。

客户端显示部分结果提示，保留未列出模型的手动名称草稿；没有增加原生操作/API DTO/路由/Store/依赖。目录中的模型不等于已资格能力。原BFF HostAdmin/主机白名单/secret_ref/配置revision/节流/最后密钥clear与原配置不变断言保留。

14目录相关中含新增2页/分页界限/错误；加原runtime设置/native Anthropic合计32通过17.53s。TS通过、live Vite2.55s；既有完整列表选择注册+新增部分结果手动填写两个合成HTTP场景×四视口8通过12.7s（0skip/flaky），真实API/模型/手机0。没有重复93前端单测/完整发行，前批93保留原scope。

首次浏览器新场景在编辑器关闭时fill超时，1fail/2pass/1interrupted/4未跑，原日志保留；中止余下重复错误。修夹具时相对路径误用导致FileNotFoundError，未改到源码，却误启动一次同错误测试，已中断（1pass/1interrupted/6未跑），browser-final.txt不是通过。随后按正确绝对路径明确点击原“添加供应商草稿”入口，保留原部分提示/无非GET/无自动测试/未列出名字断言，使用新输出目录完成8通过，不删改首错。旧失败截图上下文被该无效重跑复用的输出目录覆盖，原始首错文本仍在browser.txt；不声称旧失败截图完整保留。

独立前批资格实读：55805d5 run43201141379 Core114pass32.64s/clientSKIP；53f0db9 run43202095801 client93unit/148browser通过、CoreSKIP。摘录独立保存，不当本源码CI/全仓。无新安装/APK/生产/真实模型/手机/自然度或长期资格，CURRENT266+409不变。

下一：返回原C关联独立清除/后续策略，继续商业INTERPRET/C/RENDER私人状态与保留/真实反馈融合、自主机会、S8广迁移及原A–H。目录按页显式继续读取及更多原生协议等仍有产品开发差额；不将此次有界翻页当全部供应商适配完成。
