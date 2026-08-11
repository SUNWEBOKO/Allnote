# STM32 HAL库 SPI教学文档


> STM32 作为 SPI 主机，通过 W25Q64 读写数据，并完成 LED 状态掉电保存。

## 1. 学习目标

学完本文，你应该能掌握 6 件事：

1. 说清 SPI 的 4 根线分别做什么。
2. 理解 SPI 为什么是“时钟驱动的全双工通信”。
3. 理解主从两端必须统一的 5 个参数。
4. 会在 STM32CubeMX 里把 `SPI1` 配成主机模式。
5. 会使用 HAL 的 3 个 SPI 核心接口。
6. 理解 W25Q64 的读、写、擦除流程，以及驱动为什么要按固定顺序执行。

## 2. SPI 总线到底是什么

SPI，`Serial Peripheral Interface`，即串行外设接口。它是一种同步串行通信总线，常用于 MCU 和板级外设之间的高速、短距离通信。

常见应用包括：

- 外部 Flash
- 传感器
- ADC / DAC
- 显示屏
- 摄像头等高速模块

它的典型特点有 4 个：

- 由主机发起通信
- 由主机提供时钟
- 发送和接收可以同时发生
- 接线简单，但一主多从时每个从机都要独立片选

## 3. SPI 的 4 根线

标准 SPI 通常有 4 根关键信号线：

| 信号线 | 全称 | 相对主机方向 | 作用 |
| --- | --- | --- | --- |
| `MOSI` | `Master Output Slave Input` | 主机输出 | 主发从收 |
| `MISO` | `Master Input Slave Output` | 主机输入 | 主收从发 |
| `SCK` | `Serial Clock` | 主机输出 | 主机提供时钟 |
| `NSS/CS` | `Slave Select / Chip Select` | 主机输出 | 片选，通常低电平有效 |

### 3.1 接线规则

如果 STM32 作为主机，多个外设作为从机，那么接线规律是：

- 主机 `MOSI` 接所有从机 `MOSI`
- 主机 `MISO` 接所有从机 `MISO`
- 主机 `SCK` 接所有从机 `SCK`
- 每个从机单独占一根 `NSS/CS`

也就是说：

- `MOSI`、`MISO`、`SCK` 是共享总线
- `CS` 不是共享总线

主机想和谁通信，就把谁的 `CS` 拉低。

### 3.2 为什么 SPI 是全双工

SPI 最关键的一句话是：

> 只要时钟在走，发送和接收就同时发生。

例如主机发送 1 个字节时：

- `MOSI` 上送出 8 位数据
- `MISO` 上也会同步返回 8 位数据

因此：

- 发送时，主机其实也在接收，只是收到的数据可能不用
- 接收时，主机也必须发送一些占位数据来换时钟

这也是很多初学者容易误解的地方。所谓 `HAL_SPI_Receive()` 并不意味着“主机什么都不发”，它只是“用户只关心收到什么”。

## 4. SPI 通信前必须对齐的 5 个参数

主机和从机如果参数不一致，通信就会错位、错码，甚至完全无响应。

### 4.1 波特率

SPI 每个时钟周期传输 1 位，因此 `SCK` 的频率越高，通信速度越快。

选波特率时通常看 3 个限制：

1. 外设手册允许的最高频率
2. 板级连线和电气质量能承受的频率
3. 当前实验的稳定性优先级

例如用面包板和杜邦线做实验时，不要一上来就追高频率。先从 `1 MHz` 左右跑通，再考虑提速更稳，面包板建议不超过`10MHz`。

### 4.2 位传输顺序

常见有两种：

- `MSB First`
- `LSB First`
![[Pasted image 20260728133651.png]]
绝大多数 SPI Flash 的命令和数据都是 `MSB First`。如果主从两端位序不一致，读写结果一定错误。

### 4.3 数据位长度

常见配置有：

- `8-bit`
- `16-bit`

像 W25Q64 这样的 SPI Flash，命令、地址、数据都按字节组织，因此一般选择 `8-bit`。

### 4.4 时钟极性 CPOL

`CPOL` 决定空闲状态下时钟线的电平：

- `CPOL = 0`：空闲低电平
- `CPOL = 1`：空闲高电平
![[Pasted image 20260728133923.png]]
### 4.5 时钟相位 CPHA

`CPHA` 决定在哪个边沿采样：

