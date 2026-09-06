# 第 7 章 ADC 模数转换

## 学习目标与前置知识

学完本章后，你应能：

1. 说出 12 位 ADC 的输出范围，以及输入电压、原始值和显示电压之间的关系；
2. 为 `ADC1` 配置 `PA0` 模拟输入、规则组序列 1、单次转换和软件触发；
3. 按“启动转换 → 等待 `EOC` → 读取结果”的顺序完成单通道采集；
4. 在 `7-2 AD多通道` 中通过转换前修改序列 1，依次读取 `PA0~PA3`。

开始前应已掌握 GPIO、RCC、OLED 和基本 C 语言函数调用，并准备 STM32F103C8T6 开发板、电位器、课程所用模拟传感器模块和连接线。

## 本章闭环

`7-1 AD单通道` 与 `7-2 AD多通道` 是两个独立工程。两者都使用 `AD.c/AD.h`，但 ADC 初始化配置和 `AD_GetValue()` 参数不同，请按实验目录替换文件。

ADC 把引脚上的连续电压转换成程序可以处理的数字量。本章围绕同一条信号链完成两个实验：

```text
模拟电压 -> GPIO 模拟输入 -> ADC 通道选择 -> 采样保持
        -> 逐次逼近转换 -> ADC_DR -> 程序读取与显示
```

| 工程 | 目标 | 配置方式 |
| --- | --- | --- |
| `7-1 AD单通道` | 读取 `PA0` 电位器，显示 `0~4095` 原始值和换算电压 | 单次转换、非扫描、软件触发 |
| `7-2 AD多通道` | 依次读取 `PA0~PA3` 四路模拟量 | 每次动态选择一个通道 |

学习重点不是只得到一个数，而是理解“模拟电压 → ADC 转换 → 数字量显示”的完整过程，并能把同一套流程扩展到本章的四路轮询实验。

## 1. ADC 简介

ADC（Analog-Digital Converter，模拟-数字转换器）将引脚上连续变化的模拟电压转换为内存中可存储、处理的数字量，是模拟电路与数字电路之间的桥梁。

与 ADC 相反，DAC 将数字量转换为模拟电压。PWM 也能通过占空比得到近似的模拟效果；本章只需要区分 ADC 的方向是“模拟量转数字量”，不使用 DAC 或 PWM 完成本章实验。STM32F103C8T6 本身没有 DAC 外设。

### 1.1 STM32 ADC 的主要参数

- **12 位逐次逼近型 ADC**：量化结果范围为 $0\sim(2^{12}-1)$，即 `0~4095`。
- **最快约 $1\ \mu\text{s}$ 转换时间**：转换速度与 ADC 时钟和采样时间有关。
- **输入电压范围**：通常为 $0\sim3.3\text{ V}$，具体由参考电压决定。
- **18 个输入通道**：包括外部输入和芯片内部信号源。
- **两个转换组**：规则组最多排列 16 个通道，注入组最多排列 4 个通道。

STM32F103C8T6 具有 `ADC1`、`ADC2` 两个 ADC 外设，但受封装引脚数量限制，只引出了 10 个外部输入通道。本章只使用 `ADC1`。

![ADC 简介](assets/ppt/slide-086.png)

### 1.2 分辨率、转换时间与电压换算

位数决定量化精细程度。12 位 ADC 有 $2^{12}=4096$ 个量化等级，输出码为 `0~4095`。课堂中按满量程近似换算：

$$
V_{in}\approx\frac{D}{4095}\times 3.3\text{ V}
$$

其中 $D$ 是 ADC 读取到的原始值。这里的 `3.3 V` 是课程开发板的参考电压近似值，实验重点是理解原始值与电压的换算关系。

转换时间表示从启动转换到产生数字结果所需的时间。ADC 时钟越快、采样时间越短，单次转换通常越快，但配置仍需满足芯片的工作范围。

### 1.3 外部与内部通道

STM32 的 ADC 既有连接 GPIO 的外部通道，也有芯片内部的温度传感器和参考电压通道。本章两个实验只使用外部通道，内部通道不参与接线和程序编写。

### 1.4 规则组与其他功能

