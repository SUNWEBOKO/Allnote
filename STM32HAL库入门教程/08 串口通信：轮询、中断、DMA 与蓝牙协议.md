# 08 串口通信：轮询、中断、DMA 与蓝牙协议
上一篇：[[07 DMA：数据搬运与 ADC 多通道采集]] ｜ 下一篇：[[09 I2C：总线时序与软件 I2C 驱动 OLED]]

## 本章闭环

串口通信的核心不是记住几个 HAL 函数，而是建立一条完整的数据链：

```text
发送端内存
-> USART 数据寄存器
-> 发送移位寄存器
-> TX 引脚上的高低电平
-> 对端 RX 引脚
-> 接收移位寄存器
-> USART 数据寄存器
-> 接收端内存
-> 数据包解析与业务动作
```

本章沿着这条链路逐步完成五个实验：

1. 实验一：使用 USART2 轮询发送 `Hello World`，再接收固定 2 字节指令控制红、绿、蓝 LED；
2. 实验二：使用中断模式完成非阻塞定长接收；
3. 实验三：使用 DMA 完成定长收发；
4. 实验四：使用 DMA 与 IDLE 空闲线接收不定长数据；
5. 实验五：使用 USART3 连接蓝牙透传模块，解析带包头、长度和校验和的数据包。

完成本章后，应能：

- 正确连接 TTL UART 的 TX、RX 和 GND；
- 解释起始位、数据位、校验位、停止位与波特率；
- 区分轮询、中断和 DMA 各自承担的数据搬运工作；
- 使用 `HAL_UART_Receive_IT()` 和 `HAL_UART_RxCpltCallback()` 完成定长接收；
- 使用 `HAL_UARTEx_ReceiveToIdle_DMA()` 和 `HAL_UARTEx_RxEventCallback()` 接收不定长数据；
- 解释 IDLE、HT、TC 三类接收事件，避免把半传输回调误当成完整数据包；
- 设计并校验一个简单二进制数据包；
- 沿“引脚—参数—中断—DMA—缓冲区—协议”链路定位串口故障。

默认芯片为 STM32F103C8T6，开发环境为 STM32CubeMX、STM32CubeIDE 或 Keil 与 STM32 HAL 库。电脑调试串口使用 USART2，默认引脚为 PA2/PA3；蓝牙串口使用 USART3，默认引脚为 PB10/PB11。实际开发板若已重映射或使用板载 USB 转串口芯片，应以原理图为准。

## 1. 先分清 UART、USART 与电平标准

### 1.1 本章所说的“串口”是什么

“串行通信”只说明数据按时间顺序一位一位传送，范围很广。USB、SPI、I2C、CAN 都属于串行通信，但它们的电气结构和协议并不等同于单片机常说的 TTL UART。

本章讨论的是 STM32 USART 外设工作在异步模式时形成的 UART 通信：

- `UART`：Universal Asynchronous Receiver/Transmitter，通用异步收发器；
- `USART`：Universal Synchronous/Asynchronous Receiver/Transmitter，同时支持同步和异步模式；
- STM32F103 的 USART 配置为 `Asynchronous` 后，就可以用于常见的无时钟线 UART 通信。

TTL UART、RS-232 和 RS-485 不能只靠改软件参数互相直连：

| 名称 | 常见线路 | 电气特点 | 与 STM32 直连 |
| --- | --- | --- | --- |
| 3.3 V TTL UART | TX、RX、GND | 以 MCU 电源域为逻辑电平参考 | 可以，但要核对电平 |
| 5 V TTL UART | TX、RX、GND | 高电平可能接近 5 V | 不应默认可直连 |
| RS-232 | TX、RX、GND | 正负电压、逻辑可能反相 | 需要 RS-232 收发器 |
| RS-485 | A、B，常带 GND | 差分、常为半双工总线 | 需要 RS-485 收发器 |
| USB | D+、D- | 差分总线和完整 USB 协议 | 需要 USB 外设或 USB 转串口芯片 |

板载 USB 转串口芯片的作用，是在 USB 协议与 TTL UART 之间转换。电脑看到的是一个虚拟串口，STM32 侧仍通过 USART 的 TX/RX 收发字节。

### 1.2 TX 与 RX 必须交叉连接

两个设备全双工通信时：

```text
设备 A TX ----> 设备 B RX
设备 A RX <---- 设备 B TX
设备 A GND ----- 设备 B GND
```

TX 是本设备发送端，RX 是本设备接收端，因此不能把两个 TX 接在一起。若只需要 STM32 单向发送给电脑，只连接 `STM32 TX -> 转串口 RX` 和 GND 即可；若需要双向通信，则两条数据线都要连接。

### 1.3 为什么必须共地

数字电平是相对参考点的电压。发送端输出“3.3 V 高电平”，实际含义是 TX 相对发送端 GND 约为 3.3 V。若接收端与发送端没有共同参考地，它看到的电压可能漂移，通信就会不稳定或完全失败。

因此，两个独立供电的设备通常必须共地。共地解决的是参考电势问题，不等于允许两个不同电压域直接连接。

### 1.4 供电电压和 IO 电平不能混为一谈

STM32F103x8/B 的 `VDD` 工作范围为 2.0～3.6 V。数据手册虽然标出了许多 `FT`（5 V tolerant）引脚，但不是所有引脚都耐受 5 V；PA2、PA3 的引脚表中并未标为 FT，不能把 5 V UART 信号直接接到 PA3。

蓝牙模块的 `VCC` 允许接 5 V，不代表模块的 UART TX 一定输出 5 V；模块电源与通信 IO 电平是两个不同参数。连接前应核对模块板说明，优先使用 3.3 V UART 电平，必要时增加电平转换。

具体做法：

- 多数 USB 转 TTL 模块板上有 3.3 V/5 V 跳线或跳帽，**把跳线拨到 3.3 V 一侧**，让模块 TX 的高电平变成 3.3 V，这是最简单也最可靠的一步；
- 跳线固定为 5 V、无法改变的模块，不要直接接到 `PA3`：应加电平转换（专用电平转换模块或 3.3 V 供电的转串口芯片）；仅在应急时可用串电阻限流加钳位，且不能长期依赖；
- 蓝牙模块侧同理，先确认模块的 UART IO 是 3.3 V 逻辑再接线。

再强调一次：`PA2/PA3` 在 STM32F103C8T6 上不是 5 V 容忍（FT）引脚，把 5 V 直接加进去会让电流经引脚内部保护结构灌入，可能永久损坏引脚。

## 2. UART 怎样把一个字节放到线上

### 2.1 异步通信为什么不需要时钟线

UART 没有额外的时钟线，双方预先约定波特率和帧格式。接收端检测到起始位后，按约定时间间隔采样数据位，因此通信双方至少要一致配置：

- 波特率；
- 数据位长度；
- 奇偶校验；
- 停止位数量。

最常见的配置是 `115200, 8N1`：

- `115200`：每秒 115200 个码元；
- `8`：8 个数据位；
- `N`：无奇偶校验；
- `1`：1 个停止位。

### 2.2 一帧 8N1 数据的结构

线路空闲时通常保持高电平。发送一个 8 位字节时，典型 8N1 帧为：

```text
空闲高电平
-> 1 位起始位 0
-> 8 位数据，低位先发
-> 1 位停止位 1
-> 回到空闲高电平
```

每个有效字节实际占用：

$$
1+8+1=10\ \text{bit}
$$

因此在 115200 波特、8N1 条件下，忽略帧间间隔时的理论最大字节率为：

$$
\frac{115200}{10}=11520\ \text{Byte/s}
$$

这里 UART 使用二进制 NRZ 编码，一个码元携带一个比特，所以数值上波特率等于比特率。更一般的通信系统中，一个码元可能携带多个比特，二者不能永远画等号。

### 2.3 波特率不一致为什么会乱码

接收端根据自己的波特时钟决定采样时刻。双方波特率不一致时，采样点会逐位偏移；偏移积累到一定程度后，接收端会把相邻位误判为当前位，产生错误字符、帧错误或完全收不到数据。

出现乱码时，先检查：

1. MCU 与串口助手的波特率是否一致；
2. 是否都为 8N1；
3. MCU 外部晶振和时钟树是否配置正确；
4. 串口助手是否把二进制数据误按文本显示。

### 2.4 ASCII 显示与十六进制显示

串口线上只有字节，没有“字符模式”和“十六进制模式”。这两个模式只是串口助手对同一字节的不同解释。

例如字符串 `Hello` 的前两个字节为：

| 字符 | ASCII 十六进制 |
| --- | --- |
| `H` | `0x48` |
| `e` | `0x65` |

若按文本显示，`0x48 0x65` 会显示为 `He`；若按 HEX 显示，则显示为 `48 65`。调试二进制协议时应使用 HEX 模式，调试普通文本时使用 ASCII 或 UTF-8 文本模式。

## 3. STM32F103 的 USART 资源

### 3.1 USART 数量与速率上限

STM32F103x8/B 中等容量产品最多包含 USART1、USART2 和 USART3。数据手册给出的接口能力为：

- USART1 最高通信速率可达 4.5 Mbit/s；
- USART2、USART3 最高通信速率可达 2.25 Mbit/s；
- 所有 USART 都支持 DMA。

USART1 位于 APB2，最高外设时钟可达 72 MHz；USART2 和 USART3 位于 APB1，最高外设时钟为 36 MHz。实际波特率由外设时钟与波特率分频值共同决定，CubeMX 会根据时钟树计算 `USART_BRR`。

STM32F103 的波特率分频公式为：

$$
\text{USARTDIV}=\frac{f_{\text{PCLK}}}{16\times \text{baud}}
$$

`USARTDIV` 写进 `USART_BRR` 时，整数部分占高 12 位（尾数），小数部分只有 4 位，也就是分频只能取到 `1/16` 的整数倍（等效于 `BRR = round(USARTDIV × 16)`）。在 `PCLK1 = 36 MHz` 时：

| 波特率 | USARTDIV | BRR 寄存器 | 实际波特率 | 相对误差 |
| --- | --- | --- | --- | --- |
| 115200 | 19.53125 | `0x138`（尾数 19、小数 8 → 分频 19.5） | 115384.6 | +0.16% |
| 9600 | 234.375 | `0xEA6`（尾数 234、小数 6 → 分频 234.375） | 9600 | 0% |

