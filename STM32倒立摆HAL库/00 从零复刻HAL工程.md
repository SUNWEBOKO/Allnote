# 00 从零复刻 HAL 工程

## 本章问题

怎样从空白 CubeMX 工程开始，搭出一个能编译、下载、默认不启动闭环，并且后续 13 章都能直接复用的 HAL 底座？

## 本章完成后得到什么

完成本章后，新手应当能够从空白 STM32CubeMX 工程开始，独立得到一个可编译、可下载、默认不主动启动闭环的 HAL 工程，并能继续执行第 01～13 章实验。首次上电仍必须断开电机 VM 或准备硬件急停。

---

## 1. 开始前的准备

### 1.1 软件

建议使用以下版本：

| 软件/包                       | 建议版本                | 用途              |
| -------------------------- | ------------------- | --------------- |
| STM32CubeMX                | 6.17 及以上（配套 `.ioc` 由 6.17.0 保存） | 图形化配置和代码生成      |
| STM32CubeF1                | V1.8.7              | HAL、CMSIS 和启动文件 |
| CMake                      | 3.22 以上             | 生成/构建工程         |
| Ninja                      | 1.10 以上             | CMake 构建后端      |
| `arm-none-eabi-gcc`        | GNU Tools for STM32 | 编译和链接           |
| STM32 VS Code 官方插件         | 与 CubeMX/CMake 配套   | 自动加载、编译、下载和调试   |
| ST-LINK Utility/Programmer | 与 ST-Link 匹配        | 下载和复位           |


### 1.2 硬件

- STM32F103C8T6 最小系统板；
- 课程 TB6612FNG 驱动板；
- 12 V 编码减速电机；
- OLED（PB8/PB9 软件 I²C）；
- 角度传感器 G1（PB0/ADC1_IN8）；
- 旋钮 RP1～RP4（PA2～PA5/ADC2_IN2～IN5）；
- 按键 K1～K4；
- 编码器 A/B（PA6/PA7）；
- 电机 PWM（PA0/TIM2_CH1）；
- USB-TTL、ST-Link、示波器或逻辑分析仪（建议准备）。

第一次配置 CubeMX 时先不要接电机电源。USB-TTL 的 TX/RX/GND 与开发板共地，外部 3.3 V 电源不要重复并接。

### 1.3 目录

建议先新建一个空目录，不要直接覆盖已经能运行的课程工程：

```text
E:\ProjectStm\倒立摆_rebuild
```

本教程后面的命令都以这个目录为例。完成后可以再改名为 `E:\ProjectStm\倒立摆`。

---

## 2. 在 CubeMX 新建工程

### 2.1 选择芯片

1. 打开 STM32CubeMX。
2. 选择 `File → New Project`。
3. 在 `MCU Selector` 中搜索：

   ```text
   STM32F103C8T6
   ```

4. 选择 `STM32F103C(8-B)Tx`，点击 `Start Project`。

不要选 `STM32F103C8T6` 的其他封装或 STM32F103RB/CB 等容量更大的型号，否则链接脚本、启动文件和引脚封装会不同。

### 2.2 Project Manager 设置

在 `Project Manager → Project` 中设置：

| 项目 | 设置 |
|---|---|
| Project Name | `InvertedPendulum` |
| Toolchain / IDE | `CMake` |
| Firmware Package | `STM32Cube FW_F1 V1.8.7` |
| Generate Under Path | `E:\ProjectStm\倒立摆_rebuild` |
| Generate Code | 勾选 |
| Keep User Code | 勾选 |

在 `Code Generator` 中建议选择：

```text
Generate peripheral initialization as a pair of '.c/.h' files per peripheral
```

这样会生成 `tim.c/tim.h`、`adc.c/adc.h`、`gpio.c/gpio.h`、`usart.c/usart.h`，后面添加用户代码时不容易和 CubeMX 自动生成代码混在一起。

> 如果教程中的 `.ioc` 由旧版 CubeMX 保存，重新生成时选择同一 MCU 即可；不要把 `.ioc`、`.c` 和 `.h` 混在不同 STM32 系列之间复制。

---

## 3. 配置时钟

进入 `Clock Configuration`。

### 3.1 72 MHz 时钟树

按以下链路配置：

```text
HSE（外部 8 MHz 晶振）
    ↓
PLL Source Mux = HSE
    ↓
PLLMUL = ×9
    ↓
SYSCLK = 72 MHz
    ↓
AHB Prescaler = /1  → HCLK 72 MHz
    ↓
APB1 Prescaler = /2  → PCLK1 36 MHz
    ↓
APB2 Prescaler = /1  → PCLK2 72 MHz
```

STM32F1 在 APB 预分频不为 1 时，APB 定时器时钟为 PCLK 的 2 倍，因此：

```text
TIM1CLK = TIM2CLK = TIM3CLK = 72 MHz
```

### 3.2 ADC 时钟

ADC 最大允许时钟为 14 MHz，设置：

```text
ADC clock = PCLK2 / 6 = 12 MHz
```