- `CPHA = 0`：第一个边沿采样
- `CPHA = 1`：第二个边沿采样
![[Pasted image 20260728134020.png]]
### 4.6 四种 SPI 模式

`CPOL` 和 `CPHA` 组合后形成 4 种模式：

| 模式 | CPOL | CPHA | 含义 |
| --- | --- | --- | --- |
| Mode 0 | 0 | 0 | 空闲低电平，第一个边沿采样 |
| Mode 1 | 0 | 1 | 空闲低电平，第二个边沿采样 |
| Mode 2 | 1 | 0 | 空闲高电平，第一个边沿采样 |
| Mode 3 | 1 | 1 | 空闲高电平，第二个边沿采样 |

本实验中的 W25Q64 支持 `Mode 0` 和 `Mode 3`，这里采用 `Mode 3`。

## 5. STM32 作为 SPI1 主机时怎么配

下面以 `SPI1` 为例，说明 STM32 如何作为主机去连接外部 Flash。

### 5.1 引脚分配

本实验可按下面的方案接线：

| STM32 引脚 | 功能 |
| --- | --- |
| `PA5` | `SPI1_SCK` |
| `PA6` | `SPI1_MISO` |
| `PA7` | `SPI1_MOSI` |
| `PA4` | 普通 GPIO，手动控制 `CS` |
| `PA0` | 按键输入，上拉 |
| `PC13` | 板载 LED 输出 |

这里把 `PA4` 当作普通 GPIO，而不是用硬件 NSS。

### 5.2 CubeMX 推荐配置

在 CubeMX 中，SPI 建议这样设置：

- `Mode = Full-Duplex Master`
- `Hardware NSS Signal = Disable`
- `Data Size = 8 Bits`
- `First Bit = MSB First`
- `Clock Polarity = High`
- `Clock Phase = 2 Edge`

这对应 `Mode 3`。

### 5.3 为什么这里要软件片选

教学和调试阶段，软件片选更直观：

1. 通信开始前，先把 `CS` 拉低
2. 发送命令、地址、数据
3. 通信结束后，再把 `CS` 拉高

这样和手册里的 SPI 事务图是一一对应的，也更便于理解具体外设在做什么。

### 5.4 SPI 波特率怎么来

CubeMX 里 SPI 波特率通常通过预分频得到：

```text
SPI 时钟 = APB 时钟 / 预分频系数
```

例如 `SPI1` 挂在 `APB2`，若 `PCLK2 = 8 MHz`，预分频选 `8`，则：

```text
SPI 波特率 = 8 MHz / 8 = 1 MHz
```

第一次连线调试建议先低速跑通，再逐步提速。

## 6. HAL 的 3 个核心 SPI 接口

### 6.1 `HAL_SPI_Transmit`

只关心发送时使用：

```c
HAL_SPI_Transmit(&hspi1, tx_data, size, HAL_MAX_DELAY);
```

参数意义：

- 第 1 个参数：SPI 句柄
- 第 2 个参数：发送缓冲区
- 第 3 个参数：发送字节数
- 第 4 个参数：超时时间

典型片选流程：

```c
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
HAL_SPI_Transmit(&hspi1, tx_data, size, HAL_MAX_DELAY);
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
```

### 6.2 `HAL_SPI_Receive`

只关心接收结果时使用：

```c
HAL_SPI_Receive(&hspi1, rx_data, size, HAL_MAX_DELAY);
```

要点有 3 个：

- 它底层仍然会发送数据
- 发送的作用是产生时钟
- 接收缓冲区最好先填成 `0xFF`

```c
uint8_t rx_data[2] = {0xFF, 0xFF};

HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
HAL_SPI_Receive(&hspi1, rx_data, 2, HAL_MAX_DELAY);
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
```

### 6.3 `HAL_SPI_TransmitReceive`

收发同时关心时最自然：

```c
HAL_SPI_TransmitReceive(&hspi1, tx_data, rx_data, size, HAL_MAX_DELAY);
```

它最符合 SPI 的本质，适合：

- 发命令同时读状态
- 一边送 dummy byte，一边收返回值
- 做时序调试

## 7. 先做一个最小闭环：按键切换 LED

在“掉电保存”之前，先把按键和 LED 的基本逻辑跑通。

目标是：

- 每按一次按钮
- 在按钮松开时切换一次 LED 状态

### 7.1 按键边沿检测思路

定义两个变量：

- `previous`：上一次按键状态
- `current`：当前按键状态

