# STM32 HAL 库 UART 串口教学文档

## 1. 学完以后能做什么

完成本文后，你应该能够：

- 解释 UART 串口的 `TX`、`RX`、数据帧和波特率。
- 说明 UART 与 USART 的区别，并理解为什么入门实验通常使用异步模式。
- 在 CubeMX 中配置 `USART1`、`PA9/PA10` 和 `115200 8N1`。
- 看懂 CubeMX 生成的 `huart1` 串口句柄和初始化函数。
- 使用 `HAL_UART_Transmit()` 向电脑发送字节、数组和字符串。
- 使用 `HAL_UART_Receive()` 接收命令，并控制 `PC13` 板载 LED。
- 使用 `HAL_UART_Transmit_IT()`、`HAL_UART_Receive_IT()` 和完成回调实现非阻塞收发。
- 配置 USART1 TX/RX DMA，并理解 Normal 模式、传输事件和缓冲区所有权。
- 使用一个接收缓冲区和 `HAL_UARTEx_ReceiveToIdle_DMA()` 完成入门级不定长接收。
- 使用 BT24 蓝牙串口透传模块完成无线回显，并理解“蓝牙链路”和“UART 链路”的边界。
- 设计带帧头、总长度、指令内容和校验和的数据包，在主循环中校验并解析 RGB LED 控制命令。
- 根据串口参数、接线、事件类型、缓冲区状态和返回值定位常见问题。

## 2. 实验准备

### 2.1 硬件

- STM32F103C8T6 最小系统板或兼容开发板。
- ST-Link 或其他兼容的调试下载器。
- USB 转 TTL 串口模块。
- BT24 蓝牙串口透传模块（第 12 节使用）。
- USB 数据线、杜邦线和开发板配套器件。

USB 转 TTL 模块的逻辑电平必须与开发板兼容，具体电压范围以模块和开发板资料为准。调试器和 USB 转 TTL 模块可以同时连接电脑，但它们承担的工作不同：调试器负责下载和调试，USB 转 TTL 模块负责把串口信号转换为电脑可以识别的 USB 串口。

### 2.2 TTL 电平边界

板级资料中常说的“TTL 串口”，通常指没有经过 RS-232 或 RS-485 收发器的单端数字串口。在 STM32F103 开发板上，信号通常以 3.3 V CMOS 逻辑工作：低电平接近 `0 V`，高电平接近 `3.3 V`。

不要因为 USB 转 TTL 模块标有“TTL”就默认其 `TXD` 输出为 3.3 V，或默认 STM32 的所有输入都能直接承受 5 V。外设 `TXD` 接到 STM32 `RX` 前，应检查模块输出电平、目标引脚的容限条件和开发板原理图；不能确认时，使用电平转换或选择 3.3 V 逻辑模块。

### 2.3 软件

- STM32CubeMX。
- MDK-ARM（Keil）。
- 串口调试助手。
- 支持 BLE 串口透传的电脑或安卓调试工具（第 12 节使用）。

串口调试助手的具体界面可能不同，但必须能够选择串口号、波特率、数据位、校验位、停止位，并切换 ASCII 与十六进制显示或发送格式。

## 3. UART 串口基础

### 3.1 TX 和 RX

串口最基本的异步通信需要两条信号线：

| 信号 | 全称 | 作用 |
| --- | --- | --- |
| `TX` | Transmit | 发送数据 |
| `RX` | Receive | 接收数据 |

通信双方的发送端要连接到对方的接收端，因此接线必须交叉：

```text
STM32 USART1_TX (PA9)  ->  USB-TTL RXD
STM32 USART1_RX (PA10) <-  USB-TTL TXD
STM32 GND               --- USB-TTL GND
```

只连接 `TX` 或 `RX`，或者把 `TX` 对 `TX`、`RX` 对 `RX`，都不能完成正常的双向通信。双方还必须共享信号参考地。

UART 是单端信号，接收端判断的是“信号线相对于本地 `GND` 的电压”。如果两台设备没有连接 `GND`，两端的电平参考就不一致，轻则出现乱码或丢字节，重则完全无法通信。因此排线时应把 `GND` 与 `TX/RX` 同等对待。

### 3.2 UART 与 USART

- **UART**：Universal Asynchronous Receiver/Transmitter，通用异步收发器，只支持异步通信。
- **USART**：Universal Synchronous/Asynchronous Receiver/Transmitter，通用同步/异步收发器，既支持异步模式，也支持同步模式。

异步模式不需要单独的时钟线，通常使用 `TX` 和 `RX` 两条线。同步模式还会增加时钟线 `CK`，但入门串口实验一般不使用它。本文使用 `USART1` 的异步模式。

### 3.3 数据帧

串口不是直接把一串电平无边界地发送出去，而是按数据帧传输。一个常见数据帧由以下部分组成：

```text
空闲高电平 -> 起始位 -> 数据位 -> 可选校验位（由配置决定） -> 停止位 -> 空闲高电平
```

- **空闲状态**：数据线通常保持高电平。
- **起始位**：发送方把数据线拉低，告诉接收方一帧数据开始了。
- **数据位**：实际传输的二进制数据，常用 8 位。
- **校验位**：可选，用于进行简单的奇偶校验。
- **停止位**：数据线保持高电平，表示当前帧结束。

在常见的 8 位、无校验、1 位停止位配置中，简称 `8N1`：

- `8`：8 位数据位。
- `N`：No parity，不使用校验位。
- `1`：1 位停止位。

### 3.4 数据位和低位先传

串口常见的数据位传输顺序是低位在前（LSB first）。例如十进制 `100` 的 8 位二进制表示为：

```text
100 = 01100100
```

实际发送数据位时，顺序为最低位到最高位：

```text
0、0、1、0、0、1、1、0
```

接收端按照相同的数据帧格式采样这些电平，重新组合成一个字节。

### 3.5 校验位

校验位不是额外传输一整字节数据，而是根据数据位中 `1` 的数量生成一个检查位。常见方式有：

- **奇校验**：数据位和校验位中的 `1` 总数为奇数。
- **偶校验**：数据位和校验位中的 `1` 总数为偶数。
- **无校验**：不传输校验位，数据位全部用于有效数据。

校验只能帮助发现一部分传输错误，不能替代完整的通信协议。收发双方必须选择相同的校验方式；一方选择 `None`、另一方选择 `Even`，接收到的内容就会异常。

### 3.6 停止位

停止位用于标记一帧数据的结束，常见配置为 1 位。某些串口外设还支持 0.5、1.5 或 2 位停止位，但入门实验通常使用 1 位。

### 3.7 波特率

波特率表示每秒传输多少个 bit。例如：

- `9600`：每秒传输 9600 bit，每 bit 约需要 `1/9600` 秒。
- `115200`：每秒传输 115200 bit，每 bit 约需要 `8.68 us`。