在 CubeMX 中如果时钟树右侧有 `ADC Prescaler`，选择 `/6`；如果当前版本只在 RCC/ADC 参数中显示，确认生成的 `SystemClock_Config()` 中存在：

```c
PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_ADC;
PeriphClkInit.AdcClockSelection = RCC_ADCPCLK2_DIV6;
HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit);
```

保存 `.ioc` 后检查时钟树没有红色错误。

### 3.3 固件生成前的时钟验收

在继续配置引脚前，确认你能在 CubeMX 中读出：

```text
SYSCLK = 72 MHz
HCLK  = 72 MHz
PCLK1 = 36 MHz
PCLK2 = 72 MHz
ADC  = 12 MHz
```

若 HSE 不能启动，HAL 的 `SystemClock_Config()` 必须进入 `Error_Handler()`，不能静默继续使用错误的时钟假设。

---

## 4. 配置 GPIO 和引脚

在 `Pinout & Configuration → Pinout & Configuration` 中逐个点击引脚。信号和 GPIO 设置必须成对完成。

### 4.1 总表

| 引脚 | CubeMX Signal | GPIO 设置 | 初始电平/标签 |
|---|---|---|---|
| PA0 | `TIM2_CH1` | Alternate Function Push-Pull | `MOTOR_PWM` |
| PA2 | `ADC2_IN2` | Analog | `RP1` |
| PA3 | `ADC2_IN3` | Analog | `RP2` |
| PA4 | `ADC2_IN4` | Analog | `RP3` |
| PA5 | `ADC2_IN5` | Analog | `RP4` |
| PA6 | `TIM3_CH1` | —（由编码器模式自动生成） | `ENCODER_A` |
| PA7 | `TIM3_CH2` | —（由编码器模式自动生成） | `ENCODER_B` |
| PA9 | `USART1_TX` | Alternate Function Push-Pull | `USART1_TX` |
| PA10 | `USART1_RX` | Input | `USART1_RX` |
| PA11 | `GPIO_Input` | Pull-up | `K3` |
| PA12 | `GPIO_Input` | Pull-up | `K4` |
| PB0 | `ADC1_IN8` | Analog | `ANGLE_G1` |
| PB8 | `GPIO_Output` | Open-Drain，No Pull-up | High，`OLED_SCL` |
| PB9 | `GPIO_Output` | Open-Drain，No Pull-up | High，`OLED_SDA` |
| PB10 | `GPIO_Input` | Pull-up | `K1` |
| PB11 | `GPIO_Input` | Pull-up | `K2` |
| PB12 | `GPIO_Output` | Push-Pull | Low，`AIN1` |
| PB13 | `GPIO_Output` | Push-Pull | Low，`AIN2` |
| PC13 | `GPIO_Output` | Push-Pull | High，`LED` |

PA13/PA14 保持 `Serial Wire`：PA13 为 SWDIO，PA14 为 SWCLK。

表中的"标签"只是图纸阅读用的显示名，不影响生成代码，可以自行命名；PA6/PA7 的输入模式和上拉由编码器模式的 MSP 初始化自动生成，不需要在 GPIO 页单独设置。

### 4.2 OLED 开漏设置

PB8/PB9 是软件 I²C，不是 HAL 硬件 I²C：

1. 选择 `GPIO_Output`。
2. 在 GPIO 设置中把 Output Mode 选为 `Open-Drain`。
3. Pull-up 选择 `No Pull-up`（外部上拉由硬件板提供）。
4. 初始输出设为 High。

错误设置成推挽会把软件 I²C 的总线行为和电平驱动方式改变。

### 4.3 按键设置

四个按键均为低有效：

```text
按下 = 0
松开 = 1
```

CubeMX 中全部设置为 `GPIO_Input + Pull-up`，不要配置成下拉。

### 4.4 电机方向和 LED

PB12/PB13 初始为 Low，PC13 初始为 High：

```text
PB12=0, PB13=0 → TB6612 滑行
PC13=1        → 板载 LED 熄灭
```

不要在 GPIO 初始化前让方向脚处于不确定状态。

---

## 5. 配置 TIM1：1 ms 控制节拍

点击 `TIM1 → Internal Clock`。

在 `Parameter Settings` 设置：

| 参数 | 值 |
|---|---:|
| Prescaler | `71` |
| Counter Period | `999` |
| Clock Division | `DIV1` |
| AutoReloadPreload | `Disable` |

在 `NVIC Settings` 勾选 `TIM1 update interrupt`，设置：

```text
Preemption Priority = 2
Sub Priority = 0
```

计算：

$$
T=\frac{72\text{ MHz}}{(71+1)(999+1)}=1\text{ ms}
$$

这一路只负责产生固定节拍。不要在 TIM1 回调中放 OLED、阻塞串口或无限 ADC 等待。

---

## 6. 配置 TIM2：20 kHz 电机 PWM

点击 `PA0 → TIM2_CH1`，然后在 `TIM2 → PWM Generation CH1` 中设置：

| 参数 | 值 |
|---|---:|
| Prescaler | `35` |
| Counter Period | `99` |
| Pulse | `0` |
| PWM mode | `PWM1` |
| Output Compare Polarity | `High` |

