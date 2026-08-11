# 第 1 章 GPIO 输入与输出（HAL 库）

## 本章闭环

GPIO（General Purpose Input/Output，通用输入输出）连接 STM32 内部程序与外部电路。本章围绕同一条主线展开：先根据外部电路判断引脚方向和有效电平，再在 CubeMX 中配置模式，由 `MX_GPIO_Init()` 完成硬件初始化，最后使用 HAL 函数读写引脚。

本章完成两个实验：

| 工程 | 目标 | 主要资源与核心机制 |
| --- | --- | --- |
| 双 LED 闪烁 | 比较推挽输出与开漏输出 | `PA9` 推挽输出、`PC13` 开漏输出、`HAL_GPIO_WritePin()` |
| 按钮控制 LED | 从输入电平过渡到按键事件 | `PA9` 上拉输入、`PC13` 开漏输出、消抖与状态机 |

```text
外部接线与电平含义 -> CubeMX 引脚模式 -> MX_GPIO_Init()
                    -> HAL 读写 -> 主循环/定时中断 -> LED 或按键现象
```

两个实验都使用 `STM32F103C8T6`。其中 `PA9` 在两个实验中的接法和方向不同，切换工程时必须同时修改接线与 CubeMX 配置。

## 1. GPIO 基础与硬件结构

### 1.1 GPIO 解决什么问题

GPIO 让程序能够直接控制或检测芯片引脚：

- 从芯片内部向外部驱动高、低电平，称为输出；
- 从外部电路读取引脚电平，称为输入；
- 将引脚交给 USART、TIM、SPI 等片上外设，称为复用功能。

GPIO 模式不能脱离电路单独选择。配置前应先确认谁驱动引脚、高低电平分别表示什么、未触发时是否会悬空，以及引脚是否已被调试接口或其他外设占用。

### 1.2 引脚类别与命名

CubeMX 封装图中的引脚可先分为两类：

| 类别 | 典型引脚 | 作用 |
| --- | --- | --- |
| 特殊功能引脚 | `VDD`、`VSS`、`VBAT`、`NRST`、启动模式选择引脚 | 供电、备用域、复位或启动配置，不能当作普通 GPIO 使用 |
| 普通 IO 引脚 | `PA0`、`PB6`、`PC13` 等 | 可配置为 GPIO，也可分配给片上外设 |

普通 IO 按端口分组，字母表示端口，数字表示端口内的引脚编号。例如 `PA9` 属于 `GPIOA`，在 HAL 代码中写作端口 `GPIOA` 和引脚掩码 `GPIO_PIN_9`。

- `GPIOA` 通常包含 `PA0`～`PA15`；
- `GPIOB` 通常包含 `PB0`～`PB15`；
- `STM32F103C8T6` 常用封装中只引出了 `PC13`～`PC15`，并非每个端口都有 16 个可用引脚；
- 引脚是否存在、是否支持某项复用功能，必须以具体型号和封装的数据手册为准。

电源正端常写作 `VDD`，地写作 `VSS`；开发板资料也可能使用 `VCC`、`GND`。实际电压范围应查目标芯片数据手册。

### 1.3 GPIO 内部信号路径

GPIO 的关键路径可以简化为：

```text
外部引脚 -> 保护网络 -> 输入缓冲器 -> 输入数据寄存器 -> HAL 读取
    ^
    +--------- 输出驱动器 <- 输出数据寄存器 <- HAL 写入
```

- **保护网络**：在数据手册规定的条件下限制异常电压产生的电流，但不能当作可随意吸收能量的保险丝；
- **输入缓冲器**：把外部电压判定为数字高、低电平；
- **输出驱动器**：由推挽或开漏结构决定引脚能否主动拉高、拉低；
- **配置与数据寄存器**：保存模式、速度、上下拉和输出状态。

CubeMX 把寄存器配置图形化并生成 `MX_GPIO_Init()`；`HAL_GPIO_ReadPin()`、`HAL_GPIO_WritePin()` 等函数最终仍通过寄存器完成读写。

