# 第 8 章 DMA 数据搬运

## 本章闭环

DMA 按固定规则在两个地址之间搬运数据，让 CPU 不必逐项执行读写。本章完成两个实验：

| 工程 | 数据路径 | 触发方式 |
| --- | --- | --- |
| `8-1 DMA数据转运` | `DataA[] -> DMA1_Channel1 -> DataB[]` | 存储器到存储器，软件启动 |
| `8-2 DMA+AD多通道` | `ADC1->DR -> DMA1_Channel1 -> AD_Value[]` | ADC 转换完成产生硬件请求 |

配置始终围绕六个问题展开：从哪里读、写到哪里、一次搬多宽、地址是否自增、搬多少次、由谁触发。理解这条主线后，存储器复制和 ADC 扫描只是两组不同参数。

## 1. DMA 简介

DMA 是 **Direct Memory Access**，即直接存储器访问（或直接存储器存取）。它是协助 CPU 搬运数据的外设，可以在不让 CPU 逐项参与的情况下完成：

- 外设寄存器 $leftrightarrow$ SRAM；
- Flash/SRAM $leftrightarrow$ SRAM（存储器到存储器）。

这里的“外设”通常指外设的数据寄存器（`DR`，Data Register），例如 `ADC1->DR`、串口数据寄存器；“存储器”通常指运行内存 SRAM 和程序存储器 Flash。搬运期间 CPU 可以处理别的任务。

STM32F103C8T6 只有 `DMA1`，包含 7 个通道；带有 DMA2 的型号才会额外拥有 DMA2 的 5 个通道。通道可以看作独立的数据通路：不同通道可分别配置不同的源地址、目的地址和触发源。

### 1.1 软件触发与硬件触发

- **软件触发**：适合 Flash/SRAM 之间的整批复制。启动后 DMA 尽快连续搬运，直到传输计数器减到 0。
- **硬件触发**：适合外设数据。外设在“一个数据准备好”的时刻发出 DMA 请求，DMA 响应一次、搬运一次。例如 ADC 转换完成、串口收到一个字节、定时器事件到来。

硬件触发源是“特定”的：每个外设请求连接到固定 DMA 通道，不能随意换通道。以 F103 为例，`ADC1` 的 DMA 请求连接到 `DMA1_Channel1`。

## 2. STM32 的存储器映射

DMA 访问的是地址。理解地址区间，才能理解“数组在哪”“寄存器在哪”以及 DMA 从哪里读、向哪里写。

![STM32 存储器映射](assets/ppt/slide-103.png)

### 2.1 ROM 与 RAM

STM32 的地址空间按用途可分为 ROM（掉电不丢失）和 RAM（掉电丢失）。主要区域如下：

| 区域 | 起始地址 | 作用 |
| --- | --- | --- |
| 主 Flash | `0x08000000` | 存放编译后的程序代码和常量 |
| 系统存储器 | `0x1FFFF000` 附近（具体边界以芯片手册为准） | 出厂 Bootloader，支持系统 Bootloader 下载 |
| 选项字节 | `0x1FFFF800` 附近（具体边界以芯片手册为准） | 写保护、看门狗等配置 |
| SRAM | `0x20000000` | 运行时变量、数组、结构体 |
| 外设寄存器 | `0x40000000` | GPIO、ADC、DMA 等外设寄存器 |
| 内核外设 | `0xE0000000` | NVIC、SysTick 等 Cortex-M3 内核外设 |

F103 的地址是 32 位，理论寻址空间为 4 GB；其中大量区间是保留地址。地址 `0x00000000` 是别名区，实际映射到 Flash、系统存储器或 SRAM，映射关系由 `BOOT0/BOOT1` 决定。

普通变量由编译器放入 SRAM，地址通常以 `0x2000...` 开头；`const` 修饰的只读数据通常放在 Flash，地址通常以 `0x0800...` 开头：

```c
uint8_t a = 0x66;          // 通常位于 SRAM，可读写
const uint8_t table[] = {  // 通常位于 Flash，只读
    0x01, 0x02, 0x03, 0x04
};
```

Flash 通过总线直接访问时只能读不能写，因此 DMA 的目的地址不能直接填写 Flash 区域。Flash 写入需要 Flash 接口控制器先擦除、再编程，这属于另一章内容。SRAM 可正常读写；外设寄存器是否可读写要以参考手册为准，数据寄存器通常是 DMA 的实际读写对象。

