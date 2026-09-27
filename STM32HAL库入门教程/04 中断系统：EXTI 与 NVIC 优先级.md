# 04 中断系统：EXTI 与 NVIC 优先级

## 本章问题

外部信号怎样经过 EXTI 和 NVIC 到达 HAL 回调，并且不破坏共享中断线路？

前几章中，程序主要依靠主循环主动检查外部状态：第 1 章反复调用 `HAL_GPIO_ReadPin()` 读取按键，第 0 章用 `HAL_Delay()` 等待。这一章改用硬件在事件发生时通知 CPU。要让通知抵达用户代码，需要串起三层机制：**EXTI**（外部中断/事件控制器）检测引脚边沿，**NVIC**（嵌套向量中断控制器）决定响应时机和顺序，**HAL 回调**把事件交给业务代码。

本章配套两个独立 CubeMX 工程：`E:\ProjectStm\Courses\HAL04_EXTI_NVIC\01_IR_PB14`（红外计次）和 `E:\ProjectStm\Courses\HAL04_EXTI_NVIC\02_Encoder_PB0_PB1`（编码器判向），分别对应第 5、6 节。第 4.2 节会讲一个回调如何同时服务多条 EXTI 线——技术上完全可以把两个实验合并进一个工程；这里仍拆成两个，是为了让每个实验保持最小、互不牵连。

## 学习目标

- 画出 GPIO、EXTI、NVIC、IRQHandler 和 HAL 回调的执行链；
- 在 CubeMX 中配置 EXTI 引脚、触发边沿和 NVIC IRQ；
- 根据抢占优先级和响应优先级安排中断嵌套顺序；
- 用 `volatile` 计数器完成 PB14 红外计次；
- 用 PB0/PB1 的 A/B 相信号判断编码器方向。

## 1. 中断解决什么问题

### 1.1 先建直觉：医生坐诊，不要门口盯人

把 CPU 想成一位只坐在诊室里的医生，把"外部事件"想成来就诊的病人：

- **轮询**相当于医生每隔几秒跑到大门口张望一次："有人吗？没人？再等几秒再来看。"病人在两次张望之间来了又走，医生就完全不知道；而且医生大部分时间花在"跑去看"这件事上，没工夫看病。
- **中断**相当于在诊室里装一个叫号铃：病人一到门口按下按钮（硬件置位），铃响（NVIC 收到请求），医生把手头的病历先合上（保存现场），出去看一眼再回来接着写（恢复现场）。医生只需要专注于手头的工作，一个也不会漏。

对应到芯片上：主循环是医生的本职工作，中断服务函数是"按铃后的处理"。中断的本质是**硬件替你盯着输入，事件来了才叫人**。

### 1.2 轮询代码的两个漏洞

轮询是在主循环中反复读取输入：

```c
while (1)
{
    if (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_14) == GPIO_PIN_RESET)
    {
        count++;
    }
}
```

这段"看起来能跑"的代码有两个漏洞：

- **分不清"一次事件"和"保持状态"**。持续低电平会被读取很多次——遮挡不放开的 1 秒里可能 `count` 已经加了几万次，而你想数的只是"遮了一次"。要区分两者就得自己记上一次的电平，代码越来越绕；
- **短脉冲会完全错过**。主循环被刷新、延时或其他任务占用时（比如正在跑一轮 OLED 刷新），一个只有几微秒宽的脉冲可能恰好在两次读取之间出现又消失，CPU 根本没看到。

中断由硬件在事件到来时请求 CPU，主循环不必持续检查输入：边沿检测这一步完全由 EXTI 硬件完成，哪怕主循环正在 `HAL_Delay(500)` 里干等，边沿也不会丢（EXTI 检测到边沿会先置位挂起寄存器，等 CPU 有空就响应）。

### 1.3 一次中断的完整执行链

GPIO EXTI 的完整执行链为：

```text
外部电平变化
-> GPIO 输入
-> EXTI 按上升沿/下降沿检测并置位 EXTI_PR
-> NVIC 按优先级决定是否响应
-> IRQHandler
-> HAL_GPIO_EXTI_IRQHandler() 检查并清除挂起位
-> HAL_GPIO_EXTI_Callback() 更新计数或状态
-> 返回被中断的代码
```

把这条链路逐层展开：

| 层 | 谁在做 | 做什么 |
| --- | --- | --- |
| 电平变化 / GPIO 输入 | 外部电路 + GPIO 硬件 | 红外模块 DO 翻转、编码器 A 相跳变，电平经引脚送进 EXTI |
| EXTI | EXTI 硬件 | 按配置的边沿方向检测，命中则把 `EXTI_PR` 对应位置 1（挂起位） |
| NVIC | NVIC 硬件 | 看该 IRQ 是否使能、优先级是否够高，决定"现在响应"还是"排队" |
| IRQHandler | 启动文件 + CubeMX 生成的 `stm32f1xx_it.c` | 芯片根据向量表跳进 `EXTI15_10_IRQHandler()` 这类函数 |
| HAL 中间层 | HAL 库 | `HAL_GPIO_EXTI_IRQHandler()` 查挂起位、清挂起位、调回调 |
| 用户回调 | 你写的 `app_exti.c` | `HAL_GPIO_EXTI_Callback()` 里区分引脚、改计数 |
| 返回 | 硬件自动 | 恢复现场，回到主循环被打断的那一行继续跑 |

注意"保存/恢复现场"由硬件自动完成，你不需要写任何入栈出栈代码——这是 Cortex-M3 内核替你做的，也是中断用起来"像函数调用"的原因。

