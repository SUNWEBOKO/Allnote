# 03 时钟系统：时钟树、PLL 与 HAL 配置
上一篇：[[02 OLED 调试：I2C 显示数据流]] ｜ 下一篇：[[04 中断系统：EXTI 与 NVIC 优先级]]

## 学习目标与前置知识

读完本章，应能完成以下闭环：

- 解释时钟信号为什么是 MCU 正常工作的基础；
- 从时钟树中找出 HSI、HSE、PLL、SYSCLK、HCLK、PCLK1、PCLK2 以及 RTC/IWDG 等分支；
- 根据目标频率计算 PLL、AHB、APB 分频参数，并检查总线和外设上限；
- 使用 CubeMX/HAL 将 STM32F103 从默认约 `8 MHz` 配置到常用的 `72 MHz`；
- 用 LED、HAL 频率读取函数或 MCO 验证实际时钟，并按信号链排查异常。

默认对象是常见的 STM32F103C8T6 最小系统板。不同型号的时钟源、频率上限、外设挂载位置和 PLL 选项可能不同，实际工程必须以对应数据手册、参考手册和板卡原理图为准。

## 1. 为什么单片机必须有时钟

### 1.1 从逻辑电路到时序逻辑

组合逻辑电路的输出只由当前输入决定；寄存器、计数器、状态机等时序逻辑还需要保存“过去的状态”。如果内部各级门电路的传播延时不同，输入变化后会出现短暂的中间状态。若寄存器在这段时间采样，就可能把错误结果写入状态。

时钟信号是一列周期性方波。边沿触发器只在指定边沿采样，给组合逻辑留下一个完整周期完成传播和稳定。因此，时钟不是“让代码变快的开关”这么简单，而是协调 CPU、存储器、总线和外设状态更新的统一节拍。

在系统层面，串口需要稳定的波特率，定时器需要准确的计数步长，ADC 需要满足采样时钟范围，USB 需要专用的 `48 MHz` 时钟。它们都依赖时钟树提供可计算、可分配的脉冲。

### 1.2 时钟门控与节能

总线有时钟，不等于每个外设都已获得时钟。RCC 中的外设时钟使能位相当于门控开关：

```text
SYSCLK -> AHB/APB 分频 -> PCLKx -> 外设时钟门控 -> 外设寄存器和状态机
```

例如 `PCLK2 = 72 MHz` 时，若没有执行 `__HAL_RCC_GPIOC_CLK_ENABLE()`，GPIOC 仍不能正常访问。关闭未使用外设的门控还能降低动态功耗。

## 2. 先建立“时钟树地图”

![STM32F1 时钟树总览](<image/Pasted image 20260727154625.png>)

阅读时钟树建议遵循“树根 → 树干 → 树枝 → 树叶”的顺序：

1. **树根：时钟源**，产生原始振荡信号；
2. **树干：PLL 与系统时钟选择**，把输入选择、倍频和切换组合成 `SYSCLK`；
3. **树枝：AHB/APB 分频器**，把系统时钟分配给不同总线；
4. **树叶：CPU、存储器、DMA、GPIO、串口、定时器、ADC、USB、RTC 等具体模块**。

主干可以概括为：

```text
HSI/HSE -> PLL/系统时钟选择 -> SYSCLK -> AHB -> HCLK -> APB1/APB2 -> PCLK1/PCLK2
```

STM32F1 的学习主线还有一棵低速树，主要服务 RTC、独立看门狗等模块。

## 3. 四类时钟源

| 缩写 | 含义 | 常见来源 | 优点 | 局限与典型用途 |
| --- | --- | --- | --- | --- |
| `HSI` | High-Speed Internal | 片内 RC，F103 常见 `8 MHz` | 不需外部器件、启动简单 | 精度通常低于晶振，适合作为默认或备用源 |
| `HSE` | High-Speed External | 外部晶振或外部时钟输入 | 频率精度较高，适合系统主频和通信 | 需要外部硬件；晶振与旁路模式不能混选 |
| `LSI` | Low-Speed Internal | 片内低速 RC | 成本低、可独立运行 | 精度较低，常给 IWDG 或 RTC 备选 |
| `LSE` | Low-Speed External | 常见 `32.768 kHz` 晶振 | 精度高，可由后备电源维持 RTC | 需要晶振和匹配电路，启动时间较长 |

