# 03 基础驱动：CubeMX与HAL库实现

## 学习目标

- 区分 CubeMX 生成代码与用户驱动代码。
- 用 GPIO 和定时中断完成 LED 与按键实验。
- 用 ADC、PWM、编码器和串口接口完成独立实验。
- 将驱动接入唯一的主程序与定时回调。

## 1.  HAL 代码骨架

### 1.1 三份代码，三种归属

本章以 STM32F103C8T6、CubeMX 6.18.1、STM32Cube FW_F1 V1.8.7 为基准， `E:\ProjectStm\PIDproject\01 PID`为工程文件；代码分三层：

| 归属 | 位置 | 职责 |
| --- | --- | --- |
| CubeMX 生成层 | `gpio.c`、`tim.c`、`adc.c`、`usart.c` 等 | 时钟、引脚模式、外设参数、NVIC 与句柄 |
| 用户驱动层 | `led.c`、`key.c` 等及对应头文件 | 封装读写、外设启动与器件操作 |
| 应用层 | `main.c` 的 USER CODE 区 | 实验变量、初始化调用、主循环与定时回调 |

`MX_xxx_Init()` 通常完成外设配置；用户的 `XX_Init()` 是否还需启动硬件，要看具体驱动。例如 `Key_Init()` 是空函数，`LED_Init()` 只恢复默认电平，`Timer_Init()` 才会启动 TIM1。

**本章所有独立实验均保留 CubeMX 生成的唯一 `main()`，不整段覆盖它。** 当前 [main.c](E:/ProjectStm/PIDproject/01%20PID/Core/Src/main.c) 的注释区保存了多个旧测试 `int main()`

| 内容      | 放置位置                                              |
| ------- | ------------------------------------------------- |
| 驱动头文件   | `/* USER CODE BEGIN Includes */`                  |
| 文件作用域变量 | `/* USER CODE BEGIN PV */`                        |
| 用户初始化   | `/* USER CODE BEGIN 2 */`，在生成的 `MX_xxx_Init()` 之后 |
| 循环体     | 已有 `while (1)` 内的 `/* USER CODE BEGIN 3 */` 区     |
| 定时回调    | `/* USER CODE BEGIN 4 */`                         |


驱动头文件放在 `Core/Inc`，各自加入头文件保护和 `#include <stdint.h>`。以下是按文件分组的声明：

```c
/* led.h */
void LED_Init(void);
void LED_ON(void);
void LED_OFF(void);
void LED_Turn(void);

/* key.h */
void Key_Init(void);
uint8_t Key_GetNum(void);
uint8_t Key_GetState(void);
void Key_Tick(void);

/* timer.h */
void Timer_Init(void);

/* rp.h */
void RP_Init(void);
uint16_t RP_GetValue(uint8_t n);

/* pwm.h */
void PWM_Init(void);
void PWM_SetCompare1(uint16_t Compare);

/* motor.h */
void Motor_Init(void);
void Motor_SetPWM(int8_t PWM);

/* encoder.h */
void Encoder_Init(void);
int16_t Encoder_Get(void);

/* serial.h */
void Serial_Init(void);
void Serial_SendByte(uint8_t Byte);
void Serial_SendArray(uint8_t *Array, uint16_t Length);
void Serial_SendString(char *String);
uint32_t Serial_Pow(uint32_t X, uint32_t Y);
void Serial_SendNumber(uint32_t Number, uint8_t Length);
void Serial_Printf(char *format, ...);
uint8_t Serial_GetRxFlag(void);
uint8_t Serial_GetRxData(void);
```

例如 `key.h` 的完整外壳为：

```c
#ifndef KEY_H
#define KEY_H
#include <stdint.h>
void Key_Init(void);
uint8_t Key_GetNum(void);
uint8_t Key_GetState(void);
void Key_Tick(void);
#endif
```

OLED 保留现有 [oled.h](E:/ProjectStm/PIDproject/01%20PID/Core/Inc/oled.h) 的完整声明、字体宏及其 `oled_data.h` 依赖。

自建工程时，把用户 `.c` 登记进根目录 [CMakeLists.txt](E:/ProjectStm/PIDproject/01%20PID/CMakeLists.txt) 的现有 `target_sources`；头文件目录由 `target_include_directories` 提供。当前 PID 已登记以下源文件：
```cmake
target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    Core/Src/led.c
    Core/Src/key.c
    Core/Src/timer.c
    Core/Src/rp.c
    Core/Src/pwm.c
    Core/Src/motor.c
    Core/Src/encoder.c
    Core/Src/serial.c
    Core/Src/oled.c
    Core/Src/oled_data.c
)
target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE Core/Inc)
```

应用层在 `USER CODE BEGIN Includes` 中包含本次用到的驱动头文件即可

### 1.2 标准库与 HAL 的接口对照

| 要做的事       | 标准库写法                                                | HAL 写法                                                     |
| ---------- | ---------------------------------------------------- | ---------------------------------------------------------- |
| 开外设时钟      | `RCC_APB2PeriphClockCmd(..., ENABLE)`                | `__HAL_RCC_xxx_CLK_ENABLE()`                               |
| 配置 GPIO    | `GPIO_Init(GPIOC, &GPIO_InitStructure)`              | `HAL_GPIO_Init(GPIOC, &GPIO_InitStruct)`                   |
| 输出高/低电平    | `GPIO_SetBits` / `GPIO_ResetBits`                    | `HAL_GPIO_WritePin(端口, 引脚, GPIO_PIN_SET / GPIO_PIN_RESET)` |
| 读引脚电平      | `GPIO_ReadInputDataBit`                              | `HAL_GPIO_ReadPin(端口, 引脚)`                                 |
| 延时         | `Delay_ms(500)`                                      | `HAL_Delay(500)`                                           |
| 配定时器时基     | `TIM_TimeBaseInit(TIM1, &TIM_TimeBaseInitStructure)` | `HAL_TIM_Base_Init(&htim1)`                                |
| 开更新中断并启动   | `TIM_ITConfig(...)` + `TIM_Cmd(...)`                 | `HAL_TIM_Base_Start_IT(&htim1)`                            |
| 设 PWM 的比较值 | `TIM_SetCompare1(TIM2, Compare)`                     | `__HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, Compare)`    |
| 读写计数器      | `TIM_GetCounter` / `TIM_SetCounter`                  | `__HAL_TIM_GET_COUNTER` / `__HAL_TIM_SET_COUNTER`          |
| printf 输出  | 重定向 `fputc`（Keil）                                    | 驱动自封的 `Serial_Printf()`                                    |
| 配编码器接口     | `TIM_EncoderInterfaceConfig(...)`                    | `HAL_TIM_Encoder_Init(&htim3, &sConfig)`                   |

ADC 与串口的调用在后面各自的驱动里都有完整写法，这里不再逐行列举。

### 1.3 中断写法：从自己写 IRQHandler 到填回调函数

标准库版把中断服务函数写在：

```c
void TIM1_UP_IRQHandler(void)
{
	if (TIM_GetITStatus(TIM1, TIM_IT_Update) == SET)
	{
		//中断执行的代码
		TIM_ClearITPendingBit(TIM1, TIM_IT_Update);
	}
}
```