波特率越高，单位时间内可以传输的 bit 越多，但对时钟误差、线路质量和收发双方配置的一致性要求也更高。最重要的规则是：**收发双方的波特率、数据位、校验位和停止位必须一致。**

实际波特率由串口外设时钟分频得到。高波特率下若频繁出现乱码或帧错误，除了检查参数是否一致，还应检查 CubeMX 的时钟树和实际时钟源是否符合开发板硬件。外部晶振可用时通常比内部 RC 振荡器更稳定；但具体是否能使用外部晶振，必须以开发板电路和时钟配置为准。

本文两个实验统一使用：

```text
波特率：115200
数据位：8
校验位：None
停止位：1
数据方向：Receive and Transmit
```

## 4. 使用 CubeMX 配置 USART1

### 4.1 新建工程

1. 打开 STM32CubeMX。
2. 选择 `File -> New Project`。
3. 输入并选择目标芯片，例如 `STM32F103C8T6`。
4. 点击 `Start Project` 进入芯片配置界面。

### 4.2 保留 SWD 调试接口

在左侧选择：

```text
System Core -> SYS -> Debug -> Serial Wire
```

这样可以保留 ST-Link 使用的 SWD 调试功能。除非你明确知道自己在做什么，不要随意关闭调试接口。

### 4.3 启用 USART1 异步模式

在左侧选择：

```text
Connectivity -> USART1 -> Mode -> Asynchronous
```

启用后，CubeMX 通常会自动把 USART1 的默认引脚分配为：

| 引脚 | 功能 |
| --- | --- |
| `PA9` | `USART1_TX` |
| `PA10` | `USART1_RX` |

在 `GPIO` 配置页中可以看到，`PA9` 被配置为串口复用输出，`PA10` 被配置为串口输入。这里先保持 CubeMX 的默认配置；若使用不同芯片、重映射功能或其他封装，应重新核对引脚分配。

### 4.4 设置串口参数

在 `USART1` 的参数页中设置：

| CubeMX 选项 | 本文设置 | 含义 |
| --- | --- | --- |
| `Baud Rate` | `115200` | 波特率 |
| `Word Length` | `8 Bits` | 数据位长度 |
| `Parity` | `None` | 不使用校验位 |
| `Stop Bits` | `1` | 1 位停止位 |
| `Data Direction` | `Receive and Transmit` | 收发双向 |
| `Hardware Flow Control` | `None` | 不使用硬件流控 |

串口调试助手必须使用完全相同的参数。硬件流控未接线时应保持关闭，否则串口可能因为等待流控信号而无法正常工作。

### 4.5 配置 PC13 板载 LED

接收实验使用开发板上的板载 LED。常见最小系统板把它连接到 `PC13`，并采用低电平有效的开漏接法，但最终仍要以开发板原理图为准。

在 CubeMX 中：

1. 在芯片图中点击 `PC13`，选择 `GPIO_Output`。
2. 进入 `System Core -> GPIO`。
3. 将模式设置为 `Output Open Drain`。
4. 初始输出电平设置为高电平，使低有效 LED 默认熄灭。
5. 输出速度选择低速档位，例如 `2 MHz`。

低有效 LED 的控制关系通常是：

| `PC13` 输出 | LED 状态 |
| --- | --- |
| 低电平 | 点亮 |
| 高电平 | 熄灭 |

如果你的开发板 LED 是高电平有效，必须按实际原理图调整代码中的 `SET` 和 `RESET`。

### 4.6 生成 MDK-ARM 工程

进入 `Project Manager`：

1. 设置工程名和保存路径。
2. 在工具链选项中选择 `MDK-ARM`。
3. 点击 `Generate Code`。
4. 点击 `Open Project`，用 Keil 打开工程。

CubeMX 会生成 GPIO 和 USART 初始化代码。常见函数包括：

```c
MX_GPIO_Init();
MX_USART1_UART_Init();
```

同时，CubeMX 会生成 USART1 的句柄：

```c
UART_HandleTypeDef huart1;
```

句柄中保存了 USART1 相关的配置和运行状态。入门阶段只需要记住：调用 HAL 串口 API 时，要把 `&huart1` 作为串口句柄参数传入。

应用代码应放在 `USER CODE BEGIN` 和 `USER CODE END` 标记之间，避免重新生成 CubeMX 代码时被覆盖。

## 5. HAL 串口发送 API

### 5.1 函数原型

阻塞式发送接口为：

```c
HAL_StatusTypeDef HAL_UART_Transmit(
    UART_HandleTypeDef *huart,
    const uint8_t *pData,
    uint16_t Size,
    uint32_t Timeout
);
```

四个参数分别是：

| 参数 | 作用 |
| --- | --- |
| `huart` | 串口句柄指针，例如 `&huart1` |
| `pData` | 待发送数据缓冲区的首地址 |
| `Size` | 要发送的字节数 |
| `Timeout` | 超时时间，单位为毫秒 |

`Size` 的单位是字节。对于 ASCII 字符串，它通常等于有效字符数，但不包含末尾的 `\0`。发送一个字节就填 `1`，发送长度为 5 的数组就填 `5`。

### 5.2 `uint8_t` 与发送缓冲区

HAL 接口常使用定长整数类型：

| 类型 | 含义 | 常见范围 |
| --- | --- | --- |
| `int8_t` | 有符号 8 位整数 | `-128` 到 `127` |
| `uint8_t` | 无符号 8 位整数 | `0` 到 `255` |
| `int16_t` | 有符号 16 位整数 | `-32768` 到 `32767` |
| `uint16_t` | 无符号 16 位整数 | `0` 到 `65535` |
| `uint32_t` | 无符号 32 位整数 | 由 32 位无符号整数范围决定 |

串口发送的数据本质上是字节序列，因此单字节变量、字节数组和字符串都可以作为发送缓冲区。对于字符数组，必要时可以转换为 `uint8_t *`。

### 5.3 超时与返回值

例如：

```c
HAL_UART_Transmit(&huart1, &data, 1, 10);
```

这里的 `10` 表示最多等待 10 ms。如果在规定时间内没有完成发送，函数会返回超时状态。

入门实验通常希望函数一直等待到发送完成，可以使用：

```c
HAL_MAX_DELAY
```

返回值类型是 `HAL_StatusTypeDef`，常见状态包括：

- `HAL_OK`：操作成功。
- `HAL_ERROR`：发生错误。
- `HAL_BUSY`：串口当前正被占用。
- `HAL_TIMEOUT`：等待超时。

如果需要判断发送是否成功，应检查返回值，而不是只调用函数后忽略结果。

## 6. 实验一：单片机向电脑发送数据

### 6.1 实验目标

使用 USART1 依次向电脑发送：

1. 一个字节 `0x5A`。
2. 内容为 `12345` 的 5 个字节数组。
3. 一个字符 `a`。
4. 字符串 `Hello world`。

### 6.2 串口调试助手设置

