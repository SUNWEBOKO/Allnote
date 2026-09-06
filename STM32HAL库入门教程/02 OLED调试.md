# OLED 调试显示（HAL 库）

## 学习目标

完成本章后，你应能：

- 用 CubeMX 配置 `I2C2`，并把 SSD1306 驱动加入 HAL 工程；
- 解释 `0x3C`、`0x78` 与 STM32 HAL 地址参数的关系；
- 分别用“清帧—绘制—刷新”帧接口和行列式兼容接口完成文字、变量和图形显示；
- 根据现象把故障定位到供电、总线、驱动接入或绘图层。

前置条件：已能创建 STM32F103 HAL 工程，了解 `main.c`、GPIO 和 CubeMX 代码生成流程。

## 1. 先建立显示数据流

本章把 OLED 当作一个本地调试终端。应用代码不直接改屏幕，而是先修改 MCU 内存中的显存，再把整帧数据发送给 SSD1306：

```text
CubeMX 配置 I2C2
        ↓
MX_I2C2_Init() 创建并初始化 hi2c2
        ↓
OLED_Init() 初始化 SSD1306
        ↓
OLED_NewFrame() 清空 MCU 显存
        ↓
文字/变量/图形函数修改显存
        ↓
OLED_ShowFrame() 逐页发送整帧
        ↓
OLED 屏幕更新
```

当前驱动来自 `E:\ProjectStm\驱动库\OLED`，需要四个文件：

```text
oled.c   oled.h
font.c   font.h
```

| 项目 | 当前驱动配置 |
| --- | --- |
| 控制器 | SSD1306 |
| 分辨率 | `128x64`，单色 |
| 总线 | `I2C2`，句柄 `hi2c2` |
| HAL 地址参数 | `0x78` |
| 7 位从机地址 | `0x3C` |
| 刷新方式 | MCU 显存绘制后整帧刷新 |

驱动已经封装了初始化命令、字模读取和基础图形算法。本章重点是正确接入和调用，不要求立即重写驱动内部实现。

## 2. 硬件连接与总线前提

四针 I2C OLED 通常有 `GND`、`VCC`、`SCL`、`SDA`：

| OLED | STM32F103 常见连接 | 作用 |
| --- | --- | --- |
| `GND` | `GND` | 共地 |
| `VCC` | `3.3V` 或模块规定电源 | 供电 |
| `SCL` | `PB10 / I2C2_SCL` | 时钟 |
| `SDA` | `PB11 / I2C2_SDA` | 数据 |

```text
PB10 / I2C2_SCL  --------  SCL
PB11 / I2C2_SDA  --------  SDA
3.3 V            --------  VCC
GND              --------  GND
```

STM32 和 OLED 必须共地，`SCL` 与 `SDA` 不能接反。I2C 使用开漏输出并依靠上拉电阻恢复高电平，多数成品模块已自带上拉，但仍应查看模块资料。`PB10/PB11` 若被 USART3 等外设占用，必须先在 CubeMX 中解决引脚冲突。第 9 章的 MPU6050 同样使用 I2C2，其 7 位地址 `0x68` 与 OLED 的 `0x3C` 不同，两者可直接并联在同一总线。

## 3. 地址和驱动绑定

驱动底层发送函数直接使用 `hi2c2` 与 `OLED_ADDRESS`：

```c
#define OLED_ADDRESS 0x78

void OLED_Send(uint8_t *data, uint8_t len)
{
    /* HAL 使用左移后的地址；0x78 对应 7 位地址 0x3C。 */
    HAL_I2C_Master_Transmit(
        &hi2c2,
        OLED_ADDRESS,
        data,
        len,
        HAL_MAX_DELAY);
}
```

SSD1306 常见的 7 位地址是 `0x3C`，部分模块通过跳线或电阻配置为 `0x3D`。应先用 I²C 扫描或查看模块资料确认地址。STM32 HAL 的主机收发接口通常接收左移一位后的地址，因此：

```text
7 位地址：0x3C
HAL 参数：0x3C << 1 = 0x78
```

所以在当前工程中（模块 7 位地址为 `0x3C`），`HAL_I2C_IsDeviceReady()` 和 `HAL_I2C_Master_Transmit()` 都传 `0x78`；若模块实际为 `0x3D`，HAL 参数应改为 `0x7A`。不要把已经左移后的参数再次左移。

这也决定了接入工程必须同时满足：

1. 已生成 `MX_I2C2_Init()`；
2. 工程中存在全局句柄 `I2C_HandleTypeDef hi2c2`；
3. `OLED_Init()` 调用前已经执行 `MX_I2C2_Init()`。

若改用 I2C1，必须同时修改驱动句柄、CubeMX 外设配置和实际接线；只改其中一处不能完成移植。

