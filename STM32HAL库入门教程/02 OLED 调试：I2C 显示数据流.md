# 02 OLED 调试：I2C 显示数据流

## 本章问题

程序运行到哪一步、变量变成多少，光看 LED 只能猜。本章给板子接一块 0.96 寸 OLED，把状态直接显示出来；同时第一次接触 I2C 总线，说清硬件 I2C 和软件 I2C 两条路怎么选、怎么配。

## 学习目标

- 配好硬件 I2C（`PB10/PB11`）或软件 I2C（`PB8/PB9`）的接线与参数。
- 说清一条显示数据从函数调用到屏幕像素经过哪几层。
- 用数字、字符串和中文字符接口显示变量。
- 用局部刷新写出数值变化时不错位的界面。
- 用绘图接口画线和图形。

## 1. 两条 I2C 路线

驱动有两版，对外函数名、参数和返回值完全相同，差别只在底层通信：

| | 硬件 I2C 版 | 软件 I2C 版 |
| --- | --- | --- |
| 引脚 | `PB10`(SCL)、`PB11`(SDA)，由 `I2C2` 外设控制 | 任意两个 GPIO，本章用 `PB8`(SCL)、`PB9`(SDA) |
| 通信方式 | CPU 把字节交给 I2C 外设 | 程序逐位翻转引脚电平 |
| 占用 CPU | 少 | 多，每一位都要等 |
| 适用场合 | 正式使用，`I2C2` 引脚空闲 | `I2C2` 引脚被串口等外设占用 |

两版源码文件名相同、函数同名，不能同时登记进工程，否则链接时会报重复定义。`CMakeLists.txt` 里登记哪一套，就只编译哪一套。

### 1.1 接线

| OLED | 硬件 I2C 版 | 软件 I2C 版 | 作用 |
| --- | --- | --- | --- |
| `GND` | `GND` | `GND` | 共地 |
| `VCC` | `3.3 V` | `3.3 V` | 供电 |
| `SCL` | `PB10` | `PB8` | 时钟 |
| `SDA` | `PB11` | `PB9` | 数据 |

上电前确认三件事：STM32 与 OLED 共地；模块供电规格允许 3.3 V；SDA、SCL 有上拉电阻。多数四针模块自带上拉，阻值约 4.7 kΩ。

### 1.2 CubeMX 配置

两版都要先保留 `SYS → Debug = Serial Wire`。

硬件版在 `Connectivity → I2C2` 把 `Mode` 选为 `I2C`，`PB10`、`PB11` 会自动变成 `I2C2_SCL`、`I2C2_SDA`。参数按下表：

| 字段 | 取值 |
| --- | --- |
| I2C Speed Mode | Standard Mode |
| I2C Clock Speed | `100000` |
| I2C Addressing Mode | 7-bit |
| 其余项 | 保持默认 |

软件版把 `PB8`、`PB9` 选为 `GPIO_Output`，每个引脚确认四项：

- 初始电平 `High`，总线空闲时必须是高电平；
- 模式 `Output Open Drain`，开漏才能让从机在应答位拉低 SDA；
- 上下拉 `No pull-up and no pull-down`，上拉交给模块上的电阻；
- 速度 `High`。

两版分别来自 `E:\ProjectStm\驱动库\OLED（硬件iic）` 和 `OLED（软件IIC）`，用哪版就把那四个文件复制到工程 `User/Drivers/OLED/`。可调项都在 `OLED.c` 开头：

```c
/* 硬件版：换 I2C 外设就改这里 */
#define OLED_I2C_HANDLE    hi2c2
#define OLED_I2C_ADDR      0x78U   /* 7 位地址 0x3C 左移一位，补写方向位 */
#define OLED_I2C_TIMEOUT   100U

/* 软件版：换引脚改这四行，SCL 速度改 OLED_DELAY_LOOPS */
#define OLED_SCL_PORT       GPIOB
#define OLED_SCL_PIN        GPIO_PIN_8
#define OLED_SDA_PORT       GPIOB
#define OLED_SDA_PIN        GPIO_PIN_9
#define OLED_DELAY_LOOPS    40U    /* 空循环次数，越大 SCL 越慢 */
```

