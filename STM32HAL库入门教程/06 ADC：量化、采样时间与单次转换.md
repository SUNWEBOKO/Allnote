# 06 ADC：量化、采样时间与单次转换

## 本章问题

<<<<<<< Updated upstream
ADC 读数怎样受参考电压、采样时间和转换模式影响，并转换成一个可解释的物理量？

本章前五章主要处理数字量：引脚处于高、低电平，定时器处于计数或停止状态。电位器、光照、电池电压和传感器输出则通常连续变化。ADC（Analog-to-Digital Converter）负责在指定时刻对模拟电压采样，并将其映射为有限位数的数字码。本章集中讨论三个直接影响读数的因素：

- **参考电压**：决定满量程对应的输入电压；
- **采样时间**：决定采样电容能否充分充电；
- **转换模式**：决定每次触发获得一个通道还是一组通道的结果。本章先完整实现“单次、非扫描”采集。
=======
模拟电压怎样变成芯片里的一个数？做这件事的是 ADC。读数准不准，取决于参考电压、采样时间和转换模式。本章用一只电位器走完“采样 → 量化 → 显示”的完整链路。
>>>>>>> Stashed changes

## 学习目标

- 换算 12 位 ADC 原码对应的输入电压。
- 按 ADC 时钟和信号源内阻选择采样档位。
<<<<<<< Updated upstream
- 用"单次 + 非扫描"完成一个通道的轮询采集。

## 0. 本章实验与工程

本章对应 `E:\ProjectStm\Courses\HAL06_ADC` 下的 `01_Basic` 工程，基线一致：STM32F103C8T6、CubeMX 6.17.0、FW_F1 V1.8.7、HSE+PLL 72 MHz、ADC 预分频 `/6`，对应第 6 节的实验。

ADC 的多通道扫描 + DMA 采集是另一条主线，完整实做在 [[07 DMA：数据搬运与 ADC 多通道采集]]；定时器触发的定时采样也放在那一章展开（届时会用到 `03_TimerTrigger` 工程）。
=======
- 用单次、非扫描模式完成一个通道的采集。
- 分层定位 ADC 读数异常。
>>>>>>> Stashed changes

## 1. ADC 的工作

<<<<<<< Updated upstream
GPIO、串口和定时器处理的是数字量；电位器、分压电路、电池电压和传感器输出通常是连续变化的模拟量。ADC（Analog-to-Digital Converter）在某一时刻把模拟电压映射为有限位数的数字码：
=======
ADC 在指定时刻把模拟电压映射成有限位数的数字码。12 位 ADC 只有 4096 个格子，两个相差不到一格电压的输入会得到同一个结果。
>>>>>>> Stashed changes

STM32F1 的 ADC 采用逐次逼近结构，一次转换分四步：

<<<<<<< Updated upstream
用一把最小刻度只有 1 cm 的尺子给人量身高，结果只能是 172、173 这样的整数厘米——比 172 高一点点也只能记 172。ADC 做的是同一件事：

- **尺子的量程**是参考电压 $V_{REF}$（本章为 3.3 V）；
- **尺子的最小刻度**是 1 LSB（本章约 0.8 mV，见 2.1 节）；读出来的数（原码）永远是整数，两个相邻整数之间的电压细节全部丢失。

所以 ADC 世界里没有"精确的 1.6500 V"，只有"落在哪个刻度格里"。理解了这一点，后面讲分辨率、对齐、量化误差就都不抽象了。

### 1.2 一次转换的两个阶段

STM32F1 的 ADC 采用 SAR（Successive Approximation Register，逐次逼近寄存器）结构。一次转换包含两个阶段：

1. **采样保持**：采样开关给内部采样电容充电，随后断开输入，暂时保持该电压；
2. **逐次逼近转换**：从最高位开始依次试探，保留不超过输入的位，最终得到 12 位二进制原码。

采样保持相当于"拍快照"：先把此刻的电压复制到电容上存住，接下来转换期间即使输入变了也不影响结果。逐次逼近则像用天平称重：先放最重的砝码（对应最高位），重了就取下来、轻了就留着，再试下一级砝码，12 个砝码试完，天平上的组合就是 12 位原码。

分辨率越高，比较次数越多；信号源内阻越大，采样电容充电越慢。后续选择 ADC 时钟和采样时间时，这两点都必须考虑。

### 1.3 信号链全景
=======
1. 采样开关闭合，外部电压给采样电容充电；
2. 开关断开，电容上的电压被保持；
3. SAR 从最高位开始，逐位与保持电压比较，定出 12 位结果；
4. 结果写入数据寄存器 `DR`，由 CPU 或 DMA 取走。
>>>>>>> Stashed changes

```text
外部输入 → 采样保持 → 逐次逼近 → DR → CPU/DMA → 换算 → 显示或控制
```

<<<<<<< Updated upstream
本章后面的每个实验都按这条链展开，第 8 节按链路排查故障。

## 2. 分辨率、参考电压与输入边界
=======
## 2. 分辨率、参考电压与输入范围
>>>>>>> Stashed changes

### 2.1 原码与电压

<<<<<<< Updated upstream
先解决"12 位 = 4096 级是怎么来的"。一个 12 位二进制数有 12 个数位，每位只能取 0 或 1，从全 0（`0b000000000000`）数到全 1（`0b111111111111`），共有 $2^{12}$ 种组合。这就是量化的本质：把 0 到 $V_{REF}$ 之间的连续电压，映射到这 4096 个整数格子上。`N` 位 ADC 就有 $2^N$ 个编码。本章使用 STM32F103 的 12 位 ADC：

$$2^{12}=4096,\qquad ADC\_Code=0\sim4095$$

