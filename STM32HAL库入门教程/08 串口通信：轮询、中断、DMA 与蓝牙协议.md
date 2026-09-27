# 08 串口通信：轮询、中断、DMA 与蓝牙协议

## 本章问题

怎样根据数据长度和实时性选择轮询、中断、DMA 或 IDLE 接收，并正确解析字节流？

上一章你已经让 DMA 替 CPU 把 ADC 数据搬进内存；本章把同一套搬运机制接到串口上，并补上串口特有的两个新问题：数据从哪来——收到几个字节才算一包，以及收到之后怎么解析成命令。

## 学习目标

- 用 USART2 轮询收发固定长度命令。
- 用中断和 DMA 完成定长收发。
- 用 DMA + IDLE 接收不定长数据。
- 用 USART3 连接蓝牙透传模块。
- 解析带长度和校验和的连续字节流。

## 1. 实验条件与串口基础

以下以 STM32F103C8T6 为例：电脑调试使用 USART2 的 PA2/PA3，参数为 `115200, 8N1`；蓝牙使用 USART3 的 PB10/PB11，BT24 模块常见参数为 `9600, 8N1`，实际以模块当前设置为准。板卡若使用了不同的重映射或板载 USB 转串口芯片，以原理图为准。

本章实验都按同一条链观察：输入是 RX 收到的字节，状态是接收长度/就绪/错误标志，输出是串口回显或 LED GPIO 动作。配套工程位于 `E:\ProjectStm\Courses\HAL08_USART_BLE`，五个子工程 `01_UART2_Polling`、`02_UART2_IT`、`03_UART2_DMA`、`04_UART2_ReceiveToIdle`、`05_USART3_BT_Protocol` 与本章五个实验一一对应。

### 1.1 UART、USART 与电平

UART 是通用异步收发器；USART 同时支持同步和异步模式。STM32F103 的 USART 配置为 `Asynchronous` 后，就可以使用没有时钟线的 TTL UART。

| 接口 | 线路/电平 | 与 STM32 直连 |
| --- | --- | --- |
| 3.3 V TTL UART | TX、RX、GND，逻辑参考为 3.3 V | 可直连，但仍要核对模块说明 |
| 5 V TTL UART | TX、RX、GND，高电平可能接近 5 V | 不应默认可直连 |
| RS-232 | 正负电压，逻辑可能反相 | 需要 RS-232 收发器 |
| RS-485 | A、B 差分线路，常为半双工 | 需要 RS-485 收发器 |
| USB | D+、D- 差分总线和 USB 协议 | 需要 USB 外设或 USB 转串口芯片 |

USB 转串口芯片只是在 USB 协议和 TTL UART 之间转换；电脑打开的是虚拟串口，STM32 侧仍然使用 USART 的 TX/RX 字节接口。

初学者可以把它想成一个"翻译官"：电脑一侧说 USB，另一侧说 TTL UART，它两边都懂。你在串口助手里敲的字符经 USB 递给翻译官，翻译官换成 TTL 电平从自己的 TX 脚吐给 STM32；反向同理。所以电脑上显示的 COM 口并不直接连到 STM32，中间永远隔着这颗芯片和两根 TTL 线，排错时两端都要照顾到。

### 1.2 TX、RX 交叉与共地

```text
设备 A TX ----> 设备 B RX
设备 A RX <---- 设备 B TX
设备 A GND ----- 设备 B GND
```

TX 是本设备的输出，RX 是本设备的输入；两个 TX 不能直接相连。双向通信要接两条数据线，单向发送至少要接 `STM32 TX -> 对端 RX` 和 GND。

可以把 TX 想成"嘴"、RX 想成"耳朵"：

- 说话的嘴必须对着听话的耳朵，所以两根数据线永远交叉；
- 嘴对嘴、耳对耳（TX 接 TX、RX 接 RX）时，双方什么都收不到；
- 接线前对每根线问一句"它从谁的嘴出来、进谁的耳朵"，就能挡住最常见的接反错误。

数字电平必须相对参考点解释。发送端的 3.3 V 是"相对发送端 GND 的约 3.3 V"，所以两个独立供电的设备通常必须共地；共地只统一参考电势，不会把 5 V 自动变成 3.3 V。

STM32F103x8/B 的 `VDD` 工作范围为 2.0～3.6 V。PA2、PA3 不是 5 V 容忍引脚，不能把 5 V UART 信号直接接到 PA3。蓝牙模块的 `VCC` 可以是 5 V，也不代表其 UART TX 一定是 3.3 V；连接前要分别核对电源和 IO 电平。USB 转 TTL 模块优先使用 3.3 V 逻辑，必要时加电平转换。

### 1.3 8N1 与波特率

先建立直觉，再记定义。I2C、SPI 都带时钟线，接收方跟着时钟脉冲逐位采样；UART 把时钟线省掉了，改用"事先约好节拍"：双方各带一块同样的表，约定每 $1/115200$ 秒走一个位，发送方按表逐位放线，接收方按表逐位采样，只要两块表快慢一致，读出来的就是同一个字节。

有了节拍，还需要"开始"和"结束"的记号。线路空闲时保持高电平；发送方把线拉低一拍就是起始位，等于先咳嗽一声"我要开始了"，接收方以这个下降沿为起点对齐自己的节拍；随后 8 个数据位低位先发；停止位回到高电平一拍，给双方留出重新对齐的喘息，然后线路回到空闲，一帧结束。

如果两块表的快慢不一样，接收方的采样点会一格一格地错开，读到第 7、8 位时早已经"张冠李戴"——这就是波特率不一致表现为乱码的原因。

因此 UART 没有时钟线，双方必须预先约定波特率、数据位、校验位和停止位。`115200, 8N1` 表示每秒 115200 码元、8 个数据位、无校验、1 个停止位。

典型 8N1 帧为：

```text
空闲高电平
-> 起始位 0
-> 8 个数据位，低位先发
-> 停止位 1
-> 回到空闲高电平
```

每个字节占用：

$$
1+8+1=10\ \text{bit}
$$

因此在 115200 波特、8N1、忽略帧间间隔时，理论最大字节率为：

$$
\frac{115200}{10}=11520\ \text{Byte/s}
$$

串口助手的 ASCII/HEX 只是显示方式：例如 `H` 的字节是 `0x48`，文本模式显示为 `H`，HEX 模式显示为 `48`；二进制协议应使用 HEX 模式核对。

### 1.4 USART、引脚与 DMA 映射