### 1.4 回调里只做三件事

中断回调应只完成"确认引脚、读取必要电平、修改少量状态"。OLED 刷新、串口打印、耗时计算和等待操作放到主循环中，避免长时间占用当前中断。

为什么要这么苛刻？中断在执行时，同级和更低优先级的中断都在排队。如果回调里刷一屏 OLED（I2C 整帧刷新约 100 ms，第 2 章算过这笔账），这段时间内再来的编码器脉冲就会丢失或延迟。本章实验的回调都只做"读一次电平、改一个计数变量"这种微秒级的工作，把显示和判断交给主循环。

## 2. EXTI 线路、寄存器与 HAL

### 2.1 EXTI 线路按引脚编号共享

STM32F1 的 EXTI 线路对应引脚编号而不是端口对象：`PA0`、`PB0`、`PC0` 都连接 `EXTI0`，但同一时刻只能选择其中一个端口。可以把 EXTI 想成一栋 16 层的楼：第 0 层（EXTI0）只有一个窗口，PA0、PB0、PC0 都想从这个窗口进出，但窗口同一时刻只接向其中一个端口。配置 `PB14` 时，GPIO 先进入 `EXTI14`，AFIO 再把 `EXTI14` 的源端口选为 GPIOB：

```text
PB14 -> EXTI14 -> AFIO_EXTICR[3] 选择 GPIOB
```

若 `PA14` 或 `PC14` 后来也配置为 `EXTI14`，后一次端口选择会覆盖前一次——表现为"原来那路中断莫名其妙不触发了"，排查时很难想到是另一个引脚抢走了窗口。

STM32F1 中还要区分两个 AFIO 寄存器的分工：

- `AFIO_EXTICR`：选择 EXTI 线路连接哪个 GPIO 端口；
- `AFIO_MAPR`：处理外设引脚重映射和 SWJ 配置，不负责选择 EXTI 源端口。

AFIO 本身也是一个外设，使用前要先开时钟。配套工程的 `Core/Src/stm32f1xx_hal_msp.c` 里，`HAL_MspInit()` 开头就有（CubeMX 生成，不需要手写；但要知道作用——少了 AFIO 时钟，"选择源端口"这一步就写不进去）：

```c
__HAL_RCC_AFIO_CLK_ENABLE();
__HAL_RCC_PWR_CLK_ENABLE();
```

### 2.2 关键寄存器与 HAL 调用

| 环节 | 关键寄存器 | HAL/CubeMX 行为 |
| --- | --- | --- |
| 选择 EXTI 源端口 | `AFIO_EXTICR` | `HAL_GPIO_Init()` 根据 GPIO 端口和引脚号写入端口选择字段 |
| 选择触发边沿 | `EXTI_RTSR`、`EXTI_FTSR` | GPIO 模式中的 `RISING`、`FALLING` 或双边沿决定配置 |
| 记录待处理事件 | `EXTI_PR` | 硬件置位，`HAL_GPIO_EXTI_IRQHandler()` 检查并清除 |
| 产生软件请求 | `EXTI_SWIER` | 不经过 GPIO 引脚变化，直接请求 EXTI 事件或中断 |
| NVIC 使能与优先级 | NVIC 的使能位、优先级寄存器 | `HAL_NVIC_EnableIRQ()`、`HAL_NVIC_SetPriority()` |

翻译成大白话：

- `EXTI_RTSR`/`EXTI_FTSR` 是两个"方向开关"：RTSR 管上升沿（0→1）、FTSR 管下降沿（1→0），开哪个就检测哪种边沿，两个都开就是双边沿；
- `EXTI_PR` 是"留言板"：边沿发生后对应位被硬件置 1，相当于"有一件事没处理"。软件向这一位写 1 才能清零（这是 F1 的特殊约定：写 1 清除，写 0 无效），留言被清掉后，同一根线才能记录下一次事件；
- `EXTI_SWIER` 平时用不到，它允许你不碰引脚、纯软件"假装"来了一次边沿，常用于测试。

在 CubeMX 中把 `PB14` 设置为 `GPIO_EXTI14` 并生成代码后，HAL 初始化链会配置 GPIO 模式、EXTI 源端口、触发边沿和中断屏蔽——你在图形界面里点的那几下，最终都落到上面这几个寄存器。

### 2.3 事件与中断是两条路

EXTI 检测到边沿之后有两条出路。EXTI 产生"事件"只可供其他硬件动作使用（比如直接触发 ADC、定时器，不经过 CPU）；向 NVIC 提交中断请求并执行应用代码时，使用的是中断路径。

CubeMX 里选引脚模式时能同时看到这两族选项，它们与 HAL 宏一一对应（来自工程内 `stm32f1xx_hal_gpio.h`）：

| CubeMX 模式族 | HAL 宏 | 去向 |
| --- | --- | --- |
| 中断模式 | `GPIO_MODE_IT_RISING` / `GPIO_MODE_IT_FALLING` / `GPIO_MODE_IT_RISING_FALLING` | 请求 NVIC，最终进入你的回调 |
| 事件模式 | `GPIO_MODE_EVT_RISING` / `GPIO_MODE_EVT_FALLING` / `GPIO_MODE_EVT_RISING_FALLING` | 只产生硬件事件信号，不进 NVIC，回调永远不执行 |

本章工程全部使用中断模式（`01_IR_PB14` 的 PB14 生成的就是 `GPIO_MODE_IT_FALLING`）。新手最常见的相关错误是"模式选成了 EVT，代码怎么写都不进中断"——事件模式根本不会向 NVIC 提请求。

