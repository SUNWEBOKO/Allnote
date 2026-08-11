# STM32 HAL 库 ADC 教学文档

## 1. 学完以后能做什么

完成本文后，你应该能够：

- 解释 ADC、模拟信号、数字信号、采样、量化和分辨率的含义。
- 说明逐次逼近型 ADC 为什么像一架不断试砝码的天平。
- 看懂 STM32 ADC 的输入通道、常规序列、注入序列、触发源和数据寄存器。
- 从 `PCLK2` 推导 ADC 时钟，并检查它是否超过目标芯片允许的上限。
- 根据信号源内阻估算采样时间，并在 CubeMX 中选择合适的采样周期档位。
- 使用 `HAL_ADC_Start()`、`HAL_ADC_PollForConversion()` 和 `HAL_ADC_GetValue()` 完成单通道转换。
- 使用 `TIM3 TRGO` 以固定频率触发 ADC。
- 配置多通道 Rank、ADC1 DMA1 Channel1 和双半区循环缓冲区，取得稳定数据帧。
- 把 NTC、Vrefint 和片内温度通道的 ADC 码转换为有意义的物理量。
- 沿着“输入 -> 采样 -> 转换 -> DMA 搬运 -> 稳定快照 -> 物理量”的链路排查 ADC 实验。

## 2. ADC 到底在做什么

ADC 是 Analog-to-Digital Converter 的缩写，即模数转换器。它把外部世界中的模拟量转换成程序可以保存和处理的数字量。

常见模拟量包括：

- 光敏器件输出的电压。
- 温度传感器输出的电压。
- 电位器滑动端的电压。
- 麦克风调理电路输出的波形。
- 电池电压经过分压后的检测信号。

MCU 不能直接把“亮度”“温度”或“声音”存进变量。传感器通常先把这些物理量转换为电压，ADC 再把电压转换为整数：

```text
物理量
  -> 传感器与调理电路
  -> 模拟电压
  -> ADC 采样与量化
  -> 数字码
  -> 程序判断、显示、记录或控制
```

### 2.1 模拟信号与数字信号

模拟信号在时间和幅值上可以连续变化。例如，气温不会只在整点发生变化，电压也可以处在 `1.700 V` 和 `1.701 V` 之间的任意值。

数字系统只能用有限位数保存结果，因此会进行两次离散化：

1. **时间离散**：每隔一段时间测量一次，这个过程称为采样。
2. **幅值离散**：把连续电压映射到有限个数字码，这个过程称为量化。

采样间隔决定“多久测一次”，量化位数决定“每次能分多细”。二者不是同一个概念。

### 2.2 12 位意味着什么

STM32F103 的 ADC 为 12 位 ADC。12 位结果共有：

$$
2^{12}=4096
$$

个可能的数字码，即 `0`～`4095`。

若参考电压为 `3.3 V`，把整个输入范围分成 4096 个量化区间，则常说的 1 LSB 大约为：

$$
q=\frac{V_{REF+}-V_{REF-}}{2^{12}}
=\frac{3.3\ \mathrm{V}}{4096}
\approx 0.806\ \mathrm{mV/LSB}
$$

位数越高，量化台阶通常越细，但这不等于实际测量一定同样准确。参考电压误差、噪声、传感器误差、布线和 ADC 本身的非理想特性都会影响结果。

### 2.3 数字码怎样换算成电压

入门实验中常用端点近似公式：

$$
V_{IN}\approx D\times\frac{V_{REF}}{2^N-1}
$$

其中：

- $D$ 是 ADC 原始码。
- $N$ 是 ADC 位数，本文中 $N=12$。
- $V_{REF}$ 是实际参考电压，很多开发板上近似等于 `VDDA`。

对于 12 位、`3.3 V` 参考电压：

$$
V_{IN}\approx D\times\frac{3.3}{4095}
$$

这里需要区分两种口径：

- 描述理想量化步长时，通常使用 $V_{REF}/2^N$。
- 把 `0` 和满量程码 `4095` 分别近似映射到 `0 V` 和 `3.3 V` 时，常使用 $D\,V_{REF}/(2^N-1)$。

二者只相差约一个 LSB 的比例，但写公式时应说明采用哪种口径。

## 3. 逐次逼近型 ADC 的工作原理

STM32F103 使用 SAR ADC。SAR 是 Successive Approximation Register 的缩写，即逐次逼近寄存器。

它的核心任务不是一次猜中输入电压，而是从最高位到最低位逐位试探。这个过程很像使用一组二进制权重的砝码称重：先试最大的砝码，再依次试更小的砝码；太重就取下，仍然偏轻就保留。

### 3.1 内部结构

逐次逼近型 ADC 可以简化为：

```text
模拟输入
   |
   v
采样开关 + 保持电容 ----> 比较器 <---- 内部 DAC
                             ^             ^
                             |             |
                             +------ SAR 寄存器
                                        |
                                        v
                                     转换结果
```

各部分的作用如下：

| 模块 | 作用 |
| --- | --- |
| 采样开关 | 在采样阶段把输入信号接到内部采样电容 |
| 保持电容 | 开关断开后暂时保持待转换电压 |
| 内部 DAC | 根据 SAR 当前试探码生成比较电压 |
| 比较器 | 判断输入保持电压和 DAC 电压谁更大 |
| SAR 寄存器 | 从最高位到最低位决定每一位保留 `1` 还是恢复为 `0` |
| 数据寄存器 | 保存最终数字结果 |

### 3.2 为什么先采样再转换

转换一个 12 位结果需要连续进行多次比较。如果输入电压在这些比较期间不断变化，各位对应的就不是同一个瞬时电压，结果会失去一致性。

因此 ADC 先闭合采样开关，让输入信号给保持电容充电；采样结束后断开开关，电容在转换阶段尽量维持这个电压。可以把完整过程分成两段：

```text
采样阶段：开关闭合，电容跟随输入电压
转换阶段：开关断开，SAR 逐位试探并生成数字码
```

### 3.3 4 位逐次逼近示例

为了便于手算，假设有一个理想 4 位 ADC，输入范围为 `0`～`3.3 V`。它的量化步长为：

$$
\frac{3.3}{2^4}=\frac{3.3}{16}=0.20625\ \mathrm{V}
$$

输入电压为 `2.21 V`，理想结果约为：

$$
\frac{2.21}{0.20625}\approx 10.72
$$

`2.21 V` 落在数字码 `10` 对应的量化区间内，十进制 `10` 即二进制 `1010`。SAR 的试探过程如下：

| 步骤 | 试探码 | DAC 近似输出 | 比较结果 | 该位处理 |
| --- | --- | ---: | --- | --- |
| 试最高位 $B_3$ | `1000` | `1.65000 V` | 小于 `2.21 V` | 保留 $B_3=1$ |
| 试 $B_2$ | `1100` | `2.47500 V` | 大于 `2.21 V` | 清除 $B_2=0$ |
| 试 $B_1$ | `1010` | `2.06250 V` | 小于 `2.21 V` | 保留 $B_1=1$ |
| 试最低位 $B_0$ | `1011` | `2.26875 V` | 大于 `2.21 V` | 清除 $B_0=0$ |

最终得到 `1010`。对于 12 位 ADC，同样从最高位试到最低位，只是需要处理 12 个比特。

## 4. STM32F103 ADC 模块怎么组织