| USART | 默认 TX | 默认 RX | 时钟/最高能力 | 本章用途 |
| --- | --- | --- | --- | --- |
| USART1 | PA9 | PA10 | APB2，最高 4.5 Mbit/s | 可作调试口 |
| USART2 | PA2 | PA3 | APB1，最高 2.25 Mbit/s | 电脑串口 |
| USART3 | PB10 | PB11 | APB1，最高 2.25 Mbit/s | 蓝牙透传 |

USART 的波特率分频公式为：

$$
\text{USARTDIV}=\frac{f_{\text{PCLK}}}{16\times\text{baud}}
$$

当 `PCLK1 = 36 MHz` 时，115200 的理想 USARTDIV 是 `19.53125`，对应 BRR 尾数 `0x138` 或 `0x139`（小数部分恰好 0.5，截尾得 8、四舍五入得 9）。CubeF1 HAL 的分频计算两级都向下取整，生成的是 `0x138`；两者波特率误差都远小于 0.1%，以生成代码为准。9600 通常生成 `0xEA6`。改变系统时钟或 APB 预分频后，必须重新查看生成的 `BRR`。

STM32F103C8T6 的 USART1/2/3 均支持 DMA，DMA 请求固定为：

| DMA1 通道 | 请求 |
| --- | --- |
| DMA1 Channel 2 | USART3_TX |
| DMA1 Channel 3 | USART3_RX |
| DMA1 Channel 4 | USART1_TX |
| DMA1 Channel 5 | USART1_RX |
| DMA1 Channel 6 | USART2_RX |
| DMA1 Channel 7 | USART2_TX |

`PB10/PB11` 同时是第 02 章 OLED 的 `I2C2_SCL/SDA`。LQFP48 没有引出 `PC0~PC12` 或 `PD8/PD9`，所以 USART3 不能用 `PC10/PC11`、`PD8/PD9` 绕开冲突；同一实验中使用第 02 章 I2C2 OLED 和本章蓝牙只能二选一。若要同时使用 OLED，可改用第 09 章的 `PB8/PB9` 软件 I2C 方案。

## 2. 搬运方式、状态位与公共配置

### 2.1 轮询、中断、DMA 的职责

三种方式的本质区别是"谁在盯着 `RXNE`"：

- 轮询：CPU 自己站在门口等。主循环反复读状态位，等到了才动手，等不到就干耗着；
- 中断：给 `RXNE` 装上门铃。CPU 平时干别的，每个字节到了门铃一响就进一次 ISR，亲自把它搬走；
- DMA：门口装了自动收件柜。`RXNE` 触发 DMA 请求，DMA 控制器把字节搬进内存，全程不用 CPU 出手，收满或线路空闲才叫人一声。

| 方式 | 谁搬运每个字节 | CPU 是否等待 | 完成通知 | 适合场景 |
| --- | --- | --- | --- | --- |
| 轮询 | CPU | 是 | 函数返回 | 初次验证、低频短数据 |
| 中断 | CPU 在 ISR 中搬运 | 否 | `HAL_UART_RxCpltCallback()` | 定长命令 |
| DMA | DMA 控制器 | 否 | DMA/UART 完成回调 | 批量收发、不定长接收 |

DMA 并没有消除 USART 的 `TXE/RXNE` 硬件事件，而是让这些事件请求 DMA 搬运；CPU 通常只在半传输、传输完成、空闲线或错误事件时介入。

选择时先看数据边界：固定 2～8 字节命令可用中断，固定数据块可用 DMA，突发不定长数据可用空闲线接收（ReceiveToIdle，对应 `HAL_UARTEx_ReceiveToIdle_DMA()`，见 2.3 节和第 6 节），连续高速流才考虑 Circular DMA 和读指针管理。

### 2.2 关键状态位

- `TXE`：`USART_DR` 中的发送数据寄存器可写，可继续装入下一字节。
- `TC`：当前完整帧已经从发送移位寄存器发出；立即关闭串口或切换 RS-485 方向时等待它，而不能只看 DMA 把最后一个字节写入 `USART_DR`。
- `RXNE`：接收数据寄存器已有可读字节。
- `IDLE`：接收过数据后检测到一段空闲帧，可作为突发数据的时间边界。
- `ORE`：上一字节未取走又收到下一字节；`FE` 是帧格式错误；`NE` 是噪声错误；还可能看到 `PE` 校验错误。

发送侧的两个标志容易混淆。把发送想成两道门：写入 `USART_DR` 只是进了第一道门（发送数据寄存器），`TXE` 随即回到可写状态，程序就可以装下一个字节；字节还要穿过第二道门（发送移位寄存器）逐位移出线路，全部移完才是 `TC`。所以"能装下一个字节"（`TXE`）比"这一帧真正发完"（`TC`）早得多，关闭串口或切换方向前要等的是后者。

`IDLE`、`ORE/FE/NE/PE` 的状态读取和清除要遵守"先读 `USART_SR`，再读 `USART_DR`"的顺序。使用 HAL 时由 `HAL_UART_IRQHandler()` 统一处理，不要在应用层另写一套清标志逻辑。DMA 接收错误和 `ORE` 通常会结束本轮接收；某些 IT 模式的 `FE/NE/PE` 可能只报告错误而继续接收，错误恢复不能一概而论。应用可用 `HAL_UART_GetError(const UART_HandleTypeDef *huart)` 读取 `HAL_UART_ERROR_ORE`、`HAL_UART_ERROR_FE`、`HAL_UART_ERROR_NE`、`HAL_UART_ERROR_PE` 等错误位。定长 IT/DMA 也可以在 `HAL_UART_ErrorCallback()` 中只置错误标志，主循环再停止并重新启动接收；不要在 ISR 中做阻塞发送或长处理。

### 2.3 USART2 的最小配置

外设参数为异步、`115200`、8 数据位、无校验、1 停止位、TX/RX；GPIO 使用 PA2/PA3。中断接收需要启用 `USART2 global interrupt`，并保留：

```c
void USART2_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart2);
}
```

DMA 使用 DMA1 Channel 6 接收、Channel 7 发送，Byte、外设地址不递增、内存地址递增、Normal 模式；UART 句柄必须通过 `__HAL_LINKDMA()` 关联 DMA 句柄，并启用对应 DMA IRQ：

```c
__HAL_LINKDMA(&huart2, hdmarx, hdma_usart2_rx_dma1_channel6);
__HAL_LINKDMA(&huart2, hdmatx, hdma_usart2_tx_dma1_channel7);

void DMA1_Channel6_IRQHandler(void)
{
    HAL_DMA_IRQHandler(huart2.hdmarx);
}

void DMA1_Channel7_IRQHandler(void)
{
    HAL_DMA_IRQHandler(huart2.hdmatx);
}
```