## 3. NVIC 优先级关键规则

### 3.1 抢占优先级与响应优先级

接着 1.1 节的医院类比，把两个优先级概念分开。想象诊室里已经有医生在看病人（CPU 正在执行某个中断）：

- **抢占优先级**是"科室级别"：级别高的医生可以直接推门打断正在问诊的医生，让他先停下。对应到 NVIC——抢占优先级决定一个中断能否打断当前正在执行的中断；
- **响应优先级（子优先级）**是"同科室里挂号先后"：两个同级医生同时到门口时，先叫号牌靠前的。但它**不能**打断已经开始问诊的人——响应优先级只决定多个同级抢占中断同时挂起时谁先执行，不能打断同级中断。

STM32 NVIC 的优先级编号越小，优先级越高：`0` 比 `3` 更紧急。可以把编号理解成"VIP 等级号"，0 号最高。

Cortex-M3 实现 4 位优先级，也就是说每个中断的优先级数值总共只有 4 个二进制位可用（0~15）。这 4 位怎么在"抢占"和"响应"之间分配，由优先级分组决定。`HAL_Init()` 默认调用：

```c
HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);
```

HAL 头文件 `stm32f1xx_hal_cortex.h` 中定义了全部五种分组的位数划分：

| 分组 | 抢占优先级位数 | 响应优先级位数 |
| --- | ---: | ---: |
| `NVIC_PRIORITYGROUP_0` | 0 位 | 4 位 |
| `NVIC_PRIORITYGROUP_1` | 1 位 | 3 位 |
| `NVIC_PRIORITYGROUP_2` | 2 位 | 2 位 |
| `NVIC_PRIORITYGROUP_3` | 3 位 | 1 位 |
| `NVIC_PRIORITYGROUP_4` | 4 位 | 0 位 |

`NVIC_PRIORITYGROUP_4` 表示 4 位抢占优先级、0 位响应优先级，因此默认分组下只有 `0~15` 的抢占等级，HAL 调用中的子优先级参数没有实际裁决作用——写多少都是 0，不起作用。若要使用响应优先级，必须先统一修改优先级分组，再为所有相关中断重新分配位数和数值（改分组会影响整个芯片所有中断的位数划分，不是单个中断的局部设置）。

CubeMX 通常在 MSP 初始化中生成等价代码：

```c
HAL_NVIC_SetPriority(EXTI15_10_IRQn, 2U, 0U);
HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);
```

`HAL_NVIC_SetPriority()` 的三个参数依次是：IRQ 编号、抢占优先级、响应优先级（子优先级）。`HAL_NVIC_EnableIRQ()` 把该 IRQ 在 NVIC 里的"允许响应"开关打开。

优先级分组必须先于 `HAL_NVIC_SetPriority()` 设置。看主函数的实际调用顺序（两个工程 `Core/Src/main.c` 相同）：`HAL_Init()` 内部先设分组 4、再配置 SysTick、最后调用 `HAL_MspInit()`（位于 `Core/Src/stm32f1xx_hal_msp.c`，本章工程在其中配置了 EXTI 的优先级和使能）→ `SystemClock_Config()` 把时钟配到 72 MHz（第 3 章）→ `MX_GPIO_Init()` 由 `HAL_GPIO_Init()` 配置 GPIO/EXTI。顺序保证了"先定分组规则，再填具体数值"。

配套工程中这两个调用放在 `HAL_MspInit()` 的 `USER CODE BEGIN MspInit 1` 区域内（`01_IR_PB14` 为 `EXTI15_10_IRQn`，`02_Encoder_PB0_PB1` 为 `EXTI0_IRQn`），这一区域同样不会被重新生成代码覆盖。

入门工程可使用默认分组和明确规划的抢占等级，不要把所有中断都随意设为 `0`——全部设 0 意味着任何中断都不能打断任何中断，失去嵌套能力，而且以后每加一个中断都要回头重排所有数值。

### 3.2 本章工程实际使用的分组与数值

两个工程的 `.ioc` 中 NVIC 配置完全一致（以 `01_IR_PB14` 的 `.ioc` 为例。`.ioc` 里冒号带转义符，实际写作 `true\:2\:0\:...`，下面已简化为可读格式）：

```text
NVIC.PriorityGroup=NVIC_PRIORITYGROUP_4
NVIC.EXTI15_10_IRQn=true:2:0:...     （02 工程为 NVIC.EXTI0_IRQn=true:2:0:...）
NVIC.SysTick_IRQn=true:15:0:...
```

逐项解读：

- **分组**：`NVIC_PRIORITYGROUP_4`，4 位全给抢占优先级，子优先级无裁决作用（第 3.1 节）；
- **EXTI 中断**：使能，抢占优先级 `2`、响应优先级 `0`。对应生成代码就是上面的 `HAL_NVIC_SetPriority(EXTI15_10_IRQn, 2U, 0U); HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);`；
- **SysTick**：使能，抢占优先级 `15`、响应 `0`。`15` 是全场最低，来自 `Core/Inc/stm32f1xx_hal_conf.h` 中的 `TICK_INT_PRIORITY 15U`（HAL 注释即 "lowest by default"）。SysTick 是 `HAL_GetTick()`/`HAL_Delay()` 的时基（`stm32f1xx_it.c` 里的 `SysTick_Handler()` 每次中断调用 `HAL_IncTick()`）。把它放到最低的效果是：你的 EXTI 回调（抢占 2）可以随时打断 SysTick，反过来 SysTick 永远不会打断你的回调——计数的时序不会被系统时基插队。同一张优先级表里还登记了 HardFault、NMI 等系统异常（`.ioc` 中可见），本章不需要改动它们。

