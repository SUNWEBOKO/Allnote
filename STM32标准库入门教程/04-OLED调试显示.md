# 第 4 章 OLED 调试显示


## 本章闭环

把 OLED 当作调试终端，显示字符串、十进制数、十六进制数和二进制数。此章重点是调用现成模块，不要求立即重写 OLED 底层驱动。

![OLED 模块](../assets/ppt/slide-038.png)

## 1. 硬件连接

课程主要使用四针 I2C OLED：`GND`、`VCC`、`SCL`、`SDA`。课程驱动用 GPIO 模拟 I2C，具体引脚以驱动文件和接线图为准；不要仅凭模块丝印猜测。

![四针与七针 OLED 接口](../assets/ppt/slide-039.png)

## 2. 加入工程

1. 将对应版本的 `OLED.c`、`OLED.h`、`OLED_Font.h` 复制到 `Hardware`。
2. 把 `OLED.c` 加入 Keil 的 `Hardware` Group。
3. 把 `Hardware` 加入 Include Paths。
4. 在 `main.c` 中包含 `OLED.h`。

```c
#include "stm32f10x.h"
#include "OLED.h"

int main(void)
{
    OLED_Init();
    OLED_ShowString(1, 1, "STM32");
    OLED_ShowNum(2, 1, 12345, 5);
    OLED_ShowHexNum(3, 1, 0xA55A, 4);

    while (1) {}
}
```

![OLED 常用驱动函数](../assets/ppt/slide-040.png)

## 3. 坐标和数字长度

课程字符库通常按 4 行、每行 16 个半角字符组织，行列从 1 开始。`OLED_ShowNum(Line, Column, Number, Length)` 的 `Length` 是固定显示位数，不是数值本身长度；位数不足通常补 0，位数过小会截断高位。

显示有符号量用 `OLED_ShowSignedNum()`；查看寄存器、地址和通信数据用十六进制；检查单个位时用二进制显示最直观。

## 4. OLED 的调试价值

调试不是“最终能显示就行”，而是让看不见的状态可观察。例如：

```c
OLED_ShowNum(1, 1, ADC_Value, 4);
OLED_ShowSignedNum(2, 1, Speed, 5);
OLED_ShowHexNum(3, 1, StatusReg, 2);
```

主循环频繁全屏清除会闪烁，应只更新变化区域。中断函数中不要执行完整 OLED 刷新：软件 I2C 慢且阻塞，应在中断中只更新变量，主循环再显示。

## 5. 常见故障

- 全黑：先查供电、共地、接口版本和 SCL/SDA 引脚。
- 显示乱码：驱动与屏幕控制器/地址不匹配，或 `OLED_Font.h` 未加入。
- 编译链接错误：只包含头文件但没有把 `OLED.c` 加入工程。
- 运行后卡顿：在高频循环或中断中大量刷新。

## 本章小结

OLED 是后续章节的观察窗口。先保证驱动模块独立通过，再把它接入其他实验；出现问题时才能判断故障来自显示模块还是被测外设。