计算：

$$
f_{PWM}=\frac{72\text{ MHz}}{(35+1)(99+1)}
=20\text{ kHz}
$$

TIM2 PWM 的 CCR 计划使用 `0～100` 的百分点。不要把 `PWM=20` 写成 20 Hz。

为什么选 20 kHz：TB6612 的 PWMA 是速度闸门，占空比决定电机两端的平均电压；开关频率选在 20 kHz 是为了远高于人耳可听频率（避免电流纹波让电机"啸叫"），又远快于电机的机械响应——电机和 2.1 节要讲的直觉一样，只感受平均值。

---

## 7. 配置 TIM3：正交编码器

点击 `PA6 → TIM3_CH1`，将 TIM3 模式设置为：

```text
Encoder Mode
```

确认 PA7 同时映射为 `TIM3_CH2`。在 `Parameter Settings` 设置：

| 参数 | 值 |
|---|---:|
| Prescaler | `0` |
| Counter Period | `65535` |
| Encoder Mode | `TI12` |
| IC1 Polarity | `Rising Edge` |
| IC1 Input Filter | `15` |
| IC2 Polarity | `Falling Edge` |
| IC2 Input Filter | `15` |

CH2 Falling 是课程硬件约定，不能为了"看起来和 CH1 一样"改成 Rising。电机逻辑方向仍要通过手转和正 PWM 单独确认。

TI12 编码模式的直觉：计数器对 A/B 两相的每个边沿都计数，旋转方向由 A、B 谁先变化的相位关系自动判别——所以 CPU 不用软件数脉冲，读计数器就同时得到了位置和方向。

---

## 8. 配置 ADC1：角度传感器

点击 `PB0 → ADC1_IN8`，在 ADC1 参数中设置：

| 参数 | 值 |
|---|---|
| Resolution | 12 bits |
| Right/left alignment | Right |
| Scan Conversion | Disable |
| Continuous Conversion | Disable |
| Number of conversions | 1 |
| External trigger | Software Start |
| Channel 8 rank | 1 |
| Sampling time | 55.5 cycles |

HAL 代码在初始化后执行一次：

```c
HAL_ADCEx_Calibration_Start(&hadc1);
```

角度控制不能把 `0～4095` 的 ADC 原始码直接称为"角度"；它是课程控制器的反馈单位。55.5 cycles 的采样时间则是给角度传感器（电位器类信号源）的内阻留足充电时间，采样电容充得稳，读数才不漂。

---

## 9. 配置 ADC2：四个旋钮

点击 PA2～PA5，分别选择 `ADC2_IN2～ADC2_IN5`，每个通道设置：

```text
Right alignment
Sampling time = 55.5 cycles
Software trigger
```

ADC2 的配置路线要特别注意：**CubeMX 里只配置一个转换通道**（`Scan Conversion = Disable`、`Number of conversions = 1`，比如先配 IN2），四个引脚都设为模拟输入。配套工程的 `BSP_ReadKnobs()` 在每次读取前用 `HAL_ADC_ConfigChannel()` 逐通道切换 IN2～IN5，再各自触发一次转换：

```text
ADC2_IN2 → 读 RP1
ADC2_IN3 → 读 RP2
ADC2_IN4 → 读 RP3
ADC2_IN5 → 读 RP4
```

不要在 CubeMX 里把 ADC2 配成"扫描 + 4 通道"——那会生成 4 个 rank 的扫描初始化，和 `BSP_ReadKnobs()` 的逐通道重配互相打架。`.ioc` 里对应的键是 `ADC2.ScanConvMode=ADC_SCAN_DISABLE`、`ADC2.NbrOfConversion=1`。`BSP_ReadKnobs()` 负责把四个旋钮值放入 `knobs[0..3]`，主循环只使用这四个结果。

---

## 10. 配置 USART1

点击 `USART1 → Asynchronous`，设置：

| 参数 | 值 |
|---|---|
| Baud Rate | `9600` |
| Word Length | `8 Bits` |
| Parity | `None` |
| Stop Bits | `1` |
| Hardware Flow Control | `None` |
| Mode | `TX_RX` |

PA9 为 TX，PA10 为 RX。HAL 发送使用 `HAL_UART_Transmit()`；串口输出放在主循环，不放在 TIM1 控制回调。

---

## 11. 生成 CubeMX 底座

点击 `GENERATE CODE`。初次生成后，项目至少应有：

```text
Core/Inc/
  main.h
  stm32f1xx_it.h
  tim.h
  adc.h
  gpio.h
  usart.h
Core/Src/
  main.c
  stm32f1xx_it.c
  stm32f1xx_hal_msp.c
  tim.c
  adc.c
  gpio.c
  usart.c
```

### 11.1 `main.c` 的最小接入

CubeMX 生成 `main.c` 后，只在用户区域加入应用头文件和两个调用：

```c
/* USER CODE BEGIN Includes */
#include "app.h"
/* USER CODE END Includes */
```

在所有外设初始化完成之后：

```c
/* USER CODE BEGIN 2 */
App_Init();
/* USER CODE END 2 */
```

在主循环中：

