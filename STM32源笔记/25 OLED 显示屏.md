# 25. OLED 显示屏：SSD1306 驱动与显存模型

> 本节重点：理解 SSD1306 OLED 驱动库"先写显存、再整帧刷新"的核心模型，掌握显存组织方式（8 页 × 128 列）与 I2C 通信协议。

---

## 本节核心问题

这节重点不是只会调用 `OLED_Printf()`，而是理解 SSD1306 OLED 驱动库怎样通过 I2C 把"显存里的像素"刷新到屏幕。

复习时抓住 5 件事：

1. OLED 驱动为什么采用"先写显存，再整帧刷新"。
2. `OLED_GRAM[8][128]` 怎样对应 128x64 像素屏幕。
3. `OLED_Init()`、`OLED_NewFrame()`、`OLED_ShowFrame()` 的调用顺序。
4. 图形、文字、图片最终都怎样落到 `OLED_SetPixel()` / `OLED_SetBlock()`。
5. 移植时要改哪些底层资源：`OLED_Init()` 传入的 I2C 句柄、OLED 地址、字体/图片数据。

---

## 二、知识主线

当前驱动面向 SSD1306 OLED，通信方式是 I2C。

OLED 与 LCD 的核心区别：

| 特性 | OLED | LCD |
|------|------|-----|
| 发光方式 | **自发光**，每像素独立发光 | 需要背光，液晶调制背光透射 |
| 对比度 | 极高（纯黑 = 不发光） | 受背光限制 |
| 视角 | 广视角（~170°） | 窄视角（TN 屏） |
| 响应速度 | 微秒级 | 毫秒级 |
| 功耗 | 黑屏极省电（像素不亮） | 背光一直亮 |
| 驱动方式 | 电流驱动 | 电压驱动 |

SSD1306 是 128×64 单色 OLED 驱动芯片，每个像素只能亮或不亮（无灰度）。驱动通过 I2C 或 SPI 与主控通信，I2C 为 4 线模式（含命令/数据区分）。

驱动的核心链路：

```text
应用层绘制函数 -> OLED_GRAM 显存 -> I2C 整帧刷新 -> OLED 屏幕
```

这套驱动不是每画一个点就立刻发 I2C，而是：

1. 先调用 `OLED_NewFrame()` 清空显存。
2. 调用 `OLED_DrawXXX()` / `OLED_PrintXXX()` 在显存中画内容。
3. 最后调用 `OLED_ShowFrame()`，一次性把整帧显存刷到屏幕。

这种方式的优点：

- 页面逻辑不用直接操作 I2C。
- 可以先把一整帧画完整，再统一显示。
- 避免频繁刷新造成闪烁和总线开销。

---

## 三、驱动库结构

参考目录：项目目录下的 `驱动库/OLED`

实际文件：

- `oled.h`：对外显示接口。
- `oled.c`：SSD1306 初始化、显存、绘图、文字输出。
- `font.h`：字体和图片结构体声明。
- `font.c`：ASCII 字库、中文 16x16 字库、图片数据。

常用公开接口：

| 类别 | 函数 |
|---|---|---|
| 初始化/显示 | `OLED_Init(void *hi2c)`、`OLED_DisPlay_On()`、`OLED_DisPlay_Off()` |
| 帧缓冲 | `OLED_NewFrame()`、`OLED_ShowFrame()` |
| 像素/区域 | `OLED_SetPixel()`、`OLED_InvertArea()` |
| 图形 | `OLED_DrawLine()`、`OLED_DrawRectangle()`、`OLED_DrawCircle()`、`OLED_DrawEllipse()` 等 |
| 图片 | `OLED_DrawImage()` |
| 文字 | `OLED_PrintASCIIChar()`、`OLED_PrintASCIIString()`、`OLED_PrintString()`、`OLED_PrintfFont()`、`OLED_Printf()` |

注意：

- `oled.c` 中实现了 `OLED_SetColorMode()`，但当前 `oled.h` 没有声明它；如果要在外部调用，需要补函数声明。
- `OLED_DisPlay_On/Off` 的函数名里 `DisPlay` 大小写比较特殊，调用时要按头文件写。
- `oled.h` 不再包含 `main.h`，只显式包含 `<stdint.h>` 和 `font.h`，头文件耦合更低。

---

## 四、底层 I2C 通信

### 1. I2C 句柄的传递方式

驱动不再硬编码 I2C 句柄，而是通过 `OLED_Init()` 由外部传入：

