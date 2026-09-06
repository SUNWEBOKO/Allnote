# STM32F103 ADC：从模拟量转换到定时器触发采集

## 学习目标与适用范围

本章以 STM32F103 的 12 位逐次逼近型 ADC 为主线，完成“理解原理—计算时间—编写 HAL 程序—扩展多通道—实现定时采样”的闭环。读完后应能：

- 解释采样、量化、编码和逐次逼近的关系；
- 根据参考电压和分辨率把 ADC 原码换算为电压；
- 计算 ADC 时钟、采样时间、转换时间和理论采样率；
- 使用 HAL 完成单通道软件触发转换；
- 使用扫描模式和 DMA 采集多个通道；
- 将 NTC、电位器、片内温度传感器和 VREFINT 组合到一个采集序列中；
- 用定时器 TRGO 产生固定周期的 ADC 触发事件。

默认对象为常见 STM32F103C8T6 最小系统板，默认 ADC 参考电压近似为 `3.3 V`。具体通道号、ADC 时钟上限、内部温度传感器误差、VREFINT 校准值和触发源选项，必须以目标芯片的数据手册、参考手册和板卡原理图为准。

## 1. ADC 要解决什么问题

GPIO、串口和定时器主要处理数字信号，而光照、电位器电压、热敏电阻电压和电池电压本质上是连续变化的模拟量。ADC（Analog-to-Digital Converter）把某一时刻的模拟电压映射为有限位数的数字码，供 CPU、DMA 或控制算法处理。

一次 ADC 测量可以拆成四个动作：

1. **采样**：通过采样开关，让输入电压给内部采样电容充电；
2. **保持**：断开开关，暂时保持电容上的电压；
3. **量化**：把保持电压与参考电压范围内的离散等级比较；
4. **编码**：把比较结果写入数据寄存器。

因此，ADC 原码不是“电压本身”，而是电压在参考范围内所处等级的编号。

## 2. 12 位 ADC 的量化关系

### 2.1 分辨率、满量程与原码

12 位 ADC 有 $2^{12}=4096$ 个编码，原码范围为 `0~4095`。若参考电压为 $V_{REF}$，常用近似换算为：

$$V_{in} \approx \frac{ADC\_Code}{2^{N}-1}V_{REF}$$

对 12 位、`3.3 V` 参考电压：

$$V_{in} \approx \frac{ADC\_Code}{4095}\times 3.3\,\text{V}$$

理想量化步长约为：

$$\Delta V = \frac{V_{REF}}{2^{N}-1}=\frac{3.3}{4095}\approx 0.806\,\text{mV}$$

有些资料用 $V_{REF}/2^N$ 定义一个 LSB，约为 `0.805 mV`。两种写法只相差一个量化定义，工程中必须保持前后一致。

### 例 1：把 ADC 原码换算为电压

**题目**：12 位 ADC 的原码为 `2048`，参考电压按 `3.3 V` 计算，求输入电压。

**解答**：

$$V_{in}=\frac{2048}{4095}\times 3.3\approx 1.6504\,\text{V}$$

因此 `2048` 约对应参考电压的一半。若要求更准确的供电补偿，不能永远假设 `VREF = 3.3 V`，应使用 VREFINT 估算实际参考电压。

### 2.2 ADC 的输入边界

ADC 输入必须处于芯片允许的模拟输入范围内，通常不能超过 `VSSA~VDDA`。输入超过参考范围会产生饱和或损坏风险；负电压也不能直接送入普通 ADC 通道。GPIO 必须配置为模拟输入，以关闭数字输入路径、降低干扰和功耗。

## 3. 逐次逼近型 ADC 的工作原理

STM32F1 使用 SAR（Successive Approximation Register，逐次逼近寄存器）型 ADC。可以把它类比为用天平和砝码称重：

1. 先把待测电压采样并保持；
2. 先尝试最高位对应的“砝码”，例如半量程；
3. 若试探值不超过输入电压，就保留该位，否则清除该位；
4. 再依次试探下一位；
5. 经过 12 次比较后，得到 12 位二进制结果。