使用 `HAL_UARTEx_ReceiveToIdle_DMA()` 时，DMA 通道 IRQ 负责缓冲区收满（TC），USART2 IRQ 负责 IDLE 和错误；两者都要开。该 API 会置位 `IDLEIE`，但不能替代 `USART2_IRQHandler()` → `HAL_UART_IRQHandler()`。短数据没有填满缓冲区时，缺 USART2 IRQ 就不会回调。

以下代码使用新版 CubeF1 HAL 提供的 `HAL_UARTEx_ReceiveToIdle_DMA()` 和 `HAL_UART_AbortReceive()`。若 HAL 中没有这些声明，应先升级 HAL，或改用 DMA + IDLE 手动处理。

各实验只保留一份同名 HAL 回调；若同时使用多个 USART，在回调内按 `huart->Instance` 分流。

### 2.4 CubeMX 中的具体操作

以工程基线 CubeMX 6.17.0 为例，打开 `.ioc` 后按四步走；每步都给出配置落在代码里的位置，配完可以回工程里核对。

**第一步，选模式与引脚。** 左侧外设列表点开 `Connectivity`，点击 `USART2`，`Mode` 下拉选 `Asynchronous`。PA2、PA3 会自动变绿并标成 `USART2_TX`、`USART2_RX`（对应 `.ioc` 里的 `PA2.Signal=USART2_TX`、`PA3.Signal=USART2_RX`、`USART2.VirtualMode=VM_ASYNC`）。若误选成只发送的单工模式，RX 引脚不会被分配，接收实验无从谈起。

**第二步，填参数。** 在 `Parameter Settings` 中核对四项，它们与 `.ioc` 键一一对应：

| 字段 | 填什么 | 对应 `.ioc` 键 | 填错的后果 |
| --- | --- | --- | --- |
| Baud Rate | `115200` | `USART2.BaudRate=115200` | 与对端不一致→乱码或完全收不到 |
| Word Length | `8 Bits` | `USART2.WordLength=WORDLENGTH_8B` | 两端字长不同→字节错位 |
| Parity | `None` | `USART2.Parity=PARITY_NONE` | 一端开校验另一端没开→最高位被当校验位，可打印字符变形 |
| Stop Bits | `1` | `USART2.StopBits=STOPBITS_1` | 停止位不一致→帧错误、丢字节 |

实验五的 USART3 同法操作，只有 Baud Rate 改填 `9600`。

**第三步，开中断。** 切到 `NVIC Settings` 页，勾选 `USART2 global interrupt`（对应 `NVIC.USART2_IRQn=true`）。不勾的后果很隐蔽：代码能编译、轮询照样能跑，但 `USART2_IRQHandler()` 根本不会触发——中断接收、ReceiveToIdle 的短数据 IDLE 回调全部静默失效。这是本章实验"收不到回调"的第一大原因。配套工程里 USART 中断优先级设为 2、DMA 通道设为 1（数值越小优先级越高，概念见第 4 章）：DMA 通道设得更高，是因为搬运事件必须及时收尾、下一轮传输才接得上；IDLE 判包晚几微秒无碍，可以排在它后面。

**第四步，加 DMA。** 切到 `DMA Settings` 页，点 `Add`，在请求下拉里选 `USART2_RX`；F103 上它固定落到 DMA1 Channel 6（映射见 1.4 节表，选不到别的通道）。需要 DMA 发送时再加一条 `USART2_TX`（Channel 7）。每条通道的参数与工程 `dma.c` 的生成代码一一对应：

| 字段 | 填什么 | 填错的后果 |
| --- | --- | --- |
| Mode | `Normal` | 选成 `Circular` 后 DMA 永不停止，不再按"收满即结束一轮"的节奏走回调 |
| Data Width | `Byte` | 选成 `Word` 会按 4 字节对齐搬运，缓冲区内容和个数全乱 |
| Increment Address | 勾 `Memory`，不勾 `Peripheral` | 不勾 Memory 递增→所有字节都写进 `buffer[0]`；勾了 Peripheral 递增→外设地址越过数据寄存器，读到随机位置 |

生成代码后核对 `main.c`：实验三、实验四的工程（`03_UART2_DMA`、`04_UART2_ReceiveToIdle`）调用顺序是 `MX_GPIO_Init()` → `MX_DMA_Init()` → `MX_USART2_UART_Init()`（`.ioc` 的 `functionlistsort` 也是这个顺序），实验五蓝牙工程 `05_USART3_BT_Protocol` 用的是 USART3，即 `MX_USART3_UART_Init()`，相对顺序相同。启动接收之前，DMA 通道必须已经初始化并经 `__HAL_LINKDMA()` 挂到 UART 句柄上；顺序乱了，`HAL_UART_Receive_DMA()` 内部对 DMA 的启动就会失败。

## 3. 实验一：USART2 轮询发送与固定长度指令

**目标与接线。** 使用 PA2/PA3 连接 USB 转 TTL，TX/RX 交叉并共地。在 CubeMX 中把 PB12、PB13、PB14 配置为 GPIO_Output：输出初始电平 `Low`、模式 `Output Push Pull`、无上下拉、速度 `Low`，三个引脚分别接红、绿、蓝 LED 阳极，LED 阴极接 GND，每只 LED 串约 1 kΩ 限流电阻。代码直接使用 `GPIOB/GPIO_PIN_12/13/14`，不依赖 GPIO User Label。

固定 2 字节命令的含义是：`R1/G1/B1` 开灯，`R0/G0/B0` 关灯。以下函数按高电平点亮计算：

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
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, state);
            break;
        case (uint8_t)'G':
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, state);
            break;
        case (uint8_t)'B':
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_14, state);
            break;
        default:
            break;
    }
}
```

在 `MX_USART2_UART_Init()` 后使用下面的最小主循环。`sizeof(message) - 1U` 去掉字符串结尾的 `'\0'`，因此实际发送 13 字节；`HAL_UART_Transmit()` 的第四个参数是毫秒超时，`HAL_MAX_DELAY` 表示持续等待。

```c
static const uint8_t message[] = "Hello World\r\n";
static uint8_t rx_polling[2];