命名规律是：`HS/LS` 表示高速/低速，`I/E` 表示内部/外部。内部 RC 不需要外接器件但精度一般；外部晶振增加硬件成本却能提供更稳定的频率。

### 3.1 HSE 的晶振模式与旁路模式

- **Crystal/Ceramic Resonator**：芯片通过振荡电路驱动外部晶振。最小系统板上常见的 `8 MHz` 石英晶振应选此项；
- **Bypass Clock Source**：外部已经有一个完整的时钟波形，直接从 HSE 输入脚送入芯片。它不是“普通晶振”的另一种叫法。

模式选错时，HSE 可能无法就绪，随后 PLL 锁定和系统时钟切换都会失败。

## 4. PLL、SYSCLK 与总线频率

### 4.1 PLL 是频率变换器

STM32F1 的 PLL 输入常见为 `HSI/2`、`HSE` 或 `HSE/2`，再乘以芯片允许的倍频系数。对 F103，可用下面的抽象公式理解：

$$PLL\_CLK = PLL\_Input \times PLL\_Mul$$

`SYSCLK` 有三种典型来源：`HSI`、`HSE` 或 `PLLCLK`。配置时本质上是在做“选路、乘法、除法”。

**例 1：从 HSE 得到 `24 MHz`**

若外部晶振 `HSE = 8 MHz`，PLL 输入选择 `HSE/2 = 4 MHz`，再选择 `PLL x6`：

$$SYSCLK = 8/2 \times 6 = 24\,\text{MHz}$$

**PLL 输出必须落在数据手册规定的范围内（F103 常见约 `16~72 MHz`，务必以手中型号的数据手册为准），低于下限可能无法锁定。** 例如用同样的前级 `/2` 配 `PLL x3` 只能得到 `12 MHz`，低于常见下限、可能失锁，只适合用来理解“前级分频”这一步，不要照此配置。

**例 2：从 HSE 得到 `72 MHz`**

若外部晶振 `HSE = 8 MHz`，选择 `HSE` 作为 PLL 输入并设置 `x9`：

$$SYSCLK = 8 \times 9 = 72\,\text{MHz}$$

### 4.2 AHB、APB1、APB2

`SYSCLK` 经过 AHB 分频得到 `HCLK`，再由两个 APB 分频器得到 `PCLK1` 和 `PCLK2`：

$$HCLK = \frac{SYSCLK}{AHB\_Prescaler}$$

$$PCLK1 = \frac{HCLK}{APB1\_Prescaler},\qquad PCLK2 = \frac{HCLK}{APB2\_Prescaler}$$

STM32F103 常见上限如下：

| 节点 | 对应结构 | 常见上限 | 典型对象 |
| --- | --- | ---: | --- |
| `HCLK` | AHB | `72 MHz` | Cortex-M3、Flash、SRAM、DMA |
| `PCLK1` | APB1 | `36 MHz` | USART2/3、I2C、CAN、TIM2~TIM4 等 |
| `PCLK2` | APB2 | `72 MHz` | GPIO、ADC、USART1、SPI1、高级定时器（`TIM1`） |

上表按 `STM32F103C8T6` 列出。它属于中容量产品，定时器只有 `TIM1~TIM4`（`TIM1` 是挂在 APB2 上的高级定时器，`TIM2~TIM4` 挂在 APB1 上）；容量更大的 F103 型号还会有 `TIM5~TIM7`，请以手中具体型号的数据手册/参考手册为准。

常用满速组合为：

```text
HSE = 8 MHz
PLL = HSE x 9 = 72 MHz
SYSCLK = 72 MHz
AHB  = /1 -> HCLK  = 72 MHz
APB1 = /2 -> PCLK1 = 36 MHz
APB2 = /1 -> PCLK2 = 72 MHz
```

APB1 不能在 F103 的 `72 MHz` 主频下直接取 `72 MHz`；`/2` 是满足 `36 MHz` 上限的必要设置。

### 4.3 APB 定时器的“×2”规则

当 APB 预分频系数为 `1` 时，定时器时钟等于 `PCLKx`；当 APB 预分频系数大于 `1` 时，F1 定时器时钟通常自动变为 `2 × PCLKx`：

