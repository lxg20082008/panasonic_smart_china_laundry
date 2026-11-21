# Panasonic Smart China Laundry

将「松下智能家电」App（中国区）中的**洗衣机**和**烘护机**接入 Home Assistant，支持**状态监控 + 云端控制**（v0.2.0）。

- 实测机型：洗衣机 XQG100-L188（0600）、烘护机 FDC-L1026D（0610）
- 协议：松下智能家电云接口（app.psmartcloud.com），状态接口 `WDevGetStatusInfoBD158`，控制接口 `WDevSetStatusInfoCommon`
- 监控实体：运行阶段 / 剩余时间 / 程序名 / 参数设置 / 智能投放余量 / 各类提醒传感器，以及运转终了 / 机门 / 童锁等二进制传感器
- 控制实体：电源、童锁开关；启动、暂停按钮；程序 / 水温 / 转速 / 水位 / 烘干类型选择；洗涤、漂洗、脱水、烘干时间数值
- 控制依赖设备机身「远程控制」键开启（`remoteStatus`），否则云端拒绝指令
- 注意：云平台为**单点登录**，HA 登录后手机 App 会被挤下线

## 链接

- [README（完整文档）](https://github.com/lxg20082008/panasonic_smart_china_laundry)
- [问题反馈](https://github.com/lxg20082008/panasonic_smart_china_laundry/issues)
