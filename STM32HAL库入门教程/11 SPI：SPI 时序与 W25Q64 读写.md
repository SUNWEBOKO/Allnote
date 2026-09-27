# 11 SPI：SPI 时序与 W25Q64 读写

## 本章问题

怎样用软件 SPI 和 HAL SPI 可靠读取、擦除、写入并回读 W25Q64？

## 学习目标

- 用四根信号线解释一次 SPI 字节交换。
- 按模式 0 时序实现 `MySPI` 软件收发。
- 用 W25Q64 命令完成读 ID、擦除、编程和回读。
- 按实验现象定位 SPI 与 Flash 操作故障。

## 0. 本章路线图：三个工程怎么学

本章从 0 开始走三步递进：先用 GPIO 手搓时序看懂 SPI，再把底层换成 SPI1 外设，最后看一眼工程化驱动的样子。配套工程 `E:\ProjectStm\Courses\HAL11_SPI_W25Q64` 下的三个互相独立子工程与三步一一对应，先跟正文自己搭，搭完再用它们对照验证：

| 子工程 | 底层 | 关键配置 | 回答的问题 |
| --- | --- | --- | --- |
| `01_SoftSPI_GPIO` | GPIO 逐位模拟模式 0 | `PA4` CS、`PA5` SCK、`PA6` MISO、`PA7` MOSI | 时序是怎么一位一位发出去的？ |
| `02_HardSPI_HAL` | SPI1 外设 + 教学版驱动 | 模式 0、8 位、MSB 先发、软件 NSS | 换成硬件外设后代码怎么改？ |
| `03_HardSPI_Library` | SPI1 外设 + 句柄版库驱动 | 同 `02`，驱动换成 `w25q64.c/.h` | 能长期复用的驱动长什么样？ |

三个工程使用完全相同的接线（`PA4`～`PA7` 加 OLED），区别只在驱动文件：

- `01` 与 `02` 使用教学版驱动 `User/Drivers/W25Q64_Tutorial/`（`MySPI.c`、`W25Q64.c`、`W25Q64_Ins.h`），第 4～6 节逐行讲解的就是它；`02` 只替换 `MySPI.c` 的实现，`W25Q64.c` 一字不改（见第 7 节）；
- `03` 使用句柄版库驱动 `User/Drivers/W25Q64_Library/`，API 与教学版不同，见第 7.3 节；
- 三个工程的测试流程一致：读 JEDEC ID → 擦除 0 号扇区 → 单独读回 `0xFF` 验证擦除 → 写入 4 字节 → 回读比较。

同名 API 不能混进同一个编译目标：教学版和库版都定义了 `W25Q64_*` 函数，CMake 登记哪套就编译哪套，登记方法见 [[00 从零建立HAL工程]] 第 5 节。

## 1. SPI 四线、片选与四种模式

SPI 是由主机提供时钟的同步、全双工总线。刚从 [[09 I2C：总线时序与软件 I2C 驱动 OLED]]、[[10 MPU6050：软硬件 I2C 读写六轴数据]] 的 I2C 过来，可以这样建立第一印象：I2C 用两根线、靠"地址字节"点名；SPI 用四根线各司其职、靠一根片选线点名。用课堂类比记住四根线：

- `SCK` 是节拍器：主机每敲一下拍子，双方各传一位数据，没有拍子谁也不动；
- `MOSI` 是主机递出去的讲义：主机说，从机听；
- `MISO` 是从机递回来的答案：从机说，主机听；
- `CS/SS` 是点名：只有被点到名（拉低）的器件才允许听和说。

以下方向均以 STM32 主机为准：

| 信号 | 方向 | 作用 |
| --- | --- | --- |
| `SCK` | 输出 | 主机产生串行时钟 |
| `MOSI` | 输出 | Master Output Slave Input，主机发送、从机接收 |
| `MISO` | 输入 | Master Input Slave Output，从机发送、主机接收 |
| `CS/SS` | 输出 | 低电平时选中当前从机 |

一主多从时，`SCK`、`MOSI`、`MISO` 可以共用，各从机使用独立 `CS`。未被选中的器件不参与通信。

### 1.1 SPI 收发的是"交换"

主机和从机都可看作一个移位寄存器。每个 `SCK` 周期内，双方按模式规定的边沿同时移出一位并移入一位，因此 8 个时钟周期交换一个字节：

```c
uint8_t MySPI_SwapByte(uint8_t byte_send);
```

只发送时可以忽略返回值；只接收时仍要发送一个占位字节，例如 `0xFF`，用 8 个时钟换回 8 位数据。原因很直接：时钟只能由主机产生，主机不发字节就敲不出 8 个拍子，从机手里有数据也递不出来。

### 1.2 CS 划分事务

`CS` 拉低开始一次事务，拉高结束事务：

```text
CS = 1
CS = 0 -> 命令 -> 24 位地址 -> 数据/占位字节
CS = 1
```

W25Q64 的命令、地址和数据必须处在同一次 `CS = 0` 事务中。若在命令和地址之间抬高 `CS`，该命令会被当作一条不完整或已经结束的指令。

### 1.3 四种模式

| 模式 | CPOL | CPHA | `SCK` 空闲电平 | 采样边沿 |
| --- | ---: | ---: | --- | --- |
| Mode 0 | 0 | 0 | 低 | 第一个边沿，即上升沿 |
| Mode 1 | 0 | 1 | 低 | 第二个边沿，即下降沿 |
| Mode 2 | 1 | 0 | 高 | 第一个边沿，即下降沿 |
| Mode 3 | 1 | 1 | 高 | 第二个边沿，即上升沿 |

W25Q64 支持模式 0 和模式 3，本章统一使用模式 0：MSB 先发，`SCK` 空闲为低，发送端先稳定 `MOSI`，再在 `SCK` 上升沿采样 `MISO`，最后拉低 `SCK` 准备下一位。

```text
1. SCK 保持低电平
2. 把当前发送位放到 MOSI
3. SCK 拉高，读取 MISO
4. SCK 拉低
5. 重复 8 次
```

### 1.4 和 I2C 对比：多两根线换来什么