### 2.2 寄存器也是一种存储器

外设寄存器本质上也是映射到地址空间的一组存储单元。软件读写寄存器，就等于通过地址控制硬件电路：寄存器的位可能连接到引脚、开关、数据选择器或计数器。

标准库用“结构体 + 基地址”访问寄存器。例如 `ADC1` 是指向 ADC 外设结构体的指针，`ADC1->DR` 等价于“ADC1 基地址 + DR 偏移”。F103 中：

```c
// ADC1 基地址 0x40012400，DR 偏移 0x4C
// ADC1->DR 的实际地址为 0x4001244C
```

也可以直接用物理地址访问（实际工程优先使用库定义）：

```c
#define ADC1_DR_ADDR  ((uint32_t)0x4001244C)
uint32_t value = *(__IO uint32_t *)ADC1_DR_ADDR;
```

## 3. DMA 框图与工作参数

![DMA 基本结构](assets/ppt/slide-103.png)

DMA 与 CPU 都是总线矩阵的主动单元，可以访问右侧的 Flash、SRAM 和外设寄存器。DMA 自己的配置寄存器挂在 AHB 总线上，CPU 通过 AHB 写入这些寄存器；外设通过 DMA 请求线提供硬件触发。

DMA1 有 7 个通道，但 DMA 总线只有一条，多个通道需要分时复用。通道冲突由仲裁器按优先级处理；CPU 与 DMA 同时争用总线时，仲裁器会保证 CPU 仍能获得一定的总线带宽。

### 3.1 两个站点的三个参数

STM32 手册通常把 DMA 两端称为“外设站点”和“存储器站点”。它们各有三个参数：

1. **起始地址**：从哪里读、写到哪里；
2. **数据宽度**：一次搬运 8 位（Byte）、16 位（HalfWord）还是 32 位（Word）；
3. **地址是否自增**：一次搬运完成后，地址是否移动到下一个数据单元。

“外设站点”只是 DMA 结构中的名称，并不限制地址必须是寄存器。做 SRAM 到 SRAM 复制时，可以把源数组地址填到外设站点，把目标数组地址填到存储器站点；也可以反过来，同时反转方向参数。

![DMA 数据宽度与地址自增](assets/ppt/slide-105.png)

典型选择：

- 数组逐项复制：两端宽度相同，两端地址都自增；
- ADC 扫描：外设地址为 `ADC1->DR`，不自增；SRAM 数组地址自增；两端通常都用半字。

### 3.2 传输计数器与自动重装

传输计数器决定总共搬运多少个“数据单元”。每搬运一次，计数器减 1；减到 0 后，正常模式停止。

- `DMA_Mode_Normal`：搬运一轮后停止，适合一次数组复制或 ADC 单次扫描；
- `DMA_Mode_Circular`：计数器归零后自动恢复初值，适合 ADC 连续扫描。

地址在一轮传输结束时也会回到起始位置，便于循环模式开始下一轮。

### 3.3 触发、开关和启动条件

`DMA_M2M` 决定触发方式：

- `DMA_M2M_Enable`：存储器到存储器，使用软件触发；
- `DMA_M2M_Disable`：使用外设硬件请求触发。

启动一次传输必须同时满足三个条件：

1. 通道已使能（`DMA_Cmd(channel, ENABLE)`）；
2. 传输计数器大于 0；
3. 触发源已经产生请求。

正常模式传输完成后，若要再次启动，必须按手册要求执行：**先关闭 DMA，再写传输计数器，最后重新使能 DMA**。

### 3.4 DMA 请求与通道映射

![DMA 请求映射](assets/ppt/slide-107.png)

每个 DMA 通道都可由软件触发，也连接到一个或多个特定硬件请求。以 DMA1 为例，`DMA1_Channel1` 可响应 `ADC1` 请求；其他定时器、串口请求分别连接到各自规定的通道。使用硬件触发时，先查芯片参考手册的 DMA 请求映射表，再选择通道。

同一通道的硬件请求由对应外设的 DMA 输出使能函数打开，例如：

```c
ADC_DMACmd(ADC1, ENABLE);  // 打开 ADC1 -> DMA 的请求输出
```

通道优先级有 `VeryHigh`、`High`、`Medium`、`Low` 四级；只有多个通道同时工作时，优先级才明显影响仲裁。

