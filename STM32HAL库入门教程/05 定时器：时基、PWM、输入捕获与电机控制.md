# 05 定时器：时基、PWM、输入捕获与电机控制


## 本章问题

<<<<<<< Updated upstream
怎样用定时器分别实现固定周期、PWM、输入捕获和电机控制？

第 4 章让硬件在“事件发生”时触发处理；本章进一步利用定时器提供稳定的时间基准和波形控制。固定周期任务、舵机与电机驱动，以及外部脉冲测量，都可以由同一类外设完成。
=======
`HAL_Delay()` 让 CPU 干等，既不准，也没法同时做别的事。电机调速、舵机转角、测频都需要芯片按时间表自己干活。定时器把“时间”变成硬件行为：用 `PSC/ARR` 得到固定周期，就是时基；让计数值撞上 `CCR` 时翻转电平，就是 PWM；在外部边沿出现时把 `CNT` 抄进 `CCR`，就是输入捕获。
>>>>>>> Stashed changes

## 学习目标

- 用 `PSC/ARR` 配置 1 Hz 更新中断。
- 用 PWM 控制 LED、舵机和直流电机。
- 用输入捕获测量 PWM 的频率和占空比。
- 用外部时钟统计输入脉冲。
- 用编码器接口读取方向和增量。

## 0. 硬件与工程

| 物品 | 实验 | 注意 |
| --- | --- | --- |
| 最小系统板 + ST-LINK | 全程 | 第 0 章底座 |
| 红外对管类光电传感器 | 实验二 | 输出限 3.3 V，开漏需上拉 |
| LED + 约 1 kΩ 电阻 | 实验三 | 串在 PA6 与 LED 之间 |
| SG90 类舵机 | 实验四 | 独立 5 V 供电，与 MCU 共地 |
| TB6612 + 直流减速电机 | 实验五 | VM 用独立电机电源 |
| 杜邦线 | 实验六 | PA0 自环到 PA6 |
| 增量编码器 | 实验七 | A/B 接 PA8/PA9，共地 |

<<<<<<< Updated upstream

## 1. 定时器计数与时基

### 1.1 统一模型与资源

以下示例以 STM32F103C8T6、72 MHz 系统时钟为例；不同封装的定时器通道和引脚映射以实际数据手册与 CubeMX 配置为准。STM32F103C8T6 可用 `TIM1`（APB2）和 `TIM2~TIM4`（APB1），本组实验分别用它们实现定时中断、外部时钟、PWM、输入捕获和编码器计数。

所有功能都围绕同一个计数器展开：

```text
时钟源或外部引脚
        -> PSC 预分频
        -> CNT 计数状态
        -> ARR 更新边界
        -> 更新中断 / CCR 比较 / 输入锁存 / 编码器方向判断
        -> 周期任务、PWM 输出或测量结果
```

同一引脚不能同时承担两个复用功能。例如 `PA6/TIM3_CH1` 只能在本组实验中单独用于 PWM 或输入捕获，不能把两个实验的外设初始化同时打开。实验六用 `PA0/TIM2_CH1` 输出测试 PWM，`PA6` 只作输入捕获。`htimx` 是对应定时器的句柄，CubeMX 生成的初始化函数填充它，后续 HAL 调用通过该句柄操作外设。初始化顺序保持为：

```text
HAL_Init()
-> SystemClock_Config()
-> MX_GPIO_Init()
-> MX_TIMx_Init()       // 同时完成 GPIO 复用、定时器参数和必要的 NVIC 配置
-> HAL_TIM_*_Start...() // 最后启动计数、比较或捕获
```

复用引脚的初始化不是单独的 GPIO 函数，而是藏在 `MX_TIMx_Init()` 内部：HAL 在外设初始化时回调 `HAL_TIM_MspPostInit()`（本组工程中在 `tim.c`），把 PA6、PB8 这类复用脚配成复用推挽输出。所以"配了 PWM 通道但引脚没波形"时，先检查生成代码里 `HAL_TIM_MspPostInit()` 是否配置了对应引脚，而不是去 `MX_GPIO_Init()` 里找。