1. 将 USB 转 TTL 模块插入电脑。
2. 在设备管理器或串口调试助手中确认新增的 COM 口。
3. 如果电脑上存在多个串口，可先拔出 USB 转 TTL 模块，记录消失的端口，再插回去，新增的端口就是目标端口。
4. 设置 `115200`、`8` 位数据、无校验、1 位停止位、无硬件流控。
5. 先打开串口，等待程序下载完成。

### 6.3 发送代码

将下面代码放在 `main.c` 中。注意代码涉及两个不同的 `USER CODE` 区域，不能整块塞进同一处：

- `#include <string.h>` 这一行放在 `USER CODE BEGIN Includes` / `USER CODE END Includes` 之间（文件顶部）
- 其余代码放在 `USER CODE BEGIN 2` / `USER CODE END 2` 之间（外设初始化完成之后）

这样 CubeMX 重新生成代码时才不会丢失这两部分，也不会产生嵌套标记。位置放对了，代码会在初始化后发送一次，而不是在 `while (1)` 中不停刷屏：

```c
/* USER CODE BEGIN Includes */
#include <string.h>
/* USER CODE END Includes */

/* USER CODE BEGIN 2 */
uint8_t byteNumber = 0x5A;
uint8_t byteArray[] = "12345";
uint8_t charA = 'a';
char message[] = "Hello world";

HAL_UART_Transmit(&huart1, &byteNumber, 1, HAL_MAX_DELAY);
HAL_UART_Transmit(&huart1, byteArray, 5, HAL_MAX_DELAY);
HAL_UART_Transmit(&huart1, &charA, 1, HAL_MAX_DELAY);
HAL_UART_Transmit(
    &huart1,
    (uint8_t *)message,
    (uint16_t)strlen(message),
    HAL_MAX_DELAY
);
/* USER CODE END 2 */
```

说明：

- `0x5A` 是一个字节，因此长度参数为 `1`。
- `byteArray` 的内容是 5 个字符，长度参数为 `5`。
- `message` 是以 `\0` 结尾的 C 字符串，`strlen()` 返回有效字符数，不包含末尾的 `\0`。
- 若希望最后换行，可以把字符串改成 `"Hello world\r\n"`，同时由 `strlen()` 自动计算新长度。

### 6.4 查看实验结果

如果发送 `0x5A`，串口助手应切换到十六进制接收模式；如果查看 `12345`、`a` 和 `Hello world`，可以切换到 ASCII 模式。

发送代码放在 `USER CODE BEGIN 2` 后只执行一次。若把它放在 `while (1)` 中，单片机会不断重复发送，串口窗口会快速滚动，这是代码位置导致的正常现象。

### 6.5 编译与调试

1. 编译工程，确认没有 error 和 warning。
2. 通过 ST-Link 下载程序。
3. 复位单片机。
4. 打开串口调试助手，观察接收窗口。

调试单步执行时，可以先用十六进制模式观察 `0x5A`，再切换到 ASCII 模式观察字符和字符串。若使用 Keil 断点调试，调试优化等级过高可能使单步行为不直观，可暂时把 C/C++ 优化设置为 `Level 0`，验证完成后再按项目需求恢复。

## 7. HAL 串口接收 API

### 7.1 函数原型

阻塞式接收接口为：

```c
HAL_StatusTypeDef HAL_UART_Receive(
    UART_HandleTypeDef *huart,
    uint8_t *pData,
    uint16_t Size,
    uint32_t Timeout
);
```

参数含义与发送接口相似：

| 参数 | 作用 |
| --- | --- |
| `huart` | 串口句柄指针，例如 `&huart1` |
| `pData` | 接收缓冲区首地址，函数把收到的数据写入这里 |
| `Size` | 期望接收的字节数 |
| `Timeout` | 超时时间，单位为毫秒 |

### 7.2 接收一个字节

```c
uint8_t dataRcvd;

HAL_StatusTypeDef status = HAL_UART_Receive(
    &huart1,
    &dataRcvd,
    1,
    HAL_MAX_DELAY
);
```

这里把 `dataRcvd` 的地址传给 `pData`，函数收到 1 个字节后才返回。使用 `HAL_MAX_DELAY` 时，如果电脑没有发送数据，程序会一直等待在这个调用处。

### 7.3 接收多个字节

一次接收 10 个字节，可以准备长度为 10 的数组：

```c
uint8_t buffer[10];

HAL_UART_Receive(
    &huart1,
    buffer,
    10,
    HAL_MAX_DELAY
);
```

函数只有在收到足够数量的数据，或者发生错误、忙状态、超时后才会返回。因此 `Size` 的选择必须和发送端实际发送的协议长度一致；如果发送端只发 1 个字节，而接收端等待 10 个字节，程序就会继续等待剩余数据。

### 7.4 检查返回值

推荐至少在调试阶段检查接收结果：

```c
if (HAL_UART_Receive(&huart1, &dataRcvd, 1, 1000) == HAL_OK)
{
    // 收到一个完整字节
}
else
{
    // 发生错误、串口忙或接收超时
}
```

使用 `HAL_MAX_DELAY` 的简单实验可以省略超时分支，但实际项目应根据任务需求决定是否使用有限超时，并处理非 `HAL_OK` 返回值。

## 8. 实验二：通过串口命令控制板载 LED

### 8.1 实验目标

电脑通过 USB 转 TTL 模块发送 ASCII 字符：

| 收到的数据 | 操作 |
| --- | --- |
| `'1'` | 点亮板载 LED |
| `'0'` | 熄灭板载 LED |

注意：字符 `'1'` 和数值 `1` 不是同一个概念。串口助手选择 ASCII 发送时，发送的是字符编码；程序中应比较 `'1'` 和 `'0'`，不要写成数值 `1` 和 `0`。

### 8.2 CubeMX 与接线

USART1 和 PC13 的配置沿用前文：

```text
STM32 PA9  (USART1_TX) -> USB-TTL RXD
STM32 PA10 (USART1_RX) <- USB-TTL TXD
STM32 GND              --- USB-TTL GND
```

`PC13` 配置为板载 LED 对应的 GPIO 输出模式。若开发板采用低电平点亮，则初始化输出高电平，避免复位后 LED 默认亮起。

### 8.3 接收控制代码

将代码放入 `while (1)` 的用户代码区域：

```c
/* USER CODE BEGIN 2 */
uint8_t dataRcvd;
/* USER CODE END 2 */

/* USER CODE BEGIN WHILE */
while (1)
{
    if (HAL_UART_Receive(&huart1, &dataRcvd, 1, HAL_MAX_DELAY) == HAL_OK)
    {
        if (dataRcvd == '0')
        {
            // PC13 低有效：输出高电平，LED 熄灭
            HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
        }
        else if (dataRcvd == '1')
        {
            // PC13 低有效：输出低电平，LED 点亮
            HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
        }
    }
}
/* USER CODE END WHILE */
```

程序运行过程如下：