HAL 版由 CubeMX 在 `stm32f1xx_it.c` 生成 IRQ 入口，入口调用 HAL 处理函数，再进入用户回调。TIM1 更新进入 `HAL_TIM_PeriodElapsedCallback()`，USART1 接收完成进入 `HAL_UART_RxCpltCallback()`。HAL 负责检查中断标志与清除相应标志；用户回调仍须按 `Instance` 区分外设，再执行对应业务。

回调是 HAL 里预定义好的**弱函数**，`stm32f1xx_hal_tim.c` 里有一个空实现。用户在自己文件里写出同名函数，链接时会用用户的实现覆盖空版本。

### 1.4 本工程的引脚与外设总表

| 功能 | 引脚 | CubeMX 里的配置 |
| --- | --- | --- |
| 板载 LED | PC13 | GPIO_Output，推挽，低速，初始高电平 |
| 按键 K1 / K2 | PB10 / PB11 | GPIO_Input，上拉，按下为低 |
| 按键 K3 / K4 | PA11 / PA12 | GPIO_Input，上拉，按下为低 |
| 电位器 RP1~RP4 | PA2 / PA3 / PA4 / PA5 | ADC2_IN2~IN5，模拟输入 |
| 电机 PWM（PWMA） | PA0 | TIM2_CH1 |
| 电机方向 AIN1 / AIN2 | PB12 / PB13 | GPIO_Output，推挽，初始低电平 |
| 编码器 E1A / E1B | PA6 / PA7 | TIM3_CH1 / CH2，编码器接口 |
| 串口 USART1 | PA9 / PA10 | TX / RX，9600 8N1，开接收中断 |
| OLED | PB8 / PB9 | GPIO_Output，开漏，初始高电平（软件 I2C 的 SCL / SDA） |

时钟树：HSE 8 MHz 经 PLL ×9 得到 **SYSCLK = 72 MHz**；APB1 = 36 MHz（定时器时钟仍是 72 MHz），APB2 = 72 MHz；ADC 时钟取 PCLK2 的 6 分频 = **12 MHz**。

### 1.5 与入门教程共用驱动

本项目的原版基准是标准库 `01-基础驱动代码`；[[STM32HAL库入门教程/README|入门教程]]使用 `E:\ProjectStm\驱动库` 的宏定义版，默认配置相同；

与入门教程库逐项对照：LED、TIMER、RP、OLED 的默认引脚、外设配置和公开 API 一致；PWM/MOTOR 的默认引脚与外设配置一致，`Motor_SetPWM()` 的调用语义相同；KEY、ENCODER 采用单次采样与读后清零；SERIAL 采用 `vsprintf`、`uint8_t` 索引和无临界区。

## 2. 动手之前：套件状态、供电与下载

本节的测试面向电机控制状态，套件默认是倒立摆状态，先做一次机械变换：

1. 拔掉角度传感器的接头；
2. 用钳子拧掉最上面四个固定螺母；
3. 用内六角扳手**拧松**最下面两个顶丝（铜联轴器上的黑色顶丝，松即可，拧掉容易弄丢）；
4. 拿掉上面的倒立板部分，用手拧掉上面的四个铜柱，再把刚拧掉的四个螺母拧回铜柱螺纹上，用钳子轻轻紧一下；
5. 拿出转盘，先稍微松开它自带的两颗顶丝；把转盘插到电机输出轴上时，**让顶丝对准输出轴的切面**，再拧紧两颗顶丝，这样固定更牢、不容易打滑。

供电分两路，必须先理清再上电：

- **电机驱动电源 VM**：按套件说明使用 12 V 适配器与电源开关；12 V 不能直接接 STM32 或其他低压引脚。板内稳压路径、逻辑电源及其连接须按原理图或实物核对，不能仅凭外设源码推断。
- **STM32 供电**：若板上稳压器已经输出 3.3 V，不要再把 ST-Link 或 USB 转串口模块的 **3.3 V 电源输出**并联接入同一电源网。先按适配器标识确认端子用途：供电输出应断开，**目标电压参考输入 Vref/VTref 则用于检测目标电压，不能笼统要求拔掉**。不同 ST-Link 小板端子定义可能不同，不能只凭“最下面一根线”判断。
- 目标板、驱动板、下载器及串口模块保持共地；SWDIO/SWCLK 等调试信号按实际接口连接。调整机械结构或电机接线时先断电；电机初测保持低占空比，避免转盘碰撞。板上电源连接与 STBY 的实际状态均需结合实物确认（待实测）。

## 3. 板载 LED：最小的一次 GPIO 输出

### 3.1 引脚与配置

板载 LED 接在 **PC13**，低电平点亮。CubeMX 里把它配成 `GPIO_Output`：

| 配置项                  | 取值               | 作用               |
| -------------------- | ---------------- | ---------------- |
| GPIO output level    | High             | 上电默认熄灭           |
| GPIO mode            | Output Push Pull | 推挽输出，能直接拉低点亮 LED |
| Maximum output speed | Low              | LED 不需要翻转速度      |

### 3.2 驱动代码

`Core/Src/led.c` 里只留四件事，其他交给 CubeMX：

```c
#include "main.h"

/**
  * 函    数：LED初始化
  * 参    数：无
  * 返 回 值：无
  * 说    明：PC13的时钟和GPIO模式已由CubeMX在MX_GPIO_Init中配置好，
  *           此函数只负责设置引脚初始化后的默认电平
  */
void LED_Init(void)
{
	/*设置GPIO初始化后的默认电平*/
	HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
}

/**
  * 函    数：LED开启
  * 参    数：无
  * 返 回 值：无
  */
void LED_ON(void)
{
	HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
}

/**
  * 函    数：LED关闭
  * 参    数：无
  * 返 回 值：无
  */
void LED_OFF(void)
{
	HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
}

/**
  * 函    数：LED状态翻转
  * 参    数：无
  * 返 回 值：无
  */
void LED_Turn(void)
{
	if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) == GPIO_PIN_RESET)
	{
		HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
	}
	else
	{
		HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
	}
}
```
### 3.3 验证

在 `USER CODE BEGIN Includes` 包含 `led.h`，将下面两段放入生成的主程序，不添加新的 `main()`：

```c
/* USER CODE BEGIN 2：本次实验的用户初始化 */
LED_Init();

/* USER CODE BEGIN 3：已有 while (1) 的循环体 */
LED_ON();
HAL_Delay(500);
LED_OFF();
HAL_Delay(500);
LED_Turn();
HAL_Delay(500);
LED_Turn();
HAL_Delay(500);
```

编译下载后，PC13 的 LED 应每隔 500 ms 改变亮灭状态：亮、灭、翻转为亮、翻转为灭，闪烁周期 1 s。这个独立实验不启动 TIM1，也不需要定时回调或 OLED。

## 4. 按键：非阻塞式扫描

### 4.1 引脚与配置

四个按键都接成**上拉输入**，按下导通到地，所以按下时读到低电平。

| 按键 | 引脚 | 读到的电平 |
| --- | --- | --- |
| K1 | PB10 | 松开为高，按下为低 |
| K2 | PB11 | 同上 |
| K3 | PA11 | 同上 |
| K4 | PA12 | 同上 |

CubeMX 里四个引脚都设成 `GPIO_Input`，Pull-up/Pull-down 选 **Pull-up**。
### 4.2 驱动代码

