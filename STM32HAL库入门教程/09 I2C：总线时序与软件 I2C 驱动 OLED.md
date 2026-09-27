# 09 I2C：总线时序与软件 I2C 驱动 OLED

## 本章问题

没有硬件 I2C 外设时，怎样用 GPIO 产生合法时序并让 OLED 稳定显示？

第 [[02 OLED 调试：I2C 显示数据流]] 章里，你已经用硬件 I2C2 让 OLED 显示过内容：配置好 `hi2c2`，调用显示函数，屏幕就亮了。那时 I2C 是一个"能用就行"的黑盒——START、字节、应答这些动作全部由外设替你完成。本章把这个黑盒打开：用 PB8、PB9 两个普通 GPIO 逐位翻转出 I2C 时序，让同一块屏幕在"不启用任何 I2C 外设"的情况下照常工作。手写时序的意义不在于替代硬件外设：一是看懂电气层面到底发生了什么（第 [[10 MPU6050：软硬件 I2C 读写六轴数据]]、[[11 SPI：SPI 时序与 W25Q64 读写]] 章用的是同一套分析方法），二是学会"用普通 GPIO 模拟协议"这条通用出路，三是出故障时能对照波形说出"哪个动作没发生"。

## 学习目标

- 用 PB8、PB9 开漏 GPIO 产生软件 I2C 时序。
- 读懂开漏、上拉、START、STOP、第 9 个时钟与 ACK。
- 调用软件 I2C 版 OLED 驱动显示字符、字符串和变量。
- 对照屏幕现象与逻辑分析仪波形定位故障。
- 说清软件 I2C 与硬件 I2C 外设的分工和取舍。

## 0. 同一个屏幕的两条路

第 2 章和本章驱动的是同一块 128×64 SSD1306 OLED，走的是两条不同的路：

| | 第 2 章：硬件 I2C | 本章：软件 I2C |
| --- | --- | --- |
| 时序由谁产生 | `I2C2` 外设自动产生 | CPU 逐位翻转 GPIO |
| 引脚 | `PB10/PB11`（复用为 `I2C2_SCL/SDA`） | `PB8/PB9`（普通 GPIO） |
| GPIO 模式 | 复用开漏，由 `HAL_I2C_MspInit()` 配置 | 开漏输出，由 `MX_GPIO_Init()` 配置 |
| 速率 | `ClockSpeed = 100000`，即 100 kHz | 取决于 GPIO 翻转速度，必须实测 |
| 应答与时钟拉伸 | 外设硬件处理 | 本驱动不读取、不等待 |

两条路的终点是同一种波形：`START → 0x78 → 0x00/0x40 → 数据 → STOP`。

## 1. 接线与 GPIO 配置

实验对象为 STM32F103C8T6 和 128×64 SSD1306 OLED。PB8、PB9 是普通 GPIO，不使用硬件 I2C 外设——这正是本章的出发点：I2C 本质上是一份"电平怎么变化"的约定，而不是某几个引脚的专利，任何两个能输出高低电平的引脚都能模拟它。

| OLED | STM32F103C8T6 | 作用 |
| --- | --- | --- |
| `VCC` | `3.3V` | 模块供电 |
| `GND` | `GND` | 共地 |
| `SCL` | `PB8` | 软件 I2C 时钟 |
| `SDA` | `PB9` | 软件 I2C 数据 |

上电前检查：

1. STM32 与 OLED 必须共地，SCL、SDA 不能接反——没有共同的地，"高电平""低电平"对双方来说不是同一套标准。
2. 先确认模块供电规格；本实验按 3.3 V 供电，不要仅凭外观判断模块可以接 5 V。
3. SDA、SCL 必须有上拉。多数 4 针 OLED 模块自带上拉，但应查模块原理图或断电测电阻；常见起点是 4.7 kΩ，最终要结合模块已有电阻、总线电容和上升时间确定（没有上拉会发生什么，见 2.4 节）。
4. 上拉只能拉到 STM32 可承受的 3.3 V。若模块把总线拉到 5 V，不能直接连接 PB8、PB9。
5. 总线空闲时，SCL、SDA 都应接近 3.3 V。若始终为低，先断电检查短路、接反、供电和上拉，不要反复下载程序。

以 STM32F103C8T6、外部 8 MHz 晶振和 72 MHz 系统时钟为例（时钟树细节见 [[03 时钟系统：时钟树、PLL 与 HAL 配置]]），CubeMX 中配置：

1. PB8、PB9 设为 `Output Open Drain`；
2. `Output Level` 设为 `High`，`Pull` 设为 `No pull`，`Speed` 设为 `High`（生成代码中对应 `GPIO_SPEED_FREQ_HIGH`，它直接影响软件 I2C 的速度上限，见 4.5 节）；
3. 不把硬件 I2C1 重映射到 PB8、PB9，也不启用同引脚的 I2C1；
4. 生成代码后，确认 `MX_GPIO_Init()` 先于 `OLED_Init()` 执行，并将两脚初始化为 `GPIO_MODE_OUTPUT_OD`。

生成的 `MX_GPIO_Init()` 关键内容如下（`.ioc` 对应行为 `PB8.GPIO_ModeDefaultOutputPP=GPIO_MODE_OUTPUT_OD`、`PB8.GPIO_PuPd=GPIO_NOPULL`、`PB8.PinState=GPIO_PIN_SET`，PB9 相同，三个子工程完全一致；键名里的 `OutputPP` 是 CubeMX F1 工程的固定遗留写法，与取值是开漏还是推挽无关。本配套工程把 `MX_GPIO_Init()` 直接写在 `Core/Src/main.c` 中，`Core/Inc/gpio.h` 只保留声明）：