```c
// 驱动内部保存句柄
static I2C_HandleTypeDef *oled_hi2c = NULL;

static void OLED_Send(const uint8_t *data, uint8_t len)
{
  HAL_I2C_Master_Transmit(oled_hi2c, OLED_ADDRESS, (uint8_t *)data, len, HAL_MAX_DELAY);
}

// 初始化时传入句柄
void OLED_Init(void *hi2c)
{
  oled_hi2c = (I2C_HandleTypeDef *)hi2c;
  // ... 后续初始化命令
}
```

复习重点：

- `OLED_Init()` 接受 `void *` 参数，头文件不依赖 HAL 类型定义。
- `i2c.h` 只在 `oled.c` 中包含，不暴露到 `oled.h`。
- `OLED_ADDRESS = 0x78` 是 HAL 发送时使用的 8 位地址形式。
- 若硬件接在 `I2C1`，调用 `OLED_Init(&hi2c1)` 即可，无需改驱动源码。

### 2. 命令和数据的区别

SSD1306 I2C 通信中，第一个控制字节决定后面是命令还是显示数据。

当前驱动：

| 类型 | 控制字节 | 函数 |
|---|---:|---|
| 命令 | `0x00` | `OLED_SendCmd()` |
| 数据 | `0x40` | `OLED_ShowFrame()` |

`OLED_SendCmd(cmd)` 实际发送 2 字节：

```text
0x00 + cmd
```

`OLED_ShowFrame()` 每页发送：

```text
0x40 + 128 字节显存数据
```

---

## 五、显存模型：128x64 与 8 页

驱动中定义：

```c
#define OLED_PAGE   8
#define OLED_ROW    8 * OLED_PAGE
#define OLED_COLUMN 128

uint8_t OLED_GRAM[OLED_PAGE][OLED_COLUMN];
```

含义：

- 屏幕宽度：128 列。
- 屏幕高度：64 行。
- 每页高度：8 像素。
- 一共 8 页，所以 `8 * 8 = 64` 行。

显存定位公式：

```text
page = y / 8
bit  = y % 8
column = x
```

所以一个像素 `(x, y)` 对应：

```c
OLED_GRAM[y / 8][x] 的第 (y % 8) 位
```

`OLED_SetPixel()` 的核心逻辑：

```c
if (x >= 128 || y >= 64) return;

if (color == OLED_COLOR_NORMAL)
  OLED_GRAM[y / 8][x] |= 1 << (y % 8);
else
  OLED_GRAM[y / 8][x] &= ~(1 << (y % 8));
```

复习重点：

- 坐标范围是 `x: 0~127`，`y: 0~63`。
- 显存按"页 + 列"组织，不是简单二维像素数组。
- `OLED_COLOR_NORMAL = 0` 时置 1，`OLED_COLOR_REVERSED = 1` 时清 0。

### 为什么使用页寻址模式

SSD1306 的 GDDRAM 采用**页寻址（Page Addressing）**，而非连续的行列寻址。这是由 OLED 驱动芯片的内部扫描结构决定的：

- 屏体物理扫描分 8 个 COM 组（公共电极组），每组 8 行
- 每组 COM 对应一页，一次写 1 字节 = 同时控制该页内 8 行的 1 列
- `OLED_GRAM[page][column]` 的每个 bit 对应一页内 8 行中的一行

```text
列： 0   1   2  ...  127
页0: B0  B1  B2  ...  B127    ← 每字节控制 8 个垂直像素
页1: B0  B1  B2  ...  B127
...
页7: B0  B1  B2  ...  B127

每个字节的 bit0 = 最上面一行(y=0)，bit7 = 最下面一行(y=7)
```

这就是 `OLED_SetPixel()` 需要用 `y / 8` 和 `y % 8` 定位的原因——先找页，再找页内的位偏移。这种寻址方式让 SSD1306 可以在保持较少引脚的前提下驱动 128×64 像素。

---

## 六、初始化与整帧刷新

### 1. 初始化：`OLED_Init()`

`OLED_Init()` 做了三类事情：

1. 发送 SSD1306 初始化命令。
2. 清空显存并刷新一次空屏。
3. 开启显示。

关键流程：

```text
0xAE 关闭显示
发送寻址、扫描方向、对比度、电荷泵等配置命令
OLED_NewFrame()
OLED_ShowFrame()
0xAF 开启显示
```

其中：

- `0xAE`：关闭显示。
- `0xAF`：开启显示。
- `0x8D + 0x14`：开启电荷泵。
- `0xA6`：正常显示。

### 2. 清空显存：`OLED_NewFrame()`

```c
memset(OLED_GRAM, 0, sizeof(OLED_GRAM));
```

它只清空 MCU 内存中的显存，不会自动更新屏幕。

### 3. 刷新屏幕：`OLED_ShowFrame()`

`OLED_ShowFrame()` 会逐页刷新：