输入数据寄存器（通常称为 `IDR`）反映引脚当前实际采样到的电平，读取按键和传感器时应使用它；输出数据寄存器（通常称为 `ODR`）保存程序写入的输出锁存值。`HAL_GPIO_TogglePin()` 翻转的是输出锁存值，不是对外部电压重新测量，因此它适合切换自身输出状态，不适合代替输入检测。

### 1.4 八种工作模式

STM32F1 的 GPIO 模式可以从三个问题理解：信号由谁驱动、输出级如何工作、输入未连接时由谁提供默认电平。

| 类别 | 模式 | 电气行为与用途 |
| --- | --- | --- |
| 通用输出 | 推挽输出 | 能主动输出高、低电平，适合 LED 和普通数字控制线 |
| 通用输出 | 开漏输出 | 只能主动拉低，写 1 时为高阻态，需要上拉源得到高电平 |
| 复用输出 | 推挽输出 | USART、TIM、SPI 等外设接管引脚并主动输出高、低电平 |
| 复用输出 | 开漏输出 | 外设接管引脚，输出级为开漏，常用于需要共享线路的接口 |
| 输入 | 上拉输入 | 内部弱上拉，外部未驱动时默认为高电平 |
| 输入 | 下拉输入 | 内部弱下拉，外部未驱动时默认为低电平 |
| 输入 | 浮空输入 | 无内部默认电平，只适合外部电路已提供稳定电平的情况 |
| 输入 | 模拟输入 | 关闭数字输入判定，供 ADC 等模拟功能使用 |

推挽输出使用上下两个 MOS 管交替工作：写 `0` 时主动拉向 `VSS`，写 `1` 时主动拉向 `VDD`。两个推挽输出不能直接相连后输出相反电平，否则会形成较大的对抗电流。

开漏输出关闭主动上拉通路：

| 写入值 | 推挽输出 | 开漏输出 |
| --- | --- | --- |
| `GPIO_PIN_RESET` | 主动输出低电平 | 主动拉低 |
| `GPIO_PIN_SET` | 主动输出高电平 | 高阻态，电平由外部上拉决定 |

输入端阻抗很高。若外部电路没有提供确定电平，又未配置上拉或下拉，引脚会悬空，读取结果可能在 `GPIO_PIN_RESET` 与 `GPIO_PIN_SET` 之间随机变化。

遇到新电路时，可按下面四步判断模式：

1. MCU 自己驱动、片上外设驱动，还是外部电路驱动？
2. 输出是否必须主动拉高？若需要，通常选择推挽；只需拉低且线路要共享时考虑开漏。
3. 输入未触发时是否有稳定默认电平？没有就配置上拉或下拉。
4. 当前引脚是否被调试接口、晶振或其他复用功能占用？

### 1.5 输出速度与电气边界

GPIO 输出速度描述引脚电平变化的边沿能力，不等于 CPU 执行速度，也不保证在任意负载下得到同频率的方波。STM32F1 在 CubeMX 中常见的速度档位如下：

| CubeMX 档位 | 常见标称档位 | 使用建议 |
| --- | ---: | --- |
| Low | 2 MHz | LED、继电器等低速控制 |
| Medium | 10 MHz | 较快的数字接口 |
| High | 50 MHz | 有快速边沿要求的通信接口 |

负载电容、走线和外部器件都会影响实际上升与下降时间。选择原则是：在满足时序要求的前提下使用最低速度档位，以减少功耗、电磁干扰和信号完整性问题。本章 LED 实验使用 Low。

部分引脚在数据手册中标记为 `FT`（5 V tolerant，5 V 容忍），只表示它在规定的数字输入条件下可承受特定的 5 V 输入，不能据此认为：

- GPIO 能输出 5 V；输出高电平仍接近芯片 `VDD`；
- 模拟模式、上电和掉电过程也一定容忍 5 V；
- 可以忽略最大注入电流与绝对最大额定值。

外接 USB-TTL、传感器或其他模块时优先使用 3.3 V 逻辑。是否可以接入 5 V 信号，只能根据目标引脚和数据手册判断。

### 1.6 引脚复用与重映射

同一引脚可能支持多个功能。例如 `PA9` 可作为普通 GPIO，也常作为 `USART1_TX`。当 USART1 接管 `PA9` 后，应用程序应通过 UART API 发送数据，而不是继续用 `HAL_GPIO_WritePin()` 模拟串口波形。