```c
void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();

  /* 先写高电平再配模式：上电复位后引脚默认浮空，
     若先配模式后写电平，配置过程中总线可能被短暂拉低。 */
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8 | GPIO_PIN_9, GPIO_PIN_SET);
  GPIO_InitStruct.Pin = GPIO_PIN_8 | GPIO_PIN_9;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_OD;    /* 开漏输出 */
  GPIO_InitStruct.Pull = GPIO_NOPULL;            /* 不用内部上下拉，靠外部上拉 */
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /* PC13 板载 LED 同样配为开漏输出并写高（低电平点亮，写高即熄灭）。 */
}
```

这里的 `High` 表示释放总线，不是推挽输出 3.3 V；`No pull` 只表示未启用 STM32 内部弱上下拉，不代表总线上可以没有外部上拉。

## 2. I2C 的关键电气机制

先建立一个贯穿全章的直觉：SCL 负责提供节拍，SDA 在节拍之间准备数据，并在规定的时刻保持稳定。所有时序规则，都是在规定 SDA 何时可以变化、何时必须保持不变。

### 2.1 开漏、上拉与线与逻辑

`SCL` 和 `SDA` 都采用开漏方式：

- 写 `0`：GPIO 主动把线拉低；
- 写 `1`：GPIO 转为高阻态，释放总线，由上拉电阻恢复高电平。

只要任意设备拉低，整条线就是低电平；只有所有设备都释放，线路才为高电平。这种"线与"结构允许主机发送完 8 位后释放 SDA，让从机在第 9 个时钟拉低它表示 ACK。若主机仍用推挽输出强高电平，而从机为 ACK 拉低 SDA，就会发生高低电平争用：主机想把线顶在高电平，从机想把线拽到低电平，结果取决于谁的驱动能力更强，通信不可靠。

SCL 也是开漏线。从机可以在需要更多准备时间时继续把 SCL 拉低，这称为**时钟拉伸**。主机不能只认为"已经让 SCL 输出高"就继续发送，而应等待 SCL 引脚实际变为高电平。本章的最小驱动没有实现时钟拉伸等待——用于会拉伸时钟的从机时必须补上；第 9 拍 ACK 的处理见 2.3 节。

### 2.2 数据、START 与 STOP

普通数据位遵循以下规则：

- SCL 为低电平时，发送方改变 SDA；
- SCL 为高电平时，接收方读取 SDA，发送方必须保持 SDA 稳定。

只有 START 和 STOP 允许 SDA 在 SCL 高电平期间改变：

- SDA 在 SCL 高电平期间由高变低：START；
- SDA 在 SCL 高电平期间由低变高：STOP。

正因为数据在 SCL 高电平期间必须稳定，START 和 STOP 才能用 SDA 的特殊变化表示控制信号：接收方看到"时钟为高而数据发生变化"，就知道这不是普通数据位，而是一次开始或结束。

空闲状态是 SCL、SDA 都为高。一次典型写事务按 `START → 地址与读写位 → 数据字节与 ACK → STOP` 进行。

### 2.3 一个字节与第 9 个时钟

I2C 每字节发送 8 位，最高位 D7 先发送——递纸条的人总是从最高位开始递。8 个数据时钟后还有第 9 个应答时钟：

- 接收方在第 9 个时钟期间把 SDA 拉低：`ACK=0`；
- 接收方不拉低、让 SDA 保持高：`NACK=1`。

主机在第 9 个时钟前必须先释放 SDA。这一步和"线与"直接相关：主机松手后，SDA 的控制权暂时交给从机——从机拉低就是 ACK，从机不拉、上拉电阻把线顶回高就是 NACK。主机如果这时候还按住 SDA，从机的应答根本没有机会表达。

以写地址字节 `0x78`（二进制 `0111 1000`）为例，一拍一位：

| 时钟 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9（应答） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 位 | D7=0 | D6=1 | D5=1 | D4=1 | D3=1 | D2=0 | D1=0 | D0=0 | 从机拉低=ACK |

本章的 `OLED_I2C_SendByte()` 会产生这个应答时钟，但不读取返回值——所以屏幕有显示，也不能仅靠程序变量确认每一字节都得到 ACK；需要用逻辑分析仪查看 SDA，或把函数改为读取 ACK（第 9 拍 SCL 为高期间用 `HAL_GPIO_ReadPin()` 读 PB9，低即 ACK；属扩展练习，本驱动未实现）。

### 2.4 为什么软件 I2C 必须用开漏加上拉

把 2.1 节的结论落到本章配置上：SDA 在不同时刻由主机和从机分别驱动——主机发地址和数据时按住它，从机在每字节第 9 拍接管它，所以主机侧必须"只会拉低或松手"（`GPIO_MODE_OUTPUT_OD`），从机才有机会表达不同意见；而开漏写 1 等于松手，高电平完全由上拉电阻把线顶回 3.3 V，这就是 `No pull` 绝不等于"总线上可以没有上拉"的原因——它只是把这件事交给模块板载或外接电阻，因为外部上拉可以按总线电容和速率选得更合适。`Output Level = High` 让上电默认状态是"释放总线"。反过来看两个典型错误配置的后果：

- 把 PB8/PB9 配成推挽输出：写 1 时强推高，从机 ACK 拉低时形成争用，轻则波形畸变，重则损坏引脚；
- 开漏但忘接上拉：写 0 一切正常，写 1 后总线悬空、电平不定，通信时好时坏。