```c
/* USER CODE BEGIN WHILE */
App_Process();
/* USER CODE END WHILE */
```

`App_Init()` 内部启动 TIM1 中断、TB6612、OLED 和 ADC 校准；`App_Process()` 只处理旋钮、OLED 和串口等主循环任务。不要把这两个函数的内容重新复制一份到 `main.c`。

### 11.2 `USER CODE` 规则

CubeMX 自动生成区域中的内容只能在：

```c
/* USER CODE BEGIN ... */
/* USER CODE END ... */
```

之间修改。较大的 PID、状态机和板级适配不要直接塞进 `main.c`，应放到 `User/Src`。

### 11.3 重新生成后的检查

每次点击 `GENERATE CODE` 后，重新检查：

- `MX_TIM1_Init()` 是否仍然存在；
- `MX_TIM2_Init()` 是否仍然存在；
- `MX_TIM3_Init()` 是否仍然存在；
- `HAL_TIM_Base_Start_IT(&htim1)` 是否由应用层调用；
- `TIM1_UP_IRQHandler()` 是否调用 `HAL_TIM_IRQHandler(&htim1)`；
- ADC1 是否仍为 PB0/IN8/55.5 cycles；
- ADC 时钟是否仍为 PCLK2/6；
- USART1 是否仍为 9600 8N1。

本教程的 HAL 工程使用 `NVIC_PRIORITYGROUP_4`。TIM1 配置为抢占优先级 2、子优先级 0。重新生成代码后，确认外设和 NVIC 参数仍与 `.ioc` 一致。

不要把旧 SPL 工程的函数复制到 CubeMX 生成文件中。

---

## 12. 生成代码后的文件边界

CubeMX 负责生成 `Core/Inc/`、`Core/Src/`、`Drivers/`、启动文件、链接脚本和中断文件。生成后按下面的边界组织代码：

```text
Core/       CubeMX 生成的启动代码和 HAL 外设初始化
User/       自己编写的 PID、BSP、应用调度和板级驱动
Tests/      脱离硬件的主机算法测试
```

`Core/` 中的初始化函数由 CubeMX 生成。应用层只调用它们，不在 `main.c` 重复实现 `MX_GPIO_Init()`、`MX_TIM1_Init()`、`MX_ADC1_Init()` 等函数。

长期代码放在 `User/`，小型入口改动才放在 `USER CODE` 区域。

在 CubeMX 重新生成代码、再由 VS Code 插件编译后，确认 `Core/` 文件存在、应用层能调用 `MX_*_Init()`，再继续本章第 13 节。

---

## 13. 加入应用层文件

在工程根目录建立：

```text
User/Inc/
User/Src/
User/Drivers/TB6612/
User/Drivers/OLED/
Tests/host/
```

按配套 HAL 例程的同名文件建立：

```text
User/Inc/control_types.h
User/Inc/pid.h
User/Inc/cascade.h
User/Inc/balance.h
User/Inc/swingup.h
User/Inc/bsp.h
User/Inc/app.h
User/Inc/app_config.h

User/Src/pid.c
User/Src/cascade.c
User/Src/balance.c
User/Src/swingup.c
User/Src/bsp.c
User/Src/app.c

User/Drivers/TB6612/tb6612.h
User/Drivers/TB6612/tb6612.c
User/Drivers/OLED/OLED.h
User/Drivers/OLED/OLED.c
User/Drivers/OLED/OLED_Font.h
```

这些文件是控制核心和 BSP，不应放进 CubeMX 的自动生成区域。

| 文件 | 新手第一次只需要确认的内容 |
|---|---|
| `User/Src/pid.c` | 一个 PID 实例保存积分、上一拍误差和输出 |
| `User/Src/cascade.c` | 外环输出先限幅，再作为内环目标 |
| `User/Src/balance.c` | 角度越界时返回 0，不继续执行控制 |
| `User/Src/swingup.c` | 停止优先、脉冲计时、超时和故障状态 |
| `User/Src/bsp.c` | ADC、编码器、电机、按键、UART 的 HAL 适配 |
| `User/Src/app.c` | 1 ms 调度、模式选择、按键和遥测 |
| `User/Drivers/TB6612` | 只处理 GPIO 方向和 TIM2 比较值 |
| `User/Drivers/OLED` | 只处理 PB8/PB9 软件 I²C 和显示 |

### 13.0 推荐构建顺序

按下面的顺序完成，每一步都通过 VS Code 官方 STM32 插件验证：

```text
CubeMX 生成空工程并编译
→ 加入 OLED/TB6612 驱动
→ 加入 BSP
→ 加入 TIM1 回调和 App
→ 在 CMakeLists 登记 User 文件
→ 编译、下载、验收 APP_DEMO_OBSERVE
```

应用层初始化时需要完成这些事情：

```c
HAL_ADCEx_Calibration_Start(&hadc1);
HAL_ADCEx_Calibration_Start(&hadc2);
HAL_TIM_Base_Start_IT(&htim1);
HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1);
HAL_TIM_Encoder_Start(&htim3, TIM_CHANNEL_ALL);
```