1. `HAL_UART_Receive()` 等待电脑发来 1 个字节。
2. 收到数据后，函数把字节写入 `dataRcvd`。
3. 程序判断它是否为字符 `'0'` 或 `'1'`。
4. 根据命令写入 `PC13`。
5. 循环回到接收位置，等待下一条命令。

### 8.4 下载和验证

1. 编译工程并下载到单片机。
2. 按下复位按钮。
3. 在串口调试助手中选择 ASCII 发送模式。
4. 发送字符 `1`，观察 LED 是否点亮。
5. 发送字符 `0`，观察 LED 是否熄灭。

如果 LED 的亮灭逻辑与预期相反，先确认开发板原理图；若 LED 是高电平有效，只需交换两个 `HAL_GPIO_WritePin()` 调用中的 `GPIO_PIN_SET` 和 `GPIO_PIN_RESET`。

## 9. UART 中断模式

阻塞式 `HAL_UART_Receive()` 在数据到齐前不会返回。对简单命令实验，这种写法最直观；但主循环还有显示、控制或计算任务时，长时间等待会拖住整个程序。

中断模式把“启动接收”和“接收完成后的处理”分开：

```text
主程序调用 HAL_UART_Receive_IT()
-> 函数立即返回，主循环继续运行
-> USART 收到指定数量的数据
-> USART1_IRQHandler()
-> HAL_UART_IRQHandler()
-> HAL_UART_RxCpltCallback()
```

### 9.1 CubeMX 配置

在原有 `USART1` 异步模式配置上，进入 `NVIC Settings`，勾选：

```text
USART1 global interrupt
```

CubeMX 会在中断文件中生成 `USART1_IRQHandler()`。用户代码不需要改写 HAL 内部判断，只需调用启动函数并实现弱回调。

### 9.2 中断发送与接收 API

```c
HAL_UART_Transmit_IT(&huart1, txData, txSize);
HAL_UART_Receive_IT(&huart1, rxData, rxSize);
```

它们与阻塞式 API 相比去掉了 `Timeout`：调用只负责启动传输，真正完成要等后续中断。缓冲区在完成回调之前必须一直有效，也不能被随意改写。

### 9.3 实验：接收命令时主循环继续闪灯

定义一个接收字节和闪灯间隔：

```c
static uint8_t uart_rx_byte;
static volatile uint32_t blink_interval = 1000U;
```

初始化完成后、进入 `while (1)` 前，只启动一次接收：

```c
if (HAL_UART_Receive_IT(&huart1, &uart_rx_byte, 1U) != HAL_OK)
{
    Error_Handler();
}
```

接收完成后，HAL 调用：

```c
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART1)
    {
        return;
    }

    if (uart_rx_byte == '1')
    {
        blink_interval = 1000U;
    }
    else if (uart_rx_byte == '2')
    {
        blink_interval = 300U;
    }
    else if (uart_rx_byte == '3')
    {
        blink_interval = 50U;
    }

    (void)HAL_UART_Receive_IT(&huart1, &uart_rx_byte, 1U);
}
```

最后一行负责开启下一次接收。`HAL_UART_Receive_IT()` 的 Normal 接收只完成一轮；漏掉重新启动后，程序只能响应第一个字节。也不要在 `while (1)` 中无条件反复调用启动函数，否则上一轮尚未结束时会不断得到 `HAL_BUSY`。

主循环仍然可以按 `blink_interval` 执行闪灯或其他任务。对应的主循环写法为：

```c
while (1)
{
    HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
    HAL_Delay(blink_interval);
}
```

`blink_interval` 声明为 `volatile`，是因为它会被中断回调改写、又被主循环读取。更严格的工程会让回调只置标志，再由主循环解析命令；本例只处理一个字节，保留这种直接写法便于观察链路。

### 9.4 发送完成与错误回调

常见回调还包括：

```c
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart);
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart);
```

`TxCplt` 表示发送缓冲区可以再次使用；错误回调可记录错误并请求主循环恢复。工程中每个弱回调只能有一个全局实现，使用多个 UART 时应根据 `huart->Instance` 分流。

## 10. UART 场景中的 DMA

### 10.1 轮询、中断和 DMA 怎么选

阻塞式接口适合最小验证，但 CPU 会在函数内部等待。中断式接口不必持续轮询，不过每个字节仍由 CPU 参与搬运。DMA 则让硬件在 USART 数据寄存器和内存之间自动传输：

```text
CPU：配置方向、地址、宽度和长度
DMA：按 USART 请求搬运数据
CPU：在完成、错误或空闲事件后处理结果
```

| 方式 | CPU 介入粒度 | 优点 | 典型场景 |
| --- | --- | --- | --- |
| 阻塞轮询 | 整个等待和搬运过程 | 代码直观 | 少量调试输出、最小实验 |
| 中断 | 每个事件或字节 | 不必持续等待 | 低速命令、小数据量通信 |
| DMA | 启动、边界和错误 | CPU 负担低 | 连续或批量收发 |

DMA 不能提高 UART 波特率。它改变的是“谁搬数据”，不是串口线上每 bit 的持续时间。数据很少时，配置 DMA、处理中断和管理缓冲区的成本可能高于直接调用阻塞接口。

### 10.2 STM32F103 的固定通道映射

STM32F103 使用固定 DMA 请求映射，USART1 常用通道为：

| 请求 | DMA 通道 | 方向 |
| --- | --- | --- |
| USART1_TX | DMA1 Channel4 | Memory to Peripheral |
| USART1_RX | DMA1 Channel5 | Peripheral to Memory |

这里的 Channel 不是串口引脚，而是一套独立搬运状态机。同一个 DMA 通道不能同时承担两项传输，项目增加其他外设时应在 CubeMX 中检查冲突。

### 10.3 UART DMA 的宽度、模式和地址规则

UART 数据寄存器地址固定，因此外设地址自增关闭；内存数组需要依次读写，因此内存地址自增开启。本文按字节收发，外设和内存数据宽度均设为 Byte。

TX 和本节的 RX 都使用 Normal 模式：

```text
启动 -> 搬运 N 个字节 -> TC 完成 -> 停止
```

Normal 模式完成后不会自动开始下一轮。TX 需要在有新消息时重新启动，RX 则要在接收事件后重新调用接收接口。本文不使用 Circular RX，因为它需要额外管理当前位置、回绕和环形缓冲区读写索引。

### 10.4 CubeMX 配置

在前文 USART1 配置基础上：

1. 在 USART1 的 DMA Settings 中添加 TX 和 RX。
2. TX 使用 DMA1 Channel4，Memory to Peripheral，Byte，Normal，优先级 Low。
3. RX 使用 DMA1 Channel5，Peripheral to Memory，Byte，Normal，优先级 Medium。
4. 两者都关闭外设地址自增、开启内存地址自增。
5. 在 NVIC 中使能 USART1 global interrupt、DMA1 Channel4 和 DMA1 Channel5 中断。