假设待测电压为 `0.9 V`、参考电压为 `3.3 V`：

- 最高位试探半量程 `1.65 V`，输入较小，最高位置 `0`；
- 接着试探剩余码值代表的电压；
- 每一步都保留“不会超过输入”的最大组合；
- 最终得到约 `0.9/3.3×4095 ≈ 1117` 的原码。

这个过程解释了两个重要事实：

- **转换时间与分辨率相关**：位数越高，需要的逐次比较越多；
- **采样时间与信号源相关**：采样电容必须先充到足够接近输入电压，输入源阻抗越大，充电越慢。

## 4. ADC 时钟与时间预算

### 4.1 ADC 时钟来源

STM32F103 的 ADC1、ADC2 通常挂载在 APB2。ADC 时钟由 `PCLK2` 经过专用预分频器得到：

$$f_{ADC}=\frac{PCLK2}{ADC\_Prescaler}$$

F103 常见 ADC 时钟上限为 `14 MHz`。例如 `PCLK2 = 72 MHz` 时：

```text
/2 -> 36 MHz，超限
/4 -> 18 MHz，超限
/6 -> 12 MHz，满足
/8 ->  9 MHz，满足
```

CubeMX 通常会在设置系统主频后自动提示或选择合适的 ADC 分频，但仍应在 Clock Configuration 页面检查实际值。

ADC 时钟周期为：

$$T_{ADC}=\frac{1}{f_{ADC}}$$

例如 `fADC = 14 MHz` 时，$T_{ADC}\approx 71.43\,\text{ns}$。

### 4.2 转换时间

对 STM32F1 的 12 位 ADC，逐次逼近转换阶段通常固定消耗：

$$T_{conv}=12.5T_{ADC}$$

其中 `12` 个周期对应 12 位逐次比较，额外 `0.5` 个周期属于器件内部转换开销。实际工程应以具体型号手册的 ADC conversion time 表格为准。

### 4.3 采样时间

采样阶段由采样开关和采样电容完成。输入信号源并非理想电压源，总存在源阻抗 $R_S$；ADC 内部也有等效采样电阻 $R_{ADC}$ 和采样电容 $C_{ADC}$。采样电压按照 RC 充电规律逼近输入：

$$V_C(t)=V_{in}\left(1-e^{-t/((R_S+R_{ADC})C_{ADC})}\right)$$

采样时间太短时，电容尚未充满，转换结果会偏离真实值。分辨率越高，允许的采样误差越小；源阻抗越大，所需采样时间越长。

教学材料给出的设计原则是：把采样误差控制在约四分之一 LSB 以内。对 12 位、`3.3 V` 量程：

$$1\,LSB\approx 0.806\,\text{mV},\qquad \frac{1}{4}LSB\approx 0.202\,\text{mV}$$

采样时间应根据数据手册中的 $R_S$、$R_{ADC}$、$C_{ADC}$ 和误差要求计算，再向上选择一个可用档位。STM32F1 常见采样时间档位包括 `1.5、7.5、13.5、28.5、41.5、55.5、71.5、239.5` 个 ADC 周期；具体选项以芯片和 HAL 版本为准。

### 例 2：估算一次转换的最短时间

**题目**：理想信号源近似为零阻抗，ADC 时钟为 `14 MHz`，根据教学材料选择 `1.5` 周期采样时间，求单次转换理论耗时和最大转换次数。

**解答**：

$$T_{total}=(1.5+12.5)T_{ADC}=14T_{ADC}$$

$$T_{ADC}=\frac{1}{14\,\text{MHz}}$$

$$T_{total}=1\,\mu\text{s}$$

理想连续运行时约为 `1 MSPS`。这是理论上限，不包含触发、DMA、CPU、总线仲裁和软件处理开销；实际采样率通常更低。

### 4.4 采样时间不是越短越好

选择采样时间时要在精度和吞吐率之间折中：