七个实验与配套子工程一一对应，全部在 `E:\ProjectStm\Courses\HAL05_TIM_Peripherals\` 下：

| 实验 | 子工程目录 | 定时器分工 |
| --- | --- | --- |
| 实验一：1 s 定时中断 | `01_BaseTimer` | TIM4 更新中断 |
| 实验二：外部时钟计数 | `02_ExternalClock` | TIM2 外部时钟模式 2（ETR） |
| 实验三：LED 呼吸灯 | `03_PWM_LED` | TIM3 CH1 输出 PWM |
| 实验四：舵机 | `04_PWM_Servo` | TIM4 CH3 输出 50 Hz PWM |
| 实验五：TB6612 电机 | `05_TB6612` | TIM3 CH1 PWM + 方向 GPIO |
| 实验六：PWMI 测频测占空比 | `06_PWMI` | TIM2 输出 + TIM3 捕获 |
| 实验七：编码器 | `07_Encoder` | TIM1 编码器接口模式 |

实验六是一个独立的新建工程：子工程目录 `06_PWMI`，工程与 `.ioc` 均命名为 `HAL05_PWMI`。它让 TIM2 自己输出一路参数已知的 PWM，再用 TIM3 的输入捕获把频率和占空比测出来，自发自收的动机在 3.4 节展开。

### 1.2 PSC、CNT、ARR 与定时器时钟

先建立一个简化模型：定时器按照计数时钟递增或递减，达到边界后产生更新事件。`PSC` 降低计数频率，`CNT` 保存当前计数值，`ARR` 规定计数边界，`CCR` 则用于设定 PWM 比较点或保存输入捕获值。下面先给出严格定义，再用公式说明各寄存器之间的关系。

- `PSC`（Prescaler）预分频器：实际分频系数是 `PSC+1`；
- `CNT`（Counter）计数器：每收到一个有效计数时钟就加一或减一；
- `ARR`（Auto-Reload Register）自动重装载寄存器：规定计数边界；
- `CCR`（Capture/Compare Register）捕获比较寄存器：决定 PWM 的比较点，或接收输入捕获的计数值。

在向上计数模式中，`CNT` 从 `0` 数到 `ARR`，下一个计数时钟到来时回到 `0` 并产生更新事件。因此：
=======
七个实验各建一个工程：

| 实验 | 目录 | 定时器用法 |
| --- | --- | --- |
| 一：1 s 定时中断 | `01_BaseTimer` | TIM4 更新中断 |
| 二：外部时钟计数 | `02_ExternalClock` | TIM2 ETR |
| 三：LED 呼吸灯 | `03_PWM_LED` | TIM3 CH1 PWM |
| 四：舵机 | `04_PWM_Servo` | TIM4 CH3，50 Hz |
| 五：TB6612 电机 | `05_Motor` | TIM3 CH1 PWM + 方向 GPIO |
| 六：测频测占空比 | `06_PWMI` | TIM2 输出 + TIM3 捕获 |
| 七：编码器 | `07_Encoder` | TIM1 编码器模式 |

F103C8T6 可用 `TIM1`（挂 APB2）和 `TIM2~TIM4`（挂 APB1）。同一引脚不能同时承担两个复用功能，`PA6/TIM3_CH1` 在这些实验里只能单独用作 PWM 或捕获。`htimx` 是 CubeMX 生成的定时器句柄，后续 HAL 调用都通过它操作外设。

## 1. 定时器计数与时基

### 1.1 定时器就是一个计数器

定时器只做三件事：按节拍加一或减一，当前值存在 `CNT`；数到 `ARR` 就回到起点，同时产生更新事件；节拍快慢由 `PSC` 决定。

在计数器上再挂三种硬件动作，就得到本章的全部用法：

- 输出比较：`CNT` 匹配 `CCR` 时改变输出电平，得到 PWM；
- 输入捕获：指定边沿出现时把 `CNT` 抄进 `CCR`，用来测时间；
- 编码器接口：用 A/B 两相正交信号在硬件里判向，直接让 `CNT` 加或减。

![定时器内部结构](image/timer-block-diagram.png)

### 1.2 PSC、CNT、ARR

`PSC` 是预分频器，实际分频系数为 `PSC+1`；`CNT` 是当前计数值；`ARR` 是计数边界；`CCR` 是比较值或捕获值。

向上计数时，`CNT` 从 0 数到 `ARR`，下一个时钟回到 0 并产生更新事件。计数节拍是：
>>>>>>> Stashed changes

$$
f_{\mathrm{CNT}}=\frac{f_{\mathrm{TIM}}}{\mathrm{PSC}+1}
$$

<<<<<<< Updated upstream
=======
更新频率和周期是：

>>>>>>> Stashed changes
$$
f_{\mathrm{update}}=\frac{f_{\mathrm{TIM}}}{(\mathrm{PSC}+1)(\mathrm{ARR}+1)},\qquad
T_{\mathrm{update}}=\frac{(\mathrm{PSC}+1)(\mathrm{ARR}+1)}{f_{\mathrm{TIM}}}
$$

<<<<<<< Updated upstream
两个 `+1` 来自计数范围：预分频器和主计数器都包含 `0`。公式中的 `f_TIM` 指实际送到 TIMx 的计数时钟；外部时钟模式 2 时，应把 ETR 有效脉冲频率代入。例如 `PSC=0` 是 1 分频，`ARR=0` 仍然会产生一个计数周期，而不是零周期。本组实验统一采用向上计数；中央对齐或其他模式的边界计算不能直接套用此式。

**1 s 定时示例**：若 `f_TIM=72 MHz`，先取 `PSC=7199`：

$$
f_{\mathrm{CNT}}=\frac{72\,\mathrm{MHz}}{7200}=10\,\mathrm{kHz}
$$

再取 `ARR=9999`，每周期计数 `10000` 次：
=======
两个 `+1` 是因为分频器和计数器都从 0 开始。`PSC=0` 就是 1 分频，`ARR=999` 对应 1000 个计数节拍。

以 72 MHz 的 TIM4 配 1 s 为例，先取 `PSC=7199`，节拍降到 10 kHz；再取 `ARR=9999`，正好数 10000 拍：
>>>>>>> Stashed changes

$$
T_{\mathrm{update}}=\frac{10000}{10\,\mathrm{kHz}}=1\,\mathrm{s}
$$

对应配置是 `Prescaler=7199`、`Counter Period=9999`、向上计数。

<<<<<<< Updated upstream
定时器时钟不能机械地把 `PCLK` 代入公式：APB 预分频为 1 时，定时器时钟等于对应 `PCLK`；APB 预分频不为 1 时，定时器时钟自动乘二。常见的 72 MHz 配置中，`PCLK1=36 MHz`，但 `TIM2~TIM4` 的时钟是 `72 MHz`。

对于 `PSC`、`ARR` 都是 16 位且 `f_TIM=72 MHz` 的定时器，单次向上计数的最长周期约为：
=======
`PSC` 和 `ARR` 都是 16 位时，最长的单次定时是：
>>>>>>> Stashed changes

$$
T_{\max}=\frac{65536\times65536}{72\times10^6}\approx59.65\,\mathrm{s}
$$

<<<<<<< Updated upstream
更长的周期可用较短更新周期配合软件累计。`ARR` 位宽随定时器和芯片而变，不能把上述数值直接套到所有型号。
=======
需要更长周期时，让定时器按较短周期反复中断，再在软件里累计。
>>>>>>> Stashed changes

### 1.3 预装载与启动

<<<<<<< Updated upstream
`PSC` 没有预装载，写入会直接改变后续分频；运行中修改可能截断当前计数，通常应先停表。`ARR` 是否预装载由 `AutoReloadPreload`（`TIMx_CR1` 的 `ARPE` 位）决定：使能时，新 `ARR` 先写入预装载值，更新事件才转入活动寄存器；禁用时，写入会立即改变当前周期的边界。需要平滑改变周期时，应启用该选项。CCR 是否预装载则由通道配置决定。

`HAL_TIM_Base_Init()` 在配置末尾产生一次更新事件（向 `TIMx_EGR` 写入 `TIM_EGR_UG`），复位 `CNT` 并把预装载值装入活动寄存器。不同 HAL 版本对更新标志 `UIF` 的处理不同：新版驱动通常会清掉它，旧版驱动可能需要手动清除。下面实验统一在启动前调用 `__HAL_TIM_CLEAR_FLAG(&htim4, TIM_FLAG_UPDATE)`，再调用 `HAL_TIM_Base_Start_IT(&htim4)`；这次清除在新版驱动中无害，在旧版驱动中可避免启动后的多余更新中断。

定时中断实验的 CubeMX 配置顺序是：选择内部时钟，填写 `PSC/ARR`，在 NVIC 勾选更新中断，生成代码，最后清除 `UIF` 并调用 `HAL_TIM_Base_Start_IT()`。常用 HAL 接口如下：

| 操作 | 接口 |
| --- | --- |
| 启动/停止更新中断 | `HAL_TIM_Base_Start_IT()` / `HAL_TIM_Base_Stop_IT()` |
| 更新中断回调 | `HAL_TIM_PeriodElapsedCallback()` |
| 读取/写入计数值 | `__HAL_TIM_GET_COUNTER()` / `__HAL_TIM_SET_COUNTER()` |
| 读取/运行时改写自动重装载值 | `__HAL_TIM_GET_AUTORELOAD()` / `__HAL_TIM_SET_AUTORELOAD()` |

表中 `Start_IT/Stop_IT` 与 `Start/Stop` 的区别只在要不要开放更新中断：实验一要"听钟声"，用 `_IT` 版本；实验二只读计数值，普通版本即可。
=======
`PSC` 始终经过缓冲，运行中写入的新值要等到下一次更新事件才生效。`ARR` 是否缓冲由 `AutoReloadPreload` 决定：使能时同样等更新事件，禁用时立即改变周期。

`HAL_TIM_Base_Init()` 在配置末尾会产生一次更新事件，把 `CNT` 清零并装入预装载值，同时可能置位 `UIF`。启动前先清一次标志，避免把这次初始化当成第一次定时到点：

```c
__HAL_TIM_CLEAR_FLAG(&htim4, TIM_FLAG_UPDATE);
HAL_TIM_Base_Start_IT(&htim4);
```

常用的 HAL 接口：

| 操作 | 接口 |
| --- | --- |
| 启动/停止更新中断 | `HAL_TIM_Base_Start_IT()` / `HAL_TIM_Base_Stop_IT()` |
| 更新中断回调 | `HAL_TIM_PeriodElapsedCallback()` |
| 读写计数值 | `__HAL_TIM_GET_COUNTER()` / `__HAL_TIM_SET_COUNTER()` |

`Start_IT` 和 `Start` 的区别只在于是否开放更新中断：需要回调就用 `_IT`，只读计数值用普通版本。
>>>>>>> Stashed changes

### 1.4 实验一：1 s 定时中断

目标是让 TIM4 每秒产生一次更新中断，回调里只让 `g_tick` 加一。

<<<<<<< Updated upstream
**配置**：`Internal Clock`，`PSC=7199`，`ARR=9999`，NVIC 使能 `TIM4_IRQn`。CubeMX 操作：左侧 `Timers` 列表点开 `TIM4`，`Mode` 区 `Clock Source` 下拉选 `Internal Clock`；下方 `Parameter Settings` 里 `Prescaler` 填 `7199`、`Counter Mode` 保持 `Up`、`Counter Period` 填 `9999`、`auto-reload preload` 保持 `Disable`；再切到 `NVIC Settings` 子页勾选 `TIM4 update interrupt`——漏勾的后果是定时器照常计数，但 NVIC 不放行，`g_tick` 永远不动。有两个字段容易多写 1：`Prescaler` 填的是寄存器原始值（7199，对应分频 7200），`Counter Period` 填的是 `ARR`（9999，对应计数 10000）；按 7200/10000 填写，1 s 会变成约 1.00024 s，单秒看不出，累计一小时慢约 0.86 s。生成代码里还能看到 `ClockDivision = TIM_CLOCKDIVISION_DIV1`：它规定数字滤波基准 `tDTS` 与计数时钟的关系（DIV1 即两者相等），不改变 CNT 的计数频率，本章保持默认。以下代码放入 CubeMX 生成的 `main.c` 用户区，初始化函数由 CubeMX 生成；它包含从启动到回调的完整用户路径。

在 `MyCode` 复刻本实验的完整路径：

1. 复制第 0 章模板工程到 `MyCode\05_TIM\01_BaseTimer`；
2. 双击 `.ioc`，按上文 CubeMX 操作配置 TIM4 并勾选 NVIC；
3. `GENERATE CODE` 后回到 VS Code；
4. 在 `USER CODE BEGIN PV` 区声明 `g_tick`，在 `USER CODE BEGIN 2` 区写清标志与启动两行，在 `main.c` 末尾用户区写回调；
5. 模板已登记 `main.c`，无需改动 CMake；
6. 编译、下载，打开调试，把 `g_tick` 加入 Watch（或 Live Watch）窗口，全速运行观察。
=======
CubeMX 中打开 `TIM4`，`Clock Source` 选 `Internal Clock`，`Prescaler=7199`、`Counter Period=9999`、`Counter Mode=Up`、`auto-reload preload=Disable`；在 `NVIC Settings` 勾选 `TIM4 update interrupt`，抢占优先级按第 04 章的表填 `2`。
>>>>>>> Stashed changes

```c
volatile uint32_t g_tick;

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM4)
    {
        g_tick++;
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM4_Init();

    __HAL_TIM_CLEAR_FLAG(&htim4, TIM_FLAG_UPDATE);
    HAL_TIM_Base_Start_IT(&htim4);

    while (1)
    {
    }
}
```

<<<<<<< Updated upstream
**输入 → 状态 → 输出**：TIM4 更新事件进入 NVIC → 回调只递增 `g_tick` → 调试器中的数值每秒加一。`g_tick` 同时被中断和主程序访问，必须声明为 `volatile`；中断中不放显示等耗时操作。`HAL_Delay()` 和空循环都不能替代硬件定时。

第一次用定时中断，值得把"从计满到自己的函数被调用"整条链走一遍，每个环节都能在工程里找到坐标：

```text
CNT 数到 ARR，下一拍归零，硬件置起更新标志 UIF
-> 启动文件 startup_stm32f103xb.s 的向量表把 TIM4 中断指向 TIM4_IRQHandler()
-> Core/Src/stm32f1xx_it.c：TIM4_IRQHandler() 调用 HAL_TIM_IRQHandler(&htim4)
-> HAL 库确认是更新中断，清掉 UIF，调用 HAL_TIM_PeriodElapsedCallback()
-> main.c 中的同名回调执行 g_tick++
```

`HAL_TIM_PeriodElapsedCallback()` 在 HAL 驱动源码里是一个带 `__weak` 标记的空函数；在 `main.c` 里写出同名函数，链接器就用它覆盖空版本。回调开头判断 `htim->Instance == TIM4` 是在为将来留余地：一旦再开第二个定时器中断，所有更新中断都会涌进同一个回调，没有 `Instance` 判断就会串台。本工程把 TIM4 抢占优先级设为 2（见 `tim.c` 的 `HAL_TIM_Base_MspInit()`）；本章只有这一个定时器中断，优先级数值不影响现象，第 4 章的优先级规则在这里照常适用。

**预期现象**：`g_tick` 每秒增加 1，启动时没有多余跳变。如果看到 X，说明 Y：`g_tick` 启动瞬间就已经是 1（还没等满 1 s 就开始计数），说明启动前残留的更新标志没被清掉（旧版 HAL 驱动的行为），按 1.3 的顺序把 `__HAL_TIM_CLEAR_FLAG()` 放回 `HAL_TIM_Base_Start_IT()` 之前；`g_tick` 一动不动，按第 6 节信号链从"启动调用 → NVIC → 回调"逐级查。若周期恰好差 2 倍，先查 `f_TIM` 是否误用了 `PCLK`，再查 `PSC/ARR` 的 `+1`。

### 1.5 实验二：外部时钟脉冲计数

**目标**：用 TIM2 外部时钟模式 2 统计光电传感器输出的脉冲。

外部时钟模式 2 让 `ETR` 引脚上的有效边沿直接成为计数时钟。STM32F103 的 `TIM2_ETR` 映射到 `PA0`；CubeMX 中选择 `Clock Source=ETR2`，生成代码对应 `htim.Init.ClockSource = TIM_CLOCKSOURCE_ETRMODE2`。外部时钟不经过从模式控制器，和 `TIx/ITR` 触发的外部时钟模式 1 不同。

**接线与配置**：光电传感器 `DO -> PA0`，传感器与 STM32 共地；开漏输出需要上拉到 3.3 V。`PA0` 不是 STM32F103 的 5 V 容忍引脚，5 V 输出必须先降到 3.3 V 或经过合适的电平转换。取 `PSC=0`、`ARR=65535`，让 16 位计数范围全部可用；滤波越强，抗毛刺能力越好，但延迟越大、最高可接受频率越低。CubeMX 操作：`Timers → TIM2` 的 `Clock Source` 下拉选 `ETR2`——选成 `ITRx` 或 `Internal Clock`，都得不到"ETR 引脚直接当计数时钟"的行为；引脚图上 `PA0` 会自动显示为 `TIM2_CH1_ETR`。ETR 的分频与滤波保持默认，即不分频、不滤波。
=======
`g_tick` 同时被中断和主程序访问，必须加 `volatile`。回调里判断 `Instance`，是为了以后增加第二个定时器时两条中断不会串台。下载后 `g_tick` 应每秒加一，启动时没有多余跳变。

驱动库的 `Timer_Init()` 内部只有一句 `HAL_TIM_Base_Start_IT(&TIMER_HANDLE)`，只负责启动中断；时基由 CubeMX 配好，默认对应 `TIM1`，`PSC=71`、`ARR=999`，即 1 ms 节拍。项目里通常保留 1 ms，在回调中每 1000 次再递增秒计数，这样一个定时器可以同时喂给按键扫描和 PID 采样。

### 1.5 实验二：外部时钟计数

外部时钟模式 2 让 `ETR` 引脚上的每个有效边沿替代一次计数时钟。F103 的 `TIM2_ETR` 映射到 `PA0`，CubeMX 中 `Clock Source` 选 `ETR2`，`PSC=0`、`Counter Period=65535`，ETR 分频和滤波保持默认。

接线：传感器 `DO → PA0`，与 MCU 共地，开漏输出上拉到 3.3 V。
>>>>>>> Stashed changes

```c
static uint16_t last_count = 0U;

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM2_Init();
    HAL_TIM_Base_Start(&htim2);

    while (1)
    {
        uint16_t now = (uint16_t)__HAL_TIM_GET_COUNTER(&htim2);
        if (now != last_count)
        {
            last_count = now;
            HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
        }
        HAL_Delay(100U);
    }
}
```

<<<<<<< Updated upstream
**输入 → 状态 → 输出**：传感器有效边沿 → TIM2 硬件递增 `CNT` → 主循环检测到计数变化并翻转 PC13。`HAL_TIM_Base_Start()` 不能省略，否则外部时钟已经接到 TIM2，计数器也可能一直保持 0。

主循环的 `HAL_Delay(100)` 只决定"多久看一眼"，不影响计数本身：`CNT` 由硬件递增，CPU 睡着也不丢数，只要采样间隔内增量不超过 16 位计数范围。

若每个脉冲代表位移 `s`，累计距离和固定采样窗口速度为：

$$
d=N\times s,\qquad v=\frac{\Delta N\times s}{\Delta t}
$$

脉冲代表一条边界、半个周期还是一个完整周期，必须在测量前定义清楚。例如转轮每个孔位产生一个完整脉冲、每格代表 1 mm，计数 5000 就是 5 m；若实际每个孔落出两个边沿却按"一个脉冲"换算，距离就整整翻倍——定义含糊的代价是成倍偏差。

**预期现象**：`TIM2->CNT` 随有效脉冲增长，PC13 在检测到变化时翻转。传感器静止时计数应基本不变；计数抖动先查电平、共地、极性和滤波。如果看到 X，说明 Y：引脚确有脉冲而 `CNT` 恒为 0，先确认 `HAL_TIM_Base_Start()` 已调用、`Clock Source` 确实选了 `ETR2`；不碰线 `CNT` 也疯涨，是引脚悬空拾取干扰的典型表现，检查传感器输出类型和上拉；手指搭在信号线上计数就跳变，同样是悬空。

## 2. 输出比较与 PWM

### 2.1 PWM 时序、占空比与边界

先建立直觉：LED 和电机都不认识"数字量的一半"——引脚要么高要么低；但只要开关足够快，人眼和电机就只感受到平均值。一个周期内高电平所占的比例就是占空比，它是 PWM 唯一要传递的信息；定时器用"一个周期内何时从高变低"这个切换点来携带它，切换点由比较值 `CCR` 决定。

PWM 通过快速切换输出改变高电平持续时间。在向上计数、有效高电平、PWM 模式 1 下：
=======
`HAL_Delay(100)` 只决定多久看一次，不影响计数本身。`CNT` 由硬件递增，CPU 睡着也不丢脉冲。传感器静止时计数应基本不变；若抖动，先查电平、共地和滤波。

## 2. 输出比较与 PWM

### 2.1 PWM 的原理

PWM 是输出比较在整段计数周期里反复执行的结果。PWM 模式 1 下，`CNT < CCR` 时输出有效电平，否则输出无效电平：
>>>>>>> Stashed changes

```text
CNT < CCR  → 高
CNT >= CCR → 低
```

<<<<<<< Updated upstream
占空比和分辨率为：
=======
占空比和分辨率分别是：
>>>>>>> Stashed changes

$$
D=\frac{\mathrm{CCR}}{\mathrm{ARR}+1},\qquad \Delta D=\frac{1}{\mathrm{ARR}+1}
$$

<<<<<<< Updated upstream
必须记住三个边界：

- `CCR=0`：占空比为 0%；
- `CCR=ARR`：占空比为 `ARR/(ARR+1)`，还不是严格 100%；
- `CCR=ARR+1`：整个周期都满足 `CNT<CCR`，可得到严格 100%；但 16 位寄存器在 `ARR=65535` 时无法写入 65536，只能得到接近满占空比。

**20 kHz 电机 PWM**：若 `f_TIM=72 MHz`，取 `PSC=0`、`ARR=3599`：
=======
`CCR=0` 是 0%，`CCR=ARR+1` 是严格的 100%。同一定时器的多个通道共享 `PSC`、`CNT` 和 `ARR`，频率一致，各通道的 `CCR` 独立。

![PWM 输出结构与波形](image/pwm-block-diagram.png)

以 20 kHz 电机 PWM 为例，72 MHz 下取 `PSC=0`、`ARR=3599`：
>>>>>>> Stashed changes

$$
f_{\mathrm{PWM}}=\frac{72\,\mathrm{MHz}}{(0+1)(3599+1)}=20\,\mathrm{kHz}
$$

<<<<<<< Updated upstream
一个周期有 3600 个计数，`CCR=1800` 约为 50%。这 3600 档就是本配置的分辨率：`CCR` 每加 1，占空比只变 $1/3600$，呼吸灯的过渡因此足够平滑。20 kHz 可把电机开关噪声移出大多数人耳可听范围；占空比相同并不保证转速相同，负载和供电会改变实际转速。

同一定时器的多个通道共享 `PSC`、`CNT` 和 `ARR`，所以频率和周期同步；各通道的 `CCR` 独立。一个通道不能同时作为 PWM 输出和输入捕获。

### 2.2 实验三：LED 呼吸灯

**目标**：用 TIM3_CH1 改变 LED 的平均亮度。

**配置**：TIM3 选择内部时钟，CH1 选择 `PWM Generation CH1`，PWM mode 1、向上计数、Polarity High，取 `PSC=0`、`ARR=3599`。生成代码中对应 `TIM_OCMODE_PWM1`、`TIM_OCPOLARITY_HIGH` 和 `TIM_COUNTERMODE_UP`；`PA6` 是 `TIM3_CH1`。CubeMX 操作：在引脚图上点 `PA6`，弹出列表选 `TIM3_CH1`；再到 `Timers → TIM3`，`Clock Source` 选 `Internal Clock`，`Mode` 区 `Channel1` 下拉选 `PWM Generation CH1`；`Parameter Settings` 里确认 `Mode` 为 `PWM mode 1`、`CH Polarity` 为 `High`，`Pulse` 先保持 `0`。若 `CH Polarity` 误选 `Low`，波形整体反相，"CCR 越大越亮"就变成"CCR 越大越暗"，呼吸方向颠倒多半是它。

**接线**：`PA6 -> 约 1 kΩ 限流电阻 -> LED 阳极`，LED 阴极接 `GND`。不能把板载 PC13 当作 PWM 输出；PC13 没有定时器通道。高电平有效时，`CCR` 越大，LED 平均电流越大。
=======
`CCR=1800` 约为 50%。3600 档的分辨率让占空比每加 1 只变约 0.028%，呼吸灯过渡足够平滑。选 20 kHz 是因为它刚好在入耳范围上沿，既避开可闻啸叫，又不会让开关损耗和干扰明显增加。

### 2.2 实验三：LED 呼吸灯

接线：`PA6 → 约 1 kΩ 电阻 → LED 阳极`，阴极接 `GND`。高电平有效时，`CCR` 越大，平均电流越大。

CubeMX 中把 `PA6` 选为 `TIM3_CH1`，`TIM3` 的 `Channel1` 选 `PWM Generation CH1`，`PSC=0`、`Counter Period=3599`、`Pulse=0`，PWM mode 1、Polarity High。
>>>>>>> Stashed changes

```c
int main(void)
{
    int32_t ccr;

    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM3_Init();

    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);

    while (1)
    {
        for (ccr = 0; ccr <= 3599; ccr += 10)
        {
            __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, (uint32_t)ccr);
            HAL_Delay(5U);
        }
        for (ccr = 3599; ccr >= 0; ccr -= 10)
        {
            __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, (uint32_t)ccr);
            HAL_Delay(5U);
        }
    }
}
```

<<<<<<< Updated upstream
`int32_t ccr` 放在循环外，以兼容 C90 编译器。代码中 `HAL_TIM_PWM_Start()` 必须位于 `MX_TIM3_Init()` 之后。

主循环里随时改写 `CCR` 都合法。HAL 在 `HAL_TIM_PWM_ConfigChannel()` 中为 PWM 通道打开了 CCR 预装载（`OCxPE` 位，可在 HAL 源码中核对），新写入的比较值要等下一个更新事件（CNT 归零处）才转入影子寄存器统一生效——波形不会在周期中间被"撕裂"，最迟延迟一个 PWM 周期（20 kHz 即 50 µs），肉眼不可感知。这正是呼吸灯能连续渐变的原因。

**输入 → 状态 → 输出**：软件改变 `CCR` → TIM3 改变高电平持续时间 → LED 亮度渐变。**预期现象**：约以 `360 × 5 ms × 2 = 3.6 s` 为周期变亮、变暗；亮度不随 `CCR` 线性变化，且 LED 必须串限流电阻。如果看到 X，说明 Y：只见快速明暗闪烁而不见渐变，是 PWM 频率被配低了几个数量级，回查 `PSC/ARR`；亮度随 `CCR` 反向变化，查 `CH Polarity` 是否误设为 `Low`，或 LED 是否被接成了低电平点亮。

### 2.3 实验四：PWM 控制舵机

**目标**：用 50 Hz PWM 控制舵机在 0°~180° 之间往复。

常见 SG90 类舵机使用约 50 Hz、周期 20 ms 的控制脉冲，标准脉宽范围是 `500~2500 µs` 对应 `0°~180°`：500 µs 对应 0°，1500 µs 对应中位 90°，2500 µs 对应 180°。个别型号的标称范围可能略有出入，以手中舵机的规格书为准；本教程统一按 500~2500 µs / 0°~180° 编写。
=======
LED 约每 3.6 s 完成一次亮暗循环。亮度与 `CCR` 不是线性关系，限流电阻不能省。

驱动库把启动和写比较值封装成 `PWM_Init()` 与 `PWM_SetCompare1()`，默认句柄是 `htim2`，本实验把 `PWM_HANDLE` 改成 `htim3` 即可。

### 2.3 实验四：PWM 控制舵机

SG90 类舵机收到固定周期的脉冲就转到对应角度，内部有电机、减速齿轮和角度反馈。控制它只需要稳定输出 50 Hz，并改变高电平宽度。本教程按 `500~2500 µs` 对应 `0°~180°`，1500 µs 是中位。

| 舵机线 | 接到 |
| --- | --- |
| 橙/黄（信号） | `PB8`（3.3 V） |
| 红（电源） | 独立 5 V 正极 |
| 棕/黑（地） | 与 STM32 `GND` 共地 |

`PB8` 设为 `TIM4_CH3`，`TIM4` 选 `PWM Generation CH3`，`PSC=71`、`Counter Period=19999`、`Pulse=1500`。这样计数频率正好 1 MHz，一个计数就是 1 µs，`CCR` 可以直接填微秒数：
>>>>>>> Stashed changes

$$
f_{\mathrm{PWM}}=\frac{72\,\mathrm{MHz}}{(71+1)(19999+1)}=50\,\mathrm{Hz}
$$

<<<<<<< Updated upstream
计数频率为 1 MHz，一个计数正好是 1 µs，所以 `CCR` 可直接填高电平脉宽。`TIM4_CH3` 选择 PWM mode 1、Polarity High，在本配置映射到 `PB8`；封装或重映射改变时，以 CubeMX 引脚图为准。生成代码中 `Pulse` 初始值是 `1500`：上电后、主循环第一次改写 `CCR` 之前，舵机会先收到约 1.5 ms 的中位脉冲，随后才跟随扫描往复。

**安全接线**：信号线接 `PB8`（STM32 输出为 3.3 V）；舵机红线接独立 5 V 电源，不能从 MCU 的 3.3 V 输出取电；舵机地与 STM32 `GND` 共地。启动和堵转电流会造成供电压降，表现为复位、抖动或角度异常。三根线逐根核对：

| 舵机线 | 接到哪里 |
| --- | --- |
| 橙/黄（信号） | `PB8` |
| 红（电源） | 独立 5 V 电源正极 |
| 棕/黑（地） | 与 STM32 `GND` 共地 |

线色只是常见习惯，以模块丝印为准。舵机被卡住时会长时间大电流，听到持续嗡嗡声或外壳发热应立即断电。

按 0°~180° 线性映射，脉宽换算为：
=======
角度到脉宽的换算：
>>>>>>> Stashed changes

$$
t_{\mathrm{pulse}}(\theta)=500+\frac{2000\,\theta}{180}\ \mu\mathrm{s}
$$

```c
#define SERVO_MIN_US  500U
#define SERVO_MAX_US  2500U
#define SERVO_MAX_DEG 180U