USART1 global interrupt 不能省略。ReceiveToIdle 的 IDLE 事件来自 USART 外设，不是 DMA TC 中断。CubeMX 生成的 MSP 初始化还应通过 `__HAL_LINKDMA()` 把 `huart1` 与 TX/RX DMA 句柄关联，应用层不需要重复链接。

### 10.5 最小 DMA 收发

DMA API 与中断 API 的参数形式很接近：

```c
static uint8_t tx_message[] = "hello DMA\r\n";
static uint8_t rx_fixed[8];

HAL_UART_Transmit_DMA(&huart1, tx_message, sizeof(tx_message) - 1U);
HAL_UART_Receive_DMA(&huart1, rx_fixed, sizeof(rx_fixed));
```

两次调用都会立即返回。DMA 在内存与 USART 数据寄存器之间搬运数据，完成后再通过 DMA 中断进入 HAL 回调。

- HT：已搬运缓冲区的一半。
- TC：本轮全部传输完成。
- TE：DMA 访问或配置出错。

`tx_message` 在 `HAL_UART_TxCpltCallback()` 之前仍可能被 DMA 读取，不能提前改写。`rx_fixed` 只有在收满 8 字节后才算完成；长度不确定时，应改用下一节的 ReceiveToIdle。

### 10.6 连续数值输出的带宽预算

`115200 8N1` 发送一个数据字节通常需要 1 个起始位、8 个数据位和 1 个停止位，共 10 bit。若每个采样点格式化后平均占 6 字节，纯线速时间约为：

$$
t_{UART}\approx\frac{6\times10}{115200}
\approx0.52\ \mathrm{ms}
$$

以 `1 kHz` 输出时，线路预算只剩约 `0.48 ms`，还没有计入格式化、其他中断和任务。连续数据输出应根据总字节率选择以下策略：

- 低频少量数据：阻塞发送最简单。
- CPU 不能等待：使用 TX DMA，并在完成回调后复用缓冲区。
- 多个短样本：先批量编码，再一次发送，减少启动开销。
- 显示或日志不需要每个样本：降低输出频率，但保持底层采样频率不变。
- 必须无损保存高速数据：计算完整吞吐量并设计队列或环形缓冲区，不能只把阻塞接口替换成 DMA 就认为问题已经解决。

## 11. ReceiveToIdle DMA 不定长接收

### 11.1 定长 DMA 接收的限制

最直接的 UART DMA 接收接口是：

```c
HAL_UART_Receive_DMA(&huart1, buffer, length);
```

它适合协议已经规定固定长度的场景。例如接收长度设为 64，而电脑只发送 `hello` 这 5 个字节，接口会继续等待剩余 59 个字节。

USART 接收线在超过一个数据帧时间没有新数据时，可以产生 IDLE 空闲事件。HAL 把 DMA 和 IDLE 组合为：

```c
HAL_UARTEx_ReceiveToIdle_DMA(&huart1, buffer, max_size);
```

第三个参数是缓冲区容量，即本轮最多接收多少字节，不是要求对方发送的固定帧长。本文使用 Normal 模式，回调参数 `Size` 表示当前有效数据长度。若当前 HAL 包没有这个接口，应升级对应 STM32CubeF1 固件包；手工实现 IDLE 中断属于另一套方案。

### 11.2 入门工程只保留一个接收缓冲区

先做一个“收到一段数据，主循环把它原样发回”的最小闭环：

```c
#define UART_RX_BUFFER_SIZE 64U

static uint8_t uart_rx_buffer[UART_RX_BUFFER_SIZE];
static volatile uint16_t uart_rx_size = 0U;
static volatile uint8_t uart_rx_ready = 0U;
```

初始化完成后启动第一轮接收，并关闭本实验不需要的半传输通知：

```c
if (HAL_UARTEx_ReceiveToIdle_DMA(
        &huart1,
        uart_rx_buffer,
        sizeof(uart_rx_buffer)) != HAL_OK)
{
    Error_Handler();
}

__HAL_DMA_DISABLE_IT(huart1.hdmarx, DMA_IT_HT);
```

### 11.3 回调只交接本轮长度

```c
void HAL_UARTEx_RxEventCallback(
    UART_HandleTypeDef *huart,
    uint16_t Size)
{
    if ((huart->Instance == USART1) &&
        (Size > 0U) &&
        (Size <= sizeof(uart_rx_buffer)))
    {
        uart_rx_size = Size;
        uart_rx_ready = 1U;
    }
}
```

这里不在回调中打印、等待或执行复杂协议，只把有效长度交给主循环。Normal 模式在 IDLE 或缓冲区填满后结束本轮接收，因此缓冲区在重新启动前不会继续被 DMA 改写。

### 11.4 主循环处理后重新接收

```c
while (1)
{
    if (uart_rx_ready != 0U)
    {
        uint16_t size = uart_rx_size;
        uart_rx_ready = 0U;

        /* 入门回显：阻塞发送发生在主循环，不占用中断回调。 */
        (void)HAL_UART_Transmit(
            &huart1,
            uart_rx_buffer,
            size,
            100U);

        if (HAL_UARTEx_ReceiveToIdle_DMA(
                &huart1,
                uart_rx_buffer,
                sizeof(uart_rx_buffer)) != HAL_OK)
        {
            Error_Handler();
        }

        __HAL_DMA_DISABLE_IT(huart1.hdmarx, DMA_IT_HT);
    }
}
```

在串口助手发送 `hello DMA`，应收到相同内容。每次重新调用 ReceiveToIdle 后，都要再次关闭 HT，因为 HAL 可能在重新启动时恢复对应中断。

这个例子故意只用一个缓冲区：主循环处理期间暂停接收，结构清楚，但这段时间到来的数据会丢失。高吞吐、连续接收或全双工场景才需要双缓冲、环形缓冲区或队列，不应把这些结构提前塞进入门实验。

### 11.5 IDLE 不等于协议分帧

IDLE 只能说明串口线上暂时没有新字节，不能保证这一段数据就是一个完整协议包：

- 一个协议包中间出现较长间隔，可能被拆成两次回调。
- 两个协议包连续发送且中间没有足够空闲，可能在一次回调中粘在一起。
- 缓冲区填满会产生 TC，即使协议包还没有结束。

可靠协议仍需根据帧头、长度字段、分隔符或校验规则解析字节流。ReceiveToIdle 只负责把本轮收到的字节安全交给应用层。

## 12. 蓝牙串口透传与简易数据包解析

### 12.1 BT24 解决了什么问题

蓝牙常见形态包括经典蓝牙和低功耗蓝牙（Bluetooth Low Energy，BLE）。经典蓝牙常用于持续传输音频等数据，BLE 更适合低功耗、间歇通信的传感器和控制设备。

BLE 原生通信会涉及广播、扫描、连接，以及 GAP、GATT、Service、Characteristic 等概念。BT24 这类蓝牙串口透传模块已经处理了这些蓝牙协议细节，对 STM32 暴露的仍是一组普通 UART 引脚：

