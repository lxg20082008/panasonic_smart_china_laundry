# 松下智能家电 洗衣/烘护 接入（Panasonic Smart China Laundry）

将「松下智能家电」App（中国区）中的**洗衣机**和**烘护机**接入 Home Assistant。

- **集成域名**：`panasonic_smart_china_laundry`
- **协议**：松下智能家电云接口（app.psmartcloud.com），状态接口 `WDevGetStatusInfoBD158`
- **定位**：**只读监控版**——传感器 + 二进制传感器，不做控制（控制版本后续扩展）
- **实机验证**：洗衣机 XQG100-L188（品类 0600 / subType 32）、烘护机 FDC-L1026D（品类 0610 / subType 29），2026-11-09 实测通过

## 安装

### 方式一：HACS 自定义仓库（推荐，当前即可用）

1. HACS → 集成 → 右上角「⋮」→ **自定义存储库**
2. 粘贴本仓库地址 `https://github.com/lxg20082008/panasonic_smart_china_laundry`，类别选「集成」
3. 在列表中找到 **Panasonic Smart China Laundry** → 下载
4. 重启 Home Assistant，然后按下方「配置」步骤添加

### 方式二：手动复制

1. 将 `custom_components/panasonic_smart_china_laundry` 目录复制到 HA 的 `custom_components/` 下
2. 重启 Home Assistant，然后按下方「配置」步骤添加

### 配置

1. 「设置 → 设备与服务 → 添加集成 → 搜索 Panasonic Smart China Laundry」
2. 输入 App 手机号 → 密码 → 勾选设备

> ⚠️ 云平台为**单点登录**：HA 登录后，手机 App 的会话会被挤下线，需要重新登录 App；反之亦然。

## HACS 商店收录状态

标准 HACS 集成所需的 `hacs.json`、`info.md`、`brand/` 品牌图标均已就绪，Release `v0.1.0` 已发布。官方商店收录申请中：

- [hacs/default#13815](https://github.com/hacs/default/pull/13815) — 集成列表
- [home-assistant/brands#11425](https://github.com/home-assistant/brands/pull/11425) — 品牌图标

两处 PR 合并前，请用上方「自定义仓库」方式安装；合并后即可在 HACS 商店直接搜索下载。

## 支持的设备

| 品类号 | 类型 | 已实测型号 |
|---|---|---|
| 0600 | 洗衣机 | XQG100-L188 |
| 0610 | 烘护机 | FDC-L1026D |

同品类的其他型号大概率可用（协议同源），未实测型号请自行验证。

## 实体清单

### 传感器（两机共用）

| 实体 | 说明 |
| --- | --- |
| 运行阶段 | 待机 / 设定中 / 运转中 / 预约中 / 运转终了 / 异常 / 中途关机 |
| 运行状态 | 暂停 / 运行 |
| 当前程序 | 程序名（如「棉织物」「快烘」） |
| 剩余时间 | 本程序剩余分钟数 |
| 总运行时间 / 预约剩余 | 分钟数 |
| 童锁 / 机门 / 远程控制 | 状态 |
| 滤网清洁提醒 | 无需 / 需清洁 |
| 水温 | ℃ |

### 传感器（洗衣机独有）

温度设置、脱水转速、水位、烘干类型、洗涤/漂洗/脱水/烘干时间、智能投放（洗衣液/柔软剂开关、余量、不足提醒）、静音/光动银/水氧泡沫净/离心净水洗/免熨烫/加漂洗/预洗/nanoeX。

### 传感器（烘护机独有）

烘干风格、烘干进度、烘干模式、风量、水箱满提醒、护理剂购买/不足提醒、防皱保持、洗烘联动、清新保持。

### 二进制传感器

运转中、运转终了、异常、预约中、机门开、童锁、远程控制、滤网需清洁；洗衣机：洗衣液/柔软剂不足；烘护机：水箱已满、护理剂不足。

## 自动化示例

```yaml
# 洗衣机完成通知（企业微信）
alias: 洗衣机完成通知
trigger:
  - platform: state
    entity_id: binary_sensor.xi_yi_ji_yun_zhuan_zhong_liao
    to: "on"
action:
  - service: notify.wechat
    data:
      message: "洗衣机洗好了，记得晾晒～"
```

## 项目目录

```
Panasonic Smart China/
├── custom_components/panasonic_smart_china_laundry/   # 集成代码
│   ├── manifest.json
│   ├── const.py          # 常量：程序名映射、状态枚举
│   ├── token.py          # 设备 token 计算（sha512）
│   ├── api.py            # 登录 / 设备列表 / 状态查询
│   ├── config_flow.py    # 配置流（手机号→密码→勾选设备）
│   ├── __init__.py       # 轮询协调器（30 秒）
│   ├── sensor.py         # 传感器实体
│   ├── binary_sensor.py  # 二进制传感器
│   └── translations/zh-Hans.json
└── 探测资料/              # 协议逆向原始资料
    ├── device_scan_result.json   # 账号设备扫描结果
    ├── washer_status.json        # 洗衣机 135 字段实机状态
    └── dryer_status.json         # 烘护机 131 字段实机状态
```

## 协议要点（后续开发控制版参考）

- 登录：`UsrGetToken` → 密码 MD5 链 → `UsrLogin` → `ssId`
- 设备 token：`sha512(sha512(MAC后6位_品类_MAC前6位) + '_' + 后缀)`；**后缀必须保持原始大小写**（只大写 MAC 与品类），否则含字母后缀的设备会鉴权失败
- 状态：`POST WDevGetStatusInfoBD158`，header `xtoken: SSID=<ssId>`
- 控制：`POST WDevSetStatusInfoCommon`（body 为参数字段，如 program/temperature/spinSpeed/waterLevel/runingStatus 等）
- 程序枚举：官方 web 控制台 js（collocation.js），已提取到 `const.py`
- 上游参考：[mcdona1d/panasonic_smart_china](https://github.com/mcdona1d/panasonic_smart_china)；其 [PR #12](https://github.com/mcdona1d/panasonic_smart_china/pull/12) 已实现洗衣/烘护/冰箱/旋钮的控制与新增品类，控制版可借鉴其 `WDevSetStatusInfoCommon` 控制 payload 构造