115200 在 36 MHz 下除不尽，所以带一个固定的 +0.16% 偏差，远小于一帧内允许的累积误差，可以正常通信；9600 恰好整除，误差为 0。注意这里的 `PCLK1` 必须是 36 MHz：如果改过时钟树（比如把 APB1 预分频设成 1，或外部晶振频率填错），CubeMX 会按错误的 `PCLK1` 算 `BRR`，实际波特率随之偏移并出现乱码——**改动时钟树后要回到第 03 章核对 `APB1 = 36 MHz`**。

这些是外设能力上限，不代表连接线、转串口芯片、蓝牙模块和对端设备都能在该速率下可靠工作。入门调试常用 9600 或 115200。

### 3.2 常用默认引脚

| USART | 默认 TX | 默认 RX | 本章用途 |
| --- | --- | --- | --- |
| USART1 | PA9 | PA10 | 可作调试或下载接口 |
| USART2 | PA2 | PA3 | 电脑 USB 转串口 |
| USART3 | PB10 | PB11 | 蓝牙透传模块 |

STM32F103 支持 USART 引脚重映射。例如 USART2 可重映射到 PD5/PD6，USART3 可部分重映射到 PC10/PC11；但部分重映射引脚只存在于较大封装。STM32F103C8T6 常见 LQFP48 封装的端口 D 只有作晶振引脚的 PD0/PD1，没有 PD5/PD6 等通用 GPIO，因此不能照搬只适用于大封装的 USART2 重映射方案。

**`PB10/PB11` 与第 02 章 OLED 的引脚冲突**：`PB10/PB11` 正是第 02 章 OLED 使用的 `I2C2_SCL/I2C2_SDA`。STM32F103C8T6 是 LQFP48 封装，芯片没有引出 `PC0~PC12`，因此 USART3 的部分重映射（`PC10/PC11`）和完全重映射（`PD8/PD9`）在这块板子上都不可用，`USART3` 只能落在 `PB10/PB11`，**没有重映射可以绕开这个冲突**。

由此得到本章的一条硬约束：

- **不要把第 02 章的 OLED 观察窗口和本章的蓝牙实验放进同一个工程**，两者必须二选一；
- 如果既要 OLED 又要蓝牙，把 OLED 换成第 09 章《09 I2C：总线时序与软件 I2C 驱动 OLED》的 `PB8/PB9` 软件 I2C 方案，把 `PB10/PB11` 留给 `USART3`（第 02 章已经提示过这个冲突）。

### 3.3 USART 与 DMA 通道的固定映射

STM32F103C8T6 使用 DMA1，其 USART 请求映射由硬件固定：

| DMA1 通道 | USART 请求 |
| --- | --- |
| Channel 2 | USART3_TX |
| Channel 3 | USART3_RX |
| Channel 4 | USART1_TX |
| Channel 5 | USART1_RX |
| Channel 6 | USART2_RX |
| Channel 7 | USART2_TX |

CubeMX 会根据外设自动选择通道，但仍要检查通道是否被其他外设占用。DMA 通道优先级只决定多个请求冲突时的仲裁顺序，不能改变 USART 自身的字节产生速度。

## 4. USART 内部数据链与关键标志

### 4.1 发送链路

发送端可概括为：

```text
内存字节
-> USART_DR 中的发送数据缓冲
-> 发送移位寄存器
-> 按波特率逐位从 TX 输出
```

两个容易混淆的状态标志是：

| 标志 | 含义 | 适合判断什么 |
| --- | --- | --- |
| `TXE` | 发送数据寄存器已空，可以写下一个数据 | 继续填充下一字节 |
| `TC` | 当前完整帧已经从移位寄存器发送结束 | 关闭串口、切换收发方向或确认最后一位已发完 |

DMA 把最后一个字节写入 `USART_DR`，只表示内存搬运结束，不一定表示最后一个停止位已经离开 TX。需要立即关闭 USART 或控制 RS-485 方向时，还要等待 `TC=1`。

### 4.2 接收链路

接收端可概括为：

```text
RX 引脚采样
-> 接收移位寄存器
-> USART_DR 中的接收数据缓冲
-> CPU 或 DMA 读入内存
```

关键标志包括：

| 标志 | 含义 | 典型用途 |
| --- | --- | --- |
| `RXNE` | 数据寄存器中已有可读数据 | 逐字节中断或 DMA 请求 |
| `IDLE` | 接收过数据后，线路检测到一个空闲帧 | 识别一段突发数据暂时结束 |
| `ORE` | 上一个字节还未取走，下一个字节又到达 | 诊断接收不及时或链路未正确处理 |
| `FE` | 停止位等帧格式不符合预期 | 检查波特率和线路质量 |
| `NE` | 采样检测到噪声 | 检查接地、布线和干扰 |

参考手册规定，`IDLE` 标志通过“先读 `USART_SR`，再读 `USART_DR`”的软件序列清除。使用 HAL IRQ 处理函数时，不要绕过 HAL 再自行随意清标志。

`ORE`、`FE`、`NE`、`PE` 这几个错误标志也用同一套“先读 `USART_SR`、再读 `USART_DR`”的序列清除，使用 HAL 时同样由 `HAL_UART_IRQHandler()` 统一完成（它读到错误后会调用 `HAL_UART_ErrorCallback()`），应用层不要自己插队清标志。

需要特别记住的是这些错误的后果：**HAL 在报告错误的同时会中止当前接收**。中断模式下它结束这一轮接收；**DMA 模式下它会停止 DMA 通道并把句柄状态置回 Ready**，此后缓冲区不再更新、也不会再有回调——一次 ORE 之后就再也收不到数据，必须按 9.7 节的流程重新启动接收才恢复。所以“第一次能用，拔插一次线以后只能用复位恢复”这类现象，多半是错误标志触发了一次接收中止，而不是收发器坏了。

### 4.3 轮询、中断和 DMA 的分工

| 模式 | 谁搬每个字节 | CPU 是否等待 | 完成通知 | 适用场景 |
| --- | --- | --- | --- | --- |
| 轮询 | CPU | 是 | 函数返回 | 初次验证、低频短数据 |
| 中断 | CPU 在 ISR 中搬 | 否 | UART 回调 | 低到中等速率、定长命令 |
| DMA | DMA 控制器 | 否 | DMA/UART 回调 | 连续数据、批量收发、不定长接收 |

中断模式只是把“反复查询”改成“事件到来时处理”，每个字节仍需要 CPU 进入中断完成读写。DMA 则直接在 USART 数据寄存器和内存之间搬运，CPU 通常只在半传输、传输完成、空闲线或错误事件时介入。

## 5. CubeMX 基础配置

### 5.1 先保留 SWD 调试接口

从本章开始会频繁使用复用功能。新建工程后建议先在 `System Core -> SYS` 中把 Debug 设置为 `Serial Wire`，保留 SWDIO 和 SWCLK，避免错误配置调试口后无法再次下载程序。

### 5.2 USART2 轮询实验

1. 打开 `Connectivity -> USART2`；
2. 选择 `Asynchronous`；
3. 设置波特率 `115200`；
4. Word Length 选择 `8 Bits`；
5. Parity 选择 `None`；
6. Stop Bits 选择 `1`；
7. 确认引脚为 PA2/USART2_TX 和 PA3/USART2_RX；
8. 生成代码，确认存在 `MX_USART2_UART_Init()`。

若开发板已把 USART2 接到板载 USB 转串口芯片，只需 USB 数据线连接电脑；否则需要外接 USB 转 TTL 模块，并按 TX/RX 交叉、GND 共地连接。

### 5.3 中断模式增加的配置

在 USART2 的 `NVIC Settings` 中使能 `USART2 global interrupt`。**这一项在后面的所有实验里都要保留**：中断定长接收靠它，DMA / ReceiveToIdle 接收同样靠它处理 IDLE 和错误事件，不要因为改用 DMA 就把它关掉。生成代码后应存在：

```c
void USART2_IRQHandler(void)
{
    /* HAL 统一处理 RXNE、TC、IDLE 和错误标志。 */
    HAL_UART_IRQHandler(&huart2);
}
```

应用层使用 HAL 回调接收完成事件，不应删除 `HAL_UART_IRQHandler()`，因为它负责判断 TXE、TC、RXNE、IDLE 和错误等多个共用同一中断向量的来源。

### 5.4 DMA 模式增加的配置

在 USART2 的 `DMA Settings` 中分别添加：

| 请求 | 通道 | 方向 | 外设自增 | 内存自增 | 宽度 | 模式 |
| --- | --- | --- | --- | --- | --- | --- |
| USART2_RX | DMA1 Channel 6 | Peripheral to Memory | Disable | Enable | Byte | Normal |
| USART2_TX | DMA1 Channel 7 | Memory to Peripheral | Disable | Enable | Byte | Normal |

同时确认 **`DMA1 Channel 6/7` 的 NVIC 已启用**，并且**再使能 `USART2 global interrupt`**：`HAL_UARTEx_ReceiveToIdle_DMA()` 只会打开 DMA 接收并软件置位 `IDLEIE`，而 IDLE 事件是在 `USART2_IRQHandler()` → `HAL_UART_IRQHandler()` 里被识别、进而调用回调的。NVIC 里没开 USART2 全局中断时，短数据永远等不到回调，只有恰好填满缓冲区（由 DMA 通道中断报传输完成）才会回调一次，很容易被误判成“接收不工作”。（下一节的实验二只用中断、不用 DMA，则只需要 `USART2 global interrupt`。）

串口接收不定长命令时先使用 Normal 模式，完成一帧后处理并重新启动；Circular 模式适合连续流，但需要额外管理读写位置，不作为本章主代码。

### 5.5 本章输出不使用 printf

本章所有示例都用 `HAL_UART_Transmit()` 直接发送字节数组，**不依赖 `printf`**，所以五个实验的代码复制进工程后不需要任何额外配置，也与使用 Keil 还是 STM32CubeIDE 无关。

若确实想用 `printf` 打印到 USART2，必须按工具链重定向底层输出函数。Keil MDK（ARMCC / armclang）重写 `fputc()`：

```c
#include <stdio.h>

int fputc(int ch, FILE *f)
{
    uint8_t byte;

    (void)f;
    byte = (uint8_t)ch;
    HAL_UART_Transmit(&huart2, &byte, 1U, 100U);

    return ch;
}
```

重写后需要在工程选项 `Target -> Use MicroLIB` 中勾选 MicroLIB；不勾选时 `printf` 会依赖半主机调用，程序可能卡在输出上。

STM32CubeIDE / GCC 则重写 `__io_putchar()`（CubeMX 生成的 `syscalls.c` 会调用它），或直接重写 `_write()`：