判断逻辑如下：

- `previous == current`：状态没变
- `previous != current`：捕捉到一次边沿

再结合 `current` 的值判断：

- `current == 0`：按钮按下
- `current == 1`：按钮松开

本实验选择在“松开瞬间”切换 LED，这样更稳定，也方便后续保存状态。

### 7.2 消抖

机械按键存在抖动，最简单的处理办法是：

- 检测到电平变化后
- 延时 `10 ms`
- 再继续执行逻辑

### 7.3 示例代码

```c
uint8_t previous = 1;
uint8_t current = 1;
uint8_t led_state = 0;

while (1)
{
    previous = current;
    current = HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0);

    if (previous != current)
    {
        HAL_Delay(10);

        if (current == 1)
        {
            if (led_state)
            {
                HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
                led_state = 0;
            }
            else
            {
                HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
                led_state = 1;
            }
        }
    }
}
```

说明：

- 很多 STM32 开发板的 `PC13` 是低电平点亮、高电平熄灭。
- 如果你的开发板电路不同，要按实际电平逻辑调整。

## 8. 从 SPI 角度看 W25Q64

### 8.1 模块引脚与 SPI 信号的对应关系

常见 W25Q64 模块会标出这些引脚：

- `DI`
- `DO`
- `CLK`
- `CS`
- `VCC`
- `GND`

它们和标准 SPI 的对应关系如下：

| 模块引脚 | 含义 | 对应 SPI |
| --- | --- | --- |
| `DI` | 从机数据输入 | `MOSI` |
| `DO` | 从机数据输出 | `MISO` |
| `CLK` | 时钟输入 | `SCK` |
| `CS` | 片选 | `NSS/CS` |
| `VCC` | 电源正 | `3.3V` |
| `GND` | 地 | `GND` |

注意：模块命名通常是站在“从机”角度，而不是站在 STM32 主机角度。

### 8.2 容量、页、扇区、地址

W25Q64 的核心容量参数先抓 4 个：

- 总容量：`64 Mbit = 8 MB`
-  扇区 `Sector`：`4 KB`
- 页 `Page`：`256 Byte`
- 地址长度：`24 bit`

这几个量决定了读写方式：

- 读命令和写命令后面一般要跟 24 位地址
- 页编程通常以页为最小编程组织单位
- 擦除通常以扇区为基本单位

地址发送顺序是：

```text
高字节 -> 中字节 -> 低字节
```

### 8.3 常用命令码和状态位

| 命令/状态 | 值 | 作用 |
| --- | --- | --- |
| `WRITE_ENABLE` | `0x06` | 写使能 |
| `READ_STATUS_REG1` | `0x05` | 读状态寄存器 1 |
| `PAGE_PROGRAM` | `0x02` | 页编程 |
| `READ_DATA` | `0x03` | 普通读数据 |
| `SECTOR_ERASE` | `0x20` | 擦除 4 KB 扇区 |
| `JEDEC_ID` | `0x9F` | 读取芯片 ID |
| `RELEASE_POWER_DOWN` | `0xAB` | 释放掉电模式 |
| `BUSY` 位 | `0x01` | Flash 忙状态 |
| `WEL` 位 | `0x02` | 写使能锁存位 |

记忆重点：

- `0x06` 不是写数据，而是允许后续擦除和编程
- `0x05` 用来判断 Flash 是否忙
- `0x03` 是普通读命令，读之前不需要写使能
- `0x02` 是页编程命令，不能简单理解成“随便往任意地址写多少都行”

## 9. W25Q64 驱动为什么要按固定顺序写

如果只是做最小实验，直接发命令加延时也能跑通。但真实驱动不会只靠“固定延时 + 盲写”工作，因为 Flash 的状态是会变化的。

### 9.1 初始化：先确认芯片真的在线

一个更像驱动的 `W25Q64_Init()` 通常会做这些事：

1. 保存 SPI 句柄和 `CS` 引脚信息
2. 先把 `CS` 拉高，保证芯片未被选中
3. 发送 `0xAB`，释放掉电模式
4. 发送 `0x9F`，读取 `JEDEC ID`
5. 判断返回值是否符合芯片型号
6. 再检查 Flash 是否处于忙状态

也就是说，初始化并不只是“SPI 外设配好了”，还包括“我确认挂在总线上的这颗 Flash 确实能响应”。

### 9.2 发送地址：命令后面固定跟 24 位地址