STM32F103C8T6 集成 ADC1 和 ADC2，两者的外设时钟都来自 APB2 侧的 ADC 时钟分支。在常见 STM32F103C8T6 封装上，可以使用 `PA0`～`PA7`、`PB0` 和 `PB1` 等外部模拟输入。ADC1 还可以测量片内温度传感器和内部参考电压通道。具体可用通道与引脚取决于芯片型号和封装，不能把其他 F103 型号的通道数量直接套用过来。

### 4.1 多路输入共用一个转换核心

ADC 不需要为每个输入引脚各放置一套完整 SAR 转换器。它使用模拟多路选择器，把选中的通道依次接到转换核心：

```text
ADC_IN0 --\
ADC_IN1 ---\
ADC_IN2 ----> 模拟多路选择器 -> 采样保持 -> SAR -> 数据寄存器
...       ---/
内部通道 --/
```

因此“多通道转换”在时间上仍然是按计划逐个完成，而不是真正同时完成。

### 4.2 常规序列与注入序列

STM32F103 ADC 提供两套转换计划：

| 序列 | 主要特点 | 结果位置 |
| --- | --- | --- |
| 常规序列（Regular group） | 适合一般周期采样，可安排最多 16 个 Rank | `DR` 数据寄存器 |
| 注入序列（Injected group） | 可被特定事件插入，最多 4 个 Rank | `JDR1`～`JDR4` |

本文两个实验都只使用常规序列。注入序列用于理解模块结构，不在本文中展开编程。

### 4.3 Channel、Rank 和采样时间

这三个概念必须分开：

- **Channel**：输入通道编号，例如 `ADC_CHANNEL_0` 对应 `ADC1_IN0`。
- **Rank**：通道在常规序列中的执行顺序，例如 Rank 1、Rank 2。
- **Sampling Time**：该通道每次采样阶段持续多少个 ADC 时钟周期。

例如：

```text
Rank 1: Channel 0,  7.5 cycles
Rank 2: Channel 4, 13.5 cycles
Rank 3: Channel 2, 28.5 cycles
```

每来一次序列触发，ADC 就按 `0 -> 4 -> 2` 的顺序完成一轮转换。不同通道可以根据信号源阻抗选择不同采样时间。

### 4.4 软件触发与硬件触发

常规序列需要一个启动事件：

- **软件触发**：程序调用 `HAL_ADC_Start()` 时发起转换，适合按需读取和最小实验。
- **定时器触发**：定时器的比较事件或 `TRGO` 触发 ADC，适合固定采样间隔。

软件循环加 `HAL_Delay(1)` 不能替代严格的 `1 kHz` 硬件触发。主循环还会受到串口、其他任务和中断的影响，间隔会产生抖动；定时器触发则由硬件事件确定采样时刻。

### 4.5 状态标志与结果寄存器

本文会遇到以下状态和寄存器：

| 名称 | 含义 |
| --- | --- |
| `EOC` | End of Conversion，常规转换结束标志 |
| `JEOC` | Injected End of Conversion，注入转换结束标志 |
| `AWD` | Analog Watchdog，模拟看门狗状态 |
| `DR` | 常规转换数据寄存器 |
| `JDR1`～`JDR4` | 注入转换数据寄存器 |

`HAL_ADC_PollForConversion()` 会等待转换完成状态，`HAL_ADC_GetValue()` 则读取常规组结果。多通道、连续转换以及不同 HAL 配置下的 `EOC` 语义可能不同，不能只凭单通道实验推断所有模式。

### 4.6 单次、连续、扫描和触发的关系

这几个配置项控制的不是同一件事：

| 配置维度 | 回答的问题 | 典型选择 |
| --- | --- | --- |
| 单次/连续转换 | 一次触发后只执行一轮，还是自动重复执行 | `ContinuousConvMode` |
| 扫描模式 | 一轮转换包含一个 Rank，还是依次执行多个 Rank | `ScanConvMode` |
| 软件/外部触发 | 第一轮转换在什么时刻启动 | `ExternalTrigConv` |

因此，单通道也可以连续转换，多通道也可以每次触发只扫描一轮。不要把“扫描”和“连续”当成同义词。

单次转换模式下，每次触发只执行一轮常规序列：

```text
触发 -> 执行 Rank 1...N -> 停止并等待下一次触发
```

连续转换模式下，第一次触发后会自动重复常规序列：

```text
首次触发 -> 第 1 轮 -> 第 2 轮 -> 第 3 轮 -> ...
```

单通道连续转换的最小配置和读取结构如下：

```c
hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
hadc1.Init.ContinuousConvMode = ENABLE;

if (HAL_ADC_Start(&hadc1) != HAL_OK)
{
  Error_Handler();
}

while (1)
{
  if (HAL_ADC_PollForConversion(&hadc1, 10U) == HAL_OK)
  {
    uint32_t latest_value = HAL_ADC_GetValue(&hadc1);
    // 及时处理 latest_value
  }
}
```

前两行表示 `MX_ADC1_Init()` 中应具备的初始化配置，通常由 CubeMX 生成。若 ADC 已经初始化，不能只在运行时修改 `hadc1.Init` 字段而不重新执行相应初始化流程。

连续模式会不断用新结果更新 `DR`。程序读到的是读取时刻附近的最新结果，并不代表中间每次转换都被完整处理。多 Rank 扫描时，若仍只偶尔读取同一个 `DR`，前面 Rank 的结果会被后续 Rank 覆盖，应使用 DMA 按顺序搬运。

固定周期采样通常采用另一种组合：关闭连续转换，由定时器每个周期触发一轮。这样采样时刻由定时器决定，不会在两个触发之间自由运行。

## 5. ADC 时钟、采样时间和转换时间

ADC 的速度由 ADC 时钟驱动。采样时间和转换时间都以 ADC 时钟周期为单位，因此计算之前必须先找对 `ADCCLK`。

### 5.1 ADC 时钟来自哪里

STM32F103 的 ADC 时钟通常由 `PCLK2` 再经过 ADC 预分频得到：

$$
f_{ADC}=\frac{f_{PCLK2}}{K_{ADC}}
$$

STM32F103 常见 ADC 预分频值为 `/2`、`/4`、`/6`、`/8`，且 `f_{ADC}` 不应超过 `14 MHz`。

两个典型配置如下：

| 系统配置 | `PCLK2` | ADC 分频 | `ADCCLK` |
| --- | ---: | ---: | ---: |
| 默认 HSI 示例 | `8 MHz` | `/2` | `4 MHz` |
| 常见 72 MHz 配置 | `72 MHz` | `/6` | `12 MHz` |

在 `PCLK2=72 MHz` 时，若错误选择 `/4`，ADC 时钟会达到 `18 MHz`，超过常见 F103 的 `14 MHz` 上限。CubeMX 时钟树出现红色提示时，不应忽略后继续生成工程。

### 5.2 转换阶段为什么是 12.5 个周期

对本文使用的 12 位 STM32F103 ADC，逐次比较阶段的时间为 `12.5` 个 ADC 时钟周期。一次完整转换还要加上通道的采样时间：

$$
T_{CONV}=\frac{T_{SMP,cycles}+12.5}{f_{ADC}}
$$

例如采样时间选择 `7.5` 周期、ADC 时钟为 `4 MHz`：

$$
T_{CONV}=\frac{7.5+12.5}{4\times10^6}
=5\ \mu\mathrm{s}
$$

这里的 `12.5` 周期是转换阶段，而 `20` 周期才是本例从采样开始到结果完成的总周期数。

### 5.3 理论最高转换速率

最短信号采样档位为 `1.5` 周期。若 ADC 可以工作在最大允许时钟 `14 MHz`，理想单通道总时间为：