### 2.5 软件 I2C 与硬件 I2C 外设的差别

第 0 节的表格对比了配置差异，这里补一句分工本质：硬件 I2C 外设把整份时序约定固化进了电路，START/STOP 自动生成、应答自动收发、时钟拉伸自动等待，CPU 只需把字节交给外设（第 2 章的 `HAL_I2C_Master_Transmit(&hi2c2, ...)` 就是把整个事务交给外设去完成）；软件 I2C 则是 CPU 逐位"扮演"外设，任意引脚可用、每一步都看得见，但应答、时钟拉伸这些外设免费提供的能力都要自己在代码里显式实现——本驱动为了聚焦时序选择不实现（不读 ACK、不等拉伸），中断密集或总线复杂的场合必须补上。一句话：硬件外设像"按协议办事的办事员"，软件 I2C 像"照着协议逐条执行的实习生"——慢一点，但每个动作都摊在桌面上，最适合学习。

## 3. SSD1306 地址与写事务

### 3.1 7 位地址和线上地址字节

I2C 线上发送的第一个字节由 7 位从机地址和 1 位读写方向组成：

$$
\text{AddressByte}=(\text{Address}_7\ll 1)\;|\;\text{R/W}
$$

SSD1306 常见的 7 位地址是 `0x3C`：

| 含义 | 数值 |
| --- | ---: |
| 7 位从机地址 | `0x3C` |
| 写地址字节，`R/W=0` | `0x3C << 1 = 0x78` |
| 读地址字节，`R/W=1` | `(0x3C << 1) \| 1 = 0x79` |

本章只向 OLED 写数据，所以发送 `0x78`。部分模块的 7 位地址为 `0x3D`，对应写地址字节 `0x7A`。复刻时建议在代码里明确区分这两个概念（配套驱动为教学直观，直接使用字面量 `0x78`）：

```c
#define OLED_ADDR_7BIT   0x3CU   /* 7 位从机地址：手册和逻辑分析仪显示的是它 */
#define OLED_ADDR_WRITE  (OLED_ADDR_7BIT << 1)   /* 线上地址字节：总线真正发送的是它 */
```

### 3.2 命令与显示数据

地址之后还要发送 SSD1306 控制字节。控制字节的第 6 位是 `D/C`：为 `0` 时，后续内容按命令解释；为 `1` 时，后续内容按显存数据解释。本章使用：

- `0x00`：后续字节是命令；
- `0x40`：后续字节是显示数据；
- `0xAE`：关闭显示；
- `0xAF`：开启显示。

一次命令写事务为：

```text
START -> 0x78 -> ACK -> 0x00 -> ACK -> 0xAF -> ACK -> STOP
```

一次显示数据写事务为：

```text
START -> 0x78 -> ACK -> 0x40 -> ACK -> Data -> ACK -> STOP
```

这里的简化驱动每次只携带一个命令或数据字节，因此每个字节各自产生 START、地址、控制字节、第 9 个时钟和 STOP。连续发送一帧时可以批量放入同一事务，但这不改变上述地址与控制字节含义。

配套驱动的 `OLED_Init()` 就是把 23 条初始化命令（按字节计）一条条按"命令写事务"发出去。完整序列与含义如下（参数字节跟在命令后面）：

| 命令（+参数） | 含义 |
| --- | --- |
| `0xAE` | 关显示：改配置前先让屏幕闭眼 |
| `0xD5` + `0x80` | 显示时钟分频比 / 振荡频率 |
| `0xA8` + `0x3F` | 多路复用率 64 行 |
| `0xD3` + `0x00` | 显示偏移 0 |
| `0x40` | 显示起始行设为第 0 行 |
| `0xA1` | 段（列）映射方向：`0xA1` 正常，`0xA0` 左右反置 |
| `0xC8` | COM（行）扫描方向：`0xC8` 正常，`0xC0` 上下反置 |
| `0xDA` + `0x12` | COM 引脚硬件配置 |
| `0x81` + `0xCF` | 对比度 |
| `0xD9` + `0xF1` | 预充电周期 |
| `0xDB` + `0x30` | VCOMH 电平 |
| `0xA4` | 显示跟随显存内容（误发 `0xA5` 会强制全亮，见第 8 节） |
| `0xA6` | 正常显示（非反色） |
| `0x8D` + `0x14` | 开启内部电荷泵——SSD1306 靠内部升压产生驱动电压，漏发这条屏幕点不亮 |
| `0xAF` | 开显示 |

镜像、颠倒问题正对应 `0xA1`、`0xC8` 两条命令（排障见第 8 节）；`OLED_Init()` 末尾还会调用 `OLED_Clear()` 清屏。对照 `OLED_Init()` 源码逐行看，发送顺序与上表一致。

### 3.3 一次写事务的逐拍拆解

把 3.2 节第一条事务按"打拍子"摊开：每个字节占 9 拍，3 个字节共 27 拍。每一拍的分工完全一致——SCL 低电平时主机摆好 SDA 下一位，SCL 高电平期间从机采样，第 9 拍主机松手、从机表态。

```text
动作            SCL 拍数   谁在动 SDA              对应驱动函数
──────────────────────────────────────────────────────────────
START            —        主机：高→低             OLED_I2C_Start()
地址字节 0x78    1~9      主机 8 位 + 从机 ACK    OLED_I2C_SendByte(0x78)
控制字节 0x00    10~18    主机 8 位 + 从机 ACK    OLED_I2C_SendByte(0x00)
命令字节 0xAF    19~27    主机 8 位 + 从机 ACK    OLED_I2C_SendByte(Command)
STOP             —        主机：低→高             OLED_I2C_Stop()
```