再看参考电压。ADC 输出的原码本身只是一个"比例"：它不知道也不关心输入的绝对电压，只知道输入是满量程的百分之几。满量程的位置由参考电压 $V_{REF}$ 定义——就像尺子上必须先刻好"100 cm"这条线，后面的刻度才有意义。让原码 `4095` 对应参考电压，常用换算式为：

$$V_{in}\approx\frac{ADC\_Code}{2^N-1}V_{REF}$$

当 $N=12$、$V_{REF}=3.3\,\text{V}$ 时：

$$V_{in}\approx\frac{ADC\_Code}{4095}\times3.3\,\text{V}$$

例如原码为 `2048`：

$$V_{in}\approx\frac{2048}{4095}\times3.3\,\text{V}\approx1.6504\,\text{V}$$

相邻码的电压间隔通常称为 1 LSB，可按 $V_{REF}/2^N$ 定义；本文的满量程换算使用 $V_{REF}/(2^N-1)$。两种定义都必须统一使用，不能在同一公式中混写。对 `3.3 V`、12 位 ADC，两者都约为：

$$1\,LSB\approx0.806\,\text{mV}$$

给一个直观感受：0.8 mV 约为一节 1.5 V 干电池电压的两千分之一，做电位器、测温这类实验完全够用；但这也是量化精度的天花板——两个相差不到 0.8 mV 的电压，ADC 分不出来。另外，参考电压取值直接决定读数准不准：本章把 $V_{REF}$ 取为 3.3 V，等于假设 VDDA 模拟供电准确且稳定；如果实际供电是 3.25 V，所有读数都会整体偏大约 1.5%。第 7 章 10.3 节会用片内基准反过来估计实际 VDDA。
=======
12 位 ADC 的输出范围是 `0~4095`。原码只是比例，满量程对应参考电压 $V_{REF}$：

$$
V_{in}\approx\frac{\mathrm{ADC\_Code}}{4095}V_{REF}
$$

$V_{REF}=3.3$ V、原码 2048 时：

$$
V_{in}\approx\frac{2048}{4095}\times3.3\approx1.6504\ \mathrm{V}
$$

一个码对应的电压约为：

$$
1\,LSB\approx\frac{3.3}{4096}\approx0.806\ \mathrm{mV}
$$

参考电压必须准确稳定。若实际 VDDA 只有 3.25 V，所有读数会整体偏大约 1.5%。
>>>>>>> Stashed changes

### 2.2 数据对齐

12 位结果放进 16 位寄存器有两种摆法：

- 右对齐：高 4 位补 0，读数是 `0~4095`；
- 左对齐：结果左移 4 位，读数是原码的 16 倍。

<<<<<<< Updated upstream
可以把 16 位寄存器想成 16 格的抽屉，12 位结果只有 12 格的东西：靠右放（右对齐），前面空 4 格，读出来的数就是原码本身；靠左放（左对齐），读出来的数相当于整体放大了 $2^4=16$ 倍。

HAL 配置分别为 `ADC_DATAALIGN_RIGHT` 和 `ADC_DATAALIGN_LEFT`。本章实验统一使用右对齐；使用左对齐时必须先右移 4 位，不能直接套用 `0~4095`。
=======
本章统一用右对齐（`ADC_DATAALIGN_RIGHT`）。若用了左对齐，读回后要右移 4 位，否则数值会大 16 倍。

### 2.3 输入范围
>>>>>>> Stashed changes

ADC 输入必须落在 `VSSA~VDDA` 之间。超过 VDDA 时，采样电容只能充到 VDDA，原码停在 4095，读数失去意义，还可能损坏引脚。不要把 5 V 信号直接接进 F103 的模拟引脚。

<<<<<<< Updated upstream
ADC 输入必须位于芯片规定的模拟范围 `VSSA~VDDA` 内，并满足引脚绝对最大额定值。输入高于 `VDDA` 可能导致读数饱和，也可能增加损坏风险；普通 ADC 通道不能直接输入负电压。外部电路与开发板必须共地。

为什么超范围会"饱和"？采样电容是个杯子，水位最高只能到杯口（VDDA）：输入 4 V 时杯子照样只装到 3.3 V 对应的水位，原码顶在 `4095` 不再上升——读数失去意义，还可能损伤引脚。

ADC 引脚应配置为 `GPIO_MODE_ANALOG`，以关闭数字输入路径并降低干扰和功耗。不要把 `5 V` 信号直接送入只允许 `3.3 V` 模拟输入的 STM32F103 引脚。
=======
ADC 引脚要配成 `GPIO_MODE_ANALOG`，关闭数字输入通路，减少干扰和功耗。常见的模拟输入接法有三种：

![模拟输入的常见接法](image/adc-input-circuits.png)

电位器滑动端直接输出可调电压；NTC 与固定电阻分压测温度；5 V 信号则要先用电阻分压到 3.3 V，例如 17 kΩ 与 33 kΩ 分压得到 $5\times33/(17+33)=3.3$ V。
>>>>>>> Stashed changes

## 3. 通道与 ADC 时钟

<<<<<<< Updated upstream
### 3.1 外部通道和内部通道

芯片内部只有一个 ADC 转换核心，但引脚有很多个可能要测的信号，所以通道的本质是一个**模拟多路开关**：像一台万用表轮流碰不同的测试点，每次只把一个引脚接到转换核心上。共用一个核心能省成本，代价是同一时刻只能测一路，多路必须排队（第 5、7 节）。

STM32F103C8T6 常用外部通道映射如下；实际可用引脚还要以目标封装原理图为准。
=======
### 3.1 外部通道

STM32F103C8T6 有 ADC1 和 ADC2，每个 ADC 同一时刻只转换一路。常用通道映射：
>>>>>>> Stashed changes

