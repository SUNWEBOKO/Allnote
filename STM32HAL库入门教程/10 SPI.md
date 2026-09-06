# STM32 HAL 库 SPI 读写 W25Q64


## 1. 本章要完成什么

学完本章，你应该能够：

1. 说明 `SCK`、`MOSI`、`MISO`、`CS` 四根线的作用。
2. 理解 SPI 的同步、全双工和一主多从结构。
3. 根据模式 0 时序，用 GPIO 交换一个字节。
4. 解释为什么接收数据时仍要发送占位字节。
5. 说清 W25Q64 写使能、擦除、页编程和忙等待的顺序。
6. 用软件 SPI 读取 W25Q64 的 JEDEC ID。
7. 在 CubeMX 中配置 SPI1，并用 HAL 完成擦除、写入和读取。
8. 按“读 ID -> 擦除 -> 写入 -> 回读”的顺序定位故障。

两课之间的关系是：

```text
第 26 课：软件 SPI
GPIO 模拟 SCK/MOSI，读取 MISO
    -> 理解模式 0 和字节交换
        -> 读取 W25Q64 ID

第 27 课：硬件 SPI
SPI1 自动产生时钟和收发
    -> 展开写使能、忙等待、擦除、页编程、读取
        -> 完成 01 02 03 04 写入与回读
```

## 2. 实验现象与接线

### 2.1 预期现象

OLED 显示内容可概括为：

```text
MID: EF
DID: 4017
W: 01 02 03 04
R: 01 02 03 04
```

其中：

- `MID`：生产厂商 ID，常见值为 `0xEF`；
- `DID`：存储器类型与容量组成的 16 位器件 ID，W25Q64BV 常见为 `0x4017`；
- `W`：准备写入的数组；
- `R`：从 Flash 读回的数组。

ID 正确只能证明基础通信大概率正常；写入值与读回值完全一致，才说明写使能、擦除、页编程、忙等待和读取流程已经闭环。

### 2.2 W25Q64 与 STM32F103 接线

| W25Q64 模块 | 作用 | STM32F103 |
| --- | --- | --- |
| `CS` | 片选，低电平有效 | `PA4` |
| `CLK` | 串行时钟 | `PA5` |
| `DO` | Flash 输出 | `PA6` |
| `DI` | Flash 输入 | `PA7` |
| `VCC` | 电源 | `3.3V` |
| `GND` | 地 | `GND` |

从 STM32 主机角度看：

- W25Q64 的 `DI` 接 STM32 的 `MOSI`；
- W25Q64 的 `DO` 接 STM32 的 `MISO`。

STM32F103x8/B 数据手册中，SPI1 默认复用引脚是：

- `PA4`：`SPI1_NSS`
- `PA5`：`SPI1_SCK`
- `PA6`：`SPI1_MISO`
- `PA7`：`SPI1_MOSI`

软件 SPI 也选择这四个引脚，是为了切换到硬件 SPI1 时不需要改线。

> [!warning]
> W25Q64 使用 3.3 V 供电。模块必须与 STM32 共地，`CS` 上电后应先保持高电平。

## 3. SPI 通信基础

### 3.1 四根通信线

| 信号 | 全称 | 主机方向 | 作用 |
| --- | --- | --- | --- |
| `SCK` | Serial Clock | 输出 | 主机产生时钟 |
| `MOSI` | Master Output Slave Input | 输出 | 主机向从机发送数据 |
| `MISO` | Master Input Slave Output | 输入 | 从机向主机发送数据 |
| `CS/SS` | Chip/Slave Select | 输出 | 选择参与本次通信的从机 |

SPI 的典型特点是：

- **同步**：主机通过 SCK 提供时钟；
- **全双工**：发送与接收可同时进行；
- **一主多从**：SCK、MOSI、MISO 可以共享，每个从机一般使用独立 CS；
- **速度较高**：没有 I²C 的地址与应答开销，适合板级高速外设。

输出信号一般使用推挽输出；主机的 MISO 引脚配置为输入，可按电路需要选择浮空或上拉。

### 3.2 一主多从如何选设备

```text
主机 SCK  ----+---- 从机 1 SCK
              +---- 从机 2 SCK

主机 MOSI ----+---- 从机 1 MOSI
              +---- 从机 2 MOSI

主机 MISO ----+---- 从机 1 MISO
              +---- 从机 2 MISO

主机 CS1  --------- 从机 1 CS
主机 CS2  --------- 从机 2 CS
```

主机把某个从机的 CS 拉低，才表示选择该设备。未被选中的从机应释放 MISO，避免干扰总线。

### 3.3 SPI 是“交换”，不是单向搬运

主机和从机内部都可以看作有一个移位寄存器。每来一个时钟：

- 主机移出一位到 MOSI；
- 从机移出一位到 MISO；
- 双方同时把对方的一位移入自己的寄存器。

8 个时钟后，双方交换完一个字节。

因此软件 SPI 的核心函数通常叫：

```c
uint8_t MySPI_SwapByte(uint8_t byte_send);
```