### 3.3 多条 EXTI 线路共享一个 IRQ

16 条 EXTI 线路并不对应 16 个 NVIC 入口，F103 把它们打包成 7 个 IRQ：

| EXTI 线路 | NVIC IRQ | IRQHandler |
| --- | --- | --- |
| EXTI0~EXTI4 | 对应的 `EXTIn_IRQn` | `EXTI0_IRQHandler()`~`EXTI4_IRQHandler()` |
| EXTI5~EXTI9 | `EXTI9_5_IRQn` | `EXTI9_5_IRQHandler()` |
| EXTI10~EXTI15 | `EXTI15_10_IRQn` | `EXTI15_10_IRQHandler()` |

EXTI0~4 每条线独享一个 IRQ；5~9 和 10~15 则五条线挤在一个 IRQ 里。由此产生两个直接后果：

- **优先级只能整组配置**。同一共享 IRQ 中的所有线路共用一组 NVIC 优先级，不能给 `EXTI14` 和 `EXTI15` 配置不同的 NVIC 抢占等级——在 NVIC 眼里它们就是同一个中断源；
- **一次进中断可能要处理多条线**。共享 IRQ 触发时，你得在处理过程中判断到底是哪几条线挂起了（见第 4.2 节）。

`PB0=EXTI0` 和 `PB1=EXTI1` 则属于两个独立 IRQ，可以配置不同的优先级；本实验只把 PB0 配置为 EXTI，PB1 作为普通输入读取，因此只使能 `EXTI0_IRQn`，PB1 的电平变化不会产生任何中断。

## 4. HAL 入口与共享状态

### 4.1 从向量表到用户回调：完整链路逐层拆解

下面用工程中的真实代码走一遍第 1.3 节执行链的后半段（IRQHandler 及之后）。以 `01_IR_PB14` 的 PB14 为例。

**第 1 层：向量表（`startup_stm32f103xb.s`）**。芯片响应中断时，硬件根据向量表找到该 IRQ 对应的函数地址。启动文件里能看到一整列函数名：

```asm
.word EXTI0_IRQHandler
...
.word EXTI15_10_IRQHandler
```

`EXTI15_10_IRQn` 这个编号是 40——注意向量表开头还有 16 个内核异常入口，它是排在内核异常之后的第 40 个外设中断入口，对应 `EXTI15_10_IRQHandler`——函数名必须和向量表里的名字一字不差，写错了等于链接到一个不存在的地址（落到默认死循环 `Default_Handler`）。

**第 2 层：CubeMX 生成的中断入口（`Core/Src/stm32f1xx_it.c`）**。因为你在 CubeMX 里使能了 `EXTI15_10_IRQn`，生成代码时它会自动写出：

```c
void EXTI15_10_IRQHandler(void)
{
  HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_14);
}
```

**第 3 层：HAL 通用处理函数（`Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_gpio.c`）**。工程固件包里它的源码只有短短几行：

```c
void HAL_GPIO_EXTI_IRQHandler(uint16_t GPIO_Pin)
{
  /* EXTI line interrupt detected */
  if (__HAL_GPIO_EXTI_GET_IT(GPIO_Pin) != 0x00u)
  {
    __HAL_GPIO_EXTI_CLEAR_IT(GPIO_Pin);
    HAL_GPIO_EXTI_Callback(GPIO_Pin);
  }
}
```

`HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_14)` 的参数是 EXTI 线路对应的引脚号；`EXTI_PR` 的第 14 位对应 `EXTI14`。该函数检查 pending 位（`__HAL_GPIO_EXTI_GET_IT`），命中后清除（`__HAL_GPIO_EXTI_CLEAR_IT`），再调用用户版 `HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)`。清除挂起位这一步很重要：不清除，函数返回后 NVIC 看到的还是"有请求"，会立刻再进来一次。

**第 4 层：你的回调（`User/Src/app_exti.c`）**。HAL 库里的默认回调是个空壳（同一个文件里）：

```c
__weak void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
  ...
}
```

`__weak` 的含义：如果整个工程里没有任何地方定义同名函数，链接器就用这个空实现（什么都不发生）；一旦你在 `app_exti.c` 里写了同名函数，链接器就改用你的版本。所以"实现回调"不是去改 HAL 源文件，而是在自己的文件里新建同名函数——`02_Encoder_PB0_PB1` 的入口则相应是 `EXTI0_IRQHandler()` 里调 `HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_0)`，链路完全同构。

### 4.2 一个回调如何服务多条线：共享回调问题

HAL 全工程只认一个回调名字，一个工程只能实现一个用户回调；`EXTI15_10_IRQHandler()` 也只有一个。那么 PB14、PB15 都可能触发时怎么办？两层都要"分发"：

**在 IRQHandler 里逐线检查**。共享 IRQ 中要分别调用：

```c
HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_14);
HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_15);
```

两个调用各自检查、各自清除自己那条线的挂起位。如果只写 PIN_14 这一行，PIN_15 触发时也会进入共享 IRQ，但没人清它的 pending 位——于是另一条线路的挂起位保留，之后共享 IRQ 会多响应一次（表现为"退出后立刻又进一次中断"）。

**在回调里用 `GPIO_Pin` 区分**。回调收到的 `GPIO_Pin` 参数，就是 IRQHandler 传给 `HAL_GPIO_EXTI_IRQHandler()` 的那个值，所以区分逻辑非常直白：