按键需要把机械抖动与一次有效操作区分开。`Key_GetState()` 只读瞬时电平；按编号顺序返回第一个按下的键，多键同时按下不是本例的输入模型。`Key_Tick()` 每 1 ms 进入一次，每 20 次取样一次；本次为 0、上次非 0 时，把上次键码写入 `Key_Num`，即松手产生一次键码。

这是离散采样方案：不能保证两次采样之间毫无抖动，也会忽略很短的按压。`Key_GetNum()` 读取后清零，未加临界区；只允许一个主循环调用者。

```c
#include "main.h"
#include "key.h"

/*中断写、主循环读的单键码邮箱*/
uint8_t Key_Num;

/**
  * 函    数：按键初始化
  * 参    数：无
  * 返 回 值：无
  * 说    明：K1~K4的时钟和上拉输入模式已由CubeMX在MX_GPIO_Init中配置好，
  *           此函数无需再做配置，保留是为了让主程序的调用格式保持一致
  */
void Key_Init(void)
{

}

/**
  * 函    数：获取全局变量定义的按键键码
  * 参    数：无
  * 返 回 值：按键键码
  */
uint8_t Key_GetNum(void)
{
	uint8_t Temp;
	if (Key_Num)
	{
		Temp = Key_Num;
		Key_Num = 0;
		return Temp;
	}
	return 0;
}

/**
  * 函    数：获取按键状态
  * 参    数：无
  * 返 回 值：有按键按下，直接返回键码（非阻塞），没有按键按下，返回0
  */
uint8_t Key_GetState(void)
{
	if (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_10) == GPIO_PIN_RESET)
	{
		return 1;
	}
	if (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_11) == GPIO_PIN_RESET)
	{
		return 2;
	}
	if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_11) == GPIO_PIN_RESET)
	{
		return 3;
	}
	if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_12) == GPIO_PIN_RESET)
	{
		return 4;
	}
	return 0;
}

/**
  * 函    数：用于驱动按键模块运行的自定义按键定时中断函数
  * 参    数：无
  * 返 回 值：无
  * 注意事项：此函数必须在主程序中每隔1ms自动执行一次
  */
void Key_Tick(void)
{
	static uint8_t Count;
	static uint8_t CurrState, PrevState;

	Count ++;
	if (Count >= 20)
	{
		Count = 0;
		PrevState = CurrState;
		CurrState = Key_GetState();

		if (CurrState == 0 && PrevState != 0)
		{
			Key_Num = PrevState;
		}
	}
}
```

`Key_Init()` 保留空实现，因为 GPIO 已由 `MX_GPIO_Init()` 配置。`Key_Num` 是中断写、主循环读的单键码邮箱；`Key_GetNum()` 读取后清零。读清不是原子操作，未加临界区，只允许一个主循环调用者；邮箱只存一个键码，主循环来不及取时新键码会覆盖旧值，并非事件队列。

### 4.3 验证

包含 `key.h`、`timer.h`、`oled.h`。本实验与第 5.4 节的纯计时实验二选一；使用第 5.3 节的 `TickMs` 变量和唯一 TIM1 回调，另加以下片段：

```c
/* USER CODE BEGIN PV */
int32_t j = 0;

/* USER CODE BEGIN 2 */
OLED_Init();
Key_Init();
Timer_Init();                     //依赖准备好后才开 TIM1 中断

/* USER CODE BEGIN 3 */
switch (Key_GetNum())
{
case 1: ++j; break;
case 2: --j; break;
case 3: j += 10; break;
case 4: j -= 10; break;
default: break;
}
uint32_t ticks = TickMs;           //对齐的 32 位单次读取
OLED_Printf(0, 0, OLED_8X16, "i:%10lu", (unsigned long)ticks);
OLED_Printf(0, 16, OLED_8X16, "j:%+10ld", (long)j);
OLED_Update();
HAL_Delay(10);
```

编译下载后，`i` 每毫秒自增（屏幕只在刷新时显示最新快照）；分别按下并松开 K1～K4，`j` 应加 1、减 1、加 10、减 10。按住不连发；一次按下并松开只产生一次键码。`j` 用有符号类型，初值 0 时减 1 应显示 -1，而不是无符号回绕。

## 5. 1 ms 时基：TIM1 更新中断

### 5.1 为什么是 TIM1

这块芯片（STM32F103C8T6）有 TIM1～TIM4 四个定时器。本工程用 TIM2 输出电机 PWM、TIM3 做编码器、TIM1 提供 1 ms 按键节拍；与 [[02 PID离散化与程序实现]] 集成时，TIM4 专门提供 10 ms PID 周期，不把两种节拍混用。当前 `.ioc` 尚未启用 TIM4。

### 5.2 配置与定时时间计算

在 CubeMX 的 Timers 里勾选 TIM1：

| 配置项                                  | 取值             |
| ------------------------------------ | -------------- |
| Clock Source                         | Internal Clock |
| Prescaler (PSC - 16 bits value)      | 72 - 1 = 71    |
| Counter Period (AutoReload Register) | 1000 - 1 = 999 |
| NVIC → TIM1 update interrupt         | 勾选             |
| Preemption Priority                  | 2              |

定时时间按"分频后计满一轮"算：

$$
T=\frac{(PSC+1)\times(ARR+1)}{f_{TIM}}=\frac{72\times1000}{72\,\mathrm{MHz}}=1\,\mathrm{ms}
$$

`f_TIM` 是定时器时钟。TIM1 挂在 APB2 上，APB2 分频系数为 1，所以定时器时钟就等于 72 MHz

### 5.3 驱动代码与中断回调

驱动的 `Core/Src/timer.c` 只剩启动一句：

```c
#include "main.h"
#include "tim.h"

/**
  * 函    数：定时中断初始化
  * 参    数：无
  * 返 回 值：无
  * 说    明：TIM1的时基单元（PSC=72-1，ARR=1000-1）和更新中断已在CubeMX中配置好，
  *           此函数只需启动更新中断即可
  */
void Timer_Init(void)
{
	HAL_TIM_Base_Start_IT(&htim1);
}
```

`htim1` 由 CubeMX 在 `tim.c` 定义、在 `tim.h` 声明，因此驱动包含 `tim.h`。不要把定时回调写进 `timer.c` 后又在 `main.c` 定义一遍。

下面是本章独立按键、时基、电机实验共用的版本，只在 `main.c` 放一份；编码器实验按第 8.4 节替换它，PID 集成时按第 11 节合并分支：

```c
/* USER CODE BEGIN PV */
volatile uint32_t TickMs = 0;      //TIM1 写，主循环只读

/* USER CODE BEGIN 4 */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
	if (htim->Instance == TIM1)
	{
		++TickMs;
		Key_Tick();                 //1 ms 扫描入口，内部再分频取样
	}
}
```

在 `USER CODE BEGIN Includes` 包含 `key.h` 和 `timer.h`。回调按 `Instance` 分支，因为所有定时器共用此出口；硬件更新标志由 HAL 处理，用户仍需区分外设实例。

### 5.4 验证

使用第 5.3 节的变量及回调，包含 `oled.h`，用下面片段替换按键实验的初始化和循环体：