static uint16_t Servo_AngleToPulse(uint16_t angle)
{
    if (angle > SERVO_MAX_DEG) angle = SERVO_MAX_DEG;
    return (uint16_t)(SERVO_MIN_US +
                       ((SERVO_MAX_US - SERVO_MIN_US) * angle) / SERVO_MAX_DEG);
}

int main(void)
{
    int16_t a;

    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM4_Init();
    HAL_TIM_PWM_Start(&htim4, TIM_CHANNEL_3);

    while (1)
    {
        for (a = 0; a <= 180; a += 5)
        {
            __HAL_TIM_SET_COMPARE(&htim4, TIM_CHANNEL_3,
                                  Servo_AngleToPulse((uint16_t)a));
            HAL_Delay(50U);
        }
        for (a = 180; a >= 0; a -= 5)
        {
            __HAL_TIM_SET_COMPARE(&htim4, TIM_CHANNEL_3,
                                  Servo_AngleToPulse((uint16_t)a));
            HAL_Delay(50U);
        }
    }
}
```

<<<<<<< Updated upstream
**输入 → 状态 → 输出**：角度变量 → 脉宽换算并写入 `CCR` → PB8 输出控制脉冲 → 舵机转到对应角度。**预期现象**：舵机从 0° 到 180° 往复，单程约 `37 × 50 ms ≈ 1.85 s`。脉宽顶到 500/2500 µs 时舵机到达机械行程端点属正常；若手中舵机的规格书范围更窄，端点会顶住限位、持续嗡嗡发热，此时把 `SERVO_MIN_US/SERVO_MAX_US` 改回规格书数值即可。如果看到 X，说明 Y：上电就抖动或嗡嗡作响，先查独立 5 V 供电能力与共地，再看是否顶住机械限位；完全不响应，按"信号脚 → 50 Hz → 脉宽范围"顺序逐项核对。
=======
舵机从 0° 到 180° 往复，单程约 1.85 s。脉宽顶到 500/2500 µs 时到达机械端点属正常；若舵机规格书范围更窄，端点会顶住限位、持续发热，这时把两个宏改回规格书数值。

### 2.4 TB6612 与直流电机
>>>>>>> Stashed changes

STM32 只输出方向和 PWM 信号，电机电流由 TB6612 的 H 桥和独立电源承担。H 桥由四只功率管组成，切换导通组合就改变电机两端电压方向。

<<<<<<< Updated upstream
STM32 只输出方向和 PWM 控制信号，电机电流由 TB6612 的 H 桥和独立电机电源承担。接线关系如下：

- `VM` 接电机电源，`VCC` 接 3.3 V 逻辑电源；
- `VM` 与 `GND` 之间并联一只不小于 `10 µF` 的电容，尽量靠近模块；
- `GND` 与 STM32 共地；
- `AIN1/AIN2` 决定方向，`PWMA` 接收 PWM，`STBY` 拉高后才使能驱动器。

先看芯片要什么输入：`AIN1`、`AIN2` 就是两个普通的方向开关，用第 1 章练过的推挽输出拉高拉低即可；`PWMA` 是速度闸门，接的正是 2.1 节那种 20 kHz PWM。芯片内部是一个 H 桥——四只功率管把电机夹在中间：`IN1=1`、`IN2=0` 时电流从 `OUT1` 流向 `OUT2`，电机朝一个方向转；`IN1=0`、`IN2=1` 时电流反向、电机反转；两个输入都为 0 时输出关断，电机自由滑行。调速就靠 `PWMA` 的占空比——2.1 节说过，开关足够快时"人眼和电机只感受到平均值"：闸门打开的时间比例越高，电机两端平均电压越高，转得越快；PWM 为低的短暂期间输出被短接、绕组电流缓慢衰减，不影响这个结论。整条信号链是：`PA0/PA1（方向）+ PA6（调速）→ AIN1/AIN2/PWMA → OUT1/OUT2 → 电机`。

`STBY=0` 时驱动器待机、输出高阻；`STBY=1` 时，方向和 PWM 状态按下面的真值表生效：

| IN1 | IN2 | PWM | 状态 |
| ---: | ---: | ---: | --- |
| 1 | 0 | 高/有效 | 一个方向转动（电流 `OUT1→OUT2`，具体方向以电机接线为准） |
| 0 | 1 | 高/有效 | 相反方向转动（电流 `OUT2→OUT1`） |
| 0 | 0 | 任意 | 停止（滑行）：输出关断，电机自然减速 |
| 1 | 1 | 任意 | 短路刹车：输出两端被短接，电机快速停转 |
| 1 或 0 | 与 IN1 相反 | 低 | 短路刹车：PWM 低电平期间输出经低边短接 |

即：`IN1=IN2=0` 的"停止"就是输出关断、电机自然滑行；`IN1=IN2=1` 才是短路刹车；`STBY=0` 时无论输入如何都是高阻待机。各行电流路径细节以 TB6612FNG 数据手册真值表为准（待实测）。

"正转"和"反转"只是软件约定，电机接反时可交换 `IN1/IN2` 定义。首次测试应空载、低占空比运行，不能在高速时直接反向。
=======
TB6612 的控制引脚：

- `AIN1`、`AIN2` 是方向开关，用推挽输出控制；
- `PWMA` 接 PWM，占空比决定平均电压和转速；
- `STBY` 是总使能，低电平时输出高阻，拉高后方向和 PWM 才生效。

本实验把 `STBY` 直接接 3.3 V 常使能，驱动不再控制它。

`IN1`、`IN2`、`PWM` 的组合如下（`STBY=1`）：

| IN1 | IN2 | PWM | 状态 |
| ---: | ---: | ---: | --- |
| 1 | 0 | 有效 | 一个方向转动 |
| 0 | 1 | 有效 | 反方向转动 |
| 0 | 0 | 任意 | 滑行，电机自然减速 |
| 1 | 1 | 任意 | 短路刹车，快速停转 |
| 方向相反 | | 低 | 短路刹车 |

信号链是 `PA0/PA1（方向）+ PA6（调速）→ AIN1/AIN2/PWMA → OUT1/OUT2 → 电机`。
>>>>>>> Stashed changes

### 2.5 实验五：TB6612 驱动电机

接线：`PWMA → PA6/TIM3_CH1`，`AIN1 → PA0`，`AIN2 → PA1`，`STBY → 3.3 V`（常使能），`VM` 接独立电机电源，全板共地。

<<<<<<< Updated upstream
**接线与配置**：`PWMA -> PA6/TIM3_CH1`，`AIN1 -> PA0`，`AIN2 -> PA1`，`STBY -> PC2`；TIM3 使用 PWM mode 1、Polarity High 的 20 kHz PWM（`PSC=0`、`ARR=3599`）。AIN1、AIN2、STBY 配置为推挽输出；AIN1/AIN2 初始为低，`MX_GPIO_Init()` 也应让 `STBY` 初始为 Low（`.ioc` 的 `PC2.PinState=GPIO_PIN_RESET`），避免上电误使能电机。

上电顺序同样属于安全接线，与教程 README 的安全提醒一致：第一次上电先让 `VM` 断电或把电机线脱开，只跑逻辑部分，确认 `STBY` 为低、`IN1/IN2` 为低、PA6 无 PWM 输出，再把电机电源接回来，从 40% 以下占空比开始试转。配套工程 `05_TB6612` 采用的正是这条上电链：`TB6612_Init()` 先写低 `STBY`、设好 `IN1/IN2` 安全初值，启动 PWM 后才拉高 `STBY` 使能。

以下代码给出从初始化到运动循环的完整路径；`htim3` 由 CubeMX 生成。
=======
CubeMX 中 `PA0`、`PA1` 设为 `GPIO_Output`，`PA6` 设为 `TIM3_CH1`，`TIM3` 选 `PWM Generation CH1`，`PSC=0`、`Counter Period=3599`、`Pulse=0`。

把 `MOTOR`、`PWM` 驱动放进 `User/Drivers/` 并登记到 `CMakeLists.txt`，再改驱动顶部的宏适配本实验：

| 宏 | 默认值 | 改成 |
| --- | --- | --- |
| `MOTOR_IN1_PORT/PIN` | `GPIOB` / `GPIO_PIN_12` | `GPIOA` / `GPIO_PIN_0` |
| `MOTOR_IN2_PORT/PIN` | `GPIOB` / `GPIO_PIN_13` | `GPIOA` / `GPIO_PIN_1` |
| `PWM_HANDLE` | `htim2` | `htim3` |
| `PWM_PERIOD_COUNTS` | `100` | `3600`（仅标注） |

`Motor_SetPWM()` 直接写 `CCR`，不做百分比换算，也不限幅；主程序按 `ARR+1`（本例 3600）限制带符号指令。`PWM_HANDLE` 也要改，因为 `Motor_Init()` 内部调用的是 `PWM_Init()`，它读的是 `pwm.h` 的宏。
>>>>>>> Stashed changes

```c
#include "tim.h"
#include "tb6612.h"