```c
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == GPIO_PIN_14)
    {
        /* PB14 的事件 */
    }
    else if (GPIO_Pin == GPIO_PIN_15)
    {
        /* PB15 的事件 */
    }
}
```

配套工程 `02_Encoder_PB0_PB1` 是"单线使用回调"的实例：回调里只有一个 `if (GPIO_Pin == GPIO_PIN_0)`，因为整个工程只把 PB0 配成了 EXTI。红外和编码器按上面的分发写法完全可以合并进一个工程；本教程仍分成两个，只为让每个实验保持最小——一个工程只验证一条链路，排错时不必先排除另一个实验的干扰。

业务逻辑应写在回调的 `USER CODE` 区域，不要直接改写自动生成的 IRQHandler。本教程的实际做法是把回调实现在独立的 `User/Src/app_exti.c` 里：`User/` 目录整体不受 CubeMX 管理，与写在 `USER CODE` 区域等效，而且比把几十行业务代码塞进 `stm32f1xx_it.c` 的 `USER CODE 1` 区域更清晰。

### 4.3 中断与主循环共享变量：`volatile`

中断和主循环共同访问的变量至少应声明为 `volatile`：

```c
static volatile uint32_t g_event_count = 0U;
```

`volatile` 告诉编译器"这个变量随时可能被你看不见的执行流改掉，每次都老老实实读写内存"。不加会怎样？编译器可能把主循环里的 `g_event_count` 缓存进寄存器，优化出"读一次、永远比较同一个值"的循环，主循环永远看不到中断里加上的数——现象是"调试器里看变量明明在变，主循环就是没反应"。

但 `volatile` 不是万能的：它只保证每次都实际访问内存，不保证"读取后清零"或"读取后再写回"等复合操作具有原子性。Cortex-M3 上对齐的 16 位或 32 位单次读写通常由一条指令完成；本教程的计数器只有一个中断写者、主循环只读取，可直接使用。若主循环还要"读取并清零"，"读"和"清"是两步，中断可能插在两步之间塞进一个新事件，这个事件会被随后的清零覆盖——应在很短的临界区内完成（先 `__disable_irq()` 再开），避免覆盖中断期间刚到达的新事件。本章两个实验刻意把主循环设计成"只读"，就是为了绕开这个坑。

把用户代码放在 CubeMX 的 `USER CODE` 区域；以下示例用 `app_exti.c` 和 `app_exti.h` 组织共享状态与访问函数：计数变量 `static` 在 `.c` 文件内部，外部只能通过 `IR_GetCount()`/`Encoder_GetCount()` 读——这个"只读窗口"保证了主循环不会误写计数。

### 4.4 用户代码如何进入编译

`app_exti.c` 是自己新建的文件，按第 00 章第 5 节的规则，需要在根 `CMakeLists.txt` 里登记进编译清单；`main.c` 里的接入点只有两处，都在 `USER CODE` 区域内：

```c
/* USER CODE BEGIN Includes */
#include "app_exti.h"
/* USER CODE END Includes */
...
/* USER CODE BEGIN PV */
static uint32_t last_count = 0U;    /* 主循环记录上一次读到的计数 */
/* USER CODE END PV */
```

漏登记的典型报错是 ``undefined reference to `IR_GetCount'``；漏 include 则是 `implicit declaration of function 'IR_GetCount'`（C11 下 GCC 的报错原文，常伴随链接失败）。这两类错误都发生在编译期，比运行期的中断问题好查得多。

## 5. 实验一：PB14 红外传感器计次

### 5.1 接线、CubeMX 与数据流

对射式红外模块的接线为：

```text
VCC -> 3.3 V（按模块规格确认）
GND -> MCU GND
DO  -> PB14
```

本例假设"无遮挡为高、遮挡为低"，只在遮挡开始的下降沿计数。这个假设决定了后面所有配置的方向，如果模块相反，触发边沿要跟着反（见 5.4 节）。

CubeMX 配置逐步执行（配套工程 `01_IR_PB14` 已按此配置，对照生成的 `main.c` 中的 `GPIO_MODE_IT_FALLING` 核对）：

1. **引脚模式**：在芯片图上点击 `PB14`，弹出菜单选 `GPIO_EXTI14`；然后在左侧 `GPIO` 配置页把 `GPIO Mode` 设为 `External Interrupt Mode with Falling edge trigger detection`（生成代码里对应 `GPIO_MODE_IT_FALLING`）。选错的后果：选成 `GPIO_Input` 则变成普通输入，永远不触发中断；选成 `External Event Mode...`（EVT 族）则不进 NVIC，回调同样不会执行；
2. **上下拉**：`GPIO Pull-up/Pull-down` 本工程实际选 `No pull-up and no pull-down`（`.ioc` 中 `PB14.GPIO_PuPd=GPIO_NOPULL`）：红外模块的 DO 是推挽输出，空闲时始终主动输出确定电平，不需要内部上下拉帮忙。通用规则是按信号源选择：信号源自己总能驱动出确定电平（推挽输出）就选无上下拉；信号可能"松手"（按键、开漏输出）才必须配上/下拉，否则输入悬空、在 0/1 之间漂移，产生大量假边沿；
3. **使能 NVIC**：打开 `System Core -> NVIC` 页签，勾选 `EXTI line[15:10] interrupts` 的 Enabled（`.ioc` 中体现为 `NVIC.EXTI15_10_IRQn=true:2:0:...`）。不勾选的后果：GPIO、EXTI、向量表、IRQHandler 全都正常，但 NVIC 的开关没打开，请求被挡在门外——这是"代码全对却一次中断都不进"的最常见原因；
4. **优先级**：同一页签里把该 IRQ 的 `Preemption Priority` 填 `2`、`Sub Priority` 填 `0`（对应生成 `HAL_NVIC_SetPriority(EXTI15_10_IRQn, 2U, 0U)`）；
5. **指示灯**：`PC13` 设为 `GPIO_Output`，`GPIO Mode` 为 `Output Open Drain`、初始 `High`（本板 LED 低电平点亮，初始 High 即上电熄灭；工程中为 `GPIO_MODE_OUTPUT_OD`、`GPIO_PIN_SET`）。

配完点 `GENERATE CODE`。输入、处理和输出链为：

```text
物体遮挡 -> PB14 下降沿 -> g_ir_count 加 1
-> 主循环发现计数变化 -> PC13 翻转
```

### 5.2 最小完整代码

`User/Src/app_exti.c`：

```c
#include "app_exti.h"
#include "main.h"