| 情况 | 选择倾向 |
| --- | --- |
| 低阻抗缓冲器、追求高速 | 可选较短采样时间，但要验证误差 |
| 电位器、NTC、分压电阻较大 | 选择更长采样时间，必要时增加缓冲器 |
| 片内温度传感器、VREFINT | 按手册要求使用较长采样时间 |
| 采样结果跳动、偏低或通道切换后异常 | 先增加采样时间，再检查源阻抗和布局 |

## 5. 单通道软件触发转换

### 5.1 CubeMX 配置要点

以 ADC1 单通道为例：

1. 将目标 GPIO 配置为 `Analog`；
2. 在 `ADC1` 中使能规则组（Regular Conversions）；
3. 设置转换数量为 `1`；
4. 选择目标通道和采样时间；
5. 规则组外部触发选择软件启动；
6. 设置 ADC 时钟分频，使 $f_{ADC}\le 14\,\text{MHz}$；
7. 生成代码后，在第一次转换前执行 ADC 校准。

### 5.2 HAL 调用链

单次轮询的逻辑是：

```text
HAL_ADC_Start
    -> 软件触发规则组
HAL_ADC_PollForConversion
    -> 轮询 EOC，等待转换结束
HAL_ADC_GetValue
    -> 读取 ADC 数据寄存器 DR
原码 -> 电压/物理量
```

示例代码：

```c
uint32_t adc_code;
float voltage;

if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
    /* 校准失败时不要继续使用采样结果。 */
    Error_Handler();
}

while (1)
{
    if (HAL_ADC_Start(&hadc1) == HAL_OK)
    {
        if (HAL_ADC_PollForConversion(&hadc1, HAL_MAX_DELAY) == HAL_OK)
        {
            adc_code = HAL_ADC_GetValue(&hadc1);
            /* 12 位 ADC 满量程为 4095，不是 4096。 */
            voltage = (float)adc_code * 3.3f / 4095.0f;
        }
    }
    HAL_Delay(10);
}
```

`HAL_ADC_Start()` 启动规则组；`HAL_ADC_PollForConversion()` 通过 EOC（End of Conversion）等待常规转换完成；`HAL_ADC_GetValue()` 读取常规数据寄存器 DR。注入组使用不同的触发路径和 JDR 数据寄存器，不能与规则组混淆。

### 5.3 校准的意义

ADC 存在内部偏置和模拟误差。STM32F1 通常建议每次上电后、第一次正式转换前执行一次校准：

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
    Error_Handler();
}
```

校准不能消除参考电压误差、输入源阻抗误差和量化误差，但能改善 ADC 内部偏置造成的系统误差。

### 5.4 连续转换模式

连续模式打开后，ADC 完成一个规则序列后自动开始下一轮。软件只需启动一次：

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
    Error_Handler();
}
if (HAL_ADC_Start(&hadc1) != HAL_OK)
{
    Error_Handler();
}

while (1)
{
    if (HAL_ADC_PollForConversion(&hadc1, HAL_MAX_DELAY) == HAL_OK)
    {
        uint32_t value = HAL_ADC_GetValue(&hadc1);
        /* 使用 value */
    }
}
```

连续模式适合持续监测，但会持续占用 ADC 和可能的 DMA 带宽；若采样必须等间隔，优先使用定时器触发。

## 6. 多通道扫描与 DMA

### 6.1 规则组就是“转换队列”

ADC 规则组可以登记多个 Rank。一次触发后，ADC 按 Rank 顺序依次转换：

```text
Rank 1 -> 通道 5：电位器
Rank 2 -> 通道 4：NTC 分压
Rank 3 -> 内部温度传感器
Rank 4 -> VREFINT
```

打开多个 Rank 后，扫描模式才有意义。每个通道都有独立采样时间；内部通道通常需要比低阻抗外部通道更长的采样时间。

### 6.2 为什么多通道通常需要 DMA

STM32F1 的规则组结果通常依次写入同一个 DR。若 CPU 还没取走前一个结果，下一通道完成后可能覆盖 DR；仅靠轮询还难以可靠区分当前结果属于哪个 Rank。