### 3.5 数据宽度不一致时的对齐

两端宽度相同，数据按一个个数据单元正常搬运。宽度不一致时：

- 小宽度搬到大宽度：高位补 0；
- 大宽度搬到小宽度：高位被舍弃，只保留低位。

这与 C 语言中 `uint8_t`、`uint16_t`、`uint32_t` 之间赋值时的扩展和截断类似。若不希望出现隐式补零或截断，两个站点应选择相同的数据宽度。

## 4. 两个任务的参数推导

### 4.1 SRAM 数组 `DataA -> DataB`

任务：把 SRAM 中的 `DataA` 复制到 `DataB`。

![数组转运](assets/ppt/slide-106.png)

| 参数 | 配置 | 原因 |
| --- | --- | --- |
| 外设站点地址 | `DataA` 首地址 | 把 DataA 当作源 |
| 存储器站点地址 | `DataB` 首地址 | 把 DataB 当作目的地 |
| 两端宽度 | Byte | 数组元素是 `uint8_t` |
| 两端地址 | 都自增 | `A[0]->B[0]`、`A[1]->B[1]`… |
| 方向 | `DMA_DIR_PeripheralSRC` | 外设站点是源 |
| 传输次数 | 数组长度 | 每个字节搬一次 |
| 模式 | `DMA_Mode_Normal` | 只复制一轮 |
| 触发 | `DMA_M2M_Enable` | 不需要等待外设时机 |

### 4.2 ADC 扫描结果搬到数组

任务：ADC 扫描多个通道，每完成一个通道就把 `ADC1->DR` 搬到 `AD_Value[]`。

| 参数 | 配置 | 原因 |
| --- | --- | --- |
| 外设地址 | `&ADC1->DR` | 转换结果都从同一个寄存器读 |
| 存储器地址 | `AD_Value` 首地址 | 结果写入 SRAM 数组 |
| 外设地址 | 不自增 | 始终读取 DR |
| 存储器地址 | 自增 | 依次写入数组元素 |
| 两端宽度 | HalfWord | ADC 结果为 16 位 |
| 传输次数 | 通道数 | 每个通道搬运一次 |
| 触发 | 硬件触发 | 等 ADC 转换完成请求 |
| 模式 | 单次扫描用 Normal，连续扫描用 Circular | 与 ADC 工作模式配套 |

ADC 扫描模式中，转换结果反复写入同一个 `DR`，如果 CPU 不及时读出，前一个结果会被覆盖；DMA 正好在每次转换完成时把结果取走，因此 ADC + DMA 是最常见的组合。

## 5. 标准库配置链与手册定位

本节对应参考手册的两部分：

- 第 2 章“存储器和总线架构”：存储器映射、总线矩阵和外设地址；
- 第 10 章“DMA 控制器”：DMA 通道、请求映射、配置寄存器和标志位。

查某个寄存器地址时，先查外设基地址，再查寄存器偏移：

$$
\text{寄存器地址}=\text{外设基地址}+\text{寄存器偏移}
$$

例如 ADC1 基地址为 `0x40012400`，`DR` 偏移为 `0x4C`，所以 `ADC1->DR` 地址为 `0x4001244C`。

## 6. 实验一：`8-1 DMA数据转运`

### 6.1 建工程和验证地址

工程只需要 OLED 用于显示，DMA 搬运发生在芯片内部，不需要额外传感器。先复制 OLED 工程并命名为 `8-1 DMA数据转运`。

课堂先用一个小实验验证存储器映射：

```c
uint8_t a = 0x66;
OLED_ShowHexNum(1, 1, a, 2);
OLED_ShowHexNum(2, 1, (uint32_t)&a, 8);
```

下载后，`a` 的地址通常以 `0x2000...` 开头，说明变量位于 SRAM。加上 `const` 后：

```c
const uint8_t a = 0x66;
```

地址通常变为 `0x0800...`，说明常量被放在 Flash。字库、查找表等大量且不会改变的数据适合放在 Flash，以节省 SRAM。

外设寄存器地址固定。例如：

```c
OLED_ShowHexNum(3, 1, (uint32_t)&ADC1->DR, 8);
```

显示结果应为 `0x4001244C`。标准库通过结构体成员顺序映射寄存器；也可用物理地址指针直接访问，但实际代码优先使用库定义。

### 6.2 定义源数组和目的数组