规则组用于普通转换，最多可排列 16 个通道。ADC 还提供注入组、模拟看门狗和 DMA 等功能，本章只在框图和工作模式中作整体认识，不配置这些功能。

## 2. 逐次逼近型 ADC 的工作原理

![逐次逼近型 ADC](assets/ppt/slide-087.png)

课堂以经典的 ADC0809 为例说明逐次逼近过程：

1. 多路模拟开关根据通道地址选中一路输入。
2. 比较器比较外部未知电压与内部 DAC 输出的已知电压。
3. 逐次逼近寄存器从最高位到最低位依次试探每一位是 `1` 还是 `0`。
4. 若 DAC 电压偏高，就降低试探码；若偏低，就提高试探码，直到两者近似相等。
5. 最终试探码就是输入电压的数字编码，转换完成后产生 `EOC` 信号。

这一过程类似二分查找。8 位 ADC 需要依次判断 8 位，12 位 ADC 需要判断 12 位。`START` 用于启动转换，`CLOCK` 推动逐步比较，`VREF+` 与 `VREF-` 决定 ADC 的输入范围。

## 3. STM32 ADC 框图

![STM32 ADC 完整框图](assets/ppt/slide-088.png)

![ADC 基本结构](assets/ppt/slide-089.png)

按信号流向阅读框图：

1. 外部 GPIO 通道和内部通道进入模拟多路开关；
2. 选中的通道进入规则组或注入组序列；
3. 软件或硬件触发信号启动转换；
4. `ADCCLK` 驱动逐次比较过程；
5. 转换结果进入数据寄存器；
6. 转换完成后置位相应状态标志。

### 3.1 软件触发与硬件触发

![ADC 触发控制](assets/ppt/slide-095.png)

- **软件触发**：程序调用函数启动转换，适合本章两个实验的按需读取。
- **硬件触发**：由定时器等外部事件启动转换，本章不配置硬件触发。

### 3.2 参考电压与模拟电源

`VREF+`、`VREF-` 决定 ADC 的参考范围，`VDDA`、`VSSA` 为模拟部分供电。在 STM32F103C8T6 上，参考端已在芯片内部与模拟电源相连；课程核心板上按 `VDDA=3.3V`、`VSSA=GND` 理解，因此本章输入范围按 $0\sim3.3\text{ V}$ 处理。

### 3.3 ADC 时钟

`ADCCLK` 来自 APB2 时钟经 RCC 预分频。系统配置中 `PCLK2=72MHz`，ADC 时钟上限为 `14MHz`，可选的 `/2`、`/4`、`/6`、`/8` 分频结果如下：

| 分频 | ADCCLK | 是否满足上限 |
| --- | ---: | --- |
| `/2` | 36 MHz | 否 |
| `/4` | 18 MHz | 否 |
| `/6` | 12 MHz | 是 |
| `/8` | 9 MHz | 是 |

本章选择 `/6`，即 `ADCCLK=12MHz`。

### 3.4 转换完成标志

本章采用轮询方式读取 `EOC`（End Of Conversion，转换结束）标志：启动转换后等待 `EOC` 置位，再读取转换结果。注入组、模拟看门狗和中断标志不参与本章实验。

## 4. 输入通道

![ADC 输入通道与引脚对应关系](assets/ppt/slide-090.png)

STM32F103C8T6 可用的 10 个外部 ADC 通道为：

| 通道 | 引脚 | 通道 | 引脚 |
| --- | --- | --- | --- |
| `ADC_Channel_0` | PA0 | `ADC_Channel_5` | PA5 |
| `ADC_Channel_1` | PA1 | `ADC_Channel_6` | PA6 |
| `ADC_Channel_2` | PA2 | `ADC_Channel_7` | PA7 |
| `ADC_Channel_3` | PA3 | `ADC_Channel_8` | PB0 |
| `ADC_Channel_4` | PA4 | `ADC_Channel_9` | PB1 |

本章实验使用 `ADC_Channel_0~3`，分别对应 `PA0~PA3`。内部温度传感器和内部参考电压通道不在本章实验中使用。

## 5. 规则组的四种转换模式