| 对比点 | I2C（第 9、10 章） | SPI（本章） |
| --- | --- | --- |
| 线数 | 2 根：`SCL`、`SDA` | 至少 4 根：`SCK`、`MOSI`、`MISO`、`CS` |
| 器件寻址 | 每次事务先发地址字节 | 不发地址字节，`CS` 拉低即选中对应器件 |
| 方向 | 半双工，一根 `SDA` 轮流说 | 全双工，`MOSI`/`MISO` 各走各的（见 1.1 的"交换"） |
| 应答 | 每个字节有 ACK 应答位 | 没有应答位，正确与否靠回读比对确认（见第 8 节实验） |
| 速度 | 相对较低 | 可以很高，本章硬件 SPI 配到 18 MHz（见第 7.1 节） |
| 典型器件 | OLED、MPU6050 | NOR Flash、屏幕、高速 ADC |

多出来的线不是白花的：`MOSI`/`MISO` 分开让收发可以同时进行；`CS` 独立让"选中谁""数据帧从哪开始、到哪结束"都由主机直接掌控。代价是每个从机都要多占一根 `CS` 线，引脚紧张的场合 I2C 仍更有优势。

## 2. 接线与 W25Q64 存储结构

| W25Q64 模块 | STM32F103 | 方向 |
| --- | --- | --- |
| `CS` | `PA4` | STM32 输出，低有效 |
| `CLK` | `PA5` | STM32 输出 |
| `DO` | `PA6 / SPI1_MISO` | STM32 输入 |
| `DI` | `PA7 / SPI1_MOSI` | STM32 输出 |
| `VCC` | `3.3V` | 电源 |
| `GND` | `GND` | 必须共地 |

W25Q64 的 `DI` 接主机 `MOSI`，`DO` 接主机 `MISO`。软件 SPI 和硬件 SPI1 都使用 `PA4`～`PA7`，切换时不用改线。

> [!warning]
> `CS` 上电后必须保持高电平；W25Q64 模块必须使用 3.3 V，并与 STM32 共地。

W25Q64 是非易失性 NOR Flash，容量为 64 Mbit：

$$
64\ \text{Mbit} \div 8 = 8\ \text{MB} = 0x00800000\ \text{B}
$$

| 项目 | 数值 |
| --- | ---: |
| 总容量 | 8 MB |
| 页 Page | 256 B |
| 扇区 Sector | 4 KB，即 4096 B |
| 地址位数 | 24 位 |
| 地址范围 | `0x000000`～`0x7FFFFF` |

24 位地址必须按高字节、中字节、低字节发送：

```c
MySPI_SwapByte((uint8_t)(address >> 16));
MySPI_SwapByte((uint8_t)(address >> 8));
MySPI_SwapByte((uint8_t)address);
```

### 2.1 页、扇区、块：8 MB 的地址地图

把 8 MB 想成一栋档案楼，就能记住 Flash 的四级结构：

| 单位 | 大小 | 作用 | 类比 |
| --- | ---: | --- | --- |
| 页 Page | 256 B | 一次页编程能写入的最大范围 | 一页信纸，只能往上添字 |
| 扇区 Sector | 4 KB | 扇区擦除的最小单位 | 一个档案柜，擦除只能整柜清空 |
| 块 Block | 32 KB / 64 KB | 更大的擦除单位（命令 `0x52`/`0xD8`，本章工程定义了但测试未用） | 一整排柜子 |
| 全片 | 8 MB | 芯片擦除（命令 `0xC7`，同上） | 整栋楼清空 |

两个由结构直接推出的对齐要求，后面驱动会反复用到：

- 页编程要求数据不跨页：页大小 256 B，页内偏移加写入长度不能超过 256；
- 扇区擦除要求地址按 4 KB 对齐：4 KB 就是 `0x1000`，所以合法的擦除地址低 12 位必须全是 0，例如 `0x000000`、`0x001000`、`0x002000`。

为什么擦除后读回来是 `0xFF`？因为 Flash 的物理规则是"把 1 写成 0"（第 3 节规则 2）：擦除把一整个扇区的位统一恢复成 1，每个字节都变回 `0xFF`；写入只能在原本是 `1` 的位置凿出 `0`。第 8 节的实验正是利用这一点验证擦除是否成功。

裸芯片还有两个低电平有效引脚：

- `/WP`：写保护。为低时禁止编程和擦除。
- `/HOLD`：暂停串行通信。为低时，主机暂时不能正常读写状态或数据。

常见模块已将二者上拉；若模块引出了这两个脚，应保持高电平。

## 3. Flash 规则与命令码

W25Q64 的关键规则如下：

1. **先写使能**：页编程和擦除前必须先发送 `0x06`，并让该命令单独占用一次 `CS` 事务。
2. **只能把 1 写成 0**：编程不能把 `0` 恢复为 `1`；需要恢复时必须先擦除。
3. **擦除单位是扇区**：本章使用 `0x20`，一次擦除 4 KB，不能只擦除一个字节。
4. **页编程不能跨页**：一页 256 B，必须满足"页内偏移 + 写入长度 $\le 256$"。例如从 `0x0000F8` 写入时最多发送 8 B。
5. **擦除和编程后等待 BUSY**：命令结束后，芯片仍在内部操作；发送 `0x05` 读取状态寄存器，直到 bit 0 的 `BUSY = 0`。
6. **普通读取不需要写使能**：`0x03` 可以连续跨页读取，但开始前仍应确认 Flash 不忙。

状态寄存器 1 中，bit 0 是 `BUSY`，bit 1 是写使能锁存位 `WEL`。写使能后可用 `0x05` 检查 `WEL = 1`。

这些规则背后的"为什么"，初学阶段记住三条就够了：

- **写使能是一道保险**。复位后 `WEL` 为 0，只有显式发送 `0x06` 才置 1。没有这道保险，总线上的干扰字节就可能触发擦除，整片数据说没就没。所以本章驱动在每次页编程、每次扇区擦除前都重新走一遍写使能流程（见第 5 节 `W25Q64_PageProgram()`、`W25Q64_SectorErase()`），而不是假设上一次的 `WEL` 还在；
- **`0x06` 必须独占一次 `CS` 事务**。本章驱动的写法是 `MySPI_Start()` → 发 `0x06` → `MySPI_Stop()`，让 `CS` 在命令后立刻抬高（见第 6 节事务表）；
- **`BUSY` 是芯片的"工作中"指示灯**。主机发完擦除或编程命令只是"下了订单"，真正干活的是芯片内部的操作。期间唯一该做的就是读状态等它完工——本章驱动用 10 s 超时兜底（`W25Q64_BUSY_TIMEOUT_MS` 定义为 `10000UL`），超时仍忙就报错返回，避免程序死在轮询循环里。