DMA 可在每次 EOC 后自动执行：

```text
ADC1->DR -> values[0]
ADC1->DR -> values[1]
ADC1->DR -> values[2]
ADC1->DR -> values[3]
```

典型配置：外设到内存、外设地址不递增、内存地址递增、数据宽度 `Half Word`、普通模式或循环模式。

```c
uint16_t adc_values[4];

if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
    Error_Handler();
}
if (HAL_ADC_Start_DMA(&hadc1, (uint32_t *)adc_values, 4U) != HAL_OK)
{
    Error_Handler();
}

while (1)
{
    float potentiometer = (float)adc_values[0] * 3.3f / 4095.0f;
    float ntc_voltage   = (float)adc_values[1] * 3.3f / 4095.0f;
    /* adc_values[2]：内部温度，adc_values[3]：VREFINT */
    HAL_Delay(100);
}
```

若开启连续扫描，DMA 应使用循环模式，数组写满后从 `values[0]` 重新开始。使用 DMA 时要确认数组元素类型与 DMA 数据宽度匹配：`uint16_t` 对应 Half Word，`uint32_t` 对应 Word。

### 6.3 DMA 完成回调

普通 DMA 模式下，一轮 Rank 全部传输完成后可在回调中处理数组：

```c
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1)
    {
        /* adc_values[0..3] 已完成一轮更新 */
    }
}
```

循环模式下，主循环可以持续读取数组，但要考虑读取过程中数组被 DMA 更新的问题。对高可靠应用，应使用双缓冲、序号或短临界区，避免处理半更新数据。

## 7. NTC 热敏电阻测温

### 7.1 分压原理

NTC（Negative Temperature Coefficient）温度越高，阻值越小。它与固定电阻串联形成分压，ADC 测量中点电压。若固定电阻为 $R_F$，NTC 为 $R_T$，且中点电压取在 NTC 一侧，需根据实际接线选择公式：

$$V_{out}=V_{REF}\frac{R_T}{R_F+R_T}$$

反解得到：

$$R_T=R_F\frac{V_{out}}{V_{REF}-V_{out}}$$

若电阻上下位置相反，分压公式会改变。不要脱离原理图直接套用。

### 7.2 阻值换算为温度

NTC 的阻值到温度通常使用 Beta 模型或 Steinhart–Hart 模型。Beta 模型的一种常见形式为：

$$\frac{1}{T}=\frac{1}{T_0}+\frac{1}{B}\ln\left(\frac{R}{R_0}\right)$$

其中 $T$、$T_0$ 为开尔文温度，$R$、$R_0$ 为对应阻值，$B$ 为热敏电阻参数。最后换算摄氏度：

$$T_{^\circ C}=T-273.15$$

必须使用实际 NTC 的 $R_0$、$B$ 或厂家 Steinhart–Hart 系数。只知道“10 kΩ”不足以唯一确定温度曲线。

### 例 3：为什么握住 NTC 后 ADC 电压可能下降

**题目**：开发板上的 NTC 与 `10 kΩ` 电阻分压，中点接 ADC。握住 NTC 后，串口显示的 NTC 电压变小，是否与 NTC 的负温度系数矛盾？

**分析**：握住后温度升高，NTC 阻值下降。若 NTC 位于分压上臂、固定电阻位于下臂，则：

$$V_{out}=V_{REF}\frac{R_F}{R_T+R_F}$$

随着 $R_T$ 下降，分母变小，分压中点电压会升高；若实际接线是 NTC 位于下臂，则：

$$V_{out}=V_{REF}\frac{R_T}{R_F+R_T}$$

随着 $R_T$ 下降，电压会降低。

**结论**：现象取决于 NTC 在分压器中的位置，必须先看原理图再解释电压变化。温度方向正确但电压方向相反，并不一定是 ADC 错误。

## 8. VREFINT 与片内温度传感器

### 8.1 用 VREFINT 修正实际参考电压

