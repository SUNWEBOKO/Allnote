# 03 时钟系统：时钟树、PLL 与 HAL 配置

## 本章问题

<<<<<<< Updated upstream
怎样从时钟树推导 HSI/HSE/PLL 配置，并用实验比较 8 MHz 和 72 MHz？

前两章的程序已经能够运行并驱动 OLED，但还留下一个基础问题：芯片究竟以多快的速度运行？第 0 章的 CubeMX 配置中写着 `HSE 8 MHz + PLL×9 = 72 MHz`，当时我们暂时照用。本章回到这行配置，说明时钟源、总线频率和 `HAL_Delay(500)` 的 1 ms 时基分别从哪里来。完成后，你将用两个工程对比 8 MHz 与 72 MHz 下的 LED 闪烁速度。

## 学习目标

- 画出 STM32F103 从 HSI/HSE 到 SYSCLK、HCLK、PCLK1 和 PCLK2 的路径
- 检查 PLL、AHB 和 APB 分频参数是否满足频率上限
- 按初始化顺序配置 HSE、PLL、SYSCLK、分频和 Flash 等待周期
- 核对 HAL 频率读数与 MCO 输出波形
- 比较 8 MHz 与 72 MHz 配置下的 LED 速度
=======
前两章的延时、I2C 速度都默认芯片跑在 72 MHz，这个数字从第 0 章就填在 CubeMX 里，却一直没解释。本章沿着时钟树看节拍从哪里来，把 8 MHz 算成 72 MHz，再配置到工程里，最后用 LED 闪烁速度验证。

## 学习目标

- 画出 HSI/HSE 到 SYSCLK、HCLK、PCLK1、PCLK2 的路径。
- 用 `8 MHz × 9 = 72 MHz` 算主频，并核对 PLL 的输入输出范围。
- 按分频关系算出三条总线频率，判断是否超限。
- 按顺序配置 HSE、PLL、SYSCLK、分频和 Flash 等待周期。
- 用 HAL 读数或 MCO 引脚核对实际时钟。
>>>>>>> Stashed changes

## 1. 时钟与时钟树

<<<<<<< Updated upstream
### 1.0 先建立直觉：为什么芯片需要"心跳"

把芯片想象成一条流水线：CPU、存储器、外设都是工位，数据是流水线上的零件。如果每个工位各干各的、想动就动，零件传到下一个工位时可能还没就位，就会出错。**时钟就是统一的口令**：每敲一下，所有寄存器同时向前走一步。

用电路的语言再说一遍：门电路有传播延迟，输入变化后的一小段时间里，信号可能停在"半途"的中间状态。寄存器、计数器这类要"记住东西"的电路，必须等信号稳定后，在时钟边沿那一刻一次性把值存下来，否则就会记下错误值——所以全芯片共用同一个心跳，让所有电路在同一时刻采存、同一时刻前进。

因此，时钟不仅决定运行速度，还决定串口波特率、定时器计数步长、ADC 采样速率等外设参数。这一条后面章节会反复用到：第 5 章定时器计数快慢、第 8 章串口波特率准不准，全都取决于本章配置的时钟树。

以下以 `STM32F103C8T6` 和板载 `8 MHz` HSE 晶振为计算示例；其他型号的频率范围、外设挂载位置和 PLL 选项应以对应数据手册为准。

### 1.1 时钟树主线

![STM32F1 时钟树总览](<image/Pasted image 20260727154625.png>)

> 这张图只作时钟树示意。STM32F103C8T6 的实际可用外设和引脚以目标芯片资料、CubeMX 时钟树及生成的 `SystemClock_Config()` 为准。
=======
CPU、存储器和外设按同一个节拍工作，这个节拍就是时钟。节拍快，同一段代码跑得就快；串口波特率、定时器步长、ADC 采样率也都由它分出来，所以时钟错了，所有跟时间有关的数字都会跟着错。
>>>>>>> Stashed changes

把时钟树看成一套“分级齿轮”：最左边是动力源（可选振荡器），中间是倍频齿轮（PLL，把 8 MHz 转成 72 MHz）和选挡开关（系统时钟 MUX，决定哪个源驱动主轴），SYSCLK 之后再经过 AHB、APB 分频器，把合适的频率分配给各外设。

<<<<<<< Updated upstream
读图时先沿主干向上追踪 `HSI/HSE -> PLL/MUX -> SYSCLK -> AHB -> HCLK`，再沿 `APB1/APB2` 找到 `PCLK1/PCLK2` 和具体外设：

```text
HSI/HSE -> PLL 与系统时钟选择 -> SYSCLK
        -> AHB 分频 -> HCLK
        -> APB1/APB2 分频 -> PCLK1/PCLK2 -> GPIO、串口、定时器、ADC 等
```

低速分支 `LSI/LSE` 主要服务 RTC 和独立看门狗 IWDG，不经过高速 PLL 主干。

时钟源有四种，名字由两个词根拼成：`HS/LS` 表示高速/低速，`I/E` 表示内部/外部。所以 HSI 就是"高速内部"，HSE 就是"高速外部"，依此类推：
=======
时钟树的主线是三行：

```text
HSI/HSE → PLL → SYSCLK
              → AHB 分频 → HCLK
              → APB1/APB2 分频 → PCLK1/PCLK2 → GPIO、串口、定时器、ADC
```

四个时钟源的名字由“高速/低速”和“内部/外部”组合而成：
>>>>>>> Stashed changes

| 时钟源 | 频率与特点 | 用途 |
| --- | --- | --- |
| `HSI` | 片内 RC，8 MHz，启动快、精度低 | 默认系统时钟、PLL 输入 |
| `HSE` | 外部晶振，常见 4~16 MHz，精度高 | 系统主频、PLL 输入 |
| `LSI` | 片内低速 RC，约 40 kHz | 独立看门狗、RTC 备选 |
| `LSE` | 外部 32.768 kHz 晶振 | RTC |

<<<<<<< Updated upstream
HSI 是片内的 RC 振荡器——用电阻电容的充放电节奏产生时钟，好处是芯片上电立刻可用、不依赖任何外部元件，代价是频率会随温度、电压和芯片个体漂移，出厂时校准到"大约 8 MHz"。HSE 是焊在板子上的石英晶振，机械振动频率非常稳定，所以要求精确频率的场合（串口波特率、USB、精确定时）都应切到 HSE 或 PLL。

HSE 使用晶振时选择 **Crystal/Ceramic Resonator**；只有外部已经提供完整方波时才选择 **Bypass Clock Source**，两种模式不能混用。最常见的错误是板子上明明焊着晶振，却在 CubeMX 里选了 Bypass——HAL 会去等一个永远不会来的外部方波，实验 02 会直接卡在时钟启动这一步（详见 6.1 节）。

### 1.2 本章实验走的是哪两条路径

把时钟树收拢成一张简图，并标出两个配套工程各自走过的路径（频率为两个工程的实际配置值）：