```c
int __io_putchar(int ch)
{
    uint8_t byte;

    byte = (uint8_t)ch;
    HAL_UART_Transmit(&huart2, &byte, 1U, 100U);

    return ch;
}
```

两点补充：

- 两种重定向都是逐字节阻塞发送，只适合调试打印，不要在中断、回调或要求实时性的循环中调用；
- 用 `%f`/`%lf` 打印浮点数时，浮点格式化代码默认不会被链接：GCC / STM32CubeIDE 需要在链接选项里加入 `-u _printf_float`，Keil 勾选 `Use MicroLIB` 后即可用。不额外使能时 `%f` 没有输出，这不是串口配置错误。

## 6. 实验一：轮询发送与固定长度指令

### 6.1 每秒发送一次 Hello World

在用户代码区定义：

```c
static const uint8_t message[] = "Hello World\r\n";
```

主循环中发送：

```c
while (1)
{
    HAL_UART_Transmit(&huart2,
                      message,
                      (uint16_t)(sizeof(message) - 1U),
                      100U);
    HAL_Delay(1000U);
}
```

> **本章各实验是替换关系，不是叠加关系。** 五个实验共用同一个 `main.c`：做下一个实验时，把上一个实验的主循环和回调**替换**掉，而不是把新代码追加在后面。一个 `main.c` 只能有一个 `while (1)`，两个循环写在同一个函数里时第二个永远执行不到；`HAL_UART_RxCpltCallback()`、`HAL_UARTEx_RxEventCallback()`、`HAL_UART_ErrorCallback()` 这些 HAL 弱回调同理，同名强定义在同一个工程里只能保留一个。

`sizeof(message) - 1U` 去掉了字符串结尾自动添加的 `'\0'`。也可以使用 `strlen()`，但需要包含 `string.h`，并将返回的 `size_t` 在确认长度不超过 `uint16_t` 后转换。

`HAL_UART_Transmit()` 的第四个参数是超时时间，单位为毫秒。`HAL_MAX_DELAY` 表示持续等待，适合最小实验，但正式程序应评估外设异常时永久阻塞的风险。

### 6.2 固定 2 字节 LED 指令

规定命令格式：

| 第 0 字节 | 第 1 字节 | 含义 |
| --- | --- | --- |
| `'R'`、`'G'`、`'B'` | `'0'` | 关闭对应 LED |
| `'R'`、`'G'`、`'B'` | `'1'` | 打开对应 LED |

例如：

- `R1`：打开红灯；
- `B0`：关闭蓝灯。

先把三个 LED 引脚配置为 GPIO 推挽输出。本章用 `PB12`、`PB13`、`PB14` 分别接红、绿、蓝三色 LED：这三个引脚在 LQFP48 上没有复用冲突（`PA2/PA3` 归 USART2，`PB10/PB11` 归 OLED 的 I2C2 或 USART3，`PB8/PB9` 归第 09 章的软件 I2C OLED，`PA13/PA14` 是 SWD 调试口，`PC13` 是板载 LED）。

CubeMX 配置与接线：

| 引脚 | GPIO 模式 | User Label | 接线 |
| --- | --- | --- | --- |
| `PB12` | `GPIO_Output`，`Output Push Pull`，初始电平 Low | `RED_LED` | `PB12` → 约 1 kΩ 限流电阻 → 红灯阳极（长脚），阴极（短脚） → GND |
| `PB13` | 同上 | `GREEN_LED` | 绿灯同样串 1 kΩ 后接 GND |
| `PB14` | 同上 | `BLUE_LED` | 蓝灯同样串 1 kΩ 后接 GND |

要点：

- **User Label 必须填**：在 CubeMX 的引脚图上双击引脚（或 `System Core -> GPIO` 面板里改 `User Label`），填 `RED_LED` 等名字，生成代码时才会产出 `RED_LED_GPIO_Port` 与 `RED_LED_Pin` 这两个宏；不填标签就只有 `GPIOB`、`GPIO_PIN_12`，下面的代码会编译不过。
- 限流电阻不能省。LED 正向压降约 2 V，引脚 3.3 V 输出、串 1 kΩ 时电流约 1.3 mA，足够看清亮灭又不会超过引脚的 8 mA 推荐电流；直接接会过流。
- 阳极接引脚、阴极接 GND 是**高电平点亮**：写 `GPIO_PIN_SET` 亮，写 `GPIO_PIN_RESET` 灭。

两种接法下写值与现象的关系必须分清：

| 接法 | 点亮 | 熄灭 |
| --- | --- | --- |
| 高电平点亮（引脚 → 电阻 → LED 阳极，阴极接 GND） | `GPIO_PIN_SET` | `GPIO_PIN_RESET` |
| 低电平点亮（LED 阳极接 VDD，阴极接引脚，如板载 `PC13`） | `GPIO_PIN_RESET` | `GPIO_PIN_SET` |

命令语义只表示“开灯/关灯”，不表示写什么电平。下面 `LED_ApplyAsciiCommand()` 的 `state` 按高电平点亮计算（`'1'` → `GPIO_PIN_SET`），若开发板是低电平点亮，**只在这一个函数里把 `GPIO_PIN_SET` 和 `GPIO_PIN_RESET` 互换**，协议含义不变。

```c
static void LED_ApplyAsciiCommand(const uint8_t command[2])
{
    GPIO_PinState state;

    if (command[1] == (uint8_t)'0')
    {
        state = GPIO_PIN_RESET;
    }
    else if (command[1] == (uint8_t)'1')
    {
        state = GPIO_PIN_SET;
    }
    else
    {
        return;
    }

    switch (command[0])
    {
        case (uint8_t)'R':
            HAL_GPIO_WritePin(RED_LED_GPIO_Port, RED_LED_Pin, state);
            break;

        case (uint8_t)'G':
            HAL_GPIO_WritePin(GREEN_LED_GPIO_Port, GREEN_LED_Pin, state);
            break;

        case (uint8_t)'B':
            HAL_GPIO_WritePin(BLUE_LED_GPIO_Port, BLUE_LED_Pin, state);
            break;

        default:
            break;
    }
}
```

### 6.2.1 只有最小系统板时的降级方案

如果手上只有最小系统板（只有板载 `PC13` 那颗低电平点亮的 LED，没有外接三色灯），不必额外接线，把三个逻辑灯都映射到 `PC13` 即可：`RED_LED`、`GREEN_LED`、`BLUE_LED` 都当成同一个灯，直接用 `GPIOC` 与 `GPIO_PIN_13`，连 User Label 都不需要。

```c
/* 最小系统板降级版：三个逻辑灯都映射到板载 PC13（低电平点亮）。 */
static void LED_ApplyAsciiCommand(const uint8_t command[2])
{
    if (command[1] == (uint8_t)'1')
    {
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET); /* 低电平点亮 */
    }
    else if (command[1] == (uint8_t)'0')
    {
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);   /* 高电平熄灭 */
    }
    else
    {
        return;
    }

    /* 单灯方案不区分 command[0]：发 R1、G1、B1 都点亮同一个灯。 */
}
```

`PC13` 按第 01 章配置为输出（`Output Open Drain`，初始电平 `High`）。这个版本能验证的只有三条：发 `R1` 灯亮、发 `R0` 灯灭、两种情况都能收到原样回显。链路本身（引脚、波特率、收发、命令解析）已经被完整验证，三色灯只是额外把 `command[0]` 区分开而已。

轮询接收、回显和执行命令：

```c
static uint8_t rx_polling[2];

while (1)
{
    if (HAL_UART_Receive(&huart2,
                         rx_polling,
                         (uint16_t)sizeof(rx_polling),
                         HAL_MAX_DELAY) == HAL_OK)
    {
        LED_ApplyAsciiCommand(rx_polling);

        HAL_UART_Transmit(&huart2,
                          rx_polling,
                          (uint16_t)sizeof(rx_polling),
                          100U);
    }
}
```

这个程序只有收满 2 字节后才返回。若只发送一个字节，`HAL_UART_Receive()` 会继续等待第二个字节；这正是“定长接收”的含义。

### 6.3 实验验收

1. 串口助手设置为 115200、8N1；
2. 文本模式发送 `R1`，红灯点亮并收到 `R1` 回显；
3. 发送 `B1`，蓝灯点亮；
4. 发送 `B0`，蓝灯熄灭；
5. 把串口助手波特率故意改错，观察乱码；
6. 切换 HEX 显示，观察 `R1` 对应 `52 31`。

只有最小系统板（用了 6.2.1 节降级方案）时，把验收条件替换成三条：发 `R1` 板载灯亮、发 `R0` 板载灯灭、两次都能收到原样回显；发 `G1`、`B1` 也点亮同一个灯，属于预期现象，不是接线错误。第 5、6 条（改错波特率看乱码、HEX 对照）在最小板上同样可以做。

## 7. 实验二：中断模式定长接收

### 7.1 非阻塞启动与完成回调

`HAL_UART_Receive_IT()` 只负责启动一次接收，然后立即返回。HAL 在每个 `RXNE` 事件中搬运一个字节；收满指定长度后，才调用：

```c
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart);
```

完整调用链为：

```text
RX 收到字节
-> USART2_IRQHandler
-> HAL_UART_IRQHandler
-> HAL 内部读取 USART_DR
-> 收满指定数量
-> HAL_UART_RxCpltCallback
```

### 7.2 为什么不能在 while 中反复启动

错误写法是每次循环都调用：

```c
HAL_UART_Receive_IT(&huart2, rx_it_buf, 2U);
```

上一次接收尚未结束时，UART 句柄仍处于 Busy 状态，下一次调用会返回 `HAL_BUSY`。正确模型是：

```text
启动一次
-> 等待回调
-> 主循环处理
-> 再启动下一次
```

### 7.3 最小完整代码

在用户变量区定义：

```c
static uint8_t rx_it_buf[2];
static volatile uint8_t rx_it_ready = 0U;
```

初始化完成后、进入主循环前启动一次：

```c
if (HAL_UART_Receive_IT(&huart2,
                        rx_it_buf,
                        (uint16_t)sizeof(rx_it_buf)) != HAL_OK)
{
    /* Busy 通常表示上一次接收尚未完成。 */
    Error_Handler();
}
```

回调中只交接事件，不执行耗时解析或阻塞发送：

```c
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        rx_it_ready = 1U;
    }
}
```