软件 I2C 的速度由 `OLED_DELAY_LOOPS` 决定。72 MHz 下 40 次空循环约 1~2 µs，SCL 约 300 kHz，在 SSD1306 的 400 kHz 上限之内。屏幕花屏或初始化偶尔失败，先把这里调大。

### 1.3 什么时候必须用软件 I2C

`PB10/PB11` 除了 `I2C2`，还复用为 `USART3_TX/RX`、`TIM2_CH3/CH4` 等功能。本章一块屏独占 `I2C2` 没有问题；第 08 章的实验用 `USART2` 的 `PA2/PA3`，若改用 `USART3` 接蓝牙，`PB10/PB11` 就得让给串口，只能改走软件 I2C。软件 I2C 的引脚可以任选，代价是占用 CPU 时间。

后续章节的 OLED 接线按资源占用切换：06、07 章不占用 `PB10/PB11`，用硬件 I2C2 版；09 章把这两根线让给 MPU6050，OLED 回到软件 I2C 的 `PB8/PB9`；10 章的 SPI 用 `PA4~PA7`，也不与 `PB8/PB9` 冲突。切换版本只换驱动文件和 CMake 登记，显示代码不变。

## 2. 数据怎么走到屏幕

### 2.1 五层链路

1. 应用函数：`OLED_ShowString()`、`OLED_ShowNum()` 等按坐标算出要改哪些位。
2. 显存：结果写进 MCU 内存里的 `OLED_DisplayBuf[8][128]`。到这一步屏幕还没有变化。
3. `OLED_Update()`：逐页读出显存，打包成 I2C 事务。
4. I2C 传输：硬件版调用 `HAL_I2C_Master_Transmit()`，软件版逐位翻转引脚。
5. SSD1306 的 GDDRAM：屏幕芯片收到数据后写入自己的显存，并持续扫描点亮像素。

关键只有一句：显示函数只改 MCU 内存，`OLED_Update()` 才把内容发到屏幕。

### 2.2 驱动文件

| 文件 | 内容 |
| --- | --- |
| `OLED.c` | 显存、初始化命令、绘图、文字和字节发送 |
| `OLED.h` | 对外函数声明、字体宏、填充标志 |
| `OLED_Data.c` | 字模和示例图像 |
| `OLED_Data.h` | 字模类型、字符集开关 |

常用的对外接口：

```c
void OLED_Init(void);
void OLED_Update(void);
void OLED_UpdateArea(int16_t X, int16_t Y, uint8_t Width, uint8_t Height);

void OLED_Clear(void);
void OLED_Reverse(void);
void OLED_ReverseArea(int16_t X, int16_t Y, uint8_t Width, uint8_t Height);
void OLED_ShowChar(int16_t X, int16_t Y, char Char, uint8_t FontSize);
void OLED_ShowString(int16_t X, int16_t Y, char *String, uint8_t FontSize);
void OLED_ShowNum(int16_t X, int16_t Y, uint32_t Number, uint8_t Length, uint8_t FontSize);
void OLED_ShowSignedNum(int16_t X, int16_t Y, int32_t Number, uint8_t Length, uint8_t FontSize);
void OLED_ShowHexNum(int16_t X, int16_t Y, uint32_t Number, uint8_t Length, uint8_t FontSize);
void OLED_ShowBinNum(int16_t X, int16_t Y, uint32_t Number, uint8_t Length, uint8_t FontSize);
void OLED_ShowFloatNum(int16_t X, int16_t Y, double Number, uint8_t IntLength, uint8_t FraLength, uint8_t FontSize);
void OLED_Printf(int16_t X, int16_t Y, uint8_t FontSize, char *format, ...);

void OLED_DrawPoint(int16_t X, int16_t Y);
void OLED_DrawLine(int16_t X0, int16_t Y0, int16_t X1, int16_t Y1);
void OLED_DrawRectangle(int16_t X, int16_t Y, uint8_t Width, uint8_t Height, uint8_t IsFilled);
void OLED_DrawCircle(int16_t X, int16_t Y, uint8_t Radius, uint8_t IsFilled);
void OLED_ShowImage(int16_t X, int16_t Y, uint8_t Width, uint8_t Height, const uint8_t *Image);
```