```text
【低速分支】（与本章实验无关，知道即可）
LSI（约 40 kHz） ────────→ IWDG（独立看门狗，只能由 LSI 驱动）
LSE（32.768 kHz） ───────→ RTC（RTC 也可选 LSI 或 HSE/128）

【高速分支】（本章主角）

  HSI 8 MHz（片内 RC）──────────────┐
                                   ├─→ [系统时钟 MUX]   ← 挡位三选一：HSI / HSE / PLLCLK
  HSE 8 MHz（板载晶振）─→ [PLL] ────┘        01 工程选 HSI；02 工程选 PLLCLK
                        （HSE /1 × 9 = 72 MHz）     ↓
                                              SYSCLK（01：8 MHz ／ 02：72 MHz）
                                                    ↓
                                              [AHB /1] ─→ HCLK（01：8 MHz ／ 02：72 MHz）
                                                    ↓
                                    ┌── [APB2 /1] ─→ PCLK2（01：8 MHz ／ 02：72 MHz）
                                    │        ─→ GPIO、USART1、SPI1、TIM1
                                    └── [APB1 /2] ─→ PCLK1（01：8 MHz ／ 02：36 MHz）
                                             ─→ USART2/3、I2C、TIM2~TIM4

实验 01_HSI_8MHz 的路径：HSI → MUX 选 HSI → SYSCLK 8 MHz → HCLK/PCLK1/PCLK2 全部 8 MHz
实验 02_PLL_72MHz 的路径：HSE → PLL ×9 → MUX 选 PLLCLK → SYSCLK 72 MHz → HCLK 72、PCLK1 36、PCLK2 72
```

SysTick 挂在 Cortex-M3 内核一侧，跟随 HCLK 计数；MCO 是一根可以把内部时钟"引出来看"的引脚（PA8），本章 4.2 节会用它做独立测量。

### 1.3 总线时钟还要经过外设门控

总线有频率不等于外设已经工作。GPIO、TIM、ADC 等外设还需要对应的 RCC 门控位：
=======
HSI 不依赖外部元件，上电即可用，但频率会随温度和电压漂移；HSE 是板上的石英晶振，频率稳定，需要精确时钟时都用它。CubeMX 里使用板载晶振，选 `Crystal/Ceramic Resonator`。

时钟送到总线之后，每个外设还有自己的门控开关，用对应的 `__HAL_RCC_*_CLK_ENABLE()` 打开：
>>>>>>> Stashed changes

```c
__HAL_RCC_GPIOC_CLK_ENABLE();  /* GPIOC 在 APB2 */
__HAL_RCC_TIM2_CLK_ENABLE();   /* TIM2 在 APB1 */
__HAL_RCC_DMA1_CLK_ENABLE();   /* DMA1 在 AHB */
```

<<<<<<< Updated upstream
可以把门控位想象成每间外设"屋子"自己的电闸：总线是主配电箱，电闸不合上，屋子里的设备再好也不转。第 1 章你已经在 `MX_GPIO_Init()` 里见过 `__HAL_RCC_GPIOC_CLK_ENABLE()`——没有这一行，往 `GPIOC` 寄存器写什么都没反应，这是"引脚完全没动静"类故障的高频原因。

门控只决定时钟是否送达外设，不会改变 `PCLK1/PCLK2` 的频率。
=======
门控没开，写外设寄存器不会有任何反应。它只决定时钟是否送到外设，不改变总线频率。

## 2. PLL 与主频计算
>>>>>>> Stashed changes

### 2.1 从 8 MHz 到 72 MHz

<<<<<<< Updated upstream
### 2.1 PLL 输入、输出和合法范围

PLL（锁相环）名字听起来吓人，本质是一个"可控倍频齿轮"：它让内部一个高速振荡器与输入时钟保持严格的相位同步，同步关系就是"输出频率 = 输入频率 × 固定倍数"。输入只有 8 MHz，晶振很难直接焊出 72 MHz 的谐振频率，而 PLL 可以稳定地把 8 MHz 整整倍乘 9 倍——这就是它存在的原因。

STM32F103 的 PLL 输入可选 `HSI/2`、`HSE` 或 `HSE/2`，倍频通常为 `x2~x16`：

$$
f_{\mathrm{PLL}}=f_{\mathrm{PLL\ in}}\times M
$$

F103 的 PLL 输入频率范围为 `1~25 MHz`（数据手册给出的电气限制），输出上限为 `72 MHz`；输入或输出越界都可能导致无法锁定或超规运行。可以这样理解这两条边界：输入太低，PLL 内部电路跟不上节奏锁不住；输出太高，超出这颗芯片的设计速度，同样不可靠。`SYSCLK` 最后可选择 `HSI`、`HSE` 或 `PLLCLK`，因此配置过程本质上是"选源、乘频、分频、切换"。

分频挡位和倍频可以自由组合，例如 `HSE/2 ×6` 同样从 8 MHz 得到 24 MHz；判断组合是否合法的办法很机械——代入公式，逐项检查输入在 `1~25 MHz` 内、输出在 `16~72 MHz` 内。例如同样的 `/2` 挡只乘 `3`，得到 `12 MHz`，低于 PLL 输出下限 16 MHz，就不是合法配置。

从 `8 MHz` HSE 得到 F103C8T6 的最高常用主频：

$$
f_{\mathrm{SYSCLK}}=8\times 9=72\,\mathrm{MHz}
$$

`8 × 9 = 72` 没有任何取整余量，所以板载晶振频率必须和软件假设一致：晶振真是 `8 MHz`，`×9` 才是 72；如果板上焊的是别的频率，`×9` 就会得到一个错误的主频（本章 6.4 节会给出发现方法）。

### 2.2 AHB 与 APB 分频

`SYSCLK` 先经过 AHB 分频得到 `HCLK`，再由两个 APB 分频器得到 `PCLK1` 和 `PCLK2`：

$$
f_{\mathrm{HCLK}}=\frac{f_{\mathrm{SYSCLK}}}{N_{\mathrm{AHB}}}
$$

$$
f_{\mathrm{PCLK1}}=\frac{f_{\mathrm{HCLK}}}{N_{\mathrm{APB1}}},\qquad
f_{\mathrm{PCLK2}}=\frac{f_{\mathrm{HCLK}}}{N_{\mathrm{APB2}}}
$$

为什么主轴之后还要再"减速"？因为不是每个外设都吃得下 72 MHz：CPU 和 Flash 跑得快，但许多老资格外设（比如 I2C、低速串口）跟不上。分成三条转速递减的总线，既让快的跑满，又让慢的稳定工作，还顺便省电。三条总线的"转速上限"由芯片设计决定：

STM32F103 的 AHB 合法分频为 `/1、/2、/4、/8、/16、/64、/128、/256、/512`（RCC_CFGR 的 HPRE 位段），APB 合法分频为 `/1、/2、/4、/8、/16`；72 MHz 配置用到的只是其中最常用的几档，最终仍以具体型号手册和 CubeMX 可选值为准。