> **实验之间是替换关系。** `HAL_UART_RxCpltCallback()` 是 HAL 声明的全局弱函数，一个工程里只能保留一个强定义：把本节和 8.3 节的两份回调同时留在 `main.c` 里会直接编译报重定义。做本节实验时，请用这里的回调与主循环替换掉 6.1、6.2 节的版本，`while (1)` 也只保留一个。

主循环中处理并重新启动：

```c
while (1)
{
    if (rx_it_ready != 0U)
    {
        LED_ApplyAsciiCommand(rx_it_buf);

        HAL_UART_Transmit(&huart2,
                          rx_it_buf,
                          (uint16_t)sizeof(rx_it_buf),
                          100U);

        rx_it_ready = 0U;

        if (HAL_UART_Receive_IT(&huart2,
                                rx_it_buf,
                                (uint16_t)sizeof(rx_it_buf)) != HAL_OK)
        {
            Error_Handler();
        }
    }

    /* 这里可以继续执行按键、传感器、显示等其他任务。 */
}
```

这个单缓冲区模型在回调后暂不重启接收，因此主循环处理期间不会被新数据覆盖，适合命令间隔较大的入门实验。代价是处理期间到达的新字节无法接收；高吞吐场景需要双缓冲或环形缓冲区。

### 7.4 为什么第二次命令没有反应

`HAL_UART_Receive_IT()` 默认只完成一轮规定长度的接收。若只在初始化时启动一次，却没有在处理完成后重新启动，第一次命令正常，后续命令就不会再进入缓冲区。

修复重点不是把启动函数塞回 `while` 顶部，而是在“上一轮已完成且缓冲区已处理”之后重新启动。

### 7.5 实验验收

1. 把 `static uint8_t rx_it_buf[2];` 改成 `static uint8_t rx_it_buf[5];`（两处 `sizeof(rx_it_buf)` 会自动跟着变成 5，不必再改别的）；
2. 串口助手**一次发送 5 个字节**（例如 `RB01X`），回调应立即触发，主循环把 5 个字节原样回显；
3. 判别点：这是“收满 5 字节就回调”，与 8.3 节 `HAL_UART_Receive_DMA(&huart2, rx_dma_fixed, 64U)` 的“必须凑满 64 字节才回调一次”正好形成对照——同样发 5 字节，后者毫无反应，这里立刻有回显；
4. 把长度改回 2，发 `R1` 应立即回显，说明回调时机由 `HAL_UART_Receive_IT()` 的长度参数决定，与发送端一次发多少字节无关。

## 8. 实验三：DMA 定长收发

### 8.1 DMA 减少了哪部分 CPU 工作

中断接收时，每到一个字节都会因 `RXNE` 进入 UART 中断，HAL 再由 CPU 把 `USART_DR` 中的数据写入数组。DMA 接收开启后，数据链变为：

```text
RXNE 事件
-> USART 产生 DMA 请求
-> DMA1 Channel 6 读取 USART2_DR
-> 写入 rx_dma_fixed[]
-> 传输数量减 1
```

发送方向则是：

```text
TXE 事件
-> USART 产生 DMA 请求
-> DMA1 Channel 7 从 tx_buffer[] 取一个字节
-> 写入 USART2_DR
```

CPU 不再为每个字节进入 UART 中断，只在 DMA 半传输、传输完成或错误等事件时介入。DMA 并没有消除 USART 的 TXE/RXNE 硬件事件，而是让这些事件请求 DMA 搬运数据。

### 8.2 HAL 接口

定长 DMA 发送：

```c
HAL_UART_Transmit_DMA(&huart2, tx_buffer, tx_length);
```

定长 DMA 接收：

```c
HAL_UART_Receive_DMA(&huart2, rx_buffer, rx_length);
```

对应的完成回调仍然是：

```c
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart);
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart);
```

但此时接收完成事件来自 DMA 通道，而不是 CPU 逐字节搬运完成。

### 8.3 定长 2 字节接收示例

变量：

```c
static uint8_t rx_dma_fixed[2];
static volatile uint8_t rx_dma_fixed_ready = 0U;
static uint8_t tx_dma_fixed[2];
static volatile uint8_t tx_dma_fixed_busy = 0U;
```

初始化后启动一次：

```c
if (HAL_UART_Receive_DMA(&huart2,
                         rx_dma_fixed,
                         (uint16_t)sizeof(rx_dma_fixed)) != HAL_OK)
{
    Error_Handler();
}
```

回调交接事件：

```c
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        rx_dma_fixed_ready = 1U;
    }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        tx_dma_fixed_busy = 0U;
    }
}
```

> **实验之间是替换关系。** 这里的 `HAL_UART_RxCpltCallback()` 与 7.3 节的那一份同名，一个工程里只能保留一个强定义：做本节实验时，把 7.3 节的回调换成本节的版本（本节的回调同时服务定长 DMA 接收），`while (1)` 也只保留本节的版本。

主循环处理并重启：

```c
if (rx_dma_fixed_ready != 0U)
{
    LED_ApplyAsciiCommand(rx_dma_fixed);

    if (tx_dma_fixed_busy == 0U)
    {
        tx_dma_fixed[0] = rx_dma_fixed[0];
        tx_dma_fixed[1] = rx_dma_fixed[1];
        tx_dma_fixed_busy = 1U;

        if (HAL_UART_Transmit_DMA(&huart2,
                                  tx_dma_fixed,
                                  (uint16_t)sizeof(tx_dma_fixed)) != HAL_OK)
        {
            tx_dma_fixed_busy = 0U;
        }
    }

    rx_dma_fixed_ready = 0U;

    if (HAL_UART_Receive_DMA(&huart2,
                             rx_dma_fixed,
                             (uint16_t)sizeof(rx_dma_fixed)) != HAL_OK)
    {
        Error_Handler();
    }
}
```

这个示例使用独立的 RX/TX 数组。`HAL_UART_Transmit_DMA()` 返回 `HAL_OK` 后，发送缓冲区在 `HAL_UART_TxCpltCallback()` 之前必须保持不变；不能把已经重新交给 RX DMA 的数组同时作为仍在发送的 TX 缓冲区。

### 8.4 定长 DMA 仍然不能自动判断包长

`HAL_UART_Receive_DMA(&huart2, buffer, 64U)` 的含义是“接收满 64 个数据元素后完成”，不是“最多接收 64 字节并自动识别实际长度”。若发送端只发 7 字节，普通定长 DMA 会继续等待剩余 57 字节。

要在少于缓冲区容量时结束本轮接收，需要额外的边界事件。UART 的 IDLE 空闲线检测正是常用方案。

### 8.5 实验验收

1. 保持本节代码的 2 字节配置，发送 `R1` 应看到 LED 动作与原样回显；
2. 把长度改成 64：`static uint8_t rx_dma_fixed[64];`、`static uint8_t tx_dma_fixed[64];`，两处 `sizeof` 会自动跟着变；同时把回显部分的两行赋值改成整段复制（`memcpy(tx_dma_fixed, rx_dma_fixed, sizeof(rx_dma_fixed));`，需要包含 `string.h`）。**此时必须一次发满 64 字节才会进入一次 `HAL_UART_RxCpltCallback()`**；
3. 只发 5 个字节时 LED 不动、也没有回显，**这是预期行为**：定长 DMA 只负责搬满指定数量，自己给不出“实际收到多少”这个信息（这也正是 9.1 节要引入 IDLE 的原因）；
4. 不要用“发 5 字节没反应”判定 DMA 坏了：先用串口助手一次发满 64 字节确认链路正常，再对照第 3 条理解现象。

## 9. 实验四：DMA 与 IDLE 接收不定长数据

### 9.1 IDLE 能告诉我们什么

参考手册规定：USART 接收过数据后，如果检测到一个完整的空闲帧，`IDLE` 标志置位；使能 `IDLEIE` 后会产生 UART 中断。

较新的 STM32CubeF1 HAL 将这个机制封装为：

```c
HAL_UARTEx_ReceiveToIdle_DMA(&huart2, rx_buffer, max_size);
```

如果所用旧版 HAL 没有 `HAL_UARTEx_ReceiveToIdle_DMA()` 或 `HAL_UARTEx_RxEventCallback()`，应改用“DMA 接收 + USART IDLE 中断”手动处理，或升级到包含该扩展接口的 CubeF1 软件包；不要直接复制本节代码后忽略编译器报错。

自己核对的办法：打开工程里的 `Drivers/STM32F1xx_HAL_Driver/Inc/stm32f1xx_hal_uart_ex.h`，搜索 `HAL_UARTEx_ReceiveToIdle_DMA`。能看到声明，说明当前 HAL 版本支持本节写法；搜索不到，就说明 CubeF1 固件包过旧，需要在 CubeMX 的 `Help -> Manage embedded software packages` 里升级 STM32Cube MCU Package for STM32F1，再重新生成工程。

它的含义是：

> 启动 DMA 接收，直到缓冲区收满，或在未收满前检测到 IDLE 事件。

使用它之前，CubeMX 的 NVIC 里**必须同时打开两个中断，缺一不可**：

| NVIC 条目 | 负责的事件 | 不开会怎样 |
| --- | --- | --- |
| `DMA1 Channel 6 global interrupt` | 缓冲区收满（TC） | 收满也不会回调 |
| `USART2 global interrupt` | IDLE 空闲线、ORE/FE/NE/PE 错误 | 短数据（没填满缓冲区）永远没有回调 |

`HAL_UARTEx_ReceiveToIdle_DMA()` 内部只会自动置位 `IDLEIE`，IDLE 事件本身仍然在 `USART2_IRQHandler()` → `HAL_UART_IRQHandler()` 里被识别并调用回调，所以只开 DMA 通道中断是不够的。这也是 5.4 节强调要同时打开两处 NVIC 的原因。

第三个参数是本轮最多能放入缓冲区的数据元素数，不是已知的数据包长度。回调参数 `Size` 才表示当前缓冲区中已有多少个有效数据元素。

本章使用 DMA Normal 模式，因此 `Size` 可以直接作为本轮有效长度。Circular 模式下，`Size` 更接近“DMA 当前写到缓冲区的哪个位置”，应用要与上一次位置比较并处理回绕，不能每次都把 `buffer[0..Size-1]` 当成一批全新的数据。

### 9.2 IDLE 不是协议包头

IDLE 是时间边界，不是内容边界。把一次 IDLE 回调直接当成一个完整数据包，只在以下前提下可靠：

- 发送端连续发送一帧，中间没有过长停顿；
- 两帧之间存在至少一个可检测的空闲间隔；
- 接收处理速度足够，下一帧不会在重新启动前到达。