TIM1 的中断转发链必须保持为：

```text
TIM1_UP_IRQHandler
→ HAL_TIM_IRQHandler(&htim1)
→ HAL_TIM_PeriodElapsedCallback()
→ App_Tick1ms()
```

### 13.1 配套例程的源码边界

`E:\ProjectStm\倒立摆\User` 和 `E:\ProjectStm\倒立摆\Tests` 是本教程配套的版本化参考实现。新手不需要一次抄完所有文件：

- 第 00 章先使用 `app.c`、`bsp.c`、OLED 和 TB6612 的观察模式；
- 第 02～03 章再加入 PID 和调度；
- 第 05～09 章逐步加入单环、积分、微分、偏移和串级；
- 第 10～12 章再加入角度、平衡和起摆。

复制时只复制当前章节需要的 `User/` 文件；`Core/` 始终由 CubeMX 重新生成。进入第 02 章做第一个闭环实验前，至少需要复制：`control_types.h`、`pid.h`、`pid.c`，以及配套的 `app.c`（含速度环调度）和 `app_config.h`——第 02 章开头会再提醒一次。

### 13.2 文件创建顺序和函数清单

不要一次把十几个文件全部写出来。按下面顺序，每完成一层就编译或运行主机测试：

| 顺序 | 文件 | 必须先完成的函数/状态 |
|---:|---|---|
| 1 | `control_types.h`、`pid.h` | `pid_config_t`、`pid_t`、`pid_result_t` |
| 2 | `pid.c` | `pid_init`、`pid_reset`、`pid_prime`、`pid_step` |
| 3 | `cascade.h/.c` | `cascade_init`、`cascade_reset`、`cascade_step` |
| 4 | `balance.h/.c` | `balance_init`、`balance_reset`、`balance_angle_safe`、`balance_update` |
| 5 | `swingup.h/.c` | `swingup_init`、`swingup_reset`、`swingup_step`、`swingup_clear_fault` |
| 6 | `bsp.h/.c` | `BSP_Init`、角度两阶段读取、旋钮读取、编码器差值、电机和 UART |
| 7 | `app.h/.c` | `App_Init`、`App_Tick1ms`、`App_Process`、按键和模式切换 |
| 8 | TB6612/OLED 驱动 | 方向/PWM、GPIO 开漏软件 I²C 和显示函数 |

每层完成后检查：

```text
PID 层：不包含 stm32f1xx_hal.h，能用主机 GCC 编译
串级/平衡/起摆层：不访问 HAL 句柄
BSP 层：只做 HAL 适配，不放 PID 公式
App 层：独占控制器状态，按 TIM1 1 ms 调度
```

如果主机测试不能通过，先不要把它加入 CubeMX 工程；这样可以把算法错误和 HAL/生成代码错误分开。

### 13.3 第一次接入应用层

在 `main.c` 完成 `App_Init()` 和 `App_Process()` 后，先只使用：

```c
APP_DEMO_OBSERVE
```

复制章节快照时只复制源文件和 `User/`。不要复制旧的 `build/`、`CMakeCache.txt` 或调试缓存；换目录后由 VS Code 插件重新 Configure。确认 OLED、串口、ADC、编码器和按键，再逐步开启：

```text
OBSERVE
→ SPEED
→ POSITION
→ CASCADE
→ BALANCE
→ SWINGUP
```

不要第一次编译就选择 `APP_DEMO_SWINGUP`。

### 13.4 默认安全模式

`User/Inc/app_config.h` 中保留：

```c
#define APP_SELECTED_DEMO APP_DEMO_OBSERVE
```

第一次下载只能使用：

```text
APP_DEMO_OBSERVE
```

确认供电、OLED、ADC、编码器和按键后，才进入速度或平衡实验。

### 13.5 OLED 驱动的集成

本教程配套 OLED 驱动使用：

```text
PB8 = SCL
PB9 = SDA
7 位地址常见值 0x3C，驱动发送字节 0x78
```

它是软件 I²C，写入函数直接发送显示数据，没有独立的显存 `OLED_Update()` 步骤。不要把 `PB8/PB9` 误配置成硬件 I²C1 的默认 PB6/PB7。

### 13.6 TB6612 驱动

TB6612 只控制 A 路：

```text
AIN1 = PB12
AIN2 = PB13
PWMA = PA0/TIM2_CH1
```

课程逻辑方向：

| 命令 | PB12 | PB13 |
|---|---|---|
| 正 | Low | High |
| 负 | High | Low |
| 滑行 | Low | Low |

TB6612 的 `STBY` 在课程板上接 3.3 V，不是 MCU 软件控制脚。

---

## 14. 在 CMakeLists 中加入 User 代码和驱动

CubeMX 和 VS Code 官方 STM32 插件负责生成工具链、HAL 库入口和 `Core/` 源文件列表。你只需要在工程根目录的 `CMakeLists.txt` 中登记自己新增的 `User/` 源码和驱动目录。