| 节点 | STM32F103C8T6 常见上限 | 典型对象 |
| --- | ---: | --- |
| `HCLK` | `72 MHz` | Cortex-M3、Flash、SRAM、DMA |
| `PCLK1` | `36 MHz` | USART2/3、I2C、CAN、TIM2~TIM4 |
| `PCLK2` | `72 MHz` | GPIO、ADC、USART1、SPI1、TIM1 |

`72 MHz` 主频的常用组合为：
=======
PLL 是一个可控倍频器，输出频率等于输入频率乘以倍频系数：

$$
f_{\mathrm{PLL}} = f_{\mathrm{PLL\ in}} \times M
$$

F103 的 PLL 输入可以选 `HSI/2`、`HSE` 或 `HSE/2`，倍频挡位为 `x2~x16`。输入必须在 1~25 MHz，输出必须在 16~72 MHz，越界会锁不住或超规运行。

本章用 8 MHz 的 HSE，倍频系数取 9：

$$
f_{\mathrm{SYSCLK}} = 8 \times 9 = 72\,\mathrm{MHz}
$$

72 MHz 是 F103 的设计上限，再高不能保证正常工作。`8 × 9` 也没有取整余量，所以板载晶振必须确实是 8 MHz。

### 2.2 AHB 与 APB 分频

不是所有外设都能跑 72 MHz，所以 SYSCLK 先经 AHB 分频得到 HCLK，再经两个 APB 分频得到 PCLK1 和 PCLK2：

$$
f_{\mathrm{HCLK}} = \frac{f_{\mathrm{SYSCLK}}}{N_{\mathrm{AHB}}}, \qquad
f_{\mathrm{PCLK1}} = \frac{f_{\mathrm{HCLK}}}{N_{\mathrm{APB1}}}, \qquad
f_{\mathrm{PCLK2}} = \frac{f_{\mathrm{HCLK}}}{N_{\mathrm{APB2}}}
$$

三条总线的上限和挂载对象：

| 节点 | 上限 | 典型对象 |
| --- | --- | --- |
| `HCLK` | 72 MHz | Cortex-M3、Flash、SRAM、DMA |
| `PCLK1` | 36 MHz | USART2/3、I2C、TIM2~TIM4 |
| `PCLK2` | 72 MHz | GPIO、ADC、USART1、SPI1、TIM1 |

常用的 72 MHz 配置是：
>>>>>>> Stashed changes

```text
HSE = 8 MHz
PLL = HSE × 9 = 72 MHz
SYSCLK = 72 MHz
AHB  = /1 → HCLK  = 72 MHz
APB1 = /2 → PCLK1 = 36 MHz
APB2 = /1 → PCLK2 = 72 MHz
```

<<<<<<< Updated upstream
APB1 不能在 F103 的 `72 MHz` 主频下直接取 `72 MHz`，因此必须至少 `/2`。核对方法很机械：把每个分频挡位代进上面的公式，逐个检查 `HCLK ≤ 72`、`PCLK1 ≤ 36`、`PCLK2 ≤ 72`，任何一项越界都要重选挡位。CubeMX 的 Clock Configuration 页面会在你选错时画出红色错误提示，配置合法后提示才会消失。

### 2.3 定时器与专用外设时钟

APB 定时器时钟还要应用"乘 2"规则：

$$
f_{\mathrm{TIM}x}=
\begin{cases}
f_{\mathrm{PCLK}x}, & N_{\mathrm{APB}x}=1\\
2f_{\mathrm{PCLK}x}, & N_{\mathrm{APB}x}>1
\end{cases}
$$

这条规则读起来奇怪（分频之后反而乘回去？），设计意图是：无论 APB 怎么减速，定时器都尽量拿到能拿到的最高时钟，这样同一个定时器在不同分频挡位下都有足够的计时分辨率。结论记成一句话：**APB 分频大于 1 时，该总线上定时器的实际时钟是 PCLK 的 2 倍。**

所以 `PCLK1=36 MHz` 时，TIM2~TIM4 的输入时钟通常按 `72 MHz` 计算；`PCLK2=72 MHz` 且 APB2 不分频时，APB2 定时器时钟仍为 `72 MHz`。

其他分支不能直接用总线名称代替计算：

- **SysTick**：Cortex-M3 内核自带的计数器，HAL 的 `HAL_Delay()` 和 HAL Tick 依赖它。`HAL_Init()` 里就是拿 `SystemCoreClock` 除以 1000 算出"1 ms 中断一次"的装载值（工程 HAL 源码 `HAL_InitTick()` 中可见），所以 SysTick 的节奏直接跟着 HCLK 走；`HAL_RCC_ClockConfig()` 成功后会按新的 `HCLK` 重新配置 HAL Tick。
- **ADC**：F103 的 ADC 时钟由 `PCLK2` 再分频。`PCLK2=72 MHz` 时，`/6` 得 `12 MHz`、`/8` 得 `9 MHz`；`/2` 和 `/4` 会超过常见的 `14 MHz` 上限。第 6 章配 ADC 时要专门核对这一分频。
- **USB**：F103 USB 需要精确的 `48 MHz`。`72 MHz` PLL 可通过专用 `1.5` 分频得到 `48 MHz`，不能把 `PCLK2` 直接当作 USB 时钟。
- **RTC**：可选 `LSE`、`LSI` 或 `HSE/128`；`32.768 kHz` LSE 经 `32768` 分频可得到 `1 Hz`——这就是手表晶振为什么是 2 的 15 次方：连续除以 2 十五次，正好得到秒脉冲。
- **IWDG**：F103 的 IWDG 只能由 LSI 驱动，主系统时钟异常时仍可复位系统。
- **Flash**：频率升高必须增加等待周期。Flash 的读出速度有限，CPU 却越跑越快，于是需要在取指时插入等待拍——就像翻书速度跟不上眼睛扫视速度时，只能每翻一页多等一拍。F103 常见边界为 `HCLK≤24 MHz` 用 `0 WS`，`24 MHz<HCLK≤48 MHz` 用 `1 WS`，`48 MHz<HCLK≤72 MHz` 用 `2 WS`。HAL 里对应的宏是 `FLASH_LATENCY_0/1/2`（定义在 `stm32f1xx_hal_flash.h`）。等待周期配少会导致取指不可靠、程序行为异常，配多了只是稍微变慢；所以 72 MHz 必须给 `FLASH_LATENCY_2`，8 MHz 给 `FLASH_LATENCY_0` 就够。
=======
CubeMX 的 `Clock Configuration` 页会在参数非法时标红。页面上的频率只是按输入算出的图纸值，它不知道板上的晶振实际有多快。

### 2.3 定时器与专用外设时钟

APB 上的定时器不直接使用 PCLK，而是按下面的规则取时钟：

