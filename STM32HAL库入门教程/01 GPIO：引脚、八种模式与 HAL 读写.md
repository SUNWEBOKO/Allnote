# 01 GPIO：引脚、八种模式与 HAL 读写
下一篇：[[02 OLED 调试：I2C 显示数据流]]

## 本章闭环

本章以 STM32F103C8T6 和 CubeMX/HAL 为对象，完成一条可跟做的 GPIO 学习链：

```text
认识引脚 -> 理解 GPIO 电气结构 -> 选择输入/输出模式
-> 配置速度与复用 -> 编写 HAL 程序 -> 下载、观察、排错
```

示例默认使用常见最小系统板：板载 LED 接 `PC13`，按键或外接 LED 可接 `PA9`；具体板卡仍应以原理图为准。

## 1. 学习目标与准备

完成本章后，应能够：

- 读懂 `PA9`、`PC13` 等 STM32 引脚名称；
- 区分 GPIO 的 8 种工作模式；
- 根据外部电路选择推挽、开漏、上拉、下拉或浮空输入；
- 在 CubeMX 中配置引脚、调试接口和输出速度；
- 使用 `HAL_GPIO_WritePin()`、`HAL_GPIO_ReadPin()`、`HAL_Delay()` 编写 LED 与按钮实验；
- 理解 IO 复用与重映射，并能处理下载接口被锁死的问题。

准备：STM32F103C8T6 开发板、ST-LINK、USB 线、CubeMX、Keil MDK、LED、约 `1 kΩ` 限流电阻、轻触按键、杜邦线和 USB 转 TTL 模块。

## 2. STM32F103 的引脚分布

### 2.1 特殊引脚与普通 IO

在 CubeMX 的芯片引脚图中，彩色引脚通常代表电源、复位、晶振、启动配置或其他专用功能；蓝灰色引脚通常是可编程 GPIO。常见特殊引脚包括：

| 引脚 | 作用 |
| --- | --- |
| `VDD` | 电源正端 |
| `VSS` | 地 |
| `VBAT` | 备用电池，为后备域供电 |
| `NRST` | 芯片复位输入 |
| `BOOT0` | 启动模式选择 |
| `PC14/PC15` | 常用于低速外部晶振 `LSE` |
| `PD0/PD1` | 常用于高速外部晶振 `HSE` |
| `PA13 (SWDIO)` | SWD 调试口数据线，初学阶段不要占用 |
| `PA14 (SWCLK)` | SWD 调试口时钟线，初学阶段不要占用 |

资料中用 `VDD/VSS` 描述正电源和地；工程接线时也常见 `VCC/GND` 说法。不要把 `VBAT`、`NRST` 或晶振引脚当作普通 GPIO 随意使用。`PA13`、`PA14` 同理：**把 LED、按键等普通功能配到这两个脚，会导致下载和调试连接失败**；本章工程中让它们保持 SWD 调试功能即可。

### 2.2 GPIO 分组与编号

STM32F103 常见 GPIO 组为 `GPIOA`、`GPIOB`、`GPIOC`、`GPIOD`。每组最多 16 个引脚，编号从 `0` 到 `15`：

```text
GPIOA: PA0 ... PA15
GPIOB: PB0 ... PB15
GPIOC: PC13、PC14、PC15
GPIOD: PD0、PD1
```

代码中，组和编号分开表示。例如 `PA9` 对应 `GPIOA` 与 `GPIO_PIN_9`；`PC13` 对应 `GPIOC` 与 `GPIO_PIN_13`。

## 3. GPIO 的八种工作模式

GPIO 的信号方向有两类：从芯片内部到引脚是输出，从引脚到芯片内部是输入。STM32F1 的 8 种模式可按“通用/复用”和“推挽/开漏”理解：

| 方向  | 通用功能           | 复用功能          |
| --- | -------------- | ------------- |
| 输出  | 通用输出推挽、通用输出开漏  | 复用输出推挽、复用输出开漏 |
| 输入  | 输入浮空、输入上拉、输入下拉 | 模拟输入（ADC功能）   |

### 3.1 推挽输出

推挽输出可看作上下两个 MOS 管交替导通：

- 写 `0`：下方 N-MOS 导通，引脚连接 `VSS`，输出低电平；
- 写 `1`：上方 P-MOS 导通，引脚连接 `VDD`，输出高电平。