while (1)
{
    if (HAL_UART_Transmit(&huart2,
                          message,
                          (uint16_t)(sizeof(message) - 1U),
                          100U) != HAL_OK)
    {
        Error_Handler();
    }

    if (HAL_UART_Receive(&huart2,
                         rx_polling,
                         (uint16_t)sizeof(rx_polling),
                         HAL_MAX_DELAY) == HAL_OK)
    {
        LED_ApplyAsciiCommand(rx_polling);

        if (HAL_UART_Transmit(&huart2,
                              rx_polling,
                              (uint16_t)sizeof(rx_polling),
                              100U) != HAL_OK)
        {
            Error_Handler();
        }
    }

    HAL_Delay(1000U);
}
```

这段程序先发一次 `Hello World\r\n`，然后阻塞在接收上：在收到第一条 2 字节命令之前，`Hello World` 只会出现一次，不会每秒重复。想演示周期发送，应移走阻塞接收并另用 tick 调度。

**操作与预期。** 串口助手设为 `115200, 8N1`：上电先看到 `Hello World`；发送 `R1` 应点亮红灯并收到 `R1` 回显；发送 `B0` 应熄灭蓝灯。发送 1 个字节时程序仍会等待第 2 个字节，这是定长接收的正常现象。把波特率改错应出现乱码；切换 HEX 后，`R1` 应显示为 `52 31`。

如果上电连 `Hello World` 都看不到，先不要动代码：核对串口助手打开的端口和波特率，确认 STM32 的 TX（PA2）接到模块的 RX。程序第一件事就是发问候，问候都没有说明发送链路或电脑侧显示有问题，与接收配置无关。

只有最小系统板、没有任何外接 LED 时，可以退而求其次：把某一条命令（如 `R1/R0`）映射到低电平点亮的 `PC13` 的亮灭，仅用于验证"命令到达并被执行"——三个通道挤在一个灯上无法区分红绿蓝，观察链降级为通断判断，按完每条命令只能看同一个灯的反应。

## 4. 实验二：USART2 中断定长接收

**启动一次，等待回调。** `HAL_UART_Receive_IT()` 启动一轮指定长度的接收并立即返回；每个 `RXNE` 事件仍由 CPU 在 ISR 中搬运，收满后才调用 `HAL_UART_RxCpltCallback()`。不要在主循环顶部无条件反复启动，否则上一轮未结束时通常会得到 `HAL_BUSY`。

```c
static uint8_t rx_it_buf[2];
static volatile uint8_t rx_it_ready = 0U;

static void UART2_StartReceive(void)
{
    if (HAL_UART_Receive_IT(&huart2,
                            rx_it_buf,
                            (uint16_t)sizeof(rx_it_buf)) != HAL_OK)
    {
        Error_Handler();
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        rx_it_ready = 1U;
    }
}
```

在 `MX_USART2_UART_Init()` 后调用一次 `UART2_StartReceive()`，主循环按"处理完成 -> 清除状态 -> 再启动"的顺序运行：

```c
UART2_StartReceive();

while (1)
{
    if (rx_it_ready != 0U)
    {
        LED_ApplyAsciiCommand(rx_it_buf);

        if (HAL_UART_Transmit(&huart2,
                              rx_it_buf,
                              (uint16_t)sizeof(rx_it_buf),
                              100U) != HAL_OK)
        {
            Error_Handler();
        }

        rx_it_ready = 0U;
        UART2_StartReceive();
    }
}
```

回调只置 `rx_it_ready`，主循环读取数组后才重新启动；因此处理期间不会被新接收覆盖，但这段窗口内的数据也不会被接收。连续高吞吐场景需要处理区复制、双缓冲或环形队列。

配套工程 `02_UART2_IT` 在此之上多了一个错误出口，完整代码如下（`uart_error` 与 `rx_it_ready` 一样声明为 `volatile`，否则主循环可能永远读到被编译器优化的旧值）：

```c
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        uart_error = 1U;
    }
}

/* 主循环中，先处理错误再处理数据： */
while (1)
{
    if (uart_error != 0U)
    {
        uart_error = 0U;
        HAL_UART_AbortReceive(&huart2);   /* 彻底停掉上一轮接收 */
        UART2_StartReceive();             /* 再重新启动 */
    }

    if (rx_it_ready != 0U)
    {
        /* ……与前面相同的数据处理…… */
    }
}
```

恢复动作放在主循环而不是错误回调里，是因为错误回调仍处在 ISR 上下文，那时接收状态还没清理干净，直接重启容易撞上异常；"先中止、再启动"的顺序与 6.2 节的错误恢复一致。

**操作与预期。** 把数组改成 `rx_it_buf[5]`，一次发送 5 字节 `RB01X`，应立即回显 5 字节；只发 2 字节则不会完成本轮。改回 2 后发送 `R1`，应再次回显。第二次命令没有反应，通常是处理完成后漏掉了再次调用 `HAL_UART_Receive_IT()`。一条回显都没有则要往前查：`USART2 global interrupt` 是否勾选、`USART2_IRQHandler()` 是否调用 `HAL_UART_IRQHandler(&huart2)`——中断链路断了，回调一次都不会进来，现象和"没启动接收"一模一样。

## 5. 实验三：USART2 定长 DMA 收发

**输入与状态。** RX DMA 使用 Channel 6，TX DMA 使用 Channel 7；DMA 搬运期间 CPU 不逐字节进入 USART 中断。下面使用独立 RX/TX 数组，避免 DMA 正在读取发送数组时又被改写。

```c
static uint8_t rx_dma_fixed[2];
static uint8_t tx_dma_fixed[2];
static volatile uint8_t rx_dma_ready = 0U;
static volatile uint8_t tx_dma_busy = 0U;

static void UART2_StartReceiveDMA(void)
{
    if (HAL_UART_Receive_DMA(&huart2,
                             rx_dma_fixed,
                             (uint16_t)sizeof(rx_dma_fixed)) != HAL_OK)
    {
        Error_Handler();
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        rx_dma_ready = 1U;
    }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        tx_dma_busy = 0U;
    }
}
```

初始化时先调用 `MX_DMA_Init()`，再调用 `MX_USART2_UART_Init()`，最后启动一次：

```c
UART2_StartReceiveDMA();