```c
// W25Q64_Ins.h（完整文件，与配套工程一致）
#ifndef INC_W25Q64_INS_H_
#define INC_W25Q64_INS_H_

/* 基本读写与状态 */
#define W25Q64_WRITE_ENABLE						0x06
#define W25Q64_WRITE_DISABLE					0x04
#define W25Q64_READ_STATUS_REGISTER_1			0x05
#define W25Q64_READ_STATUS_REGISTER_2			0x35
#define W25Q64_WRITE_STATUS_REGISTER			0x01

/* 编程与擦除 */
#define W25Q64_PAGE_PROGRAM						0x02
#define W25Q64_QUAD_PAGE_PROGRAM				0x32
#define W25Q64_SECTOR_ERASE_4KB					0x20
#define W25Q64_BLOCK_ERASE_32KB					0x52
#define W25Q64_BLOCK_ERASE_64KB					0xD8
#define W25Q64_CHIP_ERASE						0xC7
#define W25Q64_ERASE_SUSPEND					0x75
#define W25Q64_ERASE_RESUME						0x7A

/* 读取 */
#define W25Q64_READ_DATA						0x03
#define W25Q64_FAST_READ						0x0B
#define W25Q64_FAST_READ_DUAL_OUTPUT			0x3B
#define W25Q64_FAST_READ_DUAL_IO				0xBB
#define W25Q64_FAST_READ_QUAD_OUTPUT			0x6B
#define W25Q64_FAST_READ_QUAD_IO				0xEB
#define W25Q64_OCTAL_WORD_READ_QUAD_IO			0xE3
#define W25Q64_CONTINUOUS_READ_MODE_RESET		0xFF

/* 身份与功耗 */
#define W25Q64_RELEASE_POWER_DOWN_HPM_DEVICE_ID	0xAB
#define W25Q64_POWER_DOWN						0xB9
#define W25Q64_HIGH_PERFORMANCE_MODE			0xA3
#define W25Q64_MANUFACTURER_DEVICE_ID			0x90
#define W25Q64_READ_UNIQUE_ID					0x4B
#define W25Q64_CMD_JEDEC_ID                     0x9F

/* 占位字节 */
#define W25Q64_DUMMY_BYTE						0xFF

#endif
```

其中本章用到 `0x06/0x05/0x02/0x20/0x03/0x9F/0xFF/0xAB` 这 8 个；其余宏对应四线快读、四线编程、块擦除等扩展命令，本章工程定义了但测试未用，属于"备好但不展开"的完整命令表。

其中 `0xABU` 用于释放掉电（Power-Down）状态：若上次程序用 `0xB9` 把芯片置入掉电模式，通信前必须先用 `0xAB` 唤醒；芯片本来就在正常状态时发它也无害。本章驱动发完 `0xAB` 就抬高 `CS` 并等待 1 ms，不读取随后的设备 ID 字节——完整用法是再交换 3 个占位字节后读回 ID，本驱动改用更直接的 `0x9F` 取 JEDEC ID；`0x9FU` 读取 24 位 JEDEC ID，W25Q64 的返回值应为 `0xEF4017`。

## 4. 软件 SPI：GPIO 配置与 `MySPI`

软件 SPI 不启用 SPI1 外设，只把 4 个引脚配置成普通 GPIO：

| 引脚 | 功能 | CubeMX 配置 | 初始电平 |
| --- | --- | --- | --- |
| `PA4` | `CS` | 推挽输出 | 高 |
| `PA5` | `SCK` | 推挽输出 | 低 |
| `PA6` | `MISO` | 输入，可上拉 | - |
| `PA7` | `MOSI` | 推挽输出 | 低 |

必须先执行 `MX_GPIO_Init()`，再调用 `W25Q64_Init()`；后者会调用 `MySPI_Init()` 设置空闲电平。

在 CubeMX 里的具体操作（对照上表逐项核对）：

1. 在芯片图上依次点击 `PA4`、`PA5`、`PA7`，都选 `GPIO_Output`；点击 `PA6` 选 `GPIO_Input`。四个引脚变绿即完成选择；
2. 在 `System Core → GPIO` 里逐个核对：`PA4` 的 `GPIO output level` 必须是 `High`（上电即释放总线）、`GPIO Mode` 为 `Output Push Pull`；`PA5`、`PA7` 初始 `Low`，`SCK` 空闲为低正是模式 0 的约定；`PA6` 的 `GPIO Pull-up/Pull-down` 本工程选 `No pull-up and no pull-down`——W25Q64 的 `DO` 是推挽输出，高低电平都能主动给出，不依赖内部上拉；
3. 点 `GENERATE CODE`，这些初始化会出现在 `MX_GPIO_Init()` 里。

两处初值填错的后果：`PA4` 初始若是 `Low`，芯片一上电就处于选中状态，总线毛刺可能被当成命令；`PA5` 初始若是 `High`，时钟空闲电平不符合模式 0，第一次交换的采样边沿整体错位，现象见第 10 节"ID 为 `00 00 00`"一行。

软件版和硬件版共用同一组上层接口：

```c
// MySPI.h
#ifndef INC_MYSPI_H_
#define INC_MYSPI_H_

#include "main.h"
#include <stdint.h>

void MySPI_Init(void);
void MySPI_Start(void);
void MySPI_Stop(void);
uint8_t MySPI_SwapByte(uint8_t byte_send);
HAL_StatusTypeDef MySPI_GetStatus(void);
void MySPI_ClearStatus(void);

#endif
```

软件版 `MySPI.c` 直接用 GPIO 实现模式 0：