## 4. CubeMX 配置和文件接入

### 4.1 配置 I2C2

1. 选择目标 STM32 型号，在 `SYS` 中保留 `Serial Wire`。
2. 将 `I2C2` 设置为 `I2C` 模式。
3. 确认 `PB10` 为 `I2C2_SCL`、`PB11` 为 `I2C2_SDA`。
4. 入门阶段把时钟设为 `100 kHz`。
5. 生成工程，确认 `i2c.c` 中有 `hi2c2` 和 `MX_I2C2_Init()`。

当前驱动调用阻塞式 `HAL_I2C_Master_Transmit()`，入门实验不需要额外开启 I2C 中断或 DMA。先跑通低速总线，再根据刷新速度和信号质量评估是否提速。

### 4.2 加入驱动文件

可将四个文件放入 `Drivers/OLED`：

1. 将 `oled.c`、`font.c` 加入编译目标；
2. 将驱动目录加入 Include Paths；
3. 在 `main.c` 用户包含区加入 `#include "oled.h"`。

`oled.c` 依赖 CubeMX 生成的 `i2c.h`，`oled.h` 依赖 `main.h`。找不到头文件时先查目录和包含路径；只添加头文件而未编译 `oled.c`、`font.c`，则会在链接阶段出现函数或字体对象未定义。

## 5. 显存模型和刷新边界

驱动维护：

```c
uint8_t OLED_GRAM[8][128];
```

坐标原点在左上角：`x=0~127` 向右增加，`y=0~63` 向下增加。SSD1306 按页组织纵向像素，每页对应 8 行：

```text
OLED_GRAM[0][x] -> y = 0~7
OLED_GRAM[1][x] -> y = 8~15
...
OLED_GRAM[7][x] -> y = 56~63
```

一帧显示必须按以下顺序完成：

```c
OLED_NewFrame();   // 清空 MCU 中的显存
/* 绘制文字、图形或图片 */
OLED_ShowFrame();  // 逐页发送到 SSD1306
```

`OLED_NewFrame()` 和所有绘图函数只改 RAM；`OLED_ShowFrame()` 才会发送命令和数据。绘制后忘记刷新，是“程序运行但屏幕不变”的首要原因。源码中的 `OLED_ShowFrame()` 会循环发送 8 页，每页 128 字节显示数据。

## 6. 最小显示实验

将代码放入 `USER CODE` 区域，避免 CubeMX 重新生成时被覆盖：

```c
/* USER CODE BEGIN Includes */
#include "oled.h"
/* USER CODE END Includes */

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_I2C2_Init();

    HAL_Delay(20U);  /* 给模块留出上电稳定时间 */
    OLED_Init();

    OLED_NewFrame();  /* 先在 RAM 显存中绘制整帧。 */
    OLED_PrintASCIIString(0, 0, "STM32 HAL", &afont16x8,
                          OLED_COLOR_NORMAL);
    OLED_PrintString(0, 24, "波特律动", &font16x16,
                     OLED_COLOR_NORMAL);
    OLED_DrawRectangle(0, 48, 127, 15, OLED_COLOR_NORMAL);
    OLED_ShowFrame();

    while (1)
    {
    }
}
```

预期现象是英文、字库中已有的中文以及底部矩形框同时出现。若英文正常而中文为空格，优先检查源文件/编译器编码和中文字库，而不是先怀疑 I2C。

## 7. 显示文字、变量和中文

### 7.1 ASCII 字体与坐标

当前 `font.c` 提供：

| 字体对象 | 字符尺寸 | 用途 |
| --- | ---: | --- |
| `afont8x6` | `6x8` | 小标签、状态栏 |
| `afont12x6` | `6x12` | 紧凑正文 |
| `afont16x8` | `8x16` | 常规调试信息 |
| `afont24x12` | `12x24` | 大号数值或标题 |

例如：

```c
OLED_PrintASCIIString(0, 0, "ADC:", &afont16x8,
                      OLED_COLOR_NORMAL);
```

字符串函数会按字体宽度向右绘制，但不会自动换行。使用 `afont16x8` 时，每个字符宽 8 像素，一行最多容纳 16 个完整字符；应用层要预留字符串长度对应的宽度。

### 7.2 行列式兼容接口（Show 系列）

为方便快速调试和后续章节直接调用，驱动库在显存帧接口之上提供一组“行、列”兼容接口，固定使用 `afont16x8`（宽 8、高 16），把整屏划分为 4 行 × 16 列，行、列编号都从 `1` 开始：