```c
/* USER CODE BEGIN 2 */
OLED_Init();
Key_Init();
Timer_Init();

/* USER CODE BEGIN 3 */
uint32_t ticks = TickMs;
OLED_Printf(0, 0, OLED_8X16, "ms:%10lu", (unsigned long)ticks);
OLED_Update();
HAL_Delay(20);
```

下载后用秒表观察两个显示值的差：10 s 应约增长 10000，而不是每刷新一次才加 1。`TickMs` 是 32 位无符号计数，约 49.7 天回绕一次；它用于观察节拍，不要在主循环读后清零，否则会与中断自增竞争。预期数值不等于已测得的定时精度（待实测）。

## 6. 电位器：ADC2 单次转换

### 6.1 通道与为什么用 ADC2

板上四个电位器接在 PA2～PA5，对应 ADC2 的通道 2～5。课程将 ADC1 预留给后续角度传感器的 DMA 采样，电位器则用 ADC2 轮询；当前基础工程尚未配置该 ADC1 采样链路。

| 电位器 | 引脚 | ADC2 通道 |
| --- | --- | --- |
| RP1 | PA2 | ADC2_IN2 |
| RP2 | PA3 | ADC2_IN3 |
| RP3 | PA4 | ADC2_IN4 |
| RP4 | PA5 | ADC2_IN5 |

### 6.2 配置

在 STM32F1 的 CubeMX 页面启用 ADC2 的 `IN2`～`IN5`，引脚成为模拟输入。本系列不使用其他系列界面的 `INx Single-ended` 或异步 ADC 时钟名称；以 F1 配置和生成代码为准：

| 配置项                                | 取值                                      | 原因                                                                                         |
| ---------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------ |
| Scan Conversion Mode               | Disabled                                | 不扫描，一次只转一个通道                                                                               |
| Continuous Conversion Mode         | Disabled                                | 转完就停，由软件触发下一次                                                                              |
| Number Of Conversion               | 1                                       | 规则组里只有一个位置，读哪个通道就临时配哪个                                                                     |
| External Trigger Conversion Source | Regular Conversion launched by software | 用 `HAL_ADC_Start()` 触发                                                                     |
| Rank → Sampling Time               | 保持默认 1.5 Cycles                         | CubeMX 里不动；真正的加长由驱动在每次转换前指定                                                                |
| ADC 时钟（Clock Configuration）     | APB2 peripheral clock divided by 6     | `RCC_ADCPCLK2_DIV6`，ADCCLK = 72 MHz / 6 = 12 MHz，不超过 F1 的 14 MHz 上限 |
| NVIC                               | 不勾选                                     | 用轮询读结果，不需要中断                                                                               |

驱动里实际生效的是 `55.5` 拍，一次转换的总时间就是"采样时间 + 转换时间"：

$$
t_{conv}=\frac{55.5+12.5}{12\,\mathrm{MHz}}\approx5.7\,\mu\mathrm{s}
$$

其中 12.5 个周期是 F1 ADC 的固定转换时间。约 5.7 μs 只含硬件采样与转换，不含 HAL 调用和通道重配开销。输入电压必须在 **VSSA～VDDA** 内，本板通常为 0～3.3 V；模拟输入不能接 5 V 或负电压。电位器两端接 VDDA 对应的低压电源与地，滑动端才接 ADC 引脚。

### 6.3 驱动代码

```c
#include "main.h"
#include "adc.h"

/**
  * 函    数：电位器旋钮初始化
  * 参    数：无
  * 返 回 值：无
  * 说    明：ADC2的时钟、引脚和基本参数已在CubeMX中配置好，
  *           此函数只需执行一次ADC校准
  */
void RP_Init(void)
{
	HAL_ADCEx_Calibration_Start(&hadc2);
}

/**
  * 函    数：获取电位器旋钮的AD值
  * 参    数：n 指定电位器旋钮，范围：1~4，分别表示RP1、RP2、RP3、RP4
  * 返 回 值：AD转换的值，范围：0~4095
  */
uint16_t RP_GetValue(uint8_t n)
{
	ADC_ChannelConfTypeDef sConfig = {0};

	if (n == 1)
	{
		/*配置规则组为通道2（PA2）*/
		sConfig.Channel = ADC_CHANNEL_2;
	}
	else if (n == 2)
	{
		/*配置规则组为通道3（PA3）*/
		sConfig.Channel = ADC_CHANNEL_3;
	}
	else if (n == 3)
	{
		/*配置规则组为通道4（PA4）*/
		sConfig.Channel = ADC_CHANNEL_4;
	}
	else if (n == 4)
	{
		/*配置规则组为通道5（PA5）*/
		sConfig.Channel = ADC_CHANNEL_5;
	}
	sConfig.Rank = ADC_REGULAR_RANK_1;
	sConfig.SamplingTime = ADC_SAMPLETIME_55CYCLES_5;  //采样时间
	HAL_ADC_ConfigChannel(&hadc2, &sConfig);

	HAL_ADC_Start(&hadc2);
	HAL_ADC_PollForConversion(&hadc2, HAL_MAX_DELAY);  //等待EOC标志位，即等待AD转换结束
	return HAL_ADC_GetValue(&hadc2);
}
```

四个要点：

- **校准只做一次**，放在 `RP_Init()` 里。它必须在 ADC 没在转换时执行。
- **采样时间在驱动里显式指定。** 当前生成代码是 `1.5 Cycles`，本驱动每次改为 `ADC_SAMPLETIME_55CYCLES_5`，让采样电容有更长充电时间；是否足够仍取决于信号源阻抗，不能笼统说所有电位器用 1.5 拍都会明显偏小。
- **每次转换前都要重配通道。** 规则组只有一个位置；调用者只传 `n=1～4`，其他值不在此 API 的合法范围，不能当作读取“默认通道”的办法。
- **轮询只放主循环。** `HAL_ADC_PollForConversion(..., HAL_MAX_DELAY)` 是阻塞等待，不能从 TIM1 或 TIM4 回调调用；本例假定外设已正确配置且转换正常，不把无限等待当作实时控制的保障。

### 6.4 验证

包含 `rp.h`、`oled.h`，不启动 TIM1，无定时回调：

```c
/* USER CODE BEGIN 2 */
OLED_Init();
RP_Init();

/* USER CODE BEGIN 3 */
OLED_Printf(0, 0, OLED_8X16, "RP1:%04u", (unsigned)RP_GetValue(1));
OLED_Printf(0, 16, OLED_8X16, "RP2:%04u", (unsigned)RP_GetValue(2));
OLED_Printf(0, 32, OLED_8X16, "RP3:%04u", (unsigned)RP_GetValue(3));
OLED_Printf(0, 48, OLED_8X16, "RP4:%04u", (unsigned)RP_GetValue(4));
OLED_Update();
HAL_Delay(20);
```

编译下载后依次旋转 RP1～RP4，对应显示值应随之变化，接近两端时分别接近 0 和 4095；它是 12 位原始码，不是电压。理想换算为 $V_{in}\approx AD\times VDDA/4095$，VDDA 取实际供电值。

## 7. 电机：TIM2 通道 1 的 PWM 与 TB6612

### 7.1 三个控制脚与供电

TB6612 是双路 H 桥，一路电机由下面三根信号线控制，此外还有必须有效的公共使能 STBY：