```c
// MySPI.c：软件 SPI
#include "MySPI.h"
#include "gpio.h"

static HAL_StatusTypeDef g_spi_status;

static void MySPI_W_SS(GPIO_PinState state)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, state);
}

static void MySPI_W_SCK(GPIO_PinState state)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, state);
}

static void MySPI_W_MOSI(GPIO_PinState state)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_7, state);
}

static GPIO_PinState MySPI_R_MISO(void)
{
    return HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_6);
}

void MySPI_Init(void)
{
    g_spi_status = HAL_OK;
    MySPI_W_SS(GPIO_PIN_SET);
    MySPI_W_SCK(GPIO_PIN_RESET);
    MySPI_W_MOSI(GPIO_PIN_RESET);
}

void MySPI_Start(void)
{
    MySPI_W_SS(GPIO_PIN_RESET);
}

void MySPI_Stop(void)
{
    MySPI_W_SS(GPIO_PIN_SET);
}

uint8_t MySPI_SwapByte(uint8_t byte_send)
{
    uint8_t byte_receive = 0U;
    uint8_t i;

    for (i = 0U; i < 8U; ++i)
    {
        MySPI_W_MOSI(
            ((byte_send & (0x80U >> i)) != 0U)
                ? GPIO_PIN_SET
                : GPIO_PIN_RESET
        );
        MySPI_W_SCK(GPIO_PIN_SET);

        if (MySPI_R_MISO() == GPIO_PIN_SET)
        {
            byte_receive |= (uint8_t)(0x80U >> i);
        }

        MySPI_W_SCK(GPIO_PIN_RESET);
    }

    return byte_receive;
}

HAL_StatusTypeDef MySPI_GetStatus(void)
{
    return g_spi_status;
}

void MySPI_ClearStatus(void)
{
    g_spi_status = HAL_OK;
}
```

逐位拆解这个循环，`MySPI_SwapByte(0xAA)` 的前两位是这样走的（`0xAA` = `0b10101010`，高低电平交替，最容易看懂）：

1. `i = 0`：掩码 `0x80U >> 0` 等于 `0x80`，`0xAA & 0x80` 非零，于是把 `MOSI` 置高——最高位 bit 7 先出门，这就是"MSB 先发"；
2. `SCK` 拉高：模式 0 的上升沿到来。从机在这一沿采样 `MOSI` 收走 bit 7，主机在同一个沿读 `MISO`，若为高则 `byte_receive |= 0x80`；
3. `SCK` 拉低：一位结束，双方准备下一位；
4. `i = 1`：掩码变成 `0x80U >> 1` 等于 `0x40`……如此往复，8 次后发送字节走完，`byte_receive` 里恰好就是从机递回的那个字节。

掩码 `0x80U >> i` 是整个函数的灵魂：它从最高位开始逐位右移，同时完成"取出要发的位"和"按同样位置收回的位"两件事。这也解释了软件 SPI 慢在哪里——每一位都要 4 次 GPIO 函数调用外加循环开销，速率由 CPU 执行速度决定；硬件 SPI 则把这套动作交给外设自动完成，CPU 只负责递交整字节。

软件 GPIO 不会产生 HAL SPI 错误，因此 `MySPI_GetStatus()` 始终返回 `HAL_OK`。硬件版仍保留这两个接口，用来向上层传播 `HAL_ERROR` 或 `HAL_TIMEOUT`。

四个引脚辅助函数统一用 `MySPI_W_`/`MySPI_R_` 前缀命名（W = 写、R = 读，SS = 片选）：`MySPI_W_SS()`、`MySPI_W_SCK()`、`MySPI_W_MOSI()`、`MySPI_R_MISO()`，与配套工程 `MySPI.c` 的函数名一字不差。

## 5. W25Q64 最小完整驱动

驱动返回值统一为：`0` 表示流程完成，非 `0` 表示参数错误、SPI 错误、超时或操作失败。`W25Q64_PageProgram()` 只写一页且不会自动擦除；`W25Q64_SectorErase()` 要求传入已按 4 KB 对齐的地址。

```c
// W25Q64.h（与配套工程一致）
#ifndef INC_W25Q64_H_
#define INC_W25Q64_H_

#include <stdint.h>

#define W25Q64_TOTAL_SIZE       0x00800000UL
#define W25Q64_PAGE_SIZE        256UL
#define W25Q64_SECTOR_SIZE      4096UL
#define W25Q64_JEDEC_ID         0xEF4017UL

void W25Q64_Init(void);
uint8_t W25Q64_ReadID(uint8_t *manufacturer_id, uint16_t *device_id);
uint8_t W25Q64_PageProgram(uint32_t address, const uint8_t *data, uint16_t count);
uint8_t W25Q64_SectorErase(uint32_t address);
uint8_t W25Q64_ReadData(uint32_t address, uint8_t *data, uint32_t count);

#endif
```