## 4. 软件驱动调用链与关键代码

本章使用软件 I2C 版 `OLED.c`、`OLED.h` 和 `OLED_Font.h`，不要再把第 02 章的硬件 I2C 版 OLED 驱动同时加入同一工程。两套接口名称相近，但底层和刷新行为不同，混用会导致重复定义或显示行为不符。三个配套子工程的驱动文件内容完全一致，下文引用与 `User/Drivers/OLED/OLED.c` 逐行对应。

### 4.1 三层结构：字节层、命令层、显示层

整个驱动分三层，每层只认识自己的下一层：

| 层 | 函数 | 职责 |
| --- | --- | --- |
| 字节层（I2C 时序） | `OLED_I2C_Init()`、`OLED_I2C_Start()`、`OLED_I2C_Stop()`、`OLED_I2C_SendByte()` | 只管 SCL/SDA 电平：起始、停止、发 9 拍 |
| 命令/数据层（SSD1306 协议） | `OLED_WriteCommand()`、`OLED_WriteData()`、`OLED_SetCursor()` | 组装 `0x78` + 控制字节 `0x00/0x40` + 有效字节 |
| 显示层（应用语义） | `OLED_Clear()`、`OLED_ShowChar()`、`OLED_ShowString()`、`OLED_ShowNum()`、`OLED_ShowSignedNum()`、`OLED_ShowHexNum()`、`OLED_ShowBinNum()` | 按行列取字模、拆数字、定位写入 |

对外接口由 `OLED.h` 声明：

```c
#ifndef __OLED_H
#define __OLED_H

#include <stdint.h>
#include "gpio.h"

void OLED_Init(void);
void OLED_Clear(void);
void OLED_ShowChar(uint8_t Line, uint8_t Column, char Char);
void OLED_ShowString(uint8_t Line, uint8_t Column, char *String);
void OLED_ShowNum(uint8_t Line, uint8_t Column, uint32_t Number, uint8_t Length);
void OLED_ShowSignedNum(uint8_t Line, uint8_t Column, int32_t Number, uint8_t Length);
void OLED_ShowHexNum(uint8_t Line, uint8_t Column, uint32_t Number, uint8_t Length);
void OLED_ShowBinNum(uint8_t Line, uint8_t Column, uint32_t Number, uint8_t Length);

#endif
```

调用链不是"调用显示函数后直接改屏幕"，而是自上而下逐层加工：

```text
OLED_Init()
    -> OLED_I2C_Init()：释放 SCL、SDA
    -> OLED_WriteCommand()：发送 SSD1306 初始化命令

清屏输入
    -> OLED_Clear()
    -> OLED_WriteData()

字符或变量输入
    -> OLED_ShowString() / OLED_ShowNum() / OLED_ShowSignedNum() / OLED_ShowHexNum() / OLED_ShowBinNum()
    -> OLED_ShowChar()：按行列取字模
    -> OLED_SetCursor()：发送页地址和列地址命令
    -> OLED_WriteData()：发送字模字节
        -> OLED_I2C_Start()
        -> OLED_I2C_SendByte(0x78)
        -> OLED_I2C_SendByte(0x40U)
        -> OLED_I2C_SendByte(Data)
        -> OLED_I2C_Stop()
            -> HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8/9)
SSD1306 显存
    -> OLED 像素
```

使用驱动前，还要把 `User/Drivers/OLED/OLED.c` 登记进根 `CMakeLists.txt` 的 `target_sources`、把 `User/Drivers/OLED` 加进 `target_include_directories`——登记方法与忘记登记的典型报错见 [[00 从零建立HAL工程]] 第 5 节。

### 4.2 字节层：GPIO 操作、START/STOP 与发送字节

GPIO 初始化统一由 `main()` 中的 `MX_GPIO_Init()` 完成（见第 1 节），驱动初始化只负责把两条线释放为高：

```c
#include "gpio.h"

#define OLED_W_SCL(x)	HAL_GPIO_WritePin(GPIOB,GPIO_PIN_8,x)
#define OLED_W_SDA(x)	HAL_GPIO_WritePin(GPIOB,GPIO_PIN_9,x)

void OLED_I2C_Init(void)
{
	OLED_W_SCL(1);
	OLED_W_SDA(1);
}
```

两个宏把"传 1 传 0"翻译成 `HAL_GPIO_WritePin()` 调用。HAL 头文件 `stm32f1xx_hal_gpio.h` 中 `GPIO_PIN_RESET = 0u`、`GPIO_PIN_SET = 1u`，所以宏参数直接传 0/1 与传 `GPIO_PIN_RESET/GPIO_PIN_SET` 等价。

START 和 STOP 都发生在 SCL 高电平期间，逐行对照 2.2 节的波形：

```c
void OLED_I2C_Start(void)
{
	OLED_W_SDA(1);  /* 先保证 SDA 为高（空闲态） */
	OLED_W_SCL(1);  /* 拍子响着 */
	OLED_W_SDA(0);  /* SCL 高时，SDA 高 -> 低：START */
	OLED_W_SCL(0);  /* 拉低 SCL，为第一个数据位腾出"换纸条"的间隙 */
}

void OLED_I2C_Stop(void)
{
	OLED_W_SDA(0);  /* 先把 SDA 摆到低 */
	OLED_W_SCL(1);  /* 拍子响着 */
	OLED_W_SDA(1);  /* SCL 高时，SDA 低 -> 高：STOP */
}
```