只发送时，返回值可以忽略；只接收时，也必须发送一个无用字节，例如 `0xFF`，用它换取 8 个时钟和 8 位返回数据。

课程把这个过程形容为“抛砖引玉”：

```text
主机发送无用的 0xFF
        ↓ 产生 8 个时钟
从机返回真正需要的数据
```

## 4. 片选与模式 0 时序

### 4.1 CS 决定一次事务的开始和结束

```text
CS：高 -> 低，事务开始
CS：低 -> 高，事务结束
```

读取或写入 W25Q64 时，命令、地址和数据必须位于同一个连续事务中：

```text
CS 拉低
发送命令
发送地址
发送或接收数据
CS 拉高
```

如果在命令和地址之间拉高 CS，W25Q64 会把前面的内容当成一条已经结束但不完整的指令。

### 4.2 四种 SPI 模式

| 模式 | CPOL | CPHA | SCK 空闲电平 | 采样边沿 |
| --- | --- | --- | --- | --- |
| Mode 0 | 0 | 0 | 低 | 第一个边沿 |
| Mode 1 | 0 | 1 | 低 | 第二个边沿 |
| Mode 2 | 1 | 0 | 高 | 第一个边沿 |
| Mode 3 | 1 | 1 | 高 | 第二个边沿 |

W25Q64 支持模式 0 和模式 3。课程的软件 SPI 使用模式 0：

- SCK 默认低电平；
- MOSI 先放置一位数据；
- SCK 上升沿到来时采样；
- SCK 下降沿后准备下一位；
- 数据按高位先行发送。

### 4.3 模式 0 交换一位

```text
1. SCK 保持低电平
2. 主机把当前位放到 MOSI
3. SCK 拉高，双方采样输入
4. 主机读取 MISO
5. SCK 拉低，准备下一位
```

循环 8 次，就完成一个字节的交换。

## 5. W25Q64 是什么

W25Q64 是一颗非易失性 NOR Flash，断电后数据不会丢失。

### 5.1 容量与存储结构

W25Q64 的容量是 64 Mbit：

$$
64\ \text{Mbit} \div 8 = 8\ \text{MB}
$$

| 组织单位 | 大小 |
| --- | ---: |
| 页 Page | 256 B |
| 扇区 Sector | 4 KB |
| 32 KB 块 | 32 KB |
| 64 KB 块 | 64 KB |
| 总容量 | 8 MB |

它使用 24 位地址，范围为：

```text
0x000000 ~ 0x7FFFFF
```

地址按照高字节、中字节、低字节发送：

```c
MySPI_SwapByte((uint8_t)(address >> 16));
MySPI_SwapByte((uint8_t)(address >> 8));
MySPI_SwapByte((uint8_t)address);
```

### 5.2 WP 和 HOLD

裸芯片还有两个低电平有效引脚：

- `/WP`：写保护；
- `/HOLD`：暂停串行通信。

常见模块已经将它们上拉到 VCC，使写保护和保持功能默认不生效。本章只使用 `CS`、`CLK`、`DI`、`DO` 四根通信线。

## 6. Flash 操作必须遵守的规则

### 6.1 写入前必须写使能

W25Q64 上电后默认不允许编程和擦除。每次页编程或扇区擦除前，都要先发送：

```text
0x06：Write Enable
```

写使能必须是一个独立事务：

```text
CS 拉低 -> 发送 0x06 -> CS 拉高
```

随后再开始页编程或擦除事务。

### 6.2 编程只能把 1 改成 0

擦除后的数据是 `0xFF`，即全部位为 1。

页编程只能完成：

```text
1 -> 0
```

不能直接完成：

```text
0 -> 1
```

如果需要让某些位重新变成 1，必须先擦除它所在的整个扇区。

### 6.3 擦除的最小单位是扇区

课程使用 `0x20` 扇区擦除，一次擦除 4 KB。不能只擦除一个字节。

因此地址 `0x000000` 在本章只是测试区域。实际项目必须先规划存储地址，不能随意覆盖已有数据。

### 6.4 页编程不能跨页

一页为 256 B。一次页编程最多发送 256 B，并且：

```text
页内偏移 + 写入长度 <= 256
```

若从一页末尾继续发送数据，地址会回绕到本页开头，而不是自动进入下一页。

例如从 `0x0000F8` 开始，一次最多写：

```text
256 - 0xF8 = 8 B
```

### 6.5 擦除和编程后要等待 BUSY 清零

命令发送完成后，Flash 才开始执行内部擦除或编程。状态寄存器 1 的最低位是 BUSY：

- `BUSY = 1`：芯片仍在忙；
- `BUSY = 0`：操作完成。

不能只发完命令就立刻开始下一次读写，也不应只依赖固定延时。课程驱动通过 `0x05` 读取状态寄存器，并设置超时防止程序永久卡在循环中。

### 6.6 读取相对简单

普通读取：

- 不需要写使能；
- 可以连续跨页；
- 读取完成后不会进入忙状态；
- 但不能在 Flash 仍忙于擦除或编程时开始新操作。