$$
T_{CONV,min}=\frac{1.5+12.5}{14\ \mathrm{MHz}}
=1\ \mu\mathrm{s}
$$

因此理论最高速率为：

$$
f_{sample,max}=1\ \mathrm{MSPS}
$$

但常见 `72 MHz` 时钟树使用 `/6` 后只能得到 `12 MHz`，相同采样档位下的理论速率为：

$$
\frac{12\ \mathrm{MHz}}{14}\approx857\ \mathrm{kSPS}
$$

实际系统还可能受信号源阻抗、软件读取、DMA、总线访问和模拟性能要求限制，不能只看理论周期数。

## 6. 采样时间该怎么选

ADC 输入端不是阻抗无限大的理想电压表。采样开关闭合后，外部信号源必须在有限时间内给内部采样电容充电。信号源等效内阻越大，充电越慢，需要的采样时间越长。

### 6.1 输入端的等效 RC 电路

采样阶段可以简化为：

```text
理想信号源 -> R_AIN -> R_ADC -> C_ADC
```

- $R_{AIN}$：外部信号源的戴维南等效内阻。
- $R_{ADC}$：ADC 内部采样通路的等效电阻。
- $C_{ADC}$：ADC 内部采样保持电容。

电容电压只能逐渐逼近输入电压。若采样时间太短，电容尚未建立到足够接近输入电压，转换结果会产生额外误差。

### 6.2 采样时间估算公式

若以小于约 `1/4 LSB` 的建立误差为目标，可以使用以下估算式：

$$
t_s\ge (R_{AIN}+R_{ADC})C_{ADC}\ln\left(2^{N+2}\right)
$$

也可以写成：

$$
t_s\ge (R_{AIN}+R_{ADC})C_{ADC}(N+2)\ln 2
$$

对于本教程的 STM32F103 示例，按源素材采用：

$$
R_{ADC}\approx1\ \mathrm{k\Omega},\qquad
C_{ADC}\approx8\ \mathrm{pF},\qquad N=12
$$

这些参数属于具体芯片资料口径。换用其他 STM32 系列或其他型号时，必须查对应数据手册，不应沿用这里的数值。

### 6.3 三个计算示例

假设 $f_{ADC}=14\ \mathrm{MHz}$，把计算得到的时间乘以 ADC 时钟频率，即可得到所需采样周期数：

$$
T_{SMP,cycles}=t_s f_{ADC}
$$

| $R_{AIN}$ | 最小 $t_s$ | 所需周期数 | 应选 STM32F1 档位 |
| ---: | ---: | ---: | ---: |
| $400\ \Omega$ | 约 $0.109\ \mu\mathrm{s}$ | 约 `1.52` 周期 | `7.5` 周期 |
| $10\ \mathrm{k\Omega}$ | 约 $0.854\ \mu\mathrm{s}$ | 约 `11.95` 周期 | `13.5` 周期 |
| $50\ \mathrm{k\Omega}$ | 约 $3.96\ \mu\mathrm{s}$ | 约 `55.43` 周期 | `55.5` 周期 |

STM32F1 常见采样档位为：

```text
1.5, 7.5, 13.5, 28.5, 41.5, 55.5, 71.5, 239.5 cycles
```

选择规则不是“四舍五入到最近档位”，而是：

> 选择大于或等于计算需求的最小档位。

例如需求为 `1.52` 周期时，`1.5` 周期仍略小于要求，所以应选择 `7.5` 周期。若主动选择更短档位，就是用精度余量换速度，不能再声称满足原误差条件。

### 6.4 光敏分压模块的源阻抗

常见光敏模块的模拟输出来自光敏电阻 $R_1$ 和固定电阻 $R_2$ 的分压点。计算 ADC 看到的源内阻时，需要把独立电压源置零，再求输出端的戴维南等效电阻：

$$
R_{AIN}=R_1\parallel R_2
=\frac{R_1R_2}{R_1+R_2}
$$

若固定电阻为 `10 kΩ`，无论光敏电阻怎样变化，并联结果都小于 `10 kΩ`。因此可以用 `10 kΩ` 作为偏保守的上界估算。不过，不同模块的原理图、阻值和输出缓冲方式可能不同，最终仍应以实际模块电路为准。

### 6.5 哪些办法可以改善高阻信号采样

当信号源阻抗很高时，可以采用：

- 增大 ADC 采样时间。
- 在信号源和 ADC 之间加入运算放大器电压跟随器。
- 合理加入输入电容并重新评估带宽、建立时间和稳定性。
- 降低分压电阻，但要同时评估静态功耗。

只在软件中多读几次不能自动消除采样电容建立不足的问题。必须先保证模拟输入在采样窗口内能够稳定。

## 7. 实验一：软件触发单通道转换

本实验使用光敏分压模块输出模拟电压，ADC1 读取 `PA0/ADC1_IN0`，再根据阈值控制一颗外接 LED。

### 7.1 实验目标

```text
光敏模块 AO
  -> PA0 / ADC1_IN0
  -> ADC 原始码
  -> 与阈值码比较
  -> PA9 控制外接 LED
```

很多光敏分压模块的 `AO` 电压会随光照增强而下降，但具体方向取决于分压电阻位置。若实验现象相反，应先测量 `AO`，不要直接交换代码条件来掩盖接线或模块差异。

### 7.2 硬件连接

| 模块或器件 | STM32 连接 |
| --- | --- |
| 光敏模块 `VCC` | 与模块规格匹配的电源，本实验优先使用 `3.3 V` |
| 光敏模块 `GND` | `GND`，与 STM32 共地 |
| 光敏模块 `AO` | `PA0/ADC1_IN0` |
| `PA9` | 限流电阻 -> LED -> `GND` |

外接 LED 必须串联限流电阻，可从约 `330 Ω`～`1 kΩ` 选择适合实验板和亮度的值。不要为了提高亮度去掉限流电阻，否则可能损坏 LED 或 MCU 引脚。

还要确认：

- `AO` 在任何情况下都不能超出目标 ADC 引脚允许的电压范围。
- 模块使用 `5 V` 供电时，`AO` 不一定被限制在 `3.3 V` 以内。
- ADC 模拟输入不能因为“某些数字引脚 5 V 容忍”就直接接入 5 V 模拟电压。

### 7.3 CubeMX 配置

1. 选择目标芯片，例如 `STM32F103C8T6`。
2. 在 `System Core -> SYS` 中保留 `Serial Wire` 调试接口。
3. 启用 `ADC1 -> IN0`，确认引脚为 `PA0`。
4. 将 `PA9` 配置为推挽输出，初始设为低电平。
5. 常规转换数量设为 `1`。
6. `Rank 1` 选择 `Channel 0`。
7. 根据前文计算选择采样时间；本实验可以先用 `13.5 cycles`，为约 `10 kΩ` 上界留足建立时间。若已确认 `ADCCLK=4 MHz`，前述计算只需要约 `3.42` 周期，选择 `7.5 cycles` 也能满足该估算条件；`13.5 cycles` 则能覆盖更高的合法 ADC 时钟。
8. 外部触发源选择 `Software Start`。
9. 关闭扫描和连续转换，数据右对齐。
10. 检查 `Clock Configuration` 中 `ADCCLK` 未超过芯片限制。

CubeMX 版本不同，界面文字可能略有差异。生成代码后，核心初始化参数应接近：

```c
hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
hadc1.Init.ContinuousConvMode = DISABLE;
hadc1.Init.DiscontinuousConvMode = DISABLE;
hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
hadc1.Init.NbrOfConversion = 1;

sConfig.Channel = ADC_CHANNEL_0;
sConfig.Rank = ADC_REGULAR_RANK_1;
sConfig.SamplingTime = ADC_SAMPLETIME_13CYCLES_5;
```