while (1)
{
    if (rx_dma_ready != 0U)
    {
        LED_ApplyAsciiCommand(rx_dma_fixed);

        if (tx_dma_busy == 0U)
        {
            tx_dma_fixed[0] = rx_dma_fixed[0];
            tx_dma_fixed[1] = rx_dma_fixed[1];
            tx_dma_busy = 1U;

            if (HAL_UART_Transmit_DMA(&huart2,
                                      tx_dma_fixed,
                                      (uint16_t)sizeof(tx_dma_fixed)) != HAL_OK)
            {
                tx_dma_busy = 0U;
            }
        }

        rx_dma_ready = 0U;
        UART2_StartReceiveDMA();
    }
}
```

`HAL_UART_Transmit_DMA()` 返回 `HAL_OK` 只表示 DMA 启动成功；`tx_dma_fixed` 在 `HAL_UART_TxCpltCallback()` 之前必须保持不变。完成回调到来后才能修改或复用发送数组。

**固定长度的边界。** `HAL_UART_Receive_DMA(&huart2, buffer, 64U)` 表示"收满 64 个数据元素"，不是"最多收 64 字节并自动报告实际长度"。把 RX/TX 数组改成 64 后，必须一次发满 64 字节才会进入一次 `HAL_UART_RxCpltCallback()`；只发 5 字节时没有回显是预期现象。测试 64 字节回显时可用 `memcpy(tx_dma_fixed, rx_dma_fixed, sizeof(rx_dma_fixed));` 替代两行赋值，并包含 `string.h`。

**操作与预期。** 接线与实验一相同。发送 2 字节 `R1`：红灯点亮，串口助手收到 `R1` 回显——LED 是主循环执行 `LED_ApplyAsciiCommand()` 的输出，回显是 `HAL_UART_Transmit_DMA()` 经 Channel 7 发出的输出，一条链上两个可观察点。只发 1 字节没有任何反应，这是"收满才回调"的正常表现，不是故障；改用 64 字节数组后同理。若 `HAL_UART_Transmit_DMA()` 返回非 `HAL_OK`，多半是上一轮 TX DMA 还没发完，工程里的 `tx_dma_busy` 标志就是用来挡住这种重入的。

实验三的工程 `03_UART2_DMA` 同样带有 `uart_error` 分支：错误回调置标志，主循环里 `HAL_UART_AbortReceive()` 之后重启 `UART2_StartReceiveDMA()`，与实验二的错误出口完全相同。

## 6. 实验四：DMA + IDLE 接收不定长数据

### 6.1 IDLE、HT、TC 的含义

不定长数据的难点在于：接收方事先不知道这一轮对方要说几个字节，收多少、等多久都没有依据。`IDLE` 给出的答案是"听停顿"：接收方在收到数据之后，发现线路持续保持一个整帧以上的高电平（没有新的起始位到来），就判定这一轮说完了，主动通知应用。就像听人报一串电话号码，报完总有个自然停顿——停顿本身就是"我说完了"的信号。所以它天然适合"发一包、歇一下"的命令与应答场景，不适合背靠背的连续高速数据流；停顿拆包、连发并包的问题在 9 节展开。

`HAL_UARTEx_ReceiveToIdle_DMA()` 的第三个参数是本轮最多能写入的元素数，不是已知包长；回调参数 `Size` 才是当前收到的有效字节数。Normal 模式下：

| 事件 | 含义 | 是否结束本轮 |
| --- | --- | --- |
| `HAL_UART_RXEVENT_HT` | 收到缓冲区一半 | 否 |
| `HAL_UART_RXEVENT_TC` | 缓冲区收满 | 是 |
| `HAL_UART_RXEVENT_IDLE` | 未收满时检测到空闲线 | 是 |

可在 `HAL_UARTEx_RxEventCallback()` 内准确查询事件类型：

```c
HAL_UART_RxEventTypeTypeDef event_type;

event_type = HAL_UARTEx_GetRxEventType(huart);
(void)event_type;  /* 按 HT/TC/IDLE 分支处理 */
```

如果本实验只处理 IDLE/TC，就在每次成功启动后关闭 HT 中断；关闭 HT 不会关闭独立的 TC 事件：

```c
__HAL_DMA_DISABLE_IT(huart2.hdmarx, DMA_IT_HT);
```

IDLE 是时间边界，不是协议包头。包内停顿可能把一个包拆成多次回调，两个包连续发送又可能一次回调收到多个包；真正的边界应由包头、长度或结束符决定。Normal 模式的 `Size` 可直接作为本轮长度；Circular 模式要由应用维护读写位置和回绕，不能每次把 `buffer[0..Size-1]` 直接当成一批新数据。

### 6.2 最小完整接收与恢复代码

下面的清单为了便于逐行讲解，把恢复动作拆成了独立函数；配套工程 `04_UART2_ReceiveToIdle` 把这段逻辑直接内联在 `main()` 主循环里，对照工程时按结构对应即可。

```c
#define UART2_RX_BUFFER_SIZE 64U

static uint8_t uart2_rx_buffer[UART2_RX_BUFFER_SIZE];
static volatile uint16_t uart2_rx_length = 0U;
static volatile uint8_t uart2_rx_ready = 0U;
static volatile uint8_t uart_error = 0U;

static HAL_StatusTypeDef UART2_StartReceiveToIdle(void);
static void UART2_RecoverFromRxError(void);

static HAL_StatusTypeDef UART2_StartReceiveToIdle(void)
{
    HAL_StatusTypeDef status;

    status = HAL_UARTEx_ReceiveToIdle_DMA(&huart2,
                                          uart2_rx_buffer,
                                          (uint16_t)sizeof(uart2_rx_buffer));

    if (status == HAL_OK)
    {
        __HAL_DMA_DISABLE_IT(huart2.hdmarx, DMA_IT_HT);
    }

    return status;
}

void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    if ((huart->Instance == USART2) &&
        (Size > 0U) &&
        (Size <= (uint16_t)sizeof(uart2_rx_buffer)) &&
        (uart2_rx_ready == 0U))
    {
        uart2_rx_length = Size;
        uart2_rx_ready = 1U;
    }
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2)
    {
        uart_error = 1U;
    }
}