转换模式由“单次/连续”和“非扫描/扫描”两个开关组合而成。本章的实际代码使用单次、非扫描模式，并在单通道实验中短暂观察连续转换模式。

### 5.1 单次转换，非扫描模式

![单次转换，非扫描模式](assets/ppt/slide-091.png)

规则序列只有第 1 个位置有效。每次触发只转换该通道一次，完成后置位 `EOC` 并停止。再次转换需要重新触发；若想换通道，就在触发前改写序列 1。本章两个实验都以此模式为基础。

### 5.2 连续转换，非扫描模式

![连续转换，非扫描模式](assets/ppt/slide-092.png)

仍只使用序列 1，但一次触发后会连续重复转换。程序读取 `ADC_DR` 时得到最近一次结果。单通道实验最后会把此配置短暂改为连续模式，观察下载后的显示现象。

### 5.3 单次转换，扫描模式

![单次转换，扫描模式](assets/ppt/slide-093.png)

序列表可填写多个通道，并通过 `ADC_NbrOfChannel` 指定有效序列长度。每次触发后按顺序扫描一轮。多个结果依次经过同一个规则组数据寄存器，若要稳定保存整组数据，通常配合 DMA；本章不实现这种方式。

### 5.4 连续转换，扫描模式

![连续转换，扫描模式](assets/ppt/slide-094.png)

一次触发后不断循环扫描整个序列。它同样属于后续的自动采集方式，本章只认识其工作形式，不进行配置。

## 6. 数据对齐、转换时间与校准

### 6.1 数据对齐

12 位结果存入 16 位数据寄存器时有两种方式：

- **右对齐**：高 4 位补 `0`，直接读取就是 `0~4095`，本章使用这种方式；
- **左对齐**：结果整体左移 4 位，读取时需要按左对齐格式解释。

![ADC 数据对齐](assets/ppt/slide-096.png)

### 6.2 采样保持与转换时间

AD 转换可分为“采样保持”和“量化编码”两部分。ADC 先闭合采样开关，让内部采样电容获得输入电压；随后断开开关并保持该电压，再进行逐次比较。

STM32 ADC 的总转换时间为：

$$
T_{conv}=T_{sample}+12.5T_{ADC}
$$

当 `ADCCLK=14MHz`、采样时间为 1.5 个 ADC 周期时：

$$
T_{conv}=\frac{1.5+12.5}{14\text{ MHz}}=1\ \mu\text{s}
$$

![ADC 转换时间](assets/ppt/slide-097.png)

本章使用 55.5 周期采样时间和 `12MHz` ADC 时钟，因此一次转换约为：

$$
T_{conv}=\frac{55.5+12.5}{12\text{ MHz}}\approx5.67\ \mu\text{s}
$$

### 6.3 校准

ADC 内置自校准功能。课程按照固定流程，在 ADC 上电后执行一次：

![ADC 校准](assets/ppt/slide-098.png)

1. 复位校准寄存器；
2. 等待复位校准完成；
3. 启动校准；
4. 等待校准完成。

## 7. 硬件电路

![ADC 示例硬件](assets/ppt/slide-099.png)

### 7.1 电位器产生可调电压

电位器两个固定端分别接 `3.3V` 和 `GND`，滑动端输出约 $0\sim3.3\text{ V}$。本章单通道实验把滑动端接到 `PA0`，利用旋钮改变 ADC 输入电压。

### 7.2 模拟传感器输出

多通道实验使用光敏、热敏和反射式红外传感器模块。电位器的两端接 `3.3V` 和 `GND`，滑动端接 `PA0`；三个传感器模块的 `VCC` 接 `3.3V`、`GND` 接 `GND`，它们的 `AO` 分别接 `PA1`、`PA2`、`PA3`。`DO` 是比较器产生的数字输出，不用于本章的模拟量采集。

## 8. 实验一：AD 单通道

### 8.1 接线与配置思路

参考工程目录为 `7-1 AD单通道`。加入 `Hardware/AD.c`、`Hardware/AD.h`，并沿用 OLED 文件。电位器滑动端接 `PA0`，两端分别接 `3.3V` 和 `GND`，对应 `ADC_Channel_0`。