## 7. 本章使用的指令

```c
// W25Q64_Ins.h
#ifndef __W25Q64_INS_H
#define __W25Q64_INS_H

#define W25Q64_WRITE_ENABLE      0x06
#define W25Q64_READ_STATUS_1     0x05
#define W25Q64_PAGE_PROGRAM      0x02
#define W25Q64_SECTOR_ERASE      0x20
#define W25Q64_READ_DATA         0x03
#define W25Q64_JEDEC_ID          0x9F

#endif
```

| 指令 | 作用 |
| --- | --- |
| `0x06` | 写使能 |
| `0x05` | 读状态寄存器 1 |
| `0x02` | 页编程 |
| `0x20` | 4 KB 扇区擦除 |
| `0x03` | 普通读数据 |
| `0x9F` | 读 JEDEC ID |

使用宏定义后，器件驱动表达的是操作含义，而不是散落的“魔法数字”。

## 8. 软件 SPI：CubeMX 配置

软件 SPI 不启用 SPI1 外设，只把四个引脚配置成普通 GPIO。

| 引脚 | 功能 | CubeMX 模式 | 初始电平 |
| --- | --- | --- | --- |
| `PA4` | CS | 推挽输出 | 高 |
| `PA5` | SCK | 推挽输出 | 低 |
| `PA6` | MISO | 输入，可上拉 | - |
| `PA7` | MOSI | 推挽输出 | 低 |

配置要点：

1. `PA4` 上电为高，保证 W25Q64 未被误选中；
2. `PA5` 上电为低，符合模式 0 的空闲状态；
3. `PA6` 必须是输入；
4. `PA7` 是主机输出；
5. 先完成 `MX_GPIO_Init()`，再调用软件 SPI 初始化。

## 9. 软件 SPI：MySPI 驱动

### 9.1 头文件

```c
// MySPI.h
#ifndef __MYSPI_H
#define __MYSPI_H

#include "main.h"
#include <stdint.h>

void MySPI_Init(void);
void MySPI_Start(void);
void MySPI_Stop(void);
uint8_t MySPI_SwapByte(uint8_t byte_send);

#endif
```

### 9.2 GPIO 基本操作

```c
// MySPI.c
#include "MySPI.h"

static void MySPI_WriteCS(GPIO_PinState state)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, state);
}

static void MySPI_WriteSCK(GPIO_PinState state)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, state);
}

static void MySPI_WriteMOSI(GPIO_PinState state)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_7, state);
}

static GPIO_PinState MySPI_ReadMISO(void)
{
    return HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_6);
}
```

这四个函数把“使用哪个端口和引脚”集中起来。后面的时序代码只表达 CS、SCK、MOSI、MISO，不需要反复写长参数。

### 9.3 初始化、开始和停止

```c
void MySPI_Init(void)
{
    MySPI_WriteCS(GPIO_PIN_SET);
    MySPI_WriteSCK(GPIO_PIN_RESET);
    MySPI_WriteMOSI(GPIO_PIN_RESET);
}

void MySPI_Start(void)
{
    MySPI_WriteCS(GPIO_PIN_RESET);
}

void MySPI_Stop(void)
{
    MySPI_WriteCS(GPIO_PIN_SET);
}
```

对应关系是：

```text
Init：CS=1，SCK=0
Start：CS=0
Stop：CS=1
```

### 9.4 交换一个字节

```c
uint8_t MySPI_SwapByte(uint8_t byte_send)
{
    uint8_t byte_receive = 0x00;
    uint8_t i;

    for (i = 0; i < 8U; i++)
    {
        /* 模式 0：先改变 MOSI，再在 SCK 上升沿采样 MISO。 */
        MySPI_WriteMOSI(
            ((byte_send & (0x80U >> i)) != 0U)
                ? GPIO_PIN_SET
                : GPIO_PIN_RESET
        );

        MySPI_WriteSCK(GPIO_PIN_SET);

        if (MySPI_ReadMISO() == GPIO_PIN_SET)
        {
            byte_receive |= (uint8_t)(0x80U >> i);
        }

        MySPI_WriteSCK(GPIO_PIN_RESET);
    }

    return byte_receive;
}
```

逐步分析：

1. `0x80 >> i` 依次产生 `10000000`、`01000000`、……、`00000001`；
2. 与发送字节按位与，取出当前位；
3. MOSI 在 SCK 上升沿前已经稳定；
4. 拉高 SCK，在第一个边沿采样；
5. 若 MISO 为高，就把接收字节的对应位置 1；
6. 拉低 SCK，进入下一位。

这里写成 `!= 0U`，是把任意非零的掩码结果规范为明确的高电平，而不是依赖 `HAL_GPIO_WritePin()` 把所有非零值都当作置位。

## 10. 软件 SPI：先完成读 ID

第 26 课先用读 ID 验证软件时序。这是最小、最清晰的通信闭环。

### 10.1 W25Q64 初始化和读 ID