static volatile uint32_t g_ir_count = 0U;
static uint32_t g_last_tick = 0U;

uint32_t IR_GetCount(void)
{
    return g_ir_count;
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == GPIO_PIN_14)
    {
        uint32_t now = HAL_GetTick();

        /* 低速计次演示：过滤间隔小于 20 ms 的重复边沿。 */
        if ((uint32_t)(now - g_last_tick) >= 20U)
        {
            g_ir_count++;
            g_last_tick = now;
        }
    }
}
```

`User/Inc/app_exti.h`：

```c
#ifndef __APP_EXTI_H
#define __APP_EXTI_H

#include <stdint.h>

uint32_t IR_GetCount(void);

#endif
```

在 `main.c` 中包含 `app_exti.h`，并加入：

```c
static uint32_t last_count = 0U;

while (1)
{
    uint32_t count = IR_GetCount();
    if (count != last_count)
    {
        last_count = count;
        HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
    }
}
```

三个文件各司其职：`app_exti.c` 持有中断里的计数和门限状态；`app_exti.h` 只暴露一个只读函数；`main.c` 只负责"发现计数变了就翻灯"，对中断细节一无所知。

### 5.3 回调逐行拆解

回调虽然只有几行，每一行都有讲究：

- `g_ir_count` 声明为 `volatile`：中断写、主循环读，见第 4.3 节；`g_last_tick` 只有回调自己访问，单执行流，不需要 `volatile`；
- `HAL_GetTick()` 返回系统毫秒时基（SysTick 每 1 ms 通过 `HAL_IncTick()` 递增一次），给"两次边沿隔了多久"提供时间标尺；
- `(uint32_t)(now - g_last_tick) >= 20U`：无符号减法天然容忍回绕——即使 `now` 从最大值绕回 0，差值依然正确。第一次中断时 `g_last_tick` 是 0，系统启动后约 `20 ms` 内的第一次事件也可能被忽略，这就是门限的代价；
- 先判断门限再 `g_ir_count++`：小于 `20 ms` 的重复边沿既不计数也不刷新 `g_last_tick`，门限窗口相对"上一次**有效**事件"计算。

`20 ms` 门限只是低速演示：它会合并间隔小于 `20 ms` 的边沿，但不能保证过滤所有机械或电气抖动（间隔超过 `20 ms` 的抖动照样计进去）。`uint32_t` 的无符号差值写法可以在 HAL Tick 回绕时保持正确。高速或必须逐个捕获事件时，应改用硬件滤波、输入捕获或外部计数功能。

### 5.4 预期现象与"如果看到 X，说明 Y"

生成代码、编译并下载后，低速遮挡一次时，下降沿使 `g_ir_count` 增加 `1`，主循环随后翻转一次 PC13；在调试器中也会看到计数逐步增加。若模块实测为"无遮挡低、遮挡高"，应改用上升沿（CubeMX 里改 `GPIO Mode` 为 Rising 重新生成），不能只修改软件计数逻辑。对照现象定位问题：

| 如果看到 | 说明 | 下一步 |
| --- | --- | --- |
| 遮挡一次，计一次，灯随计数翻转 | 一切正常 | 记录实验数据 |
| 完全不计数 | 中断根本没进来 | 按第 8 节从接线、模式、NVIC 勾选逐层查 |
| 遮挡时不计，移开遮挡时反而计 | 模块电平与"无遮挡为高"的假设相反 | 把触发边沿改成 Rising |
| 一次遮挡计 2~3 | 有效边沿间隔超过了 `20 ms`（门限只合并间隔小于 20 ms 的） | 用示波器/调试器看一次物理事件产生几个边沿，加大门限或处理硬件 |
| 调试器断点停留后再继续，计数少了 | 挂起位只记录"至少发生一次"，断点期间来了多次也只算一次 | 属于正常行为，连续事件统计不要用断点验证 |
| 主循环里读到的计数不更新 | `volatile` 漏写或主循环缓存了值 | 检查 `g_ir_count` 声明 |

最后对照 1.2 节的两个漏洞：一次遮挡对应**一个下降沿**，EXTI 只在边沿瞬间置位一次挂起位，"一次事件"和"保持状态"天然被区分开；短脉冲期间主循环哪怕正在 `HAL_Delay(500)`，EXTI 照样置位、NVIC 照样调度，事件不丢。代价是需要理解第 2~4 节这一整条链路——这也是本章把链路讲这么细的原因：中断方案的所有故障都藏在这些环节里。

## 6. 实验二：PB0/PB1 编码器判向

### 6.1 A/B 两相状态与方向

增量式编码器的 A、B 两路频率相同，相位相差约 `90°`。转轴匀速转动时，A、B 都是方波，只是谁先跳变不同：正转时 A 先跳，反转时 B 先跳。以 A 领先 B 为正转，一个周期可写成：

| 状态 | A | B | 正转下一状态 | 反转下一状态 |
| --- | ---: | ---: | --- | --- |
| S0 | 0 | 0 | S1 | S3 |
| S1 | 1 | 0 | S2 | S0 |
| S2 | 1 | 1 | S3 | S1 |
| S3 | 0 | 1 | S0 | S2 |

沿状态表看"S0 -> S1"（A 先升起）是正转，"S1 -> S0"（A 先落下）方向就反了——判向的原理就是**在 A 的边沿瞬间看 B 的电平**。本例采用简单 x1 解码：只在 A 相下降沿采样。下降沿后 `B=1` 表示 A 领先，计 `+1`；`B=0` 表示 B 领先，计 `-1`。x1 的意思是每个编码器周期只计一次（四状态里只采样 A 相的下降沿这一个边沿：正转对应 S2->S3，反转对应 S1->S0），牺牲分辨率换实现简单。方向符号取决于 A/B 接线和编码器型号，若整体反向，可交换 A/B 或同时反转 `+1/-1`，最终以实测校准为准。

### 6.2 接线与 CubeMX 配置

按模块规格连接 `VCC`、`GND`、`A` 和 `B`，其中 `A -> PB0`、`B -> PB1`，并与 MCU 共地。以 `PB0=A`、`PB1=B` 为例（配套工程 `02_Encoder_PB0_PB1` 已按此配置）：

1. **PB0**：点击选 `GPIO_EXTI0`，`GPIO Mode` 为 `External Interrupt Mode with Falling edge trigger detection`（`GPIO_MODE_IT_FALLING`），`GPIO Pull-up/Pull-down` 本工程实际选 `Pull-up`（`.ioc` 中 `PB0.GPIO_PuPd=GPIO_PULLUP`）；
2. **PB1**：选 `GPIO_Input`，同样选 `Pull-up`（`PB1.GPIO_PuPd=GPIO_PULLUP`）——B 相是随时要读的电平，悬空会读到噪声；
3. **NVIC**：`System Core -> NVIC` 页签勾选 `EXTI line0 interrupt`，抢占 `2`、响应 `0`（`.ioc` 中 `NVIC.EXTI0_IRQn=true:2:0:...`）。注意不要顺手把 `EXTI line1` 也勾上——本方案 PB1 不需要中断；
4. **PC13**：与实验一相同，配置为输出、初始 High。

只给 PB0 配 EXTI 而不是两条线都配，是因为 `PB0=EXTI0`、`PB1=EXTI1` 属于两个独立 IRQ（第 3.3 节）：本方案只在 A 相下降沿采样，PB1 只要能被读到就行，多开一路中断只会增加无意义的执行次数。

生成的中断入口（`Core/Src/stm32f1xx_it.c`）为：

```c
void EXTI0_IRQHandler(void)
{
  HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_0);
}
```

与实验一的 `EXTI15_10_IRQHandler()` 对照可以看出：除了向量表入口不同，中间两层完全一样。

### 6.3 最小完整代码

`User/Src/app_exti.c`：

```c
#include "app_exti.h"
#include "main.h"