| 通道 | 引脚 | 通道 | 引脚 |
| --- | --- | --- | --- |
| `ADC_CHANNEL_0` | PA0 | `ADC_CHANNEL_5` | PA5 |
| `ADC_CHANNEL_1` | PA1 | `ADC_CHANNEL_6` | PA6 |
| `ADC_CHANNEL_2` | PA2 | `ADC_CHANNEL_7` | PA7 |
| `ADC_CHANNEL_3` | PA3 | `ADC_CHANNEL_8` | PB0 |
| `ADC_CHANNEL_4` | PA4 | `ADC_CHANNEL_9` | PB1 |

<<<<<<< Updated upstream
通道号与引脚由芯片硬件决定，不能互换。片内温度传感器 `ADC_CHANNEL_16` 和参考电压通道 `ADC_CHANNEL_VREFINT`（Channel 17）不占外部引脚，并且只连接在 `ADC1` 上，不能配置到 `ADC2`。
=======
通道号与引脚由硬件绑定，不能互换。C8T6 的 LQFP48 封装只引出这 10 个外部通道。片内温度传感器（通道 16）和参考电压 `VREFINT`（通道 17）不占引脚，且只接在 ADC1 上。

![ADC 通道与引脚完整对应关系](image/adc-channel-map.png)

多通道扫描时，切换通道后采样电容里还残留着上一路的电荷，必须重新充满。通道数越多、源阻抗越大，一轮扫描的时间越紧。
>>>>>>> Stashed changes

### 3.2 ADC 时钟

ADC 时钟由 `PCLK2` 经专用预分频器得到：

<<<<<<< Updated upstream
$$f_{ADC}=\frac{PCLK2}{ADC\_Prescaler}$$
=======
$$
f_{ADC}=\frac{\mathrm{PCLK2}}{\mathrm{ADC\_Prescaler}}
$$
>>>>>>> Stashed changes

F103 的 ADC 时钟上限是 14 MHz。`PCLK2=72 MHz` 时：

| 预分频 | $f_{ADC}$ | 是否可用 |
| --- | ---: | --- |
| /2 | 36 MHz | 否 |
| /4 | 18 MHz | 否 |
| /6 | 12 MHz | 是 |
| /8 | 9 MHz | 是 |

<<<<<<< Updated upstream
本章统一选择 `/6`，即 $f_{ADC}=12\,\text{MHz}$。STM32F1 的 ADC 分频属于 RCC 外设时钟配置，不是在 `ADC_InitTypeDef` 中设置。三个 HAL06 工程的 `SystemClock_Config()` 末尾都有这段配置（代码事实）：
=======
本章选 `/6`，得到 12 MHz。STM32F1 的 ADC 分频属于 RCC 配置，不在 `ADC_InitTypeDef` 里，而在 `SystemClock_Config()` 末尾：
>>>>>>> Stashed changes

```c
PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_ADC;
PeriphClkInit.AdcClockSelection = RCC_ADCPCLK2_DIV6;
if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
{
  Error_Handler();
}
```

<<<<<<< Updated upstream
配套工程核对：三个 HAL06 工程的 `.ioc` 中都记录了 `RCC.ADCFreq_Value=12000000`（时钟树显示 12 MHz），但早期生成的 `SystemClock_Config()` 里并没有上面这段代码——图纸写了 12 MHz，代码却让 ADC 按复位默认值吃 PCLK2/2 = 36 MHz，超出 14 MHz 上限。这是配套工程里真实出现过的问题，后来已修复：`SystemClock_Config()` 末尾补上了 `HAL_RCCEx_PeriphCLKConfig()`，`.ioc` 补了 `RCC.ADCPRE=RCC_ADCPCLK2_DIV6`（第 7 章 `02_ADC_Scan` 工程同样存在并已一并修复），修复后各工程编译通过。它留下的教训是：**时钟树上的数字只是图纸，必须核对生成代码里真的有对应配置**。复刻时用第 7 章的方式确认 $f_{ADC}$，而分频档直接进 4.1 节的转换时间计算。
=======
这段代码经常缺失。`.ioc` 和时钟树都显示 12 MHz，生成代码里却没有对应配置，ADC 就仍按复位默认的 `/2` 跑在 36 MHz，超出上限。直接核对两处：`.ioc` 里有没有 `RCC.ADCPresc=RCC_ADCPCLK2_DIV6`，`SystemClock_Config()` 末尾有没有 `HAL_RCCEx_PeriphCLKConfig()`。

## 4. 采样时间

### 4.1 转换时间
>>>>>>> Stashed changes

一次转换由采样窗口和逐次逼近两段组成：

<<<<<<< Updated upstream
### 4.1 一次转换需要多少时间

STM32F1 的 12 位 ADC 在 SAR 阶段通常需要 `12.5` 个 ADC 周期，因此一次转换可按下式估算：

$$T_{total}=\left(T_{sample}+12.5\right)T_{ADC}=\frac{T_{sample}+12.5}{f_{ADC}}$$

其中 $T_{sample}$ 以 ADC 周期计。12.5 这个数是 SAR 逐位逼近 12 次加上固定开销的结果，每颗 ADC 都要把这一步做完才算出一个码。STM32F1 常见采样档位为：
=======
$$
T_{\mathrm{total}}=\frac{T_{\mathrm{sample}}+12.5}{f_{ADC}}
$$

12.5 个周期来自 12 位比较和半拍固定开销。可选采样档位是：
>>>>>>> Stashed changes

```text
1.5、7.5、13.5、28.5、41.5、55.5、71.5、239.5 个 ADC 周期
```

<<<<<<< Updated upstream
例如 $f_{ADC}=14\,\text{MHz}$、采样时间为 `1.5` 周期：