发送字节是全驱动的核心。`0x80U >> i` 依次选出 D7 到 D0；第 9 个时钟前必须释放 SDA：

```c
void OLED_I2C_SendByte(uint8_t Byte)
{
	uint8_t i;
	for (i = 0; i < 8; i++)
	{
		OLED_W_SDA(!!(Byte & (0x80 >> i)));  /* SCL 为低时摆好本位 */
		OLED_W_SCL(1);                       /* 从机在 SCL 高电平期间读取 */
		OLED_W_SCL(0);                       /* 拉低，准备下一位 */
	}
	OLED_W_SDA(1);   /* 8 位发完，主机先释放 SDA，把第 9 拍让给从机 */
	OLED_W_SCL(1);   /* 第 9 个时钟：从机拉低即 ACK，本驱动不读取 */
	OLED_W_SCL(0);
}
```

三个细节值得停下来看：

- **循环里为什么没有先 `OLED_W_SCL(0)`？** 进入循环时 SCL 已经是低电平——`Start()` 的最后一步是 `SCL(0)`，且每次循环也以 `SCL(0)` 结束，"SCL 低电平时摆 SDA"的前提天然成立，每个数据位只需 3 次 GPIO 操作。
- **`!!` 是在做什么？** `Byte & (0x80 >> i)` 的结果可能是 `0x40` 这类"非 0 也非 1"的值；`!!` 把任何非零值规约成 1、零规约成 0，保证传给宏的只有 0/1。
- **9 拍在哪里数？** 循环 8 次是 8 个数据时钟，循环外 `SDA(1) → SCL(1) → SCL(0)` 是第 9 个应答时钟。每字节 9 个 SCL 脉冲；一次"START + 3 字节 + STOP"共 27 个脉冲、88 次 `HAL_GPIO_WritePin()` 调用（START 4 次 + 3×27 次 + STOP 3 次）。

### 4.3 命令/数据层：WriteCommand 与 WriteData

命令和显示数据的地址相同，只改变控制字节：

```c
void OLED_WriteCommand(uint8_t Command)
{
	OLED_I2C_Start();
	OLED_I2C_SendByte(0x78);		/* 从机地址（写） */
	OLED_I2C_SendByte(0x00);		/* 控制字节：后续是命令 */
	OLED_I2C_SendByte(Command);
	OLED_I2C_Stop();
}

void OLED_WriteData(uint8_t Data)
{
	OLED_I2C_Start();
	OLED_I2C_SendByte(0x78);		/* 从机地址（写） */
	OLED_I2C_SendByte(0x40);		/* 控制字节：后续是显存数据 */
	OLED_I2C_SendByte(Data);
	OLED_I2C_Stop();
}
```

两个函数只差一个控制字节，却把数据送进 SSD1306 里两个完全不同的地方：`0x00` 后面的字节被当作命令执行，`0x40` 后面的字节被当作像素写进显存——"命令误用 `0x40`、数据误用 `0x00`"正是排障时的经典原因（见第 8 节）。

介于两层之间还有定位函数。SSD1306 的页寻址把 128×64 显存分成 8 页（每页高 8 像素、宽 128 列）：

```c
void OLED_SetCursor(uint8_t Y, uint8_t X)
{
	OLED_WriteCommand(0xB0 | Y);					/* 设置页地址 Y：0~7 */
	OLED_WriteCommand(0x10 | ((X & 0xF0) >> 4));	/* 设置列地址高 4 位 */
	OLED_WriteCommand(0x00 | (X & 0x0F));			/* 设置列地址低 4 位 */
}
```

一次定位 = 3 条命令事务，列地址拆成高、低 4 位分两条命令发送，这是 SSD1306 页寻址模式的约定。

### 4.4 显示层：页寻址与字符显示

有了字节层和命令层，显示层只需关心"哪里、显示什么"。字模来自 `OLED_Font.h` 的 `static const uint8_t OLED_F8x16[][16]`：每个可打印 ASCII 字符占 16 字节，前 8 字节是上半页、后 8 字节是下半页。

```c
void OLED_ShowChar(uint8_t Line, uint8_t Column, char Char)
{
	uint8_t i;

	if ((Line == 0U) || (Line > 4U) || (Column == 0U) || (Column > 16U))
	{
		return;
	}
	if (((unsigned char)Char < (unsigned char)' ') ||
	    ((unsigned char)Char > (unsigned char)'~'))
	{
		Char = ' ';
	}

	OLED_SetCursor((Line - 1) * 2, (Column - 1) * 8);		/* 上半页 */
	for (i = 0; i < 8; i++)
	{
		OLED_WriteData(OLED_F8x16[(unsigned char)Char - ' '][i]);
	}
	OLED_SetCursor((Line - 1) * 2 + 1, (Column - 1) * 8);	/* 下半页 */
	for (i = 0; i < 8; i++)
	{
		OLED_WriteData(OLED_F8x16[(unsigned char)Char - ' '][i + 8]);
	}
}
```

读这段代码要注意四点：