| 信号 | 引脚 | 作用 |
| --- | --- | --- |
| PWMA | PA0（TIM2_CH1） | 频率固定，用占空比调速 |
| AIN1 | PB12 | 方向控制 |
| AIN2 | PB13 | 方向控制 |

AIN1/AIN2 确定输出极性，PWMA 的高电平占比决定驱动时间比例，但**停驱动、滑行和短刹车不是同一件事**。正常工作要求 VCC 逻辑供电、VM 电机供电、共地且 **STBY 为高**；STBY 为低时进入待机，输出高阻。本工程没有 STBY GPIO，需按板上接线或原理图确认并使能，不能凭源码断言它已被拉高。不要将 STBY 接到 12 V。

| STBY | AIN1/AIN2 | PWMA | 含义 |
| --- | --- | --- | --- |
| 低 | 任意 | 任意 | 待机，输出高阻 |
| 高 | 低/高 | 高 | 本程序定义的正方向 |
| 高 | 高/低 | 高 | 本程序定义的负方向 |
| 高 | 低/低 | 高 | 停止驱动，输出高阻，电机可惯性滑行 |
| 高 | 高/高 | 任意 | 短刹车，两输出同为低电平 |
| 高 | 任意 | 低 | 短刹车状态，不等于转轴瞬时停止 |

本驱动 `Motor_SetPWM(0)` 令 PWMA 恒低，方向仍按非负分支设为低/高，属于上述低 PWM 状态，不是显式高阻滑行 API。实际减速受惯量、负载等影响，**PWM=0 不会保证瞬停，也不能替代安全断电**。反转实验应先降到零并等待转盘停稳，再逐步给反向小占空比。

VM 由 12 V 适配器经电源开关供给；它与逻辑 VCC 是不同电源。这里给出的是开环电压驱动比例，不直接设定转速或保证力矩。

### 7.2 配置与 PWM 频率

PA0 在 CubeMX 里点成 `TIM2_CH1`，通道模式选 `PWM Generation CH1`：

| 配置项            | 取值           | 说明                   |
| -------------- | ------------ | -------------------- |
| Prescaler      | 36 - 1 = 35  | 分频到 2 MHz            |
| Counter Period | 100 - 1 = 99 | 计数 100 个 → 20 kHz    |
| PWM Mode       | PWM mode 1   | 计数值小于 CCR 时输出有效电平    |
| Pulse (CCR1)   | 0            | 上电占空比为 0             |
| GPIO Speed     | 保持默认 Low     | 20 kHz 的翻转速度在低速档绰绰有余 |
| NVIC           | 不勾选          | 输出 PWM 不需要中断         |

频率计算：

$$
f_{PWM}=\frac{f_{TIM}}{(PSC+1)\times(ARR+1)}=\frac{72\,\mathrm{MHz}}{36\times100}=20\,\mathrm{kHz}
$$

20 kHz 位于人耳听觉上限附近，通常有助于减小 PWM 可闻噪声，但并不保证电机完全无声。占空比为：

$$
\mathrm{Duty}=\frac{CCR}{ARR+1}=\frac{CCR}{100}
$$

所以 CCR 直接取 0~100 就正好对应 0%~100%，驱动函数里不必再做换算。

### 7.3 驱动代码

底层只负责"改 CCR"，上层负责"方向 + 速度"，分成两个文件：

```c
/*pwm.c：只做PWM输出*/
#include "main.h"
#include "tim.h"

/**
  * 函    数：PWM初始化
  * 参    数：无
  * 返 回 值：无
  * 说    明：TIM2的时基单元（PSC=36-1，ARR=100-1）和通道1的输出比较模式
  *           已在CubeMX中配置好，此函数只需启动通道1，让PWM开始输出
  */
void PWM_Init(void)
{
	HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1);
}

/**
  * 函    数：PWM设置CCR
  * 参    数：Compare 要写入的CCR的值，范围：0~100
  * 返 回 值：无
  * 注意事项：CCR和ARR共同决定占空比，此函数仅设置CCR的值，并不直接是占空比
  *           占空比Duty = CCR / (ARR + 1)
  */
void PWM_SetCompare1(uint16_t Compare)
{
	__HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, Compare);
}
```

```c
/*motor.c：方向引脚 + 调用底层PWM*/
#include "main.h"
#include "pwm.h"

/**
  * 函    数：直流电机初始化
  * 参    数：无
  * 返 回 值：无
  * 说    明：方向控制引脚PB12和PB13已在CubeMX中配置为推挽输出，
  *           此处将两个方向引脚置低，再启动PWM；初始CCR=0并不代表高阻滑行
  */
void Motor_Init(void)
{
	HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12 | GPIO_PIN_13, GPIO_PIN_RESET);

	PWM_Init();
}

/**
  * 函    数：直流电机设置PWM
  * 参    数：PWM，范围：-100~100；正值IN1=0/IN2=1，负值相反
  *           正负仅是软件方向约定，实际转向取决于电机接线与观察方向
  * 返 回 值：无
  */
void Motor_SetPWM(int8_t PWM)
{
	if (PWM >= 0)
	{
		HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);
		HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, GPIO_PIN_SET);
		PWM_SetCompare1(PWM);
	}
	else
	{
		HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
		HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, GPIO_PIN_RESET);
		PWM_SetCompare1(-PWM);
	}
}
```

函数名用 `Motor_SetPWM()` 而不是 `Motor_SetSpeed()`，是因为这里给的是**开环的占空比**。

### 7.4 验证与方向调整

包含 `motor.h`、`key.h`、`timer.h`、`oled.h`，用第 5.3 节的唯一 TIM1 回调；本实验不使用 TIM4。先确认 STBY 有效且机械部分可安全转动，再放入：

```c
/* USER CODE BEGIN PV */
int16_t PWM = 0;

/* USER CODE BEGIN 2 */
OLED_Init();
Key_Init();
Motor_Init();                     //内部已经调用 PWM_Init，不要再启动一次
Timer_Init();

/* USER CODE BEGIN 3 */
uint8_t key = Key_GetNum();
if (key == 1) { PWM += 10; }
if (key == 2) { PWM -= 10; }
if (PWM > 100) { PWM = 100; }
if (PWM < -100) { PWM = -100; }
if (key == 3) { PWM = 0; }
Motor_SetPWM((int8_t)PWM);
OLED_Printf(0, 0, OLED_8X16, "PWM:%+04d", (int)PWM);
OLED_Update();
HAL_Delay(10);
```

编译下载后，初值为零；K1 松手加 10、K2 松手减 10，限幅到 -100～100；K3 松手把命令归零，转盘随后减速而非保证立刻停住。初测只给小占空比，零附近未必能克服静摩擦，不要把这一点误读成占空比等于速度。

转向与约定相反时，**二选一改一处**，不要两处同时改：

- 改软件：把 `Motor_SetPWM()` 里两组 `SET`/`RESET` 的引脚对调；
- 改硬件：把接电机的两根线对调。


## 8. 编码器：TIM3 编码器接口

### 8.1 正交编码为什么数到 408

电机尾部是霍尔编码器，它把**转子的机械角度**变成 A、B 两路方波。两路相差 90°：转一个方向时 A 超前 B，反方向时 B 超前 A——硬件靠这个相位关系就能判断方向，不需要软件去猜。这类输出叫**正交信号**。

