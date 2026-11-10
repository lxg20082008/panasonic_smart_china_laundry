# Panasonic Smart China Laundry

将「松下智能家电」App（中国区）中的**洗衣机**和**烘护机**接入 Home Assistant（只读监控版）。

- 实测机型：洗衣机 XQG100-L188（0600）、烘护机 FDC-L1026D（0610）
- 协议：松下智能家电云接口（app.psmartcloud.com），状态接口 `WDevGetStatusInfoBD158`
- 实体：运行阶段 / 剩余时间 / 程序名 / 参数设置 / 智能投放余量 / 各类提醒传感器，以及运转终了 / 机门 / 童锁等二进制传感器

控制版（程序选择、启动暂停、参数下发）规划中。