$$
f_{\mathrm{TIM}x} =
\begin{cases}
f_{\mathrm{PCLK}x}, & N_{\mathrm{APB}x} = 1 \\
2 f_{\mathrm{PCLK}x}, & N_{\mathrm{APB}x} > 1
\end{cases}
$$

所以本章 `PCLK1 = 36 MHz`，但 TIM2/3/4 的时钟是 72 MHz。第 5 章算 PWM 频率时若拿 36 MHz 去算，实测周期会正好差一倍。

其余几路时钟：

- SysTick 由 HCLK 驱动，`HAL_Init()` 按 `SystemCoreClock` 配出 1 ms 中断，`HAL_Delay()` 靠它计时；
- ADC 时钟由 PCLK2 再分频，72 MHz 下 `/6` 得 12 MHz、`/8` 得 9 MHz，`/2`、`/4` 会超过常见的 14 MHz 上限；
- USB 需要精确的 48 MHz，由 PLL 经 1.5 分频得到；
- RTC 可选 LSE、LSI 或 HSE/128，32.768 kHz 经 32768 分频得到 1 Hz；
- 独立看门狗只能由 LSI 驱动；
- Flash 频率越高，读取越跟不上 CPU，必须插入等待周期，本章 72 MHz 用 `FLASH_LATENCY_2`。

## 3. CubeMX 与 HAL 配置

### 3.1 CubeMX 设置
>>>>>>> Stashed changes

以 HSE 8 MHz、PLL ×9、72 MHz 为例：

<<<<<<< Updated upstream
### 3.1 CubeMX 必要设置

以 HSE `8 MHz`、PLL `x9`、`72 MHz` 为例：

1. 在 `Pinout & Configuration -> RCC` 中启用 HSE；板载晶振选择 `Crystal/Ceramic Resonator`。这一步对应"打开动力源"；
2. 在 `Clock Configuration` 中确认输入频率为 `HSE=8 MHz`。这一步对应"告诉图纸晶振实际多快"；
3. 设置 `PLL Source = HSE`、HSE 预分频 `/1`、`PLL Mul = x9`。这一步是"接好并调好倍频齿轮"；
4. 将 `System Clock Mux` 选为 `PLLCLK`。这一步是"把选挡杆推到 PLL 挡"；
5. 设置 `AHB=/1`、`APB1=/2`、`APB2=/1`，并确认错误提示已消失。这一步是"给三条总线分转速"，错误提示消失说明上限检查全部通过；
6. 生成代码，检查 `SystemClock_Config()` 中的 Flash 参数为 `FLASH_LATENCY_2`。这一步是"给 CPU 取指留出等待拍"。

配置完成后可以对照 `.ioc` 文件：实验 02 的工程里会出现 `RCC.PLLMUL=RCC_PLL_MUL9`、`RCC.PLLSourceVirtual=RCC_PLLSOURCE_HSE`、`RCC.SYSCLKSource=RCC_SYSCLKSOURCE_PLLCLK`、`RCC.APB1CLKDivider=RCC_HCLK_DIV2` 这些行（本教程配套 `.ioc` 中已核对），它们就是你在 Clock Configuration 页面里的每次点击。另外注意：启用 HSE 后，`PD0/PD1` 两个引脚被自动占用作 `RCC_OSC_IN/RCC_OSC_OUT`，不能再当普通 GPIO 用。

### 3.2 初始化顺序与完整 HAL 配置

CubeMX 生成的启动顺序通常是：
=======
1. `Pinout & Configuration → RCC`，`HSE` 选 `Crystal/Ceramic Resonator`。
2. `Clock Configuration` 确认 `HSE = 8 MHz`。
3. `PLL Source` 选 `HSE`，HSE 预分频 `/1`，`PLL Mul` 选 `x9`。
4. `System Clock Mux` 选 `PLLCLK`。
5. `AHB = /1`、`APB1 = /2`、`APB2 = /1`，确认没有红色错误提示。
6. 生成代码。

8 MHz 与 72 MHz 各存一份 `.ioc`，切换时在 CubeMX 的 `Clock Configuration` 页按下面几项核对，不要手改 `.ioc`：

| 设置 | 8 MHz 对照组 | 72 MHz 实验组 |
| --- | --- | --- |
| `HSE` | 关闭 | `Crystal/Ceramic Resonator` |
| `PLL` | 关闭 | 源 `HSE`，倍频 `x9` |
| `System Clock Mux` | `HSI` | `PLLCLK` |
| `AHB Prescaler` | `/1` | `/1` |
| `APB1 Prescaler` | `/1` | `/2` |
| `APB2 Prescaler` | `/1` | `/1` |

`.ioc` 是 CubeMX 的私有文本格式，键名随版本变化。要在文件里核对 72 MHz 组，关键几项是 `PD0-OSC_IN.Mode=HSE-External-Oscillator`、`RCC.PLLSourceVirtual=RCC_PLLSOURCE_HSE`、`RCC.PLLMUL=RCC_PLL_MUL9`、`RCC.SYSCLKSource=RCC_SYSCLKSOURCE_PLLCLK`、`RCC.APB1CLKDivider=RCC_HCLK_DIV2`；8 MHz 对照组由另一份纯 HSI 的 `.ioc` 保存，不靠手改同一文件。

### 3.2 初始化顺序
>>>>>>> Stashed changes

```text
Reset_Handler → SystemInit() → C 运行库 → main()
main() → HAL_Init() → SystemClock_Config() → MX_xxx_Init() → 主循环
```

<<<<<<< Updated upstream
逐级解释这条链：上电后启动文件 `startup_*.s` 先把堆栈和中断向量表摆好（第 0 章提过），然后调 `SystemInit()`——它只做最基础的系统初始化，此时芯片仍运行在复位默认的 HSI 8 MHz 上。进入 `main()` 后，`HAL_Init()` 设置默认 NVIC 分组、初始化 HAL Tick（把 SysTick 配成 1 ms 中断，供 `HAL_Delay()` 使用）并调用 `HAL_MspInit()`；`SystemClock_Config()` 再建立目标系统时钟并更新 SysTick，最后才初始化依赖这些时钟的外设。看到 `SystemInit()` 不能直接认定系统已经运行在 `72 MHz`，仍应检查 `SystemClock_Config()` 的实际内容。

这个顺序也有讲究：时钟必须先于外设配好。如果先初始化串口再改主频，波特率就会按错误的时钟算出来——这也是"改时钟后串口乱码"的根源（见 6.5 节）。

适用于 `STM32F103C8T6 + HSE 8 MHz + PLL x9` 的完整函数为：
=======
`SystemInit()` 只做最基础的系统初始化，此时芯片还跑在复位默认的 HSI 8 MHz 上。`HAL_Init()` 设置 NVIC 分组并把 SysTick 配成 1 ms。真正把主频推到 72 MHz 的是 `SystemClock_Config()`：
>>>>>>> Stashed changes