static void UART2_RecoverFromRxError(void)
{
    uart2_rx_length = 0U;
    uart2_rx_ready = 0U;

    /* 先停止当前接收，再重新启动；顺序不能颠倒。 */
    if (HAL_UART_AbortReceive(&huart2) != HAL_OK)
    {
        (void)HAL_UART_DMAStop(&huart2);
    }

    if (UART2_StartReceiveToIdle() != HAL_OK)
    {
        Error_Handler();
    }
}
```

初始化顺序为 `HAL_Init()`、时钟、GPIO、`MX_DMA_Init()`、`MX_USART2_UART_Init()`，最后启动一次接收：

```c
if (UART2_StartReceiveToIdle() != HAL_OK)
{
    Error_Handler();
}
```

主循环中，回调只交接长度；主循环读取稳定数组、完成处理后再重启。错误标志也由主循环处理：

```c
while (1)
{
    if (uart_error != 0U)
    {
        uart_error = 0U;
        UART2_RecoverFromRxError();
    }

    if (uart2_rx_ready != 0U)
    {
        uint16_t length = uart2_rx_length;

        /* 在这里读取 uart2_rx_buffer[0..length-1]。 */
        if (length > 0U)
        {
            if (HAL_UART_Transmit(&huart2,
                                  uart2_rx_buffer,
                                  length,
                                  100U) != HAL_OK)
            {
                Error_Handler();
            }
        }

        uart2_rx_length = 0U;
        uart2_rx_ready = 0U;

        if (UART2_StartReceiveToIdle() != HAL_OK)
        {
            Error_Handler();
        }
    }
}
```

这个单缓冲区模型的所有权顺序是：DMA 写入 -> 回调记录 `Size` -> 主循环读取 -> 清状态 -> 重新启动。Normal 模式的 IDLE/TC 已经结束本轮，正常路径直接重启；错误路径才先 `HAL_UART_AbortReceive()` 再启动。处理期间 USART 暂停接收；需要连续接收时，应在回调中快速复制到另一块缓冲区后立即启动，或改用 Circular DMA 加软件读指针。

**操作与预期。** 启用 USART2 与 DMA IRQ 后，发送 1、5、13 字节都应进入 `HAL_UARTEx_RxEventCallback()`，主循环原样回显，`Size` 等于实际长度。若 64 字节缓冲区只收到 5 字节却无回调，通常是未启用 `USART2 global interrupt`，IDLE 无法触发短数据回调。要验证错误恢复，应主动制造可确认的 FE/NE/ORE 并观察错误回调，而不是仅拔插空闲 RX 线。另外，工程在长度不少于 2 字节时还会按前两字节驱动 LED（`LED_ApplyAsciiCommand()`）：发送 `R1` 会点亮红灯，只想验证回显就发 `12345` 之类的非命令字节。

## 7. 实验五：USART3 蓝牙透传接收

### 7.1 透传链路与接线

蓝牙透传模块把无线协议栈隐藏在模块内部，对 STM32 暴露普通 UART：

```text
手机/电脑 <-> 蓝牙无线链路 <-> 透传模块 <-> USART3 <-> STM32
```

BT24 仅作为示例；经典蓝牙与 BLE、主机/从机角色、服务和特征都要以模块说明书为准。

```text
STM32 PB10 / USART3_TX -> 模块 RX
STM32 PB11 / USART3_RX <- 模块 TX
STM32 GND              -> 模块 GND
模块 VCC               -> 按模块板标注供电
```

先检查 TX/RX 是否交叉、GND 是否共地、模块 UART IO 是否兼容 3.3 V。模块 `VCC` 允许 5 V 不代表 TX/RX 允许 5 V。

USART3 配置为异步、PB10/PB11、`9600, 8N1`（若模块被 AT 指令改过，以模块当前参数为准）；启用 `USART3 global interrupt`，RX 使用 DMA1 Channel 3；如需 DMA 发送，再使用 Channel 2。RX/TX 均按 Byte、外设地址固定、内存地址递增、Normal 模式配置。USART3 的 IRQ 处理函数必须调用：

```c
void USART3_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart3);
}

void DMA1_Channel3_IRQHandler(void)
{
    HAL_DMA_IRQHandler(huart3.hdmarx);
}

void DMA1_Channel2_IRQHandler(void)
{
    HAL_DMA_IRQHandler(huart3.hdmatx);
}
```

本实验的 ReceiveToIdle 仍需同时开启 DMA1 Channel 3 IRQ 和 USART3 IRQ；`PB10/PB11` 与第 02 章 I2C2 OLED 不能同时占用。

### 7.2 复用 USART2 的接收实现

对 STM32 来说，蓝牙模块就是"另一台串口对端"：模块从无线链路收到什么字节，就原样从自己的 TX 引脚吐给 USART3，不添加格式、不解释内容。既然接口行为和电脑侧的 USB 转 TTL 完全一样，6.2 节那套 ReceiveToIdle 状态与函数就可以原封不动搬过来，只换实例和引脚——这也是先在 USART2 上把接收调通、再迁移到 USART3 的用意。

复制 6.2 节的 ReceiveToIdle 状态和函数，再按下表替换：

| USART2 | USART3 |
| --- | --- |
| `huart2` | `huart3` |
| `uart2_rx_buffer/length/ready/error` | `uart3_rx_buffer/length/ready`、`uart_error` |
| `UART2_RX_BUFFER_SIZE` | `UART3_RX_BUFFER_SIZE`，仍取 `64U` |
| `UART2_StartReceiveToIdle()` | `UART3_StartReceiveToIdle()` |
| `UART2_RecoverFromRxError()` | `UART3_RecoverFromRxError()` |
| DMA1 Channel 6 | DMA1 Channel 3 |
| `USART2_IRQHandler()` | `USART3_IRQHandler()` |

初始化顺序仍为：配置 DMA → `MX_USART3_UART_Init()` → 启动一次 `UART3_StartReceiveToIdle()`。错误路径先中止接收，再重启 ReceiveToIdle。

若同时使用 USART2 和 USART3，只保留一份 `HAL_UARTEx_RxEventCallback()` 和 `HAL_UART_ErrorCallback()`，在函数内按 `huart->Instance` 用 `if/else if` 分流。蓝牙模块只转发字节，不会自动回显或发送 ACK。

## 8. 蓝牙协议帧与校验

### 8.1 帧格式

先想清楚为什么要"设计"一个帧，而不是直接把 `LED_ID`、`STATE` 两个字节发过去。UART 只保证把字节原样送到，不保证接收方能看懂：字节流里没有"这是开头"的标记，没有"一共几个字节"的信息，也不知道路上有没有字节被干扰损坏。直接发裸数据，接收方分不清 `01 FF` 是新命令还是上一包的残骸。协议帧就是给字节流加的一套标点：

- 帧头 `0xAA` 回答"从哪里开始"——双方约定的固定口令；
- `Length` 回答"要等多久才算收齐"——让接收方知道这个包总共有几个字节；
- `Checksum` 回答"内容对不对"——为无线链路上的损坏提供最后一道检查。

三件套齐全，解析器才有把握把字节流切成一个个可信的包；9 节的断包、粘包、噪声处理全部建立在这三个字段之上。

| 字节位置 | 字段 | 含义 |
| ---: | --- | --- |
| 0 | Header | 固定 `0xAA` |
| 1 | Length | 从 Header 到 Checksum 的整包总字节数 |
| 2...N-2 | Payload | 每两字节为一组 `[LED_ID, STATE]` |
| N-1 | Checksum | 前面所有字节累加后的低 8 位 |

`LED_ID`：`0x01` 红、`0x02` 绿、`0x03` 蓝；`STATE`：`0x00` 关闭、`0xFF` 打开。缓冲区上限为 `PACKET_MAX_SIZE = 32U`；由于 Payload 是非空偶数字节，合法 `Length` 只能是 `5、7、9……31`。

若整包长度为 `N`：

$$
\text{Checksum}=
\left(\sum_{i=0}^{N-2}\text{packet}[i]\right)\bmod 256
$$

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

打开红灯的帧为：

```text
AA 05 01 FF AF
```

因为 `0xAA + 0x05 + 0x01 + 0xFF = 0x1AF`，低 8 位是 `0xAF`。关闭红灯并打开绿灯的帧为：

```text
AA 07 01 00 02 FF B3
```

这里的 `05`、`07` 都是整包长度，不是 Payload 长度；第二帧最后的校验字节是 `0xB3`。

### 8.2 先完整验证，再执行 GPIO

解析顺序固定为：实际长度为 `5..31` 的奇数、包头 `0xAA`、Length 等于实际长度、Payload 长度为正偶数、校验和正确、所有 LED_ID/STATE 合法；全部通过后才执行命令，避免"前半包已经生效、后半包才发现错误"。

下面的清单把"合法性检查"拆成了独立函数，便于讲解；配套工程 `05_USART3_BT_Protocol` 把这些检查内联在 `Packet_ProcessLedCommand()` 中，没有同名函数，对照时按结构对应即可。

```c
#define PACKET_MAX_SIZE 32U

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
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, pin_state);
            break;
        case 0x02U:
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, pin_state);
            break;
        case 0x03U:
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_14, pin_state);
            break;
        default:
            break;
    }
}