```c
uint8_t DataA[] = {0x01, 0x02, 0x03, 0x04};
uint8_t DataB[4];
```

`DataA` 是源，`DataB` 是目的。数组名在表达式中会退化为首元素地址，因此调用初始化函数时可直接传入 `DataA` 和 `DataB`，再转换为 DMA 所需的 `uint32_t` 地址。

### 6.3 DMA 模块的初始化思路

在工程中添加 `MyDMA.c/.h` 模块，避免与库函数 `DMA_...` 重名。初始化步骤按课堂 PPT 的框图进行：

1. 开启 DMA1 时钟；
2. 配置外设站点和存储器站点的地址、宽度、自增；
3. 配置传输方向、传输次数、传输模式、触发方式和优先级；
4. 把结构体参数写入指定通道；
5. 使能 DMA 通道。

若使用硬件触发，还要在对应外设中打开 DMA 请求输出；若使用 DMA 中断，则还需 `DMA_ITConfig`、NVIC 和中断函数。本节先用轮询完成标志，不展开中断。

### 6.4 第一次搬运：初始化后立即执行

```c
#include "stm32f10x.h"

void MyDMA_Init(uint32_t AddrA, uint32_t AddrB, uint16_t Size)
{
    DMA_InitTypeDef DMA_InitStructure;

    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_DMA1, ENABLE);

    DMA_InitStructure.DMA_PeripheralBaseAddr = AddrA;
    DMA_InitStructure.DMA_PeripheralDataSize = DMA_PeripheralDataSize_Byte;
    DMA_InitStructure.DMA_PeripheralInc = DMA_PeripheralInc_Enable;
    DMA_InitStructure.DMA_MemoryBaseAddr = AddrB;
    DMA_InitStructure.DMA_MemoryDataSize = DMA_MemoryDataSize_Byte;
    DMA_InitStructure.DMA_MemoryInc = DMA_MemoryInc_Enable;
    DMA_InitStructure.DMA_DIR = DMA_DIR_PeripheralSRC;
    DMA_InitStructure.DMA_BufferSize = Size;
    DMA_InitStructure.DMA_Mode = DMA_Mode_Normal;
    DMA_InitStructure.DMA_M2M = DMA_M2M_Enable;
    DMA_InitStructure.DMA_Priority = DMA_Priority_Medium;

    DMA_Init(DMA1_Channel1, &DMA_InitStructure);
    DMA_Cmd(DMA1_Channel1, ENABLE);
}
```

这里把 `DataA` 放在“外设站点”只是沿用库结构体的命名；实际它是 SRAM 地址。`DMA_M2M_Enable` 选择软件触发，`DMA_Mode_Normal` 让计数器归零后停止。

主函数中调用：

```c
MyDMA_Init((uint32_t)DataA, (uint32_t)DataB, 4);
```

使能通道后，DMA 立即把 4 个字节从 `DataA` 复制到 `DataB`，源数组内容不变。

### 6.5 为什么第二次不能直接启动

正常模式完成后，传输计数器已经为 0，通道虽然仍配置着，但不会再搬运。重新启动必须先关闭通道，再写入计数器，最后重新打开：

```c
static uint16_t MyDMA_Size;

void MyDMA_Init(uint32_t AddrA, uint32_t AddrB, uint16_t Size)
{
    /* 前面的时钟和 DMA_InitStructure 配置不变 */
    MyDMA_Size = Size;
    DMA_Init(DMA1_Channel1, &DMA_InitStructure);
    DMA_Cmd(DMA1_Channel1, DISABLE);
}

void MyDMA_Transfer(void)
{
    DMA_Cmd(DMA1_Channel1, DISABLE);
    DMA_SetCurrDataCounter(DMA1_Channel1, MyDMA_Size);
    DMA_ClearFlag(DMA1_FLAG_TC1);
    DMA_Cmd(DMA1_Channel1, ENABLE);

    while (DMA_GetFlagStatus(DMA1_FLAG_TC1) == RESET) {
    }
    DMA_ClearFlag(DMA1_FLAG_TC1);
}
```

初始化时先 `DISABLE`，由 `MyDMA_Transfer()` 决定何时开始，便于在主循环中观察搬运前后的数据。`DMA_SetCurrDataCounter()` 只能在通道关闭后调用，这是第二次传输不启动时首先检查的地方。