因此推挽可以主动输出高、低两种电平，适合驱动普通 LED、数字控制线等，但两个输出端不能同时强行驱动相反电平。

### 3.2 开漏输出

开漏输出保持上方 P-MOS 关闭：

- 写 `0`：N-MOS 导通，输出低电平；
- 写 `1`：N-MOS 关闭，引脚呈高阻抗，近似断开。

开漏本身不能主动输出高电平，通常需要外部上拉电阻。它适合多设备共享总线、线与逻辑和某些低电平有效电路。

### 3.3 通用输出与复用输出

通用输出由用户代码直接控制。例如调用 `HAL_GPIO_WritePin()` 改变 `PA9` 电平。

复用输出则把引脚控制权交给片上外设。例如 `PA9` 可作为 `USART1_TX`，串口模块写入数据后自动产生发送波形；此时应用代码不能再把 `PA9` 当作普通 GPIO 随意翻转。

### 3.4 输入上拉、下拉与浮空

输入模式相当于用高内阻电压表观察外部电平。如果既没有外部驱动，也没有内部上下拉，引脚会悬空，容易受到干扰而随机读到 `0` 或 `1`。

- **输入上拉**：内部电阻接到 `VDD`，无外部信号时默认读 `1`；
- **输入下拉**：内部电阻接到 `VSS`，无外部信号时默认读 `0`；
- **输入浮空**：上下拉均关闭，必须由外部电路提供稳定电平；
- **模拟输入**：关闭数字输入路径，用于 ADC 等模拟信号，不能按普通数字输入理解。

选择原则是：外部信号有明确驱动时可用浮空；按钮、开关等可能断开的信号应使用上拉或下拉，让“松开”状态仍有确定电平。

## 4. IO 复用与重映射

同一引脚可承担多个功能。例如 `PA9` 既可作为普通 GPIO，也可作为 `USART1_TX` 或定时器通道引脚。启用 USART1 后，PA9 由 USART1 托管。

当两个外设的默认引脚发生冲突时，可使用复用重映射把其中一个外设移动到备用引脚。例如 USART1 的发送、接收功能可重映射到 `PB6/PB7`（具体映射以芯片数据手册和 CubeMX 版本为准）。

配置步骤：

1. 在 CubeMX 中启用目标外设；
2. 查看引脚冲突提示和可用备用映射；
3. 在 `GPIO`/`AFIO` 相关配置中启用重映射；
4. 重新检查 GPIO 模式、速度、上下拉和外部接线；
5. 生成代码，确认外设初始化和 AFIO 重映射代码均存在。

## 5. 最大输出速度

GPIO 电平切换并非瞬间完成。输出从低到高需要上升时间，从高到低需要下降时间；边沿过慢时，信号无法在目标周期内稳定保持有效电平。

STM32F1 常见输出速度档位如下：

| 档位 | 典型上升/下降时间 | 最大输出速度 |
| --- | ---: | ---: |
| 低速 | `125 ns` | `2 MHz` |
| 中速 | `25 ns` | `10 MHz` |
| 高速 | `5 ns` | `50 MHz` |

最大输出速度不是“程序必须以该频率翻转”，而是普通 GPIO/复用输出的边沿能力档位。应选满足信号要求的最小档位：LED 和低速控制线通常选低速；较快的 SPI、定时器输出再按实际边沿和信号完整性选择中速或高速。USB D+/D− 使用专用 USB 复用功能和收发器，不能简单按普通 GPIO 输出速度来理解。

## 6. HAL 与 CubeMX 的 GPIO 编程接口

### 6.1 初始化顺序

典型 HAL 工程的初始化链为：

```text
HAL_Init()
-> SystemClock_Config()
-> MX_GPIO_Init()
-> 其他外设初始化
-> while (1)
```

CubeMX 生成的 GPIO 配置应放在 `MX_GPIO_Init()` 中，用户逻辑放在 `USER CODE BEGIN/END` 区域，以免重新生成工程时被覆盖。

### 6.2 写引脚：`HAL_GPIO_WritePin()`

函数形式：

```c
HAL_GPIO_WritePin(GPIOx, GPIO_Pin, PinState);
```

- `GPIOx`：GPIO 组，如 `GPIOA`、`GPIOC`；
- `GPIO_Pin`：引脚编号，如 `GPIO_PIN_9`；
- `PinState`：`GPIO_PIN_RESET` 写 `0`，`GPIO_PIN_SET` 写 `1`。