- 一个 8×16 字符 = 两次定位（上半页、下半页）+ 16 个数据字节 = 22 次写事务；
- `OLED_F8x16[Char - ' ']`：字模表从空格（ASCII 0x20）开始排，用字符码减 `' '` 得到下标；
- 开头的越界检查拒绝第 1～4 行、第 1～16 列之外的坐标，非打印 ASCII 一律按空格显示；
- 数字显示函数都在"拆位"：`OLED_Pow()` 算出 10/16/2 的幂，`OLED_ShowNum()` 用 `Number / OLED_Pow(10, Length - i - 1) % 10 + '0'` 从高到低逐位变字符——固定显示低 `Length` 位、不足补 0；`OLED_ShowSignedNum()` 先单独显示 `+` 或 `-`，负数用 `0U - (uint32_t)Number` 取绝对值（避免对 `INT32_MIN` 取负溢出）；`OLED_ShowHexNum()`、`OLED_ShowBinNum()` 同理换进制。所有数字最终都汇入 `OLED_ShowChar()`。

`OLED_Clear()` 是最"暴力"的应用：8 页 × 128 列全部写 `0x00`，即每页 1 次定位 + 128 个数据字节，共 8×131 = 1048 次"3 字节事务"。它也解释了为什么初始化结束后总线会忙上一阵。

与第 2 章驱动的行为差异也要记住：本章软件 I2C 版没有在 STM32 侧维护整帧缓冲区，每个字符即写即显、直接写入 SSD1306 显存，不需要再调用整帧刷新函数（第 2 章硬件版驱动先把内容画进单片机内的显示缓冲区，再整帧刷新）。

### 4.5 驱动里的延时与速度

本驱动的每个 SCL 边沿都是一次 `HAL_GPIO_WritePin()`，中间没有任何延时函数，SCL 频率由主频、HAL 函数开销和编译优化共同决定，只能实测不能口算；在 72 MHz 下可能超过 SSD1306 的 400 kHz 上限。想保守可靠，就在 `OLED_W_SCL(1)` 与 `OLED_W_SCL(0)` 之间插几微秒延时，或改用定时器、DWT（Cortex-M3 内核自带的周期计数器）产生可预测延时——每位变慢，清屏 1048 次事务、每个字符 22 次事务的刷新时间按同样比例放大。改变主频或编译优化后要重新测量。

对照第 2 章还有个反直觉的事实：硬件 I2C 被限在 100 kHz，不加延时的软件 I2C 反而可能冲到 400 kHz 以上——"软件 = 慢"并不成立，真正的约束是 SSD1306 的 400 kHz 上限和信号质量。测量手段就是第 6 节的逻辑分析仪：改延时、改主频或改优化等级后，重新量一遍 SCL 周期。另外，`OLED_Init()` 开头的约 100 ms 上电等待只用于等待屏幕稳定，与 SCL 频率无关。

## 5. 三个子实验与预期现象

配套工程 `HAL09_OLED_SoftI2C` 下有三个子工程，驱动相同、主程序逐步加码，每个都按"输入 → 处理 → 输出 → 预期现象"检验信号链的一段。

### 5.1 01_Char：最小字符显示

在已加入上述软件驱动、并由 CubeMX 生成 `SystemClock_Config()` 的工程中，最小运行代码为：

```c
#include "main.h"
#include "OLED.h"

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();

    OLED_Init();
    OLED_ShowChar(1, 1, 'A');
    OLED_ShowString(2, 1, "I2C");
    OLED_ShowNum(3, 1, 12345U, 5U);

    while (1)
    {
    }
}
```

用 ST-Link 下载并复位后，预期看到：

```text
第 1 行：A
第 2 行：I2C
第 3 行：12345
```

配套子工程 `01_Char` 是它的最简版，`USER CODE` 区域只有 `OLED_Init();` 和 `OLED_ShowChar(1, 1, 'A');` 两行。输入是"第 1 行第 1 列显示 A"；处理路径是 `OLED_ShowChar()` → 两次 `OLED_SetCursor()`（页 0 与页 1、列 0）→ 16 个字模字节；输出是屏幕左上角一个 8×16 的 "A"。预期现象：**第 1 行第 1 格显示 A，其余全黑**——"其余全黑"本身也是重要现象，说明 `OLED_Init()` 末尾的 `OLED_Clear()`（1024 个 0x00）正常执行了。

如果看到 X，说明 Y：

- 全黑且 SCL/SDA 空闲电平不是高 → 供电、共地、上拉或接线问题，按第 8 节从底层查起；
- 空闲电平正常、有波形但全黑 → 初始化命令没生效，用逻辑分析仪核对 3.2 节的命令事务；
- A 显示成别的字符 → 字模下标错（`OLED_F8x16[Char - ' ']` 的减 `' '` 偏移被改动）；
- 只显示字符的上半或下半 → 两次 `SetCursor`、两段 8 字节有一段没写；
- 字符位置不对 → `(Line - 1) * 2`、`(Column - 1) * 8` 的换算或 `SetCursor` 命令值被动过。

### 5.2 02_Variables：字符串与变量显示

软件 I2C 版会直接写入对应显存，不需要再调用整帧刷新函数。当前 8×16 字体接口把屏幕分为 4 行、16 列，坐标从 1 开始；示例驱动会拒绝第 1～4 行、第 1～16 列之外的坐标，字符串到达第 16 列后停止，非打印 ASCII 按空格显示。新字符串比旧字符串短时，未覆盖的尾部可能残留，可先调用 `OLED_Clear()`，或用固定宽度和空格覆盖。

显示递增变量时，可把显示部分改为：

```c
uint32_t count = 0U;

OLED_Init();
OLED_ShowString(1, 1, "COUNT:");

while (1)
{
    OLED_ShowNum(2, 1, count, 6U);
    count++;
    HAL_Delay(100U);
}
```

预期第二行每 100 ms 增加 1（显示函数本身也要花时间，实际间隔略大于 `HAL_Delay` 的数值）。