下面两种情况都会破坏“一次回调等于一个包”的假设：

1. 一个数据包内部字节间隔过长，可能被拆成两次 IDLE 事件；
2. 两个数据包背靠背发送且中间没有空闲，可能在一次回调中一起到达。

因此，IDLE 适合把连续字节流切成“本次收到的一段数据”，真正的包边界仍应由包头、长度或结束符确定。

### 9.3 RxEvent 回调可能由三类事件触发

STM32CubeF1 HAL 的 `HAL_UARTEx_RxEventCallback()` 在 DMA 模式下可能由以下事件触发：

| 事件 | 含义 | Normal 模式是否结束接收 |
| --- | --- | --- |
| `HAL_UART_RXEVENT_HT` | 缓冲区接收一半 | 否 |
| `HAL_UART_RXEVENT_TC` | 缓冲区接收满 | 是 |
| `HAL_UART_RXEVENT_IDLE` | 未收满时检测到空闲线 | 是 |

可在回调中查询：

```c
HAL_UART_RxEventTypeTypeDef event_type;

event_type = HAL_UARTEx_GetRxEventType(huart);
```

事件类型应在 `HAL_UARTEx_RxEventCallback()` 内读取，此时句柄中保存的是本次回调对应的准确事件。

本实验只希望“空闲或缓冲区满时处理一段数据”，因此可以关闭 DMA 半传输中断：

```c
__HAL_DMA_DISABLE_IT(huart2.hdmarx, DMA_IT_HT);
```

关闭 HT 后，缓冲区收满仍会通过 TC 触发回调。不能只判断“进入了 `HAL_UARTEx_RxEventCallback()`”就断言一定发生了 IDLE。

### 9.4 每次重新启动后都要关闭 HT

`HAL_UARTEx_ReceiveToIdle_DMA()` 内部重新启动 DMA 时，会重新配置 DMA 中断。若应用不需要半传输事件，应在每一次成功启动后立即关闭 HT：

```c
#define UART2_RX_BUFFER_SIZE 64U

static uint8_t uart2_rx_buffer[UART2_RX_BUFFER_SIZE];
static volatile uint16_t uart2_rx_length = 0U;
static volatile uint8_t uart2_rx_ready = 0U;
static volatile uint8_t uart2_rx_error = 0U;   /* 由 9.7 节的错误回调置位 */

static HAL_StatusTypeDef UART2_StartReceiveToIdle(void)
{
    HAL_StatusTypeDef status;

    status = HAL_UARTEx_ReceiveToIdle_DMA(&huart2,
                                          uart2_rx_buffer,
                                          (uint16_t)sizeof(uart2_rx_buffer));

    if (status == HAL_OK)
    {
        /* 本示例只处理 IDLE/TC，关闭 HT 可避免半帧回调。 */
        __HAL_DMA_DISABLE_IT(huart2.hdmarx, DMA_IT_HT);
    }

    return status;
}
```

初始化后调用：

```c
if (UART2_StartReceiveToIdle() != HAL_OK)
{
    Error_Handler();
}
```

### 9.5 回调只交接长度

```c
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    if (huart->Instance == USART2)
    {
        if ((Size > 0U) &&
            (Size <= (uint16_t)sizeof(uart2_rx_buffer)) &&
            (uart2_rx_ready == 0U))
        {
            uart2_rx_length = Size;
            uart2_rx_ready = 1U;
        }
    }
}
```

本例使用 DMA Normal 模式。IDLE 或 TC 结束本轮接收后，DMA 不再改写数组，因此主循环可以安全读取当前缓冲区。回调中不立即重启，是为了避免主循环解析时 DMA 覆盖同一数组。

### 9.6 主循环处理、回显并重新启动

```c
while (1)
{
    if (uart2_rx_ready != 0U)
    {
        uint16_t length = uart2_rx_length;

        /* 在这里解析 uart2_rx_buffer[0..length-1]。 */

        HAL_UART_Transmit(&huart2,
                          uart2_rx_buffer,
                          length,
                          100U);

        uart2_rx_length = 0U;
        uart2_rx_ready = 0U;

        if (UART2_StartReceiveToIdle() != HAL_OK)
        {
            Error_Handler();
        }
    }

    /* 错误分支：uart2_rx_error 由 9.7 节的 ErrorCallback 置位。 */
    if (uart2_rx_error != 0U)
    {
        uart2_rx_error = 0U;

        /* 出错时本轮收到的数据已不可信，长度和就绪标志一并清掉。 */
        uart2_rx_length = 0U;
        uart2_rx_ready = 0U;

        UART2_RecoverFromRxError();
    }

    /* 执行其他非阻塞任务。 */
}
```

这个入门结构的时序为：

```text
Start ReceiveToIdle DMA
-> IDLE 或 TC
-> 回调记录 Size
-> 主循环处理稳定缓冲区
-> 重新 Start
```

它优先保证“当前包不被覆盖”，适合低频命令。处理期间 USART 没有处于接收状态，新到字节可能丢失。若发送端不能等待，应在回调中快速复制到另一个处理缓冲区后立即重启，或使用 Circular DMA 加环形缓冲区。

### 9.7 错误恢复

噪声、帧错误或溢出会让 HAL 进入 `HAL_UART_ErrorCallback()`（用 `HAL_UART_GetError()` 可以查到具体是 `HAL_UART_ERROR_ORE / FE / NE / PE`）。这里有一个容易忽略的后果：**HAL 在报告错误的同时会中止当前接收，并把句柄状态置回 Ready。** DMA 通道已经停止，缓冲区不会再有新数据进来，此时如果应用不重新启动接收，串口就“死”了。最典型的现场是：

> 第一次上电收发都正常，拔插一次 USB 转 TTL（或蓝牙模块上电的瞬间）之后就再也收不到任何数据，必须按复位键才恢复。

之所以发生在拔插或模块上电瞬间，是因为这类动作会在 RX 线上产生一段电平跳变，被 USART 采样成噪声或帧错误，触发一次接收中止。

最小实验先记录错误标志：

```c
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        uart2_rx_error = 1U;
    }
}
```

`uart2_rx_error` 已在 9.4 节与接收缓冲区一起声明。回调里只置标志，中止和重启都放到主循环做（中断里不做长操作）：

关于放置位置：CubeMX 生成 `main.c` 时，`/* USER CODE BEGIN 4 */` 区在 `main()` 之后。`UART2_RecoverFromRxError()`（以及 9.4 节的 `UART2_StartReceiveToIdle()`）要在 `main()` 之前有原型，否则按 C99 会报“隐式声明函数”。做法是在文件上方 `/* USER CODE BEGIN PFP */` 区补上：

```c
static void UART2_RecoverFromRxError(void);
static HAL_StatusTypeDef UART2_StartReceiveToIdle(void);
```

函数体写在 `/* USER CODE BEGIN 4 */` 区即可。

```c
/* 错误后重新启动接收：必须先中止再启动，否则句柄仍是 Busy。 */
static void UART2_RecoverFromRxError(void)
{
    /* 读 SR、读 DR 清标志的动作已由 HAL_UART_IRQHandler() 完成，
       这里只负责停止当前接收并把句柄状态恢复成 Ready。 */
    if (HAL_UART_AbortReceive(&huart2) != HAL_OK)
    {
        /* Abort 失败说明状态异常，退回更彻底的停止方式。
           个别旧版本 HAL 没有 HAL_UART_AbortReceive()，可直接用这一句。 */
        (void)HAL_UART_DMAStop(&huart2);
    }

    if (UART2_StartReceiveToIdle() != HAL_OK)
    {
        Error_Handler();
    }
}
```

顺序不能颠倒：先 `HAL_UART_AbortReceive()`（或 `HAL_UART_DMAStop()`）结束这一轮接收，再调用 `UART2_StartReceiveToIdle()`；在句柄仍是 Busy 时直接重启会返回 `HAL_BUSY`。正式工程还应把 `HAL_UART_GetError()` 的返回值分类记录（ORE 多为接收不及时，FE/NE 多为电平或线路问题），而不是无限重启后掩盖线路问题。

### 9.8 实验验收

1. 串口助手发送任意长度（1 字节、5 字节、13 字节都可以），**都应立即触发 `HAL_UARTEx_RxEventCallback()` 并原样回显**，回调参数 `Size` 等于本次实际收到的字节数；
2. 判别点：同样的 5 个字节，8.3 节的定长 DMA 毫无反应，这里立即回调——这正是“IDLE 给出时间边界”的价值；
3. 若发 5 个字节完全没有回调，而把 `uart2_rx_buffer` 长度改成 5 后又能收到数据，说明 NVIC 里只开了 DMA 通道中断、**没开 `USART2 global interrupt`**：IDLE 事件在 `USART2_IRQHandler()` 里处理，全局中断没开就只有缓冲区填满时（TC 由 DMA 通道中断触发）才会回调一次。这是本章最容易踩的配置陷阱，见 5.4、9.1 和 14.4；
4. 想同时验证错误恢复，可在程序运行中拔插一次 USB 转 TTL 的 RX 线，观察是否在不动复位键的情况下继续回显；若此后永久无数据，就是 9.7 节的恢复代码没有生效。

## 10. 实验五：使用蓝牙串口透传模块

### 10.1 透传模块把复杂协议隐藏在模块内部

蓝牙协议栈包含广播、扫描、连接、服务和特征等多层机制。串口透传模块已经在模块内部实现这些协议，对 STM32 暴露一个普通 UART：

```text
手机或电脑
<-> 蓝牙无线链路
<-> 蓝牙透传模块
<-> UART TX/RX
<-> STM32 USART3
```

手机发送的字节由模块转发给 STM32；STM32 从 USART3 发出的字节再由模块转发给已连接的主机。对主程序而言，蓝牙只是“换了一段传输介质”，缓冲区和数据包解析方法与有线串口相同。

经典蓝牙和 BLE 是不同技术分支。具体模块采用哪一种、主从角色如何命名、使用何种服务和特征，应以模块说明书为准。本章以课程使用的 BT24 透传模块为例演示，不把模块行为推广到所有蓝牙模块。

### 10.2 硬件连接

课程板将 USART3 默认引脚引出：

```text
STM32 PB10 / USART3_TX -> 模块 RX
STM32 PB11 / USART3_RX <- 模块 TX
STM32 GND              -> 模块 GND
模块 VCC               -> 按模块板标注供电
```

连接前检查：