```c
// W25Q64.c：软件 SPI 版本
#include "W25Q64.h"
#include "W25Q64_Ins.h"
#include "MySPI.h"

void W25Q64_Init(void)
{
    MySPI_Init();
}

void W25Q64_ReadID(uint8_t *manufacturer_id,
                   uint16_t *device_id)
{
    MySPI_Start();

    MySPI_SwapByte(W25Q64_JEDEC_ID);

    *manufacturer_id = MySPI_SwapByte(0xFF);

    *device_id = MySPI_SwapByte(0xFF);
    *device_id <<= 8;
    *device_id |= MySPI_SwapByte(0xFF);

    MySPI_Stop();
}
```

`0x9F` 返回三个字节：

```text
第 1 字节：Manufacturer ID
第 2 字节：Memory Type
第 3 字节：Capacity
```

后两个字节拼成 16 位器件 ID：

```c
device_id = ((uint16_t)high_byte << 8) | low_byte;
```

发送的三个 `0xFF` 没有业务含义，它们只负责产生时钟，把 W25Q64 的三个 ID 字节换回来。

### 10.2 主程序验证

```c
uint8_t manufacturer_id;
uint16_t device_id;

MX_GPIO_Init();
OLED_Init();

W25Q64_Init();
W25Q64_ReadID(&manufacturer_id, &device_id);

OLED_ShowString(1, 1, "MID:");
OLED_ShowHexNum(1, 5, manufacturer_id, 2);

OLED_ShowString(1, 9, "DID:");
OLED_ShowHexNum(1, 13, device_id, 4);
```

预期显示：

```text
MID: EF
DID: 4017
```

如果 ID 不正确，先不要继续写入实验。软件 SPI 的接线、CS 和模式 0 时序必须先验收通过。

## 11. W25Q64 完整指令流程

第 27 课在硬件 SPI 工程中重点解释这些函数。它们同样可以建立在软件 SPI 的 `MySPI_SwapByte()` 之上。

### 11.1 写使能

```c
static void W25Q64_WriteEnable(void)
{
    MySPI_Start();
    MySPI_SwapByte(W25Q64_WRITE_ENABLE);
    MySPI_Stop();
}
```

`0x06` 自己构成一条事务。发送完成并拉高 CS 后，写使能锁存位 WEL 才会置位。

### 11.2 等待不忙

```c
static uint8_t W25Q64_WaitBusy(uint32_t timeout_ms)
{
    uint32_t start_tick = HAL_GetTick();
    uint8_t status;

    MySPI_Start();
    MySPI_SwapByte(W25Q64_READ_STATUS_1);

    do
    {
        status = MySPI_SwapByte(0xFF);

        if ((HAL_GetTick() - start_tick) >= timeout_ms)
        {
            MySPI_Stop();
            return 1U;
        }
    } while ((status & 0x01U) != 0U);

    MySPI_Stop();
    return 0U;
}
```

只发送一次 `0x05`，随后在 CS 保持低电平时连续读取状态。循环必须同时具备两个退出条件：

- `BUSY` 清零；
- 达到超时时间。

没有超时的忙等待可能让整个程序永久卡死。

### 11.3 页编程

```c
uint8_t W25Q64_PageProgram(uint32_t address,
                           const uint8_t *data,
                           uint16_t count)
{
    uint16_t i;
    uint16_t page_offset;

    if ((data == NULL) || (count == 0U) || (count > 256U))
    {
        return 1U;
    }

    page_offset = (uint16_t)(address & 0xFFU);
    if ((uint16_t)(page_offset + count) > 256U)
    {
        return 1U;
    }

    if (W25Q64_WaitBusy(1000U) != 0U)
    {
        return 1U;
    }

    W25Q64_WriteEnable();

    MySPI_Start();
    MySPI_SwapByte(W25Q64_PAGE_PROGRAM);
    MySPI_SwapByte((uint8_t)(address >> 16));
    MySPI_SwapByte((uint8_t)(address >> 8));
    MySPI_SwapByte((uint8_t)address);

    for (i = 0; i < count; i++)
    {
        MySPI_SwapByte(data[i]);
    }

    MySPI_Stop();

    return W25Q64_WaitBusy(1000U);
}
```

标准事务为：

```text
写使能
CS 拉低
0x02 + 24 位地址 + 本页数据
CS 拉高
等待 BUSY=0
```

课程原理强调“页编程不能跨页”。这里把这个条件直接写成参数检查，防止数据在当前页内回绕。

### 11.4 扇区擦除

```c
uint8_t W25Q64_SectorErase(uint32_t address)
{
    if (W25Q64_WaitBusy(1000U) != 0U)
    {
        return 1U;
    }

    W25Q64_WriteEnable();

    MySPI_Start();
    MySPI_SwapByte(W25Q64_SECTOR_ERASE);
    MySPI_SwapByte((uint8_t)(address >> 16));
    MySPI_SwapByte((uint8_t)(address >> 8));
    MySPI_SwapByte((uint8_t)address);
    MySPI_Stop();

    return W25Q64_WaitBusy(1000U);
}
```