static volatile int16_t g_encoder_count = 0;

int16_t Encoder_GetCount(void)
{
    return g_encoder_count;
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == GPIO_PIN_0)
    {
        GPIO_PinState b = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_1);

        /* 饱和计数，避免长时间运行后有符号溢出。 */
        if (b == GPIO_PIN_SET)
        {
            if (g_encoder_count < INT16_MAX) g_encoder_count++;
        }
        else
        {
            if (g_encoder_count > INT16_MIN) g_encoder_count--;
        }
    }
}
```

在 `app_exti.h` 中声明 `int16_t Encoder_GetCount(void);`（头文件的整体写法与 5.2 节的 `app_exti.h` 相同，替换声明即可）。

在 `main.c` 中包含头文件，并加入：

```c
static int16_t last_count = 0;

while (1)
{
    int16_t count = Encoder_GetCount();
    if (count != last_count)
    {
        last_count = count;
        HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
    }
}
```

三处值得注意的写法：

- `g_encoder_count` 用 `int16_t`（有符号）：计数要能表示正转和反转两个方向；到 `INT16_MAX`/`INT16_MIN` 就停住的饱和写法避免长时间单向转动后有符号溢出变成大负数/大正数；
- `if (GPIO_Pin == GPIO_PIN_0)` 就是共享回调的"区分引脚"写法在单线工程中的样子（第 4.2 节）——将来往同一工程加第二条 EXTI 线时，扩展的是这里的 `else if` 和 IRQHandler 里的第二行 `HAL_GPIO_EXTI_IRQHandler()`；
- 读 B 相用的是 `HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_1)`：PB1 没配 EXTI，但普通输入照样随时可读。

数据链为：

```text
编码器 A/B 电平 -> PB0 下降沿 -> 读取 PB1
-> 有符号计数加/减 -> PC13 翻转和调试器读数
```

### 6.4 预期现象与"如果看到 X，说明 Y"

生成代码、编译并下载后，正转时 `g_encoder_count` 应逐步增大，反转时逐步减小，每次计数变化都会翻转 PC13。在调试器 Expressions 窗口里添加 `g_encoder_count`（或通过 `Encoder_GetCount()` 间接观察），边转边看正负变化最直观。对照现象定位问题：

| 如果看到 | 说明 | 下一步 |
| --- | --- | --- |
| 正转递增、反转递减 | 一切正常 | 记录方向与计数的对应关系 |
| 方向与预期相反 | A/B 接线顺序或编码器相位定义与假设不符 | 交换 A/B 接线，或同时反转 `+1/-1` 符号 |
| 静止时计数漂移 | 输入悬空、上下拉不合适、接线接触或电磁干扰 | 检查 PB0/PB1 上拉、接线；GPIO EXTI 没有数字滤波，先解决电气问题 |
| 转一格计 2~3 | 机械触点在真实边沿附近抖动 | 属于机械抖动，见 6.5 节的对策 |
| 快速旋转时明显丢计数 | 超出了 GPIO 中断 + x1 解码的能力范围 | 换定时器编码器模式（第 5 章） |

若静止时计数仍变化，优先检查输入上下拉、接线和机械抖动；若方向相反，则校准 A/B 接线或计数符号。机械触点可能在一次真实边沿附近产生多个跳变，因此静止计数抖动不能靠"中断正常"解释。

### 6.5 适用边界与升级路线

该代码是最简单的低速 x1 解码，普通 GPIO EXTI 没有可直接设置数字滤波参数（硬件滤波需要在边沿检测之外另加电路或外设能力）。低速输入可增加时间门限（参照实验一 `20 ms` 的写法，但要注意门限同时限制最高计数速度）；需要更可靠的 x2/x4 解码时应使用四状态 Gray code 状态机（把 6.1 节的状态表完整实现，每个状态转换计一次）；连续高速计数则应使用定时器的编码器模式（定时器硬件直接解码 A/B 相，不占用 CPU 中断），对应 [[05 定时器：时基、PWM、输入捕获与电机控制]] 的编码器实验。

## 7. 本章验收

- [ ] 红外实验的 EXTI 触发沿和计数现象已记录；
- [ ] 编码器实验的正负方向已确认；
- [ ] 共享 IRQ 的 pending 清除路径已检查；
- [ ] 用户回调放在 `User/` 或 `USER CODE` 区域；
- [ ] 能从触发沿、NVIC、IRQHandler、回调逐层排错；
- [ ] 能复述本章工程的优先级分组和 EXTI/SysTick 优先级数值（对照 3.2 节）。

## 8. 根据现象排查中断故障

排查的总原则：沿着 1.3 节的执行链从前往后确认，链路哪一层断了，问题就在哪一层。把每一层变成可观察的证据：

| 现象 | 优先检查 | 具体检查步骤与判断依据 |
| --- | --- | --- |
| 回调完全不进入 | 接线与共地、GPIO 是否为 EXTI、触发边沿、NVIC 是否启用 | ① 万用表/逻辑分析仪确认引脚电平确实变化；② `.ioc` 与生成代码里模式是 `GPIO_MODE_IT_FALLING` 这类 IT 族而不是 EVT 族或普通 Input；③ 触发边沿方向与实际电平变化方向一致；④ NVIC 页签确认勾选（`EXTI15_10_IRQn=true:2:0`），生成的 `stm32f1xx_it.c` 里有对应 IRQHandler；⑤ 调试器运行时读 `EXTI_PR` 看挂起位是否置位——置位而回调不进，问题在 NVIC 层之后 |
| 回调进入但计数重复 | 传感器阈值抖动、机械触点抖动、电磁干扰 | 用示波器观察一次物理事件产生了几个有效边沿；确认 `20 ms` 门限已生效（门限只合并间隔小于 20 ms 的边沿）；仍重复则边沿间隔大于门限，属真实多次触发 |
| PB14 正常，加入 PB15 后异常 | `EXTI15_10_IRQHandler()` 是否处理所有可能的 pin | 检查共享 IRQ 里是否对每条可能触发的线各调用了一次 `HAL_GPIO_EXTI_IRQHandler()`；漏掉的 pending 位会保留并影响后续响应（表现为退出后立刻重进中断） |
| 编码器静止时计数漂移 | PB0/PB1 是否悬空、上下拉是否合适、接线和干扰 | 核对 `.ioc` 中两引脚的 `GPIO_PuPd`（本工程为 `GPIO_PULLUP`）；检查共地；GPIO EXTI 没有数字滤波参数，先处理电气问题再谈软件 |
| 编码器方向与预期相反 | A/B 接线、型号的相位定义、`+1/-1` 规则 | 交换 A/B 或反转符号后重新验证同一转向；把结论记进实验记录，作为该编码器的固定校准 |
| 优先级与设计不符 | 优先级分组、编号方向、共享 IRQ | 确认分组是 `NVIC_PRIORITYGROUP_4`（子优先级无作用）；记住编号越小越高；`EXTI10~15` 只能共享同一组 NVIC 优先级，`EXTI14` 和 `EXTI15` 无法配置成不同抢占等级 |
| 中断执行时间很长或其他事件丢失 | 回调中的 OLED、串口、延时或长循环 | 回调只更新短小状态，耗时处理放到主循环；怀疑时先临时清空回调验证现象是否恢复 |
| 主循环中的复合更新偶尔丢数 | `volatile` 使用和多执行流竞争 | 确认共享变量带 `volatile`；"读取并清零"这类复合操作要放进很短的临界区——`volatile` 不保证复合操作原子，必要时缩短并保护临界区 |

上一篇：[[03 时钟系统：时钟树、PLL 与 HAL 配置]] ｜ 下一篇：[[05 定时器：时基、PWM、输入捕获与电机控制]]