| 函数 | 说明 |
| --- | --- |
| `OLED_ShowChar(Line, Column, Char)` | 显示单个 ASCII 字符 |
| `OLED_ShowString(Line, Column, String)` | 从指定位置向右显示字符串，超出第 16 列裁剪 |
| `OLED_ShowNum(Line, Column, Number, Length)` | 无符号十进制，固定 `Length` 位，高位补 `0` |
| `OLED_ShowSignedNum(Line, Column, Number, Length)` | 先显示 `+` 或 `-`，再显示 `Length` 位数字，共占 `Length + 1` 列 |
| `OLED_ShowHexNum(Line, Column, Number, Length)` | 大写十六进制，固定 `Length` 位，不带 `0x` 前缀 |
| `OLED_ShowBinNum(Line, Column, Number, Length)` | 二进制，固定 `Length` 位 |

```c
OLED_ShowString(1, 1, "CNT:");
OLED_ShowNum(1, 6, 2048U, 4U);      /* 显示 CNT:2048 */
OLED_ShowSignedNum(2, 1, -125, 5);  /* 显示 -00125 */
OLED_ShowHexNum(3, 1, 0xA5U, 2U);   /* 显示 A5 */
```

使用边界有三条：

1. 兼容函数内部仍然写 `OLED_GRAM`，并在返回前自动调用一次 `OLED_ShowFrame()` 整帧刷新；可与绘图函数混用，但同样不能在中断中调用；
2. 每次调用都发送整帧约 1 KB 数据，`100 kHz` 下单次刷新需要几十毫秒；同一屏更新多个值时优先合并为一次“清帧—绘制—刷新”，或提高 I2C 时钟后再使用兼容接口；
3. 起始行列越界时函数不动作；`Length` 应结合起始列和剩余宽度选择。

后续章节示例中的 `OLED_ShowNum()`、`OLED_ShowSignedNum()`、`OLED_ShowString()`、`OLED_ShowHexNum()` 均指这组接口。

### 7.3 用 `snprintf()` 格式化显示

需要变长字符串、右对齐、浮点数或拼接多段内容时，先用 `snprintf()` 生成字符串再绘制：

```c
#include <stdio.h>

char text[20];
uint16_t adc_value = 2048U;
int16_t speed = -125;

OLED_NewFrame();

snprintf(text, sizeof(text), "ADC:%u",
         (unsigned int)adc_value);
OLED_PrintASCIIString(0, 0, text, &afont16x8,
                      OLED_COLOR_NORMAL);

snprintf(text, sizeof(text), "SPD:%d", (int)speed);
OLED_PrintASCIIString(0, 20, text, &afont16x8,
                      OLED_COLOR_NORMAL);

snprintf(text, sizeof(text), "REG:%02X",
         (unsigned int)0xA5U);
OLED_PrintASCIIString(0, 40, text, &afont16x8,
                      OLED_COLOR_NORMAL);

OLED_ShowFrame();
```

`%u` 用于无符号十进制，`%d` 用于有符号十进制，`%X` 用于寄存器或通信数据。`snprintf()` 的缓冲区必须包含结尾的 `\0`；空间不足时字符串会被截断，因此要按最大可能位数留余量。

### 7.4 中文字库的边界

```c
OLED_PrintString(0, 0, "波特律动", &font16x16,
                 OLED_COLOR_NORMAL);
```

中文显示同时依赖四个条件：源文件是 UTF-8、编译器按 UTF-8 解释字符串、`font.c` 包含目标汉字、字模格式与驱动读取方向一致。`font16x16` 只覆盖字库中实际定义的汉字；驱动不会自动为任意汉字生成点阵。缺字时应先生成并加入字模。

## 8. 图形、图片和颜色模式

```c
OLED_NewFrame();
OLED_DrawLine(0, 0, 127, 63, OLED_COLOR_NORMAL);
OLED_DrawCircle(32, 32, 15, OLED_COLOR_NORMAL);
OLED_DrawFilledRectangle(70, 10, 39, 20,
                         OLED_COLOR_NORMAL);
OLED_DrawImage(0, 16, &bilibiliImg, OLED_COLOR_NORMAL);
OLED_ShowFrame();
```

驱动还提供三角形、填充三角形、椭圆和单像素接口。`OLED_COLOR_NORMAL` 在清空的显存上点亮目标像素，`OLED_COLOR_REVERSED` 清除目标像素；它表示绘图操作的反相，不是灰度或第二种物理颜色。

### 8.1 矩形参数要以源码为准

当前两个矩形函数都会把横向终点写成 `x + w`：

```c
OLED_DrawLine(x, y, x + w, y, color);
```

因此：