若默认复用引脚与已有资源冲突，可查看参考手册中的 AFIO 重映射表。例如部分 STM32F1 器件可把 USART1 重映射到 `PB6/PB7`。处理引脚冲突时按以下顺序检查：

1. 确认外设需要的信号数量和方向；
2. 在 CubeMX 封装图中查看默认复用位置；
3. 检查 SWD、晶振、供电和已有外设是否占用相关引脚；
4. 根据目标芯片的复用表选择可用的重映射方案；
5. 同步修改 PCB 接线、CubeMX 配置和代码中的端口/引脚宏。

## 2. HAL 配置与 GPIO 读写链

### 2.1 CubeMX 通用配置链

本章两个实验都遵循下面的配置链：

```text
选择芯片 -> 保留 SWD -> 分配 GPIO 功能 -> 设置模式/上下拉/速度/初始电平
        -> 生成 MX_GPIO_Init() -> 在 USER CODE 区编写应用 -> 编译并下载
```

具体步骤如下：

1. 通过 `File -> New Project` 选择 `STM32F103C8T6`；
2. 在 `System Core -> SYS -> Debug` 中选择 `Serial Wire`，保留 SWD 调试能力；
3. 在芯片图中把目标引脚设为 `GPIO_Output` 或 `GPIO_Input`；
4. 在 `System Core -> GPIO` 中设置输出类型、初始电平、速度和上下拉；
5. 在 `Project Manager` 中设置工程名、路径和工具链，例如 `MDK-ARM`；
6. 生成代码，并把应用逻辑写入 `USER CODE BEGIN` 与 `USER CODE END` 之间；
7. 编译确认没有 error 和 warning，再通过 ST-Link 下载。

若未保留 `Serial Wire`，程序下载后可能占用调试引脚；若输入没有上拉/下拉或外部偏置，读取值会不稳定；若初始输出电平设置错误，LED 可能在进入 `while (1)` 前就被点亮。

### 2.2 `MX_GPIO_Init()` 完成了什么

CubeMX 生成的 `MX_GPIO_Init()` 主要完成三件事：

1. 开启对应 GPIO 端口的时钟；
2. 在初始化前写入输出引脚的初始电平；
3. 使用 `GPIO_InitTypeDef` 和 `HAL_GPIO_Init()` 配置引脚、模式、上下拉和速度。

因此程序还未进入主循环时，引脚状态就可能已经发生变化。每次修改 CubeMX 配置后都应重新生成代码，并检查自定义逻辑是否仍位于用户代码区域。

生成代码中的 `GPIO_InitTypeDef` 是一张 GPIO 配置单：结构体成员保存引脚掩码、模式、上下拉和速度，`HAL_GPIO_Init()` 接收它的地址并把配置写入硬件。阅读或手写初始化代码时，可以按“先填结构体，再传给初始化函数”的顺序理解：

```c
GPIO_InitTypeDef GPIO_InitStruct = {0};

GPIO_InitStruct.Pin = GPIO_PIN_9;
GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
GPIO_InitStruct.Pull = GPIO_NOPULL;
GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
```

这里的 `&GPIO_InitStruct` 是结构体变量的地址。HAL 函数通过指针读取配置成员；这也是 CubeMX 生成代码看起来比单个写电平函数更长的原因。

### 2.3 HAL 读写函数

写指定引脚：

```c
HAL_GPIO_WritePin(GPIOx, GPIO_Pin, PinState);
```

- `GPIOx`：端口，例如 `GPIOA`、`GPIOC`；
- `GPIO_Pin`：引脚掩码，例如 `GPIO_PIN_9`、`GPIO_PIN_13`；
- `PinState`：`GPIO_PIN_RESET` 写 0，`GPIO_PIN_SET` 写 1。

一个端口的多个引脚可以通过按位或组成掩码，一次传给 `HAL_GPIO_WritePin()`：

```c
HAL_GPIO_WritePin(GPIOA,
                  GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_2,
                  GPIO_PIN_RESET);
```