### 6.6 主循环与实验现象

```c
while (1)
{
    DataA[0]++;
    DataA[1]++;
    DataA[2]++;
    DataA[3]++;

    OLED_ShowHexNum(1, 1, DataA[0], 2);
    OLED_ShowHexNum(1, 4, DataA[1], 2);
    OLED_ShowHexNum(1, 7, DataA[2], 2);
    OLED_ShowHexNum(1, 10, DataA[3], 2);
    OLED_ShowHexNum(2, 1, DataB[0], 2);
    OLED_ShowHexNum(2, 4, DataB[1], 2);
    OLED_ShowHexNum(2, 7, DataB[2], 2);
    OLED_ShowHexNum(2, 10, DataB[3], 2);
    Delay_ms(1000);

    MyDMA_Transfer();

    OLED_ShowHexNum(3, 1, DataA[0], 2);
    OLED_ShowHexNum(3, 4, DataA[1], 2);
    OLED_ShowHexNum(3, 7, DataA[2], 2);
    OLED_ShowHexNum(3, 10, DataA[3], 2);
    OLED_ShowHexNum(4, 1, DataB[0], 2);
    OLED_ShowHexNum(4, 4, DataB[1], 2);
    OLED_ShowHexNum(4, 7, DataB[2], 2);
    OLED_ShowHexNum(4, 10, DataB[3], 2);
    Delay_ms(1000);
}
```

课堂调试时还显示两个数组的地址：普通 SRAM 数组通常在 `0x2000...`。若把源数组定义为 `const`，它会位于 Flash（`0x0800...`），可以验证 Flash 到 SRAM 的 DMA 复制；此时不能再对 `DataA` 做 `++`。

## 7. 实验二：ADC 扫描 + DMA

### 7.1 从 ADC 多通道工程改造

复制上一节 ADC 多通道工程，命名为 `8-2 DMA+AD多通道`。保留 `PA0`～`PA3` 的接线和 OLED 显示，增加 DMA 初始化及结果数组。

先定义数组并在头文件声明：

```c
uint16_t AD_Value[4];
// MyDMA.h 或 ADC.h
extern uint16_t AD_Value[4];
```

### 7.2 配置 ADC 扫描四个通道

四个通道分别放入规则组序列 1～4；序列号与通道号的对应关系决定数组中结果的顺序：

```c
ADC_RegularChannelConfig(ADC1, ADC_Channel_0, 1, ADC_SampleTime_55Cycles5);
ADC_RegularChannelConfig(ADC1, ADC_Channel_1, 2, ADC_SampleTime_55Cycles5);
ADC_RegularChannelConfig(ADC1, ADC_Channel_2, 3, ADC_SampleTime_55Cycles5);
ADC_RegularChannelConfig(ADC1, ADC_Channel_3, 4, ADC_SampleTime_55Cycles5);

ADC_InitStructure.ADC_ScanConvMode = ENABLE;
ADC_InitStructure.ADC_NbrOfChannel = 4;
```

单次扫描时，启动一次 ADC 就转换四个通道后停止；连续扫描时，四个通道会不断重复转换。

### 7.3 配置 `DMA1_Channel1`

ADC1 的 DMA 请求固定连接到 `DMA1_Channel1`，不能改用其他通道。关键配置如下：

```c
DMA_InitTypeDef DMA_InitStructure;

RCC_AHBPeriphClockCmd(RCC_AHBPeriph_DMA1, ENABLE);

DMA_InitStructure.DMA_PeripheralBaseAddr = (uint32_t)&ADC1->DR;
DMA_InitStructure.DMA_PeripheralDataSize = DMA_PeripheralDataSize_HalfWord;
DMA_InitStructure.DMA_PeripheralInc = DMA_PeripheralInc_Disable;
DMA_InitStructure.DMA_MemoryBaseAddr = (uint32_t)AD_Value;
DMA_InitStructure.DMA_MemoryDataSize = DMA_MemoryDataSize_HalfWord;
DMA_InitStructure.DMA_MemoryInc = DMA_MemoryInc_Enable;
DMA_InitStructure.DMA_DIR = DMA_DIR_PeripheralSRC;
DMA_InitStructure.DMA_BufferSize = 4;
DMA_InitStructure.DMA_Mode = DMA_Mode_Normal;     // 单次扫描
DMA_InitStructure.DMA_M2M = DMA_M2M_Disable;      // 硬件触发
DMA_InitStructure.DMA_Priority = DMA_Priority_Medium;

DMA_Init(DMA1_Channel1, &DMA_InitStructure);
DMA_Cmd(DMA1_Channel1, ENABLE);
ADC_DMACmd(ADC1, ENABLE);                         // 打开 ADC DMA 请求
```