不要把这段代码机械粘贴到 CubeMX 生成区之外；应先让 CubeMX 生成初始化，再核对实际宏名和配置是否一致。

### 7.4 三个核心 HAL 接口

#### `HAL_ADC_Start()`

```c
HAL_StatusTypeDef HAL_ADC_Start(ADC_HandleTypeDef *hadc);
```

它使能 ADC 常规转换流程。当前配置采用软件启动，因此调用后会发起一次常规序列转换。

#### `HAL_ADC_PollForConversion()`

```c
HAL_StatusTypeDef HAL_ADC_PollForConversion(
    ADC_HandleTypeDef *hadc,
    uint32_t Timeout
);
```

它以轮询方式等待转换完成。教学代码也要检查返回值，否则超时后继续读取会把旧值误当作新结果。

#### `HAL_ADC_GetValue()`

```c
uint32_t HAL_ADC_GetValue(ADC_HandleTypeDef *hadc);
```

它读取常规转换数据寄存器 `DR`。虽然 ADC 只有 12 位，HAL 返回类型仍是 `uint32_t`。

### 7.5 启动前先校准

STM32F1 ADC 支持校准。校准用于补偿 ADC 内部转换链路的偏移误差，减少所有测量值整体偏大或偏小的情况；它不能修复参考电压误差、传感器误差或采样时间不足。应在 ADC 初始化完成、第一次转换之前调用：

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
  Error_Handler();
}
```

不要把校准放进 `while (1)` 每次重复执行。它是启动阶段操作，不是每次采样步骤。

### 7.6 最小闭环代码

下面的代码假设：

- `PA9` 外接 LED 为高电平点亮。
- 光敏模块光照增强时，`AO` 电压下降。
- `VREF` 近似为 `3.3 V`。
- 阈值电压取 `1.5 V`。

阈值可先换算成数字码，避免主循环每次做浮点运算：

$$
D_{TH}=\frac{1.5}{3.3}\times4095\approx1861
$$

在 `main()` 初始化完成后、进入主循环之前：

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
  Error_Handler();
}
```

在 `while (1)` 中：

```c
const uint32_t light_threshold = 1861U;

if (HAL_ADC_Start(&hadc1) != HAL_OK)
{
  Error_Handler();
}

if (HAL_ADC_PollForConversion(&hadc1, 10U) == HAL_OK)
{
  uint32_t adc_raw = HAL_ADC_GetValue(&hadc1);

  if (adc_raw < light_threshold)
  {
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_SET);
  }
  else
  {
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_RESET);
  }
}
else
{
  Error_Handler();
}

HAL_Delay(10U);
```

`HAL_Delay(10)` 只用于限制这个演示的刷新频率，不决定 ADC 的硬件采样时间。若 LED 方向或模块输出方向与假设相反，应按实测电路调整条件。

### 7.7 需要显示电压时怎么计算

可以把原始码转换为毫伏整数：

```c
uint32_t adc_mv = (adc_raw * 3300U + 2047U) / 4095U;
```

`+2047U` 用于在整数除法前做近似四舍五入。这里假设参考电压恰好是 `3300 mV`；若需要更准确的电压，必须测量实际 `VDDA/VREF+`，或在适用条件下利用内部参考通道估算供电。

## 8. 实验二：TIM3 TRGO 定时触发 ADC

软件触发适合“程序现在想读一次”的场景。若要每隔 `1 ms` 采样一次，应该让定时器产生稳定触发事件：

```text
TIM3 计数器溢出
  -> Update Event
  -> TIM3 TRGO
  -> ADC1 常规序列外部触发
  -> ADC1_IN0 完成转换
  -> EOC
  -> 主循环读取 DR
```

### 8.1 TRGO 是什么

TRGO 是 Trigger Output，即触发输出。定时器可以把内部事件送给 ADC、DAC 或其他定时器。

把 TIM3 的主模式选择设为 `Update` 后，每次更新事件都会通过 `TRGO` 输出一个触发。对向上计数且正常使用自动重装的定时器，计数器溢出并重装时会产生更新事件。

ADC 也可能支持来自某些定时器通道的 `CCx` 比较事件。本文选择 `TIM3 TRGO`，因为它不需要占用定时器输出引脚，且采样频率直接由基本计数周期决定。

### 8.2 计算 1 kHz 更新频率

定时器更新频率为：

$$
f_{update}=\frac{f_{TIM3}}{(PSC+1)(ARR+1)}
$$

假设默认配置下 `TIM3CLK=8 MHz`，设置：

$$
PSC=7,\qquad ARR=999
$$

则：

$$
f_{update}=\frac{8\ \mathrm{MHz}}{(7+1)(999+1)}
=1\ \mathrm{kHz}
$$

即每 `1 ms` 触发一次 ADC。

若系统时钟改成 `72 MHz`，必须重新确认 `TIM3CLK`。TIM3 挂在 APB1 上；当 APB1 分频不为 1 时，定时器内核时钟通常为 `2 × PCLK1`。例如 `PCLK1=36 MHz` 时，TIM3 常得到 `72 MHz`，不能继续沿用上面的 `PSC=7`。

### 8.3 CubeMX 配置

#### ADC1

1. 启用 `ADC1_IN0/PA0`。
2. 常规转换数量设为 `1`，Rank 1 选择 Channel 0。
3. 根据源阻抗选择采样时间，本实验沿用 `13.5 cycles`。
4. 关闭连续转换。
5. 外部触发源选择 `Timer 3 Trigger Out event`。
6. 选择正确触发边沿；STM32F1 CubeMX/HAL 通常由具体外部触发枚举决定。

#### TIM3

1. 时钟源选择 `Internal Clock`。
2. `Prescaler` 设为 `7`。
3. 向上计数，`Counter Period` 设为 `999`。
4. `Trigger Output (TRGO)` 选择 `Update Event`。

生成代码后，ADC 外部触发和 TIM3 主模式配置应接近：

```c
hadc1.Init.ContinuousConvMode = DISABLE;
hadc1.Init.ExternalTrigConv = ADC_EXTERNALTRIGCONV_T3_TRGO;
hadc1.Init.NbrOfConversion = 1;

sMasterConfig.MasterOutputTrigger = TIM_TRGO_UPDATE;
sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
```

宏名会随 HAL 版本和目标器件略有差异，应以 CubeMX 为当前工程生成的代码为准。

### 8.4 启动顺序

定时器一启动就可能产生更新触发。为了避免 ADC 尚未就绪时丢失第一个有效触发，推荐顺序为：

1. 初始化 ADC 和 TIM3。
2. 校准 ADC。
3. 调用 `HAL_ADC_Start()`，使 ADC 进入等待外部触发的状态。
4. 调用 `HAL_TIM_Base_Start()`，让 TIM3 开始产生 `TRGO`。

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
  Error_Handler();
}

if (HAL_ADC_Start(&hadc1) != HAL_OK)
{
  Error_Handler();
}

if (HAL_TIM_Base_Start(&htim3) != HAL_OK)
{
  Error_Handler();
}
```

外部触发模式下，`HAL_ADC_Start()` 主要负责使能并武装 ADC；真正的每次采样时刻由 TIM3 触发事件决定。它不需要在主循环中每次重复调用。

### 8.5 读取并观察结果

主循环仍使用轮询取得每次定时触发的结果：

```c
static volatile uint32_t adc_raw;
static volatile uint32_t adc_mv;