- `OLED_DrawRectangle()` 覆盖 `(w + 1) x (h + 1)` 个像素；
- `OLED_DrawFilledRectangle()` 循环 `h` 行，覆盖 `(w + 1) x h` 个像素；
- 需要空心 `40x20` 时传 `w=39, h=19`；
- 需要填充 `40x20` 时传 `w=39, h=20`。

绘制前检查 `x+w`、`y+h` 是否越过 `127`、`63`。`OLED_SetPixel()` 会忽略越界像素，但图形函数中的无符号坐标运算仍可能导致边界附近出现异常。

### 8.2 图片数据

图片由以下结构描述：

```c
typedef struct Image {
    uint8_t w;
    uint8_t h;
    const uint8_t *data;
} Image;
```

`font.c` 已提供示例图片 `bilibiliImg`。自定义图片时要提供宽度、高度和取模数据，并保证取模方向、位序与 `OLED_SetBlock()` 的列行式格式一致。图片倾斜、错位或每 8 行交错时，优先检查这些参数。

## 9. 作为调试终端的刷新策略

推荐把显示更新组织成固定数据链：

```text
采集变量 -> 格式化字符串 -> 清帧 -> 绘制全部内容 -> 刷新
```

`OLED_ShowFrame()` 每次发送 8 页整屏数据，并以 `HAL_MAX_DELAY` 阻塞等待。因此：

- 不要在中断服务函数或 I2C 完成回调中刷新整屏；
- 中断只更新变量或置位“数据就绪”标志；
- 主循环按固定周期刷新，初始可采用约 `100 ms`；
- 多个设备共用 `I2C2` 时，由应用层保证事务顺序，避免同一句柄重入。

显示关闭函数如下：

```c
OLED_DisPlay_Off();
OLED_DisPlay_On();
```

关闭显示不等于清空 `OLED_GRAM`。重新开启后若需要确定画面，应重新清帧、绘制并调用 `OLED_ShowFrame()`。

## 10. 分层验收与排错

### 10.1 先验证总线，再验证显示内容

按层验收能避免把字库问题误判为 I2C 问题：

1. `MX_I2C2_Init()` 和 `hi2c2` 已生成并执行；
2. `PB10/PB11` 没有外设冲突，供电、共地和上拉正常；
3. 地址 `0x78` 能获得设备应答；
4. `OLED_Init()` 执行后屏幕能清空并开启；
5. ASCII 字符串显示；
6. 图形配合 `OLED_ShowFrame()` 更新；
7. 最后加入中文、图片和动态变量。

可临时测试地址应答：

```c
if (HAL_I2C_IsDeviceReady(&hi2c2, 0x78, 3U, 100U) != HAL_OK)
{
    Error_Handler();
}
```

该测试只证明地址阶段收到 ACK，不能证明初始化命令、显存布局和绘图逻辑都正确。

### 10.2 常见故障定位

| 现象 | 优先检查 |
| --- | --- |
| OLED 全黑 | 供电、共地、I2C2、PB10/PB11、上拉、地址、初始化前延时 |
| 地址无应答 | 是否误用 `0x7A`，模块地址是否为 `0x3C`，SCL/SDA 是否接反 |
| 初始化或刷新卡住 | `hi2c2` 是否已初始化，总线是否被拉低，阻塞发送是否一直等待 |
| PB10/PB11 无波形 | `MX_I2C2_Init()` 是否执行，引脚是否被其他外设占用 |
| 找不到 `i2c.h` 或 `main.h` | CubeMX 目录和驱动目录是否加入 Include Paths |
| 链接时报 OLED/字体未定义 | `oled.c`、`font.c` 是否加入编译目标 |
| 绘制后不更新 | 是否调用 `OLED_ShowFrame()` |
| 兼容 Show 系列无显示 | 行列是否越界、`OLED_Init()` 是否已执行 |
| 英文正常、中文为空格 | UTF-8 编码、编译器设置、中文字库内容 |
| 矩形尺寸不符 | 空心为 `(w+1)x(h+1)`，填充为 `(w+1)xh` |
| 图片错位或每 8 行交错 | 取模方向、位序、宽高和列行式格式 |
| 主循环明显变慢 | 是否刷新过于频繁，或 I2C2 上存在其他阻塞事务 |

## 本章小结

当前驱动面向 SSD1306，通过 `hi2c2` 和 HAL 地址 `0x78` 通信。应用层先修改 `OLED_GRAM[8][128]`，再由 `OLED_ShowFrame()` 逐页发送整帧；行列式 Show 系列是这条链路的快捷封装，适合简单调试输出。后续调试 ADC、传感器、PID、按键和状态机时，继续沿用“状态变量由外设更新，主循环负责格式化、绘制和周期刷新”的分层方式。先把 I2C2、初始化、显存绘制和刷新分别验收，OLED 才能成为稳定的观察窗口。