外设端固定读取 `ADC1->DR`，所以不自增；SRAM 端每写入一个半字就自增，避免四个结果互相覆盖。ADC 结果是 16 位，因此两端都选 `HalfWord`。

### 7.4 单次扫描 + 单次 DMA

单次模式下，每次启动 ADC 前都要重新装载 DMA 传输计数器：

```c
void AD_GetValue(void)
{
    DMA_Cmd(DMA1_Channel1, DISABLE);
    DMA_SetCurrDataCounter(DMA1_Channel1, 4);
    DMA_ClearFlag(DMA1_FLAG_TC1);
    DMA_Cmd(DMA1_Channel1, ENABLE);

    ADC_SoftwareStartConvCmd(ADC1, ENABLE);
    while (DMA_GetFlagStatus(DMA1_FLAG_TC1) == RESET) {
    }
    DMA_ClearFlag(DMA1_FLAG_TC1);
}
```

调用 `AD_GetValue()` 后，ADC 依次完成四个通道，DMA 将结果写入 `AD_Value[0]`～`AD_Value[3]`。主循环只需显示数组：

```c
AD_GetValue();
OLED_ShowNum(1, 1, AD_Value[0], 4);
OLED_ShowNum(2, 1, AD_Value[1], 4);
OLED_ShowNum(3, 1, AD_Value[2], 4);
OLED_ShowNum(4, 1, AD_Value[3], 4);
```

### 7.5 连续扫描 + 循环 DMA

如果把 ADC 改为连续转换、DMA 改为循环模式，并在初始化末尾启动 ADC：

```c
ADC_InitStructure.ADC_ContinuousConvMode = ENABLE;
DMA_InitStructure.DMA_Mode = DMA_Mode_Circular;

DMA_Init(DMA1_Channel1, &DMA_InitStructure);
DMA_Cmd(DMA1_Channel1, ENABLE);
ADC_DMACmd(ADC1, ENABLE);
ADC_SoftwareStartConvCmd(ADC1, ENABLE);
```

ADC 会连续扫描四个通道，DMA 在每轮结束后自动重装计数器，把最新结果持续刷新到 `AD_Value[]`。此时不需要 `AD_GetValue()`，主循环随时读取数组即可。

这里的硬件自动化体现了 STM32 的外设互联：定时器可以触发 ADC，ADC 转换完成可以触发 DMA，DMA 再把结果写入 SRAM，CPU 只在需要时读取结果。

## 8. 验收与排错

1. **完全没有搬运**：先查 DMA 时钟、通道映射、`DMA_Cmd` 是否使能，以及硬件触发外设的 DMA 请求是否打开。
2. **只有第一个数组元素变化**：检查目的地址是否设置了 `DMA_MemoryInc_Enable`。
3. **ADC 四个值错位**：检查 `ADC_RegularChannelConfig` 的序列号和数组索引是否一致。
4. **数值像字节拼错**：检查两端数据宽度；ADC 通常应使用 `HalfWord`。
5. **第二次正常模式不启动**：确认顺序是 `DISABLE -> DMA_SetCurrDataCounter -> ENABLE`，并清除了传输完成标志。
6. **数组数据偶尔新旧混合**：CPU 读取数组时 DMA 可能仍在更新。低速入门实验可接受；需要一致快照时，应使用传输完成/半传输中断或在明确边界复制数据。

## 本章小结

DMA 不是会“思考”的算法，而是按照固定规则重复执行“读一个地址、写另一个地址”：

> 地址、数据宽度、地址自增、传输次数、触发时机、通道与优先级。

存储器到存储器复制通常使用软件触发和正常模式；ADC 扫描通常使用外设到存储器、外设地址不自增、存储器地址自增、半字宽度和硬件触发。掌握这组参数，DMA 的配置就可以从框图逐项推导出来。

本节还没有展开“存储器到外设”的完整工程。串口发送一批数据就是典型应用，配置方法与本章的两个站点和触发逻辑相同，可在学习串口 DMA 时继续扩展。