1. 设置页地址：`0xB0 + page`。
2. 设置列起点：`0x00`、`0x10`。
3. 发送 `0x40 + 128 字节数据`。
4. 重复 8 页。

对应流程：

```text
page 0: 设置页/列 -> 发送 128 字节
page 1: 设置页/列 -> 发送 128 字节
...
page 7: 设置页/列 -> 发送 128 字节
```

复习重点：

> 画图只改显存；真正显示必须调用 `OLED_ShowFrame()`。

---

## 七、绘图函数怎么工作

### 1. 像素与区域

最底层的公开像素接口是：

```c
OLED_SetPixel(x, y, color);
```

区域反色：

```c
OLED_InvertArea(x, y, w, h);
```

`OLED_InvertArea()` 会把指定区域中的显存位逐个异或，适合做选中框、菜单高亮。

### 2. 图形绘制

常用图形接口：

| 函数 | 作用 |
|---|---|
| `OLED_DrawLine()` | 画线，斜线使用 Bresenham 算法 |
| `OLED_DrawRectangle()` | 画矩形边框 |
| `OLED_DrawFilledRectangle()` | 画填充矩形 |
| `OLED_DrawTriangle()` | 画三角形边框 |
| `OLED_DrawFilledTriangle()` | 画填充三角形 |
| `OLED_DrawCircle()` | 画圆 |
| `OLED_DrawFilledCircle()` | 画填充圆 |
| `OLED_DrawEllipse()` | 画椭圆 |

这些函数最终都会落到 `OLED_SetPixel()` 或按行/块写显存。

### 3. 图片绘制

图片结构体：

```c
typedef struct Image {
  uint8_t w;
  uint8_t h;
  const uint8_t *data;
} Image;
```

绘制图片：

```c
OLED_DrawImage(x, y, &clockImg, OLED_COLOR_NORMAL);
```

实际内部调用：

```c
OLED_SetBlock(x, y, img->data, img->w, img->h, color);
```

`font.c` 中已经内置了多张图片，例如：

- `clockImg`
- `lightImg`
- `mpuImg`
- `gameImg`
- `returnImg`
- `bilibiliImg`
- `Emoji_Gragh[]`
- `Menu_Gragh[]`

---

## 八、文字与字库

### 1. ASCII 字体

`font.c` 中提供多种 ASCII 字体：

| 字体 | 尺寸 |
|---|---|
| `afont8x6` | 8x6 |
| `afont12x6` | 12x6 |
| `afont16x8` | 16x8 |
| `afont24x12` | 24x12 |

打印 ASCII 字符串：

```c
OLED_PrintASCIIString(0, 0, "HELLO", &afont16x8, OLED_COLOR_NORMAL);
```

### 2. 中文/混合字符串

中文字体结构体：

```c
typedef struct Font {
  uint8_t h;
  uint8_t w;
  const uint8_t *chars;
  uint8_t len;
  const ASCIIFont *ascii;
} Font;
```

当前默认中文字体：

```c
extern const Font font16x16;
```

字库规则：

- 每个中文字模前 4 字节存 UTF-8 编码。
- 后面接字模数据。
- `font16x16` 中每个字模占 `4 + 16 * 16 / 8 = 36` 字节。
- 找不到中文时，如果是 ASCII，就回退到 `font->ascii`。
- 找不到非 ASCII 字模时，用空格占位。

打印混合字符串：

```c
OLED_PrintString(0, 0, "时间12:30", &font16x16, OLED_COLOR_NORMAL);
```

### 3. printf 风格输出

指定字体：

```c
OLED_PrintfFont(0, 0, &font16x16, OLED_COLOR_NORMAL, "temp:%d", temp);
```

默认字体：

```c
OLED_Printf(0, 0, OLED_COLOR_NORMAL, "temp:%d", temp);
```

`OLED_Printf()` 默认使用 `font16x16`，内部会用 `vsnprintf()` 计算长度，再 `malloc()` 临时缓冲区。

复习重点：

- `OLED_Printf()` 方便，但会动态分配内存。
- 小 MCU 项目里频繁调用时，要注意堆空间和碎片风险。

---

## 九、典型使用流程

最常用流程：

```c
OLED_Init(&hi2c2);   // 传入已初始化的 I2C 句柄

while (1)
{
  OLED_NewFrame();

  OLED_Printf(0, 0, OLED_COLOR_NORMAL, "count:%d", count);
  OLED_DrawRectangle(0, 20, 60, 20, OLED_COLOR_NORMAL);
  OLED_DrawImage(80, 16, &clockImg, OLED_COLOR_NORMAL);

  OLED_ShowFrame();
}
```

调用顺序要记牢：

```text
初始化 I2C -> OLED_Init(&hi2c)
每一帧：OLED_NewFrame() -> 绘制/打印 -> OLED_ShowFrame()
```