示例：

```c
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_SET);
HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
/* 亮灭关系取决于 LED 是高电平有效还是低电平有效。 */
```

注意“写入值”和“物理现象”不是一回事：**LED 是低电平点亮还是高电平点亮，由 LED 的接法决定**——阳极接电源、阴极接引脚时写 `0` 点亮；阴极接电源、阳极接引脚时写 `1` 点亮。**推挽/开漏描述的是输出级结构，与有效电平是两件正交的事**：低电平点亮的 LED 用推挽输出写 `0` 同样能点亮。板载 `PC13` LED 的具体输出模式以开发板原理图为准，不能只凭“板载”二字断定它必须是开漏。

### 6.3 读引脚：`HAL_GPIO_ReadPin()`

函数形式：

```c
GPIO_PinState state = HAL_GPIO_ReadPin(GPIOx, GPIO_Pin);
```

返回 `GPIO_PIN_SET` 表示读到逻辑 `1`，返回 `GPIO_PIN_RESET` 表示读到逻辑 `0`。按钮程序应根据接线先建立“按下/松开”和“电平 0/1”的对应关系，再写条件判断。

### 6.4 延时：`HAL_Delay()`

```c
HAL_Delay(500U);   // 延时 500 ms
```

`HAL_Delay()` 依赖 HAL Tick，适合入门实验和低实时性任务；精确周期、非阻塞任务或高速波形应使用定时器、中断或 DMA。

### 6.5 从标准库到 HAL 的对应关系

已学过标准库的读者可以按下表迁移，但要注意底层寄存器的差别：

| 标准库 | HAL | 说明 |
| --- | --- | --- |
| `GPIO_SetBits(GPIOx, GPIO_Pin)` | `HAL_GPIO_WritePin(GPIOx, GPIO_Pin, GPIO_PIN_SET)` | 底层写 `BSRR`，单次原子写 |
| `GPIO_ResetBits(GPIOx, GPIO_Pin)` | `HAL_GPIO_WritePin(GPIOx, GPIO_Pin, GPIO_PIN_RESET)` | 底层写 `BRR`（或 `BSRR` 高 16 位），同样是原子写 |
| `GPIO_ReadInputDataBit(GPIOx, GPIO_Pin)` | `HAL_GPIO_ReadPin(GPIOx, GPIO_Pin)` | 读 `IDR`，返回 `GPIO_PIN_SET` / `GPIO_PIN_RESET` |
| 自行用 `ODR` 取反 | `HAL_GPIO_TogglePin(GPIOx, GPIO_Pin)` | HAL 专门提供的翻转接口 |

两点容易形成错误认知的地方：

- `HAL_GPIO_WritePin()` 走的是 `BSRR`/`BRR` 的**单次原子写，不是读改写 `ODR`**，因此不会因为“读-改-写”被中断打断而误改同一组的其他引脚；
- 读电平统一用 `HAL_GPIO_ReadPin()`，它读的是 `IDR`。**在复用输出或开漏输出下，`IDR` 才是引脚上的真实电平，而 `ODR` 只是最后一次写入的锁存值**，不能拿 `ODR` 当引脚实际电平使用。

用 `HAL_GPIO_TogglePin()` 可以把闪烁写得更简洁——它不关心当前电平，只把它翻到相反状态：

```c
/* 这段代码写在 main() 里已有的 while (1) 内部。 */
while (1)
{
    /* 每个周期翻转一次，亮灭节奏由 HAL_Delay 决定。 */
    HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
    HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_9);
    HAL_Delay(500U);
}
```

`HAL_GPIO_TogglePin()` 适合“只要求翻转、不关心当前是亮还是灭”的场合；如果代码里需要按条件指定亮灭（例如按键控制 LED），仍然用 `HAL_GPIO_WritePin()`。

## 7. 实验一：板载 LED 与外接 LED 闪烁

### 7.1 接线与逻辑

常见最小系统板的板载 LED 接在 `PC13`：LED 阳极接 `VDD`、阴极接 `PC13`，所以是低电平点亮。这里“低电平点亮”说的是 **LED 的接法**，与输出级用推挽还是开漏无关——两种输出级写 `0` 都能把引脚拉低、点亮 LED。具体选用哪种输出模式和初始电平，以开发板原理图和实测为准。