直接使用 `3.3 V` 计算外部电压是假设供电精确稳定。STM32 内部提供约 `1.2 V` 的 VREFINT 通道。测得其 ADC 原码后，可以反推出实际 VDDA：

$$V_{DDA}\approx \frac{V_{REFINT}}{ADC_{VREFINT}}(2^N-1)$$

然后再用估计的 $V_{DDA}$ 计算外部通道电压：

$$V_{in}\approx \frac{ADC_{in}}{2^N-1}V_{DDA}$$

VREFINT 的典型值和芯片个体误差需以数据手册或出厂校准常数为准。把 `1.2 V` 当作绝对精确值只能得到近似补偿。

### 8.2 片内温度传感器

片内温度传感器适合观察温度变化趋势，但绝对误差可能较大。教学材料特别提醒：不要把它当作高精度温度计；若需要精确温度，应使用外部校准传感器或经过完整标定的器件。

内部通道通常具有较长的最小采样时间要求。例如数据手册给出的 VREFINT 最小采样时间约为 `5.1 μs`，片内温度传感器最小采样时间约为 `17.1 μs`；应根据当前 ADC 时钟换算为周期并选择不低于要求的档位。

## 9. 定时器触发 ADC

### 9.1 为什么不用软件循环定时

在 `while` 中反复调用 `HAL_ADC_Start()`，采样间隔会受到循环执行时间、中断、串口输出和其他任务影响，难以保持固定。定时器可以硬件产生稳定的触发事件，让 ADC 在确定的时间点开始转换。

ADC 常规组外部触发源大致分为两类：

- **定时器 CCx 事件**：捕获/比较通道发生匹配或捕获时产生；
- **定时器 TRGO**：定时器主模式控制器输出触发信号，常用 Update Event。

### 9.2 用 TIM3 TRGO 每 1 ms 触发一次

假设默认系统时钟为 `8 MHz`，TIM3 输入时钟也为 `8 MHz`，希望每 `1 ms` 产生一次更新事件。定时器更新频率为：

$$f_{update}=\frac{f_{TIM}}{(PSC+1)(ARR+1)}$$

选择：

```text
PSC = 7    -> 计数频率 = 8 MHz / 8 = 1 MHz
ARR = 999  -> 每 1000 个计数更新一次
fupdate = 1 MHz / 1000 = 1 kHz
周期 = 1 ms
```

### 9.3 CubeMX 配置路径

1. 启用 ADC 输入通道并设置规则组转换数量为 `1`；
2. 在 TIM3 中选择 Internal Clock；
3. 设置 Prescaler=`7`、Counter Period/ARR=`999`、向上计数；
4. 将 TIM3 Trigger Event Selection 设置为 `Update Event`，使 TRGO 输出更新事件；
5. 回到 ADC1，将 Regular Conversion External Trigger Source 选择为 `TIM3 TRGO`；
6. 设置合适的采样时间和 ADC 时钟；
7. 生成代码并检查启动顺序。

### 9.4 HAL 启动顺序

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
    Error_Handler();
}
if (HAL_ADC_Start(&hadc1) != HAL_OK)       /* 使能 ADC 外部触发路径 */
{
    Error_Handler();
}
if (HAL_TIM_Base_Start(&htim3) != HAL_OK)  /* 开始产生 TIM3 TRGO */
{
    Error_Handler();
}