```text
手机或电脑发送 BLE 数据
  -> BT24 接收蓝牙数据
  -> BT24 从 UART_TX 原样输出
  -> STM32 USART3_RX 接收

STM32 USART3_TX 发送
  -> BT24 UART_RX 接收
  -> BT24 原样转成 BLE 数据
  -> 手机或电脑收到
```

“透传”表示模块尽量原样转发负载，不表示数据天然带有消息边界。STM32 看到的仍是连续字节流；需要区分多条命令时，应用层必须自行设计数据包格式。

蓝牙连接通常由两个角色配合完成：BT24 作为从设备/外设持续广播，手机或电脑作为主设备/中心设备扫描并发起连接。连接建立后，双方才能交换数据。

### 12.2 接线与电平

课程配套学习板为蓝牙模块引出了 `USART3_TX`、`USART3_RX`、`5V` 和 `GND`。接线规则仍然是 TX 与 RX 交叉、双方共地：

```text
STM32 USART3_TX  ->  BT24 RX
STM32 USART3_RX  <-  BT24 TX
学习板 5V        ->  BT24 VCC
学习板 GND       --- BT24 GND
```

这里的 `5V` 是课程配套 BT24 模块板的供电接法，不等于其 UART 信号也是 5 V。若使用不同厂家或不同版本的模块，应先核对模块的供电范围、UART 逻辑电平和引脚顺序，再接到 STM32；不能仅凭外观或“BT24”名称推断。

### 12.3 CubeMX 配置 USART3

在新工程中完成以下配置：

1. 将 `USART3` 设为 Asynchronous。
2. 按课程配套 BT24 的默认参数设置为 `9600 8N1`，关闭硬件流控。若模块参数已修改，以模块当前配置为准。
3. 为 `USART3_RX` 添加 DMA，数据宽度设为 Byte，内存地址自增，模式设为 Normal。
4. 在 NVIC 中使能 `USART3 global interrupt` 和对应 DMA 通道中断。
5. 若不使用 DMA 发送，TX 无需添加 DMA；阻塞式发送已经足够完成本节低速实验。
6. 把三色 LED 对应 GPIO 配置为推挽输出，并设置便于阅读的用户标签，例如 `LED_R`、`LED_G`、`LED_B`。

在常见 STM32F103 映射中，`USART3_TX` 使用 `PB10`、`USART3_RX` 使用 `PB11`，RX 对应 `DMA1 Channel3`。最终引脚和 DMA 映射必须以当前芯片封装、CubeMX 冲突检查和生成结果为准。

### 12.4 先完成无线回显

先不要急着解析命令。沿用第 11 节的 ReceiveToIdle 单缓冲区结构，只把串口句柄换成 `huart3`：

```c
#define BT_RX_BUFFER_SIZE 64U

static uint8_t bt_rx_buffer[BT_RX_BUFFER_SIZE];
static volatile uint16_t bt_rx_size = 0U;
static volatile uint8_t bt_rx_ready = 0U;
```

初始化完成后启动接收：

```c
if (HAL_UARTEx_ReceiveToIdle_DMA(
        &huart3,
        bt_rx_buffer,
        sizeof(bt_rx_buffer)) != HAL_OK)
{
    Error_Handler();
}

__HAL_DMA_DISABLE_IT(huart3.hdmarx, DMA_IT_HT);
```

回调仍然只交接长度：

```c
void HAL_UARTEx_RxEventCallback(
    UART_HandleTypeDef *huart,
    uint16_t Size)
{
    if ((huart->Instance == USART3) &&
        (Size > 0U) &&
        (Size <= sizeof(bt_rx_buffer)))
    {
        bt_rx_size = Size;
        bt_rx_ready = 1U;
    }
}
```

若第 11 节的 USART1 实验与本节放在同一个工程中，只保留一个 `HAL_UARTEx_RxEventCallback()`，在函数内分别判断 `USART1` 和 `USART3`，不能重复定义同名回调。

主循环检测到一轮数据后，把这段数据原样发回 BT24，再重新启动接收：

```c
if (bt_rx_ready != 0U)
{
    uint16_t size = bt_rx_size;
    bt_rx_ready = 0U;

    (void)HAL_UART_Transmit(
        &huart3,
        bt_rx_buffer,
        size,
        100U);

    if (HAL_UARTEx_ReceiveToIdle_DMA(
            &huart3,
            bt_rx_buffer,
            sizeof(bt_rx_buffer)) != HAL_OK)
    {
        Error_Handler();
    }

    __HAL_DMA_DISABLE_IT(huart3.hdmarx, DMA_IT_HT);
}
```

电脑有 BLE 功能时，可以在支持 BLE 串口透传的调试助手中扫描模块，例如带蓝牙模式的“波特律动串口助手”；安卓手机也可以使用模块厂商提供的简易透传工具。`nRF Connect` 能查看更完整的广播、Service 和 Characteristic 信息，功能更专业，但只做本节透传实验时不必先掌握全部 GATT 操作。课程配套 BT24 的默认广播名称为 `BT24`。连接后发送任意字节，若收到完全相同的数据，无线回显链路就已打通：

```text
调试工具 -> BLE -> BT24 -> USART3 RX -> STM32
STM32 -> USART3 TX -> BT24 -> BLE -> 调试工具
```

### 12.5 定义 RGB LED 控制数据包

无线回显只能证明链路可用。为了让 STM32 判断一条命令从哪里开始、总共有多长、内容是否基本完整，规定如下二进制数据包：

| 字段 | 长度 | 本节约定 |
| --- | ---: | --- |
| 帧头 | 1 字节 | 固定为 `0xAA` |
| 总长度 | 1 字节 | 从帧头到校验和的全部字节数 |
| 指令内容 | $2n$ 字节 | 每两个字节组成“LED 编号 + 状态” |
| 校验和 | 1 字节 | 前面所有字节累加后保留低 8 位 |

LED 编号和状态定义为：

| 字节值 | 含义 |
| --- | --- |
| `0x01` | 红色 LED |
| `0x02` | 绿色 LED |
| `0x03` | 蓝色 LED |
| `0x00` | 熄灭 |
| `0xFF` | 点亮 |

例如，只点亮红灯：

```text
AA 05 01 FF AF
|  |  |  |  +-- 校验和：(AA + 05 + 01 + FF) & FF = AF
|  |  +--+----- 红灯，点亮
|  +----------- 总长度 5 字节
+-------------- 帧头
```

同时熄灭红灯、点亮绿灯：

```text
AA 07 01 00 02 FF B3
```

其校验和为：

$$
(\mathrm{0xAA}+\mathrm{0x07}+\mathrm{0x01}+\mathrm{0x00}
+\mathrm{0x02}+\mathrm{0xFF})\bmod 256=\mathrm{0xB3}
$$

调试工具必须使用十六进制发送。ASCII 字符串 `AA 05 01 FF AF` 和五个原始字节 `0xAA 0x05 0x01 0xFF 0xAF` 不是同一组数据。