很多驱动都会把“命令 + 地址”的组织封装成一个小函数，例如：

```c
cmd[0] = opcode;
cmd[1] = address >> 16;
cmd[2] = address >> 8;
cmd[3] = address;
```

这个格式适用于读、写、擦除等多种操作，差别只在 `opcode`。

### 9.3 读数据的标准事务

普通读数据流程可以概括为：

1. 拉低 `CS`
2. 发送 `0x03`
3. 发送 24 位起始地址
4. 连续读取若干字节
5. 拉高 `CS`

用事务图表示就是：

```text
CS 拉低
MOSI: 0x03 + A23~A16 + A15~A8 + A7~A0
MISO: 连续返回数据
CS 拉高
```

更稳妥的驱动还会在读之前先做一件事：

- 先等待 `BUSY` 位清零

这样可以避免在芯片还没完成上一轮编程或擦除时立刻发起新读操作。

### 9.4 写使能：先把 WEL 打开

擦除和编程之前都要先执行写使能：

1. 等待 Flash 不忙
2. 拉低 `CS`
3. 发送 `0x06`
4. 拉高 `CS`
5. 再读状态寄存器，确认 `WEL` 位已经置 1

为什么要强调这一步？因为：

- 没有 `WEL = 1`
- 后面的擦除和编程通常不会生效

所以 `Write Enable` 不是形式步骤，而是状态切换步骤。

### 9.5 擦除：通常按扇区对齐

最常见的是扇区擦除：

- 命令：`0x20`
- 单位：`4 KB`

基本流程：

1. 地址向下对齐到扇区边界
2. 执行写使能
3. 发送 `0x20 + 24 位地址`
4. 等待 `BUSY` 位清零

更完整的驱动可能还支持：

- `32 KB` 块擦除
- `64 KB` 块擦除
- 整片擦除

但入门实验先理解扇区擦除就够了。

### 9.6 页编程：写函数通常不会自动擦除

这是工程里最容易忽略的一点：

> `Write()` 往往只负责编程，不负责自动擦除。

也就是说：

- 写之前，目标区域通常要先擦除
- 写函数内部负责把数据按页拆开
- 每次页编程前都要重新写使能

典型页编程事务如下：

```text
CS 拉低
MOSI: 0x02 + A23~A16 + A15~A8 + A7~A0 + data...
CS 拉高
等待 BUSY 清零
```

### 9.7 为什么要拆页

W25Q64 的页大小是 `256 Byte`，页编程不能随意跨页。

因此一个更完整的 `W25Q64_Write()` 会做这些事：

1. 检查地址范围是否合法
2. 检查写入长度是否合法
3. 计算当前页还剩多少空间
4. 把大块数据拆成若干个不跨页的小块
5. 每一块分别执行页编程

如果当前地址不是页起始地址，那么这一页能写的空间会更少。

### 9.8 为什么真实驱动会检查范围和长度

这里至少有两层原因：

1. W25Q64 的容量只有 `8 MB`，越界访问本身就是错误
2. HAL SPI 的长度参数通常是 `uint16_t`，超长传输会受到接口本身限制

所以更完整的驱动往往会做：

- 地址范围检查
- 长度检查
- 长数据分块发送

## 10. 教学版闭环与驱动版闭环

### 10.1 教学版为什么可以直接“写使能 + 擦除 + 延时 + 编程”

为了先讲明白 SPI 事务，最小教学版本通常这样写：

1. 发 `0x06`
2. 发 `0x20 + 地址`
3. 延时等待擦除完成
4. 再发 `0x06`
5. 发 `0x02 + 地址 + 数据`
6. 再延时等待编程完成

它的优点是：

- 好理解
- 好观察波形
- 便于把“命令码、地址、数据”三者对应起来

### 10.2 驱动版为什么更倾向于“查状态而不是固定延时”

真实驱动更常见的思路是：

1. `WriteEnable()`
2. `EraseSector()` 或 `EraseRange()`
3. `WaitBusy()`
4. `Write()`
5. `WaitBusy()`
6. `Read()`

这比单纯固定延时更稳，因为：

- 不同温度、电压、器件状态下耗时并不完全一样
- 单纯延时可能等得不够，也可能等得过头
- 通过 `BUSY` 位判断能直接知道芯片什么时候真的做完了

## 11. 保存 LED 状态到 Flash 的最小实现框架

### 11.1 保存函数