static TB6612_Motor motor_a = {
    .in1_port    = GPIOA,
    .in1_pin     = GPIO_PIN_0,
    .in2_port    = GPIOA,
    .in2_pin     = GPIO_PIN_1,
    .pwm_timer   = &htim3,
    .pwm_channel = TIM_CHANNEL_1,
    .stby_port   = GPIOC,
    .stby_pin    = GPIO_PIN_2,
    .use_stby    = 1U
};

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM3_Init();

    if (TB6612_Init(&motor_a) != HAL_OK)
    {
        Error_Handler();
    }

    while (1)
    {
<<<<<<< Updated upstream
        TB6612_SetSpeed(&motor_a, 40);   /* 正转，40% */
        HAL_Delay(1000U);

        TB6612_Brake(&motor_a);
        HAL_Delay(200U);

        TB6612_SetSpeed(&motor_a, -40);  /* 反转，40% */
=======
        Motor_SetPWM(1440);  /* 正转 40%：1440 / 3600 */
        HAL_Delay(1000U);

        Motor_SetPWM(0);     /* 短路刹车 */
        HAL_Delay(200U);

        Motor_SetPWM(-1440); /* 反转 40% */
>>>>>>> Stashed changes
        HAL_Delay(1000U);

        TB6612_Stop(&motor_a);           /* 滑行停止 */
        HAL_Delay(500U);
    }
}
```

<<<<<<< Updated upstream
本组代码使用 `tb6612.h` 的单路电机 API：一个 `TB6612_Motor` 对象控制一路电机。`TB6612_Init()` 必须在 `MX_GPIO_Init()` 和 `MX_TIM3_Init()` 之后调用，它会启动 PWM、设置安全初值并退出待机。`TB6612_SetSpeed()` 接受 `-100~100`，正负表示方向，绝对值表示占空比；`0` 调用 `TB6612_Stop()`。超出 ±100 的值会被驱动自动限幅。驱动内部把百分比换算回计数：`CCR = (ARR+1) × 占空比 ÷ 100`（四舍五入，中间值用 64 位防溢出，见 `tb6612.c` 的 `set_pwm()`）——这就是 2.1 节的百分比占空比落到具体寄存器值的路径。`TB6612_Stop()`（`IN1=IN2=0`）让电机自然滑行，`TB6612_Brake()`（`IN1=IN2=1`）短路刹车；只有 `STBY=0` 才进入高阻待机。

对照 2.4 节把两层钉在一起：主循环里 `TB6612_SetSpeed(&motor_a, 40)` 落到芯片上就是 `IN1=1`、`IN2=0`、`PWMA` 收到 40% 占空比——正是真值表第一行"一个方向转动 + 闸门开四成"。

**输入 → 状态 → 输出**：带符号速度 → 驱动函数设置 `IN1/IN2` 和 `CCR` → TB6612 输出功率驱动 → 电机方向、速度和停止状态变化。**预期现象**：正转 1 s、短刹 0.2 s、反转 1 s、滑行停止 0.5 s 循环。短路刹车时电机应快速减速；若需要立刻停转用 `TB6612_Brake()`，需要高阻待机用 `TB6612_Standby()`。若状态不符，先量 `VM/VCC`、`STBY`、PWM 波形和 `IN1/IN2`。

## 3. 输入捕获与从模式

### 3.1 捕获时序与回绕

直觉画面：`CNT` 是一块一直在走的秒表，输入捕获就是"抓拍"——指定边沿出现的那一瞬，硬件自动把秒表当前读数抄进该通道的 `CCR`。CPU 在忙别的事也不会错过这一瞬；两次抓拍的读数相减，就是两个边沿之间的时间。这正是捕获比"软件轮询引脚"更适合测时序的原因。

输入捕获在指定边沿到来时把当前 `CNT` 自动锁存到通道的 `CCR`。设两次捕获值为 $N_1$、$N_2$，计数时钟为 $f_c$，则两次边沿之间的时间为：
=======
`Motor_SetPWM()` 接受带符号 `CCR`，正负表示方向，绝对值直接写入比较寄存器；驱动不换算、不限幅。上例的 1440 已在 ±3600 内；若指令来自按键、PID 或其他计算，主程序先按 `ARR+1`（本例 3600）限幅再调用：

```c
int16_t duty = 5000;              /* 示例值；实际来自按键、PID 或其他计算 */
if (duty >  3600) duty =  3600;   /* 限幅到 100% */
if (duty < -3600) duty = -3600;
Motor_SetPWM(duty);
```

实际转向还取决于电机线序，接反了就交换 `OUT1`/`OUT2`。`Motor_SetPWM(0)` 是短路刹车；要滑行，应让 `IN1=IN2=0`（PWM 电平不影响这个状态）。

现象是正转 1 s、短刹 0.2 s、反转 1 s、短刹 0.5 s，循环往复。

## 3. 输入捕获与从模式

### 3.1 捕获的原理

输入捕获把“写 `CCR` 让它比较”反过来：外部边沿到来时，硬件把当前 `CNT` 锁存进 `CCR`。路径是：

```text
引脚 → 极性选择 → 输入滤波与分频 → TI1FP1
     → 捕获比较器把 CNT 锁存进 CCR1
     → 同时送给从模式控制器