### 2.3 坐标与字体

屏幕分辨率 `128×64`，原点在左上角，`X` 向右 0~127，`Y` 向下 0~63。SSD1306 的显存按页组织：64 行分成 8 页，每页 8 行、128 列，每列一个字节对应 8 个像素。

![SSD1306 显存结构与页列寻址](image/ssd1306-gddram.png)

字体用两个宏选择：

| 宏 | 宽 × 高 | 一行放几个字符 | 屏幕能放几行 |
| --- | ---: | ---: | ---: |
| `OLED_8X16` | 8 × 16 | 16 | 4 |
| `OLED_6X8` | 6 × 8 | 21 | 8 |

`Y` 按字体高度心算：用 `OLED_8X16` 时，四行起点分别是 0、16、32、48；想让行之间留空隙，就取 0、24、48。`X` 是字符起点，后续字符按字体宽度自动右移。

## 3. 最小实验：在屏幕上显示内容

要写的只有 `USER CODE` 区域：头文件放 `Includes`，初始化和首帧绘制放 `USER CODE 2`。

```c
/* USER CODE BEGIN Includes */
#include "OLED.h"
/* USER CODE END Includes */

/* USER CODE BEGIN 2 */
HAL_Delay(20U);
if (HAL_I2C_IsDeviceReady(&hi2c2, 0x78U, 3U, 100U) != HAL_OK)
{
    Error_Handler();     /* 0x78 上没有设备应答，先查接线和供电 */
}
OLED_Init();

OLED_ShowString(0, 0, "STM32 HAL", OLED_8X16);
OLED_ShowString(0, 24, "你好世界", OLED_8X16);
OLED_DrawRectangle(0, 48, 128, 16, OLED_UNFILLED);
OLED_Update();
/* USER CODE END 2 */
```

软件版没有外设可探测，去掉 `HAL_I2C_IsDeviceReady()` 那几行即可：

```c
OLED_Init();
OLED_ShowChar(0, 0, 'A', OLED_8X16);
OLED_Update();
```

下载后应当同时看到英文、中文和底部矩形框。每改一次显存，都要再调用一次 `OLED_Update()` 才会显示。

## 4. 显示变量

### 4.1 固定宽度数字

调试界面里数字不断变化，如果宽度跟着位数走，后面的标签会被推着跳。`OLED_ShowNum()` 一族用 `Length` 参数固定字符数，不足补 0，超出只保留低位：

```c
OLED_ShowString(0,  0, "CNT:", OLED_8X16);
OLED_ShowNum(32, 0, 2048U, 4U, OLED_8X16);       /* CNT:2048 */
OLED_ShowSignedNum(0, 16, -125, 5U, OLED_8X16);   /* -00125 */
OLED_ShowHexNum(0, 32, 0xA5U, 2U, OLED_8X16);     /* A5 */
OLED_ShowBinNum(0, 48, 0x5AU, 6U, OLED_8X16);     /* 011010 */
OLED_Update();
```

`OLED_ShowSignedNum()` 固定占“符号 + `Length` 位数字”，算 `X` 时要给符号留位置。`OLED_ShowFloatNum()` 输出 `±整数.小数`，会四舍五入；F103 没有硬件浮点单元，浮点运算慢且占空间，非必要不用。

### 4.2 动态界面的标准写法

标签位置固定，数据用固定宽度写在固定行，每轮只刷新数据区：

```c
/* USER CODE BEGIN PV */
uint16_t adc_value = 2048U;
int16_t  speed = -125;
uint8_t  cnt = 0U;
/* USER CODE END PV */

/* USER CODE BEGIN WHILE */
OLED_ShowString(0,  0, "ADC:", OLED_8X16);
OLED_ShowString(0, 16, "SPD:", OLED_8X16);
OLED_ShowString(0, 32, "CNT:", OLED_8X16);
OLED_Update();

while (1)
{
    /* adc_value 换成真实数据源，例如第 06 章的 ADC 读取 */
    speed++;
    cnt++;

    OLED_ShowNum(32,  0, adc_value, 4U, OLED_8X16);
    OLED_ShowSignedNum(32, 16, speed, 5U, OLED_8X16);
    OLED_ShowNum(32, 32, cnt, 3U, OLED_8X16);

    OLED_UpdateArea(0, 0, 128, 48);   /* 只刷前三行 */
    HAL_Delay(100U);
}
/* USER CODE END WHILE */
```