$$T_{total}=\frac{1.5+12.5}{14\,\text{MHz}}=1\,\mu\text{s}$$

这是忽略触发、DMA、总线和软件开销的理论上限，不是整机保证能达到的采样率。

### 4.2 源阻抗决定采样档位

为什么采样时间可以调？回到 1.2 节的"拍快照"：快照拍在采样电容上，而充电需要时间。把采样开关想成水龙头，采样电容想成杯子，信号源内阻想成水管的粗细：

- 水管粗（源阻抗小）：杯子很快灌到目标水位，龙头开一小会儿（短采样档位）就够；
- 水管细（源阻抗大，比如电位器本身有 10 kΩ）：水流慢，龙头必须开足够久；
- **龙头开得太短**（采样档位选太小）：开关断开那一刻杯子还没灌满，SAR 拿着一个"偏低的水位"去转换——读数系统性偏低，而且源阻抗或温度稍有变化读数就跳。

把信号源内阻 $R_S$、ADC 等效采样电阻 $R_{ADC}$ 和采样电容 $C_{ADC}$ 组成一阶 RC 模型：

$$V_C(t)=V_{in}\left(1-e^{-t/[(R_S+R_{ADC})C_{ADC}]}\right)$$

时间常数为：

$$\tau=(R_S+R_{ADC})C_{ADC}$$

若要求采样残余误差小于约四分之一 LSB，12 位 ADC 可使用下面的保守判据：
=======
例如 14 MHz、采样 1.5 周期时，一次转换约 1 µs。这是理论值，不包含触发、总线和软件开销。

### 4.2 采样窗口与源阻抗

采样窗口是采样开关闭合的时间，电容在这段时间里充电。窗口太短，电容没充满，读数会偏低。

![采样保持的一阶 RC 等效电路](image/adc-sample-hold-rc.png)

充电按指数规律进行：

$$
V_C(t)=V_{in}\left(1-e^{-t/\tau}\right),\qquad \tau=(R_S+R_{ADC})C_{ADC}
$$

![采样电容充电曲线](image/adc-sample-charge-curve.png)

要让残余误差小于约四分之一 LSB，采样时间至少取 $9.7\tau$。以 $R_{ADC}\le1$ kΩ、$C_{ADC}\approx8$ pF、源阻抗 10 kΩ 为例：

$$
\tau=(10+1)\,\mathrm{k}\Omega\times8\,\mathrm{pF}\approx88\ \mathrm{ns}
$$
>>>>>>> Stashed changes

$$
t\ge9.7\times88\ \mathrm{ns}\approx0.85\ \mu\mathrm{s}
$$

12 MHz 下约 10.3 个周期，所以最短应选 13.5 档。实验用 55.5 档，采样时间约 4.6 µs，约为时间常数的 52 倍，对常见 10 kΩ 电位器余量充足。

### 4.3 档位怎么选

<<<<<<< Updated upstream
$$t\geq9.7\times88\,\text{ns}\approx0.85\,\mu\text{s}$$

在 $f_{ADC}=12\,\text{MHz}$ 时约为 `10.3` 个周期，因此理论最短应选 `13.5` 档。实验使用 `55.5` 档，采样时间约为：

$$\frac{55.5}{12\,\text{MHz}}\approx4.6\,\mu\text{s}$$

它约为上述时间常数的 `52` 倍，对常见 `10 kΩ` 电位器留有较大裕量。

采样档位不是越长越好，也不是越短越好：

- 低阻抗缓冲输出可使用较短档位提高吞吐率；
- 电位器、NTC 和电阻分压通常应使用较长档位；
- 内部温度传感器和 VREFINT 必须满足各自最小采样时间（下限数值见第 7 章 10.3 节）；
- 结果系统性偏低、跳动或通道切换后突变时，应先检查源阻抗，再增加采样时间或增加电压跟随器。

例如把信号源内阻增至 `100 kΩ`，时间常数约为 `808 ns`。`55.5` 档只有约 `5.7τ`，残余误差约为 `0.33%`，折合约 `13 LSB`；此时应使用 `239.5` 档或增加缓冲器。上述计算只是一阶估算，最终仍要结合目标芯片数据手册、外部电容和通道切换后的稳定时间验证。

"增加电压跟随器"值得多说一句：运放接成跟随器（输出直接接反相输入）后，输出阻抗极小，相当于在信号源和 ADC 之间加了一个"就近蓄水池"——信号源只需慢悠悠地给蓄水池补水，而采样电容充电瞬间由蓄水池高速供水。源阻抗大又想跑快采样率时，这是标准解法。给初学者的选档口诀：**分压/传感器输入，从 `55.5` 档起步；内部通道按第 7 章 10.3 节的下限选；读数偏低再加大档位；追求吞吐率才去压缩档位。**
=======
| 信号源 | 源阻抗 | 建议档位 | 理由 |
| --- | --- | --- | --- |
| 运放缓冲输出 | 很低 | 1.5~7.5 | 电容瞬间充满，可提高吞吐率 |
| 电位器、NTC、电阻分压 | 1 kΩ~100 kΩ | 55.5 起步 | 10 kΩ 下约有 52τ 余量 |
| 内部温度、VREFINT | 片内 | 按数据手册 | 各有最小采样时间 |

源阻抗 100 kΩ 时，55.5 档只剩约 5.7τ，误差折合约 13 LSB，应改用 239.5 档，或在信号源后加电压跟随器。跟随器输出阻抗极低，相当于在 ADC 前放了一个蓄水池，源阻抗大又想跑高采样率时常用。

读数系统性偏低、无故跳动或切换通道后突变，先查源阻抗，再加大采样时间或加缓冲。