STM32 编码器接口选择 **Encoder Mode TI1 and TI2** 后，会对 A、B 两相的上升沿和下降沿计数，即一个信号周期计 4 次。按课程电机参数，每相每电机轴圈产生 11 个信号周期，四倍频后为 44 计数，再乘减速比得到输出轴一圈的计数：

$$
44\times9.2767\approx408
$$

其中 $44=11\times4$，9.2767 是课程电机的减速比，因此输出轴一圈约 408 计数（待实测）。四倍频不是软件换算出来的结果，而是 8.2 节把接口选成 TI1 and TI2 后由硬件完成计数。更换电机后，应按其编码器分辨率、计数模式与减速比重新确定换算系数。

### 8.2 配置

| 配置项                     | 取值                       | 说明                  |
| ----------------------- | ------------------------ | ------------------- |
| Combined Channels       | Encoder Mode             | 一次占用 CH1、CH2 两路     |
| Encoder Mode            | Encoder Mode TI1 and TI2 | A、B 两个边沿都计数，四倍频     |
| Channel1 → Polarity     | Rising Edge              | 不反相                 |
| Channel1 → Input Filter | 15                       | 最大滤波，抑制电机换向的毛刺      |
| Channel2 → Polarity     | Falling Edge             | 反相，以此校正方向           |
| Channel2 → Input Filter | 15                       | 同上                  |
| Counter Period          | 65535                    | 计数范围最大，一次读取能覆盖的增量更宽 |
| Prescaler               | 0                        | 编码器计数不分频            |


### 8.3 驱动代码

以下恢复为标准库原版/入门教程库的读后清零写法。`Encoder_Init()` 只启动 TIM3 编码器接口；`Encoder_Get()` 读取 CNT 后立即清零，返回上次调用以来的增量。读与清不是原子操作，窗口内到来的边沿可能丢失；只允许一个周期性调用者，高速连续测速时应改用自由计数＋模差。

```c
#include "main.h"
#include "tim.h"
#include "encoder.h"

/**
  * 函    数：编码器初始化
  * 参    数：无
  * 返 回 值：无
  * 说    明：TIM3的编码器接口已在CubeMX中配置好，此函数只负责启动
  */
void Encoder_Init(void)
{
	HAL_TIM_Encoder_Start(&htim3, TIM_CHANNEL_ALL);
}

/**
  * 函    数：获取编码器的增量值
  * 参    数：无
  * 返 回 值：自上此调用此函数后，编码器的增量值
  */
int16_t Encoder_Get(void)
{
	/*使用Temp变量作为中继，目的是返回CNT后将其清零*/
	int16_t Temp;
	Temp = (int16_t)__HAL_TIM_GET_COUNTER(&htim3);
	__HAL_TIM_SET_COUNTER(&htim3, 0);
	return Temp;
}
```

`Encoder_Init()` 必须在 `MX_TIM3_Init()` 之后调用。这里的 `htim3` 是固定引脚版的句柄，等价于教程库的 `ENCODER_HANDLE`。

`Encoder_Get()` 返回增量，不是绝对位置；累加增量得到相对位置，固定周期的增量可换算速度。40 ms 读取一次时，`delta/408.0/0.04` 的单位为转/秒；10 ms PID 周期则应除以 0.01，不能沿用 0.04。

### 8.4 验证与方向调整

包含 `encoder.h`、`key.h`、`timer.h`、`oled.h`。电机不供驱动命令，手动转动输出轴；用下列版本**替换**第 5.3 节的变量和回调，不同时保留两份：

```c
/* USER CODE BEGIN PV */
volatile int16_t Speed = 0;        //单位：计数/40 ms，并非转/秒
volatile int32_t Location = 0;     //本次短时实验的累计计数

/* USER CODE BEGIN 2 */
OLED_Init();
Key_Init();
Encoder_Init();
Timer_Init();

/* USER CODE BEGIN 3 */
uint32_t primask = __get_PRIMASK();
__disable_irq();
int16_t speed = Speed;
int32_t location = Location;       //两项取同一采样周期的快照
__set_PRIMASK(primask);
OLED_Printf(0, 0, OLED_8X16, "Speed:%+06d", (int)speed);
OLED_Printf(0, 16, OLED_8X16, "Loc:%+11ld", (long)location);
OLED_Update();
HAL_Delay(20);

/* USER CODE BEGIN 4：唯一的定时回调 */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
	if (htim->Instance == TIM1)
	{
		Key_Tick();
		static uint8_t Count;
		if (++Count >= 40)
		{
			Count = 0;
			int16_t delta = Encoder_Get(); //唯一调用者
			Speed = delta;
			Location += delta;
		}
	}
}
```

编译下载后，手动正反转输出轴，`Speed` 应呈相反符号；停稳后增量应接近零，`Location` 保留累计位置。同一方向转一整圈，位置差应约为 408（待实测），这不是要求显示值每次恰好等于 408。`Location` 用 32 位有符号量，仅用于不溢出的短时实验。

电机“正命令”的实际转向应与编码器正增量统一。若方向相反，只交换 A/B 相、调整某一路极性或在增量处取反中的一项；不能同时改多处抵消。本工程现有 IC2 反相是配置事实，不代表任意接线都会得到正确反馈符号。

## 9. 串口：USART1 收发与 printf

### 9.1 接线与参数

| 配置项 | 取值 |
| --- | --- |
| 波特率 | 9600 |
| 字长 | 8 位 |
| 停止位 | 1 位 |
| 校验 | 无 |
| 硬件流控 | 无 |

使用 **3.3 V TTL 电平** USB 转串口模块：模块 TX → PA10（RX）、模块 RX → PA9（TX）、GND → GND。这里目标板独立供电，模块 VCC 不接，避免并联供电；不能把 RS-232 的正负电压信号直接接到 MCU。

### 9.2 配置

在 Connectivity 里勾 USART1，Mode 选 `Asynchronous`，参数照上表填，然后在 NVIC Settings 里勾 **USART1 global interrupt**，抢占优先级给 0。参考工程的 `PID.ioc` 与 `usart.c` 已把波特率改为 9600。

### 9.3 驱动代码

下面各代码块共同组成 `serial.c`。按标准库原版恢复：接收使用单字节邮箱，`Serial_Printf()` 用 `vsprintf()`，字符串索引用 `uint8_t`，`Serial_GetRxFlag()` 读取后直接清零，不加临界区。原版的 `fputc()` 是 Keil 的 `printf` 重定向，本工程用 CMake/GCC，不移植它，统一调用 `Serial_Printf()`。

```c
#include "main.h"
#include "usart.h"
#include "serial.h"
#include <stdio.h>
#include <stdarg.h>

uint8_t Serial_RxData;        /*接收的数据*/
uint8_t Serial_RxFlag;        /*接收标志位*/
```

初始化只开启一次单字节接收，接收交给中断，避免主循环被等数据卡住：