配套子工程 `02_Variables` 是这个思路的完整版：初始化后先写好 4 行标签 `SOFT I2C`、`COUNT:`、`SIGNED:`、`PB8/PB9`，主循环为：

```c
static uint32_t counter;   /* 全局静态变量，上电为 0 */

while (1)
{
    OLED_ShowNum(2, 8, counter, 5);
    OLED_ShowSignedNum(3, 8, (int32_t)counter - 500U, 5);
    counter++;
    HAL_Delay(200U);
}
```

- **输入**：每轮循环把 `counter` 与 `counter - 500` 送显示；
- **处理**：`OLED_ShowNum()` 拆成 5 位数字写在列 8~12，`OLED_ShowSignedNum()` 输出符号 + 5 位数字（列 8~13）；
- **输出**：两行数字每约 200 ms 刷新一次；
- **预期现象**：第二行从 `00000` 起递增；第三行从 `-00500` 起同步递增，`counter` 数到 500 时跨过 0 变成 `+00000`——正好演示有符号数的符号处理。

如果看到 X，说明 Y：

- 两行数字同步变化、第三行过零变号 → 一切正常；
- 数字压到标签上 → 列参数与标签长度不匹配（`"COUNT:"` 6 个字符、`"SIGNED:"` 7 个字符，数字都从列 8 开始写）；
- 数字不再更新 → 主循环停了：检查 `HAL_Delay()` 是否还在、`while` 是否被改跳出；
- 数字残留旧值 → 每轮用固定宽度整段重写即可避免；自己把宽度改小就会出现。

三个实验共用的数据路径为：

```text
变量或字符串
    -> 数字拆位或字符取字模
    -> 光标页/列命令
    -> 0x78 地址 + 0x00/0x40 控制字节 + 命令/数据
    -> START、8 个数据时钟、第 9 个 ACK 时钟、STOP
    -> SSD1306 显存与 OLED 像素
```

### 5.3 03_Waveform：给逻辑分析仪制造周期性事务

配套子工程 `03_Waveform` 专为第 6 节的波形观察准备。初始化后写好 3 行固定标签 `I2C WAVEFORM`、`SCL=PB8`、`SDA=PB9`，主循环为：

```c
while (1)
{
    OLED_ShowString(4, 1, "LOGIC TEST");
    HAL_Delay(1000U);
    OLED_ShowString(4, 1, "          ");   /* 10 个空格覆盖旧内容 */
    HAL_Delay(1000U);
}
```

- **输入**：第 4 行每秒交替写入 `"LOGIC TEST"` 和 10 个空格；
- **处理**：每个字符串 10 个字符、每个字符 22 次写事务，每次交替就是一簇 220 次事务的连续总线活动；
- **输出**：第 4 行文字每秒出现、消失一次；SCL/SDA 上每秒爆发一簇事务，簇与簇之间两线保持高电平（空闲）；
- **预期现象**：屏幕前三行固定、第 4 行以 1 s 周期闪烁；逻辑分析仪上看到"复位后一大段密集事务（23 条初始化命令 + 1048 次清屏事务），随后每秒一簇"的节奏。第 4 行的空格写入也演示了 5.2 节"用等宽空格覆盖旧内容"的做法。

如果看到 X，说明 Y：

- 第 4 行每秒正常闪烁 → 波形观察环境就绪；
- 屏幕正常但分析仪采不到波形 → 检查采样率、通道定义（PB8=SCL、PB9=SDA）与地线；
- 空白那一秒总线仍有活动 → 空格覆盖没写进去（字符串被改动），或循环外还有代码在刷屏。

## 6. 用逻辑分析仪观察写事务

1. 逻辑分析仪地线接 STM32 `GND`；
2. 一路接 PB8 并定义为 `SCL`，一路接 PB9 并定义为 `SDA`；
3. 选择 I2C 协议解码，采样率应足以识别每个 SCL 周期；
4. 观察 `OLED_Init()` 的初始化过程。本驱动最后一条命令为 `0xAF`，应看到等价事务：

```text
START -> 0x3C Write -> ACK -> 0x00 -> ACK -> 0xAF -> ACK -> STOP
```

有些解码器显示 7 位地址与方向 `0x3C Write`，有些显示线上完整地址字节 `0x78`；二者表示同一个写地址。显示数据事务中的控制字节应为 `0x40`。

建议用 `03_Waveform` 配合观察：复位后先抓到初始化阶段的长串事务，随后每秒一簇，每簇开头都能找到 `START`，非常适合逐项核对。观察时逐项对应：

- START：SCL 高电平期间，SDA 由高变低；
- 数据：D7 先发，SCL 高电平期间 SDA 保持稳定；
- 每字节：8 个数据时钟后还有第 9 个 ACK 时钟；
- 写命令：地址后为 `0x00`；
- 写显存：地址后为 `0x40`；
- STOP：SCL 高电平期间，SDA 由低变高。

若第 9 个时钟期间 SDA 为高，接收方没有 ACK。还要测量 SCL 频率和上升沿；若从机拉伸 SCL，波形会出现更长的低电平，但上述最小写驱动不会等待该过程。两件值得专门记录的事：一是 **SCL 频率**——在波形上量两个相邻上升沿的间隔就是 SCL 周期，对照 400 kHz 上限判断是否要按 4.5 节加延时；二是**上升沿形状**——上拉合适时边沿陡峭，若上升沿圆滑缓慢（上拉过大或总线电容大），从机可能在 SCL 高电平前段采到中间电平，通信就会偶发出错。上升沿过慢与速率过高，是"平时正常、偶发花屏"的两大来源。