## 5. 转换模式与校准
>>>>>>> Stashed changes

扫描、连续、触发和 Rank 的关系可以记成：触发决定什么时候开始，扫描决定一次走几个通道，Rank 决定通道顺序。

<<<<<<< Updated upstream
规则组可以登记多个 Rank。Rank 可以理解为"流水线上的工位顺序"：触发一次，ADC 从 1 号工位开始依次加工：

```text
Rank 1 -> Rank 2 -> Rank 3 -> Rank 4
```

每个 Rank 都有自己的通道和采样时间；只有打开扫描并把 `NbrOfConversion` 设为大于 `1`，多个 Rank 才会组成一轮扫描。

| 模式 | 一次触发后的行为 | 常见用法 |
| --- | --- | --- |
| 单次 + 非扫描 | 转换 Rank 1 后停止 | 读取一个通道 |
| 连续 + 非扫描 | 不断重复转换 Rank 1 | 持续监测一个通道 |
| 单次 + 扫描 | 按 Rank 转换一轮后停止 | DMA 采集一帧 |
| 连续 + 扫描 | 一轮结束后立即开始下一轮 | DMA 循环采集 |

非扫描时只使用 Rank 1。若要轮流读取不同通道，可以停机后重新配置 Rank 1；若要一次得到多个结果，应固定 Rank 顺序并用 DMA 搬运。规则组读取 `DR`，注入组使用独立的触发路径和 `JDR`，本章不把两者混用。

- **路线 A：非扫描 + 重配 Rank 1**——每次只转一个通道，要换通道就重新调用 `HAL_ADC_ConfigChannel()` 把 Rank 1 指到另一个通道；代码直观、不需要 DMA，代价是每次换通道多几次函数调用，且通道一多代码就散。了解它有助于理解 Rank 的本质，实际工程中多通道采集几乎都走路线 B；
- **路线 B：扫描 + DMA**——一次触发按 Rank 顺序转完所有通道，DMA 自动把结果搬到数组；吞吐率高、时序整齐，是 [[07 DMA：数据搬运与 ADC 多通道采集]] 的主题。

STM32F1 在第一次正式转换前应校准一次：
=======
| 触发 | 扫描 | 一次触发后的行为 | 数据去向 |
| --- | --- | --- | --- |
| 单次 | 关 | 转换 Rank 1 后停止 | CPU 轮询读 `DR` |
| 连续 | 关 | 反复转换 Rank 1 | CPU 每次读最新值 |
| 单次 | 开 | 按 Rank 走一轮后停止 | DMA 搬进数组 |
| 连续 | 开 | 一轮接一轮 | DMA 循环覆盖数组 |

非扫描时只用 Rank 1。要轮流读不同通道，可以停机后重配 Rank 1；要一次得到多个结果，应固定 Rank 顺序并用 DMA，见第 07 章。

F103 在第一次正式转换前应校准一次：
>>>>>>> Stashed changes

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
    Error_Handler();
}
```

校准在 `MX_ADC1_Init()` 之后、第一次 `HAL_ADC_Start()` 之前执行。漏掉不会报错，典型表现是最低几位在几个码之间来回摆，容易被误当成干扰。CubeMX 不会自动生成这行代码。

<<<<<<< Updated upstream
## 6. 实验一：单通道软件触发采集

### 6.1 接线与配置

电位器是一个三端可调分压器：两个固定端接电源和地，中间滑动端的电压随旋钮在 0 到电源电压之间连续变化——它就是最安全的"模拟信号发生器"。电位器接线：
=======
## 6. 实验：单通道软件触发采集

### 6.1 接线
>>>>>>> Stashed changes

```text
3.3 V   → 电位器固定端
GND     → 另一个固定端
滑动端  → PA0 / ADC_CHANNEL_0
```

开发板与外部电路共地，PA0 不得高于 VDDA。先用万用表确认滑动端电压在 0~3.3 V 之间。

本章的 OLED 沿用 [[02 OLED 调试：I2C 显示数据流]] 的硬件 I2C2 版（`PB10/PB11`，地址 `0x78`）。若工程里用的是软件 I2C 版，6.3 节删掉 `HAL_I2C_IsDeviceReady()` 那几行和 `#include "i2c.h"` 即可，`OLED_Init()` 和显示代码不变；两版不要同时登记。

<<<<<<< Updated upstream
CubeMX 中设置：

1. PA0 配置为 `Analog`；
2. 启用 ADC1 Regular Conversions，转换数量为 `1`；
3. Rank 1 选择 `ADC_CHANNEL_0`；
4. 采样时间选择 `ADC_SAMPLETIME_55CYCLES_5`；
5. 扫描和连续转换关闭，外部触发选择软件启动；
6. ADC 预分频选择 `/6`，检查得到 $f_{ADC}=12\,\text{MHz}$（并按 3.2 节确认分频代码确实在工程里）；
7. 第一次转换前执行 ADC 校准。

对应的 ADC 初始化核心代码为（与 `01_Basic/Core/Src/adc.c` 一致）：
=======
### 6.2 CubeMX 配置

1. `PA0` 配置为 `Analog`。
2. 启用 ADC1 的 Regular Conversions，转换数量为 1。
3. Rank 1 选择 `ADC_CHANNEL_0`。
4. 采样时间选 `ADC_SAMPLETIME_55CYCLES_5`。
5. 关闭扫描和连续转换，外部触发选软件启动。
6. ADC 预分频选 `/6`，确认生成代码里有对应配置。
7. 第一次转换前执行校准。

生成的初始化代码如下：
>>>>>>> Stashed changes