这些 `GPIO_PIN_x` 不是连续的编号，而是“对应位为 1”的掩码。多引脚写入只影响掩码选中的位；若应用需要同时控制同一端口上的多个器件，应先画出“哪一位为 0/1 时哪个器件有效”的对应关系。不要把 HAL 的单引脚/掩码写入误解为可以安全覆盖整个端口，端口上的其他功能引脚仍需单独保护。

翻转指定输出引脚：

```c
HAL_GPIO_TogglePin(GPIOx, GPIO_Pin);
```

它只翻转输出数据，不会自动判断外部器件是高电平有效还是低电平有效。控制多个有效电平相反的器件时，显式写 `SET/RESET` 更容易读懂。

读取引脚：

```c
GPIO_PinState state;
state = HAL_GPIO_ReadPin(GPIOx, GPIO_Pin);
```

返回 `GPIO_PIN_RESET` 表示低电平，返回 `GPIO_PIN_SET` 表示高电平。程序必须结合接线判断这个电平对应“按下”“松开”“点亮”还是“熄灭”。

毫秒延时：

```c
HAL_Delay(500);  // 500 ms
```

`HAL_Delay()` 依赖 HAL 时基，适合入门实验和低速控制，不适合精确微秒时序，也不适合在需要并发处理多项任务的主循环中长时间阻塞。

## 3. 实验一：PC13 与 PA9 双 LED 闪烁

### 3.1 目标、接线与现象

本实验用两种不同接法比较开漏和推挽输出：

```text
板载 LED：VDD -> LED 阳极，LED 阴极 -> PC13
外接 LED：PA9 -> 限流电阻（约 1 kΩ）-> LED 阳极，LED 阴极 -> GND
```

- `PC13` 采用低电平有效接法：写 0 点亮，写 1 后由上拉使其熄灭；
- `PA9` 采用高电平有效接法：写 1 点亮，写 0 熄灭；
- 外接 LED 必须串联限流电阻，极性以器件符号和实际封装为准；
- 下载并复位后，两颗 LED 应同时亮灭，完整周期约为 1 s。

### 3.2 CubeMX 配置与数据流

| 引脚 | GPIO 模式 | 初始电平 | 速度 |
| --- | --- | --- | --- |
| `PC13` | Output Open-Drain | High，LED 熄灭 | Low |
| `PA9` | Output Push-Pull | Low，LED 熄灭 | Low |

程序的数据流为：

```text
while (1) -> HAL_GPIO_WritePin() -> 输出数据寄存器
          -> 推挽/开漏输出级 -> LED 电流 -> 亮灭现象
```

`PC13` 的开漏输出写 1 时只是停止拉低，电平是否为高取决于板上上拉和 LED 电路；`PA9` 的推挽输出则可以主动输出高、低电平。

### 3.3 主循环代码

将下面的逻辑放入 `main.c` 的 `while (1)` 用户代码区域：

```c
while (1)
{
  // 点亮：PC13 低有效，PA9 高有效
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_SET);
  HAL_Delay(500);

  // 熄灭
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9, GPIO_PIN_RESET);
  HAL_Delay(500);
}
```

如果只验证一颗推挽 LED，也可使用：

```c
while (1)
{
  HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_9);
  HAL_Delay(500);
}
```

### 3.4 现象解释与边界

两段 `HAL_Delay(500)` 组成约 1 s 的完整周期。若只有一颗 LED 工作，先检查接线、限流电阻和有效电平，不要在未确认电路前直接交换 `SET/RESET`。

该实验只验证低速 GPIO 输出。实际负载超过单个引脚允许的输出电流时，必须增加三极管或 MOS 管等驱动级，不能由 GPIO 直接带动大电流器件。

同一判断方法也适用于低电平触发的有源蜂鸣器：控制脚接到 GPIO 后，先确认模块的有效电平，再把“响/停”映射到 `GPIO_PIN_RESET/SET`。GPIO 输出的是控制电平，不是蜂鸣器声音频率；有源蜂鸣器通常只需维持有效电平，无源蜂鸣器则需要定时器等周期波形。

## 4. 实验二：按钮控制板载 LED

### 4.1 目标、接线与输入逻辑

按钮一端接 `PA9`，另一端接 GND，`PA9` 配置为上拉输入；`PC13` 继续控制低电平有效的板载 LED。