- TX 与 RX 是否交叉；
- GND 是否共地；
- 模块 VCC 是否允许 5 V；
- 模块 UART IO 是否与 3.3 V 逻辑兼容；
- 插头线序是否与丝印一致。

不要因为模块电源端写着 5 V，就把 5 V 连接到 STM32 的 TX/RX。

### 10.3 CubeMX 配置

1. 将 USART3 配置为 `Asynchronous`；
2. 按模块说明书或 AT 指令查询确认模块当前波特率，再填入 CubeMX（BT24 的常见默认值是 `9600, 8N1`）；
3. 确认默认引脚为 PB10/TX、PB11/RX；
4. 开启 `USART3 global interrupt`；
5. 添加 USART3_RX DMA1 Channel 3；
6. 如需 DMA 发送，再添加 USART3_TX DMA1 Channel 2；
7. RX 使用 Byte、外设地址固定、内存地址递增、Normal 模式；
8. 生成代码并检查 DMA IRQ 和 `USART3_IRQHandler()`。

第 3 步还有一个必须处理的坑：`PB10/PB11` 和第 02 章 OLED 的 `I2C2` 是同一组引脚，而 LQFP48 没有引出 `PC0~PC12`，`USART3` 无法用重映射绕开（详见 3.2 节）。所以**本次实验的工程里不要再启用第 02 章的 `I2C2`**：两者二选一，或者把 OLED 换成第 09 章 `PB8/PB9` 的软件 I2C 方案。如果 CubeMX 里同时启用，会在引脚图上直接报黄色冲突，生成的代码也会让 OLED 和蓝牙都工作不正常。

第 4 步和第 5 步都要勾：和 USART2 的 ReceiveToIdle 一样，`ReceiveToIdle` 同时需要 DMA 通道中断（缓冲区收满）和 `USART3 global interrupt`（IDLE 与错误），只开一个会出现“短数据没有回调”。

模块的默认波特率可能被 AT 指令修改过。若透传无响应，应先确认模块当前参数，而不是只反复修改 MCU 代码。

### 10.4 先做回显实验

先不要急着解析指令。把 USART3 的接收流程改成与 USART2 相同的 ReceiveToIdle DMA，在主循环中把收到的数据原样发回 USART3。

验收顺序：

1. 主机扫描并连接模块；
2. 发送短文本，确认原样返回；
3. 发送较长文本，确认 `Size` 与返回长度一致；
4. 切换 HEX 模式发送二进制数据；
5. 确认断开电脑后，手机也能完成同样回显。

开始回显之前，先确认“模块在线且波特率一致”：按模块说明书进入 AT 配置状态（常见做法是发 `AT`，模块回 `OK`，具体指令和是否需要换行以模块文档为准）。模块波特率和 MCU 的 `USART3` 不一致时，`AT` 不会有任何回复，而这个现象与“接线错误”“收发器坏了”完全一样；先排掉它，后面就不用反复怀疑 MCU 代码。

只有“无线链路 -> 模块 -> USART3 -> DMA -> 缓冲区 -> 回发”完整连通后，再加入协议解析。否则协议代码会掩盖硬件和连接问题。

### 10.5 USART3 接收变量与统一回调

USART3 的接收结构与 USART2 相同：

```c
#define UART3_RX_BUFFER_SIZE 64U

static uint8_t uart3_rx_buffer[UART3_RX_BUFFER_SIZE];
static volatile uint16_t uart3_rx_length = 0U;
static volatile uint8_t uart3_rx_ready = 0U;

static HAL_StatusTypeDef UART3_StartReceiveToIdle(void)
{
    HAL_StatusTypeDef status;

    status = HAL_UARTEx_ReceiveToIdle_DMA(&huart3,
                                          uart3_rx_buffer,
                                          (uint16_t)sizeof(uart3_rx_buffer));

    if (status == HAL_OK)
    {
        __HAL_DMA_DISABLE_IT(huart3.hdmarx, DMA_IT_HT);
    }

    return status;
}
```

一个工程只能保留一个同名全局 HAL 弱回调强定义。若 USART2 和 USART3 同时使用 ReceiveToIdle，应在同一个回调中按实例分流，而不是在两个 `.c` 文件中各定义一次：

```c
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    if (huart->Instance == USART2)
    {
        if ((Size > 0U) &&
            (Size <= (uint16_t)sizeof(uart2_rx_buffer)) &&
            (uart2_rx_ready == 0U))
        {
            uart2_rx_length = Size;
            uart2_rx_ready = 1U;
        }
    }
    else if (huart->Instance == USART3)
    {
        if ((Size > 0U) &&
            (Size <= (uint16_t)sizeof(uart3_rx_buffer)) &&
            (uart3_rx_ready == 0U))
        {
            uart3_rx_length = Size;
            uart3_rx_ready = 1U;
        }
    }
}
```

若工程只使用 USART3，保留 USART3 分支即可。初始化完成后调用一次 `UART3_StartReceiveToIdle()`，主循环处理完当前缓冲区后再重新启动。

## 11. 设计一个简易 LED 控制数据包

### 11.1 为什么两个字节还不够

`R1` 适合人工输入，但扩展性和抗干扰能力有限：

- 不容易在任意字节流中找到命令起点；
- 无法表示一包中有多少条命令；
- 数据出错时缺少检验手段；
- 二进制传感器值不适合全部编码成字符。

因此定义一个简单二进制帧：

| 字节位置 | 字段 | 含义 |
| ---: | --- | --- |
| 0 | Header | 固定 `0xAA` |
| 1 | Length | 整包总字节数，包含包头、长度和校验和 |
| 2...N-2 | Payload | 每两个字节为一组 `[LED_ID, STATE]` |
| N-1 | Checksum | 前面所有字节累加后取低 8 位 |

LED 命令定义：

| LED_ID | LED |
| ---: | --- |
| `0x01` | 红灯 |
| `0x02` | 绿灯 |
| `0x03` | 蓝灯 |

状态定义：

| STATE | 动作 |
| ---: | --- |
| `0x00` | 关闭 |
| `0xFF` | 打开 |

### 11.2 校验和

若整包长度为 `N`，最后一字节存放校验和，则：

$$
\text{checksum}
=
\left(
\sum_{i=0}^{N-2}\text{packet}[i]
\right)\bmod 256
$$

C 语言中把累加结果转换为 `uint8_t`，即可保留低 8 位：

```c
static uint8_t Packet_Checksum8(const uint8_t *data, uint16_t length)
{
    uint16_t sum = 0U;
    uint16_t i;

    for (i = 0U; i < length; ++i)
    {
        sum = (uint16_t)(sum + data[i]);
    }

    return (uint8_t)sum;
}
```

简单累加和能发现许多单字节错误，但不能检测所有错误，例如某个字节增加 1、另一个字节同时减少 1，结果可能不变。需要更强检错能力时应使用 CRC，并根据协议增加序号、确认和重传机制。

### 11.3 示例一：打开红灯

待发送字段：

```text
AA 05 01 FF ??
```

校验和：

$$
0xAA+0x05+0x01+0xFF=0x1AF
$$

取低 8 位得到 `0xAF`，完整帧为：

```text
AA 05 01 FF AF
```

### 11.4 示例二：关闭红灯并打开绿灯

字段：

```text
AA 07 01 00 02 FF ??
```

校验和：

$$
0xAA+0x07+0x01+0x00+0x02+0xFF=0x1B3
$$

完整帧为：

```text
AA 07 01 00 02 FF B3
```

这里 `Length=0x07` 表示整包共 7 字节，不是 Payload 长度。协议双方必须对长度字段的口径保持一致。

### 11.5 先完整验证，再执行动作

解析时应按以下顺序检查：

1. 实际长度至少为 5；
2. 实际长度不超过协议和缓冲区上限；
3. 第 0 字节为 `0xAA`；
4. Length 字段等于实际接收长度；
5. Payload 长度为偶数，能完整组成命令对；
6. 校验和正确；
7. 所有 LED_ID 和 STATE 均合法；
8. 全部检查通过后，再统一执行 GPIO 动作。

不能边检查边控制 LED。若第一组命令已经执行，后来才发现第二组非法或校验和错误，设备会进入“半包生效”的不一致状态。

### 11.6 完整解析函数

```c
typedef enum
{
    PACKET_OK = 0,
    PACKET_ERROR_LENGTH,
    PACKET_ERROR_HEADER,
    PACKET_ERROR_PAYLOAD,
    PACKET_ERROR_CHECKSUM,
    PACKET_ERROR_COMMAND
} PacketStatus;

static uint8_t LED_CommandIsValid(uint8_t led_id, uint8_t state)
{
    uint8_t led_valid;
    uint8_t state_valid;

    led_valid = (uint8_t)((led_id >= 0x01U) && (led_id <= 0x03U));
    state_valid = (uint8_t)((state == 0x00U) || (state == 0xFFU));

    return (uint8_t)(led_valid && state_valid);
}

static void LED_ApplyBinaryCommand(uint8_t led_id, uint8_t state)
{
    GPIO_PinState pin_state;

    pin_state = (state == 0xFFU) ? GPIO_PIN_SET : GPIO_PIN_RESET;

    switch (led_id)
    {
        case 0x01U:
            HAL_GPIO_WritePin(RED_LED_GPIO_Port, RED_LED_Pin, pin_state);
            break;

        case 0x02U:
            HAL_GPIO_WritePin(GREEN_LED_GPIO_Port, GREEN_LED_Pin, pin_state);
            break;

        case 0x03U:
            HAL_GPIO_WritePin(BLUE_LED_GPIO_Port, BLUE_LED_Pin, pin_state);
            break;

        default:
            break;
    }
}

static PacketStatus Packet_ProcessLedCommand(const uint8_t *packet,
                                             uint16_t size)
{
    uint16_t payload_length;
    uint16_t i;

    if ((packet == NULL) || (size < 5U) || (size > 255U))
    {
        return PACKET_ERROR_LENGTH;
    }

    if (packet[0] != 0xAAU)
    {
        return PACKET_ERROR_HEADER;
    }

    if (packet[1] != (uint8_t)size)
    {
        return PACKET_ERROR_LENGTH;
    }

    payload_length = (uint16_t)(size - 3U);
    if ((payload_length == 0U) || ((payload_length % 2U) != 0U))
    {
        return PACKET_ERROR_PAYLOAD;
    }

    if (Packet_Checksum8(packet, (uint16_t)(size - 1U)) != packet[size - 1U])
    {
        return PACKET_ERROR_CHECKSUM;
    }

    for (i = 2U; i < (uint16_t)(size - 1U); i += 2U)
    {
        if (LED_CommandIsValid(packet[i], packet[i + 1U]) == 0U)
        {
            return PACKET_ERROR_COMMAND;
        }
    }

    for (i = 2U; i < (uint16_t)(size - 1U); i += 2U)
    {
        LED_ApplyBinaryCommand(packet[i], packet[i + 1U]);
    }

    return PACKET_OK;
}
```