外接 LED 使用推挽接法：`PA9 -> 限流电阻（约 1 kΩ） -> LED 阳极`，LED 阴极接 `VSS/GND`。LED 长脚通常为阳极，短脚为阴极；接反会导致不亮，过流则可能损坏器件。

### 7.2 CubeMX 配置

1. 新建 `STM32F103C8T6` 工程；
2. `System Core -> SYS -> Debug` 选择 `Serial Wire`；
3. 将 `PC13`、`PA9` 设置为 `GPIO_Output`；
4. `PC13` 选择 `Output Open Drain`，初始电平 `High`；
5. `PA9` 选择 `Output Push Pull`，初始电平 `Low`；
6. 两个引脚输出速度均选低速；
7. `Project Manager -> Project`：填写工程名（例如 `GPIO_LED`）和保存路径（避免中文路径）；`Toolchain/IDE` **必须主动改成 `MDK-ARM`**——CubeMX 的默认值是 `EWARM`（IAR），保持默认不会生成 `.uvprojx`，读者会找不到能用 Keil 打开的工程。若改用 STM32CubeIDE，则这里选 `STM32CubeIDE`；本文以 Keil MDK 为例；
8. `Project Manager -> Code Generator`：勾选 “Generate peripheral initialization as a pair of .c/.h files”，把各外设初始化拆成独立文件——本文后面提到的 `gpio.c`/`gpio.h` 就是这个选项生成的；其余选项保持默认；
9. 确认引脚和时钟配置无误后，点击 `GENERATE CODE` 生成工程；
10. 生成结束后，到工程目录下的 `MDK-ARM` 子目录中找到 `<工程名>.uvprojx`，用 Keil MDK 打开它（不要错开 `.ioc` 文件或工程根目录）。

### 7.3 主循环代码（填入 `main.c` 的 `USER CODE BEGIN WHILE` 区域）

CubeMX 已经生成了完整的 `main()` 骨架，其中包括 `HAL_Init()`、`SystemClock_Config()`、`MX_GPIO_Init()` 和 `while (1)` 循环框架。下面这段只是**循环体**，请填到 `main.c` 中 `USER CODE BEGIN WHILE` / `USER CODE END WHILE`（或 `USER CODE BEGIN 3` / `USER CODE END 3`）标记之间，**不要整份替换 `main.c`**——整份替换会丢掉外设初始化，下次重新生成工程时用户代码也会被覆盖。

```c
/* 这段代码写在 main() 中已有的 while (1) 内部，不是整份 main.c。 */
while (1)
{
    /* 板载 LED：低电平点亮，写 0 点亮（有效电平由接法决定）。 */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
    /* 外接 LED：阳极经限流电阻接 PA9，写 1 点亮。 */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_SET);
    HAL_Delay(500U);

    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_RESET);
    HAL_Delay(500U);
}
```

这段代码不需要自己声明变量：`GPIOC`、`GPIO_PIN_13`、`GPIOA`、`GPIO_PIN_9` 和 `HAL_Delay()` 都来自 CubeMX 已在 `main.c` 中包含的 `main.h`（其中包含 `stm32f1xx_hal.h`）。

### 7.4 观察与调试

编译无错误后下载并复位，两个 LED 应同步闪烁。可在 Keil 中关闭优化（优化等级 `0`）并使用 ST-LINK 单步执行，观察每次写引脚后 LED 的变化。若 LED 亮灭相反，优先检查 LED 极性（长短脚是否接反）和该接法对应的有效电平：阳极接电源、阴极接引脚就是低电平点亮，阴极接电源、阳极接引脚就是高电平点亮。有效电平由接法决定，与推挽/开漏无关。

## 8. 实验二：按钮控制 LED

### 8.1 按键电路

按钮一端接 `PA9`，另一端接地；`PA9` 配置为输入上拉。按钮松开时，触点断开，内部上拉使 `PA9` 为高电平；按钮按下时，`PA9` 被接地，读到低电平：

```text
松开 -> PA9 = 1
按下 -> PA9 = 0
```

> **动手前先确认两件事：**
>
> 1. **先拆除实验一接在 `PA9` 上的外接 LED 与限流电阻。** 实验二把 `PA9` 改成输入上拉，如果 LED 支路还挂在引脚上，它会在引脚与 `VDD`/`VSS` 之间形成通路，按下和松开时的读数都不再干净（例如松开时读不到稳定的高电平）；
> 2. `PA9` 是 `USART1_TX` 的默认引脚（`PA10` 是 `USART1_RX`），第 08 章的串口实验会占用它。做串口实验时不要把按键或 LED 接在 `PA9`/`PA10` 上，本实验做完后建议把这两个脚空出来。