if (HAL_ADC_PollForConversion(&hadc1, 10U) == HAL_OK)
{
  adc_raw = HAL_ADC_GetValue(&hadc1);
  adc_mv = (adc_raw * 3300U + 2047U) / 4095U;
}
else
{
  Error_Handler();
}
```

可以在调试器的 Watch 窗口观察 `adc_raw` 和 `adc_mv`。单步或断点会改变连续采样时序，因此更适合使用实时变量监视；需要把采样值持续发送到电脑时，参见 [UART 串口教学文档](02%20UART.md)中的连续数值输出与 DMA 发送章节。

若主循环来不及在下一次转换前读取 `DR`，就可能丢失样本或只读到更新后的结果。需要严格保存连续结果时，应使用后文的 ADC DMA 和稳定帧方案。

### 8.6 实际采样频率由谁决定

定时器给出的只是目标触发频率，还必须满足：

$$
T_{trigger}\ge T_{CONV}
$$

本例中若 `ADCCLK=4 MHz`、采样时间为 `13.5` 周期：

$$
T_{CONV}=\frac{13.5+12.5}{4\ \mathrm{MHz}}
=6.5\ \mu\mathrm{s}
$$

它远小于 `1 ms` 触发周期，因此 ADC 有足够时间完成转换。若把触发频率提高到接近 ADC 极限，就必须重新计算总转换时间，并评估读取链路能否跟上。

## 9. 多通道 ADC 为什么需要 DMA

### 9.1 扫描模式不是同时转换

STM32F103 ADC 的常规组只有一套转换核心。扫描模式只是让模拟多路选择器按照 Rank 顺序依次接入不同通道：

```text
一次 TIM3 触发
  -> Rank 1：电位器
  -> Rank 2：NTC
  -> Rank 3：片内温度
  -> Rank 4：Vrefint
  -> 本轮结束
```

四个结果的采样时刻存在先后差异。对于 `1 ms` 一帧的慢变量采集，这个差异通常可以接受；若目标信号变化很快或要求真正同步采样，应选择具有同步 ADC 能力的器件或重新设计采样架构。

### 9.2 多个 Rank 共用一个 DR

常规组每完成一个 Rank，都会把结果写入同一个数据寄存器 `DR`：

```text
Rank 1 完成 -> DR = 电位器结果
Rank 2 完成 -> DR = NTC 结果，覆盖 Rank 1
Rank 3 完成 -> DR = 片内温度结果，覆盖 Rank 2
Rank 4 完成 -> DR = Vrefint 结果，覆盖 Rank 3
```

程序若只在序列结束后调用一次 `HAL_ADC_GetValue()`，通常只能得到最后一个 Rank 的结果。依靠 CPU 在每次转换之间抢读 `DR`，既增加时序耦合，也容易因中断或其他任务漏读。

### 9.3 DMA 保存 Rank 顺序

DMA 可以在每次 `DR` 更新后立即把结果搬到数组：

```text
Rank 1 -> adc_dma_buffer[0]
Rank 2 -> adc_dma_buffer[1]
Rank 3 -> adc_dma_buffer[2]
Rank 4 -> adc_dma_buffer[3]
```

DMA 的主要价值是减少 CPU 逐次搬运，并不提高 ADC 本身的转换速度。数组下标与 Rank 一一对应；只要 CubeMX 的 Rank 顺序不变，程序就能稳定判断每个结果属于哪个通道。

### 9.4 本实验的模式组合

| 配置 | 选择 | 原因 |
| --- | --- | --- |
| 扫描模式 | Enable | 一轮依次执行 4 个 Rank |
| 连续转换 | Disable | 每轮起点由定时器控制 |
| 外部触发 | `TIM3 TRGO` | 获得固定 `1 ms` 帧周期 |
| DMA 模式 | Circular | 连续复用缓冲区，不必每帧重新启动 |

如果同时开启连续转换，第一次 TIM3 触发后 ADC 会自动不断重复整轮序列，后续采样不再保持 `1 ms` 间隔。固定帧率采集应关闭连续转换。

## 10. 四通道采集实验设计

### 10.1 外部接线

电位器接法：

```text
3.3 V ---- 电位器高端
GND   ---- 电位器低端
PA0   ---- 电位器滑动端
```

NTC 采用固定上拉电阻、热敏电阻接地的拓扑：

```text
3.3 V
  |
R_pullup = 10 kΩ
  |
  +------ PA1 / ADC1_IN1
  |
NTC = 10 kΩ, B = 3950 K
  |
 GND
```

所有外部模块必须与 STM32 共地，PA0 和 PA1 电压不得超过 ADC 引脚允许范围。NTC 的标称阻值、Beta 值和精度必须以实际器件规格书为准。

### 10.2 Rank 表

| Rank | HAL 通道 | 来源 | 采样时间示例 | 数组索引 |
| ---: | --- | --- | ---: | --- |
| 1 | `ADC_CHANNEL_0` | `PA0` 电位器 | `13.5 cycles` | `ADC_FRAME_POT` |
| 2 | `ADC_CHANNEL_1` | `PA1` NTC 分压 | `13.5 cycles` | `ADC_FRAME_NTC` |
| 3 | `ADC_CHANNEL_TEMPSENSOR` | 片内温度传感器 | `239.5 cycles` | `ADC_FRAME_TEMPSENSOR` |
| 4 | `ADC_CHANNEL_VREFINT` | 内部参考电压 | `239.5 cycles` | `ADC_FRAME_VREFINT` |

片内温度传感器和 Vrefint 通过 ADC1 访问。内部通道需要较长采样时间（RM0008 建议温度传感器与 Vrefint 使用最大采样档位），不能因为外部低阻通道可以使用较短档位，就把所有 Rank 统一设成最短采样时间。

### 10.3 计算一帧转换时间

12 位 ADC 的单 Rank 总周期为：

$$
T_{rank,cycles}=T_{sample,cycles}+12.5
$$

本实验一帧需要：

$$
T_{frame,cycles}
=2(13.5+12.5)+2(239.5+12.5)
=556
$$

若 `ADCCLK=4 MHz`：

$$
T_{frame}=\frac{556}{4\ \mathrm{MHz}}=139\ \mu\mathrm{s}
$$

它小于前文 TIM3 产生的 `1 ms` 触发周期。增加 Rank、延长采样时间或提高触发频率后，都必须重新检查：

$$
T_{frame}<T_{trigger}
$$

## 11. ADC 场景中的 DMA 配置

### 11.1 STM32F103 的固定请求映射

STM32F103 使用固定 DMA 通道映射，ADC1 通常对应 `DMA1 Channel1`，不能像带有 DMAMUX 的器件那样自由选择请求通道。ADC 完成一次转换后产生 DMA 请求，数据方向为 Peripheral to Memory。

DMA 与 CPU 都要访问内部总线。DMA 可以减少 CPU 指令开销，但仍有总线成本；多个高频 DMA 同时运行时，应根据丢数风险设置优先级。

### 11.2 CubeMX 的 ADC 与 DMA 设置

ADC1 沿用前文 TIM3 TRGO 设置，并修改为：

1. 启用 `ADC1_IN0/PA0`、`ADC1_IN1/PA1`、片内温度和 Vrefint。
2. `Scan Conversion Mode` 设为 Enable。
3. `Continuous Conversion Mode` 设为 Disable。
4. `Number Of Conversion` 设为 `4`。
5. 按 Rank 表设置顺序和采样时间。
6. 数据右对齐，外部触发源选择 `TIM3 Trigger Out`。

DMA1 Channel1 设置为：

| 配置项 | 取值 |
| --- | --- |
| Direction | Peripheral to Memory |
| Peripheral Increment | Disable |
| Memory Increment | Enable |
| Peripheral Data Width | Half Word |
| Memory Data Width | Half Word |
| Mode | Circular |
| Priority | High |

同时使能 DMA1 Channel1 中断，以便使用半传输和传输完成回调。CubeMX 还应生成 DMA 时钟、NVIC 配置，并通过 `__HAL_LINKDMA()` 把 ADC 句柄与 DMA 句柄关联。

### 11.3 宽度、长度和事件

12 位 ADC 结果使用 `uint16_t` 保存，DMA 宽度应为 Half Word。`HAL_ADC_Start_DMA()` 的长度表示传输多少个 Half Word，不是字节数。缓冲区类型、DMA 宽度和长度解释必须保持一致。

ADC 循环采集会用到三个事件：

- HT：前半区已经写完，DMA 正在写后半区。
- TC：后半区已经写完，DMA 回到前半区继续工作。
- TE：DMA 访问或配置发生错误。

Normal 模式搬完指定长度后停止；Circular 模式会回到缓冲区开头继续覆盖旧数据，因此程序必须明确哪些区域已经稳定、哪些区域仍归 DMA 所有。

## 12. 双半区缓冲与稳定数据帧

### 12.1 单帧循环缓冲的竞态

若循环缓冲区只有 4 个元素，DMA 写完 Rank 4 后会立即回到索引 0。主循环读取时，DMA 可能已经开始覆盖下一帧，最终得到跨帧组合。

关闭 CPU 中断不能冻结 DMA。DMA 是独立的总线主设备，即使 CPU 暂时不响应中断，它仍可能继续写内存。因此，不能把“关中断后复制原始 DMA 数组”当作一致性方案。

### 12.2 双半区结构

让 DMA 缓冲区容纳两帧：

```text
adc_dma_buffer[0..3] = 前半区，一帧
adc_dma_buffer[4..7] = 后半区，一帧
```

- 前半区写满时触发 HT，DMA 正在写后半区，前半区稳定。
- 后半区写满时触发 TC，DMA 已回到前半区，后半区稳定。

回调只把稳定半区复制到独立的应用快照，不执行 `logf()`、`snprintf()`、显示刷新或其他耗时操作。

### 12.3 类型、索引和缓冲区

```c
#include <stdbool.h>
#include <math.h>