static uint8_t Packet_ProcessLedCommand(const uint8_t *packet,
                                        uint16_t size)
{
    uint16_t payload_length;
    uint16_t i;

    if ((packet == NULL) || (size < 5U) || (size > PACKET_MAX_SIZE))
    {
        return 0U;
    }

    if ((packet[0] != 0xAAU) || (packet[1] != (uint8_t)size))
    {
        return 0U;
    }

    payload_length = (uint16_t)(size - 3U);
    if ((payload_length == 0U) || ((payload_length % 2U) != 0U))
    {
        return 0U;
    }

    if (Packet_Checksum8(packet, (uint16_t)(size - 1U)) != packet[size - 1U])
    {
        return 0U;
    }

    for (i = 2U; i < (uint16_t)(size - 1U); i += 2U)
    {
        if (LED_CommandIsValid(packet[i], packet[i + 1U]) == 0U)
        {
            return 0U;
        }
    }

    for (i = 2U; i < (uint16_t)(size - 1U); i += 2U)
    {
        LED_ApplyBinaryCommand(packet[i], packet[i + 1U]);
    }

    return 1U;
}
```

若 LED 为低电平点亮，只在 `LED_ApplyBinaryCommand()` 中反转 `GPIO_PIN_SET/GPIO_PIN_RESET`，不要改变协议中的 `0x00/0xFF` 含义。简单累加和能发现许多单字节错误，但不能排除所有碰撞。

## 9. 字节流解析：断包、粘包与噪声

UART 只提供连续字节流。`IDLE` 回调的一次 `Size` 不能直接当作一个包：

```text
断包：第一次 AA 07 01，第二次 00 02 FF B3
粘包：AA 05 01 FF AF AA 05 03 00 B2
噪声：37 99 AA 05 01 FF AF
```

第二个示例中的校验和为 `0xAA + 0x05 + 0x03 + 0x00 = 0xB2`。解析器必须寻找 `0xAA`，按 Length 等待完整帧，遇到非法长度或校验失败时只前移一个候选字节，再继续寻找真正包头。

这个最小解析器没有帧间超时：若噪声中的 `0xAA` 后给出看似合法的奇数长度，而发送端不再补齐，解析器会一直等待。可靠传输应增加接收超时，或使用结束符、转义、COBS/SLIP 等成帧方法（COBS/SLIP 是两种常见的字节流成帧方案，这里只需知道有这类方法，暂不展开）。

### 9.1 流缓冲区与追加

USART3 每次回调的数组仍由 DMA 写入；主循环先把它复制到软件流缓冲区，再清状态、重启接收、解析：

```c
#define STREAM_BUFFER_SIZE 128U

static uint8_t stream_buffer[STREAM_BUFFER_SIZE];
static uint16_t stream_write = 0U;
static uint16_t stream_read = 0U;

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

### 9.2 长度驱动的解析器

```c
static void Stream_Parse(void)
{
    uint16_t length;
    uint16_t i;

    while (stream_read < stream_write)
    {
        /* 跳过无效前缀，寻找包头 0xAA。 */
        while ((stream_read < stream_write) &&
               (stream_buffer[stream_read] != 0xAAU))
        {
            stream_read++;
        }

        /* 连长度字段都没到齐，等待下一批数据。 */
        if ((uint16_t)(stream_write - stream_read) < 2U)
        {
            break;
        }

        length = stream_buffer[stream_read + 1U];
        if ((length < 5U) ||
            (length > PACKET_MAX_SIZE) ||
            ((length & 1U) == 0U))
        {
            stream_read++;
            continue;
        }

        /* 整包还没到齐，等待下一批数据。 */
        if ((uint16_t)(stream_write - stream_read) < length)
        {
            break;
        }

        if (Packet_ProcessLedCommand(&stream_buffer[stream_read], length) != 0U)
        {
            stream_read = (uint16_t)(stream_read + length);
        }
        else
        {
            /* 校验失败只前移一个字节，避免漏掉包内的真包头。 */
            stream_read++;
        }
    }

    /* 把未消费的字节移到开头，避免读写位置一直增长。 */
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

把 9 节开头的断包例子放进这套代码走一遍，就能看清"状态"藏在哪。第一次回调送来 `AA 07 01`，第二次送来 `00 02 FF B3`：

| 阶段 | `stream_read` 之后剩余的字节 | 判断与动作 |
| --- | --- | --- |
| 第一次解析 | `AA 07 01` | `buffer[0]` 是 `0xAA`，不跳过；已有 3 字节 $\ge 2$，读出 `length = 7`；7 在 5..32 且是奇数，是合法候选；但 3 < 7，整包未到齐，`break` 等待 |
| 追加第二批 | `AA 07 01 00 02 FF B3` | 尾部整理没有丢字节，7 个字节在缓冲区里排齐 |
| 第二次解析 | 同上 | `length = 7` 合法，剩余 7 $\ge$ 7，收齐整包；`Packet_ProcessLedCommand()` 校验通过，`stream_read` 前移 7 |
| 收尾 | 空 | `stream_read == stream_write`，循环退出；尾部整理把读写位置都归零 |

结果是红灯熄灭、绿灯点亮：一包拆成两次回调，最终仍被当成一个完整帧执行。噪声例子 `37 99 AA 05 01 FF AF` 则相反——`37`、`99` 都不是 `0xAA`，各前移 1 字节后找到真正的包头，正常收包。这里能看出"校验失败只前移 1 字节"的意义：如果噪声里恰好嵌着一个真包头，按整块丢弃会把它一起扔掉；每次只前进 1 字节，才不漏掉任何可能的帧起点。

整个解析器的"状态机"并没有用显式的状态变量，而是由循环内的判断分支隐式表达：当前处于"找包头""等长度字段""等整包""校验并消费"四个阶段中的哪一个，完全由 `stream_read` 指向的内容和剩余字节数决定。读懂这张走查表，比背代码更能记住这套流程。

### 9.3 主循环中的所有权与重启顺序

```c
if (uart_error != 0U)
{
    uart_error = 0U;
    /* 错误可能丢字节，丢弃错误前的半包。 */
    stream_read = 0U;
    stream_write = 0U;
    UART3_RecoverFromRxError();
}