```c
/**
  * 函    数：串口初始化
  * 参    数：无
  * 返 回 值：无
  * 说    明：USART1的参数（9600、8位字长、1位停止位、无校验）和引脚
  *           已在CubeMX中配置好，此函数只需开启接收中断
  */
void Serial_Init(void)
{
	HAL_UART_Receive_IT(&huart1, &Serial_RxData, 1);
}

/**
  * 函    数：串口接收完成回调函数
  * 参    数：huart 触发中断的串口
  * 返 回 值：无
  * 注意事项：此函数为中断回调函数，无需调用，接收完成后自动执行
  */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
	if (huart->Instance == USART1)
	{
		Serial_RxFlag = 1;
		HAL_UART_Receive_IT(&huart1, &Serial_RxData, 1);
	}
}
```

`HAL_UART_Receive_IT()` 每次只接收指定长度；本例一字节完成后必须重新挂接。`HAL_UART_RxCpltCallback()` 只在 `serial.c` 定义一份，不复制到 `main.c`。邮箱只存一个字节，主循环未取时新数据会覆盖旧值；重新挂接有间隙，连续高速输入还可能丢字节，原版没有实现错误恢复。

发送采用阻塞式 API，适合主循环中的低速观察与打印，不在 TIM1/TIM4 或串口接收回调里发送：

```c
/**
  * 函    数：串口发送一个字节
  * 参    数：Byte 要发送的一个字节
  * 返 回 值：无
  */
void Serial_SendByte(uint8_t Byte)
{
	HAL_UART_Transmit(&huart1, &Byte, 1, HAL_MAX_DELAY);
}

/**
  * 函    数：串口发送一个数组
  * 参    数：Array 要发送数组的首地址
  * 参    数：Length 要发送数组的长度
  * 返 回 值：无
  */
void Serial_SendArray(uint8_t *Array, uint16_t Length)
{
	uint16_t i;
	for (i = 0; i < Length; i ++)
	{
		Serial_SendByte(Array[i]);
	}
}

/**
  * 函    数：串口发送一个字符串
  * 参    数：String 要发送字符串的首地址
  * 返 回 值：无
  */
void Serial_SendString(char *String)
{
	uint8_t i;
	for (i = 0; String[i] != '\0'; i ++)
	{
		Serial_SendByte(String[i]);
	}
}
```

`Serial_SendString()` 接受以 `\0` 结尾的有效字符串，索引用 `uint8_t`，与标准库原版一致；超过 255 个字符会在索引处回绕，长字符串应自行分段。数字发送仍用内部次方函数取位；`Length=0` 不输出，1～10 输出固定宽度，不足补零、超宽保留低位。`Serial_Printf()` 用 `vsprintf()` 写入 100 字节缓冲区：

```c
/**
  * 函    数：次方函数（内部使用）
  * 返 回 值：返回值等于X的Y次方
  */
uint32_t Serial_Pow(uint32_t X, uint32_t Y)
{
	uint32_t Result = 1;
	while (Y --)
	{
		Result *= X;
	}
	return Result;
}

/**
  * 函    数：串口发送数字
  * 参    数：Number 要发送的数字，范围：0~4294967295
  * 参    数：Length 要发送数字的长度，范围：0~10
  * 返 回 值：无
  */
void Serial_SendNumber(uint32_t Number, uint8_t Length)
{
	uint8_t i;
	for (i = 0; i < Length; i ++)
	{
		Serial_SendByte(Number / Serial_Pow(10, Length - i - 1) % 10 + '0');
	}
}

/**
  * 函    数：自己封装的printf函数
  * 参    数：format 格式化字符串
  * 参    数：... 可变的参数列表
  * 返 回 值：无
  */
void Serial_Printf(char *format, ...)
{
	char String[100];
	va_list arg;
	va_start(arg, format);
	vsprintf(String, format, arg);
	va_end(arg);
	Serial_SendString(String);
}
```

100 字节缓冲区没有长度保护，格式字符串仍须与参数类型匹配；与标准库原版一致。超长输出可能越界，调试时控制行长，不能把这段当成安全格式化。

接收侧的 `Serial_GetRxFlag()` 读取并清除标志，`Serial_GetRxData()` 只读数据、不清数据。两个函数都不加临界区，与标准库原版一致。查标志和取数据是两次独立调用，中间若来新字节，`Serial_GetRxData()` 可能读到新数据；低速调试可接受，连续高速接收需自行加保护或改用 DMA。

```c
/**
  * 函    数：获取串口接收标志位
  * 返 回 值：串口接收标志位，范围：0~1，接收到数据后，标志位置1，读取后标志位自动清零
  */
uint8_t Serial_GetRxFlag(void)
{
	if (Serial_RxFlag == 1)
	{
		Serial_RxFlag = 0;
		return 1;
	}
	return 0;
}

/**
  * 函    数：获取串口接收的数据
  * 返 回 值：接收的数据，范围：0~255
  */
uint8_t Serial_GetRxData(void)
{
	return Serial_RxData;
}
```

`Serial_GetRxFlag()` 先判断再清零，`Serial_GetRxData()` 只返回邮箱当前值；两者都不保护“查标志＋取数据”的组合操作。邮箱只存一个字节，读取前可能已被新数据覆盖，这不是接收队列。

### 9.4 验证

**四路电位器发送实验**：包含 `rp.h`、`serial.h`、`oled.h`，不启动 TIM1，无定时回调。用以下片段替换生成主程序中的用户初始化和循环体：

```c
/* USER CODE BEGIN 2 */
OLED_Init();
RP_Init();
Serial_Init();

/* USER CODE BEGIN 3 */
uint16_t r1 = RP_GetValue(1), r2 = RP_GetValue(2);
uint16_t r3 = RP_GetValue(3), r4 = RP_GetValue(4);
OLED_Printf(0, 0, OLED_8X16, "RP1:%04u", (unsigned)r1);
OLED_Printf(0, 16, OLED_8X16, "RP2:%04u", (unsigned)r2);
OLED_Printf(0, 32, OLED_8X16, "RP3:%04u", (unsigned)r3);
OLED_Printf(0, 48, OLED_8X16, "RP4:%04u", (unsigned)r4);
OLED_Update();
Serial_Printf("%u,%u,%u,%u\r\n", (unsigned)r1, (unsigned)r2,
              (unsigned)r3, (unsigned)r4);
HAL_Delay(10);
```

串口助手设置 9600、8N1、文本接收，应持续显示四个 0～4095 的十进制数，例如 `1234,2345,3456,4000`，行尾为 CR LF。依次转动四个旋钮，对应列变化。SerialPlot 设四通道、逗号分隔和 `\r\n` 行结束即可画四条曲线。循环周期是 ADC、显示、发送时间再加 10 ms，不是严格 10 ms。

**单字节接收回显实验**：与上面的发送实验二选一，只包含 `serial.h`，不启动 OLED、ADC 或 TIM1。`USER CODE BEGIN 2` 仅调用 `Serial_Init()`，循环体为：

```c
/* USER CODE BEGIN 3 */
uint8_t data = 0;
if (Serial_GetRxFlag())
{
	data = Serial_GetRxData();
	Serial_SendByte(data);
}
```

关闭串口助手本地回显和自动附加换行，手动低速发送一个 ASCII `A`（字节 `0x41`），应收到一个 `A`；若发送字节 `0x01`，返回的是该原始字节而不是文本 `"01"`，需用 HEX 模式观察。该实验只验证低速单字节链路，不表示连续数据流不会丢失。

## 10. OLED：软件 I2C 驱动的移植

### 10.1 为什么是软件 I2C