typedef enum
{
  ADC_FRAME_POT = 0,
  ADC_FRAME_NTC,
  ADC_FRAME_TEMPSENSOR,
  ADC_FRAME_VREFINT,
  ADC_FRAME_CHANNEL_COUNT
} AdcFrameIndex;

#define ADC_DMA_BUFFER_LENGTH (ADC_FRAME_CHANNEL_COUNT * 2U)

static volatile uint16_t adc_dma_buffer[ADC_DMA_BUFFER_LENGTH];
static volatile uint16_t adc_latest_frame[ADC_FRAME_CHANNEL_COUNT];
static volatile uint32_t adc_frame_sequence = 0U;
static volatile uint32_t adc_error_count = 0U;
```

枚举顺序必须与 CubeMX Rank 顺序一致。若以后调整 Rank，只改 CubeMX 而不改枚举，就会把某个通道的结果套进另一个通道的换算公式。

## 13. 稳定数据帧的 HAL 实现

### 13.1 回调发布完整帧

```c
static void ADC_PublishFrame(const volatile uint16_t *source)
{
  for (uint32_t i = 0U; i < ADC_FRAME_CHANNEL_COUNT; i++)
  {
    adc_latest_frame[i] = source[i];
  }

  __DMB();
  adc_frame_sequence++;
}

void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef *hadc)
{
  if (hadc->Instance == ADC1)
  {
    ADC_PublishFrame(&adc_dma_buffer[0]);
  }
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
  if (hadc->Instance == ADC1)
  {
    ADC_PublishFrame(&adc_dma_buffer[ADC_FRAME_CHANNEL_COUNT]);
  }
}

void HAL_ADC_ErrorCallback(ADC_HandleTypeDef *hadc)
{
  if (hadc->Instance == ADC1)
  {
    adc_error_count++;
  }
}
```

`__DMB()` 保证帧数据写入先于序号更新对 CPU 可见。HAL 的弱回调在整个工程中只能保留一份实现；多个 ADC 或模块共存时，应在同一个回调中按 `hadc->Instance` 分发。

### 13.2 主循环取得应用快照

```c
static bool ADC_TryReadFrame(
    uint16_t output[ADC_FRAME_CHANNEL_COUNT],
    uint32_t *last_sequence)
{
  bool has_new_frame = false;
  uint32_t primask = __get_PRIMASK();

  __disable_irq();

  if (adc_frame_sequence != *last_sequence)
  {
    for (uint32_t i = 0U; i < ADC_FRAME_CHANNEL_COUNT; i++)
    {
      output[i] = adc_latest_frame[i];
    }

    *last_sequence = adc_frame_sequence;
    has_new_frame = true;
  }

  __set_PRIMASK(primask);
  return has_new_frame;
}
```

短临界区保护的是回调会修改的应用快照，不是 DMA 原始缓冲区。DMA 仍可继续写另一个半区，但回调不会在主循环复制 `adc_latest_frame` 的中途更新它。

当前结构只保留最新帧。主循环处理速度低于采样帧率时，旧帧会被覆盖；显示温度等只关心最新值的场景通常可以接受。若每一帧都必须保存，应使用更深的帧队列并定义队列满时的策略。

### 13.3 启动顺序和主循环

初始化完成后、进入 `while (1)` 之前：

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
  Error_Handler();
}

if (HAL_ADC_Start_DMA(
        &hadc1,
        (uint32_t *)(void *)adc_dma_buffer,
        ADC_DMA_BUFFER_LENGTH) != HAL_OK)
{
  Error_Handler();
}

if (HAL_TIM_Base_Start(&htim3) != HAL_OK)
{
  Error_Handler();
}
```

顺序是“校准 -> 武装 ADC 和 DMA -> 启动 TIM3”。若先启动 TIM3，ADC 和 DMA 尚未准备好时可能错过第一个触发。

主循环按自己的节奏消费完整帧：

```c
uint16_t frame[ADC_FRAME_CHANNEL_COUNT];
uint32_t last_sequence = 0U;

while (1)
{
  if (ADC_TryReadFrame(frame, &last_sequence))
  {
    uint16_t pot_raw = frame[ADC_FRAME_POT];
    uint16_t ntc_raw = frame[ADC_FRAME_NTC];
    uint16_t die_temp_raw = frame[ADC_FRAME_TEMPSENSOR];
    uint16_t vrefint_raw = frame[ADC_FRAME_VREFINT];

    /* 在这里换算物理量或更新应用状态。 */
  }
}
```

## 14. NTC：从 ADC 码到温度

### 14.1 先确认分压拓扑

本实验采用“固定电阻接 VDDA，NTC 接地”：

$$
V_{OUT}=V_{DDA}\frac{R_{NTC}}{R_{pullup}+R_{NTC}}
$$

结合 12 位 ADC 端点近似：

$$
\frac{D}{4095}\approx\frac{V_{OUT}}{V_{DDA}}
$$

得到：

$$
R_{NTC}=R_{pullup}\frac{D}{4095-D}
$$

若 NTC 接 VDDA、固定电阻接地，则公式变为：

$$
R_{NTC}=R_{pulldown}\frac{4095-D}{D}
$$