```c
ADC_HandleTypeDef hadc1;

void MX_ADC1_Init(void)
{
    ADC_ChannelConfTypeDef channel = {0};

    hadc1.Instance = ADC1;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.NbrOfConversion = 1U;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    if (HAL_ADC_Init(&hadc1) != HAL_OK)
    {
        Error_Handler();
    }

    channel.Channel = ADC_CHANNEL_0;
    channel.Rank = ADC_REGULAR_RANK_1;
    channel.SamplingTime = ADC_SAMPLETIME_55CYCLES_5;
    if (HAL_ADC_ConfigChannel(&hadc1, &channel) != HAL_OK)
    {
        Error_Handler();
    }
}
```

<<<<<<< Updated upstream
逐个字段解释（括号内为 `01_Basic` 的实际取值）。`ADC_InitTypeDef` 的字段：

| 字段（工程值） | 含义 | 填错会怎样 |
| --- | --- | --- |
| `DataAlign`（`ADC_DATAALIGN_RIGHT`） | 结果靠右放进 16 位寄存器，读数直接是 `0~4095` | 用左对齐却忘了右移 4 位，读数会整整大 16 倍（2.2 节） |
| `ScanConvMode`（`ADC_SCAN_DISABLE`） | 关闭扫描，只认 Rank 1 一个通道 | 开了扫描却用轮询读 `DR`，前一个结果没取走就被下一个覆盖 |
| `ContinuousConvMode`（`DISABLE`） | 单次：一次触发只转一次，想再转需再 `Start` | 设 `ENABLE` 后 ADC 自己连转不停，配合软件触发会一直占用 ADC |
| `DiscontinuousConvMode`（`DISABLE`） | 不把序列拆成几段分次转换 | 学习阶段保持关闭；打开需配合 `NbrOfDiscConversion` |
| `NbrOfConversion`（`1U`） | 规则组序列长度为 1 | 与实际 Rank 数不一致时序列不完整 |
| `ExternalTrigConv`（`ADC_SOFTWARE_START`） | 由软件 `HAL_ADC_Start()` 触发 | 选了硬件触发源却不启动对应定时器，永远等不到转换（定时器触发见第 7 章） |
=======
关键字段：

| 字段 | 含义 | 填错的后果 |
| --- | --- | --- |
| `ScanConvMode` | 关闭扫描，只转 Rank 1 | 开扫描却轮询读 `DR`，结果会被下一通道覆盖 |
| `ContinuousConvMode` | 一次触发只转一次 | 选连续后会一直转换，占用 ADC |
| `NbrOfConversion` | 规则组长度 | 与实际 Rank 数不符时，数据会少一半或多出残留值 |
| `ExternalTrigConv` | 软件启动 | 选硬件触发却没启动定时器，永远等不到转换 |
| `DataAlign` | 结果右对齐 | 左对齐未右移，读数大 16 倍 |
| `SamplingTime` | 每通道的采样窗口 | 太短且源阻抗大时读数偏低 |

F103 的 `ADC_InitTypeDef` 没有分辨率字段，ADC 固定 12 位。采样时间也不在总初始化里，而是按通道配置，所以每个 Rank 可以用不同档位。

PA0 的模拟模式在 `adc.c` 底部的 `HAL_ADC_MspInit()` 中配置，`HAL_ADC_Init()` 会回调它。
>>>>>>> Stashed changes

### 6.3 代码

<<<<<<< Updated upstream
| 字段（工程值） | 含义 | 填错会怎样 |
| --- | --- | --- |
| `Channel`（`ADC_CHANNEL_0`） | 本 Rank 接通哪个模拟开关 | 通道号和引脚由硬件绑定，写错等于测了另一个引脚 |
| `Rank`（`ADC_REGULAR_RANK_1`） | 本通道排在序列第几位 | 多通道时 Rank 顺序就是数组下标顺序（第 7 章） |
| `SamplingTime`（`ADC_SAMPLETIME_55CYCLES_5`） | 采样阶段持续 55.5 个 ADC 时钟 | 档位太短、源阻抗大时读数偏低（4.2 节） |

- F103 的 `ADC_InitTypeDef` 里**没有分辨率字段**——F1 的 ADC 固定 12 位，2.1 节的 4096 级就是它的全部精度（可对照工程内 `stm32f1xx_hal_adc.h` 的结构体定义）；
- 采样时间不属于 `ADC_InitTypeDef`，而是按通道在 `ADC_ChannelConfTypeDef` 里配置——这正是"每个 Rank 可以有不同档位"的结构基础，内部通道的档位要求见第 7 章 10.3 节。

PA0 的 `GPIO_MODE_ANALOG` 不在 `MX_ADC1_Init()` 里，而在 `adc.c` 底部的 `HAL_ADC_MspInit()` 中：`HAL_ADC_Init()` 执行时会回调它，在那里使能 ADC1 和 GPIOA 时钟、把 PA0 配成模拟模式。`.ioc` 中对应的关键行：`PA0.Signal=ADC1_IN0`、`ADC1.Channel-0=ADC_CHANNEL_0`、`ADC1.SamplingTime-0=ADC_SAMPLETIME_55CYCLES_5`、`RCC.ADCFreq_Value=12000000`。

### 6.2 最小轮询代码

`HAL_ADC_Start()` 启动规则组，`HAL_ADC_PollForConversion()` 等待常规转换完成，`HAL_ADC_GetValue()` 读取 `DR`。下面是 `01_Basic/Core/Src/main.c` 的实际初始化序列（保留 CubeMX 生成的 `MX_*_Init()`，只展示用户代码）：
=======
先在 `USER CODE BEGIN Includes` 和 `PV` 里补齐本章要用的头文件与变量：

