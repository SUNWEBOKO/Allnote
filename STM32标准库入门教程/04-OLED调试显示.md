# 第 4 章 OLED 调试显示

## 本章闭环

把 OLED 当作调试终端，完成一次“接线 -> 加入驱动 -> 编译下载 -> 显示数据”的最小闭环。课程示例使用 0.96 寸四针 I2C OLED，驱动为 GPIO 模拟 I2C。

## 1. 硬件连接

本章使用四针 I2C OLED：

| OLED | STM32F103C8T6 | 说明 |
| --- | --- | --- |
| GND | GND | 必须共地 |
| VCC | 3.3V | 不要直接接 5V，除非模块明确支持 |
| SCL | PB8 | 课程 `OLED.c` 的时钟线 |
| SDA | PB9 | 课程 `OLED.c` 的数据线 |

课程驱动在 `OLED.c` 中通过开漏输出模拟 I2C，不使用 STM32 的硬件 I2C 外设。若你的模块是 7 针 SPI 版本，必须改用资料中的 `7针脚SPI版本` 驱动，不能只改接线。

![OLED 模块](../assets/ppt/slide-038.png)

## 2. 加入工程

从参考资料 `程序源码\STM32Project-无注释版\1-4 OLED驱动函数模块\4针脚I2C版本` 复制三个文件到工程的 `Hardware` 目录：

```text
OLED.c
OLED.h
OLED_Font.h
```

然后在 Keil 中：

1. 把 `OLED.c` 加入 `Hardware` Group。
2. 把 `Hardware` 目录加入 Include Paths。
3. 确认 `OLED_Font.h` 与 `OLED.c` 在同一目录，或把它所在目录加入 Include Paths。
4. 在 `main.c` 中包含 `OLED.h`。

> [!important]
> 只添加 `OLED.h` 不能完成链接；`OLED.c` 必须加入工程。`OLED_Font.h` 没有单独的函数，但缺失会导致字模数组未定义。

## 3. 第一个可运行例程

新建 `User/main.c`，直接使用下面的完整代码。它与参考工程 `4-1 OLED显示屏/User/main.c` 的显示内容一致：

```c
#include "stm32f10x.h"
#include "OLED.h"

int main(void)
{
    OLED_Init();

    OLED_ShowChar(1, 1, 'A');
    OLED_ShowString(1, 3, "HelloWorld!");
    OLED_ShowNum(2, 1, 12345, 5);
    OLED_ShowSignedNum(2, 7, -66, 2);
    OLED_ShowHexNum(3, 1, 0xAA55, 4);
    OLED_ShowBinNum(4, 1, 0xAA55, 16);

    while (1)
    {
    }
}
```

下载后应看到：第 1 行显示 `A HelloWorld!`，第 2 行显示 `12345` 和带符号数，第 3 行显示十六进制，第 4 行显示 16 位二进制。

## 4. 驱动函数与坐标

课程驱动的字符坐标从 1 开始：4 行、每行最多 16 个半角字符。常用接口如下：

| 函数 | 参数含义 | 示例 |
| --- | --- | --- |
| `OLED_ShowChar` | 行、列、单个 ASCII 字符 | `OLED_ShowChar(1, 1, 'A');` |
| `OLED_ShowString` | 行、起始列、ASCII 字符串 | `OLED_ShowString(1, 3, "STM32");` |
| `OLED_ShowNum` | 行、列、无符号数、固定位数 | `OLED_ShowNum(2, 1, 123, 5);` |
| `OLED_ShowSignedNum` | 行、列、带符号数、数字位数 | `OLED_ShowSignedNum(2, 7, -66, 2);` |
| `OLED_ShowHexNum` | 行、列、十六进制数、固定位数 | `OLED_ShowHexNum(3, 1, 0xA55A, 4);` |
| `OLED_ShowBinNum` | 行、列、二进制数、固定位数 | `OLED_ShowBinNum(4, 1, 0x55, 8);` |

`Length` 是显示位数，不是数值的实际位数。位数不足时会在左侧补 `0`；位数过小时只显示低位。例如 `OLED_ShowNum(1, 1, 12345, 3)` 只显示 `345`。

## 5. 把 OLED 接入后续实验

OLED 适合作为状态观察窗口。推荐只更新变化区域：

```c
OLED_ShowString(1, 1, "ADC:");
OLED_ShowNum(1, 6, ADC_Value, 4);
OLED_ShowHexNum(2, 1, StatusReg, 2);
```

不要在中断函数中调用 `OLED_Clear()` 或整屏刷新。当前驱动是软件 I2C，刷新过程较慢且会阻塞；中断中只更新计数器或标志位，主循环再把变量显示出来。

## 6. 验收与排错

| 现象 | 优先检查 |
| --- | --- |
| 全黑 | VCC/GND、PB8/PB9、I2C 版本、模块是否需要上拉 |
| 编译找不到 `OLED.h` | Include Paths 是否包含 `Hardware` |
| 链接找不到 `OLED_Init` | `OLED.c` 是否已加入 Keil 工程 |
| 显示乱码 | `OLED_Font.h` 是否存在，驱动与控制器是否匹配 |
| 画面闪烁或程序卡顿 | 是否在高频循环中反复 `OLED_Clear()`，是否在 ISR 中刷新 |

## 本章小结

先用 `4-1 OLED显示屏` 的完整例程确认 PB8/PB9 和驱动文件没有问题，再把 OLED 作为第 5~7 章的观察窗口。这样后续实验出现异常时，可以先排除显示模块本身的问题。