```c
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

<<<<<<< Updated upstream
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    {
        Error_Handler();
    }

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK |
                                  RCC_CLOCKTYPE_SYSCLK |
                                  RCC_CLOCKTYPE_PCLK1 |
                                  RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
    {
        Error_Handler();
    }
}
```

两个 HAL 调用的职责和寄存器链是：

- `HAL_RCC_OscConfig()` 配置并启动 HSE/PLL，通过 `RCC_CR` 等待就绪，再配置 PLL 源和倍频；
- `HAL_RCC_ClockConfig()` 设置 Flash 等待周期，通过 `RCC_CFGR` 选择 `SYSCLK`、设置 AHB/APB 分频，随后更新 `SystemCoreClock` 和 HAL Tick。

一句话分工：**Osc 管"源和齿轮"（0 到 72 的生产），Clk 管"选挡和分送"（72 的分配），外加 Flash 等待周期。**任一调用返回非 `HAL_OK` 都会进入 `Error_Handler()`。此时 LED 不亮或串口无输出，不一定是下载失败；暂停调试器并查看调用栈，可先区分是振荡器启动失败还是系统时钟切换失败（具体方法见 3.5 节）。

### 3.3 RCC_OscInitTypeDef 逐字段拆解

第一个结构体回答"用哪个源、怎么倍频"。逐字段对照工程 02 的代码：

| 字段 | 工程里的值 | 填的是什么 / 对应硬件 | 填错会怎样 |
| --- | --- | --- | --- |
| `OscillatorType` | `RCC_OSCILLATORTYPE_HSE` | 声明本次要配置哪些振荡器，多个用 `\|` 组合（如 `\|RCC_OSCILLATORTYPE_HSI`） | 漏写哪个源，HAL 就不配置哪个，它保持进入函数前的状态——想让 HSE 参与却漏声明，HSE 根本不会被打开 |
| `HSEState` | `RCC_HSE_ON` | 打开外部晶振，对应 `RCC_CR` 中的 HSE 使能位 | 填 OFF 则实验 02 无从谈起；选了 Bypass 模式而板上是晶振，等不到时钟（见 6.1 节） |
| `HSEPredivValue` | `RCC_HSE_PREDIV_DIV1` | HSE 进 PLL 前的预分频：`/1` 表示 8 MHz 原样进 PLL | 误填 `/2` 则 PLL 输入变 4 MHz，`×9` 只得到 36 MHz，整机主频减半，LED 慢一倍左右 |
| `HSIState` | `RCC_HSI_ON` | 保持片内 8 MHz 开启。芯片复位后本来就靠 HSI 运行，这是 CubeMX 生成的稳妥写法 | 一般无需改动；但若在本次调用里就填 OFF，HAL 会在还没切到 PLL 时先关掉 HSI，而此刻系统仍靠 HSI 运行，程序会当场失时钟挂死——确实要关 HSI，应等切到 PLL 之后另行处理 |
| `PLL.PLLState` | `RCC_PLL_ON` | 打开 PLL | 工程填 `RCC_PLL_NONE` 表示"完全不碰 PLL"（实验 01 就是这么写的）；本工程要 72 MHz 必须填 ON |
| `PLL.PLLSource` | `RCC_PLLSOURCE_HSE` | PLL 的输入 MUX 选 HSE（另一路是 `HSI/2`，精度较差） | 误选 `HSI/2` 得到 4 MHz 输入，`×9` = 36 MHz，同样主频减半且精度降级 |
| `PLL.PLLMUL` | `RCC_PLL_MUL9` | 倍频倍数 M，8 MHz × 9 = 72 MHz | 填小了主频变低（如 `MUL4` = 32 MHz），填出越界组合则 PLL 可能无法锁定 |

实验 01（HSI 工程）的对应写法非常短，正好是"什么都不动"的基线：

```c
RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
RCC_OscInitStruct.HSIState = RCC_HSI_ON;
RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
```

`HSICalibrationValue` 是 HSI 的出厂校准值，`RCC_HSICALIBRATION_DEFAULT` 表示用默认值，初学阶段永远保持默认即可。

最需要记住的是失败路径：**如果板载晶振没焊好、虚焊或没起振，`HSEState = RCC_HSE_ON` 之后 `RCC_CR` 里的就绪标志（HSERDY）永远不会置位，`HAL_RCC_OscConfig()` 等待一段时间后放弃，返回非 `HAL_OK`，程序进入 `Error_Handler()`。**这就是"晶振问题"最终都会表现成"停在 Error_Handler"的原因。

### 3.4 RCC_ClkInitTypeDef 逐字段拆解

第二个结构体回答"时钟选谁、往哪分"。逐字段对照工程 02：

| 字段 | 工程里的值 | 填的是什么 / 对应硬件 | 填错会怎样 |
| --- | --- | --- | --- |
| `ClockType` | SYSCLK、HCLK、PCLK1、PCLK2 四个按位或 | 声明本次要设置哪些时钟节点，没列出的本次不动 | 漏列的节点保持原值，可能不是你想要的挡位；四个全列才能一次配齐总线 |
| `SYSCLKSource` | `RCC_SYSCLKSOURCE_PLLCLK` | 系统 MUX 的挡位：选 PLLCLK 作为 SYSCLK | 漏改或误填 `HSI`，主频停留在 8 MHz——"配置 72 MHz 后 LED 速度不变"的典型原因（见 6.3 节） |
| `AHBCLKDivider` | `RCC_SYSCLK_DIV1` | SYSCLK → HCLK 的分频：/1 得 72 MHz | 填成 DIV2 则全系统降速一半，且 HCLK 变了会连带影响 PCLK1/PCLK2 |
| `APB1CLKDivider` | `RCC_HCLK_DIV2` | HCLK → PCLK1：/2 得 36 MHz，满足 36 上限 | 填成 DIV1 则 PCLK1 = 72 MHz 越界；CubeMX 会直接报错拦下，手写代码绕过则挂在其上的外设时序不可靠 |
| `APB2CLKDivider` | `RCC_HCLK_DIV1` | HCLK → PCLK2：/1 得 72 MHz | 填成 DIV2 则 PCLK2 = 36 MHz，GPIO、SPI1 等跟着变慢（不越界，但与你预期不符） |

第二个参数 `FLASH_LATENCY_2` 是 `HAL_RCC_ClockConfig()` 的独立入参，不装在结构体里：它按 2.3 节的边界表设定 Flash 等待周期。实验 02 跑 72 MHz 填 `_2`，实验 01 跑 8 MHz 填 `_0`（工程代码分别如此）。频率改了却忘记同步改它，是"超频后程序跑飞"的常见原因。

对照实验 01（HSI 工程）的 Clk 部分，差异一目了然：

```c
RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;   /* MUX 选 HSI */
RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
/* 8 MHz <= 24 MHz，Flash 用 0 等待周期 */
if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
```