若开发板 LED 为低电平点亮，只需在 `LED_ApplyBinaryCommand()` 中反转 `pin_state`，不要改协议中 `0x00/0xFF` 的含义。若用的是 6.2.1 节的单灯降级方案，把三个 `case` 里的写引脚都换成 `GPIOC` 与 `GPIO_PIN_13` 即可（低电平点亮，`pin_state` 同样要反转），包格式和命令表不受影响。

### 11.7 在主循环中解析蓝牙数据

USART3 的回调只记录 `Size`，主循环再调用解析函数：

```c
if (uart3_rx_ready != 0U)
{
    uint16_t packet_size = uart3_rx_length;
    PacketStatus status;

    status = Packet_ProcessLedCommand(uart3_rx_buffer, packet_size);

    if (status == PACKET_OK)
    {
        /* 入门实验先原包回显，证明接收、解析和发送链路均正常。 */
        HAL_UART_Transmit(&huart3,
                          uart3_rx_buffer,
                          packet_size,
                          100U);
    }

    uart3_rx_length = 0U;
    uart3_rx_ready = 0U;

    if (UART3_StartReceiveToIdle() != HAL_OK)
    {
        Error_Handler();
    }
}
```

这里使用阻塞发送并在发送后才重新启动 RX DMA，因此回显期间接收缓冲区保持稳定。正式协议若需要 ACK，应明确规定消息类型、状态码、序号和校验方式，不能临时混用文本 `OK` 与二进制控制帧。

**这个写法的边界**：它把“一次回调收到的字节”当成“一个完整包”，只在人工逐条发送时成立。把 `AA 05 01 FF AF` 和 `AA 05 03 00 B2` 连着发出去，两个包会在一次回调里一起到达，`Size` 是 10 而 `packet[1]` 是 `0x05`，`Packet_ProcessLedCommand()` 会因为 `packet[1] != size` 返回 `PACKET_ERROR_LENGTH`，**两包一起被丢弃**；反过来，一个包被拆成两次回调时前一半同样会失败。这不是实现细节，而是本模型的固有限制，见下一节的处理办法。

### 11.8 连发两包为什么不丢：最小流式解析

要同时处理“拆包”和“粘包”，必须把“一次回调”和“一个包”解耦：回调交出的字节只是字节流的一段，解析器负责在流里找出完整帧。下面是与 12.2 节八个步骤一一对应的最小实现：长度驱动 + 逐字节状态机。

先准备流缓冲区和追加函数：

```c
#define PACKET_MAX_SIZE     32U    /* 与协议约定的最大包长一致 */
#define STREAM_BUFFER_SIZE 128U

static uint8_t stream_buffer[STREAM_BUFFER_SIZE];
static uint16_t stream_write = 0U;  /* 只在主循环使用，不需要 volatile */
static uint16_t stream_read  = 0U;

/* 把刚收到的一段字节追加到流缓冲区末尾；返回 0 表示剩余空间不足。 */
static uint8_t Stream_Append(const uint8_t *data, uint16_t length)
{
    uint16_t i;

    if (length > (uint16_t)(STREAM_BUFFER_SIZE - stream_write))
    {
        return 0U;
    }

    for (i = 0U; i < length; ++i)
    {
        stream_buffer[stream_write + i] = data[i];
    }

    stream_write = (uint16_t)(stream_write + length);

    return 1U;
}
```

解析器在主循环里反复执行，直到缓冲区里再也凑不出一个候选帧：

```c
/* 取出流缓冲区中所有完整、合法的数据包并执行。 */
static void Stream_Parse(void)
{
    uint16_t length;
    uint16_t i;

    while (stream_read < stream_write)
    {
        /* 步骤 1：跳过无效前缀，寻找包头 0xAA。 */
        while ((stream_read < stream_write) &&
               (stream_buffer[stream_read] != 0xAAU))
        {
            stream_read++;
        }

        /* 步骤 2：连长度字段都没到齐，等下一批数据。 */
        if ((uint16_t)(stream_write - stream_read) < 2U)
        {
            break;
        }

        /* 步骤 3、4：读长度；范围非法时只丢弃这一个候选包头。 */
        length = (uint16_t)stream_buffer[stream_read + 1U];
        if ((length < 5U) || (length > PACKET_MAX_SIZE))
        {
            stream_read++;
            continue;
        }

        /* 步骤 5：整包还没到齐，等下一批数据。 */
        if ((uint16_t)(stream_write - stream_read) < length)
        {
            break;
        }

        /* 步骤 6、7：长度已齐，再做结构和校验和检查；通过才执行并消费整包。 */
        if (Packet_ProcessLedCommand(&stream_buffer[stream_read], length) == PACKET_OK)
        {
            stream_read = (uint16_t)(stream_read + length);
        }
        else
        {
            /* 步骤 8：校验失败只前移一个字节，避免漏掉包内的真包头。 */
            stream_read++;
        }
    }

    /* 把没消费完的字节挪回缓冲区开头，避免读写位置一直向右增长。 */
    if (stream_read > 0U)
    {
        for (i = 0U; i < (uint16_t)(stream_write - stream_read); ++i)
        {
            stream_buffer[i] = stream_buffer[stream_read + i];
        }

        stream_write = (uint16_t)(stream_write - stream_read);
        stream_read = 0U;
    }
}
```

主循环改成“先把这一批字节搬进流缓冲区，再重启接收，最后解析”：

```c
if (uart3_rx_ready != 0U)
{
    uint16_t received = uart3_rx_length;

    /* 先搬运再重启，缩短停收窗口。 */
    if (Stream_Append(uart3_rx_buffer, received) == 0U)
    {
        /* 流缓冲区已满：说明上一批数据没有被及时消费，清空后重新同步。 */
        stream_read = 0U;
        stream_write = 0U;
        (void)Stream_Append(uart3_rx_buffer, received);
    }

    uart3_rx_length = 0U;
    uart3_rx_ready = 0U;

    if (UART3_StartReceiveToIdle() != HAL_OK)
    {
        Error_Handler();
    }

    Stream_Parse();
}
```

现在的行为：

- 把 `AA 05 01 FF AF` 和 `AA 05 03 00 B2` 连着发出去，`Stream_Parse()` 会连续消费 5 字节、再消费 5 字节，两包都生效，不再返回 `PACKET_ERROR_LENGTH`；
- 把一个包拆成两次回调，第一次因为“整包没到齐”只把数据留在缓冲区，第二次凑齐后才执行；
- 前面有 `37 99` 之类噪声时，寻找 `0xAA` 的循环会跳过它们，不会像 11.7 节那样把整段丢弃；
- 单批数据不会超过 `STREAM_BUFFER_SIZE`（`uart3_rx_buffer` 最大 64 字节），所以清空后重新追加一定成功；若协议允许单批更大的数据，需要扩大 `STREAM_BUFFER_SIZE` 或改用环形队列。

注意 `Stream_Parse()` 必须在重启接收之后调用，否则解析耗时会让接收保持关闭、丢掉紧随其后的字节。`PACKET_MAX_SIZE` 要与协议约定的最大包长一致；本例只用到 5 和 7 字节，留 32 字节余量。和 9.7 节一样，这两个静态函数要在 `main()` 之前留原型（写在 `/* USER CODE BEGIN PFP */` 区），函数体放 `/* USER CODE BEGIN 4 */` 区。

## 12. 从“一次回调一个包”升级为字节流解析

### 12.1 三类必须处理的输入

真实通信不能假设每次回调恰好得到一个完整包。11.8 节的流式解析就是为下面这三种输入准备的，这里把它的设计依据说清楚。

**一个包被拆开**

```text
第一次回调：AA 07 01
第二次回调：00 02 FF B3
```

**多个包粘在一起**

```text
AA 05 01 FF AF AA 05 03 00 B2
```

第二包校验和为：

$$
0xAA+0x05+0x03+0x00=0xB2
$$

**噪声或丢字节导致错位**

```text
37 99 AA 05 01 FF AF
```

解析器必须跳过无效前缀，重新寻找 `0xAA`，不能因为第一个字节不是包头就丢弃整个缓冲区。

### 12.2 长度驱动的解析步骤

将每次 DMA/IDLE 得到的字节追加到软件缓冲区后，主循环反复执行（下面的八个步骤与 11.8 节 `Stream_Parse()` 的代码逐条对应）：

1. 从当前读位置寻找 `0xAA`；
2. 若不足 2 字节，等待下一批数据；
3. 读取 Length；
4. 若 Length 小于 5 或大于协议最大长度，丢弃当前 `0xAA`，继续找下一个；
5. 若当前缓存字节数少于 Length，等待下一批数据；
6. 取出 Length 字节，检查 Payload 结构与校验和；
7. 校验通过则执行并消费整包；
8. 校验失败则只丢弃一个候选包头字节，再尝试同步。

这里“校验失败只前移一个字节”是为了防止当前候选包内部刚好包含下一帧真正的 `0xAA`。

### 12.3 中断层与协议层应分开

推荐分层：

```text
USART + DMA
-> 接收一段字节
-> 回调只记录位置、长度或切换缓冲区
-> 主循环把字节写入环形缓冲区
-> 流解析器寻找完整帧
-> 协议校验
-> LED、传感器、控制器等业务逻辑
```

不要在 UART 或 DMA 中断中完成以下工作：

- 长循环扫描整个缓冲区；
- 阻塞串口发送；
- `HAL_Delay()`；
- OLED 刷屏；
- Flash 擦写；
- 复杂浮点计算；
- 等待其他外设。

中断占用时间过长会推迟其他中断，增加串口溢出、控制周期抖动和系统响应延迟。

### 12.4 缓冲区所有权方案

| 方案 | 接收是否连续 | 实现难度 | 适用场景 |
| --- | --- | --- | --- |
| 单缓冲区，处理后重启 | 否 | 最低 | 低频人工命令 |
| 回调复制到处理区后重启 | 基本连续 | 中 | 短包、中低速 |
| 双缓冲区 | 连续性较好 | 中 | 一包处理时间可预测 |
| Circular DMA + 软件读指针 | 连续 | 较高 | 持续字节流 |
| Circular DMA + 环形队列/消息队列 | 连续且可扩展 | 最高 | 高频通信、RTOS、多协议 |