if (uart3_rx_ready != 0U)
{
    uint16_t received = uart3_rx_length;

    if (Stream_Append(uart3_rx_buffer, received) == 0U)
    {
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

顺序是"追加当前片段 -> 清接收状态 -> 重新启动 DMA -> 解析"，这样解析时 DMA 已经可以接收下一片段。`STREAM_BUFFER_SIZE` 为 128，而 `UART3_RX_BUFFER_SIZE` 为 64；当前单批数据在清空后可以重新追加。若未来单批数据大于流缓冲区，应扩大缓冲区或改成环形队列。

该模型能正确处理：一个包跨两次回调、两个包一次到达，以及非法长度或已收齐后校验失败的噪声。单缓冲区在主循环处理期间不能持续接收；校验失败不会执行 GPIO。

**蓝牙实验操作与预期。** 手机/电脑连接模块后发送 `AA 05 01 FF AF`，红灯应点亮；发送 `AA 07 01 00 02 FF B3`，红灯关闭、绿灯点亮；拆包、粘包和已收齐的非法噪声帧不会阻止后续合法包执行。把校验字节改错，LED 状态应保持不变；不完整噪声帧因缺少超时可能持续等待。当前链路不自动回显原包，也不发送 ACK。

## 10. 本章验收

- [ ] USART2/USART3 的引脚和波特率已记录；
- [ ] 轮询、中断和 DMA 接收方式能明确区分；
- [ ] ReceiveToIdle 的一次数据帧已捕获；
- [ ] 蓝牙协议的长度、校验和解析结果可复现；
- [ ] 能处理断包、粘包和噪声字节。

## 11. 按现象排错

| 现象 | 优先检查 |
| --- | --- |
| 完全收不到数据 | TX/RX 是否交叉、是否共地、USART 实例和引脚是否正确、TX/RX 电平是否兼容、模块供电、串口助手端口；再看 GPIO/USART/DMA 时钟是否开启。 |
| 收到乱码 | 两端波特率、8N1、系统/APB 时钟、3.3 V/5 V 电平、GND 和线路干扰；发送固定 `0x55` 或 `UUUU`，先用示波器/逻辑分析仪看位宽。 |
| 只有第一条命令有效 | 初始化后只启动了一轮；完成处理后是否再次调用 `HAL_UART_Receive_IT()`、`HAL_UART_Receive_DMA()` 或 `HAL_UARTEx_ReceiveToIdle_DMA()`。 |
| IT 回调不执行 | `USARTx_IRQHandler()` 是否调用 `HAL_UART_IRQHandler()`，USART IRQ 是否开启，回调名/参数是否正确，以及是否真的收满定长字节。 |
| DMA 回调不执行 | RX/TX 是否使用固定映射通道，DMA IRQ 是否开启，`DMA1_Channelx_IRQHandler()` 是否调用 `HAL_DMA_IRQHandler()`，`__HAL_LINKDMA` 是否关联，方向/自增/宽度是否正确。 |
| ReceiveToIdle 只有收满才回调 | 很可能只开了 DMA IRQ、没开 `USARTx global interrupt`；IDLE 短数据由 USART IRQ 处理。 |
| RxEvent 在半缓冲区提前执行 | 这是 `HAL_UART_RXEVENT_HT`，不一定是一包；回调内用 `HAL_UARTEx_GetRxEventType()` 查询，或每次启动后关闭 `DMA_IT_HT`。 |
| RxEvent 在缓冲区满时执行 | 这是正常的 `HAL_UART_RXEVENT_TC`；增大分块或使用流解析，不要把 TC 当成错误。 |
| 数据偶尔错位/校验失败 | 是否把 IDLE 强行当成包边界、Length 是否为整包长度、校验范围是否正确、DMA 是否在读取时覆盖同一数组、TX DMA 是否仍在读取被修改的数组，以及是否有 ORE/FE/NE。 |
| 重复启动返回 `HAL_BUSY` | 不要在 `while` 顶部无条件启动；确认上一轮已完成，错误后先 `HAL_UART_AbortReceive()`（必要时 `HAL_UART_DMAStop()`），再启动下一轮。 |
| 蓝牙能连接但无数据 | 模块是否处于透传状态、当前波特率、USART3 是否使用 PB10/PB11、主机是否打开接收通道、是否被其他主机占用，以及发送工具的文本/HEX 模式。 |

以最常见的"收到乱码"为例，把上面的表格展开成可执行的顺序：

1. 发送端改发固定的 `0x55`（HEX 模式），排除发送内容的偶然性，`0x55` 的位型是 `01010101`，示波器上最容易数出位宽；
2. 核对串口助手与 `.ioc` 的波特率是否同为 `115200`——两端各差一点不会报错，只会乱码；
3. 波特率确实一致仍乱码，回想第 3 章的时钟树：USART2 挂在 APB1（36 MHz），若改过系统时钟或 APB 分频而代码没有重新生成，波特率分频还是旧值，按 1.4 节重新核对 `BRR`；
4. 缩短杜邦线并确认两端共地，排除长线干扰和参考电平漂移。

沿实际信号链排查即可：`TX/RX/GND/电平 -> 波特率与时钟 -> IRQ/DMA 映射 -> 缓冲区与事件 -> 长度/校验 -> GPIO 输出`。

上一篇：[[07 DMA：数据搬运与 ADC 多通道采集]] ｜ 下一篇：[[09 I2C：总线时序与软件 I2C 驱动 OLED]]