两个工程放在一起读，你会发现"配时钟"的全部内容就是：**Osc 结构体决定 8 从哪来、72 怎么造；Clk 结构体决定 72 怎么分给三条总线；外加一个 Flash 等待周期参数保证 CPU 读得过来。**

### 3.5 Error_Handler 到底做了什么

配套工程的 `Error_Handler()` 全文只有几行（两个工程相同）：

```c
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
```

行为拆解：

- `__disable_irq()` 关闭所有中断，SysTick 也在内——从此 `HAL_GetTick()` 不再增长；
- `while (1)` 原地死循环，没有任何 LED 提示、没有串口打印，从外面看就是"程序死了"。

从主流程看现象：`SystemClock_Config()` 在 `MX_GPIO_Init()` **之前**执行，所以一旦时钟配置失败，PC13 还没被初始化、主循环更没开始——你看到的不是"LED 乱闪"，而是"LED 从头到尾没闪过"（引脚停留在复位默认态，是否微亮取决于板上电路），和下载失败、GPIO 配错的表现极其相似。区分手段：

1. 调试器全速运行时按暂停（Halt），看调用栈停在谁里面：停在 `HAL_RCC_OscConfig` → `Error_Handler()`，说明振荡器（多半是 HSE 没就绪）环节失败；停在 `HAL_RCC_ClockConfig` → 说明切换或分频环节失败；
2. 也可以直接在 `Error_Handler()` 的 `while (1)` 里打断点，命中即说明配置阶段出了错；
3. 快速对照法：先烧实验 01（HSI 工程）。它能正常闪，说明下载链路、GPIO、LED 都没问题，问题被压缩到 HSE/PLL 一小段。

还有一个"隐形演员"要认识：`stm32f1xx_hal_conf.h` 中的 `#define HSE_VALUE 8000000U`。HAL 后面所有频率推算都拿它当"晶振实际频率"使用——它只是个假设值，HAL 没有能力测量真晶振。换用非 8 MHz 晶振的板子而忘了改这个宏，软件读数会"集体说谎"（详见 6.4 节）。

## 4. 最小实验：比较 8 MHz 与 72 MHz

### 4.1 LED 接线与程序

以常见 `PC13` 低电平点亮的开发板为例，实际有效电平仍以原理图为准。在 CubeMX 中把 `PC13` 配置为 GPIO Output，并将初始电平设为 LED 熄灭；保留 `Serial Wire` 调试口。两组实验使用同一段 `main()`，只改变 CubeMX 生成的 `SystemClock_Config()`——因此两个子工程（`01_HSI_8MHz`、`02_PLL_72MHz`）是两个独立工程。

配套工程的实际代码如下（`i` 放在 `USER CODE BEGIN PV` 区域作全局变量，主循环写在 `USER CODE WHILE/3` 之间；`MX_GPIO_Init()` 把 PC13 配成开漏输出 `GPIO_MODE_OUTPUT_OD`、初始电平 `GPIO_PIN_SET` 即高电平熄灭，并把初始输出写在 `HAL_GPIO_Init()` 之前）：
=======
  /* 打开 HSE，PLL 以 HSE 为输入，倍频 ×9 */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState       = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.PLL.PLLState   = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource  = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL     = RCC_PLL_MUL9;
  HAL_RCC_OscConfig(&RCC_OscInitStruct);

  /* SYSCLK 走 PLLCLK，AHB /1、APB1 /2、APB2 /1 */
  RCC_ClkInitStruct.ClockType      = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                   | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider  = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
  HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2);
}
```

第一段 `HAL_RCC_OscConfig()` 打开晶振、把 PLL 挂到 HSE 上并设置倍频，等 PLL 锁定。第二段 `HAL_RCC_ClockConfig()` 切换系统时钟源、设置分频，同时按新的 HCLK 重配 SysTick 和 Flash 等待周期。CubeMX 生成的代码还会检查返回值，失败就进 `Error_Handler()`，所以配置错误的表现通常是停在启动阶段，而不是跑飞。

时钟必须先于外设初始化。先初始化串口再改主频，波特率就会按错误的时钟算出来。

## 4. 实验：比较 8 MHz 与 72 MHz

接线只需要最小系统板和 ST-LINK，`PC13` 配成 GPIO 输出，保留 `Serial Wire`。对照组不启用 HSE 和 PLL，SYSCLK 停在 HSI 8 MHz；实验组用上一节的 72 MHz 配置。
>>>>>>> Stashed changes

```c
/* USER CODE BEGIN PV */
volatile uint32_t i;
/* USER CODE END PV */

int main(void)
{
  HAL_Init();
  SystemClock_Config();
  MX_GPIO_Init();

  while (1)
  {
    HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
    for (i = 0U; i < 1000000U; i++)
    {
    }
  }
}
```

<<<<<<< Updated upstream
实验链路如下：

```text
输入：同一段 main() + 两份不同的 SystemClock_Config()
      01_HSI_8MHz：HSI 直连，全 /1，FLASH_LATENCY_0（8 MHz）
      02_PLL_72MHz：HSE ×9，APB1 /2，FLASH_LATENCY_2（72 MHz）
处理：CPU 按当前主频逐条执行 1000000 次空循环，每圈翻转一次 PC13
输出：PC13 方波 → 板载 LED 亮灭交替
预期：72 MHz 工程的 LED 闪烁明显更快
```

为什么不继续用第 0 章的 `HAL_Delay(500)`？因为 SysTick 的装载值随 `SystemCoreClock` 自适应（2.3 节）：主频变成 9 倍，装载值也变成 9 倍，`HAL_Delay(500)` 在两个工程里都是精确的 500 ms——它太"正确"了，反而测不出主频差异。空循环的耗时才与 CPU 取指执行的速度直接挂钩，所以这里故意退回最"笨"的延时。

`volatile` 防止循环计数被当作无用代码删除，但循环时间仍受编译器、优化等级和 Flash 等待周期影响，因此这里只做定性比较。

### 4.2 预期现象与定量核对

HSI 配置下，复位后的典型主频为：

$$
f_{\mathrm{SYSCLK}}=f_{\mathrm{HSI}}=8\,\mathrm{MHz},\qquad
f_{\mathrm{HCLK}}=8/1=8\,\mathrm{MHz}
$$

HSE+PLL 配置下：

$$
f_{\mathrm{SYSCLK}}=8\times 9=72\,\mathrm{MHz}
$$

$$
f_{\mathrm{HCLK}}=72/1=72\,\mathrm{MHz},\qquad
f_{\mathrm{PCLK1}}=72/2=36\,\mathrm{MHz},\qquad
f_{\mathrm{PCLK2}}=72/1=72\,\mathrm{MHz}
$$

保持循环次数不变时，LED 在 `72 MHz` 下应明显变快；理想比例约为原来的 `1/9`，实测不必严格等于该值。定性观察方法：各数 10 秒内的闪烁次数，02 工程应约为 01 工程的 9 倍上下。"LED 变快"只能说明执行速度发生变化，不能单独证明 PLL 已经锁定。

"如果看到 X，说明 Y"对照表：

| 你看到的现象 | 说明 |
| --- | --- |
| 两个工程 LED 快慢几乎一样 | SYSCLK 很可能没切到 PLL，走 6.3 节 |
| 01 能闪、02 完全不闪 | 02 大概率停在 `Error_Handler()`，走 6.1 节 |
| 02 反而明显变慢 | PLL 参数填小了（PREDIV 误填 `/2` 或 MUL 不是 `x9`），走 3.3 节核对 |
| 01 也不闪 | 先排除下载和 GPIO 问题，走 6.2 节 |

### 4.3 用调试器读回频率，与 MCO 独立测量

先加入以下变量和赋值，在调试器 Watch 窗口观察。变量定义放在 `main()` 之前的 `USER CODE BEGIN 0` 区域，赋值语句放进主循环开头：

```c
static volatile uint32_t g_hclk_khz = 0U;