本章主代码选择单缓冲区，是为了把启动、完成、处理、重启的边界讲清楚。它不是所有项目的最终架构。

## 13. 怎样选择轮询、中断、DMA 和接收边界

| 需求 | 推荐方式 | 原因 |
| --- | --- | --- |
| 上电打印几行调试信息 | 轮询发送 | 简单、调用后即可确认结束 |
| 偶尔接收固定 2～8 字节命令 | 中断定长接收 | 配置少，CPU 开销可接受 |
| 发送较长数组 | DMA 发送 | 避免逐字节中断 |
| 接收固定长度数据块 | DMA 定长接收 | 数据边界已知 |
| 人工输入或突发不定长命令 | ReceiveToIdle IT/DMA | 可由空闲间隔结束一段接收 |
| 连续高速字节流 | Circular DMA + 软件位置管理 | 避免停收窗口 |
| 有明确包头和长度的协议 | 流缓冲区 + 长度解析 | 不依赖 IDLE 恰好等于包边界 |
| 以换行结尾的文本协议 | 字节流 + `\r\n` 查找 | 结束符就是协议边界 |

选择前依次回答：

1. 一帧长度固定还是变化？
2. 数据是偶发命令还是连续流？
3. 允许接收暂停多久？
4. 发送端能否等待 ACK 后再发下一包？
5. 一次回调中的数据是否可能包含多个包？
6. 一个包是否可能跨多次回调？
7. CPU 是否能承担逐字节中断？
8. 缓冲区由 DMA、ISR 和主循环中的谁拥有？

## 14. 验收与故障诊断

### 14.1 完全收不到数据

按顺序检查：

1. TX 与 RX 是否交叉；
2. 两端是否共地；
3. 使用的 USART 实例和引脚是否与原理图一致；
4. 是否误启用了引脚重映射；
5. 波特率、数据位、校验位、停止位是否一致；
6. 转串口或蓝牙模块是否正确供电；
7. 串口助手是否选择了正确端口；
8. 板载 USB 转串口驱动是否正常；
9. MCU TX 引脚上是否有波形；
10. USART 外设时钟和 GPIO 时钟是否已经开启。

### 14.2 收到乱码

常见原因：

- 两端波特率不一致；
- 系统时钟或 APB 时钟配置错误；
- 一端为 8N1，另一端启用了校验；
- 3.3 V/5 V 电平不兼容；
- GND 接触不良；
- 线路过长或干扰较强；
- 文本数据被按 HEX 显示，或二进制数据被按文本解释。

先发送固定字节 `0x55` 或重复字符 `UUUU`，用逻辑分析仪检查位宽是否均匀，再进入协议层。

### 14.3 只有第一条命令有效

原因通常是接收只启动了一次。检查完成回调或主循环处理后是否重新调用：

- `HAL_UART_Receive_IT()`；
- `HAL_UART_Receive_DMA()`；
- `HAL_UARTEx_ReceiveToIdle_DMA()`。

每次重新启动 ReceiveToIdle DMA 后，若不需要 HT，还要再次关闭 `DMA_IT_HT`。

### 14.4 回调完全不执行

中断模式检查：

1. USART global interrupt 是否在 CubeMX 中启用；
2. `USARTx_IRQHandler()` 是否存在；
3. IRQHandler 是否调用 `HAL_UART_IRQHandler()`；
4. 回调名称、参数和大小写是否完全正确；
5. 是否真的收满了定长接收要求的字节数。

DMA 模式还要检查：

1. RX/TX 是否使用了正确的固定 DMA 通道；
2. DMA 通道 IRQ 是否启用；
3. `DMA1_Channelx_IRQHandler()` 是否调用 `HAL_DMA_IRQHandler()`；
4. DMA 句柄是否通过 `__HAL_LINKDMA` 与 UART 句柄关联；
5. 方向、自增和数据宽度是否正确；
6. 使用 `HAL_UARTEx_ReceiveToIdle_DMA()` 时，除了 DMA 通道 IRQ，**还必须启用 `USARTx global interrupt`**。

第 6 条对应本节最典型的一种“回调不执行”：只开了 DMA 通道中断，没开 USART 全局中断时，**缓冲区收满（TC）能回调，但短数据（没填满缓冲区）永远没有回调**——发 5 个字节毫无反应，把缓冲区长度改成 5 就又能收到。判定方法就是这一条：回调和缓冲区长度绑定，说明 IDLE 中断根本没进来，去 NVIC 里补上 `USARTx global interrupt` 即可，不必改解析代码。

### 14.5 RxEvent 回调在半缓冲区时提前执行

这是 DMA HT 事件，不一定是完整包。可在回调中读取：

```c
HAL_UARTEx_GetRxEventType(huart);
```

若入门命令模式不使用 HT，在每次启动后执行：

```c
__HAL_DMA_DISABLE_IT(huart->hdmarx, DMA_IT_HT);
```

不要通过“把接收数组设得特别大”来碰运气避免 HT；这只会改变触发位置，不会消除事件机制。

### 14.6 缓冲区收满后也进入 RxEvent 回调

这是 TC 事件，属于正常行为。`HAL_UARTEx_ReceiveToIdle_DMA()` 的结束条件是“IDLE 或达到最大长度”，所以缓冲区满时即使没有 IDLE，也必须通知应用处理。

若经常 TC，说明：

- 缓冲区容量小于单次突发数据；
- 发送端没有留下空闲间隔；
- 多个数据包粘在一起；
- 应改用流式解析或更大的分块缓冲区。

### 14.7 接收数据偶尔错位或校验失败

检查：

- 是否把一次 IDLE 回调强行当作一包；
- Length 字段是否定义为整包长度；
- 校验和是否包含包头和长度、排除最后的校验字节；
- 是否在解析前验证实际 `Size`；
- DMA 是否在主循环读取时重新覆盖同一数组；
- TX DMA 是否仍在读取一个已被修改的发送数组；
- 是否存在 ORE、FE、NE；
- 环形缓冲区写指针和读指针是否正确处理回绕。

### 14.8 重复启动返回 HAL_BUSY

`HAL_BUSY` 表示同方向上已有传输尚未结束。不要忽略返回值继续执行。检查是否：

- 在 `while` 中无条件反复启动；
- IDLE/TC 回调尚未结束就再次启动；
- 上一轮错误后状态没有恢复；
- TX DMA 尚未完成就修改并再次发送同一缓冲区。

### 14.9 蓝牙能连接但没有数据

先把协议解析全部移除，只做原样回显，再检查：

1. 模块当前波特率是否仍为 9600；
2. 模块是否处于透传状态而不是 AT 配置状态；
3. USART3 是否使用 PB10/PB11；
4. 手机或电脑是否订阅/打开了模块的接收通道；
5. 模块是否已被另一台主机连接；
6. 发送工具使用的是文本还是 HEX；
7. 模块复位后参数是否恢复或改变。

不同蓝牙模块的连接流程、服务特征和 AT 指令不同，应以具体模块文档为准。

## 15. 综合自测

1. 为什么 UART 的 TX 与 RX 要交叉连接？
2. 为什么共地不能解决 5 V 与 3.3 V 的所有电平兼容问题？
3. 115200、8N1 的理论最大有效字节率是多少？
4. `TXE` 和 `TC` 分别表示什么？
5. 中断模式相比轮询减少了什么，DMA 相比中断又减少了什么？
6. 为什么 `HAL_UART_Receive_IT()` 不应在主循环中无条件反复调用？
7. USART2_RX 和 USART2_TX 分别映射到 DMA1 哪两个通道？
8. `HAL_UARTEx_ReceiveToIdle_DMA()` 的第三个参数是实际包长还是缓冲区最大容量？
9. `HAL_UARTEx_RxEventCallback()` 在 DMA 模式下可能由哪三类事件触发？
10. 为什么关闭 HT 后仍可能在缓冲区满时进入 RxEvent 回调？
11. 为什么 IDLE 不能天然保证一次回调就是一个协议包？
12. 帧 `AA 05 01 FF AF` 中 `05` 和 `AF` 分别表示什么？
13. 为什么解析器应先验证所有命令，再修改 GPIO？
14. 校验和相等能否证明数据绝对没有错误？
15. 连续高速接收为什么更适合 Circular DMA 与环形缓冲区？

**答案要点**：

1. TX 是本设备输出，必须接对端输入 RX；
2. 共地只统一参考电势，不会降低过高的输入电压；
3. `115200/10=11520 Byte/s`；
4. TXE 表示数据寄存器可写下一字节，TC 表示最后一帧已从移位寄存器发送完；
5. 中断避免 CPU 忙等，但仍由 CPU 搬每个字节；DMA 连逐字节搬运也交给硬件；
6. 上一次接收未完成时再次启动会返回 `HAL_BUSY`；
7. RX 为 Channel 6，TX 为 Channel 7；
8. 是本轮允许写入的最大数据元素数；
9. HT、TC、IDLE；
10. TC 是独立的传输完成事件；
11. IDLE 是时间间隔边界，包可能被拆分或粘连；
12. `05` 是整包长度，`AF` 是前四字节累加后的低 8 位；
13. 避免后半包非法时前半包已经生效；
14. 不能，简单累加和存在碰撞；
15. 它能持续接收，并由软件维护读写位置而不必每包停机重启。

## 本章小结

串口收发可以归纳为三层：

```text
物理层
TX/RX 交叉、共地、电平兼容、波特率与帧格式

搬运层
轮询、UART 中断、DMA、IDLE/HT/TC 事件、缓冲区所有权

协议层
包头、长度、Payload、校验和、重同步、ACK 与业务动作
```

轮询模式最适合验证“引脚和参数是否能通”；中断模式解决 CPU 忙等，但仍由 CPU 逐字节搬运；DMA 把重复搬运交给硬件，IDLE 再为突发数据提供时间边界。进入二进制协议后，不能继续把“本次收到的一段字节”直接等同于“一个完整数据包”，而要依靠包头、长度和校验进行流式解析。

对入门工程，先完成：

```text
单缓冲区
-> 启动接收
-> 回调交接
-> 主循环处理
-> 重新启动
```

只有在这条闭环稳定后，再升级到双缓冲、Circular DMA、环形队列和高吞吐协议。这样每一次复杂化都有明确目的，也更容易定位数据究竟丢在引脚、USART、DMA、缓冲区还是协议解析层。