```

CPU 在忙别的事也不会错过这一瞬。两次捕获值 $N_1$、$N_2$ 之间经过的时间是：
>>>>>>> Stashed changes

$$
t=(N_2-N_1)\frac{1}{f_c}
$$

<<<<<<< Updated upstream
若 `PSC=71`、`f_TIM=72 MHz`，则 $f_c=1\,\mathrm{MHz}$，一个计数是 1 µs。计数器回绕时必须先做无符号模差，不能把两个 `uint32_t` 直接相减后指望强制转换恢复 16 位回绕：
=======
若 `PSC=71`、`f_TIM=72 MHz`，则 $f_c=1$ MHz，一个计数就是 1 µs，可以直接把计数当微秒用。计数器回绕时要用无符号模差：
>>>>>>> Stashed changes

```c
static uint16_t CaptureDelta16(uint16_t first, uint16_t second)
{
    return (uint16_t)(second - first);
}
```

<<<<<<< Updated upstream
该写法要求单次真实间隔小于计数器模数对应的时间；32 位定时器要使用 32 位无符号模差。举例：`first=65530`、`second=3` 时，普通减法得 -65527，截成 16 位后正好是 9，与真实间隔一致——无符号模差就是这样"自动消化"回绕的。输入捕获可测频率、周期、脉宽和占空比，但被测信号必须先转换为符合 STM32 输入电平要求的数字信号。

### 3.2 测频法、测周法与从模式

**测频法（M 法）**：在固定闸门时间 $T_g$ 内统计边沿数 $N$：

$$
f_x=\frac{N}{T_g}
$$

它适合较高频率，但结果更新较慢。**测周法（T 法）**：用已知计数频率 $f_c$ 数出相邻同类边沿间的 $N$：

$$
T_x=\frac{N}{f_c},\qquad f_x=\frac{f_c}{N}
$$

它通常每个周期更新一次，适合较低频率或单次事件。两种方法都有约一个计数的量化误差；测周法若希望相对误差约不超过 1%，应尽量使单次计数 $N\ge100$。令两种方法的计数规模相同，可用中界频率选择方法：

$$
f_m=\sqrt{\frac{f_c}{T_g}}
$$

低于 $f_m$ 优先测周法，高于 $f_m$ 优先测频法。本组实验的 PWM 输入用测周法，编码器速度用测频法。

用本组实验的参数算一遍：$f_c=1\,\mathrm{MHz}$、闸门 $T_g=100\,\mathrm{ms}$ 时，$f_m=\sqrt{10^6/0.1}\approx3.2\,\mathrm{kHz}$。实验六的被测信号是 1 kHz，低于 $f_m$，测周法正合适——每个周期数得 $N=1000$，约一个计数的量化误差折合 0.1%；若改用测频法，100 ms 只数到约 100 个边沿，同样一个计数的误差就放大到 1%。

从模式控制器由触发源和从模式共同决定 `CNT` 的行为：
=======
这要求单次间隔小于计数器模数对应的时间。

### 3.2 从模式：让硬件清 CNT

单靠捕获，CPU 还要记住上次的值再相减。从模式控制器可以把这一步也交给硬件：
>>>>>>> Stashed changes

| 从模式 | 触发后的行为 |
| --- | --- |
| Reset | 清零 `CNT` 后重新计数 |
| Gated | 触发有效时计数，无效时暂停 |
| Trigger | 触发后开始计数 |
| 外部时钟模式 1 | 选定的 `TIx/ITRx/ETR` 作为计数时钟 |

<<<<<<< Updated upstream
外部时钟模式 2 的 `ETR` 直接作计数时钟，不经过从模式控制器。把通道 1 设为 `TI1FP1` 上升沿捕获，同时把同一 `TI1FP1` 设为 `Reset` 触发源：每次上升沿先得到上一周期计数值，再把 `CNT` 清零，CPU 读取 `CCR1` 即可得到周期。触发标志 `TIF` 与更新标志 `UIF` 不同；同时使用两类中断时要分别处理。

顺带一提，编码器接口模式也写在同一组从模式选择位上：`TIM_ENCODERMODE_TI12` 在 HAL 头文件里就是 `TIM_SMCR_SMS_1 | TIM_SMCR_SMS_0`（即 `SMS=011`），可以把它当成专为正交解码设计的一种从模式。

### 3.3 输入捕获配置要点

1. 通道选择 `Input Capture direct mode` 或所需的捕获模式；
2. 设置捕获极性、输入滤波和输入分频，滤波越强延迟越大；
3. 需要自动测周时设置 `Slave Mode=Reset`、`Trigger Source=TIxFPx`；
4. 需要在中断中更新变量时，开启捕获中断并在 NVIC 中启用对应 `TIMx_IRQn`；只调用 `HAL_TIM_IC_Start_IT()` 而未启用 NVIC，CPU 不会进入回调；
5. 生成代码后检查 `HAL_TIM_IC_MspInit()` 中的 `HAL_NVIC_SetPriority()` / `HAL_NVIC_EnableIRQ()`；
6. 用中断时在 `HAL_TIM_IC_CaptureCallback()` 中用 `HAL_TIM_ReadCapturedValue()` 读取捕获值；信号持续存在时也可以用 `HAL_TIM_IC_Start()` 启动后在主循环中轮询 `CCR`。

轮询的好处是路径最短，适合信号持续存在、更新率要求不高的场合；信号可能随时消失、或需要在边沿后立刻响应时，才值得开捕获中断。

实验六采用 CubeMX 的 `PWM Input on CH1` 组合模式：CH1 直连 TI1 上升沿捕获，CH2 交叉到 TI1 下降沿捕获，TI1FP1 同时作为 Reset 触发源。这样两个通道都观察同一个 `PA6`，不需要再占用 `PA7`。

### 3.4 实验六：PWMI 测 PWM 频率和占空比

**目标**：用 TIM2 输出一路已知频率和占空比的 PWM，再由 TIM3 的 PWMI 通道同时测出它的频率和占空比。

PWMI 让两个捕获通道观察同一个引脚：CH1 直连 TI1、上升沿捕获，得到整个周期的计数；CH2 交叉到 TI1、下降沿捕获，得到高电平时间的计数；TI1FP1 同时作为 Reset 从模式的触发源，在每个上升沿把 `CNT` 清零。设 `CCR1` 为周期计数、`CCR2` 为高电平计数，则：
=======
把 CH1 设为 `TI1FP1` 上升沿捕获，同时把 `TI1FP1` 设为 Reset 触发源，每个上升沿先锁存上一周期计数值，再把 `CNT` 清零，读 `CCR1` 就是周期。捕获标志 `TIF` 和更新标志 `UIF` 不是一回事，同时用两类中断时要分别处理。

### 3.3 测频法与测周法

测频率有两条路：

$$
f_x=\frac{N}{T_g}\ \text{（测频法）},\qquad
f_x=\frac{f_c}{N}\ \text{（测周法）}
$$

| | 测频法 | 测周法 |
| --- | --- | --- |
| 数什么 | 固定闸门内的边沿数 | 相邻同类边沿之间的计数 |
| 适合 | 较高频率 | 较低频率或单次事件 |
| 更新速度 | 一个闸门出一次 | 每个周期出一次 |
| 误差 | 约一个计数 | 约一个计数，$N\ge100$ 时相对误差不超过约 1% |

中界频率是 $f_m=\sqrt{f_c/T_g}$。低于它用测周法，高于它用测频法。本章测 PWM 用测周法，测编码器速度用测频法。

### 3.4 捕获配置要点

通道选 `Input Capture direct mode`，设置捕获极性、输入滤波和分频；需要自动测周时把 `Slave Mode` 设为 `Reset`、`Trigger Source` 设为 `TIxFPx`。用中断时在 `HAL_TIM_IC_CaptureCallback()` 里读 `HAL_TIM_ReadCapturedValue()`；信号持续存在、更新率要求不高时，也可以在主循环轮询 `CCR`。

滤波越强，延迟越大。信号可能随时消失、或要在边沿后立刻响应时，才值得开捕获中断。

### 3.5 实验六：PWMI 测频率和占空比

用 TIM2 输出一路已知 PWM，由 TIM3 的 PWMI 模式同时测频率和占空比。CH1 观察上升沿得到整周期计数，CH2 交叉到同一引脚观察下降沿得到高电平计数，`TI1FP1` 同时作为 Reset 触发源。

![PWMI 的内部连接通路](image/pwmi-capture-path.png)
>>>>>>> Stashed changes

$$
f_{\mathrm{PWM}}=\frac{f_c}{\mathrm{CCR1}},\qquad
D=\frac{\mathrm{CCR2}}{\mathrm{CCR1}}\times100\%
$$

<<<<<<< Updated upstream
**接线**：`PA0/TIM2_CH1 -> PA6/TIM3_CH1`，用一根杜邦线把同一块板上的输出端接到输入端。PA6 在 STM32F103 上不是 5 V 容忍引脚，外部 PWM 信号也必须限制在 3.3 V 以内。为什么让定时器自发自收？因为被测 PWM 由 TIM2 自己产生，频率和占空比都是软件写下的已知量，测出的结果应当精确等于设定值。有标准答案的测量，才能把"捕获配置错了"和"信号本身不对"干净地分开；这条链路调通之后，换成测任何真实信号都只是换接线。

**输出端配置**：TIM2 选择 `PWM Generation CH1`，PWM mode 1、Polarity High，`PSC=719`、`ARR=99`，运行时把 `CCR1` 设为 `50`：
=======
接线：`PA0/TIM2_CH1 → PA6/TIM3_CH1`，一根杜邦线即可。PA6 不是 5 V 容忍引脚，外部信号必须限制在 3.3 V 以内。

CubeMX 中 `PA0` 设为 `TIM2_CH1`，`TIM2` 选 `PWM Generation CH1`，`PSC=719`、`Counter Period=99`；`PA6` 设为 `TIM3_CH1`，`TIM3` 的 `Channel1` 选 `PWM Input on CH1`，`PSC=71`、`Counter Period=65535`，确认 `Slave Mode=Reset`、`Trigger Source=TI1FP1`。

输出端 100 个计数、计数频率 100 kHz，得到 1 kHz 方波：
>>>>>>> Stashed changes

$$
f_{\mathrm{PWM}}=\frac{72\,\mathrm{MHz}}{(719+1)(99+1)}=1\,\mathrm{kHz}
$$

<<<<<<< Updated upstream
**捕获端配置**：TIM3 选择组合通道 `PWM Input on CH1`。CH1 为 `Input Capture direct mode`、上升沿；CH2 为交叉 TI1、下降沿；`PSC=71` 使标准计数频率 $f_c=1\,\mathrm{MHz}$，`ARR=65535`；`Slave Mode=Reset`、`Trigger Source=TI1FP1`。本例用主循环轮询 `CCR`，不开启捕获中断和 `TIM3_IRQn`。生成代码中应能看到两次 `HAL_TIM_IC_ConfigChannel()` 和一次 `HAL_TIM_SlaveConfigSynchro()`；缺任一项都得不到完整的周期和高电平时间。

CubeMX 的入口是 `Timers → TIM3`：`Mode` 区把 `Channel1` 下拉选成组合项 `PWM Input on CH1`（不要给两个通道分别选 Input Capture 模式），选好后 `Parameter Settings` 里 `Slave Mode` 选 `Reset`、`Trigger Source` 选 `TI1FP1`。如果跳过组合项、只把两个通道分别配成捕获而不设 `Reset`，`CNT` 不再被上升沿清零，`CCR1` 读数会带上随机的计数起点——只有两次上升沿读数的 16 位模差才是周期，直接把 `CCR1` 当周期会漂移。
=======
捕获端 `PSC=71` 把计数频率降到 1 MHz，`ARR=65535` 留满量程。本例轮询 `CCR`，不开捕获中断。
>>>>>>> Stashed changes

```c
#include "tim.h"