```text
APB1 = /2, PCLK1 = 36 MHz -> TIM2~TIM4 时钟通常为 72 MHz（定时器资源以具体型号手册为准）
APB2 = /1, PCLK2 = 72 MHz -> APB2 定时器时钟为 72 MHz
```

因此，计算 PWM 或定时器中断频率时不能只看 `PCLK1/PCLK2`。

### 4.4 SysTick、ADC、USB 与低速分支

- **SysTick**：HAL 的 `HAL_Delay()` 和 HAL Tick 依赖它。系统时钟切换后，`HAL_RCC_ClockConfig()` 会按新的 `HCLK` 更新节拍配置。
- **ADC**：通常由 `PCLK2` 再分频。若 `PCLK2 = 72 MHz`，选择 `/6` 得到 `12 MHz`，选择 `/8` 得到 `9 MHz`；`/2`、`/4` 会超过 F103 常见的 `14 MHz` 上限。
- **USB**：需要精确的 `48 MHz`，常由 PLL 输出再经专用分频得到。是否可用及分频选项必须核对具体型号。
- **RTC**：可选 `LSE`、`LSI` 或 `HSE/128`。`32.768 kHz` 的 LSE 经 `32768` 分频可得到 `1 Hz`；LSE 精度高且适合后备域，LSI 成本低但误差较大。
- **IWDG**：通常来自 LSI，不依赖主系统高速时钟，因此主时钟异常时仍可复位系统。
- **Flash 等待周期**：主频升高时必须增加等待周期。F103 常见范围是 `0~24 MHz` 为 `0` 个、`24~48 MHz` 为 `1` 个、`48~72 MHz` 为 `2` 个；以芯片手册为准。

## 5. HAL/CubeMX 的配置链

### 5.1 配置顺序

```text
选择 HSI/HSE -> 配置 PLL -> 选择 SYSCLK
-> 配置 AHB/APB 分频 -> 设置 Flash 等待周期
-> HAL_RCC_OscConfig() -> HAL_RCC_ClockConfig()
-> 更新 SystemCoreClock 和 SysTick -> 初始化外设
```

启动调用关系通常是：

```text
Reset_Handler -> SystemInit() -> C 运行库 -> main()
              -> HAL_Init() -> SystemClock_Config() -> MX_xxx_Init()
```

不要因为看到 `SystemInit()` 就认定系统已经是 `72 MHz`。不同模板可能在 `SystemInit()` 中只复位 RCC，也可能预配置部分时钟；应以启动文件、`system_stm32f1xx.c` 和 `SystemClock_Config()` 的实际内容为准。

### 5.2 生成代码的两个关键调用

```c
if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
{
    /* HSE/PLL 未就绪时不要继续切换系统时钟。 */
    Error_Handler();
}

if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
{
    /* Flash 等待周期必须与目标主频匹配。 */
    Error_Handler();
}
```

`HAL_RCC_OscConfig()` 负责启动 HSI/HSE/PLL 并等待就绪；`HAL_RCC_ClockConfig()` 负责选择系统时钟、设置 AHB/APB 分频和 Flash 等待周期。返回 `HAL_ERROR` 时，优先检查振荡器模式、晶振频率、PLL 参数和供电条件。

时钟配置失败时的现场症状很容易被误判：`HAL_RCC_OscConfig()` / `HAL_RCC_ClockConfig()` 返回非 `HAL_OK` 后会调用 `Error_Handler()`，而它内部的 `while (1)` 会一直停在那里。**表现为板子像死机——LED 不闪、串口无输出，看起来很像“程序没下载进去”。** 排查动作是用调试器暂停（Pause），看程序计数器或调用栈是否停在 `Error_Handler`；如果是，问题在时钟源或 PLL 参数，而不在下载链路。若因为时钟配错已经连不上调试口，恢复思路见第 01 章“下载失败、调试接口被锁死”一节。

外设门控则由对应宏完成：

```c
__HAL_RCC_GPIOC_CLK_ENABLE();  /* GPIOC：APB2 */
__HAL_RCC_TIM2_CLK_ENABLE();   /* TIM2：APB1 */
__HAL_RCC_DMA1_CLK_ENABLE();   /* DMA1：AHB  */
```