初始化和读取的顺序是：

1. 开启 `ADC1` 和 `GPIOA` 时钟，配置 ADC 预分频；
2. 将 `PA0` 配置为模拟输入；
3. 把通道 0 写入规则组序列 1，并设置采样时间；
4. 配置独立模式、单次转换、非扫描、软件触发和右对齐；
5. 使能 ADC 并执行校准；
6. 每次读取时执行“软件触发 → 等待 `EOC` → 读取结果”。

### 8.2 初始化代码

```c
#include "stm32f10x.h"

void AD_Init(void)
{
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_ADC1, ENABLE);
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
    RCC_ADCCLKConfig(RCC_PCLK2_Div6);

    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AIN;
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_0;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    ADC_RegularChannelConfig(
        ADC1,
        ADC_Channel_0,
        1,
        ADC_SampleTime_55Cycles5
    );

    ADC_InitTypeDef ADC_InitStructure;
    ADC_InitStructure.ADC_Mode = ADC_Mode_Independent;
    ADC_InitStructure.ADC_DataAlign = ADC_DataAlign_Right;
    ADC_InitStructure.ADC_ExternalTrigConv = ADC_ExternalTrigConv_None;
    ADC_InitStructure.ADC_ContinuousConvMode = DISABLE;
    ADC_InitStructure.ADC_ScanConvMode = DISABLE;
    ADC_InitStructure.ADC_NbrOfChannel = 1;
    ADC_Init(ADC1, &ADC_InitStructure);

    ADC_Cmd(ADC1, ENABLE);

    ADC_ResetCalibration(ADC1);
    while (ADC_GetResetCalibrationStatus(ADC1) == SET) {}
    ADC_StartCalibration(ADC1);
    while (ADC_GetCalibrationStatus(ADC1) == SET) {}
}
```

`ADC_RegularChannelConfig()` 的参数依次为 ADC 外设、通道、规则组序列位置和采样时间。本实验把通道 0 放在序列 1；`ADC_NbrOfChannel` 按工程配置填写为 `1`，本次非扫描转换实际使用的仍是序列 1。

在 `AD.h` 中声明本实验使用的两个函数：

```c
void AD_Init(void);
uint16_t AD_GetValue(void);
```

### 8.3 启动、等待与读取

```c
uint16_t AD_GetValue(void)
{
    ADC_SoftwareStartConvCmd(ADC1, ENABLE);

    while (ADC_GetFlagStatus(ADC1, ADC_FLAG_EOC) == RESET) {}

    return ADC_GetConversionValue(ADC1);
}
```

不要用 `ADC_GetSoftwareStartConvStatus()` 判断转换是否结束。它读取的是软件启动状态，而不是转换完成状态；正确做法是轮询 `ADC_FLAG_EOC`。

`ADC_GetConversionValue()` 读取 ADC 数据寄存器并返回本次转换结果。读取完成后即可进入下一次“启动 → 等待 → 读取”流程。

### 8.4 显示原始值和电压

```c
uint16_t ADValue;
float Voltage;

ADValue = AD_GetValue();
Voltage = (float)ADValue / 4095 * 3.3;
```

必须先把 `ADValue` 转成浮点数，否则整数除法会舍弃小数部分。课堂 OLED 驱动没有浮点显示函数，因此将整数部分和小数部分分开显示：

```c
OLED_ShowNum(2, 9, (uint16_t)Voltage, 1);
OLED_ShowNum(2, 11, (uint16_t)(Voltage * 100) % 100, 2);
```

将初始化和读取函数分别放入 `Hardware/AD.c`、`Hardware/AD.h` 后，`7-1 AD单通道/User/main.c` 可使用下面的完整程序：

```c
#include "stm32f10x.h"
#include "Delay.h"
#include "OLED.h"
#include "AD.h"

uint16_t ADValue;
float Voltage;

int main(void)
{
    OLED_Init();
    AD_Init();

    OLED_ShowString(1, 1, "ADValue:");
    OLED_ShowString(2, 1, "Voltage:0.00V");

    while (1)
    {
        ADValue = AD_GetValue();
        Voltage = (float)ADValue / 4095 * 3.3f;

        OLED_ShowNum(1, 9, ADValue, 4);
        OLED_ShowNum(2, 9, (uint16_t)Voltage, 1);
        OLED_ShowNum(2, 11, (uint16_t)(Voltage * 100) % 100, 2);
        Delay_ms(100);
    }
}
```