/* 放入主循环中 */
g_hclk_khz = HAL_RCC_GetHCLKFreq() / 1000U;
```

```c
uint32_t sysclk = HAL_RCC_GetSysClockFreq();
uint32_t hclk   = HAL_RCC_GetHCLKFreq();
uint32_t pclk1  = HAL_RCC_GetPCLK1Freq();
uint32_t pclk2  = HAL_RCC_GetPCLK2Freq();
```

生成代码、编译并下载后，先在 Watch 窗口核对：HSI 实验应读到 `g_hclk_khz=8000`，72 MHz 实验应读到 `72000`。这些 HAL 函数根据当前配置和 `HSE_VALUE` 等常量推算频率，只能证明软件认为的时钟链正确，不能发现板载晶振频率填写错误。往底层看一层就明白了：`HAL_RCC_GetHCLKFreq()` 直接返回全局变量 `SystemCoreClock`（HAL 源码中就是 `return SystemCoreClock;`），而这个变量在 `system_stm32f1xx.c` 里的复位初值是 `8000000`，由 `SystemClock_Config()` 成功后按配置链更新——所以它读到的是"软件账本"，不是真实波形。

需要独立测量时，在 CubeMX 中把空闲的 `PA8` 配置为 `MCO`：

- 选择 `SYSCLK`，带宽足够时应测到约 `72 MHz`；
- 选择 `PLLCLK` 时，STM32F103 的该路径固定输出 `PLLCLK/2`，应测到约 `36 MHz`；
- STM32F1 没有任意 `/8` 的 MCO 分频，不能照搬其他系列选项。

MCO 能提供实际波形证据，但 `36 MHz` 只证明 PLL 约为 `72 MHz`；是否为 SYSCLK 还要结合 `RCC_CFGR.SWS`（状态寄存器中指示"当前系统时钟源"的两位）或软件配置判断。

## 5. 本章验收

- [ ] 能画出 HSI/HSE 到 SYSCLK、AHB、APB 的路径；
- [ ] 8 MHz 和 72 MHz 两个工程的 `HAL_RCC_Get*Freq()` 读数已记录；
- [ ] Flash latency 和 APB 定时器倍率已核对；
- [ ] 调试器能进入 `SystemClock_Config()` 和主循环；
- [ ] 能区分时钟配置失败、GPIO 问题和下载问题；
- [ ] 能说出 `Error_Handler()` 的实际行为（关中断 + 死循环）以及为什么此时 LED 不会闪。

## 6. 根据现象定位时钟故障

先用一张速查表建立索引，每一行在后面的小节里展开成"症状 → 可能原因 → 具体检查步骤"：

| 现象 | 优先检查 | 判断依据 |
| --- | --- | --- |
| 停在 `Error_Handler()` | HSE 晶振是否焊接、模式是否为 Crystal、HSE 实际频率、PLL 参数 | 判断故障发生在 `HAL_RCC_OscConfig()` 还是 `HAL_RCC_ClockConfig()` |
| 下载后 LED 完全不工作 | `SystemClock_Config()` 是否调用、GPIO 时钟和 `MX_GPIO_Init()` 是否执行 | 沿 `RCC -> GPIO 时钟 -> PC13` 逐级检查 |
| 配置 `72 MHz` 后 LED 速度不变 | SYSCLK 是否真正切到 `PLLCLK`，HSE/PLL 是否返回 `HAL_OK` | Watch 中 `HCLK` 若仍为 `8000`，软件时钟链未切换成功 |
| HAL 读数为 `72000`，MCO 频率异常 | `HSE_VALUE`、MCO 源、探头和仪器带宽 | HAL getter 使用配置常量，MCO 使用真实引脚波形 |
| 串口波特率、PWM 或 `HAL_Delay()` 异常 | HCLK、PCLK、定时器 `x2` 规则和 Flash latency | 同一外设可能使用总线时钟或专用时钟，不能只看 PCLK |
| ADC 采样过快或结果异常 | ADC 预分频和 `14 MHz` 上限 | `PCLK2` 还要继续经过 ADC 专用分频 |

### 6.1 症状一：停在 Error_Handler()（多半是 HSE 启动失败）

- **症状**：下载成功、复位后 LED 一直不闪；调试器暂停后发现程序停在 `Error_Handler()` 的 `while (1)` 里，且中断已被关闭。
- **可能原因**：
  1. 板载晶振没焊好、虚焊或损坏，HSERDY 永远不置位，`HAL_RCC_OscConfig()` 超时返回错误；
  2. CubeMX 里 HSE 误选了 `Bypass Clock Source`，芯片在等一个不存在的方波；
  3. PLL 参数填出越界组合，PLL 无法锁定；
  4. `HAL_RCC_ClockConfig()` 环节的分频或 Flash latency 参数非法。
- **具体检查步骤**：
  1. 暂停后看调用栈，确认停在 `HAL_RCC_OscConfig` 还是 `HAL_RCC_ClockConfig`，先二分故障范围；
  2. 若在 Osc 环节：目视检查晶振焊接；打开 `.ioc` 确认 HSE 是 `Crystal/Ceramic Resonator`（配套 02 工程中 `PD0/PD1` 应为 `RCC_OSC_IN/RCC_OSC_OUT`）；核对 PLLMul 与 PREDIV；
  3. 若在 Clk 环节：逐项对照 3.4 节的字段表，重点查 `FLASH_LATENCY` 是否与目标频率匹配；
  4. 用实验 01 做对照：HSI 工程能跑，就把故障锁定在 HSE/PLL 一段。

### 6.2 症状二：下载成功但 LED 完全不工作

- **症状**：程序"像没跑一样"，任何工程都一样，换回第 0 章模板却能闪。
- **可能原因**：`SystemClock_Config()` 或 `MX_GPIO_Init()` 没被调用；GPIOC 时钟没开；PC13 模式配错；LED 接线与有效电平不符。
- **具体检查步骤**：
  1. 沿 `RCC -> GPIO 时钟 -> PC13` 逐级检查：`SystemClock_Config()` 是否成功返回（调试器单步）；`MX_GPIO_Init()` 里的 `__HAL_RCC_GPIOC_CLK_ENABLE()` 是否还在（配套工程把它生成在 `HAL_GPIO_Init()` 之前）；
  2. Watch 窗口观察 `HAL_GetTick()` 是否增长：在增长说明 SysTick 和主流程都活着，问题在 GPIO 侧；不增长说明程序没跑到这里或已进 `Error_Handler()`，回到 6.1；
  3. 确认 PC13 的输出模式（配套工程为开漏 `GPIO_MODE_OUTPUT_OD`、初始 `GPIO_PIN_SET` 熄灭）与板上 LED 电路匹配。

### 6.3 症状三：配置 72 MHz 后 LED 速度不变

- **症状**：02 工程烧进去，闪烁快慢和 01 工程没区别。
- **可能原因**：`SYSCLKSource` 没有真正切到 PLLCLK；PLL 参数填小但没到失败程度；烧错了 `.elf`（把 01 当成 02 烧了）。
- **具体检查步骤**：
  1. 在 Watch 窗口加 4.3 节的频率变量：若 `HCLK` 读数仍是 `8000`，说明软件时钟链没有切换成功，回到 `SystemClock_Config()` 检查；
  2. 对照 02 工程 `main.c`，确认 `OscillatorType` 含 HSE、`PLLState` 为 ON、`SYSCLKSource` 为 `RCC_SYSCLKSOURCE_PLLCLK`、`APB1CLKDivider` 为 `RCC_HCLK_DIV2`；
  3. 确认编译输出路径里的 `.elf` 确实来自 02 工程，再下载一次。

### 6.4 症状四：HAL 读数 72000，但 MCO 波形对不上

- **症状**：软件账本说 72 MHz，示波器在 PA8 上测到的却不是 72/36 MHz。
- **可能原因**：`HSE_VALUE` 与板载晶振实际频率不符（getter 全靠它推算）；MCO 源选错（想测 SYSCLK 却选了 PLLCLK，差一个固定的 `/2`）；示波器探头或带宽不足。
- **具体检查步骤**：
  1. 打开 `stm32f1xx_hal_conf.h` 核对 `#define HSE_VALUE 8000000U` 是否与板上晶振一致——不一致时 HAL 读数全部作废，这是"软件说谎"最常见的形式；
  2. 核对 MCO 输出源：选 `SYSCLK` 期待约 72 MHz，选 `PLLCLK` 则固定输出一半约 36 MHz；
  3. 检查示波器探头衰减比设置和带宽：设置不当会把高频方波测低、测变形，读数不可信。