while (1)
{
    if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
    {
        uint32_t value = HAL_ADC_GetValue(&hadc1);
        /* 每次 TRGO 触发后得到一个新结果 */
    }
}
```

具体工程中，ADC 外部触发配置可能要求先启动 ADC 再启动定时器，也可能由 CubeMX 生成的初始化顺序决定。核心是不再手动发送软件触发，而是让 `TIM3 TRGO -> ADC Regular Trigger -> EOC -> DR/DMA` 形成硬件链路。

若要连续记录波形，可将 DMA 与定时器触发结合：每个 TRGO 启动一次 ADC 转换，EOC 触发 DMA 搬运一个样本，数组填满后在 DMA 完成回调中处理或发送。

## 10. 采集链路与问题定位

把 ADC 问题按完整信号链定位：

```text
传感器/分压 -> GPIO 模拟输入 -> 采样开关与电容
-> ADC 时钟/采样时间 -> SAR 转换 -> DR
-> DMA/CPU -> 电压换算 -> 物理量与控制逻辑
```

### 10.1 结果为 0 或接近满量程

- GPIO 没有配置为模拟输入；
- 通道号与实际引脚不一致；
- 输入没有共地；
- 输入超过 `VDDA` 或接近地；
- 读取的是错误 ADC 实例或错误数组下标。

### 10.2 数值偏低、跳动或通道切换后异常

- 采样时间太短，输入源阻抗过大；
- NTC/电位器分压电阻过大且没有缓冲；
- 多通道扫描时 DR 被覆盖；
- DMA 数据宽度、内存递增或数组长度配置错误；
- 模拟电源、地线或布局噪声较大。

优先增加采样时间、降低源阻抗或加缓冲器，再检查 DMA。

### 10.3 触发频率不对

- TIM 时钟不是假设的 `8 MHz`，可能已切换到 `72 MHz`；
- 漏掉预分频器和 ARR 的 `+1`；
- APB 分频大于 1 时定时器时钟可能自动乘 2；
- ADC 外部触发源没有选为目标 TRGO；
- TIM3 未启动或 TRGO 未选择 Update Event。

## 11. 选择哪种采集架构

| 需求 | 推荐方式 | 主要代价 |
| --- | --- | --- |
| 偶尔读一个电位器 | 单通道、软件触发、轮询 | CPU 会等待转换 |
| 持续监测单通道 | 连续转换，必要时 DMA | 采样间隔不一定由软件决定 |
| 多个慢变化传感器 | 扫描 + DMA | 需要管理 Rank 顺序和数组 |
| 固定采样率波形 | 定时器 TRGO + ADC + DMA | 配置链较长，但时间确定性最好 |
| 需要低功耗周期采样 | 定时器/低功耗触发路径 | 需核对具体低功耗唤醒能力 |

## 12. 自测题

1. 12 位 ADC、`3.3 V` 参考电压时，原码 `2048` 约对应多少电压？
2. 为什么 ADC 时钟为 `14 MHz` 时不能把 `PCLK2=72 MHz` 直接送入 ADC？
3. STM32F1 12 位 ADC 的转换阶段为什么通常按 `12.5` 个 ADC 周期计算？
4. 输入源阻抗增大时，采样时间应如何调整？
5. 多通道扫描为什么容易需要 DMA？
6. `PSC=7、ARR=999、TIM3=8 MHz` 时，TRGO 更新周期是多少？
7. 为什么 NTC 握热后电压升降必须结合分压接线判断？
8. VREFINT 如何帮助修正实际 VDDA？

**答案要点**：

1. 约 `1.65 V`；
2. F103 ADC 时钟常见上限为 `14 MHz`，需要专用分频；
3. 12 个逐次比较周期加约 `0.5` 个内部开销周期；
4. 增大采样时间，必要时降低源阻抗或增加缓冲；
5. 规则组结果依次写入 DR，CPU 可能来不及取走而被覆盖；
6. `1 ms`；
7. NTC 位于分压上臂还是下臂会决定温度升高时中点电压方向；
8. 由已知约 `1.2 V` 的 VREFINT 原码反推实际 VDDA，再用于外部通道换算。

## 本章小结

ADC 学习不能停在“读出一个数字”。完整理解应包含：

```text
模拟输入 -> 采样保持 -> 逐次逼近量化 -> 原码
-> 参考电压/分辨率换算 -> DMA 或 CPU 搬运 -> 物理量与控制
```

采样时间决定输入电容能否充足，转换时间决定 SAR 完成一次量化所需的周期，ADC 时钟决定这些周期的实际长度；扫描和 DMA 解决多通道连续搬运，定时器 TRGO 解决固定采样间隔。把这几条链路连起来，才能从“能读 ADC”进阶到“能设计可靠的采集系统”。