地址用于选择所在扇区。为了让地址含义更明确，调用时通常传入 4 KB 对齐地址，例如 `0x000000`、`0x001000`。

### 11.5 读取数据

```c
uint8_t W25Q64_ReadData(uint32_t address,
                        uint8_t *data,
                        uint16_t count)
{
    uint16_t i;

    if ((data == NULL) || (count == 0U))
    {
        return 1U;
    }

    if (W25Q64_WaitBusy(1000U) != 0U)
    {
        return 1U;
    }

    MySPI_Start();
    MySPI_SwapByte(W25Q64_READ_DATA);
    MySPI_SwapByte((uint8_t)(address >> 16));
    MySPI_SwapByte((uint8_t)(address >> 8));
    MySPI_SwapByte((uint8_t)address);

    for (i = 0; i < count; i++)
    {
        data[i] = MySPI_SwapByte(0xFF);
    }

    MySPI_Stop();

    return 0U;
}
```

读取不需要写使能，也没有页边界限制。每发送一个占位字节，就读取一个有效数据字节。

## 12. 软件 SPI 完整实验

```c
#include "W25Q64.h"
#include <string.h>

uint8_t manufacturer_id;
uint16_t device_id;

uint8_t write_data[4] = {0x01, 0x02, 0x03, 0x04};
uint8_t read_data[4] = {0};

uint8_t flash_error;
uint8_t data_match;
```

初始化和测试：

```c
MX_GPIO_Init();
OLED_Init();

W25Q64_Init();
W25Q64_ReadID(&manufacturer_id, &device_id);

flash_error = W25Q64_SectorErase(0x000000);

if (flash_error == 0U)
{
    flash_error = W25Q64_PageProgram(
        0x000000,
        write_data,
        sizeof(write_data)
    );
}

if (flash_error == 0U)
{
    flash_error = W25Q64_ReadData(
        0x000000,
        read_data,
        sizeof(read_data)
    );
}

data_match =
    (flash_error == 0U) &&
    (memcmp(write_data, read_data, sizeof(write_data)) == 0);
```

OLED 显示可按已有库调整：

```c
OLED_ShowString(1, 1, "MID:");
OLED_ShowHexNum(1, 5, manufacturer_id, 2);
OLED_ShowString(1, 9, "DID:");
OLED_ShowHexNum(1, 13, device_id, 4);

OLED_ShowString(2, 1, "W:");
OLED_ShowHexNum(2, 3, write_data[0], 2);
OLED_ShowHexNum(2, 6, write_data[1], 2);
OLED_ShowHexNum(2, 9, write_data[2], 2);
OLED_ShowHexNum(2, 12, write_data[3], 2);

OLED_ShowString(3, 1, "R:");
OLED_ShowHexNum(3, 3, read_data[0], 2);
OLED_ShowHexNum(3, 6, read_data[1], 2);
OLED_ShowHexNum(3, 9, read_data[2], 2);
OLED_ShowHexNum(3, 12, read_data[3], 2);

OLED_ShowString(4, 1, data_match ? "PASS" : "FAIL");
```

完整链路是：

```text
初始化软件 SPI
    -> 读取 ID
        -> 擦除 0x000000 所在扇区
            -> 写入 01 02 03 04
                -> 读回 4 字节
                    -> 逐字节比较
```

## 13. 硬件 SPI1：为什么要替换软件时序

软件 SPI 由 CPU 逐次操作 GPIO。硬件 SPI 则由 STM32 内部外设自动完成：

- 时钟生成；
- 8 位移位；
- 数据发送；
- 数据接收；
- 标志位管理。

硬件 SPI 的优点是速度更高、CPU 负担更小；代价是引脚和配置受外设复用功能约束。

第 27 课使用 SPI1：

```text
PA5 -> SCK
PA6 -> MISO
PA7 -> MOSI
PA4 -> 普通 GPIO，软件控制 CS
```

片选仍由软件控制，因为这样最容易保证命令、地址和数据处于同一个 W25Q64 事务。

## 14. 硬件 SPI1：CubeMX 配置

在 `Connectivity -> SPI1` 中选择：

- `Mode = Full-Duplex Master`
- `Hardware NSS Signal = Disable`
- `Data Size = 8 Bits`
- `First Bit = MSB First`
- `Clock Polarity = Low`
- `Clock Phase = 1 Edge`
- `Baud Rate Prescaler = 4`
- `CRC Calculation = Disabled`

同时把 `PA4` 配成普通 GPIO 推挽输出，初始高电平。

这组 CPOL/CPHA 对应模式 0。

若 APB2 外设时钟为 72 MHz，4 分频得到：

$$
f_{SCK}=\frac{72\ \text{MHz}}{4}=18\ \text{MHz}
$$

课程工程选择 4 分频。首次使用面包板或较长杜邦线调试时，可以先选择 64 或 128 分频，读 ID 和回读稳定后再提高速度。

硬件工程的初始化顺序必须包含：

