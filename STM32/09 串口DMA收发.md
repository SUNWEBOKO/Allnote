# 09. 串口 DMA 与不定长接收

> 本节重点：理解 DMA 如何将字节搬运从 CPU 卸载到硬件，掌握 `ReceiveToIdle` 方案实现不定长接收，以及处理 DMA 半传输中断带来的"误触发"问题。

---

## 本节核心问题

学完本节，需要能回答：

- 中断收发已经非阻塞了，为什么还需要 DMA？
- 串口接收的三种模式（轮询/中断/DMA）分别有什么特点？各适合什么场景？
- `ReceiveToIdle` 的第三个参数是"固定长度"还是"最大长度"？
- 什么是 DMA 半传输中断？为什么在不定长接收中需要关闭它？
- `HAL_UARTEx_RxEventCallback` 和 `HAL_UART_RxCpltCallback` 有什么区别？

---

## 1. 为什么还要 DMA

中断收发虽然非阻塞，但每个字节仍然需要 CPU 介入搬运：

```text
中断模式：每收到一字节 → CPU 中断 → 从寄存器搬到内存 → 返回
DMA 模式：硬件自动将字节从寄存器搬到内存 → 全部完成才通知 CPU
```

| 模式 | CPU 介入粒度 | CPU 负担 | 适用场景 |
|------|-------------|----------|----------|
| 轮询 | 整帧传输全程 | 最高 | 简单调试 |
| 中断 | 每个字节 | 中等 | 中小数据量 |
| DMA | 仅在开始和完成 | 最低 | 大数据量/高性能 |

### DMA 工作原理简介

DMA（Direct Memory Access）是一个**独立于 CPU 的硬件搬运引擎**：

```text
CPU：计算、控制、调度
DMA：在外设寄存器和内存之间批量搬运数据（无需 CPU 干预）
```

核心要素：

| 要素 | 说明 |
|------|------|
| 请求映射 | 每个外设通道（UART_RX、ADC 等）对应一条 DMA 请求线 |
| 源地址 | 从哪搬（如 UART->DR 数据寄存器） |
| 目标地址 | 搬到哪（如内存缓冲区） |
| 传输长度 | 搬多少字节 |
| 传输模式 | Normal（搬完停）或 Circular（搬完自动循环） |
| 地址自增 | 源/目标地址每次传输后是否自动递增 |

DMA 的关键思维转变：**由"每来一个字节打断 CPU"变成"告诉 DMA 去哪里搬、搬多少，完成后通知 CPU 一次"。**

---

## 2. CubeMX 配置步骤

### 2.1 DMA 通道配置

| 步骤 | 操作 |
|------|------|
| 1 | 进入 `UARTx → DMA Settings` |
| 2 | 添加 `UARTx_TX`，方向 `Memory to Peripheral` |
| 3 | 添加 `UARTx_RX`，方向 `Peripheral to Memory` |
| 4 | 数据宽度保持字节（Byte） |
| 5 | 内存地址自增使能 |
| 6 | 模式选择 `Normal`（非循环） |

### 2.2 配置参数说明

| 参数 | 说明 |
|------|------|
| 方向 | TX: 内存→外设, RX: 外设→内存 |
| 地址自增 | 每次传输后源/目标地址自动递增 |
| 模式 | Normal 传输完即停，Circular 循环缓冲 |

---

## 3. DMA 串口 API

| 函数 | 用途 |
|------|------|
| `HAL_UART_Transmit_DMA(huart, data, len)` | DMA 发送 |
| `HAL_UART_Receive_DMA(huart, buf, len)` | DMA 定长接收 |
| `HAL_UARTEx_ReceiveToIdle_DMA(huart, buf, max_len)` | DMA 不定长接收 |

**`ReceiveToIdle` 的第三个参数是"最大接收长度"，不是"本帧固定长度"。**

---

## 4. 不定长接收机制：空闲中断

```text
数据流到达 → DMA 自动搬运到缓冲区 → 串口总线空闲(IDLE) → 触发回调
```

当串口总线空闲超过一个字节时间时，硬件产生 IDLE 中断，HAL 判断本次接收结束。

```c
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    if (huart->Instance == USART2)
    {
        // 1) 处理 rx_buf[0..Size-1]（Size 是本次实际接收长度）
        ProcessData(rx_buf, Size);

        // 2) 重新启动下一轮 ReceiveToIdle DMA
        HAL_UARTEx_ReceiveToIdle_DMA(&huart2, rx_buf, sizeof(rx_buf));
    }
}
```

---

## 5. 半传输中断问题

### 5.1 现象

DMA 在传输到一半（缓冲区一半）时也会触发事件，导致 `RxEventCallback` 在数据未收完时提前被调用。

### 5.2 解决

关闭 DMA 半传输中断（HT），只保留完成传输和空闲中断：

```c
/* 初始化后执行一次 */
__HAL_DMA_DISABLE_IT(huart2.hdmarx, DMA_IT_HT);
```

### 5.3 两种回调的区别

| 回调 | 适用场景 | 说明 |
|------|----------|------|
| `HAL_UART_RxCpltCallback` | 定长中断/DMA | 固定长度接收完成 |
| `HAL_UARTEx_RxEventCallback` | ReceiveToIdle DMA | 不定长接收完成，带 Size 参数 |

---

## 6. 高频易错点

1. **只收到一帧**。回调里忘记重启 `HAL_UARTEx_ReceiveToIdle_DMA`。

2. **长包被截断**。缓冲区太小，第三个参数（最大接收长度）设置不合理。

3. **回调次数异常偏多**。未关闭 `DMA_IT_HT`，半传输中断导致提前回调。

4. **还在用旧回调**。`ReceiveToIdle` 方案应使用 `HAL_UARTEx_RxEventCallback`，写在 `RxCpltCallback` 里无效。

5. **数据粘包/拆包处理混乱**。以 `Size` 为准做边界处理，不要按固定长度硬拆。

---

## 7. 一页速记

### 三种接收模式对比

| 模式 | CPU 占用 | 灵活性 | 适合 |
|------|----------|--------|------|
| 轮询 | 最高 | 低 | 教学调试 |
| 中断 | 中 | 中 | 小数据量 |
| DMA | 最低 | 高 | 大数据量/高速 |

### 不定长接收配置
```text
HAL_UARTEx_ReceiveToIdle_DMA(huart, buf, max_len)
     ↓
空闲中断 → RxEventCallback(huart, Size)
     ↓
回调中续接下一轮
```

### 坑点口诀
```text
收到一帧就停   → 回调没续接
回调频繁提前   → 关 DMA_IT_HT
用错回调函数   → 检查是 RxEvent 还是 RxCplt
```

### 最重要的一句话
> DMA 的价值不是"让串口更快"，而是"让 CPU 更闲"——字节搬运从 CPU 转移到硬件通道。

---

## 8. 自测题

1. DMA 相比中断模式，在串口收发中的核心改进是什么？
2. `HAL_UARTEx_ReceiveToIdle_DMA()` 的第三个参数应该填什么？为什么？
3. 空闲中断（IDLE）是在什么条件下触发的？
4. DMA 半传输中断为什么会导致不定长接收的"误触发"？
5. 不定长接收场景下，应该使用哪个回调函数？
6. 如果串口 DMA 只收到一帧数据就再没反应了，最可能的原因是什么？