门控只决定“时钟是否送达”，不会改变总线频率。

### 5.3 运行时读取与独立测量

```c
uint32_t sysclk = HAL_RCC_GetSysClockFreq();
uint32_t hclk   = HAL_RCC_GetHCLKFreq();
uint32_t pclk1  = HAL_RCC_GetPCLK1Freq();
uint32_t pclk2  = HAL_RCC_GetPCLK2Freq();
```

这些函数可在调试器、串口或 OLED 上输出。下面给出两种不依赖串口和 OLED 就能落地的验证方法。

**方法一：调试器看变量（不需要任何外设和仪器）**

在 `main.c` 的文件作用域声明一个全局变量，`volatile` 用来防止编译器把“看起来没被读的赋值”优化掉：

```c
/* 放在 main.c 的 USER CODE BEGIN PV 区域（main() 函数之外）。 */
static volatile uint32_t g_hclk_khz = 0U;
```

在 `main()` 已有的循环体内周期性写入：

```c
while (1)
{
    /* USER CODE BEGIN 3 */
    g_hclk_khz = HAL_RCC_GetHCLKFreq() / 1000U;
    /* USER CODE END 3 */
}
```

编译下载后，在 Keil 中进入调试（`Debug -> Start/Stop Debug Session`），全速运行一段再按暂停，把 `g_hclk_khz` 加到 `Watch 1` 窗口观察：

- 配置成 `72 MHz` 时应显示 `72000`；
- 实验一的默认 `HSI` 配置（`8 MHz`）时应显示 `8000`。

这个判据只依赖调试器，不需要示波器，建议作为本章的默认验收方式。

**方法二：MCO 输出到 `PA8`，用示波器或频率计实测**

CubeMX 侧的操作路径：

1. 在 `Clock Configuration` 页或 `Pinout & Configuration -> RCC` 的高级参数中启用 `Master Clock Output`（MCO）；
2. `MCO` 的时钟源选择 `SYSCLK`；
3. MCO 预分频先设为 `1`（不分频）；
4. 生成代码，MCO 会输出到 `PA8`（CubeMX 会在引脚图上标出 MCO 对应引脚，若 `PA8` 已被其他功能占用需先释放）。

判据：用示波器或逻辑分析仪在 `PA8` 上测量，`72 MHz` 配置下应测到接近 `72 MHz` 的方波（预分频 `1`）。没有示波器时可先把预分频设大（例如 `/8`，得到约 `9 MHz`），再用频率计测量，这样也能避开探头带宽不足导致的读数偏低。MCO 的可选源和分频以具体芯片手册为准。

CSS（Clock Security System）可监测 HSE 故障；当工程使用 HSE 或 PLL(HSE) 时，可按芯片支持情况开启 CSS，并在故障回调中执行降级、记录或安全停机。

## 6. 实验一：默认 `8 MHz` 驱动 LED

### 6.1 目标与配置

实验目的不是制作精确延时，而是观察同一段代码在不同主频下的执行速度。

以常见 PC13 低电平点亮的开发板为例：

1. 新建 `STM32F103C8T6` 工程；
2. `System Core -> SYS -> Debug` 选择 `Serial Wire`；
3. 将 `PC13` 配置为 GPIO 输出，初始电平置为 LED 熄灭状态；
4. 若板卡为低电平点亮，可使用开漏输出；若硬件接法不同，应按原理图选择推挽或有效电平。

### 6.2 程序与数据流

```c
uint32_t i;

while (1)
{
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
    for (i = 0; i < 1000000; i++)
    {
    }

    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
    for (i = 0; i < 1000000; i++)
    {
    }
}
```

默认状态通常是 `HSI -> SYSCLK`，且 `AHB /1`：

$$SYSCLK = HSI = 8\,\text{MHz},\qquad HCLK = 8/1 = 8\,\text{MHz}$$

信号链为：`HCLK -> Cortex-M3 执行空循环 -> GPIOC 输出翻转 -> LED 亮灭`。在关闭编译优化时，100 万次循环通常接近秒级，但实际周期受流水线、编译器和指令实现影响，不能替代定时器或 `HAL_Delay()`。

## 7. 实验二：配置 `72 MHz` 并对比

### 7.1 CubeMX 操作

