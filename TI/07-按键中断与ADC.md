---
title: 按键输入与 ADC 采样
tags:
  - TI
  - MSPM0
  - GPIO
  - 按键
  - 中断
  - ADC
  - 电赛
created: 2026-05-04
---

## 本节主线

电赛题目中"启动某个模块"通常不是重新上电，而是通过按键、拨码开关等输入信号让程序从等待状态进入执行状态。

本节围绕两个常用输入模块展开：按键模块（GPIO 数字电平检测）和旋钮电位器（ADC 模拟电压采集）。

## 1\. 按键模块原理

按键板结构：公共端接固定电平 + 若干个按键输出引脚。未按下时引脚与公共端不通；按下时导通。

本节公共端接 $3.3\text{ V}$，按键输出接 PB6、PB7：

| 按键状态 | GPIO 电平 | 程序判断 |
|----------|-----------|----------|
| 未按下 | 低电平（下拉） | 未触发 |
| 按下 | 高电平 | 触发 |

引脚必须配置**下拉输入**——未按下时若悬空，电平不确定会导致误判。

## 2\. GPIO 输入配置

```c
// 配置：PB6、PB7 为输入，下拉
// key9 → PB6, key10 → PB7
```

方向选输入，开启下拉电阻。配置后检查引脚是否被工具自动改过。

## 3\. 按键读取函数

```c
uint8_t Key_GetState(uint32_t key) {
    uint32_t high_bits = DL_GPIO_readPins(KEY_PORT, key);
    return ((high_bits & key) != 0) ? 1 : 0;
}
```

`DL_GPIO_readPins()` 返回的是**引脚位掩码**（如 PB6 对应 64），不是简单的 0 或 1。用按位与判断目标引脚是否高电平。

## 4\. 轮询读取的问题

```c
while (1) {
    delay_ms(10);
    if (Key_GetState(KEY_KEY9_PIN) == 1)
        status = (status + 1) % 3;
    OLED_Refresh();
}
```

轮询法简单直观，但实时性不够好——程序在执行延时或刷屏时可能错过短暂按键。推荐用**中断**。

## 5\. GPIO 中断

中断是"外部事件主动通知单片机"的机制。主程序继续执行，按键触发时自动暂停当前任务，进入中断服务函数处理。

常见触发方式：
- 上升沿触发（低→高，按下瞬间）
- 下降沿触发（高→低，松开瞬间）
- 双边沿触发（按和松都触发）

本节配置：PB6、PB7 为**上升沿触发**（未按下低电平，按下变高电平）。选双边沿会导致一次按下触发两次。

## 6\. 中断服务函数

GPIO 多个引脚共享同一中断入口，需先判断哪个引脚触发：

```c
extern uint8_t status;   // 全局变量，在 main.c 中定义

void GROUP1_IRQHandler(void) {
    uint32_t pending = DL_GPIO_getEnabledInterruptStatus(KEY_PORT, KEY_KEY9_PIN | KEY_KEY10_PIN);
    switch (pending) {
        case KEY_KEY9_PIN:
            status = (status + 1) % 3;
            DL_GPIO_clearInterruptStatus(KEY_PORT, KEY_KEY9_PIN);
            break;
        case KEY_KEY10_PIN:
            status = (status + 2) % 3;   // 等价于减 1，避免 uint8_t 下溢
            DL_GPIO_clearInterruptStatus(KEY_PORT, KEY_KEY10_PIN);
            break;
        default:
            DL_GPIO_clearInterruptStatus(KEY_PORT, pending);
            break;
    }
}
```

注意：**必须清除中断标志**，否则反复进入中断。主函数中需启用 NVIC 中断。

## 7\. 按键状态机

```c
uint8_t status = 0;   // 全局变量

if (status == 0)      OLED显示 "Status 0";
else if (status == 1) OLED显示 "Status 1";
else if (status == 2) OLED显示 "Status 2";
```

状态循环：$0 \rightarrow 1 \rightarrow 2 \rightarrow 0$，用 `(status + 1) % 3` 实现。电赛中用于切换不同题目或流程。

## 8\. ADC 基础

ADC（模数转换器）把连续变化的模拟电压转换为数字量。12 位 ADC 输出范围 $0 \sim 4095$：

$$V_{in} = \frac{N}{4096} \times V_{ref}$$

- $V_{in}$：输入电压
- $N$：ADC 采样值
- $V_{ref}$：参考电压（决定量程上限）

## 9\. ADC 配置

使用 PA16（对应 ADC 通道 1），内部参考 $2.5\text{ V}$：

| 配置项 | 值 |
|--------|-----|
| ADC 位数 | 12 位 |
| 输入引脚 | PA16 |
| ADC 通道 | 通道 1 |
| 转换模式 | 单次转换 |
| 触发方式 | 软件触发 |
| 参考电压 | 内部 $2.5\text{ V}$ |

参考电压选 $2.5\text{ V}$ 比 $3.3\text{ V}$ 更稳定，但旋钮输出超过 $2.5\text{ V}$ 后 ADC 满量程，无法区分更高电压。

## 10\. ADC 采样代码

```c
DL_ADC12_startConversion(ADC12_0_INST);
delay_ms(1);
uint16_t adc_result = DL_ADC12_getMemResult(ADC12_0_INST, DL_ADC12_MEM_IDX_0);

float voltage = adc_result * 2.5f / 4096.0f;

char buffer[32];
sprintf(buffer, "V: %.2f", voltage);
OLED_ShowString(0, 32, buffer);
OLED_Refresh();
```

注意电压换算避免整数除法——写成 `2.5f` / `4096.0f`。

## 一页速记

- 按键公共端接 $3.3\text{ V}$，引脚配置下拉输入，按下为高电平
- `DL_GPIO_readPins()` 返回位掩码，用 `(value & pin) != 0` 判断
- 轮询可能漏检，推荐 GPIO 中断（上升沿触发）
- 中断函数中必须清除中断标志
- 状态变量用 `(status + 1) % n` 实现循环切换
- 12 位 ADC：$V_{in} = N / 4096 \times V_{ref}$
- 内部参考 $2.5\text{ V}$，输入超过 $2.5\text{ V}$ 后满量程
- ADC 流程：startConversion → 等待 → getMemResult → 换算电压