```c
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include "i2c.h"
#include "OLED.h"
/* USER CODE END Includes */

/* USER CODE BEGIN PV */
uint16_t adc_code = 0U;
uint32_t voltage_mv = 0U;
char text[16];
/* USER CODE END PV */
```

`USER CODE BEGIN 2` 里先初始化显示和 ADC，再做校准：
>>>>>>> Stashed changes

```c
HAL_Delay(20U);
if (HAL_I2C_IsDeviceReady(&hi2c2, 0x78U, 3U, 100U) != HAL_OK)
{
  Error_Handler();
}
OLED_Init();
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
  Error_Handler();
}
```

<<<<<<< Updated upstream
逐行解释：

- `HAL_Delay(20U)`：给 OLED 模块留出上电稳定时间，再开始 I2C 通信；
- `HAL_I2C_IsDeviceReady(&hi2c2, 0x78U, 3U, 100U)`：探测 I2C2 上地址 `0x78` 的设备（SSD1306 的常用地址，见第 02 章）是否应答，最多试 3 次、每次超时 100 ms。应答失败会进入 `Error_Handler()` 关中断死循环——程序"卡住不动"本身就是 OLED 没接好的信号；
- `HAL_ADCEx_Calibration_Start(&hadc1)`：按第 5 节的要求，在 `MX_ADC1_Init()` 之后、第一次转换之前校准。

主循环（`USER CODE BEGIN WHILE` 区域内）：
=======
主循环里启动转换、等待完成、读值并显示：
>>>>>>> Stashed changes

```c
if (HAL_ADC_Start(&hadc1) == HAL_OK &&
    HAL_ADC_PollForConversion(&hadc1, 10U) == HAL_OK)
{
  adc_code = (uint16_t)HAL_ADC_GetValue(&hadc1);
  voltage_mv = ((uint32_t)adc_code * 3300U + 2047U) / 4095U;
}

OLED_NewFrame();
snprintf(text, sizeof(text), "ADC:%4u", (unsigned int)adc_code);
OLED_PrintASCIIString(0, 0, text, &afont16x8, OLED_COLOR_NORMAL);
snprintf(text, sizeof(text), "V:%u.%03uV",
         (unsigned int)(voltage_mv / 1000U),
         (unsigned int)(voltage_mv % 1000U));
OLED_PrintASCIIString(0, 20, text, &afont16x8, OLED_COLOR_NORMAL);
OLED_ShowFrame();
HAL_Delay(100U);
```

电压换算用整数毫伏，避免浮点：

<<<<<<< Updated upstream
$$V_{mv}\approx\frac{ADC\_Code\times3300}{4095}$$
=======
$$
V_{\mathrm{mv}}\approx\frac{\mathrm{ADC\_Code}\times3300}{4095}
$$
>>>>>>> Stashed changes

`adc_code` 先转成 `uint32_t` 再乘，防止溢出；加 2047 是四舍五入；显示时拆成整数伏和三位小数。显示函数只改显存，`OLED_Update()` 才发送到屏幕。

<<<<<<< Updated upstream
- **乘 3300 而不是乘 3.3**：F103 没有硬件浮点单元，浮点运算又慢又占空间；把单位改成毫伏后全部用整数运算。`adc_code` 先转 `uint32_t` 再乘，避免 4095×3300 超出 16 位范围；
- **`+2047U` 用于近似四舍五入**：整数除法会把小数部分直接砍掉，先加上半个分母（4095 的一半取整为 2047），能让结果尽量靠近真实值；
- **显示拆成两段**：`voltage_mv` 是毫伏整数，`/1000` 得整数伏、`%1000` 得三位小数，用 `%u.%03u` 拼出如 `1.650V` 的形式，避免引入浮点 `printf`。

OLED 驱动函数 `OLED_NewFrame()` / `OLED_PrintASCIIString()` / `OLED_ShowFrame()` 与字体 `afont16x8` 来自第 02 章的 OLED 驱动（挂在 I2C2、PB10/PB11 上），先在内存里组好一帧再整帧显示，可避免刷新撕裂。时间预算上：`55.5 + 12.5 = 68` 个周期，在 $12\,\text{MHz}$ 下一次转换约需 `5.67 μs`；OLED 以 `100 ms` 间隔刷新时，ADC 转换时间不是整屏更新速度的瓶颈。

### 6.3 预期现象
=======
55.5 加 12.5 共 68 个周期，12 MHz 下一次转换约 5.67 µs，远快于 100 ms 的显示刷新，不是瓶颈。

### 6.4 现象与排查

旋转电位器，原码在 `0~4095` 之间变化，电压按原码比例变化。接近 GND 时读数接近 0，接近 3.3 V 时接近 4095。OLED 读数应与万用表趋势一致，末位轻微波动正常。

没有电位器时，把 PA0 分别短接到 GND 和 3.3 V 做对照。两端都不对，查模拟输入配置、通道映射、参考电压和共地；两端正常而电位器读数异常，查电位器接线和分压。先量滑动端，再量 PA0 引脚，两处一致才说明连线没问题。
>>>>>>> Stashed changes

### 6.5 驱动库写法

<<<<<<< Updated upstream
完整链路是：旋动电位器（输入）→ 软件触发、转换、整数换算（处理）→ OLED 第一行显示原码 `ADC:xxxx`、第二行显示电压 `V:x.xxxV`（输出）。

没有电位器时，可把 PA0 分别短接到 GND 和 `3.3 V` 做对照。若两端读数都不对，先查模拟输入配置、通道与引脚映射、参考电压和共地；若两端正常而电位器位置异常，再查电位器接线和外部分压电阻。

"如果看到 X，说明 Y"速查：