0.96 寸 OLED 的四针为 VCC、GND、SCL、SDA，板上 SCL 接 **PB8**、SDA 接 **PB9**。STM32F103 的这两个脚**可以作为 I2C1 重映射后的硬件引脚**；本工程未启用 I2C1，而主动选用 GPIO 软件模拟 I2C，并不是因为引脚不支持硬件 I2C。

CubeMX 把 PB8/PB9 配为 `GPIO_Output`、`Output Open Drain`、初始 `High`。开漏写 0 主动拉低，写 1 只是释放线路，**高电平必须靠上拉电阻形成**；确认 OLED 模块已有上拉，或外接上拉至兼容的 3.3 V 电源，不能只设置初始 High 就当作线路会变高。当前生成 GPIO 为 `GPIO_NOPULL`，不提供内部上拉。模块供电及其上拉电压应与 STM32 接口兼容。

### 10.2 验证

包含 `oled.h`，保留软件 OLED 驱动及字库文件的 CMake 登记。下面整个显示片段放在 `USER CODE BEGIN 2`，已有 `while (1)` 留空即可，不添加新的 `main()`，也不启动 TIM1：

```c
/* USER CODE BEGIN 2 */
OLED_Init();
OLED_ShowString(0, 0, "Hello, STM32!", OLED_8X16);
OLED_ShowFloatNum(0, 16, 12.345, 2, 3, OLED_8X16);
OLED_Printf(0, 32, OLED_8X16, "Num=%d", 666);
OLED_Update();
```

编译下载后，三行应分别显示 `Hello, STM32!`、`+12.345`、`Num=666`。原工程的 `"Hello,世界。"` 测试保留其教学含义，但依赖 `oled_data.c` 中 `OLED_CF16x16` 及匹配的编码字模，不能把任意 UTF-8 中文字符串当作通用字体；上面 ASCII 例不需要额外取中文字模。

- 显示函数先修改 MCU 内存中的显存，`OLED_Update()` 才传到屏幕；整屏刷新有耗时，放主循环或初始化，不放进 TIM1/TIM4 回调。
- 使用本工程像素坐标版 OLED API（如 `X=0,Y=16`），不要与其他教程的行列坐标版直接混用。现有 `OLED_Printf()` 使用有限缓冲区和 `vsprintf`；串口现已同样采用原版 `vsprintf`，两者都不做长度保护，不能把任一处当成安全格式化。

## 11. 主程序：把 8 个驱动拼成一个工程

### 11.1 初始化顺序

CubeMX 生成的 `main()` 已经安排好外设初始化顺序：

```c
HAL_Init();  //HAL 库与系统滴答
SystemClock_Config();  //时钟树：72MHz
MX_GPIO_Init();
MX_TIM2_Init();  //电机PWM
MX_ADC2_Init();  //电位器
MX_USART1_UART_Init();
MX_TIM3_Init();  //编码器
MX_TIM1_Init();  //1ms时基
```

用户初始化放在 `USER CODE BEGIN 2`，只初始化本次实际使用的功能。顺序由依赖决定：

- GPIO/外设生成初始化在对应驱动操作前；`RP_Init()` 校准在开始读取前，`OLED_Init()` 在显示前，`Serial_Init()` 在中断接收前。
- `Motor_Init()` 已调用 `PWM_Init()`，不要重复启动；`Key_Init()` 是空函数，LED 的 GPIO 在生成代码中已经可用，并非所有驱动都必须额外 Init 才能调用。
- OLED 没有“必须第一个”的硬件要求。中断启动则应放在依赖变量和驱动准备好之后；TIM4 闭环启动前先确认电机/编码器方向、控制状态与零输出。

例如第 9.4 节发送实验只需：

```c
/* USER CODE BEGIN 2 */
RP_Init();
Serial_Init();
OLED_Init();
```

这里 OLED 放最后同样成立。不会使用电机/编码器/定时中断的实验，不必为“统一格式”启动它们。

### 11.2 主循环、中断回调与各自的边界

| 放在哪 | 该放什么 | 不该放什么 |
| --- | --- | --- |
| 主循环 | ADC 轮询、读取按键事件、显示、低速阻塞发送 | 再次读取被控制中断独占的编码器增量 |
| TIM1，1 ms | `Key_Tick()`、短计时/分频 | ADC 轮询、OLED 更新、延时或阻塞发送 |
| TIM4，10 ms | 选定的一套 PID 采样、计算与输出 | 再扫描一遍按键或运行另一套编码器实验 |
| USART1 接收回调 | 发布单字节、置标志、重新挂接 | 显示、打印、长时间解析 |

本章允许主循环中的短阻塞调用；不能笼统说“主循环不等待、中断只置标志”。关键是阻塞业务不占用定时回调，PID 的短采样/计算/输出在预算内完成；实际最坏执行时间与中断抢占仍待实测。

与 [[02 PID离散化与程序实现]] 集成时，统一采用以下约定：**TIM1=1 ms 按键节拍，TIM4=10 ms PID，`main.c` 只有一份 `HAL_TIM_PeriodElapsedCallback()`，按 `Instance` 分支；USART 回调仍留在 `serial.c`。** 第 02 篇的位置式与增量式 PID 二选一，将所选 TIM4 分支的业务语句并入同一个回调，不再复制一个回调定义：

```c
/* USER CODE BEGIN 4：集成位置示意，不是另一份可叠加的回调 */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
	if (htim->Instance == TIM1)
	{
		Key_Tick();
	}
	else if (htim->Instance == TIM4)
	{
		/* 将02选定PID版本的采样→计算→限幅→Motor_SetPWM语句放在这里。
		   Encoder_Get()只由该分支调用一次，主循环只显示保存的快照。 */
	}
}
```

这段只展示合并位置，空的 TIM4 分支不构成闭环控制程序。集成时删除第 8.4 节 TIM1 内的 40 ms 编码器测试，不能一边运行编码器实验一边让 PID 再取一次增量。保持 `Encoder_Get()` 单一调用者；读后清零窗口内的边沿可能丢失，高速连续测速时改用自由计数＋模差。

TIM4 配置沿用第 02 篇：Internal Clock、PSC=7199、ARR=99，APB1 定时器时钟 72 MHz 时周期为 $7200\times100/72\,\mathrm{MHz}=10\,\mathrm{ms}$；启用 `TIM4 global interrupt`。让 CubeMX 生成 `htim4`、`MX_TIM4_Init()` 及 IRQ→HAL 入口，生成的外设初始化完成后，在 `USER CODE BEGIN 2` 中、控制状态准备好后调用 `HAL_TIM_Base_Start_IT(&htim4)`。不要只手写启动语句却漏掉配置和 NVIC。

**TIM4 是第 02 篇要求新增的教学配置，当前 PID 的 `.ioc`、`tim.c` 和生成主程序尚未启用它。** 本章已把参考工程的串口波特率改为 9600（`PID.ioc`、`usart.c` 与 `main.c` 注释），并把编码器返回值改为显式 `int16_t` 转换；未编译；以上 STM32F103C8T6 / CubeMX 6.18.1 / F1 V1.8.7 的 LED、按键、ADC、PWM、编码器、串口和 OLED 现象，以及供电、STBY、方向、消抖效果与实时性，均待硬件实测。

---

上一篇：[[02 PID离散化与程序实现]]