### 8.5 下载验证与临界值现象

程序下载后旋转电位器：

- 滑动端电压降低时，OLED 上的原始值随之减小，最低可接近 `0`；
- 滑动端电压升高时，原始值随之增大，最高可接近 `4095`；
- 第二行显示按照 `ADValue / 4095 × 3.3 V` 换算出的电压。

AD 值末位出现轻微波动是正常现象。如果把某个 AD 值直接用于临界判断，数值在阈值附近来回变化可能使输出反复切换。可以设置两个阈值：低于下阈值时切换到一种状态，高于上阈值时再切换回另一种状态，这就是迟滞。

### 8.6 改为连续转换

将 `ADC_ContinuousConvMode` 改为 `ENABLE`，然后在 `AD_Init()` 的校准流程结束后，只调用一次软件触发：

```c
ADC_SoftwareStartConvCmd(ADC1, ENABLE);
```

连续转换时，`AD_GetValue()` 不再重复触发或等待 `EOC`，而是直接读取最近一次结果：

```c
uint16_t AD_GetValue(void)
{
    return ADC_GetConversionValue(ADC1);
}
```

此后 ADC 会连续转换并刷新 `ADC_DR`。课堂演示中 OLED 现象与单次转换相同；实验观察完成后恢复单次转换配置。

## 9. 实验二：AD 多通道

### 9.1 接线与实验现象

参考工程目录为 `7-2 AD多通道`。加入 `Hardware/AD.c`、`Hardware/AD.h`，并沿用 OLED 文件。电位器使用滑动端作为模拟输入；后三路传感器使用模拟输出 `AO`，不能把比较器数字输出 `DO` 当作 ADC 输入。

| 信号源 | ADC 引脚 | ADC 通道 |
| --- | --- | --- |
| 电位器 | PA0 | `ADC_Channel_0` |
| 光敏传感器 `AO` | PA1 | `ADC_Channel_1` |
| 热敏传感器 `AO` | PA2 | `ADC_Channel_2` |
| 反射式红外传感器 `AO` | PA3 | `ADC_Channel_3` |

课堂中的现象为：

- 电位器旋转时，`AD0` 随之变化；
- 遮挡光敏传感器时，`AD1` 增大；
- 手握热敏传感器使其升温时，`AD2` 减小；
- 手靠近反射式红外传感器时，`AD3` 减小。

### 9.2 为什么本节不用扫描模式

扫描模式可以预先排列多个通道，各通道结果会依次写入同一个规则组数据寄存器；如果不及时把前面的结果搬走，后续转换会覆盖它，因此通常需要 DMA。

本节不实现扫描模式或 DMA，而是继续使用单次转换、非扫描模式：每次转换前动态改写规则组序列 1，然后启动转换、等待 `EOC` 并读取结果。这样更适合展示多通道读取的基本流程，扫描模式和 DMA 留到后续课程。

### 9.3 动态选择通道

将 `PA0~PA3` 全部配置为模拟输入：

```c
GPIO_InitStructure.GPIO_Pin =
    GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2 | GPIO_Pin_3;
```

在 `AD.h` 中声明本实验使用的两个函数：

```c
void AD_Init(void);
uint16_t AD_GetValue(uint8_t ADC_Channel);
```

多通道版本不再在 `AD_Init()` 中固定配置 `ADC_Channel_0`；应删除初始化函数中的那次固定通道配置，把 `ADC_RegularChannelConfig()` 放到下面的 `AD_GetValue()` 中，在每次触发前根据参数写入序列 1。

```c
uint16_t AD_GetValue(uint8_t ADC_Channel)
{
    ADC_RegularChannelConfig(
        ADC1,
        ADC_Channel,
        1,
        ADC_SampleTime_55Cycles5
    );

    ADC_SoftwareStartConvCmd(ADC1, ENABLE);
    while (ADC_GetFlagStatus(ADC1, ADC_FLAG_EOC) == RESET) {}

    return ADC_GetConversionValue(ADC1);
}
```