## 7. 本章验收

- [ ] SCL/SDA 空闲时都接近 3.3 V；
- [ ] START、地址、ACK、STOP 时序已观察；
- [ ] 字符、变量和波形显示分别通过；
- [ ] 驱动延时、ACK 和时钟拉伸边界已说明；
- [ ] 能从供电、上拉、时序、地址和字库逐层定位。

## 8. 按信号链分层排障

| 现象 | 所在层 | 优先检查 |
| --- | --- | --- |
| OLED 不亮，SCL/SDA 也没有波形 | 程序与 GPIO | 是否执行到 `OLED_Init()` 和 `MX_GPIO_Init()`；PB8、PB9 宏是否与接线一致；GPIO 是否为开漏 |
| SCL 或 SDA 空闲时始终为低 | 供电与线路 | 共地、接反、短路、模块电压、外部上拉及上拉电压；断开 OLED 后测 MCU 端能否释放为高 |
| 有波形，地址后 NACK | 地址与时序 | 模块是 `0x3C` 还是 `0x3D`；写地址是否对应 `0x78/0x7A`；第 9 个时钟前是否释放 SDA；上升沿是否过慢 |
| 有 ACK，但屏幕空白 | 控制与初始化 | 命令是否用 `0x00`、数据是否用 `0x40`；初始化命令是否完整；是否发送 `0xAF`；页地址、列地址和列偏移是否正确；字模是否存在 |
| 字符错位、镜像或上下颠倒 | SSD1306 扫描方向 | 检查初始化中的 `0xA0/0xA1`、`0xC0/0xC8` 和模块列偏移 |
| 旧字符残留或变量不更新 | 上层显示 | 软件驱动是否需要整帧刷新；新内容是否更短；固定宽度是否足够；循环和 `HAL_Delay()` 是否仍在执行 |
| 偶发花屏或复位后不稳定 | 速率与运行条件 | SCL 是否超过 400 kHz；上拉与上升沿；OLED 上电等待；电源质量；时钟拉伸；中断中是否长时间调用显示函数 |

排错顺序应保持为：`供电与接线 -> GPIO 电平 -> START/地址/ACK -> 控制字节与初始化 -> 字模与上层显示`。低层没有恢复前，不要先改字符内容或字模——信号链上任何一层断了，上层怎么改都不会有用。

上表最常见的几类故障，展开成"症状 → 可能原因 → 具体检查步骤"：

**屏幕毫无反应（全黑）**——可能原因：未供电或不共地；SCL/SDA 接反；程序没执行到 `OLED_Init()`；GPIO 没配成开漏；初始化命令没发出（`0xAF`、`0x8D/0x14` 电荷泵缺失时屏幕点不亮）。检查步骤：① 量 OLED 的 VCC/GND 电压与共地；② 断电量 SCL/SDA 是否接反、短路；③ 量两线空闲电平是否接近 3.3 V（判上拉）；④ 逻辑分析仪看有没有任何波形；⑤ 单步确认 `MX_GPIO_Init()` 已执行、宏的引脚号与接线一致；⑥ 分析仪核对最后是否发出 `0xAF`。

**整屏所有像素被点亮（全亮）**——可能原因：初始化中 `0xA4`（显示跟随显存）被误写或漏发成 `0xA5`（强制全亮）；或显存被整片写入 `0xFF`（如把清屏的 `0x00` 写成 `0xFF`）。检查步骤：① 对照 `OLED_Init()` 核对 `0xA4` 是否原样发出；② 分析仪看清屏事务的数据字节是否为 `0x00`；③ 若只改过上层代码，先恢复驱动原样再逐项 diff。

**有波形但地址后没有 ACK（地址错）**——可能原因：模块实际是 `0x3D`（写地址 `0x7A`）；第 9 拍前主机没释放 SDA；上升沿过慢导致采样错位。检查步骤：① 分析仪放大第 9 个时钟，确认 SDA 在该拍前已被主机释放；② 查模块丝印或手册确认 7 位地址；③ 核对发送的地址字节是 `0x78` 还是应为 `0x7A`；④ 测上升沿时间，过慢按上拉问题处理。

**偶发错字、花屏、复位后不稳定（时序太快或上拉问题）**——可能原因：SCL 超过 400 kHz；上拉过大或缺失使上升沿缓慢；电源纹波；上电未等稳定就发初始化。检查步骤：① 逻辑分析仪测 SCL 频率，超限则按 4.5 节加延时；② 测上升沿形状，缓慢就减小上拉阻值或缩短走线；③ 把延时加大一档做对照——若加长延时后故障消失，基本可锁定速率问题；④ 换稳电源、缩短杜邦线再试。

**通信正常但内容不对（残留、错位、不更新）**——可能原因：新内容比旧内容短造成残留；行列换算或 `SetCursor` 参数错；主循环停摆；控制字节 `0x00/0x40` 用反。检查步骤：① 先 `OLED_Clear()` 或用等宽空格覆盖，看残留是否消失；② 核对 `(Line - 1) * 2`、`(Column - 1) * 8` 与列参数；③ 确认主循环还在跑；④ 核对每条 `OLED_WriteCommand()` 用 `0x00`、每条 `OLED_WriteData()` 用 `0x40`。

上一篇：[[08 串口通信：轮询、中断、DMA 与蓝牙协议]] ｜ 下一篇：[[10 MPU6050：软硬件 I2C 读写六轴数据]]