### 12.6 校验与解析代码

先校验完整数据包，再执行 GPIO 操作。这样可以避免一个包的前半部分已经改变 LED，后半部分才发现非法值。

```c
static uint8_t BluetoothPacket_IsValid(
    const uint8_t *packet,
    uint16_t length)
{
    uint16_t i;
    uint8_t sum = 0U;

    if ((length < 5U) ||
        (length > 255U) ||
        (packet[0] != 0xAAU) ||
        (packet[1] != (uint8_t)length) ||
        (((length - 3U) % 2U) != 0U))
    {
        return 0U;
    }

    for (i = 0U; i < (length - 1U); i++)
    {
        sum = (uint8_t)(sum + packet[i]);
    }

    if (sum != packet[length - 1U])
    {
        return 0U;
    }

    for (i = 2U; i < (length - 1U); i += 2U)
    {
        uint8_t led = packet[i];
        uint8_t state = packet[i + 1U];

        if ((led < 0x01U) ||
            (led > 0x03U) ||
            ((state != 0x00U) && (state != 0xFFU)))
        {
            return 0U;
        }
    }

    return 1U;
}
```

确认数据包有效后，按两个字节一组执行命令。下面假设三色 LED 低电平点亮；`LED_R_GPIO_Port` 等名称来自 CubeMX 用户标签。若当前开发板为高电平点亮，应交换 `GPIO_PIN_RESET` 与 `GPIO_PIN_SET`。

```c
static void RgbLed_Write(uint8_t led, uint8_t state)
{
    GPIO_PinState pin_state =
        (state == 0xFFU) ? GPIO_PIN_RESET : GPIO_PIN_SET;

    switch (led)
    {
        case 0x01U:
            HAL_GPIO_WritePin(
                LED_R_GPIO_Port,
                LED_R_Pin,
                pin_state);
            break;

        case 0x02U:
            HAL_GPIO_WritePin(
                LED_G_GPIO_Port,
                LED_G_Pin,
                pin_state);
            break;

        case 0x03U:
            HAL_GPIO_WritePin(
                LED_B_GPIO_Port,
                LED_B_Pin,
                pin_state);
            break;

        default:
            break;
    }
}

static void BluetoothPacket_Execute(
    const uint8_t *packet,
    uint16_t length)
{
    uint16_t i;

    for (i = 2U; i < (length - 1U); i += 2U)
    {
        RgbLed_Write(packet[i], packet[i + 1U]);
    }
}
```

把无线回显处替换为数据包处理，处理结束后仍按第 12.4 节的代码重新启动 ReceiveToIdle：

```c
if (bt_rx_ready != 0U)
{
    uint16_t size = bt_rx_size;
    bt_rx_ready = 0U;

    if (BluetoothPacket_IsValid(bt_rx_buffer, size) != 0U)
    {
        BluetoothPacket_Execute(bt_rx_buffer, size);
    }

    if (HAL_UARTEx_ReceiveToIdle_DMA(
            &huart3,
            bt_rx_buffer,
            sizeof(bt_rx_buffer)) != HAL_OK)
    {
        Error_Handler();
    }

    __HAL_DMA_DISABLE_IT(huart3.hdmarx, DMA_IT_HT);
}
```

这个校验和只能发现一部分传输错误，不具备 CRC 那样的检错能力，也不提供身份认证或防篡改能力。校验和不相等时数据一定不符合本协议；校验和相等只表示通过了这项简单检查，不能证明数据绝对没有出错。

### 12.7 测试顺序

按从链路到协议的顺序验证，出现问题时更容易定位：

1. 扫描并连接默认名称为 `BT24` 的模块。
2. 发送任意短数据，确认无线回显内容和长度完全一致。
3. 切换到十六进制发送，发送 `AA 05 01 FF AF`，确认红灯点亮。
4. 发送 `AA 07 01 00 02 FF B3`，确认红灯熄灭、绿灯点亮。
5. 故意修改最后一个字节，确认校验失败后 LED 状态不变。
6. 故意修改长度字段或 LED 编号，确认非法数据包不会被执行。

调试助手若支持发送前自动追加校验和，例如波特律动串口助手的校验功能，可以选择 8 位累加和算法；应先确认它的计算范围是“从帧头到指令内容”，且只追加低 8 位，避免工具规则与本节协议不一致。

### 12.8 从简易解析走向字节流解析

上面的最小代码假设一次 RxEvent 恰好交付一个完整数据包，适合手动发送、包间隔较大的入门实验。发送频率升高后，这个假设可能被打破：一个包可能拆成多段，多个包也可能粘在一起。

更可靠的工程应让中断/DMA 只负责收集字节，再由主循环中的环形缓冲区或状态机按以下顺序解析：

```text
寻找 0xAA 帧头
  -> 读取并检查长度范围
  -> 缓冲区不足一整帧时继续等待
  -> 收齐后检查校验和与指令字段
  -> 执行并消费一整帧
  -> 校验失败时丢弃一个字节，重新寻找帧头
```

这条边界很重要：ReceiveToIdle 负责提高“不定长接收”的便利性，帧头、长度和校验规则才负责协议分帧。数据包解析、GPIO 控制、日志输出等工作应尽量放在主循环或任务中，不要堆进 UART 中断回调。


## 13. 常见问题排查

不要在无法通信时同时修改接线、波特率和程序。按“物理层 -> 配置层 -> 逻辑层”逐层排查，才能知道问题真正出现在哪一段：

| 层级 | 首先检查什么 |
| --- | --- |
| 物理层 | `TX/RX` 是否交叉、是否共地、电平是否兼容、USB 转 TTL 模块是否被识别 |
| 配置层 | COM 口、`115200 8N1`、硬件流控、CubeMX 引脚分配与时钟配置 |
| 逻辑层 | 代码是否已下载、HAL API 是否被执行、缓冲区长度和字符判断是否正确 |

### 13.1 串口助手找不到目标 COM 口

- 重新拔插 USB 转 TTL 模块。
- 对比插拔前后的 COM 口列表。
- 确认驱动安装正常。
- 检查串口是否已经被其他软件占用。

### 13.2 完全收不到数据

按以下顺序检查：

1. `TX` 和 `RX` 是否交叉连接。
2. STM32 与 USB 转 TTL 是否共地。
3. USB 转 TTL 的电平是否与开发板兼容。
4. 串口助手是否打开了正确的 COM 口。
5. 两端是否都是 `115200 8N1`。
6. 接收实验是否选择了 ASCII 发送模式。
7. `USART1` 是否确实分配到了 `PA9/PA10`。
8. 程序是否已经成功编译、下载并复位。

如果仍无法定位，可以先做 USB 转 TTL 模块的本机回环：暂时把模块自身的 `TXD` 与 `RXD` 短接，在串口助手中发送字符。若能收到自己发出的内容，说明电脑、驱动、COM 口和 USB 转 TTL 模块基本正常；再拆除短接，继续检查 STM32 的发送链路和接收链路。具备示波器或逻辑分析仪时，可先观察 `TX` 空闲电平和发送波形，再回到软件配置。