1. 在 `Pinout & Configuration -> RCC` 中启用 HSE；有外部晶振时选择 `Crystal/Ceramic Resonator`，不要选 Bypass；
2. 在 `Clock Configuration` 中确认 `HSE = 8 MHz`；
3. 设置 `PLL Source = HSE`、HSE 预分频 `/1`、`PLL Mul = x9`；
4. 将 `System Clock Mux` 选择为 `PLLCLK`；
5. 设置 `AHB = /1`、`APB1 = /2`、`APB2 = /1`；
6. 生成代码并检查 `SystemClock_Config()`，确认 Flash 等待周期为适合 `72 MHz` 的值。

### 7.2 计算与验收

$$PLL\_CLK = 8 \times 9 = 72\,\text{MHz}$$

$$HCLK = 72/1 = 72\,\text{MHz}$$

$$PCLK1 = 72/2 = 36\,\text{MHz},\qquad PCLK2 = 72/1 = 72\,\text{MHz}$$

下载与实验一相同的 LED 程序。空循环数量不变而 `HCLK` 提高后，LED 应明显变快，理想情况下执行时间约缩短到原来的 `1/9`；实测不会严格等于该比例，因为循环指令、等待周期和测量方式都会影响结果。**“LED 变快”只是定性现象，不能证明时钟真的切到了 `72 MHz`，请用下面两个定量判据之一验收（方法细节见 5.3 节）：**

- **方法一（调试器看变量）**：按 5.3 节方法一把 `g_hclk_khz` 加入 `Watch 1` 窗口，本实验配置下应读到 `72000`；若仍是 `8000`，说明 `SystemClock_Config()` 没有真正切到 `PLL`，回到第 10 节按链路排查；
- **方法二（MCO 实测）**：按 5.3 节方法二启用 MCO 并从 `PA8` 输出，预分频 `1` 时示波器应测到接近 `72 MHz`；没有示波器就把预分频设为 `/8`，用频率计应读到约 `9 MHz`。

## 8. 典型分支与低功耗

### 8.1 FCLK 与停止模式

FCLK 是供给 Cortex-M3 内核的自由运行时钟（free-running clock），与 HCLK 同源，不是独立的时钟域。进入停止模式后，HCLK 及多数 AHB 外设会暂停，高速时钟源和 PLL 也可能关闭；唤醒逻辑仍需要能够工作的时钟和中断采样路径。不同 F1 子型号对 FCLK 的具体表示和来源可能略有差异，不能仅凭 CubeMX 图形连线推断所有硬件细节。

从停止模式唤醒后，系统往往先回到 HSI。若应用原来依赖 `72 MHz` PLL，必须重新执行 `SystemClock_Config()`，再使用串口、定时器和精确定时功能。待机模式唤醒通常相当于复位，会重新执行启动流程。

### 8.2 RTC、后备域与 MCO

RTC/LSE 属于后备域，是否在掉电或复位后继续走时，取决于 `VBAT`、后备域复位和时钟选择；不能按普通 SRAM 的保持规律理解。需要验证频率时，可把 MCO 输出到 `PA8`，再用仪器测量真实波形。

## 9. 例题与诊断

### 例 1：从 `8 MHz` HSE 得到 `24 MHz`

**题目**：外部晶振为 `8 MHz`，希望获得 `24 MHz` 的 SYSCLK，给出两种可行思路。

**分析与解答**：

- 追求精度：选择 `HSE/2` 作为 PLL 输入，设置 `PLL x6`，得到 `8/2 × 6 = 24 MHz`；
- 追求少用外部器件：选择 `HSI/2`，设置 `PLL x6`，同样得到 `24 MHz`，但精度由 HSI 决定。

**方法提示**：先写出输入源，再写分频和倍频；不要只看 PLL 倍频数而漏掉前级 `/2`。同时要检查 PLL 输出是否落在数据手册规定的范围内（F103 常见约 `16~72 MHz`，务必以手中型号手册为准）：例如 `HSE/2` 配 `PLL x3` 得到的 `12 MHz` 低于该下限、可能无法锁定，只能用来理解分频关系，不要照此配置。

### 例 2：为什么 APB1 为 `36 MHz` 时，TIM2 仍可按 `72 MHz` 计算