### 6.5 症状五：改时钟后串口乱码、PWM 变快变慢或 HAL_Delay 不准

- **症状**：时钟配置"成功"了，但某个外设的行为从此不对：串口一串乱码、舵机角度异常、`HAL_Delay(1000)` 明显不止 1 秒。
- **可能原因**：波特率、PWM 频率、SysTick 装载值都是在时钟链确定后按"当时认为的频率"算出来的；改了时钟链而外设参数没跟着重算，比例就错了。定时器还要叠加 `x2` 规则。
- **具体检查步骤**：
  1. 先用 4.3 节的 getter 记下新的 `SYSCLK/HCLK/PCLK1/PCLK2`，一切推算以这些值为准；
  2. 串口乱码：确认波特率计算使用的时钟源（USART1 在 PCLK2，USART2/3 在 PCLK1），再核对分频结果是否仍等于目标波特率；
  3. PWM/定时异常：按 2.3 节的 `x2` 规则重算定时器输入时钟（APB1 分频大于 1 时 TIM2~TIM4 输入为 72 MHz）；
  4. `HAL_Delay()` 不准：它依赖 SysTick，而 SysTick 装载值来自 `SystemCoreClock`——若程序绕过了 `HAL_RCC_ClockConfig()` 手动改寄存器，`SystemCoreClock` 与真实 HCLK 脱节，延时全体失真。始终走 HAL 的时钟配置路径，让 HAL 自己同步这笔账。

### 6.6 症状六：HAL_Delay 卡死不返回（SysTick 不走）

- **症状**：程序停在 `HAL_Delay()` 里不再前进；或者 Watch 里 HAL 的毫秒计数 `uwTick`（`stm32f1xx_hal.c` 中定义，`HAL_GetTick()` 返回的就是它）纹丝不动。
- **可能原因**：SysTick 中断没有被响应——中断被 `__disable_irq()` 关闭（`Error_Handler()` 就这么干，之后任何依赖 Tick 的代码都会卡死）；SysTick 配置在时钟切换后没有同步更新。
- **具体检查步骤**：
  1. 全局搜索代码里有没有自己调用过 `__disable_irq()` 且没有对应的 `__enable_irq()`；
  2. Watch 观察 `uwTick`：不增长而程序没停在 `Error_Handler()`，检查 SysTick 的中断使能与优先级配置；
  3. 走正规流程：`HAL_Init()` 会先按 `SystemCoreClock` 复位初值 8000000 把 SysTick 配成 1 ms，`HAL_RCC_ClockConfig()` 成功后再按新 HCLK 重配——只要不绕过这两个函数，这笔账不会乱。
=======
`volatile` 防止编译器把空循环优化掉。循环时间还受优化等级和 Flash 等待周期影响，所以这个实验只做定性比较：同样一百万次计数，72 MHz 下 LED 闪烁应明显快于 8 MHz，理想比值约 9 倍，快一个量级就算对。

LED 变快只能说明执行速度变了，不能证明 PLL 已锁定。要拿到硬证据，就把时钟输出到 `PA8` 的 MCO 引脚测量：

```c
HAL_RCC_MCOConfig(RCC_MCO1, RCC_MCO1SOURCE_PLLCLK, RCC_MCODIV_1);
```

F1 的 `RCC_MCO1SOURCE_PLLCLK` 输出的是 PLL/2，本章配置下预期约 36 MHz。测不到时，先确认 `PA8` 已配成 MCO、探头带宽足够，再切到 `RCC_MCO1SOURCE_HSE` 看 8 MHz 晶振是否起振。也可以用 `HAL_RCC_GetSysClockFreq()` 读配置推算值，但它不能替代实际测量。用完记得关闭 MCO，把 `PA8` 还给原来的功能。

这套 72 MHz / 36 MHz / 12 MHz 的分配也是后面定时器、ADC 和串口计算的共同基准。倒立摆工程沿用同一棵时钟树（HSE 8 MHz ×9，APB1 二分频，ADC 六分频），其引脚与总线表见 [[STM32倒立摆/03 基础驱动：CubeMX与HAL库实现#1.4 本工程的引脚与外设总表]]。
>>>>>>> Stashed changes

上一篇：[[02 OLED 调试：I2C 显示数据流]] ｜ 下一篇：[[04 中断系统：EXTI 与 NVIC 优先级]]