| 你看到的 | 大概率说明 |
| --- | --- |
| 读数随旋钮平滑变化，末位偶尔 ±1~±2 | 正常。末位跳动来自电源纹波、干扰和量化噪声 |
| 恒为 `0` | PA0 一直被拉在地：滑动端线没接到 PA0、电位器接错端子，或通道/引脚映射错误 |
| 恒为 `4095` 或接近满量程 | PA0 一直被拉到高：滑动端接到 3.3 V 端子，或输入未正确接地导致漂移 |
| 数值大幅乱跳 | 杜邦线松动或过长拾取干扰；先用 GND/3.3 V 短接对照缩小范围 |
| 与万用表差一个固定比例 | VREF 不是精确的 3.300 V（2.1 节）；用片内基准 VREFINT 反推实际 VDDA 的方法见第 7 章 10.3 节 |
| 读数整体偏低且信号源内阻大 | 采样时间不足，回 4.2 节加大档位或加跟随器 |
| 屏幕全黑或程序卡死 | OLED/I2C 问题（第 02 章）；先用调试器看 `adc_code` 变量确认 ADC 侧是否正常 |

## 7. 本章验收

- [ ] ADC 时钟、采样时间和参考电压已记录；
- [ ] 单通道原始码范围合理；
- [ ] 能区分模拟输入、ADC 配置和物理传感器问题。

## 8. 按现象定位问题

按信号链从输入端向软件端检查：

```text
传感器/分压 -> GPIO 模拟输入 -> 采样电容
-> ADC 时钟与采样时间 -> SAR -> DR
-> CPU/DMA -> 换算公式 -> 显示或控制
```

排查总原则：先用最简单的已知输入（GND、3.3 V、已知中间电压）把链路切成两半，判断问题在输入端还是软件端，再逐段深入。以"读数恒 0"为例：先把 PA0 短接到 3.3 V——若读数跳到 4000 附近，说明"采样电容 -> SAR -> DR -> 软件读值 -> 换算显示"整条软件链路是通的，问题在输入端（电位器接线、滑动端到 PA0 的连线）；若短接后仍是 0，问题在配置端，按表中第 1 行的步骤逐项检查。不要在输入范围和接线尚未确认时先修改显示代码。

| 症状 | 可能原因 | 具体检查步骤 |
| --- | --- | --- |
| 结果始终为 `0` 或接近 `4095` | 输入端被拉死在电源轨；通道/引脚映射错误；读错 ADC 实例 | ① PA0 依次短接 GND 和 `3.3 V`，两端读数都正常则问题在电位器接线；② 两端都不对时，检查 PA0 是否配成 `Analog`（`HAL_ADC_MspInit()`）、通道与引脚映射、是否超过 VDDA、外部电路是否共地；③ 确认代码读的是 ADC1（`hadc1->Instance == ADC1`） |
| 读数明显偏低、跳动或通道切换后突变 | 源阻抗过大、采样时间过短；模拟电源、地线和布局噪声 | ① 核对信号源内阻（分压电阻取值）；② 按 4.2 节重算所需采样档位并加大一档对比；③ 仍不行则查 3.3 V/VDDA 稳定性、缩短杜邦线、必要时加电压跟随器 |
| 一直收不到转换完成 | 转换根本没启动，或完成标志/中断没配 | ① 确认 `HAL_ADC_Start()` 或 `HAL_ADC_Start_DMA()` 已调用且返回 `HAL_OK`；② 轮询超时时间是否够；③ 用 DMA 时完成中断是否在 CubeMX 中使能（NVIC）；④ 外部触发模式下是否误以为软件会触发（定时器触发见第 7 章） |

多通道扫描、DMA 数组和定时器触发的故障定位，以及 NTC/VREFINT 物理量换算，见 [[07 DMA：数据搬运与 ADC 多通道采集]] 的排错与换算两节。
=======
`E:\ProjectStm\驱动库\RP` 把“配通道、启动、等完成、读值”封成两个函数：

```c
void RP_Init(void);                 /* 内部执行校准 */
uint16_t RP_GetValue(uint8_t n);    /* n = 1~4，返回 0~4095 */
```

把 `rp.c`、`rp.h` 复制到 `User/Drivers/RP/` 并登记；`main.c` 里 `MX_ADC1_Init()` 之后要先调一次 `RP_Init()`。

主循环只剩 `adc_code = RP_GetValue(1);`。它每次调用都会重配通道，所以 CubeMX 里 ADC 必须保持单次、非扫描、软件触发。默认绑定 ADC2 的通道 2~5（`PA2~PA5`），本实验改两个宏：

```c
#define RP_ADC_HANDLE   hadc1              /* 默认 hadc2 */
#define RP1_CHANNEL     ADC_CHANNEL_0      /* 默认 ADC_CHANNEL_2 */
```

`RP_SAMPLING_TIME` 才是驱动实际使用的采样档位，CubeMX 里那一档只对直接调用 HAL 的写法有效，两处填成同一档最省心。

封装省掉的是重复代码，不是原理。`RP_GetValue()` 没有超时处理，ADC 真坏了程序会一直等下去。调试阶段直接调 HAL 更容易看清每一步。

倒立摆的 RP 驱动默认用 ADC2 的 `CH2~CH5`（`PA2~PA5`），本章用 ADC1/`PA0` 只是单通道最小实验；换回综合工程时把 6.5 节改过的 `RP_ADC_HANDLE` 与通道宏改回 `hadc2`、`ADC_CHANNEL_2~5` 即可，采样结构不变，见 [[STM32倒立摆/03 基础驱动：CubeMX与HAL库实现#1.5 与入门教程共用驱动]]。
>>>>>>> Stashed changes

上一篇：[[05 定时器：时基、PWM、输入捕获与电机控制]] ｜ 下一篇：[[07 DMA：数据搬运与 ADC 多通道采集]]