```c
// W25Q64.c：软件 SPI 与硬件 SPI 共用（与配套工程一致）
#include "W25Q64.h"
#include "W25Q64_Ins.h"
#include "MySPI.h"

#define W25Q64_BUSY_TIMEOUT_MS 10000UL

static uint8_t W25Q64_ValidRange(uint32_t address, uint32_t count)
{
    return (uint8_t)((count != 0U) &&
                     (address < W25Q64_TOTAL_SIZE) &&
                     (count <= (W25Q64_TOTAL_SIZE - address)));
}

static uint8_t W25Q64_SPI_OK(void)
{
    return (uint8_t)(MySPI_GetStatus() == HAL_OK);
}

static uint8_t W25Q64_WaitBusy(void)
{
    uint32_t start = HAL_GetTick();
    uint8_t status;

    MySPI_Start();
    MySPI_SwapByte(W25Q64_READ_STATUS_REGISTER_1);
    for (;;)
    {
        status = MySPI_SwapByte(W25Q64_DUMMY_BYTE);
        if (!W25Q64_SPI_OK())
        {
            MySPI_Stop();
            return 1U;
        }
        if ((status & 0x01U) == 0U)
        {
            MySPI_Stop();
            return 0U;
        }
        if ((HAL_GetTick() - start) >= W25Q64_BUSY_TIMEOUT_MS)
        {
            MySPI_Stop();
            return 1U;
        }
    }
}

static uint8_t W25Q64_WriteEnable(void)
{
    uint8_t status;

    if (W25Q64_WaitBusy() != 0U)
    {
        return 1U;
    }

    MySPI_Start();
    MySPI_SwapByte(W25Q64_WRITE_ENABLE);
    MySPI_Stop();
    if (!W25Q64_SPI_OK())
    {
        return 1U;
    }

    MySPI_Start();
    MySPI_SwapByte(W25Q64_READ_STATUS_REGISTER_1);
    status = MySPI_SwapByte(W25Q64_DUMMY_BYTE);
    MySPI_Stop();
    if (!W25Q64_SPI_OK())
    {
        return 1U;
    }
    return (uint8_t)((status & 0x02U) == 0U);
}

void W25Q64_Init(void)
{
    MySPI_ClearStatus();
    MySPI_Init();

    MySPI_Start();
    MySPI_SwapByte(W25Q64_RELEASE_POWER_DOWN_HPM_DEVICE_ID);
    MySPI_Stop();
    HAL_Delay(1U);
}

uint8_t W25Q64_ReadID(uint8_t *manufacturer_id, uint16_t *device_id)
{
    if ((manufacturer_id == 0) || (device_id == 0))
    {
        return 1U;
    }

    MySPI_ClearStatus();
    MySPI_Start();
    MySPI_SwapByte(W25Q64_CMD_JEDEC_ID);
    *manufacturer_id = MySPI_SwapByte(W25Q64_DUMMY_BYTE);
    *device_id = (uint16_t)MySPI_SwapByte(W25Q64_DUMMY_BYTE) << 8;
    *device_id |= MySPI_SwapByte(W25Q64_DUMMY_BYTE);
    MySPI_Stop();
    return (uint8_t)!W25Q64_SPI_OK();
}

uint8_t W25Q64_PageProgram(uint32_t address, const uint8_t *data, uint16_t count)
{
    uint16_t i;

    if ((data == 0) || !W25Q64_ValidRange(address, count) ||
        (((address % W25Q64_PAGE_SIZE) + count) > W25Q64_PAGE_SIZE))
    {
        return 1U;
    }

    MySPI_ClearStatus();
    if (W25Q64_WriteEnable() != 0U)
    {
        return 1U;
    }

    MySPI_Start();
    MySPI_SwapByte(W25Q64_PAGE_PROGRAM);
    MySPI_SwapByte((uint8_t)(address >> 16));
    MySPI_SwapByte((uint8_t)(address >> 8));
    MySPI_SwapByte((uint8_t)address);
    for (i = 0U; i < count; ++i)
    {
        MySPI_SwapByte(data[i]);
    }
    MySPI_Stop();
    if (!W25Q64_SPI_OK())
    {
        return 1U;
    }
    return W25Q64_WaitBusy();
}

uint8_t W25Q64_SectorErase(uint32_t address)
{
    if ((address >= W25Q64_TOTAL_SIZE) ||
        ((address % W25Q64_SECTOR_SIZE) != 0U))
    {
        return 1U;
    }

    MySPI_ClearStatus();
    if (W25Q64_WriteEnable() != 0U)
    {
        return 1U;
    }

    MySPI_Start();
    MySPI_SwapByte(W25Q64_SECTOR_ERASE_4KB);
    MySPI_SwapByte((uint8_t)(address >> 16));
    MySPI_SwapByte((uint8_t)(address >> 8));
    MySPI_SwapByte((uint8_t)address);
    MySPI_Stop();
    if (!W25Q64_SPI_OK())
    {
        return 1U;
    }
    return W25Q64_WaitBusy();
}

uint8_t W25Q64_ReadData(uint32_t address, uint8_t *data, uint32_t count)
{
    uint32_t i;

    if ((data == 0) || !W25Q64_ValidRange(address, count))
    {
        return 1U;
    }

    MySPI_ClearStatus();
    if (W25Q64_WaitBusy() != 0U)
    {
        return 1U;
    }

    MySPI_Start();
    MySPI_SwapByte(W25Q64_READ_DATA);
    MySPI_SwapByte((uint8_t)(address >> 16));
    MySPI_SwapByte((uint8_t)(address >> 8));
    MySPI_SwapByte((uint8_t)address);
    for (i = 0U; i < count; ++i)
    {
        data[i] = MySPI_SwapByte(W25Q64_DUMMY_BYTE);
    }
    MySPI_Stop();
    return (uint8_t)!W25Q64_SPI_OK();
}
```


`W25Q64_ValidRange()` 使用 `W25Q64_TOTAL_SIZE - address` 判断剩余容量，避免直接计算 `address + count` 时发生 32 位无符号数回绕（溢出后从 0 重新计数）。

## 6. 必须保持的事务时序

| 操作 | 命令事务 | 后续处理 |
| --- | --- | --- |
| 读 JEDEC ID | `CS↓ -> 0x9F -> 0xFF -> 0xFF -> 0xFF -> CS↑` | 得到 `EF 40 17` |
| 读数据 | `CS↓ -> 0x03 -> 地址高/中/低 -> 0xFF... -> CS↑` | 每个 `0xFF` 换回 1 B |
| 写使能 | 事务 1：`CS↓ -> 0x06 -> CS↑` | 事务 2 读 `0x05`，确认 `WEL = 1` |
| 页编程 | 先写使能；再 `CS↓ -> 0x02 -> 地址高/中/低 -> 本页数据 -> CS↑` | 发送 `0x05`，等待 `BUSY = 0` |
| 扇区擦除 | 先写使能；再 `CS↓ -> 0x20 -> 地址高/中/低 -> CS↑` | 发送 `0x05`，等待 `BUSY = 0` |

`0x06` 不能和 `0x02` 或 `0x20` 放在同一次 `CS` 低电平事务中。读取状态时只发送一次 `0x05`，随后在 `CS` 保持低电平时连续发送 `0xFF`，直到 bit 0 清零。

## 7. 硬件 SPI1：配置与 API 差异

硬件版仍由软件控制 `PA4/CS`，只把时钟和字节交换交给 SPI1。`W25Q64.c` 不变，只替换 `MySPI.c`。

### 7.1 CubeMX 配置

| 项目 | 设置 |
| --- | --- |
| 外设 | `SPI1` |
| Mode | `Full-Duplex Master` |
| Direction | `2 Lines` |
| Hardware NSS Signal | `Disable`，使用软件 NSS |
| Data Size | `8 Bits` |
| First Bit | `MSB First` |
| Clock Polarity | `Low` |
| Clock Phase | `1 Edge` |
| Baud Rate Prescaler | `4` |
| CRC Calculation | `Disabled` |
| `PA4` | 普通 GPIO 推挽输出，初始高 |
| `PA5/PA6/PA7` | `SPI1_SCK/MISO/MOSI` |

`CPOL = 0`、`CPHA = 0` 对应模式 0。若 APB2 时钟为 72 MHz，4 分频后：

$$
f_{SCK} = \frac{72\ \text{MHz}}{4} = 18\ \text{MHz}
$$

面包板或较长连线首次调试时可先用 64 或 128 分频。