```text
VDD -- 内部上拉电阻 -- PA9 -- 按钮 -- GND

PA9 -> HAL_GPIO_ReadPin() -> 电平/消抖/事件 -> PC13 -> 板载 LED
```

- 按钮松开：内部上拉使 `PA9` 为高电平，读到 `GPIO_PIN_SET`；
- 按钮按下：`PA9` 接地，读到 `GPIO_PIN_RESET`；
- 按住时 LED 点亮，松开时 LED 熄灭。

四脚按键的同侧引脚通常内部相连，接线前应按开发板原理图或万用表确认开关两端，避免把同一侧误当作两组触点。

### 4.2 按键抖动与事件

机械触点在按下和释放瞬间可能连续跳变。直接读取电平适合实现“按住亮、松开灭”，但若要实现“按一下翻转一次”，必须把连续电平转换成一次事件，并进行消抖。

```text
瞬时采样 -> 消抖确认 -> 稳定状态 -> 按下/松开事件 -> 应用动作
```

电平表示当前状态，事件表示状态发生了一次变化。若每次循环看到低电平就翻转 LED，长按期间会连续翻转；若触点抖动未过滤，一次操作也可能产生多个事件。

### 4.3 CubeMX 配置与最小程序

| 引脚 | GPIO 模式 | 配置 |
| --- | --- | --- |
| `PC13` | Output Open-Drain | 初始 High，速度 Low |
| `PA9` | Input | Pull-up |

最小电平控制程序如下：

```c
while (1)
{
  GPIO_PinState button = HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_9);

  if (button == GPIO_PIN_SET)
  {
    // 松开：熄灭低有效 LED
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
  }
  else
  {
    // 按下：点亮低有效 LED
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
  }
}
```

这段代码用于先验证接线、上下拉和有效电平。它检测的是当前电平，不会产生“按一次”的独立事件。

### 4.4 阻塞式消抖与单次翻转

最简单的按下消抖是在检测到低电平后延时约 20 ms，再次确认：

```c
if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_9) == GPIO_PIN_RESET)
{
  HAL_Delay(20);
  if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_9) == GPIO_PIN_RESET)
  {
    // 确认按键按下
  }
}
```

若要让一次完整按下只翻转一次，可在翻转后等待松手：

```c
if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_9) == GPIO_PIN_RESET)
{
  HAL_Delay(20);
  if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_9) == GPIO_PIN_RESET)
  {
    HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);

    while (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_9) == GPIO_PIN_RESET)
    {
      // 等待松手，防止长按期间反复翻转
    }
    HAL_Delay(20);
  }
}
```

该写法适合功能单一的入门实验，但按键按住时 CPU 会停在 `while` 中，延时期间也无法及时处理显示、串口或其他轮询任务。

### 4.5 非阻塞消抖状态机

下面是从课程最小写法升级到多任务工程时可采用的方案：由定时器每 20 ms 采样一次，连续两次结果一致才更新稳定状态，并在稳定松手时产生一次事件。它是工程化扩展，不是完成本章最小按钮实验的必要条件。

先在 CubeMX 中给 `PA9`、`PC13` 设置用户标签 `BUTTON`、`LED`，再配置周期约 20 ms 的 TIM2 更新中断。若 TIM2 输入时钟为 72 MHz，设置 `PSC = 14399`、`ARR = 99`，更新周期为：

$$
T=\frac{(PSC+1)(ARR+1)}{72\,\text{MHz}}=20\,\text{ms}
$$

按键状态机：

```c
static uint8_t key_state;            // 稳定状态：1=按下，0=松开
static uint8_t last_sample;          // 上一次采样结果
static volatile uint8_t key_event;   // 中断产生，主循环消费

static uint8_t Key_GetState(void)
{
  return (HAL_GPIO_ReadPin(BUTTON_GPIO_Port, BUTTON_Pin) == GPIO_PIN_RESET) ? 1U : 0U;
}

void Key_Tick(void)
{
  uint8_t sample = Key_GetState();

  if (sample == last_sample && sample != key_state)
  {
    uint8_t previous = key_state;
    key_state = sample;

    if (previous != 0U && key_state == 0U)
    {
      key_event = 1U;
    }
  }

  last_sample = sample;
}

uint8_t Key_GetNum(void)
{
  uint8_t event;

  __disable_irq();
  event = key_event;
  key_event = 0U;
  __enable_irq();

  return event;
}
```