```c
MX_GPIO_Init();
MX_SPI1_Init();
OLED_Init();
W25Q64_Init();
```

如果漏掉 `MX_SPI1_Init()`，`hspi1` 还没有正确配置。

## 15. 硬件 SPI1：用 HAL 改写底层收发

### 15.1 片选宏

```c
#define W25Q64_CS_LOW() \
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET)

#define W25Q64_CS_HIGH() \
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET)

#define W25Q64_SPI_TIMEOUT 1000U
```

### 15.2 初始化与读 ID

```c
#include "W25Q64.h"
#include "W25Q64_Ins.h"
#include "spi.h"

void W25Q64_Init(void)
{
    W25Q64_CS_HIGH();
}

uint8_t W25Q64_ReadID(uint8_t *manufacturer_id,
                      uint16_t *device_id)
{
    uint8_t command = W25Q64_JEDEC_ID;
    uint8_t response[3] = {0U};

    if ((manufacturer_id == NULL) || (device_id == NULL))
    {
        return 1U;
    }

    W25Q64_CS_LOW();
    /* 擦除/编程期间 BUSY=1，清零后才能开始下一事务。 */

    if (HAL_SPI_Transmit(
        &hspi1,
        &command,
        1,
        W25Q64_SPI_TIMEOUT
    ) != HAL_OK)
    {
        W25Q64_CS_HIGH();
        return 1U;
    }

    if (HAL_SPI_Receive(
        &hspi1,
        response,
        3,
        W25Q64_SPI_TIMEOUT
    ) != HAL_OK)
    {
        W25Q64_CS_HIGH();
        return 1U;
    }

    W25Q64_CS_HIGH();

    *manufacturer_id = response[0];
    *device_id = ((uint16_t)response[1] << 8) | response[2];
    return 0U;
}
```

软件 SPI 的三次 `SwapByte(0xFF)`，在硬件 SPI 中对应一次接收 3 字节。主机模式下，HAL 接收过程仍会产生时钟。

### 15.3 写使能

```c
static uint8_t W25Q64_WriteEnable(void)
{
    uint8_t command = W25Q64_WRITE_ENABLE;

    W25Q64_CS_LOW();

    if (HAL_SPI_Transmit(
        &hspi1,
        &command,
        1,
        W25Q64_SPI_TIMEOUT
    ) != HAL_OK)
    {
        W25Q64_CS_HIGH();
        return 1U;
    }

    W25Q64_CS_HIGH();
    return 0U;
}
```

### 15.4 等待不忙

```c
static uint8_t W25Q64_WaitBusy(uint32_t timeout_ms)
{
    uint8_t command = W25Q64_READ_STATUS_1;
    uint8_t status;
    uint32_t start_tick = HAL_GetTick();

    W25Q64_CS_LOW();

    if (HAL_SPI_Transmit(
        &hspi1,
        &command,
        1,
        W25Q64_SPI_TIMEOUT
    ) != HAL_OK)
    {
        W25Q64_CS_HIGH();
        return 1U;
    }

    do
    {
        if (HAL_SPI_Receive(
            &hspi1,
            &status,
            1,
            W25Q64_SPI_TIMEOUT
        ) != HAL_OK)
        {
            W25Q64_CS_HIGH();
            return 1U;
        }

        if ((HAL_GetTick() - start_tick) >= timeout_ms)
        {
            W25Q64_CS_HIGH();
            return 1U;
        }
    } while ((status & 0x01U) != 0U);

    W25Q64_CS_HIGH();
    return 0U;
}
```

第 27 课特别强调超时的作用：即使芯片异常或接线断开，程序也不能永久卡在 BUSY 循环里。

### 15.5 页编程

```c
uint8_t W25Q64_PageProgram(uint32_t address,
                           const uint8_t *data,
                           uint16_t count)
{
    uint8_t command_address[4];

    if ((data == NULL) ||
        (count == 0U) ||
        (count > 256U) ||
        (((address & 0xFFU) + count) > 256U))
    {
        return 1U;
    }

    if (W25Q64_WaitBusy(1000U) != 0U)
    {
        return 1U;
    }

    if (W25Q64_WriteEnable() != 0U)
    {
        return 1U;
    }

    command_address[0] = W25Q64_PAGE_PROGRAM;
    command_address[1] = (uint8_t)(address >> 16);
    command_address[2] = (uint8_t)(address >> 8);
    command_address[3] = (uint8_t)address;

    W25Q64_CS_LOW();

    if (HAL_SPI_Transmit(
        &hspi1,
        command_address,
        4,
        W25Q64_SPI_TIMEOUT
    ) != HAL_OK)
    {
        W25Q64_CS_HIGH();
        return 1U;
    }

    if (HAL_SPI_Transmit(
        &hspi1,
        (uint8_t *)data,
        count,
        W25Q64_SPI_TIMEOUT
    ) != HAL_OK)
    {
        W25Q64_CS_HIGH();
        return 1U;
    }

    W25Q64_CS_HIGH();

    return W25Q64_WaitBusy(1000U);
}
```