这些选项在 CubeMX 里的位置：`Pinout & Configuration → Connectivity → SPI1`，先在 Mode 列选 `Full-Duplex Master`，下方 `Parameter Settings` 面板才会展开，再按上表逐项填写。波特率分频下拉框从 2 开始成倍递增，最大到 256：$72 \div 2 = 36\ \text{MHz}$、$72 \div 4 = 18\ \text{MHz}$、$72 \div 8 = 9\ \text{MHz}$……分频越小 SCK 越快，但边沿也越陡，面包板长杜邦线的分布电容会让波形变差。先用大分频把功能跑通，再逐步降分频提速，每次修改后都要重新生成代码、编译并下载。

`Hardware NSS Signal` 为什么必须选 `Disable`？因为 W25Q64 要求"命令 + 地址 + 数据"处在同一次 `CS = 0` 事务里（第 1.2 节），事务的起止边界必须由软件精确控制；而硬件 NSS 由外设自动管理，做不出"发完一整帧再抬片选"的时序。所以 `CS` 交还 GPIO 手动控制——硬件版 `MySPI_Start()`/`MySPI_Stop()` 里只剩对 `PA4` 的一次写电平。

硬件版初始化顺序不能颠倒：

```c
HAL_Init();
SystemClock_Config();
MX_GPIO_Init();
MX_SPI1_Init();
W25Q64_Init();
```

`MX_SPI1_Init()` 内部会调用 HAL 初始化 `hspi1`，因此必须先于 `W25Q64_Init()` 和第一次 SPI 交换执行。顺序颠倒时，第一次交换字节发生在 SPI1 尚未初始化（时钟未使能、工作模式未配置）之前，这次交换不可能成功，`g_spi_status` 被记为非 `HAL_OK`，最终 `W25Q64_ReadID()` 报错，测试停在 ID 检查这一步。

### 7.2 硬件版 `MySPI.c`

```c
// MySPI.c：硬件 SPI1
#include "MySPI.h"
#include "spi.h"

static HAL_StatusTypeDef g_spi_status;

void MySPI_Init(void)
{
    g_spi_status = HAL_OK;
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
}

void MySPI_Start(void)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
}

void MySPI_Stop(void)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
}

uint8_t MySPI_SwapByte(uint8_t byte_send)
{
    uint8_t byte_receive = 0U;
    HAL_StatusTypeDef status;

    status = HAL_SPI_TransmitReceive(&hspi1,
                                      &byte_send,
                                      &byte_receive,
                                      1U,
                                      100U);
    if (status != HAL_OK)
    {
        g_spi_status = status;
        byte_receive = 0U;
    }

    return byte_receive;
}

HAL_StatusTypeDef MySPI_GetStatus(void)
{
    return g_spi_status;
}

void MySPI_ClearStatus(void)
{
    g_spi_status = HAL_OK;
}
```

| 对比点 | 软件 SPI | 硬件 SPI1 |
| --- | --- | --- |
| 外设初始化 | `MX_GPIO_Init()` | `MX_GPIO_Init()` 后再 `MX_SPI1_Init()` |
| 字节交换 | CPU 循环 8 次并翻转 GPIO | `HAL_SPI_TransmitReceive(..., 1U, 100U)` 完成 8 位收发 |
| 错误状态 | 始终为 `HAL_OK` | 保存并返回 HAL SPI 的错误或超时 |
| `CS` 控制 | `PA4` GPIO | 仍为 `PA4` GPIO |
| W25Q64 命令与事务顺序 | 相同 | 相同 |

### 7.3 03_HardSPI_Library：句柄版驱动差在哪

第三个工程硬件配置与 `02` 相同，换成句柄版库驱动（`User/Drivers/W25Q64_Library/`），设计思路从"写死资源"变成"参数注入"：

```c
W25Q64_Handle flash = {0};
W25Q64_Init(&flash, &hspi1, GPIOA, GPIO_PIN_4);
```

`W25Q64_Handle` 结构体里装着 SPI 句柄、`CS` 端口和引脚，驱动内部不再出现写死的 `hspi1`、`GPIOA`——换一个 SPI 外设或换一根片选脚，只改初始化参数。其头文件注释也写明："本驱动只依赖 HAL SPI 句柄和片选 GPIO，迁移时替换初始化参数即可。"

与教学版逐条对比：

| 能力 | 教学版（01/02） | 句柄版（03） |
| --- | --- | --- |
| 返回值 | `uint8_t`，`0` 表示成功 | `HAL_StatusTypeDef` |
| 跨页写入 | `W25Q64_PageProgram()` 只写一页，跨页要自己拆 | `W25Q64_Write()` 自动按页剩余空间拆成多次页编程 |
| 擦除对齐 | `W25Q64_SectorErase()` 要求地址已按 4 KB 对齐，否则返回参数错误 | `W25Q64_EraseSector()` 内部自动向下对齐到 4 KB |
| 长度限制 | 一次调用的长度受参数类型约束 | 单次 SPI 收发超过 65535 B 时自动分块 |
| 擦除命令 | 只有 `0x20` 扇区擦除 | 另有 32 KB/64 KB 块擦除与整片擦除（整片擦除按 120 s 超时计算） |

`03` 的测试程序还专门演示了跨页写入：从 `0x0000FE` 写 4 字节，前 2 字节落在第一页末尾、后 2 字节落到下一页开头，由 `W25Q64_Write()` 拆成两次页编程完成；擦除验证则照旧对 0 号扇区做。运行前同样要确认测试区域可丢弃。

跨页拆分和擦除对齐是库驱动最核心的两个函数，值得看一眼实现（节选自 `w25q64.c`）：

```c
HAL_StatusTypeDef W25Q64_Write(W25Q64_Handle *flash, uint32_t address,
                               const uint8_t *buffer, uint32_t len)
{
    /* ……参数检查省略…… */
    while (remain > 0U)
    {
        /* 本页还剩多少空间可写 */
        uint32_t page_left = W25Q64_PAGE_SIZE - (address % W25Q64_PAGE_SIZE);
        uint16_t chunk = (remain < page_left) ? (uint16_t)remain
                                              : (uint16_t)page_left;

        ret = W25Q64_PageProgram(flash, address, buffer, chunk);
        if (ret != HAL_OK)
        {
            return ret;
        }

        address += chunk;   /* 推进到下一片段起点 */
        buffer  += chunk;
        remain  -= chunk;
    }
    return HAL_OK;
}

HAL_StatusTypeDef W25Q64_EraseSector(W25Q64_Handle *flash, uint32_t address)
{
    address -= (address % W25Q64_SECTOR_SIZE);  /* 自动向下对齐到 4 KB */
    return W25Q64_EraseByCommand(flash, W25Q64_CMD_SECTOR_ERASE,
                                 address, W25Q64_BUSY_TIMEOUT_MS);
}
```