本实验暂不处理机械抖动，因此快速按下或松开时可能出现瞬态跳变。

### 8.2 CubeMX 配置

- `PC13`：作为输出驱动板载 LED，初始电平设为熄灭状态；低电平点亮还是高电平点亮由 LED 接法决定，输出级选推挽或开漏都能驱动，具体以开发板原理图为准；
- `PA9`：输入模式，`GPIO Pull-up/Pull-down = Pull-up`；
- `PC13`、`PA9` 的具体电气模式应与开发板原理图一致。

### 8.3 主循环代码（填入 `main.c` 的 `USER CODE BEGIN WHILE` 区域）

和实验一一样，`main()` 骨架、`HAL_Init()`、`SystemClock_Config()`、`MX_GPIO_Init()` 和 `while (1)` 都由 CubeMX 生成，下面这段只填到 `USER CODE BEGIN WHILE` / `USER CODE END WHILE` 标记之间，**不要整份替换 `main.c`**。按键状态变量 `key` 声明在循环体内部，作用域只在本轮循环，不需要在文件开头另外声明；读取它用到的 `GPIO_PinState` 类型来自 `stm32f1xx_hal.h`，`main.c` 已经包含。

```c
/* 这段代码写在 main() 中已有的 while (1) 内部，不是整份 main.c。 */
while (1)
{
    GPIO_PinState key = HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_9);

    if (key == GPIO_PIN_SET)
    {
        /* 松开：熄灭低电平有效的板载 LED。 */
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
    }
    else
    {
        /* 按下：点亮 LED。 */
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
    }
}
```

### 8.4 方法提示

按钮程序最容易写错的地方是把“按下”直接等同于逻辑 `1`。正确做法是先看原理图：按钮按下后究竟把引脚接到 `VDD` 还是 `VSS`，再决定条件分支。若要用于正式产品，还需加入消抖、长按、连发或状态机处理。

## 9. 常见故障排查

### 9.1 LED 不亮或亮灭相反

检查 LED 长短脚、限流电阻、共地、引脚编号和有效电平。**有效电平由 LED 接法决定**：阳极接电源、阴极接引脚时低电平点亮，阴极接电源、阳极接引脚时高电平点亮；**推挽和开漏是输出级结构，与有效电平无关**，低电平点亮的 LED 用推挽写 `0` 同样能点亮。板载 LED 的接法与输出模式以开发板原理图为准，不能套用同一写值。

### 9.2 按钮读数随机

确认输入没有浮空：使用内部上拉/下拉或外部电阻；检查按钮是否接错触点；确认读取的 GPIO 组和引脚号准确；确认**引脚上是否还接着 LED 支路**（实验一的外接 LED 与限流电阻没拆，会把输入电平拉偏，读数随 LED 的亮灭变化）。需要可靠按键事件时，再加入硬件或软件消抖。

### 9.3 复用外设没有波形

确认外设已启用、引脚没有被其他模块占用、复用映射正确、GPIO 速度和上下拉符合接口要求，并检查 CubeMX 生成的 AFIO/重映射配置。

### 9.4 下载失败、调试接口被锁死

STM32F103 复位后 SWJ 调试口默认是使能的（SW-DP 可用），所以**单纯没有在 `System Core -> SYS -> Debug` 里勾选 `Serial Wire`，并不等于芯片被锁死**，CubeMX 不勾选只是不为调试口生成额外配置。真正高发的原因有四类：

1. **调试引脚被程序占用**：用户代码把 `PA13 (SWDIO)`、`PA14 (SWCLK)` 配成了普通 GPIO 或其他复用功能，接管了调试引脚；
2. **在 `Debug` 下拉里显式选了 `Disable`**：这一项和"不勾选"不同，CubeMX 会生成关闭 SWJ 的代码（F1 上是 `HAL_AFIO_REMAP_SWJ_DISABLE()` 一类调用），复位后调试口就是关的，属于自己把调试口关掉。除非确实需要把 `PA13~PA15`、`PB3`、`PB4` 全部当普通 IO 用，否则不要选它；
3. **时钟或低功耗配置错误**：程序跑飞，或进入停止/待机模式后 SW-DP 无法正常响应；
4. **ST-LINK 接线与供电**：`SWDIO`、`SWCLK`、`GND`、`3.3 V` 四根线是否接对、接触是否良好，注意不要用 `5 V` 供电。