#define TEST_PWM_DUTY 50U

uint32_t pwm_frequency_hz = 0U;
uint32_t pwm_duty_percent = 0U;

static void Pwm_Measure(void)
{
    uint16_t period = (uint16_t)HAL_TIM_ReadCapturedValue(&htim3, TIM_CHANNEL_1);
    uint16_t high = (uint16_t)HAL_TIM_ReadCapturedValue(&htim3, TIM_CHANNEL_2);

    if (period == 0U)
    {
        pwm_frequency_hz = 0U;
        pwm_duty_percent = 0U;
        return;
    }

    pwm_frequency_hz = 1000000UL / period;
    pwm_duty_percent = ((uint32_t)high * 100UL) / period;
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM2_Init();
    MX_TIM3_Init();

    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, TEST_PWM_DUTY);
    HAL_TIM_IC_Start(&htim3, TIM_CHANNEL_1);
    HAL_TIM_IC_Start(&htim3, TIM_CHANNEL_2);
    HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1);

    while (1)
    {
        Pwm_Measure();
        HAL_Delay(100U);
    }
}
```

<<<<<<< Updated upstream
`HAL_TIM_ReadCapturedValue()` 是读通道 `CCR` 的封装，直接访问 `htim3.Instance->CCR1` 效果相同。`TIM_CHANNEL_1` 和 `TIM_CHANNEL_2` 都要启动；只启动一个通道时，另一个通道不会更新捕获值。`period` 是 16 位无符号数，除法前必须判断是否为 0；启动后尚未捕获到信号时，`CCR1` 也会保持 0。

**输入 → 状态 → 输出**：PA0 PWM 波形 → 导线送到 PA6 → TIM3 把周期写入 `CCR1`、把高电平时间写入 `CCR2` → 软件换算为 `pwm_frequency_hz` 和 `pwm_duty_percent`。**预期现象**：调试器中 `htim3.Instance->CCR1` 约为 `1000`、`CCR2` 约为 `500`，`pwm_frequency_hz` 约为 `1000`，`pwm_duty_percent` 约为 `50`。把 `TEST_PWM_DUTY` 改为 `20` 后，频率不变而占空比应接近 `20%`。启动后从未接导线时，两个测量值为 `0`；运行中断开导线，读数会停留在最后一次结果（PA6 悬空还可能随机跳变）——这正是本节末尾"CCR 会保留最后一次测量值"的表现。

`f_c=1 MHz`、`ARR=65535` 时不溢出的理论最低频率约为：

$$
f_{\min}=\frac{10^6}{65536}\approx15.26\,\mathrm{Hz}
$$

回环用的 PWM 由开发板自己产生，信号一直存在，因此本例不需要超时。若以后接入可能停止的外部 PWM，`CCR` 会保留最后一次测量值，需要配合捕获或更新标志判断信号是否已经中断。

## 4. 编码器接口

### 4.1 正交信号、方向与四倍频

增量编码器的 A、B 两路方波相差约 90°。方向就藏在"谁先翻转"里：正转时 A 相先于 B 相变化，反转时次序相反；硬件盯住这个先后关系自动加减 `CNT`，全程不需要 CPU 参与。使用两路的上升沿和下降沿共同计数时，一组完整正交周期通常得到 4 个计数，即四倍频。模式与实际计数边沿的对应关系是：

| 模式 | 计数边沿 | HAL 参数 |
| --- | --- | --- |
| 编码器模式 1 | TI2FP2 的两个边沿，TI1FP1 判方向 | `TIM_ENCODERMODE_TI1` |
| 编码器模式 2 | TI1FP1 的两个边沿，TI2FP2 判方向 | `TIM_ENCODERMODE_TI2` |
| 编码器模式 3 | TI1FP1、TI2FP2 的边沿都计数 | `TIM_ENCODERMODE_TI12` |

模式 1 的宏名不表示"只在 TI1 计数"，这是寄存器定义的固定对应关系。`Rising` 表示不反相该路输入，不表示只捕获上升沿；反相一路或交换 A/B 接线会改变方向符号。

本组实验使用 `TIM1`：A 相接 `PA8/TIM1_CH1`，B 相接 `PA9/TIM1_CH2`，两路与 STM32 共地；编码器装在电机上时，编码器地仍须与 STM32/驱动地共地。A/B 两相的接线核对：

| 编码器 | STM32 |
| --- | --- |
| A 相 | `PA8`（`TIM1_CH1`） |
| B 相 | `PA9`（`TIM1_CH2`） |
| 电源正极 | 按模块规格 |
| 地 | 与 STM32 共地 |

开漏 A/B 输出按模块规格上拉到 3.3 V；其他输出电平必须符合 STM32 输入范围，若超过 3.3 V 应分压或电平转换。CubeMX 选择 `Encoder Mode=TI1 and TI2`，两路 `Input Filter` 按机械噪声设置，`IC1/IC2 Polarity=Rising`（`TIM_ENCODERINPUTPOLARITY_RISING`），`PSC=0`、`ARR=65535`，生成代码后调用 `HAL_TIM_Encoder_Start()`。本组工程里两路滤波值都是 0（`IC1Filter/IC2Filter=0`）；该字段取值范围 `0x0~0xF`，数值越大滤波越强、延迟越大，读数跳变时可加大。工程还给 PA8/PA9 配了内部上拉（`GPIO_PULLUP`），A/B 为开漏输出时它就是那把上拉电阻；模块明确要求外接上拉的，仍按模块规格接。

### 4.2 实验七：编码器方向与增量验证

**目标**：读取 `TIM1` 的有符号增量；检测到非零增量时翻转 PC13，并用调试器观察 `delta` 的正负。
=======
两个捕获通道都要启动，只启动一个时另一个不会更新。`CCR1` 启动后还没捕获到信号时是 0，除法前必须判断。

现象：`CCR1` 约 1000、`CCR2` 约 500，频率约 1000 Hz，占空比约 50%。把 `TEST_PWM_DUTY` 改成 20，频率不变、占空比接近 20%。

## 4. 编码器接口

### 4.1 硬件判向

增量编码器的 A、B 两路方波相差约 90°，方向藏在“谁先翻转”里。定时器内部状态机每来一个边沿，就根据另一相的电平决定加一还是减一，不需要 CPU 参与。

| 模式 | 计数边沿 | 判向来源 | 分辨率 | HAL 参数 |
| --- | --- | --- | --- | --- |
| 模式 1 | TI1 的边沿 | TI2 电平 | x2 | `TIM_ENCODERMODE_TI1` |
| 模式 2 | TI2 的边沿 | TI1 电平 | x2 | `TIM_ENCODERMODE_TI2` |
| 模式 3 | TI1、TI2 两边沿 | 另一相电平 | x4 | `TIM_ENCODERMODE_TI12` |

本章选模式 3，A、B 两相的每个边沿都计数，分辨率最高。

![编码器接口内部结构](image/encoder-interface-block.png)

![正交编码器波形与判向真值表](image/encoder-quadrature.png)

本实验用 TIM1：A 相接 `PA8/TIM1_CH1`，B 相接 `PA9/TIM1_CH2`，编码器与 STM32 共地。CubeMX 中 `Encoder Mode` 选 `TI1 and TI2`，`IC1/IC2 Polarity=Rising`，`PSC=0`、`ARR=65535`，输入滤波先保持 0；读数跳变时再加大，数值越大延迟越大。

### 4.2 实验七：读取方向与增量
>>>>>>> Stashed changes

```c
static uint16_t last_count = 0U;

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM1_Init();
    HAL_TIM_Encoder_Start(&htim1, TIM_CHANNEL_ALL);

    last_count = (uint16_t)__HAL_TIM_GET_COUNTER(&htim1);

    while (1)
    {
        uint16_t now = (uint16_t)__HAL_TIM_GET_COUNTER(&htim1);
        uint16_t raw_delta = (uint16_t)(now - last_count);
        int16_t delta = (int16_t)raw_delta;
        last_count = now;

        if (delta != 0)
        {
            HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
        }
        HAL_Delay(100U);
    }
}
```

<<<<<<< Updated upstream
**输入 → 状态 → 输出**：A/B 边沿 → 编码器接口按方向修改 `CNT` → 主循环先做 16 位模差再得到 `delta` → 非零时翻转 PC13。**预期现象**：旋转旋钮时 `delta` 出现正负变化；实际正负号取决于 A/B 接线和器件方向，必须在实物上校准。如果看到 X，说明 Y：`delta` 恒为 0，先查 A/B 两线、共地和 `HAL_TIM_Encoder_Start()` 是否传了 `TIM_CHANNEL_ALL`；只能单方向计出数值，多半是一相接触不良——判向需要两相信号都到齐（具体表现待实测）；`delta` 偶发大幅跳变，先查接线噪声，再加大两路输入滤波。

主循环里的 `HAL_Delay(100)` 就是 4.3 节所说的采样闸门 $T_g=100\,\mathrm{ms}$：缩短它，响应更快，但同样的误差要求下单次增量变小、速度分辨率变粗。

### 4.3 位置、速度与电机反馈

直接把 `CNT` 当作相对位置时，可将 16 位无符号计数解释为 `int16_t`：

```c
static int16_t EncoderPosition(void)
{
    return (int16_t)__HAL_TIM_GET_COUNTER(&htim1);
}
```

它只适合在零点附近的回绕表示；长行程需要更宽的软件累加器。速度属于测频法：在固定闸门时间 $T_g$ 内读取增量 $\Delta CNT$，若每转产生 $C$ 个计数，则：

$$
n_{\mathrm{r/min}}=\frac{60\,\Delta CNT}{C\,T_g}
$$

编码器模式 3 且编码器标称为每转 $P$ 个单相脉冲时，$C=4P$；装在减速电机轴上还要乘减速比。举个只用代数的例子：设某编码器每转 $P=500$ 线，四倍频下 $C=2000$，采样闸门 $T_g=10\,\mathrm{ms}$ 内数得 $\Delta CNT=500$，则 $n=60\times500/(2000\times0.01)=1500\,\mathrm{r/min}$；调试时也常倒过来用——从目标分辨率反推闸门该取多长。

16 位有符号模差能恢复单次增量的前提是：

$$
|\Delta CNT|<32768
$$

高速电机应缩短采样闸门，避免单次增量跨过半个计数范围。不要在主循环中读完计数器后强行清零，因为读取与清零之间到达的边沿会丢失。

编码器反馈接入 TB6612 时，控制关系是：

```text
A/B 编码器信号 -> 定时器 CNT -> 采样窗口 delta -> 速度误差
-> 限幅后的 PWM 命令 -> TB6612 -> 电机
```

先用固定基础 PWM 校准电机方向和反馈符号，再调节 PWM；不要让未经处理的负误差直接变成反向命令。换向、传感器异常或上电状态不确定时应先停机。

## 5. 本章验收

- [ ] 时基工程的实际周期已测量；
- [ ] PWM 工程的频率、占空比和通道引脚已记录；
- [ ] PWMI 工程的频率和占空比与设定值一致；
- [ ] 电机、舵机和编码器实验的接线与限流已确认；
- [ ] 能复述一次更新中断从 CNT 归零到进入回调的完整路径；
- [ ] 每个子工程都能单独编译和下载。

## 6. 按信号链排错

先按"供电与共地 → 引脚/复用功能 → 时钟源与参数 → 初始化与启动 → 中断/状态 → 输出"的顺序排查，能快速区分硬件映射、配置和控制逻辑问题。

| 症状 | 优先检查 | 可区分的原因 |
| --- | --- | --- |
| `g_tick` 不变或周期不对 | `MX_TIM4_Init()`、`PSC/ARR`、APB 定时器时钟、`HAL_TIM_Base_Start_IT()`、NVIC、回调中的 `Instance` | 不变通常是未启动或 NVIC/回调未通；差 2 倍通常是误把 `PCLK1=36 MHz` 当成 `f_TIM` |
| TIM2 外部计数为 0 | `PA0/ETR`、共地、输出电平、`ETR2`、`HAL_TIM_Base_Start()` | 引脚电平不对时 `CNT` 不动；电平正常但计数抖动，查极性、滤波和传感器毛刺 |
| PWM 引脚没有波形 | `PA6` 复用、`MX_TIM3_Init()`、`HAL_TIM_PWM_Start()`、`PSC/ARR/CCR` | 没有波形查启动和复用；有波形但亮度不对查 `CCR` 范围、Polarity 和限流电阻 |
| 舵机不转或抖动 | PB8/CH3、50 Hz、1 MHz 计数、脉宽范围、独立 5 V、共地 | 频率正确但抖动优先查电源压降和脉宽；完全不响应查信号脚与地线 |
| 电机不转、方向错或刹车异常 | `VM/VCC`、`STBY`、PWM 波形、IN1/IN2、空载低占空比 | 四者都正确仍无动作查 H 桥和电机；方向错先交换 IN 定义，不要高速直接反向 |
| 频率和占空比都是 0 | PA0 到 PA6 的导线、PA6 输入、`HAL_TIM_IC_Start()` 是否分别启动 CH1/CH2 | 导线未接时 `CCR1`/`CCR2` 保持 0；只启动一个通道时另一个通道不更新 |
| 频率差 2 倍或占空比不对 | TIM2/TIM3 的 `PSC/ARR`、CH1 直连上升沿、CH2 交叉下降沿、Reset + TI1FP1、`period` 为 0 的判断 | 频率差 2 倍先查误用 `PCLK1=36 MHz`；占空比偏差大先查两个通道的直连/交叉与极性是否被配置成相同边沿 |
| 编码器 `delta` 方向相反或跳变 | PA8/PA9 A/B 相、编码器模式、输入滤波、16 位模差 | 不计数查接线和 `HAL_TIM_Encoder_Start()`；方向相反交换 A/B 或校准符号；大跳变先查噪声和采样闸门 |

若能在接入负载前用示波器或逻辑分析仪确认频率、极性、占空比和边沿，再接舵机或电机，通常能把配置问题与驱动/供电问题分开。

这张排错表里的每一项都能在配套工程中找到具体落点。排查时先打开对应工程按文件对照，再回到自己的 `MyCode` 比对：

| 检查项 | 工程中的位置 |
| --- | --- |
| `PSC/ARR`、通道模式、极性、从模式、编码器模式 | 各子工程 `Core/Src/tim.c` 的 `MX_TIMx_Init()` |
| NVIC 使能与优先级 | `tim.c` 的 `HAL_TIM_Base_MspInit()`（本组只有实验一启用） |
| 中断入口 `TIMx_IRQHandler` | `Core/Src/stm32f1xx_it.c` |
| PA6/PB8/PA0 等复用引脚 | `tim.c` 的 `HAL_TIM_MspPostInit()`；方向、`STBY` 等普通 GPIO 在 `main.c` 的 `MX_GPIO_Init()` |
| `f_TIM` 的来源（72 MHz） | `main.c` 的 `SystemClock_Config()`（原理见第 3 章） |
| 用户逻辑、回调与驱动 | `main.c` 的 `USER CODE` 区域；TB6612 驱动在 `User/Drivers/TB6612/` |

配置类故障大多在这一轮"对照标准答案"中现形；对照后仍然复现的，才轮到示波器或逻辑分析仪上板。
=======
`HAL_TIM_Encoder_Start()` 必须传 `TIM_CHANNEL_ALL`，它同时使能两个捕获通道。先做 16 位模差再转成 `int16_t`，正转增量为正，反转增量为负。`HAL_Delay(100)` 是采样闸门，缩短它响应更快，但同样误差下速度分辨率会变粗。

### 4.3 驱动库写法

`E:\ProjectStm\驱动库\ENCODER` 采用“读后清零”：

```c
void Encoder_Init(void);
int16_t Encoder_Get(void);   /* 返回上次调用以来的增量，并清零 CNT */
```

主循环只剩 `int16_t delta = Encoder_Get();`。`Encoder_Init()` 要放在 `MX_TIM1_Init()` 之后调用。这个函数只能有一个调用者，读和清不是原子操作，窗口内的边沿可能丢失；高速连续测速时仍用上面的自由计数加模差方案。驱动默认绑定 `TIM3`（`PA6/PA7`），换到本章的 `TIM1` 只需改 `encoder.h` 的 `ENCODER_HANDLE`。

倒立摆把定时器固定成 TIM1 1 ms 按键节拍、TIM2 20 kHz 电机 PWM、TIM3 编码器接口；本章的七个实验是为了逐项看清用法，综合时按 [[STM32倒立摆/03 基础驱动：CubeMX与HAL库实现#1.4 本工程的引脚与外设总表]] 恢复固定引脚，不能把各实验的 `.ioc` 直接拼接。
>>>>>>> Stashed changes

上一篇：[[04 中断系统：EXTI 与 NVIC 优先级]] ｜ 下一篇：[[06 ADC：量化、采样时间与单次转换]]