`W25Q64_Write()` 的关键就是每次循环先算"这一页还能写多少"（`page_left`），按剩余空间切块、逐块调用页编程；教学版把跨页拦下来返回错误，库版把它自动拆完——两者对 Flash 的操作规则完全一致，差别只在使用者的负担。`W25Q64_EraseSector()` 则用一句取余把任意地址拉回 4 KB 边界，调用者不再需要对齐。

## 8. 最小完整实验

> [!warning]
> 本实验会擦除 `0x000000`～`0x000FFF`。只有确认该区域没有有效数据后才能运行。

实验所需的全部硬件：STM32F103C8T6 最小系统板、W25Q64 模块（`PA4`～`PA7`，接线见第 2 节）、OLED 屏（软件 I2C：`PB8` 接 `SCL`、`PB9` 接 `SDA`，开漏输出，就是第 9 章那套驱动原样复用，与 SPI 的四根线互不冲突）、ST-LINK。新写了 `User/Src/app_w25q64_test.c` 之类的源文件，先在根 `CMakeLists.txt` 登记再编译（[[00 从零建立HAL工程]] 第 5 节）。

整个实验是一条"前一步不过就停"的流水线，每一步的输入、处理和预期现象：

| 步骤 | 输入 | 处理 | 预期现象 |
| --- | --- | --- | --- |
| 1 就绪 | 上电复位 | `OLED_Init()`、`W25Q64_Init()` | 屏幕第 1 行出现 `ID:` 字样 |
| 2 读 ID | 命令 `0x9F` | 交换 3 个占位字节拼出 ID | 显示 `ID:EF` 与 `DID:4017`；ID 不对则不再往下擦写 |
| 3 擦除 | 命令 `0x20` + 地址 `0x000000` | 写使能 → 擦除 → 等 `BUSY = 0` | 无报错，等待期间由 `W25Q64_WaitBusy()` 轮询兜底（最长 10 s） |
| 4 擦除验证 | 命令 `0x03` 读 4 字节 | 与 `0xFF` 逐字节比较 | 全为 `FF`；否则显示 `ERASE ERR` 并停机 |
| 5 写入 | 命令 `0x02` + 地址 + `01 02 03 04` | 写使能 → 页编程 → 等 `BUSY = 0` | 无报错 |
| 6 回读比较 | 命令 `0x03` 读 4 字节 | 与写入数据逐字节比较 | 显示 `PASS`；不一致显示 `FAIL` |

测试程序单独放在 `User/Src/app_w25q64_test.c`（新建后记得按 [[00 从零建立HAL工程]] 第 5 节登记源文件），`main.c` 的 `USER CODE 2` 区域只写一行 `W25Q64_Test();`。软件版在 `MX_GPIO_Init()` 之后调用，硬件版在 `MX_GPIO_Init()` 和 `MX_SPI1_Init()` 之后调用。`app_w25q64_test.c` 的完整内容如下（与配套工程一致）：

```c
#include "W25Q64.h"
#include "OLED.h"

static void W25Q64_ShowData(uint8_t line, const char *label, const uint8_t *data)
{
    OLED_ShowString(line, 1, (char *)label);
    OLED_ShowHexNum(line, 3, data[0], 2);
    OLED_ShowHexNum(line, 6, data[1], 2);
    OLED_ShowHexNum(line, 9, data[2], 2);
    OLED_ShowHexNum(line, 12, data[3], 2);
}

void W25Q64_Test(void)
{
    static const uint8_t write_data[4] = {0x01U, 0x02U, 0x03U, 0x04U};
    uint8_t read_data[4] = {0U};
    uint8_t erased_data[4] = {0U};
    uint8_t manufacturer_id = 0U;
    uint16_t device_id = 0U;
    uint8_t i;
    uint8_t erase_ok = 1U;
    uint8_t pass = 1U;

    OLED_Init();
    OLED_Clear();
    OLED_ShowString(1, 1, "ID:");
    W25Q64_Init();
    if (W25Q64_ReadID(&manufacturer_id, &device_id) != 0U)
    {
        OLED_ShowString(2, 1, "ID API ERR");
        while (1) { HAL_Delay(100U); }
    }
    OLED_ShowHexNum(1, 4, manufacturer_id, 2);
    OLED_ShowString(1, 9, "DID:");
    OLED_ShowHexNum(1, 13, device_id, 4);

    if ((manufacturer_id != 0xEFU) || (device_id != 0x4017U))
    {
        OLED_ShowString(2, 1, "ID CHECK    ");
        while (1) { HAL_Delay(100U); }
    }

    if ((W25Q64_SectorErase(0x000000U) != 0U) ||
        (W25Q64_ReadData(0x000000U, erased_data, 4U) != 0U))
    {
        OLED_ShowString(4, 1, "ERASE ERR   ");
        while (1) { HAL_Delay(100U); }
    }
    for (i = 0U; i < 4U; ++i)
    {
        if (erased_data[i] != 0xFFU)
        {
            erase_ok = 0U;
        }
    }
    if (erase_ok == 0U)
    {
        OLED_ShowString(4, 1, "ERASE ERR   ");
        while (1) { HAL_Delay(100U); }
    }

    if ((W25Q64_PageProgram(0x000000U, write_data, 4U) != 0U) ||
        (W25Q64_ReadData(0x000000U, read_data, 4U) != 0U))
    {
        OLED_ShowString(4, 1, "FLASH ERR   ");
        while (1) { HAL_Delay(100U); }
    }

    for (i = 0U; i < 4U; ++i)
    {
        if (read_data[i] != write_data[i])
        {
            pass = 0U;
        }
    }
    W25Q64_ShowData(2, "W:", write_data);
    W25Q64_ShowData(3, "R:", read_data);
    OLED_ShowString(4, 1, pass ? "PASS" : "FAIL");

    while (1)
    {
        HAL_Delay(200U);
    }
}
```


该文件开头包含 `W25Q64.h` 和 `OLED.h`。`W25Q64_ReadID()` 返回 `0` 只表示读取流程完成，仍必须逐项核对厂商 `0xEF` 与器件 `0x4017`；ID 不正确时，测试函数会停在 `ID CHECK`，不会继续擦写。