```cmake
target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    User/Src/app.c
    User/Src/bsp.c
    User/Src/pid.c
    User/Src/cascade.c
    User/Src/balance.c
    User/Src/swingup.c
    User/Drivers/TB6612/tb6612.c
    User/Drivers/OLED/OLED.c
)

target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    User/Inc
    User/Drivers/TB6612
    User/Drivers/OLED
)
```

如果引入的是已经编译好的独立驱动库，再加入其头文件目录和库目标：

```cmake
target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    ThirdParty/SomeDriver/Inc
)
target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE SomeDriver)
```

如果驱动是源码形式，就用 `target_sources()` 加入源文件。不要修改 CubeMX 自动生成的 `cmake/stm32cubemx/CMakeLists.txt`。

`User/` 中的 `.c` 文件只登记一次。修改 CMakeLists 后，刷新 VS Code 的 CMake 工程即可。

---

## 15. 第一次编译、下载和调试

### 15.1 在 VS Code 中编译

1. 用 VS Code 打开 CubeMX 生成的工程根目录。
2. 打开 STM32 官方 VS Code 插件，让插件加载工程的 CMake 配置。
3. 在插件中选择 `Debug` 或 `Release` 配置。
4. 点击插件的 Build/编译按钮，等待编译输出完成。
5. 编译成功后，在插件的输出面板确认生成 `InvertedPendulum.elf`。

工具链、HAL 库、启动文件、链接脚本和 CMake 预设由 CubeMX 与 STM32 插件自动处理；教程不要求新手手动编写编译命令。

### 15.2 在 VS Code 中下载和调试

1. 只接 ST-LINK 的 SWDIO、SWCLK、GND 和目标参考电压；电机电源仍可保持断开。
2. 在 STM32 插件中选择 ST-LINK 和已经编译好的 `Debug`/`Release` 配置。
3. 使用插件的 Download/Flash 或 Debug 按钮下载程序。
4. 下载完成后执行复位，确认程序从 `main()` 开始运行。

00 硬件基准程序是 Keil 工程，可以使用 Keil 下载；HAL 工程使用 VS Code 官方 STM32 插件配合 CMake 完成编译、下载和调试，不要把两套工程文件混用。

### 15.3 下载前检查

下载前必须看到：

- [ ] 目标 MCU 是 STM32F103C8T6；
- [ ] 链接脚本容量是 64 KB Flash、20 KB RAM；
- [ ] `APP_SELECTED_DEMO` 是 `APP_DEMO_OBSERVE`；
- [ ] 电机方向脚初始化为 Low；
- [ ] TIM1 为 1 ms；
- [ ] ADC 时钟为 12 MHz；
- [ ] 电机电源未在首次下载时接通；
- [ ] BOOT0 为 0，使用 SWD 下载。

### 15.4 下载后的第一动作

下载、复位后只观察（OLED 共 4 行：第 1 行 `IP` + 状态、第 2 行模式与角度、第 3 行输出与目标、第 4 行位置）：

1. OLED 第 1 行是否显示 `IP` 和 `STOP`；
2. 串口是否出现 CSV；
3. 手动转动电机时第 4 行 `L:` 位置是否变化；
4. 改变 G1 时第 2 行角度码是否变化；
5. 电机是否保持停止。

任何一项异常都先回到本章对应外设排障，不要直接进入闭环。

---

## 16. 以 00 综合测试程序作为硬件基准

在开始 HAL 闭环前，使用用户已经验证过的 00 SPL 工程做一次硬件基准记录。00 根目录包含两个版本：

```text
D:\Elec\PID入门教程资料\程序源码\程序源码\程序源码-有注释版\00-PID综合测试程序\00-PID综合测试程序-V1.0
D:\Elec\PID入门教程资料\程序源码\程序源码\程序源码-有注释版\00-PID综合测试程序\00-PID综合测试程序-V1.1
```

本教程以 **V1.1** 为主，因为 V1.1 包含 `Menu.c`、`Mode0.c` 和 Flash 参数菜单。V1.0 的差异单独标出。

这份程序与 HAL 工程不是同一个工程，不能直接混编；但它可以在同一套硬件上提供以下对照：

- 同样的供电和接线；
- 同样的 OLED、按键、旋钮和电机/编码器观察；
- 同样的角度传感器原始码趋势；
- 同样的菜单调参入口；
- 同样的 4341 进入倒立摆流程。

### 16.1 4341 启动流程

V1.1 的实际流程是：

```text
复位/上电
  → K4：开机画面进入系统选择
  → K3：选择倒立摆 Mode3
  → K4：确认"请将设备置于倒立摆状态"
  → 进入 0x31 倒立摆界面
  → K1：启动自动启摆
```

K1 在倒立摆界面不是简单地"直接进入平衡 PID"。V1.1 会先进入起摆脉冲状态，等待固定时间，再进行摆角判断，最后才可能交给平衡控制。

再次按 K1 应能停止非零运行状态。由于 00 程序的模式状态机没有返回总选择页的常规路径，返回主选择通常需要复位设备；这是 00 程序的界面行为，不是 HAL 例程的要求。

### 16.2 00 V1.1 模式表