标签必须在进入循环前先 `OLED_Update()` 一次，否则第一帧只有数据没有标签。`OLED_UpdateArea()` 只发送矩形覆盖到的页，横向可以只发指定列，纵向必须按 8 像素的页发送。因此 `Y` 取 8 的倍数、`Height` 取 8 的倍数时最省传输；不满足时，边界页里同一列的其他像素也会一起重发，内容仍来自显存，不会花屏。

### 4.3 格式化字符串

变长内容和混合格式可以先格式化到缓冲区，再交给 `OLED_ShowString()`：

```c
#include <stdio.h>

char text[20];
snprintf(text, sizeof(text), "ADC:%u", (unsigned int)adc_value);
OLED_ShowString(0, 0, text, OLED_8X16);

snprintf(text, sizeof(text), "SPD:%d", (int)speed);
OLED_ShowString(0, 16, text, OLED_8X16);
```

`%u` 是无符号十进制，`%d` 是有符号十进制，`%X` 常用于寄存器值。`snprintf()` 会补结尾的 `\0`，空间不足时截断，缓冲区要按最大位数留余量。

驱动还提供一步到位的版本：

```c
OLED_Printf(0, 0, OLED_8X16, "ADC:%u", (unsigned int)adc_value);
```

它内部先 `vsnprintf` 再调用 `OLED_ShowString()`，缓冲区大小由 `OLED_PRINTF_BUFFER_SIZE` 决定，长字符串同样会截断。

### 4.4 中文显示

`OLED_ShowString()` 支持 ASCII 与中文混排。字符集在 `OLED_Data.h` 里二选一：

```c
#define OLED_CHARSET_UTF8       /* 默认，源文件存 UTF-8 */
//#define OLED_CHARSET_GB2312   /* 可选，源文件存 GB2312 */
```

两个宏只能开一个，源文件编码必须与所选字符集一致，否则汉字查不到，只显示方框问号。每个汉字占 16×16 像素，`OLED_8X16` 一行能放 8 个汉字。用 `OLED_6X8` 显示汉字会退化成 `?`。

汉字字模放在 `OLED_Data.c` 的 `OLED_CF16x16[]` 里，格式是“字符串 + 32 字节点阵”。数组最后一项必须是空字符串 `""`，查找失败时靠它判断结束；删掉会导致越界。本工程预置了 `你`、`好`、`世`、`界` 等几个字。

## 5. 图形、图片与反色

图形和文字走同一条路：先改显存，再统一刷新。

```c
OLED_Clear();
OLED_DrawLine(0, 0, 127, 63);
OLED_DrawCircle(32, 32, 15, OLED_UNFILLED);
OLED_DrawRectangle(70, 10, 40, 20, OLED_FILLED);
OLED_ShowImage(0, 16, 16, 16, Diode);
OLED_Update();
```

绘图函数都接受负坐标，超出屏幕的部分自动丢弃，可以用“画在屏幕外再平移进来”的方式做滚动，不必自己算边界。

`OLED_Reverse()` 把整屏取反，`OLED_ReverseArea()` 只取反一块区域。调试界面里常用来标出当前选中行。取反是按位异或，执行两次回到原样。

`OLED_ShowImage()` 显示的是一张已经按显存格式排好的位图：纵向 8 点一组，低位在上，从左到右、从上到下排列。它会先清空目标区域再写入。示例图像 `Diode` 是 16×16 的二极管符号。

倒立摆的 OLED 固定走 `PB8/PB9` 软件 I2C，直接复用本章驱动；其引脚总表见 [[STM32倒立摆/03 基础驱动：CubeMX与HAL库实现#1.4 本工程的引脚与外设总表]]。

上一篇：[[01 GPIO：引脚、八种模式与 HAL 读写]] ｜ 下一篇：[[03 时钟系统：时钟树、PLL 与 HAL 配置]]