**题目**：`SYSCLK = 72 MHz`、AHB `/1`、APB1 `/2`，求 `PCLK1` 和 TIM2 常见输入时钟。

**解答**：

$$HCLK = 72/1 = 72\,\text{MHz}$$

$$PCLK1 = 72/2 = 36\,\text{MHz}$$

因为 APB1 分频系数大于 `1`，F1 定时器时钟通常自动乘 `2`，所以：

$$f_{TIM2} = 2 \times PCLK1 = 72\,\text{MHz}$$

**常见错误**：直接把 `PCLK1 = 36 MHz` 代入 PWM 频率公式，导致实际频率计算错误。

### 例 3：ADC 时钟不能直接等于 PCLK2

**题目**：`PCLK2 = 72 MHz`，ADC 预分频可选 `/2、/4、/6、/8`，选择满足 `14 MHz` 上限的常用配置。

**解答**：

```text
/2 -> 36 MHz，超限
/4 -> 18 MHz，超限
/6 -> 12 MHz，满足
/8 ->  9 MHz，满足
```

**方法提示**：所有专用外设时钟都要从上游实际频率继续计算，不能只看总线节点名称。

## 10. 故障诊断清单

按“输入 → 处理 → 状态 → 输出”的链路排查：

1. **硬件输入**：供电、复位、晶振频率、晶振焊接和 HSE 模式是否匹配；
2. **时钟处理**：PLL 输入、倍频、SYSCLK 选择和 AHB/APB 分频是否逐级算对；
3. **约束检查**：`HCLK/PCLK1/PCLK2`、ADC、USB、Flash 等是否超过上限；
4. **状态返回**：`HAL_RCC_OscConfig()` 和 `HAL_RCC_ClockConfig()` 是否返回 `HAL_OK`；
5. **门控与归属**：GPIO、TIM、ADC、DMA 所在总线是否正确，是否执行对应 `__HAL_RCC_xxx_CLK_ENABLE()`；
6. **运行时测量**：用 `HAL_RCC_Get*Freq()`、调试器或 MCO 验证，而不是只相信 CubeMX 图形界面；
7. **应用现象**：串口波特率、PWM 周期、ADC 采样和 `HAL_Delay()` 异常时，先沿时钟树回溯，再检查外设寄存器；
8. **低功耗恢复**：停止模式唤醒后是否重新配置 PLL 和 SysTick。

典型误区包括：把晶振误设为 Bypass；把 APB1 配成 `72 MHz`；忽略定时器自动乘 `2`；把 ADC 直接接到 `PCLK2`；高频运行却未设置 Flash 等待周期；用空循环当精确定时；把 `SysTick` 和 `SYSCLK` 混为一谈。

## 本章小结

STM32 时钟系统可以压缩为一条可计算主线：

```text
时钟源 -> PLL/选择 -> SYSCLK -> AHB -> HCLK -> APB1/APB2 -> PCLK1/PCLK2 -> 外设专用分支
```

`SYSCLK` 决定系统主干，AHB/APB 分频决定总线节拍，RCC 门控决定外设是否真正得到时钟，定时器、ADC、USB、RTC 等模块还可能拥有自己的特殊分支。掌握这条链，才能从“会点 CubeMX”提升到“能计算、能验证、能排错”。

### 自测

1. `HSE = 8 MHz`、PLL `x9`、AHB `/1`、APB1 `/2`、APB2 `/1` 时，`SYSCLK/HCLK/PCLK1/PCLK2` 分别是多少？
2. 为什么 `PCLK1 = 36 MHz` 时 TIM2 常按 `72 MHz` 计算？
3. HSE 晶振模式和 Bypass 模式分别适用于什么硬件？
4. 为什么不能用空循环替代精确定时？
5. 进入停止模式后，唤醒时为什么通常要重新调用 `SystemClock_Config()`？

**答案要点**：

1. `72/72/36/72 MHz`；
2. APB 分频大于 `1` 时，F1 定时器时钟通常为 `2 × PCLK1`；
3. 晶振模式连接外部晶体，Bypass 直接输入已有时钟波形；
4. 编译优化、流水线和实现细节会改变循环耗时；
5. 停止模式可能关闭 PLL/HSI/HSE，唤醒后的默认时钟不再是原来的 `72 MHz`。