在 `MX_TIM2_Init()` 之后启动更新中断，并在 HAL 定时器回调中采样：

```c
HAL_TIM_Base_Start_IT(&htim2);

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
  if (htim->Instance == TIM2)
  {
    Key_Tick();
  }
}
```

主循环只消费事件：

```c
if (Key_GetNum() != 0U)
{
  HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);
}
```

该模型将职责分成三层：`Key_GetState()` 读取瞬时电平，`Key_Tick()` 完成采样与消抖，`Key_GetNum()` 向主循环交付事件。中断中只做短小的状态更新，不执行延时、串口发送或复杂业务。

### 4.6 三种实现方式的适用范围

| 方式 | 检测对象 | 消抖/等待方式 | 对主循环影响 | 适用场景 |
| --- | --- | --- | --- | --- |
| 电平控制型 | 当前电平 | 不处理或单独消抖 | 无阻塞 | 按住亮、松开灭 |
| 阻塞式事件检测 | 一次完整操作 | 延时并等待松手 | 按住时完全阻塞 | 单一功能入门实验 |
| 非阻塞事件模型 | 稳定状态变化 | 定时采样状态机 | 不阻塞 | 多任务或工程项目 |

选择方法时先确认应用要的是“持续状态”还是“单次事件”。只有在任务并发或响应时间确有要求时，才需要把定时器和状态机引入主示例。

### 4.7 数字传感器输入的迁移方法

许多光敏、红外或磁控模块同时提供模拟输出 `AO` 和数字输出 `DO`：`AO` 是连续电压，留给 ADC 章节；`DO` 是比较器根据阈值输出的高低电平，可以按普通 GPIO 输入处理。本章若将 `DO` 接到某个输入引脚，配置上拉/下拉后即可读取：

```c
GPIO_PinState sensor = HAL_GPIO_ReadPin(SENSOR_GPIO_Port, SENSOR_Pin);

if (sensor == GPIO_PIN_SET)
{
  // 当前模块的高电平状态
}
else
{
  // 当前模块的低电平状态
}
```

模块的“见光/遮光”极性并不统一，电位器还会改变比较阈值。接入新模块时应分别观察两种状态下的 `DO` 电平，再决定程序分支；不要把某块课程模块的高低电平结论直接套到其他模块。

## 5. 调试、下载与工程边界

### 5.1 正常 ST-Link 流程

1. 在 CubeMX 中保留 `Serial Wire`；
2. 连接 ST-Link、目标板、SWDIO、SWCLK 和 GND；
3. 编译工程并下载；
4. 必要时按开发板复位键观察程序启动。

单步调试时可关闭或降低编译优化。优化可能改变代码布局、变量存储和执行顺序，使断点表现与源代码不完全一致。

### 5.2 调试接口失联后的恢复

若程序错误关闭或重映射调试接口，ST-Link 可能无法再次连接。可按开发板说明进入 STM32 系统存储器 bootloader，再通过 STM32CubeProgrammer 全片擦除。

连接前必须满足以下电气条件：

- USB-TTL 使用与目标芯片匹配的 3.3 V TTL 电平；
- USART 通常交叉连接：MCU `PA9/USART1_TX` 接 USB-TTL `RXD`，MCU `PA10/USART1_RX` 接 USB-TTL `TXD`；
- MCU 与 USB-TTL 必须共地；
- BOOT0、供电方式和复位时机以开发板原理图与说明为准。

恢复步骤：

1. 断开 ST-Link，按开发板说明设置启动跳帽，使芯片进入系统存储器 bootloader；
2. 连接 USB-TTL、`PA9`、`PA10` 和 GND；
3. 打开 STM32CubeProgrammer，接口选择 `UART`；
4. 通过设备管理器或拔插 USB-TTL 确认 COM 口；
5. 连接成功后执行 `Full chip erase`；
6. 断开连接并恢复正常启动跳帽；
7. 重新连接 ST-Link 并下载程序。