课程讲解中，“命令 + 3 字节地址”一共占 4 字节，然后再发送待写数组。

### 15.6 扇区擦除

```c
uint8_t W25Q64_SectorErase(uint32_t address)
{
    uint8_t command_address[4];

    if (W25Q64_WaitBusy(1000U) != 0U)
    {
        return 1U;
    }

    if (W25Q64_WriteEnable() != 0U)
    {
        return 1U;
    }

    command_address[0] = W25Q64_SECTOR_ERASE;
    command_address[1] = (uint8_t)(address >> 16);
    command_address[2] = (uint8_t)(address >> 8);
    command_address[3] = (uint8_t)address;

    W25Q64_CS_LOW();

    if (HAL_SPI_Transmit(
        &hspi1,
        command_address,
        4,
        W25Q64_SPI_TIMEOUT
    ) != HAL_OK)
    {
        W25Q64_CS_HIGH();
        return 1U;
    }

    W25Q64_CS_HIGH();

    return W25Q64_WaitBusy(1000U);
}
```

一次扇区擦除至少影响 4 KB，不能把它理解为“删除某一个字节”。

### 15.7 读取数据

```c
uint8_t W25Q64_ReadData(uint32_t address,
                        uint8_t *data,
                        uint16_t count)
{
    uint8_t command_address[4];

    if ((data == NULL) || (count == 0U))
    {
        return 1U;
    }

    if (W25Q64_WaitBusy(1000U) != 0U)
    {
        return 1U;
    }

    command_address[0] = W25Q64_READ_DATA;
    command_address[1] = (uint8_t)(address >> 16);
    command_address[2] = (uint8_t)(address >> 8);
    command_address[3] = (uint8_t)address;

    W25Q64_CS_LOW();

    if (HAL_SPI_Transmit(
        &hspi1,
        command_address,
        4,
        W25Q64_SPI_TIMEOUT
    ) != HAL_OK)
    {
        W25Q64_CS_HIGH();
        return 1U;
    }

    if (HAL_SPI_Receive(
        &hspi1,
        data,
        count,
        W25Q64_SPI_TIMEOUT
    ) != HAL_OK)
    {
        W25Q64_CS_HIGH();
        return 1U;
    }

    W25Q64_CS_HIGH();

    return 0U;
}
```

硬件 SPI 与软件 SPI 的事务完全对应：

| 软件 SPI | 硬件 SPI |
| --- | --- |
| `MySPI_SwapByte(command)` | `HAL_SPI_Transmit()` |
| 多次 `MySPI_SwapByte(data)` | 一次发送数据数组 |
| 多次 `MySPI_SwapByte(0xFF)` | `HAL_SPI_Receive()` |
| `MySPI_Start/Stop()` | GPIO 拉低/拉高 CS |

## 16. 硬件 SPI 完整实验

主程序的上层调用顺序与软件 SPI 相同：

```c
MX_GPIO_Init();
MX_SPI1_Init();
OLED_Init();

W25Q64_Init();
flash_error = W25Q64_ReadID(&manufacturer_id, &device_id);

if (flash_error == 0U)
{
    flash_error = W25Q64_SectorErase(0x000000);
}

if (flash_error == 0U)
{
    flash_error = W25Q64_PageProgram(
        0x000000,
        write_data,
        sizeof(write_data)
    );
}

if (flash_error == 0U)
{
    flash_error = W25Q64_ReadData(
        0x000000,
        read_data,
        sizeof(read_data)
    );
}
```

预期结果仍然是：

```text
MID: EF
DID: 4017
W: 01 02 03 04
R: 01 02 03 04
```

这说明：

- 软件 SPI 与硬件 SPI 改变的是底层字节传输方法；
- W25Q64 的命令、地址、片选边界和状态机顺序没有变化。

## 17. 三类事务必须会读

### 17.1 读取 JEDEC ID

```text
CS 拉低
发送 0x9F
接收 Manufacturer ID
接收 Memory Type
接收 Capacity
CS 拉高
```

### 17.2 扇区擦除

```text
事务 1：CS 低 -> 0x06 -> CS 高

事务 2：
CS 低
0x20 + 24 位地址
CS 高

事务 3：
0x05 + 连续读取状态
直到 BUSY=0
```

### 17.3 页编程

```text
事务 1：写使能

事务 2：
CS 低
0x02 + 24 位地址 + 数据
CS 高

事务 3：等待 BUSY=0
```

写使能和编程命令不能放在同一个 CS 低电平事务中。

## 18. 软件 SPI 与硬件 SPI 对比

| 项目 | 软件 SPI | 硬件 SPI |
| --- | --- | --- |
| 时钟 | CPU 翻转 GPIO | SPI1 自动生成 |
| 字节交换 | 循环 8 次 | 外设移位寄存器完成 |
| 引脚 | 较灵活 | 受复用功能限制 |
| 速度 | 较低 | 较高 |
| CPU 占用 | 高 | 低 |
| 教学价值 | 时序直观 | 理解 HAL 与硬件外设 |
| W25Q64 指令 | 相同 | 相同 |
| CS 边界 | 必须正确 | 必须正确 |