必须先确认实际电路拓扑，再选择公式，不能通过交换分子分母试错。

### 14.2 Beta 公式

常见 NTC 可以用 Beta 模型近似：

$$
\frac{1}{T_K}
=\frac{1}{T_0}
+\frac{1}{B}\ln\left(\frac{R_{NTC}}{R_0}\right)
$$

$$
T_C=T_K-273.15
$$

示例使用 `R0=10 kΩ`、`T0=298.15 K`、`B=3950 K`。这些参数必须来自实际 NTC 规格书，不能无条件套用到其他型号。

### 14.3 带端点故障判断的换算函数

```c
typedef enum
{
  NTC_STATUS_OK = 0,
  NTC_STATUS_SHORT_OR_LOW_SATURATION,
  NTC_STATUS_OPEN_OR_HIGH_SATURATION,
  NTC_STATUS_INVALID_ARGUMENT
} NtcStatus;

static NtcStatus NTC_Convert(
    uint16_t adc_raw,
    float *resistance_ohm,
    float *temperature_c)
{
  const float r_pullup = 10000.0f;
  const float r0 = 10000.0f;
  const float beta = 3950.0f;
  const float t0_kelvin = 298.15f;
  float resistance;
  float inverse_temperature;

  if ((resistance_ohm == NULL) || (temperature_c == NULL))
  {
    return NTC_STATUS_INVALID_ARGUMENT;
  }

  if (adc_raw <= 1U)
  {
    return NTC_STATUS_SHORT_OR_LOW_SATURATION;
  }

  if (adc_raw >= 4094U)
  {
    return NTC_STATUS_OPEN_OR_HIGH_SATURATION;
  }

  resistance =
      r_pullup * (float)adc_raw / (4095.0f - (float)adc_raw);

  inverse_temperature =
      (1.0f / t0_kelvin) + (logf(resistance / r0) / beta);

  if (inverse_temperature <= 0.0f)
  {
    return NTC_STATUS_INVALID_ARGUMENT;
  }

  *resistance_ohm = resistance;
  *temperature_c = (1.0f / inverse_temperature) - 273.15f;
  return NTC_STATUS_OK;
}
```

当 ADC 码约为 `2048` 时，示例电路中的 NTC 电阻约为 `10 kΩ`，温度应接近 `25°C`。端点值通常表示短路、断路或饱和，不应直接进入除法和对数运算。浮点换算放在主循环，不放进 DMA 回调。另外，`logf` 属于 C 数学库，工程里要用它就需要链接数学库（Keil 下在 `Options for Target -> C/C++` 的 `Misc Controls` 加 `--use_fp_opt` 或按工具链要求启用浮点/数学库），否则会报链接错误 `logf undefined`。

### 14.4 为什么通常不需要 Vrefint 修正 NTC

当 NTC 分压上端和 ADC 参考都使用同一个 `VDDA` 时，ADC 码测得的是电压比值，`VDDA` 在电阻公式中相消。只有分压电源与 ADC 参考不是同一个源，或者需要输出绝对电压时，才必须单独处理参考电压。

## 15. Vrefint 与片内温度传感器

### 15.1 使用 Vrefint 估算 VDDA

内部参考电压近似固定，而它的 ADC 码会随 `VDDA` 变化：

$$
V_{DDA}\approx\frac{V_{REFINT}\times4095}{D_{VREFINT}}
$$

```c
static bool ADC_EstimateVddaMv(
    uint16_t vrefint_raw,
    uint32_t calibrated_vrefint_mv,
    uint32_t *vdda_mv)
{
  if ((vrefint_raw == 0U) ||
      (calibrated_vrefint_mv == 0U) ||
      (vdda_mv == NULL))
  {
    return false;
  }

  *vdda_mv =
      (calibrated_vrefint_mv * 4095U + (vrefint_raw / 2U)) /
      vrefint_raw;
  return true;
}
```

当前 STM32F1 CMSIS/HAL 不提供其他一些 STM32 系列常见的标准 `VREFINT_CAL` 工厂常量接口，不能从别的系列复制校准地址。`calibrated_vrefint_mv` 应来自板级标定；只使用数据手册典型值时，结果只能作为粗略估算。

### 15.2 片内温度传感器的边界

片内温度传感器测量的是 MCU 芯片结温附近的变化，不是环境空气温度。常见近似关系为：

$$
T\approx\frac{V_{25}-V_{SENSE}}{Avg\_Slope}+25
$$

其中 $V_{25}$ 和 $Avg\_Slope$ 应查目标芯片数据手册。它们通常是典型参数，不代表每颗芯片都经过单独高精度标定。从 ADC 码计算 $V_{SENSE}$ 时，还需要先估算或测量实际 `VDDA`。

本实验保留片内温度通道，是为了演示 ADC1 内部通道、不同 Rank 使用不同采样时间，以及它与外部 NTC 的趋势对照，而不是把芯片结温当作环境温度标准。

## 16. 常见问题排查

### 16.1 ADC 原始码总是 0

依次检查：

1. 传感器是否供电、是否与 STM32 共地。
2. `AO` 是否真正连接到 `PA0/ADC1_IN0`，而不是数字输出 `DO`。
3. PA0 是否配置成 ADC 模拟输入。
4. 常规序列 Rank 1 是否选择 Channel 0。
5. 是否调用 `HAL_ADC_Start()`。
6. `HAL_ADC_PollForConversion()` 是否返回 `HAL_OK`。

### 16.2 结果总是接近 4095

- 用万用表测量 `AO` 是否真的接近参考电压。
- 检查模块是否使用 5 V 供电并输出超过 ADC 允许范围的电压。
- 检查是否接错到 `VCC` 或信号线悬空。
- 立即排除过压条件，不要只在软件中把 `4095` 当作正常饱和处理。

### 16.3 数值明显抖动

- 电源和参考电压是否稳定。
- 模拟地与数字回流是否合理，共地是否可靠。
- 信号源阻抗是否过高，采样时间是否太短。
- 连接线是否过长，旁边是否有 PWM、时钟或电机等干扰源。
- 传感器本身是否有噪声。

平均滤波可以降低随机波动，但不能修复过压、错误接线、参考电压漂移或采样建立不足。

### 16.4 电压换算不准

- 代码中的 `3300 mV` 是否等于实测参考电压。
- 传感器输出是否超出 ADC 输入范围。
- 是否把 12 位原始码错误地除以 `1023` 或 `65535`。
- ADC 是否完成校准。
- 测量误差是否已经超过 ADC、参考源或万用表本身的精度。

### 16.5 软件触发可以，定时器触发没有数据

- ADC 外部触发源是否确实选择 `TIM3 TRGO`。
- TIM3 的 TRGO 是否选择 `Update Event`。
- 是否调用 `HAL_ADC_Start()` 武装 ADC。
- 是否调用 `HAL_TIM_Base_Start()` 启动 TIM3。
- `PSC`、`ARR` 是否按实际 `TIM3CLK` 计算。
- `HAL_ADC_PollForConversion()` 是否超时。

### 16.6 采样频率不对

不要只看 `SYSCLK`。应沿时钟链检查：

```text
时钟源
  -> SYSCLK
  -> AHB / HCLK
  -> APB1 / PCLK1
  -> TIM3CLK 倍频规则
  -> PSC
  -> ARR
  -> TRGO 更新频率
```

ADC 转换速度则沿另一条链检查：

```text
PCLK2
  -> ADC 预分频
  -> ADCCLK
  -> 采样周期 + 12.5 周期
  -> 单次转换时间
```