### 13.3 收到乱码

乱码通常优先检查串口参数：波特率、数据位、校验位和停止位必须完全一致。还要区分显示格式：字节 `0x5A` 在十六进制模式下显示为 `5A`，在 ASCII 模式下对应字符 `Z`；显示模式不同，不代表单片机发送的数据不同。

### 13.4 接收程序像“卡住”

如果代码使用：

```c
HAL_UART_Receive(&huart1, &dataRcvd, 1, HAL_MAX_DELAY);
```

那么程序没有收到 1 个字节之前会一直等待，这是阻塞式接收的预期行为。调试时可以把超时改成有限值，例如 `1000` ms，并检查返回值；如果后续任务不能被长时间阻塞，可以改用中断或 DMA 接收。

### 13.5 LED 不亮或亮灭相反

- `PC13` 是否真的连接到板载 LED。
- LED 是高电平有效还是低电平有效。
- GPIO 模式是否与电路连接方式匹配。
- 初始化输出电平是否符合“默认熄灭”的预期。

不要只根据网上常见开发板的经验判断有效电平，应以当前开发板的原理图为准。

### 13.6 ReceiveToIdle 没有回调

按以下链路检查：

```text
USART1 是否收到字节
  -> USART1 global interrupt 是否使能
  -> DMA1 Channel5 是否配置并使能 IRQ
  -> HAL_UARTEx_ReceiveToIdle_DMA 是否返回 HAL_OK
  -> huart1.hdmarx 是否由 __HAL_LINKDMA 关联
  -> RxEvent 回调是否判断了正确的 USART 实例
```

### 13.7 只能收到第一段或短消息一直不返回

- ReceiveToIdle 使用 Normal 模式，每次事件后是否重新启动接收。
- 是否误用了只在收满固定长度后完成的 `HAL_UART_Receive_DMA()`。
- USART1 IDLE 中断是否真正进入。
- 接收缓冲区是否过大，而当前接口又不是 ReceiveToIdle。

### 13.8 回调在半长位置提前执行

检查每次调用 `HAL_UARTEx_ReceiveToIdle_DMA()` 后是否重新执行：

```c
__HAL_DMA_DISABLE_IT(huart1.hdmarx, DMA_IT_HT);
```

若应用本来就需要流式半缓冲处理，可以保留 HT；本文的一段数据整体交接方案则主动关闭它。

### 13.9 发送损坏、`HAL_BUSY` 或连续数据丢失

- `HAL_UART_Transmit_DMA()` 返回 `HAL_OK` 后，是否在 TX 完成回调前修改了发送数组。
- 同方向上一次传输是否仍在运行。
- ReceiveToIdle 的单缓冲区是否在主循环处理完以前被重新交给 DMA。
- 实际一次接收的数据量是否超过 `UART_RX_BUFFER_SIZE`。
- 入门单缓冲区方案暂停接收期间，对方是否仍在连续发送。

### 13.10 数据粘包或拆包

一次 RxEvent 只代表 IDLE 或缓冲区满，不代表应用协议帧。应在应用层维护字节流解析器，根据帧头、长度、分隔符和校验判断完整消息。

### 13.11 扫描不到 BT24

- 确认手机或电脑的蓝牙已经开启，并授予调试工具所需的“附近设备”或定位权限。
- BT24 是否已经正常供电并处于广播状态；等待过久时可以按模块复位键重新广播。
- 模块是否已经连接到另一台电脑或手机；调试前先断开原连接。
- 扫描名称是否被 AT 命令修改过，不要只按默认名称 `BT24` 查找。
- 使用电脑调试时，先确认电脑硬件和驱动确实支持 BLE，而不只是经典蓝牙。

### 13.12 蓝牙已连接但命令无效

- `USART3` 和 BT24 是否使用相同波特率与 `8N1` 参数。
- `TX/RX` 是否交叉，是否共地，模块 UART 电平是否兼容。
- 调试工具是否使用十六进制发送，而不是把 `AA` 当作两个 ASCII 字符。
- 长度字段是否包含帧头、长度本身、指令和最后的校验和。
- 校验和计算范围与字节顺序是否一致，是否只保留累加结果的低 8 位。
- 手机和电脑不要同时占用同一个 BT24 连接；切换调试端前先断开或复位模块。

## 14. 复习清单

### 14.1 串口配置口诀

```text
先看 TX/RX，接线要交叉；
再对齐 8N1，波特率双方相同；
发送看缓冲区和字节数；
接收看缓冲区、长度和超时；
DMA 看方向、宽度、通道和所有权。
```

### 14.2 必须记住的 API

```c
HAL_UART_Transmit(&huart1, pData, Size, Timeout);
HAL_UART_Receive(&huart1, pData, Size, Timeout);
HAL_UART_Transmit_IT(&huart1, pData, Size);
HAL_UART_Receive_IT(&huart1, pData, Size);
HAL_UART_Transmit_DMA(&huart1, pData, Size);
HAL_UARTEx_ReceiveToIdle_DMA(&huart1, pData, MaxSize);
```

### 14.3 阻塞式命令链路

```text
电脑串口助手
    -> USB 转 TTL
    -> TX/RX 交叉接线
    -> USART1(PA9/PA10)
    -> HAL_UART_Receive()
    -> 字符判断
    -> HAL_GPIO_WritePin()
    -> PC13 板载 LED
```

只要沿着这条链路逐段验证，就能把“没有反应”拆分成具体问题：输入有没有发出、线路有没有到达、HAL 有没有收到、判断条件是否匹配、GPIO 电平是否正确。

### 14.4 中断与 DMA 链路

```text
电脑发送
  -> USART1 RX / IDLE
  -> DMA1 Channel5 写 uart_rx_buffer
  -> RxEvent 回调记录 Size 与 ready
  -> 主循环处理或回显
  -> 重新开启 ReceiveToIdle
```

最重要的原则是：缓冲区交给 DMA 后不要改写；主循环处理完成后再把同一缓冲区交回 DMA。这个单缓冲区闭环最适合先理解流程。

### 14.5 蓝牙数据包链路

```text
手机或电脑
  -> BLE 连接 BT24
  -> USART3 + ReceiveToIdle DMA
  -> 回调交接 Size
  -> 主循环检查 AA 帧头与总长度
  -> 计算并比较 8 位累加和
  -> 按“LED 编号 + 状态”两字节一组执行
  -> 重新开启 ReceiveToIdle
```

这条链路中，BT24 只负责 BLE 与 UART 之间的透传；STM32 应用层负责协议分帧、合法性校验和实际控制逻辑。手动低速测试可以暂时把一次 RxEvent 当成一个包，连续通信必须改用能够处理拆包、粘包和重新同步的字节流解析器。