全片擦除会删除芯片中的用户程序和数据。若 UART bootloader 仍无法连接，应依次检查 BOOT0、复位时机、逻辑电平、TX/RX 方向、共地和芯片型号，不能通过向 GPIO 直接施加 5 V 来尝试恢复。

### 5.3 从入门示例到工程实现

本章代码用于建立最小闭环，工程中还需根据实际需求补充边界处理：

- `HAL_Delay()` 和等待松手循环会阻塞 CPU，多任务场景应改为定时调度或状态机；
- GPIO 只能驱动数据手册允许范围内的负载，大电流器件需要外部驱动级；
- 多个模块共用 HAL 回调时，应由应用层统一分发，避免在不同驱动文件中重复定义同一个回调；
- 复用功能切换必须同步修改 CubeMX、接线和应用代码，不能只改其中一处；
- 自动生成代码之外的逻辑应放在用户代码区或独立模块中，避免重新生成时被覆盖。

当 GPIO 数量和业务动作增加时，可把硬件操作封装到独立模块中：`.c` 文件保存 `HAL_GPIO_Init()`、读写函数和引脚映射，`.h` 文件只暴露 `LED_On()`、`Key_GetNum()`、`Sensor_Get()` 等业务接口，`main.c` 负责初始化顺序和功能组合。这样更换接线时主要修改驱动模块，不会把端口细节散落在主循环中；但模块化不能掩盖有效电平，接口命名和注释仍应说明高/低电平对应的物理状态。

## 6. 验收与排错

正常情况下，实验一的两颗 LED 每 500 ms 同时切换一次，实验二的按钮按下后板载 LED 点亮、松开后熄灭；采用事件模型时，每次完整按下或松手只产生一次约定事件。

排错时按真实链路检查：

```text
供电/共地/接线 -> 引脚与复用映射 -> GPIO 时钟与模式 -> 上下拉/初始电平
                -> HAL 读写 -> 定时器/中断 -> 状态机与应用逻辑 -> 可观察现象
```

| 现象 | 优先检查 |
| --- | --- |
| LED 始终不亮 | LED 极性、限流电阻、是否共地、板载 LED 是否确实连接 `PC13` |
| LED 亮灭逻辑相反 | 电路是高有效还是低有效；开漏写 1 是否有上拉源 |
| 上电后 LED 状态错误 | CubeMX 的初始输出电平，以及 `MX_GPIO_Init()` 中初始化前写入的电平 |
| 按钮读数随机 | `PA9` 是否配置 Pull-up；按钮是否悬空；模块是否共地 |
| 按一次翻转多次 | 是否把持续电平当作事件；是否完成按下/松手消抖 |
| 非阻塞按键没有事件 | 是否调用 `HAL_TIM_Base_Start_IT()`；回调是否判断 `TIM2`；定时周期是否正确 |
| 复用外设没有波形 | 引脚是否仍配置为普通 GPIO；外设时钟、复用功能和重映射是否一致 |
| CubeMX 重新生成后代码消失 | 自定义代码是否写在 `USER CODE BEGIN/END` 区域 |
| 编译通过但 ST-Link 下载失败 | SWD 是否保留、ST-Link 接线、供电、复位和启动跳帽 |
| CubeProgrammer 找不到串口 | USB-TTL 驱动、COM 口、3.3 V 电平、TX/RX 交叉连接和共地 |
| 外部 5 V 信号接入异常 | 引脚是否为 `FT`、当前是否为数字输入、注入电流和绝对最大额定值 |

## 本章小结

GPIO 配置的核心不是背模式名称，而是建立“外部电路 -> 电平含义 -> GPIO 模式 -> HAL 读写 -> 可观察现象”的完整链路。输出时先判断器件的有效电平和是否需要主动拉高，再选择推挽或开漏；输入时先确保未触发状态不悬空，再把读取到的电平解释为具体状态。

使用 HAL 库时，CubeMX 负责生成端口时钟、初始电平和 `HAL_GPIO_Init()` 配置，应用程序通过 `HAL_GPIO_WritePin()`、`HAL_GPIO_ReadPin()` 和 `HAL_GPIO_TogglePin()` 完成功能。完成本章后，应能独立配置一个 GPIO 输入或输出实验，并沿供电、接线、模式、读写和应用逻辑逐层定位故障。