把可能看到的结果列全，每一条都能落到第 10 节某一行的排查上：

- `ID:EF` 与 `DID:4017` 正常显示 → 接线、模式 0、字节交换这条基础链路已经通了；
- 停在 `ID API ERR` 或 `ID CHECK`，或 ID 位置显示 `FF`/`00` → 查接线与采样模式，见第 10 节前两行；
- 显示 `ERASE ERR` → 写使能、`0x20` 命令或等忙环节出了问题，见第 10 节"擦除后不是 `FF`"一行；
- `W:` 与 `R:` 两行不一致、显示 `FAIL` → 逐字节对比两行显示，只错个别位多半是"没擦就写"，见第 10 节写入相关行。

## 9. 实验验收

按以下顺序验收，前一步未通过时停止后续操作：

1. 上电后 `CS = 1`，模式为 0；
2. 读回 JEDEC ID `0xEF4017`：厂商 `0xEF`、器件 `0x40`、容量标识 `0x17`；
3. 擦除 `0x000000` 所在扇区，单独读回时应为 `0xFF`；
4. 写入 `01 02 03 04`，等待 `BUSY = 0`；
5. 读回 4 B 并逐字节比较；
6. 软件 SPI 通过后，只替换底层 `MySPI.c`，再验收硬件 SPI1。

完整运行结果应为：

```text
ID:EF   DID:4017
W:01 02 03 04
R:01 02 03 04
PASS
```

ID 正确只说明基础通信正常；代码中的 `PASS` 只核对最终的 `W/R` 数据，证明写使能、页编程、BUSY 等待和读取可用。擦除必须单独验证：先在目标扇区写入非 `0xFF` 数据，再执行 `W25Q64_SectorErase()` 并回读，确认目标位置变为 `0xFF`。注意：出厂全新芯片的所有字节本来就是 `0xFF`，只读到 `FF` 不能证明擦除动作发生过；本工程测试没有包含"先写脏数据再擦"这一步，留作扩展练习。

除跑通流程外，本章结束时还应具备下面的能力：

- [ ] 能不看笔记画出四线接线表，并说出每根线的类比；
- [ ] 能说出页、扇区、块的大小与页编程、扇区擦除的对齐要求；
- [ ] 能解释为什么 `0x06` 要独占一次 `CS` 事务、为什么擦写后要等 `BUSY = 0`；
- [ ] 能说出句柄注入版（`03`）与教学版驱动的差异及各自适用场合；
- [ ] 遇到 ID 全 `FF` 或全 `00`，能按第 10 节的步骤排查。

## 10. 按现象排错

| 现象 | 优先检查 |
| --- | --- |
| ID 为 `FF FF FF` | 3.3 V 和共地；`CS` 是否拉低；`PA6/DO` 是否接反或悬空；`HOLD#` 是否为高；是否产生 `SCK`；硬件分频是否过高 |
| ID 为 `00 00 00` | `MISO` 是否被拉低；`SCK` 是否翻转；CPOL/CPHA 是否为模式 0；是否在错误边沿采样 |
| ID 正确，但擦除后不是 `FF` | `/WP#` 是否为高；是否先发 `0x06`；是否发 `0x20 + 24 位地址`；`CS` 是否在同一事务中；是否等待 `BUSY = 0` |
| 擦除后为 `FF`，写入后仍为 `FF` | 编程前是否重新执行 `WREN`；是否发送 `0x02`；页编程是否越过 256 B 页边界；硬件 SPI 是否返回错误或超时 |
| 某些位写入后始终为 `0` | Flash 只能把 `1` 写成 `0`；若目标位需要从 `0` 变回 `1`，必须先擦除整个所在扇区 |
| 回读只有部分字节错误 | 检查地址高/中/低顺序、`CS` 边界、页边界、缓冲区长度，以及是否在 `BUSY = 1` 时开始了下一事务 |
| BUSY 长时间不清零 | 检查 `/HOLD#`；确认 `0x05` 后持续发送占位字节；检查状态位、SPI 错误和 10 s 超时 |
| 软件 SPI 正常，硬件 SPI 失败 | 检查 `MX_SPI1_Init()`、`Full-Duplex Master`、`8 Bits`、`MSB First`、CPOL Low、CPHA 1 Edge、软件 NSS、PA4～PA7 映射和分频 |
| 硬件 SPI 正常，软件 SPI 失败 | 检查 `CS` 初值为高、`SCK` 初值为低；确认先设置 MOSI、上升沿采样 MISO、循环恰好 8 次、从 `0x80` 开始，并用 `0xFF` 产生接收时钟 |

上表是速查索引。三个最常卡住新手的症状，把检查项展开成可动手的顺序：

**症状一：ID 读出 `FF FF FF`（像"根本没接上"）**

1. 断电检查模块 `VCC` 是否接 3.3 V、`GND` 是否与 STM32 共地；
2. 重新上电，确认 `PA4/CS` 初始为高，进入 `MySPI_Start()` 后被拉低；
3. 核对模块 `DO` 是否接到 `PA6/MISO`——`DI`/`DO` 接反是最常见的低级错误；
4. 确认模块 `HOLD#` 引脚为高（多数模块已上拉）；
5. 硬件 SPI 工程先把分频改到 64 或 128，排除信号质量因素。

**症状二：ID 读出 `00 00 00`（像"MISO 被摁死在低电平"）**

1. 确认 `PA6` 配置为输入模式而不是输出；
2. 核对 CPOL/CPHA 是否为 `Low` + `1 Edge`，即模式 0；
3. 软件 SPI 工程检查 `MySPI_SwapByte()` 是否在 `SCK` 拉高之后才读 `MISO`；
4. 有条件的话用示波器或逻辑分析仪确认 `SCK` 确实在翻转。

**症状三：擦除验证通过，写入后读回仍是 `FF`（数据没写进去）**

1. 确认页编程前重新执行了写使能流程，且 `WEL = 1` 检查通过；
2. 核对命令是否为 `0x02`，24 位地址高、中、低字节顺序是否正确；
3. 检查是否越过页边界——本章驱动遇到跨界会直接返回参数错误，而不是写一半；
4. 硬件 SPI 工程确认 `MySPI_GetStatus()` 没有返回错误或超时。

全系列到此完结：回头看第 0 章，你已经从"点亮一个 LED"走到了"用四条线读写一颗存储芯片"。

上一篇：[[10 MPU6050：软硬件 I2C 读写六轴数据]]