| 模式 | 功能 | 主要按键 |
|---|---|---|
| `0x01` | 系统选择 | K1 硬件、K2 电机、K3 倒立摆；K4 长按保存默认参数 |
| `0x11` | 按键测试 | K4 下一项 |
| `0x12` | 电位器测试 | K4 下一项 |
| `0x13` | 电机测试 | K1/K2 加减 PWM，K3 清零，K4 下一项 |
| `0x14` | 编码器测试 | 进入时清零，K4 下一项 |
| `0x15` | 角度传感器测试 | 显示 ADC 原始值，K4 下一项 |
| `0x16` | 串口测试 | K1/K2 改字节，K3 发送，K4 返回 |
| `0x20` | 电机控制选择 | K4 确认，K1 定速，K2 定位置 |
| `0x21` | 定速控制 | K1/K2/K3 调目标，K4 切换电位器调参 |
| `0x22` | 定位置控制 | K1/K2/K3 调目标，K4 切换电位器调参 |
| `0x30` | 倒立摆准备 | K4 确认 |
| `0x31` | 倒立摆控制 | K1 启停，K2/K3 调位置，K4 菜单/调参 |
| `0x32` | 参数菜单 | K1/K2 移动，K3 编辑，K4 返回 |

### 16.3 V1.1 默认参数

这些是空白 Flash 或编译初始化值；设备已有有效 Flash 时，实际值以 Flash 中保存的数据为准。

| 参数 | V1.1 编译默认 | 调节方式/范围 | 是否保存 |
|---|---:|---|---|
| 定速 `Kp/Ki/Kd` | `0.3 / 0.3 / 0` | RP1～RP3，各 0～3 | 长按 K4 保存 |
| 定速目标 | `0` | K1/K2 调整，通常 ±20，范围 ±100；K3 清零 | 不保存 |
| 定位置 `Kp/Ki/Kd` | `0.4 / 0.1 / 0.2` | RP1～RP3，各 0～3 | 长按 K4 保存 |
| 定位置目标 | `0` | K1/K2 调整 408，范围 ±816；K3 清零 | 不保存 |
| 角度内环 `Kp/Ki/Kd` | `0.25 / 0.009 / 0.41` | RP1 0～1、RP2 0～0.5、RP3 0～1 | 长按 K4 保存 |
| 倒立摆位置外环 `Kp/Ki/Kd` | `0.52 / 0.01 / 4.56` | RP1 0～5、RP2 0～1、RP3 0～10 | 长按 K4 保存 |
| 倒立摆目标位置 | `0` | K2 `+408`、K3 `-408`，范围 ±8999 | 不保存 |
| 中心值 | `2050` ADC 码 | 菜单 1900～2200，步长 10 | 是 |
| 启动力度 | `35` PWM | 菜单 0～100，步长 1 | 是 |
| 启动时间 | `90 ms` | 菜单 0～200，步长 1 | 是 |
| PWM 偏移 | `0` | 菜单 0～50，步长 1 | 是 |

这里的"中心值"是 12 位 ADC 原始计数，不是角度。

V1.1 的倒立摆捕获区间为 `1700～2300`，平衡状态在角度 `<1000` 或 `>3000` 时停止。这些是 00 程序的参数，不要直接替换 HAL 例程的 `2010/500`。

还有一个隐蔽的时序差异值得专门指出：V1.1 倒立摆的分频代码写的是 `Count2 > 5`、`Count1 > 50`，由于计到 6/51 才成立，**实际周期是 6 ms 和 51 ms**，和它自己的注释（5 ms/50 ms）差了一拍；而课程第 15、16 章的独立工程用 `Count1 >= 5`、`Count2 >= 50`，是精确的 5 ms/50 ms。V1.1 的角度内环 `0.25/0.009/0.41` 和位置外环 `0.52/0.01/4.56` 正是在 6 ms 采样下重新整定的，与 15/16 章的 `0.3/0.01/0.4`、`0.4/0/4.0` 不能互相替换——采样周期变了，离散 PID 参数必须重标。HAL 例程采用 15/16 章的精确 5 ms/50 ms 时序和对应参数。

### 16.4 V1.0 与 V1.1 的差异

V1.0 没有 V1.1 的 `Menu.c/Mode0.c` 菜单流程，倒立摆参数是固定宏：

```text
中心值       2050
启动力度     40
启动时间     90 ms
PWM 偏移     5
```

V1.1 改为：

```text
中心值       2050
启动力度     35
启动时间     90 ms
PWM 偏移     0
```

V1.0 只保存两环 PID 增益；V1.1 额外保存四个倒立摆菜单值。引用 00 的参数时必须写清版本。

### 16.5 00 的串口不是 CSV

V1.1 串口测试的实际行为是：

- K1：`TxData += 1`；
- K2：`TxData -= 1`，按 `uint8_t` 回绕；
- K3：发送一个原始 `uint8_t`；
- 接收：USART1 RXNE 中断每次接收一个原始字节并置单比特标志；
- OLED 上的 `TxData:%02X` 只是显示格式；
- 线上没有帧头、逗号、换行或 `Target,Actual,Out` 文本。