### 16.7 多通道数组值与 Rank 对不上

- 检查 CubeMX Rank 顺序和 `AdcFrameIndex` 枚举顺序。
- 检查 DMA 内存自增是否使能。
- 检查 DMA 外设和内存宽度是否都为 Half Word。
- 不要根据数值大小猜通道归属。

### 16.8 DMA 回调不执行或只有第一帧

- 是否调用 `HAL_ADC_Start_DMA()`，并检查其返回值。
- ADC1 是否链接到 DMA1 Channel1。
- DMA1 Channel1 NVIC 和 HT/TC 中断是否使能。
- DMA 是否误设为 Normal。
- TIM3 是否启动并持续产生 TRGO。
- 是否在回调中错误停止 ADC 或 DMA。

### 16.9 多个通道偶尔不属于同一帧

不要让主循环直接读取正在循环改写的原始 DMA 数组。缓冲区必须至少包含两个完整帧，并且只在 HT/TC 回调中复制 DMA 已经离开的稳定半区。

`volatile` 只能防止编译器省略访问，不能阻止 DMA 覆盖数组，也不能保证多个字段来自同一帧。

### 16.10 NTC 温度方向或数值异常

- 确认 NTC 在分压上方还是下方，代码公式必须与接线一致。
- 检查上拉或下拉电阻的实际阻值。
- 核对 $R_0$、$B$ 和 $T_0$ 是否属于当前器件。
- 对 `ADC=0`、`ADC=4095` 及附近饱和值先做故障判断。
- 确认 `logf()` 参数为正，并检查工程的数学库配置。

### 16.11 内部通道不稳定或主循环丢帧

- 温度传感器和 Vrefint 是否配置在 ADC1，并使用足够长的采样时间。
- ADC 是否在第一次采集前完成校准。
- 比较 `adc_frame_sequence` 的差值，确认主循环是否低于发布帧率。
- 不要每帧做大量格式化、阻塞发送或整屏刷新。
- 只关心最新值时可以覆盖旧帧；必须保存每一帧时应增加队列，并定义溢出策略。

## 17. 一页速记

### 17.1 核心概念

- ADC 把模拟电压转换成数字码。
- 12 位 ADC 有 4096 个量化码：`0`～`4095`。
- 理想 1 LSB 约为 $V_{REF}/4096$。
- 逐次逼近过程从最高位到最低位依次试探。
- 采样保持电路先取得电压，再让 SAR 在相对稳定的电压上完成比较。

### 17.2 STM32 模块结构

- Channel 决定“测哪一路”。
- Rank 决定“第几个测”。
- Sampling Time 决定“采样开关闭合多久”。
- 常规序列结果在 `DR`，注入序列结果在 `JDRx`。
- 软件触发适合按需测量，定时器触发适合固定采样间隔。
- 多 Rank 共用一个 `DR`，连续保存结果通常需要 DMA。
- ADC1 在 STM32F103 上固定映射到 DMA1 Channel1。

### 17.3 核心公式

完整转换时间：

$$
T_{CONV}=\frac{T_{SMP,cycles}+12.5}{f_{ADC}}
$$

采样时间估算：

$$
t_s\ge (R_{AIN}+R_{ADC})C_{ADC}(N+2)\ln 2
$$

采样档位要向上选择满足要求的最小值。

固定上拉、NTC 接地时：

$$
R_{NTC}=R_{pullup}\frac{D}{4095-D}
$$

### 17.4 HAL 调用链

软件触发：

```text
校准一次
  -> HAL_ADC_Start
  -> HAL_ADC_PollForConversion
  -> HAL_ADC_GetValue
```

TIM3 外部触发：

```text
校准一次
  -> HAL_ADC_Start
  -> HAL_TIM_Base_Start
  -> 循环 Poll
  -> GetValue
```

多通道循环 DMA：

```text
校准一次
  -> HAL_ADC_Start_DMA
  -> HAL_TIM_Base_Start
  -> HT/TC 发布稳定半区
  -> 主循环取得应用快照
  -> 物理量换算
```

## 18. 自测题

1. 12 位 ADC 为什么输出范围是 `0`～`4095`，却有 4096 个可能值？
2. 采样和量化分别让信号的哪个维度离散化？
3. 为什么 SAR 转换开始前需要采样保持电路？
4. Channel、Rank 和 Sampling Time 分别控制什么？
5. `PCLK2=72 MHz` 时，为什么 ADC 预分频 `/4` 通常不合适？
6. 采样时间需求为 `11.95` 周期时，为什么应选 `13.5` 而不是 `7.5` 周期？
7. `ADCCLK=4 MHz`、采样时间为 `13.5` 周期时，完成一次转换需要多长时间？
8. 软件触发单通道转换需要依次调用哪三个 HAL 接口？
9. 使用 TIM3 TRGO 触发 ADC 时，为什么通常先启动 ADC，再启动 TIM3？
10. 为什么多 Rank 序列结束后只读一次 `DR` 无法得到所有通道？
11. 为什么固定周期扫描要关闭连续转换模式？
12. ADC DMA 配置为 Half Word、长度为 8 时，一共写入多少字节？
13. 为什么关闭 CPU 中断不能冻结 `adc_dma_buffer`？
14. HT 回调执行时，DMA 缓冲区的哪一半是稳定的？
15. Rank 顺序改变后，代码中的哪一处也必须同步改变？
16. 为什么示例 NTC 分压通常不需要先用 Vrefint 修正？
17. 固定上拉、NTC 接地时，升温通常会让 ADC 码怎样变化？
18. 为什么片内温度传感器不能直接当作环境温度计？

### 18.1 参考答案

1. 12 个二进制位有 $2^{12}=4096$ 种组合，最小值为 0，最大值为 4095。
2. 采样让时间离散化，量化让幅值离散化。
3. SAR 要连续比较多次；保持电路让这些比较尽量针对同一个瞬时输入电压。
4. Channel 选择输入，Rank 决定序列顺序，Sampling Time 决定采样阶段持续的 ADC 周期数。
5. `/4` 会得到 `18 MHz`，超过 STM32F103 ADC 常见的 `14 MHz` 上限；通常至少使用 `/6` 得到 `12 MHz`。
6. 采样档位必须不小于计算需求，`7.5 < 11.95`，只有 `13.5` 能满足条件。
7. $(13.5+12.5)/4\ \mathrm{MHz}=6.5\ \mu\mathrm{s}$。
8. `HAL_ADC_Start()`、`HAL_ADC_PollForConversion()`、`HAL_ADC_GetValue()`。
9. 先让 ADC 进入等待外部触发状态，可以减少启动 TIM3 后第一个触发丢失的风险。
10. 各 Rank 共用 `DR`，后一个结果会覆盖前一个；DMA 应在每次转换完成时搬走结果。
11. 连续转换开启后，一次触发会让 ADC 自动重复序列，后续帧起点不再由 TIM3 控制。
12. 8 个 Half Word 共 `8 × 2=16` 字节。
13. DMA 是独立总线主设备，屏蔽 CPU 中断只会阻止 ISR 执行，不会停止 DMA 写内存。
14. 前半区稳定，DMA 正在写后半区。
15. `AdcFrameIndex` 枚举以及所有按该索引解释数据的代码。
16. 分压电源和 ADC 参考同为 `VDDA`，计算电阻比值时 `VDDA` 相消。
17. NTC 电阻随温度升高而减小，该拓扑下分压和 ADC 码通常一起降低。
18. 它测量的是芯片结温附近变化，且参数通常为典型值，不代表环境温度或逐颗高精度标定结果。
