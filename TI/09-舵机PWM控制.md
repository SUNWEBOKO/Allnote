---
title: 舵机控制与 PWM
tags:
  - TI
  - MSPM0
  - 舵机
  - PWM
  - 定时器
  - 电赛
created: 2026-05-04
---

## 本节主线

舵机是一种可控角度执行机构，常见于电磁炮角度调节、小车转向、机械臂等电赛场景。它通常只需三根线：电源正极、电源负极和 PWM 信号线。

舵机控制的核心是 PWM（脉宽调制）——在固定周期内改变高电平时间来决定角度。本节使用定时器硬件自动生成 PWM，而非 GPIO 加延时手动翻转。

## 1\. 舵机三根线

| 线 | 颜色 1 | 颜色 2 | 连接 |
|---|--------|--------|------|
| GND | 棕色 | 黑色 | 电源负极 + 单片机 GND 共地 |
| VCC | 红色 | 红色 | 电源正极（$5\text{ V}$），独立供电 |
| 信号 | 黄色 | 白色 | 单片机 PWM 输出引脚 |

**千万不能直接用开发板 5V 给舵机供电**——舵机启动电流大，可能拉低电压导致单片机复位。用独立电源模块（如锂电池 + 降压模块）。

舵机 GND 必须和单片机 GND 共地，否则 PWM 信号没有参考点。

## 2\. PWM 控制原理

普通 $180^\circ$ 舵机要求 PWM 周期 $T = 20\text{ ms}$（频率 $50\text{ Hz}$），高电平时间决定角度：

| 高电平时间 | 角度 |
|-----------|------|
| $0.5\text{ ms}$ | $0^\circ$ |
| $1.5\text{ ms}$ | $90^\circ$ |
| $2.5\text{ ms}$ | $180^\circ$ |

角度 $\theta$ 与高电平时间 $t_{high}$ 的线性关系：

$$\theta = \frac{t_{high} - 0.5\text{ ms}}{2\text{ ms}} \times 180^\circ$$

$$t_{high} = 0.5\text{ ms} + \frac{\theta}{180^\circ} \times 2\text{ ms}$$

## 3\. 为什么不用 GPIO + 延时手搓 PWM

```c
while (1) {
    GPIO_SetHigh(); delay_ms(1.5);
    GPIO_SetLow();  delay_ms(18.5);
}
```

这种方法确实能产生 PWM，但 CPU 一直在空等延时，无法同时做其他事（读传感器、控制算法、通信等）。实际工程使用**定时器硬件**自动生成 PWM。

## 4\. 定时器生成 PWM 的原理

定时器本质是计数器——接收固定频率脉冲，每来一个脉冲计数值加 1。两个关键值：
- **周期值**：计数到多少重新开始，决定 PWM 周期
- **比较值**：计数到多少翻转电平，决定高电平时间

计数过程：计数值从 0 开始 → 到比较值时低电平 → 到周期值时复位 → 高电平重新开始。

## 5\. 本节参数配置

定时器计数频率设为 $100\text{ kHz}$，每计数 1 次对应 $0.01\text{ ms}$：

- 周期 $20\text{ ms} \rightarrow 2000\text{ 次计数}$
- $0.5\text{ ms} \rightarrow 50\text{ 次计数}$
- $1.5\text{ ms} \rightarrow 150\text{ 次计数}$
- $2.5\text{ ms} \rightarrow 250\text{ 次计数}$

| 角度 | 比较值 |
|------|--------|
| $0^\circ$ | $50$ |
| $90^\circ$ | $150$ |
| $180^\circ$ | $250$ |

## 6\. CCS 配置

添加 Timer PWM 配置（如 `TIMG7_C1` → `PA27`），命名如 `SERVO`：

1. 定时器时钟分频到约 $100\text{ kHz}$
2. 计数模式：向上计数
3. 周期值：$2000$
4. 初始比较值：$150$（$90^\circ$）
5. 保存编译

## 7\. 动态改变角度

```c
// 角度转比较值
uint32_t Servo_AngleToCompare(float angle) {
    if (angle < 0.0f) angle = 0.0f;
    if (angle > 180.0f) angle = 180.0f;
    return (uint32_t)(50.0f + angle / 180.0f * 200.0f);
}

// 设置角度
void Servo_SetAngle(float angle) {
    uint32_t compare = Servo_AngleToCompare(angle);
    DL_TimerG_setCaptureCompareValue(TIMG7, compare, DL_TIMER_CC_0_INDEX);
}

// 往复摆动
while (1) {
    for (int v = 50; v <= 250; v++) {
        DL_TimerG_setCaptureCompareValue(TIMG7, v, DL_TIMER_CC_0_INDEX);
        delay_ms(10);
    }
    for (int v = 250; v >= 50; v--) {
        DL_TimerG_setCaptureCompareValue(TIMG7, v, DL_TIMER_CC_0_INDEX);
        delay_ms(10);
    }
}
```

## 8\. 示波器观察

周期应为 $20\text{ ms}$（$50\text{ Hz}$），高电平幅值约 $3.3\text{ V}$。手动数格子比自动测量更可靠。

## 9\. 常见错误

- **未共地**：舵机由外部电源供电，GND 必须与单片机相连
- **板载 5V 供电**：舵机启动电流大，应用独立电源
- **PWM 频率不对**：普通舵机要求 $50\text{ Hz}$，偏差会导致抖动或角度不准
- **比较值超范围**：卡机械限位会发热甚至烧毁，留余量
- **信号线接错引脚**：必须接到配置好的定时器通道对应引脚

## 一页速记

- 舵机三线：GND（棕/黑）、VCC（红）、信号（黄/橙）
- 舵机独立供电，GND 必须和单片机共地
- PWM 周期 $20\text{ ms}$（$50\text{ Hz}$），高电平时间决定角度
- $0.5\text{ ms}\to 0^\circ$、$1.5\text{ ms}\to 90^\circ$、$2.5\text{ ms}\to 180^\circ$
- 用定时器硬件生成 PWM，不用 GPIO 手搓
- 计数频率 $100\text{ kHz}$，周期值 $2000$，比较值 $50$~$250$
- 动态改比较值 = 动态改角度，范围留余量避免撞限位