下面这个版本仍然保留教学写法，它的价值在于把 SPI 事务完全展开。唯一要注意的是**擦除等待不能用固定延时**：

> W25Q64 扇区擦除的典型耗时约 `150 ms`（最大值以数据手册为准）。只等 `100 ms` 就继续发页编程，芯片可能还没擦完，`0x02` 会被忽略，现象就是"代码正常、波形正常，但数据根本没存进去"。所以先提供一个查 `BUSY` 位的轮询函数：

```c
static void WaitBusy(void)
{
    uint8_t status_cmd = 0x05;
    uint8_t status = 0x00;

    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, &status_cmd, 1, HAL_MAX_DELAY);
    do {
        HAL_SPI_Receive(&hspi1, &status, 1, HAL_MAX_DELAY);
    } while (status & 0x01);   /* BUSY=1 表示还在擦除/编程 */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
}
```

注意：`HAL_SPI_Receive` 底层仍会发出占位时钟来把数据移进来，所以这里 `0x05 + 循环收字节` 就完成了"发读状态命令 → 反复读状态"的完整事务。

```c
static void SaveLedState(uint8_t led_state)
{
    uint8_t write_enable_cmd = 0x06;
    uint8_t erase_cmd[4] = {0x20, 0x00, 0x00, 0x00};
    uint8_t program_cmd[5] = {0x02, 0x00, 0x00, 0x00, led_state};

    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, &write_enable_cmd, 1, HAL_MAX_DELAY);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);

    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, erase_cmd, 4, HAL_MAX_DELAY);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
    WaitBusy();

    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, &write_enable_cmd, 1, HAL_MAX_DELAY);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);

    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, program_cmd, 5, HAL_MAX_DELAY);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
    WaitBusy();
}
```

这个版本做的事情很直接：

- 把 `0x000000` 所在扇区擦掉（擦完才继续）
- 再把 `led_state` 写到 `0x000000`（写完才返回）

它不是高性能写法，但非常适合教学。页编程的等待同样用 `WaitBusy()` 而不是 `HAL_Delay(10)`——和 §14.7 的提醒保持一致。

### 11.2 读取函数

```c
static uint8_t LoadLedState(void)
{
    uint8_t read_cmd[4] = {0x03, 0x00, 0x00, 0x00};
    uint8_t led_state = 0xFF;

    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, read_cmd, 4, HAL_MAX_DELAY);
    HAL_SPI_Receive(&hspi1, &led_state, 1, HAL_MAX_DELAY);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);

    return led_state;
}
```

这里对应的 SPI 动作是：

- 先发 `0x03 + 24 位地址`
- 再收回 1 字节数据

### 11.3 如果换成更接近驱动的理解

如果从驱动角度描述同一个闭环，可以写成：

1. `W25Q64_EraseSector(&flash, 0x000000)`
2. `W25Q64_Write(&flash, 0x000000, &led_state, 1)`
3. `W25Q64_Read(&flash, 0x000000, &led_state, 1)`

其中驱动内部会负责：

- 写使能
- 地址组织
- 页拆分
- 忙位等待
- 错误返回

也就是说，教学版把事务展开给你看，驱动版把事务封装成接口让上层调用。

## 12. 上电恢复 LED 状态

系统重新上电后，先从 Flash 读出之前保存的状态，再恢复 LED：

```c
led_state = LoadLedState();

if (led_state == 1)
{
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
}
else
{
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
}
```

而在按钮松开、LED 状态翻转之后，再调用保存函数：

```c
SaveLedState(led_state);
```

这样就实现了完整实验闭环：

1. 按键改变 LED 状态
2. LED 状态写入 Flash
3. 重新上电时从 Flash 读回
4. 按读回值恢复 LED

## 13. 工程上还要再多想一步

最小实验能跑通，不代表它已经适合长期使用。

### 13.1 为什么不能每次都擦同一个扇区

NOR Flash 擦除有寿命限制。如果每次按键都执行：

- 擦除 `4 KB`
- 只写 `1 Byte`

那么同一扇区会很快被反复磨损。

### 13.2 掉电还可能发生在擦写过程中

如果系统在下面两个时刻突然掉电：

- 扇区刚擦完，还没写回数据
- 页编程进行到一半

那你读出来的数据就可能失效。

### 13.3 更稳妥的项目策略

真实项目更常用的思路是：

