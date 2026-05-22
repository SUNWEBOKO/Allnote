---
title: OLED 显示与 I2C 通信
tags:
  - TI
  - MSPM0
  - OLED
  - I2C
  - 显示
  - 电赛
created: 2026-05-04
---

## 本节主线

上一阶段用 GPIO 点灯是最基础的输出，本节更进一步——使用 OLED 屏幕显示字符串和变量。OLED 不仅能表示"亮或灭"，还能显示调试信息、传感器读数、状态变量。

使用的是四针 I2C OLED 模块（$128\times64$ 分辨率，$GND$、$VCC$、$SCL$、$SDA$）。重点不是从零写驱动，而是移植已有驱动代码，配置 I2C 外设，连接硬件，调用显示函数。

## 1\. I2C 通信基础

I2C 只需两根线：
- **SCL（时钟线）**：通信节拍，告诉双方"现在该读/写一位数据"
- **SDA（数据线）**：传输具体数据（高低电平表示 1 和 0）

本节使用开发板上的 `I2C1`，`SCL` 对应 `PB2`，`SDA` 对应 `PB3`。

接线：

```
OLED GND → 开发板 GND
OLED VCC → 开发板 3.3V
OLED SCL → PB2
OLED SDA → PB3
```

**注意**：不同 OLED 模块引脚顺序可能不同，接线前看丝印。GND 和 VCC 接反会烧坏模块。

## 2\. I2C 上拉电阻

I2C 的 SCL 和 SDA 都需要上拉电阻。I2C 设备通常只负责把线拉低或释放，当所有设备释放时，由上拉电阻把线拉成高电平。没有上拉电阻总线悬空，通信不稳定。

CCS 配置中把内部电阻配置为上拉。很多 OLED 模块板已自带外部上拉，同时开启内部上拉一般不影响低速实验。

## 3\. 在 CCS 中配置 I2C1

1. 添加 I2C 外设，命名为 `OLED`（名字影响生成的宏）
2. 选择 `I2C1`
3. 频率设为 $100\text{ kHz}$（默认 $1\text{ MHz}$ 在面包板杜邦线上可能不稳定）
4. 引脚映射：`SCL` → `PB2`，`SDA` → `PB3`
5. 内部上拉开启
6. 保存并重新编译

## 4\. 导入 OLED 驱动代码

资料包中已有写好的驱动（三个文件：`oled.c`、`oled.h`、字体文件），复制到当前工程目录。CCS 中确认文件可见后编译一次。

**关键步骤**：修改驱动中的 I2C 实例名。驱动代码默认可能是 `I2C_INST`，但配置中命名为 `OLED`，生成实例名为 `OLED_INST` 或类似。到配置生成的头文件中查找真实实例名，替换驱动代码中的默认名。

## 5\. 初始化与显示流程

```c
SYSCFG_DL_init();   // 初始化系统和外设（含 I2C）
OLED_Init();         // 初始化 OLED 模块
OLED_Clear();        // 清空显示缓冲区
OLED_Refresh();      // 刷新到屏幕

// 显示固定字符串
OLED_ShowString(0, 0, (uint8_t *)"Hello TI", 8);
OLED_Refresh();
```

OLED 通常以左上角 $(0,0)$ 为原点。$128\times64$ 屏幕中，$X\in[0,127]$，$Y\in[0,63]$。

**`OLED_Refresh()` 很重要**：显示函数写入缓冲区，只有调用 `Refresh()` 才通过 I2C 发送到屏幕。

## 6\. 显示变量

变量不能直接显示，需用 `sprintf()` 格式化为字符串：

```c
#include <stdio.h>

int a = 20;
char oled_str[50];

sprintf(oled_str, "a = %d", a);
OLED_ShowString(0, 46, (uint8_t *)oled_str, 8);
OLED_Refresh();
```

注意：
- `sprintf()` 需要包含 `<stdio.h>`
- 字符串类型警告可显式转换为 `(uint8_t *)`
- 循环中反复显示变量时，注意清除旧内容或补空格覆盖

## 7\. 常见问题排查

- OLED 完全不亮 → 先测 VCC 与 GND 电压
- 供电正常但不显示 → 检查 GND 共地、SCL/SDA 是否接反
- I2C 频率太高 → 降到 $100\text{ kHz}$
- 编译报错 → I2C 实例名与生成宏不一致
- 显示重叠或残留 → 刷新前 `OLED_Clear()` 或调整坐标

## 一页速记

- 四针 OLED：GND、VCC、SCL、SDA。SCL→PB2，SDA→PB3
- I2C 需要上拉电阻，CCS 中配置内部上拉
- I2C 频率建议 $100\text{ kHz}$（面包板杜邦线更稳定）
- 驱动中 I2C 实例名必须与配置生成宏一致
- 显示流程：初始化 → 清屏 → ShowString → Refresh
- 显示变量用 sprintf() 格式化，包含 `<stdio.h>`
- OLED 是调试利器：显示传感器读数、状态变量、错误码