课程 01～13 示例和本 HAL 工程的 CSV 遥测是不同协议。对照 00 时要用串口工具的 HEX 接收；对照 HAL 时使用 ASCII/CSV，并记录模式、字段和换行。

### 16.6 Flash 参数区

00 V1.1 将参数放在 STM32F103C8 最后 1 KiB Flash：

```text
起始地址：0x0800FC00
大小：1024 bytes
半字 0：0xA5A5 有效标记
```

它没有版本号、CRC 或双备份。HAL 工程目前**没有实现 Flash 参数保存**，只使用编译期 `app_config.h` 和 RAM 中的 PID 状态。新手若以后增加保存功能，必须同时：

1. 在链接脚本中保留 `0x0800FC00～0x0800FFFF`；
2. 设计版本号和参数范围检查；
3. 擦除、写入和读取失败时保持旧参数或进入安全默认；
4. 不把 00 的 `Store.c` 直接复制到 HAL 工程。

### 16.7 00 与 01～16 的关系

00 不是 01～16 全部算法的简单合集：

- 00 集成了基础驱动、位置式 PID、积分分离、PID 结构体封装、角度传感器、角度—位置串级和自动起摆；
- 00 的倒立摆不是课程 12 的速度—位置串级，而是位置外环 → 角度内环；
- 增量式 PID、积分限幅、变速积分、微分先行、不完全微分和输入死区没有完整集成到 00 的通用 PID；
- 00 的硬件还包含 B 路电机/编码器和 TIM4，HAL 教学例程只实现 A 路，专注课程倒立摆主链路；
- 00 还读取了 PB1/ADC1_IN9 的第二路角度，HAL 教学例程只使用 PB0/ADC1_IN8 的 G1；除非要做双角度对照，不要把 PB1 当作本教程必配引脚。

因此，00 用作"硬件和菜单基准"，01～16 用作"算法递进教材"，HAL 工程用"同一实验链重新实现"。

建议先烧录 00 程序，记录串口、角度码、正负 PWM、编码器符号和 4341 流程，再烧录 HAL 的 `APP_DEMO_OBSERVE`。

如果 HAL 观测结果与 00 不一致，先查 CubeMX 引脚、时钟、ADC、编码器极性和电机方向，不要先修改 PID。

### 16.8 00 源码核对位置

| 事实 | 文件与行号 |
|---|---|
| 4341 流程 | `00-PID综合测试程序-V1.1\User\Mode0.c:19-65`、`Mode3.c:119-180` |
| 菜单参数 | `00-PID综合测试程序-V1.1\User\Menu.c:10-31`、`Mode3.c:20-56` |
| 倒立摆状态机 | `00-PID综合测试程序-V1.1\User\Mode3.c:423-568` |
| Flash 地址 | `00-PID综合测试程序-V1.1\System\Store.c:4-47` |
| 串口单字节行为 | `00-PID综合测试程序-V1.1\User\Mode1.c:194-238`、`Hardware\Serial.c:156-199` |
| 硬件驱动 | `00-PID综合测试程序-V1.1\Hardware\*.c` |

---

## 17. 新手常见错误

| 现象 | 根因 | 处理 |
|---|---|---|
| 电机上电动 | GPIO 初始电平或方向顺序错误 | PB12/PB13 先写 Low，再初始化 PWM |
| 编码器反向 | CH2 没有 Falling 或 EA/EB 相位相反 | 先改硬件极性/符号，不先改 Kp |
| 角度没有变化 | PB0、ADC1_IN8、ADC 校准或盲区 | 用观察模式读取原始码 |
| 旋钮值异常 | PA2～PA5 通道映射或 `BSP_ReadKnobs()` 读取顺序错误 | 逐个旋钮核对四个 ADC 原始值 |
| OLED 无显示 | PB8/PB9 开漏、外部上拉、地址、供电 | 逻辑分析仪测 SCL/SDA |
| 编译成功但下载后无串口 | USART1 未初始化或没有调用发送 | 检查 PA9/PA10、9600 8N1 和 `App_Process()` |
| CMake 找不到 User 源文件 | 根 `CMakeLists.txt` 没有登记新增文件 | 在 `target_sources()` 和 `target_include_directories()` 中加入 |
| 重新生成后控制代码消失 | 代码写在 CubeMX 自动区域外但未复制 | 把长期代码放 `User/`，小改动放 USER CODE 区 |

## 18. 本章验收记录

完成后填写：

```text
工程路径：
CubeMX 版本：
FW_F1 版本：
编译器版本：
Debug 构建结果：
Release 构建结果：
OLED 结果：
ADC1 G1 原始码范围：
ADC2 RP1～RP4 是否独立：
TIM1 实际周期：
TIM2 PWM 频率：
编码器正方向：
电机正方向：
串口 CSV：
00 程序版本：V1.0 / V1.1
00 4341 流程是否完成：
00 TX 是否确认是 HEX 单字节：
HAL 串口是否为 ASCII/CSV：
00 程序与 HAL 观察结果是否一致：
```

## 下一章

本章验收通过后，进入 [[01 平台接线与HAL工程]]，再按顺序完成后续章节。不要在工程底座还没有通过时直接调倒立摆 PID。