主循环依次读取四个通道：

```c
AD0 = AD_GetValue(ADC_Channel_0);
AD1 = AD_GetValue(ADC_Channel_1);
AD2 = AD_GetValue(ADC_Channel_2);
AD3 = AD_GetValue(ADC_Channel_3);
```

每次调用都完整执行“选择通道 → 启动转换 → 等待完成 → 读取结果”，因此四个结果分别对应四次转换。

将上述代码放入完整的 `User/main.c` 后，可直接下载验证：

```c
#include "stm32f10x.h"
#include "Delay.h"
#include "OLED.h"
#include "AD.h"

uint16_t AD0, AD1, AD2, AD3;

int main(void)
{
    OLED_Init();
    AD_Init();

    OLED_ShowString(1, 1, "AD0:");
    OLED_ShowString(2, 1, "AD1:");
    OLED_ShowString(3, 1, "AD2:");
    OLED_ShowString(4, 1, "AD3:");

    while (1)
    {
        AD0 = AD_GetValue(ADC_Channel_0);
        AD1 = AD_GetValue(ADC_Channel_1);
        AD2 = AD_GetValue(ADC_Channel_2);
        AD3 = AD_GetValue(ADC_Channel_3);

        OLED_ShowNum(1, 5, AD0, 4);
        OLED_ShowNum(2, 5, AD1, 4);
        OLED_ShowNum(3, 5, AD2, 4);
        OLED_ShowNum(4, 5, AD3, 4);
        Delay_ms(100);
    }
}
```

## 10. 下载验证与排错

### 10.1 单通道验收

1. 确认电位器两端接 `3.3V` 和 `GND`，滑动端接 `PA0`；
2. 下载 `7-1 AD单通道` 程序；
3. 旋转电位器，确认 OLED 第一行的原始值在 `0~4095` 范围内变化；
4. 确认第二行电压显示随原始值变化，旋钮两端附近分别接近 `0 V` 和 `3.3 V`。

### 10.2 多通道验收

1. 按照 `PA0~PA3` 与 `ADC_Channel_0~3` 的对应关系接线；
2. 电位器滑动端接 `PA0`；后三个传感器的 `VCC`、`GND` 和 `AO` 分别按接线表连接，并与开发板共地；
3. 下载 `7-2 AD多通道` 程序；
4. 旋转、遮挡、加热或靠近对应传感器，确认 OLED 的 `AD0~AD3` 分别产生相应变化。

### 10.3 常见问题

| 现象 | 优先检查 |
| --- | --- |
| 原始值始终为 `0` | 传感器输出是否接到对应引脚、GPIO 是否为模拟输入、ADC1 时钟是否开启 |
| 原始值没有变化 | 电位器两端电源、传感器是否接 `AO`、信号线是否接错 |
| 单通道数值与电压显示不对应 | 换算式中的 `4095`、`3.3` 和浮点转换是否正确 |
| 多通道数据对应错误 | `ADC_Channel_0~3` 与 `PA0~PA3` 的对应关系、主循环调用顺序 |
| 程序卡在等待转换 | ADC 是否使能、是否执行软件触发、是否轮询 `ADC_FLAG_EOC` |

排错时按“接线 → GPIO 模拟输入 → ADC 时钟与通道 → 软件触发 → `EOC` → 读取结果”的顺序逐段确认。

## 本章小结

本章完成了两个 ADC 实验：

- `7-1 AD单通道` 使用 `ADC1` 的 `ADC_Channel_0`，以单次、非扫描、软件触发方式读取 `PA0` 电位器，并在 OLED 上显示原始值和换算电压；
- `7-2 AD多通道` 仍使用单次、非扫描方式，在每次转换前动态修改规则组序列 1，依次读取 `PA0~PA3` 四路模拟量；
- 两个实验的共同读取流程是“启动转换 → 等待 `EOC` → 读取结果”；
- 扫描模式下的多通道自动保存需要 DMA，留到后续课程学习。