首选恢复手段是用 **Connect under reset（复位时连接）**：在 STM32CubeProgrammer 的 `Mode` 中选择 `Under reset` 再 `Connect`，或者在 Keil 的 ST-LINK 调试设置（`Options for Target -> Debug -> Settings`）里把连接方式设为 `under Reset`，必要时按住开发板复位键再点连接。这样通常就能重新连上，**绝大多数情况下不必擦片**。

只有 `Connect under reset` 也连不上时，才走第 10 节的 UART Bootloader 全片擦除，并在擦除后重新烧录一个没有占用 `PA13`/`PA14` 的工程。

## 10. 使用 Bootloader 清除程序恢复烧录

> 这是恢复操作，会擦除芯片中的程序；确认不需要保留原程序后再执行。

### 10.1 硬件连接

1. 拔下 ST-LINK；
2. 按开发板说明设置启动跳帽，使芯片进入系统 Bootloader；
3. USB 转 TTL 与单片机共地，并使用 `3.3 V` 电平兼容的模块；
4. 常见连接为：单片机 `PA9 (USART1_TX)` 接 USB-TTL 的 `RXD`，单片机 `PA10 (USART1_RX)` 接 USB-TTL 的 `TXD`，`GND` 对 `GND`。供电电压按开发板和模块规格确认，不能机械照搬不明的 `5 V` 接法。

### 10.2 CubeProgrammer 操作

1. 安装并启动 STM32CubeProgrammer；
2. 连接方式选择 `UART`；
3. 通过拔插 USB-TTL、刷新端口列表确认正确 COM 号；
4. 点击 `Connect`；
5. 执行 `Full chip erase`（整片擦除）并确认完成；
6. 点击 `Disconnect`，断开 USB-TTL；
7. 恢复启动跳帽到从 Flash 启动的位置；
8. 重新连接 ST-LINK，再烧录一个正确配置调试接口的工程。

如果 UART 无法连接，依次检查启动跳帽、TX/RX 是否交叉、共地、串口号、电平和供电；不要在未确认电压兼容性时把 5 V 直接接到 3.3 V IO。

## 11. 综合自测

### 题 1

`PA9` 配置为输入上拉，按钮另一端接地。按钮按下和松开时分别读到什么？

**答案**：松开为 `1`，按下为 `0`。上拉提供默认高电平，按下后外部接地把引脚拉低。

### 题 2

为什么开漏输出写 `1` 后不是高电平？

**答案**：写 `1` 会关闭下拉 MOS 管，而上拉 MOS 管本来就关闭，因此引脚处于高阻抗；若需要高电平，必须依靠外部上拉。

### 题 3

`PA9` 同时被 USART1_TX 和普通 GPIO 使用时，为什么不能继续用 `HAL_GPIO_WritePin()` 控制它？

**答案**：启用复用功能后，PA9 的控制权交给 USART1 外设，电平由串口发送逻辑产生。若发生冲突，应使用重映射或更换引脚。

### 题 4

驱动 LED 时为什么通常选择低速输出，而不是高速？

**答案**：LED 所需翻转频率很低，低速已足够；更快边沿会增加功耗、信号带宽和电磁干扰，没有收益。

### 题 5

按钮程序已经能判断按下，但松开时偶尔闪烁，最可能缺少什么？

**答案**：机械消抖。按键触点在切换瞬间会多次弹跳，需要延时确认、计时采样或状态机处理。

## 本章小结

GPIO 学习的核心不是记住若干菜单项，而是建立“引脚电路 -> 模式 -> 电平逻辑 -> HAL API -> 外部现象”的对应关系：

```text
推挽：主动输出高/低
开漏：主动输出低，写 1 为高阻抗
上拉：无外部信号时默认高
下拉：无外部信号时默认低
复用：外设接管引脚
速度：选择满足信号要求的最小档位
```

遇到 GPIO 故障时，按“供电与接线 -> 引脚编号 -> 模式与极性 -> 时钟门控 -> 复用映射 -> 程序逻辑 -> 下载方式”的顺序排查，通常比反复改代码更快定位问题。