软件 SPI 的目的不是追求速度，而是把时序变成可以逐行阅读的代码。硬件 SPI 的目的，是让外设自动执行已经理解的时序。

## 19. 验收顺序与故障定位

### 19.1 推荐验收顺序

1. 检查 3.3 V、电源地和接线；
2. 只读取 JEDEC ID；
3. 擦除测试扇区；
4. 读回并确认数据为 `0xFF`；
5. 写入 `01 02 03 04`；
6. 再次读回；
7. 使用 `memcmp()` 逐字节比较；
8. 软件 SPI 成功后再切换硬件 SPI。

### 19.2 ID 全为 `FF`

优先检查：

- CS 是否没有拉低；
- PA6/MISO 是否悬空或接错；
- DI 与 DO 是否接反；
- W25Q64 是否未供电或没有共地；
- 软件 SPI 是否没有产生 SCK；
- 硬件 SPI 分频是否过高。

### 19.3 ID 全为 `00`

检查：

- PA6 是否误配置为输出；
- MISO 是否短路到地；
- SCK 是否没有翻转；
- 模式和采样边沿是否错误。

### 19.4 ID 正确但写不进去

依次检查：

1. 页编程和擦除前是否发送 `0x06`；
2. 目标区域是否已经擦除；
3. 编程是否跨页；
4. 命令、地址和数据是否处于同一个 CS 事务；
5. 操作后是否等待 BUSY 清零；
6. 地址是否在 `0x000000 ~ 0x7FFFFF`；
7. HAL 接口是否返回错误或超时。

### 19.5 软件 SPI 正常，硬件 SPI 失败

说明 W25Q64 指令层大概率正确，重点检查：

- `MX_SPI1_Init()` 是否执行；
- `Full-Duplex Master`；
- `8 Bits`；
- `MSB First`；
- `CPOL Low`；
- `CPHA 1 Edge`；
- NSS 是否禁用；
- PA4 是否仍由普通 GPIO 控制；
- 分频是否过小。

### 19.6 硬件 SPI 正常，软件 SPI 失败

重点检查：

- CS 初始是否为高；
- SCK 初始是否为低；
- MOSI 是否在上升沿前稳定；
- 是否在 SCK 高电平时读取 MISO；
- 是否循环恰好 8 次；
- 是否从最高位 `0x80` 开始；
- 接收时是否发送了占位字节。


## 20. 自测

### 题 1

为什么读取 ID 时要在发送 `0x9F` 后继续发送或产生三个字节的时钟？

### 题 2

为什么 PA4/CS 初始化必须为高电平？

### 题 3

为什么写使能 `0x06` 必须和页编程 `0x02` 分成两个事务？

### 题 4

从地址 `0x0000F8` 开始，一次页编程最多能写多少字节？

### 题 5

擦除命令已经发送结束，为什么不能立刻开始页编程？

### 题 6

软件 SPI 能正确读出 `EF 40 17`，硬件 SPI 却全为 `FF`，应该优先检查哪一层？

### 参考答案

1. SPI 接收依赖主机时钟。发送占位字节或调用硬件接收，是为了继续产生时钟，把三个 ID 字节移出来。
2. CS 低电平表示选中器件。初始化为高可避免上电和 GPIO 配置期间产生不完整指令。
3. CS 上升沿结束并锁存一条指令。必须先结束 `0x06` 事务使 WEL 置位，再开始编程事务。
4. 页内偏移是 `0xF8 = 248`，剩余 `256 - 248 = 8` B。
5. CS 拉高后 Flash 才开始内部擦除。必须读取状态寄存器，等待 BUSY 清零。
6. 优先检查硬件 SPI 总线层，包括 CubeMX 模式、位序、分频、NSS、PA4 片选和 `MX_SPI1_Init()`。

## 21. 一页回顾

- SPI 使用 SCK、MOSI、MISO、CS，是同步全双工通信。
- 8 个时钟完成一个字节交换；只接收时也要产生时钟。
- 课程软件 SPI 使用模式 0：SCK 空闲低，上升沿采样，MSB 先行。
- 软件 SPI 使用 PA4、PA5、PA6、PA7，分别对应 CS、SCK、MISO、MOSI。
- W25Q64 容量 64 Mbit，即 8 MB；页 256 B，扇区 4 KB。
- `0x9F` 读 ID，`0x06` 写使能，`0x05` 读状态。
- `0x02` 页编程，`0x20` 扇区擦除，`0x03` 读数据。
- 编程只能把 1 改成 0；要恢复为 1，必须先擦除。
- 页编程不能跨页，擦除和编程后必须等待 BUSY 清零。
- 第 26 课用软件 SPI 看清时序，第 27 课用硬件 SPI/HAL 完成同一套 W25Q64 事务。
- 最终验收链：读 ID -> 擦除 -> 写入 -> 回读 -> 比较。