如果只调用绘图函数但不 `OLED_ShowFrame()`，屏幕不会更新。

---

## 十、移植时要改什么

### 1. I2C 资源

驱动初始化时传入 I2C 句柄：

```c
OLED_Init(&hi2c1);   // 换成工程实际使用的 I2C 句柄
```

如果换工程，重点检查：

- `OLED_Init()` 传入的句柄是否与 I2C 初始化一致。
- OLED 地址是否仍是 `0x78`（可在 `oled.c` 中修改 `OLED_ADDRESS`）。
- `oled.c` 中 `#include "i2c.h"` 是否指向工程正确的 HAL I2C 头文件。

### 2. 屏幕参数

当前参数适配 128x64：

```c
#define OLED_PAGE   8
#define OLED_ROW    8 * OLED_PAGE
#define OLED_COLUMN 128
```

如果换成 128x32 或其他尺寸，显存大小、刷新页数、初始化命令都要一起检查。

### 3. 字体和图片

`font.h` 注释说明：字库和图片数据可用"波特律动 LED 取模助手"生成。

移植或新增图标时要保证：

- `Image.w`、`Image.h` 与数据尺寸一致。
- 字模数据排列方式与 `OLED_SetBlock()` 期待的列行式一致。
- 中文字库需要保存 UTF-8 编码头，否则 `OLED_PrintString()` 找不到字。

---

## 十一、高频易错点

1. **忘记调用 `OLED_ShowFrame()`**。`OLED_NewFrame()` 和绘图函数只改显存，不会自动刷新屏幕。

2. **每次循环不清帧**。不调用 `OLED_NewFrame()`，旧内容会留在显存里，造成残影式叠加。

3. **I2C 句柄不匹配**。句柄通过 `OLED_Init()` 传入，传入的 I2C 必须已经初始化且与 OLED 硬件连接一致，否则屏幕不会响应。

4. **OLED 地址写错**。当前 HAL 发送使用 `0x78`。有些资料写 `0x3C` 是 7 位地址表达，不能直接混用。

5. **坐标越界**。屏幕范围是 `x: 0~127`、`y: 0~63`。单点函数会保护，复杂图形仍要自己注意尺寸。

6. **误解颜色模式**。`OLED_COLOR_NORMAL` 是置位显示，`OLED_COLOR_REVERSED` 会按反色方式写显存。

7. **中文显示不出来**。`OLED_PrintString()` 只能显示字库中已有的中文；没有字模就会用空格代替。

8. **频繁使用 `OLED_Printf()` 导致内存风险**。该函数内部会 `malloc()` 临时缓冲区，资源紧张时要谨慎。

9. **外部调用 `OLED_SetColorMode()` 编译报错**。函数在 `oled.c` 中实现，但当前 `oled.h` 没有声明；要用就补声明。

10. **换屏幕尺寸只改宏不够**。SSD1306 初始化命令、页数、显存、刷新逻辑都要一起核对。

---

## 十二、速记区

- **驱动模型**：先画到 `OLED_GRAM`，再 `OLED_ShowFrame()` 整帧刷新。
- **屏幕尺寸**：128x64，分 8 页，每页 8 像素高。
- **显存定位**：`OLED_GRAM[y / 8][x]` 的第 `y % 8` 位。
- **I2C 地址**：当前驱动用 `0x78`。
- **I2C 句柄**：通过 `OLED_Init(void *hi2c)` 外部传入，不再硬编码。
- **命令控制字节**：`0x00`。
- **数据控制字节**：`0x40`。
- **常用流程**：`OLED_NewFrame()` -> 绘制/打印 -> `OLED_ShowFrame()`。
- **默认 printf 字体**：`font16x16`。
- **中文字库规则**：前 4 字节 UTF-8 编码，后面是字模数据。

---

## 十三、自测清单

1. 为什么这个 OLED 驱动要先写显存，再整帧刷新？
2. `OLED_GRAM[8][128]` 怎样对应 128x64 的屏幕？
3. 坐标 `(x, y)` 对应显存中的哪一页、哪一列、哪一位？
4. `OLED_SendCmd()` 和 `OLED_ShowFrame()` 发送的控制字节分别是什么？
5. 为什么调用了 `OLED_Printf()` 但屏幕可能没有变化？
6. `OLED_PrintString()` 显示中文时，为什么字库里要保存 UTF-8 编码头？
7. `OLED_Printf()` 相比 `OLED_PrintString()` 多了什么便利，也多了什么风险？
8. 把驱动移植到另一个工程时，最先应该检查哪几个地方？
9. `OLED_Init()` 为什么用 `void *hi2c` 而不用 `I2C_HandleTypeDef *hi2c`？