1. 先在 RAM 中更新状态
2. 通过消抖、延时或批处理合并多次写入
3. 在扇区中追加记录，而不是每次回写同一地址
4. 给记录加序号、版本号、校验值
5. 上电时读取“最后一条完整记录”
6. 检查所有擦写接口的返回值

所以本文的实验方案应该理解为：

- 它非常适合教学
- 但它不是最终量产写法

## 14. 高频易错点

### 14.1 `MOSI` / `MISO` 接反

- `MOSI` 是主发从收
- `MISO` 是主收从发

接反后，波形可能有，数据却完全不对。

### 14.2 片选时序错误

通信前拉低 `CS`，通信结束后拉高 `CS`。如果 `CS` 控制时机不对，从机就不会把这次事务当成完整命令来处理。

### 14.3 SPI 模式不匹配

重点检查：

- `CPOL`
- `CPHA`

本实验用 `Mode 3`。如果主从两边模式不一致，最常见现象就是“总线看起来有时钟，但读出来全错”。

### 14.4 误以为接收时主机不用发数据

SPI 接收必须靠主机发时钟。没有时钟，从机就不会把数据推出来。

### 14.5 写 Flash 前忘记写使能

没有 `0x06`，后续擦除和编程通常不会生效。

### 14.6 写前不擦除

`Write()` 通常不自动擦除，目标区域往往要先擦再写。

### 14.7 不等待擦除或编程完成

如果 Flash 还忙着擦除或编程，你就继续发下一条命令，结果很容易异常。更稳妥的做法是查 `BUSY` 位，而不是只写死延时。

### 14.8 页编程跨页

W25Q64 的页大小是 `256 Byte`。页编程不能简单跨页，驱动通常需要自己拆块。

### 14.9 只发 `0x06`，但没确认 `WEL`

更稳的做法是：

- 发完 `0x06`
- 再读状态寄存器
- 确认 `WEL` 真的置位

### 14.10 按键不消抖

一次按键可能被系统识别成多次边沿，导致 LED 状态来回跳。

### 14.11 LED 电平逻辑写反

板载 LED 常见低电平点亮，但不是所有开发板都这样。一定要按原理图确认。

### 14.12 一次状态变化对应一次扇区擦除

这种做法虽然简单，但会浪费寿命并扩大掉电损坏窗口。教学中可以这样写，工程中不要默认这样用。

## 15. 整个实验真正想教会你的是什么

把全文合起来看，这个实验的主线其实很清楚：

1. 先认识 SPI 的 4 根线和主从结构
2. 再理解 SPI 为什么是全双工
3. 然后统一 SPI 的 5 个关键参数
4. 接着在 CubeMX 中把 STM32 配成 `SPI1` 主机
5. 学会用 HAL 发命令、发地址、收数据
6. 最后把 W25Q64 的读写、擦除和掉电记忆串成一个完整闭环

真正难的不是背出 `MOSI/MISO/SCK/CS`，而是把下面这些事情同时做对：

- 主从关系正确
- 模式匹配正确
- 片选时序正确
- 命令和地址顺序正确
- Flash 的状态机顺序正确
- 上层业务逻辑和底层 SPI 事务能闭环

## 16. 一页速记

- **SPI 一句话**：主机提供时钟，用 `MOSI/MISO/SCK/CS` 完成高速同步串行通信。
- **四根线**：`MOSI` 主发从收，`MISO` 主收从发，`SCK` 主机给时钟，`CS` 拉低选中从机。
- **通信本质**：只要有时钟，发送和接收就同时发生。
- **5 个参数**：波特率、位序、数据位长度、`CPOL`、`CPHA`。
- **本实验配置**：`SPI1 + Full Duplex Master + 8 bit + MSB First + Mode 3 + 软件 CS`。
- **Flash 常用命令**：`0x06` 写使能，`0x05` 读状态，`0x03` 读数据，`0x02` 页编程，`0x20` 扇区擦除，`0x9F` 读 ID，`0xAB` 释放掉电。
- **读事务**：`CS` 拉低 -> `0x03 + 24 位地址` -> 连续接收 -> `CS` 拉高。
- **写事务**：写使能 -> 擦除目标区域 -> 等待不忙 -> 页编程 -> 再等不忙。
- **教学版闭环**：按钮切 LED -> 写 Flash -> 上电读 Flash -> 恢复 LED。
- **工程版提醒**：不要每次都擦同一扇区；要考虑寿命、忙位、跨页、校验和掉电安全。
