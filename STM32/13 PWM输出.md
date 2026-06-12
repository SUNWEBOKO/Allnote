# 13. PWM 输出：从原理到 CubeMX 配置与呼吸灯

> 本节重点：理解 PWM 的频率和占空比如何由定时器的 PSC、ARR、CCR 决定，掌握从 CubeMX 配置到 HAL 代码实现呼吸灯的完整流程。

---

## 本节核心问题

学完本节，需要能回答：

- PWM 的频率和占空比分别由什么决定？
- 为什么没有 DAC 也能通过 PWM 实现"近似模拟输出"？
- 定时器的 `CNT`、`ARR`、`CCR` 在 PWM 生成中各起什么作用？
- PWM 模式 1 下，改变输出极性（Polarity）对波形有什么影响？
- 呼吸灯代码中为什么需要两个方向的 `for` 循环？

---

## 1. PWM 基本概念

PWM（Pulse Width Modulation，脉冲宽度调制）本质是**固定频率下的高低电平切换**。

### 1.1 关键参数

| 参数 | 含义 | 公式 |
|------|------|------|
| 周期 `T` | 一个完整高低电平循环的时间 | `T = 1 / f` |
| 频率 `f` | 每秒循环次数 | `f = 1 / T` |
| 占空比 `D` | 高电平时间占周期的比例 | `D = Ton / T` |

### 1.2 等效模拟量输出

对于 LED、电机等有惯性/积分效应的负载，PWM 可呈现宏观等效电压：

$$
V_{avg} \approx V_{high} \times D
$$

示例（`V_high = 3.3V`）：

| 占空比 | 等效电压 | 视觉效果 |
|--------|----------|----------|
| 50% | 约 1.65V | 中等亮度 |
| 10% | 约 0.33V | 低亮度 |
| 90% | 约 2.97V | 高亮度 |

---

## 2. 为什么使用 PWM

STM32F103C8T6 有 ADC（可采样模拟量）但没有 DAC（不能直接输出连续模拟电压）。PWM 成为**数字方式近似模拟输出**的主要手段。

常见用途：

- LED 亮度调节（呼吸灯）
- 电机调速
- 舵机角度控制
- 蜂鸣器发声

---

## 3. 定时器生成 PWM 的原理

### 3.1 核心寄存器

| 寄存器 | 作用 |
|--------|------|
| `CNT` | 计数器当前值 |
| `ARR` | 自动重装载值，决定计数上限（影响频率） |
| `CCR` | 比较值，决定占空比 |

定时器持续计数，并不断比较 `CNT` 和 `CCR`，输出引脚电平按规则切换。

### 3.2 PWM 模式 1 + 上计数 + 高极性

```text
CNT < CCR   → 输出有效电平（高电平）
CNT >= CCR  → 输出无效电平（低电平）
```

注意：有效/无效电平由极性（Polarity）决定。修改极性后波形会反相。

### 3.3 频率与占空比公式

$$
f_{pwm} = \frac{f_{tim}}{(PSC + 1) \times (ARR + 1)}
$$

$$
Duty = \frac{CCR}{ARR + 1} \quad (\text{PWM1, 上计数, 高有效})
$$

---

## 4. CubeMX 配置（视频示例）

### 4.1 时钟配置

系统主频 72MHz，以此给 TIM3 配置 PWM。

### 4.2 定时器与通道选择

| 配置项 | 设置值 |
|--------|--------|
| 定时器 | TIM3 |
| 时钟源 | `Internal Clock` |
| Channel 1 | `PWM Generation CH1` |
| 输出引脚 | PA6 (TIM3_CH1) |

### 4.3 定时器基准参数

| 参数 | 值 | 含义 |
|------|----|------|
| `PSC` | 71 | 72 分频 |
| `ARR` | 99 | 计数 0~99，共 100 个计数 |
| `Counter Mode` | Up | 上计数模式 |

```text
f_pwm = 72,000,000 / (72 × 100) = 10,000 Hz
T_pwm = 1 / 10,000 = 0.1 ms
```

### 4.4 PWM 通道参数

| 参数 | 值 | 说明 |
|------|----|------|
| `PWM Mode` | Mode 1 | — |
| `Pulse (CCR)` | 50 | 初始占空比 50% |
| `Polarity` | High | 高有效 |
| `Fast Mode` | Disable | 高频场景可按需启用 |
| 比较预装载 | Enable | 避免周期中途改值影响当前周期 |

```text
Duty = 50 / (99 + 1) = 50%
```

### 4.5 GPIO 模式

PWM 输出引脚自动配置为**复用推挽输出**（AF Push-Pull）。

---

## 5. HAL 代码实现

### 5.1 启动 PWM

```c
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
```

### 5.2 运行时修改占空比

```c
__HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, compare);
```

- `compare` 范围：`0 ~ ARR`（本例 0~99）
- 值越大，占空比越大（PWM1 + 上计数 + 高有效条件下）

### 5.3 呼吸灯完整代码

```c
/* USER CODE BEGIN 2 */
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
/* USER CODE END 2 */

/* USER CODE BEGIN WHILE */
while (1)
{
    for (int i = 0; i < 100; i++)
    {
        __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, i);
        HAL_Delay(10);
    }

    for (int i = 99; i >= 0; i--)
    {
        __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, i);
        HAL_Delay(10);
    }
}
/* USER CODE END WHILE */
```

实现逻辑：第一段渐亮（CCR 递增），第二段渐暗（CCR 递减），循环往复。

---

## 6. 高频易错点

1. **波形无输出**。未调用 `HAL_TIM_PWM_Start` / 通道引脚不对应 / GPIO 不是复用推挽输出。

2. **频率算错**。忘记复核 `f_tim` 的来源（注意 APB 定时器倍频规则）。

3. **占空比调不动或有毛刺**。改错了 CCR 通道 / 预装载未开启导致中途突变。

4. **亮度变化看不出来**。每步 `HAL_Delay` 太短或步长太大，降低变化速度。

5. **极性搞反**。修改 Polarity 后波形反相，占空比表现与预期相反。

---

## 7. 一页速记

### 核心公式
```text
f_pwm = f_tim / ((PSC + 1) × (ARR + 1))
Duty  = CCR / (ARR + 1)      (PWM1, 上计数, 高有效)
```

### 本例参数
```text
72MHz → PSC=71 → ARR=99 → 10kHz
CCR=50 → Duty ≈ 50%
```

### 核心 API
| 函数 | 用途 |
|------|------|
| `HAL_TIM_PWM_Start(tim, channel)` | 启动 PWM 输出 |
| `__HAL_TIM_SET_COMPARE(tim, ch, val)` | 修改占空比 |

### 与输入捕获的关系
```text
输入捕获：读外部脉冲宽度（测时间）
PWM 输出：按设定输出脉冲宽度（生成时间）
两者依赖同一套比较机制，方向相反
```

### 最重要的一句话
> 频率看 `PSC + ARR`，占空比看 `CCR`，启动靠 `PWM_Start`。

---

## 8. 自测题

1. PWM 的周期和占空比分别由定时器的哪些参数决定？
2. 为什么 STM32F103C8T6 需要用 PWM 来模拟模拟输出？
3. PWM 模式 1、上计数、高极性下，CCR 增大时占空比增大还是减小？为什么？
4. 如果修改 Polarity 为 Low，波形会怎么变化？
5. 呼吸灯代码中，为什么渐亮和渐暗要各用一个 `for` 循环？
6. 如果 `PSC = 71`、`ARR = 199`、`f_tim = 72MHz`，PWM 频率是多少？

---
