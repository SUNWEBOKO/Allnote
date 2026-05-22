---
title: UART 串口通信
tags:
  - TI
  - MSPM0
  - UART
  - 串口
  - 通信
  - 电赛
created: 2026-05-04
---

## 本节主线

串口（UART）是嵌入式系统中最常用的通信方式之一。单片机可以通过串口与电脑、视觉板、蓝牙模块等设备交换数据。本节重点掌握三件事：怎么接线、怎么配置、怎么写代码。

## 1\. UART 与 I2C 的区别

| 特性 | I2C | UART |
|------|-----|------|
| 信号线 | SCL（时钟）+ SDA（数据） | TX（发送）+ RX（接收） |
| 同步方式 | 有专用时钟线同步 | 异步，需约定波特率 |
| 接线 | 同向连接 | **交叉连接** |

## 2\. 接线规则

```
单片机 TX → 对方 RX
单片机 RX ← 对方 TX
单片机 GND ↔ 对方 GND
```

**TX 接对方 RX，RX 接对方 TX**。初学最常见的错误就是 TX-TX 直连。GND 必须共地。

## 3\. USB 转串口与电脑通信

单片机 UART 信号不能直接插 USB 口，需 USB 转串口模块（CH340/CH341）。

本节用 `UART0`，引脚：`PA28（TX）`、`PA31（RX）`。

接线：
```
PA28 (开发板 TX) → 模块 RX
PA31 (开发板 RX) → 模块 TX
GND              ↔ 模块 GND
```

电脑端用串口调试助手，选择对应 COM 口，波特率设为 `115200`。

## 4\. 工程配置

基于上一节工程复制修改。syscfg 中添加 UART 外设，命名如 `print`（名字影响生成宏）：

- 引脚：`PA28`、`PA31`
- 波特率：`115200`
- 保存并重新编译

## 5\. 发送字符与字符串

```c
void UART_SendChar(UART_Regs *uart, char ch) {
    DL_UART_Main_transmitDataBlocking(uart, ch);
}

void UART_SendString(UART_Regs *uart, const char *str) {
    while (*str != '\0') {
        UART_SendChar(uart, *str);
        str++;
    }
}

// 使用
UART_SendString(PRINT_INST, "hello ti\r\n");
```

`\r\n` 添加换行，串口助手显示更清晰。

## 6\. 接收数据与中断

发送主动权在单片机，但**接收不能阻塞等待**——单片机还需执行其他任务。用中断机制：

配置工具中开启 UART 接收中断 → 代码中启用 NVIC：

```c
NVIC_EnableIRQ(PRINT_INST_INT_IRQN);
```

中断服务函数：

```c
void PRINT_INST_IRQHandler(void) {
    switch (DL_UART_Main_getPendingInterrupt(PRINT_INST)) {
        case DL_UART_MAIN_IIDX_RX: {
            uint8_t data = DL_UART_Main_receiveData(PRINT_INST);
            DL_UART_Main_transmitDataBlocking(PRINT_INST, data);  // 回显
            break;
        }
        default:
            break;
    }
}
```

## 7\. 回显实验

电脑发送什么字符，单片机就返回什么字符。验证双向通信正常。

主函数结构：

```c
#include "ti_msp_dl_config.h"
#include "UART.h"

int main(void) {
    SYSCFG_DL_init();
    NVIC_EnableIRQ(PRINT_INST_INT_IRQN);

    while (1) {
        UART_SendString(PRINT_INST, "hello ti\r\n");
        delay_cycles(32000000);
    }
}
```

## 8\. 常见问题

- **收不到数据**：驱动是否安装？COM 口选对？波特率一致？TX-RX 交叉？GND 共地？
- **乱码**：波特率不匹配、数据位/停止位/校验位不一致、杜邦线接触不良
- **只能发不能收**：RX 是否接到模块 TX？接收中断开启？NVIC 使能？中断函数名写对？
- **改外设名后报错**：宏名和中断函数名都要同步修改

## 一页速记

- UART 接线：TX→RX、RX→TX、GND↔GND
- 波特率必须一致（常用 115200）
- USB 转串口模块（CH340）连接电脑
- 发送：逐个字符发送直到 '\0'
- 接收：用中断，不要在 while(1) 中阻塞等待
- 中断流程：配置开启 → NVIC_EnableIRQ → 服务函数中读取 + 清除标志
- 回显实验验证收发双向正常
