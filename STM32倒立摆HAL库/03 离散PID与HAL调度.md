# 03 离散 PID 与 HAL 调度

## 本章问题

PID 公式放进 STM32 后，误差历史、积分状态和输出限幅应该按什么顺序更新？HAL 定时器如何提供固定控制周期？

> 前置：先完成 [[00 从零复刻HAL工程]]、[[01 平台接线与HAL工程]] 和 [[02 PID基本原理]]。本章的调度代码必须在 TIM1 回调中可编译。

## 1. 位置式与增量式

令：

$$
e_k=r_k-y_k
$$

位置式：

```text
e1 ← e0
e0 ← target - actual
I  ← I + e0
out = Kp*e0 + Ki*I + Kd*(e0-e1)
out = clamp(out, -100, 100)
```

增量式：

```text
e2 ← e1
e1 ← e0
e0 ← target - actual
out = out + Kp*(e0-e1) + Ki*e0
    + Kd*(e0 - 2*e1 + e2)
out = clamp(out, -100, 100)
```

无饱和、相同初值和相同误差序列时，两种公式可以得到相同结果；一旦输出限幅，增量式的 `out` 历史会改变后续行为。工程实现还会对位置式的 `I` 做限幅（默认 ±500）；积分分离和条件积分在两种形式下都有效，见第 06 章。

## 2. 本工程的 PID 核心

`User/Src/pid.c` 把以下状态放进 `pid_t`：

```c
integral
previous_error
previous_source
derivative_state
previous_d_term
output
initialized
```

`pid_step()` 的关键顺序是：

```text
计算误差
→ 死区闸门判断（|e| < 死区时直接输出 0 并冻结积分，闸门不改写误差）
→ 更新积分（含积分分离与条件积分）
→ 计算 P/I/D
→ 加输出偏移
→ 最终限幅
→ 保存历史
```

首次调用没有上一拍数据，D 项为 0；`pid_prime()` 可在已知当前反馈时预置历史。

本工程保留课程的离散系数约定：`integral` 是误差和，`D` 是每拍差分。这样可以直接阅读课程参数，但改变采样周期时必须重新确认 `Ki/Kd`。

## 3. HAL 固定节拍

TIM1 配置：

```text
TIM1CLK = 72 MHz
PSC = 71
ARR = 999
T = 72 MHz / (72 × 1000) = 1 ms
```

中断链：

```text
TIM1_UP_IRQHandler
    → HAL_TIM_IRQHandler(&htim1)
        → HAL_TIM_PeriodElapsedCallback()
            → App_Tick1ms()
```

`App_Tick1ms()` 负责编码器快照、按键扫描、角度采样和控制器分频。OLED、`snprintf` 和 `HAL_UART_Transmit()` 放在 `App_Process()` 主循环。

## 4. 周期表

| 任务 | 周期 | 代码 |
|---|---:|---|
| TIM1 调度 | 1 ms | `App_Tick1ms()` |
| 角度采样 | 5 ms | `APP_ANGLE_PERIOD_TICKS` |
| 速度/位置单环 | 40 ms | `APP_CONTROL_PERIOD_TICKS` |
| 平衡位置外环 | 50 ms | 采样拍计数每 10 次触发一次（`APP_POSITION_PERIOD_SAMPLES`） |
| 自动起摆极值判断 | 40 ms | `swingup.detect_period_ticks` |

角度 ADC 采用两阶段非阻塞读取：先调用 `BSP_StartAngleConversion()`，下一拍再调用 `BSP_ReadAngleIfReady()`。分频器每个 1 ms 拍都递增、与转换状态无关，所以启动加读取虽然跨两拍，采样周期仍是精确的 5 ms；平衡外环也用独立的采样拍计数分频，不受绝对节拍相位影响。控制 ISR 不等待 HAL tick。

连续两拍未完成就放弃本次样本并进入安全处理。旋钮 ADC 仍在主循环使用有限超时。

> 对应标准库教程的第 03 章："离散计算、状态更新和控制器复位"。HAL 版不重新生成外设工程，只观察 `User/Src/pid.c` 和 `User/Src/app.c` 的调用顺序。

## 新手操作卡

### 实验 3-1：先验证一拍的状态变化

1. 复制第 02 章的工程为 `03_DiscretePID`。
2. 保持 `APP_DEMO_OBSERVE`，先观察 `app_ticks`、`app_angle` 和串口 `state` 是否变化。
3. 在调试器中观察 `pid_t` 的 `previous_error`、`integral`、`output` 和 `initialized`。
4. 不修改参数，只调用或观察一次 `pid_step()`。

注意：`APP_DEMO_OBSERVE` 下调度器不会调用 `pid_step()`，这些状态会一直是 0。要观察真实状态变化，把模式切到 `APP_DEMO_SPEED` 并按 K1 启动，或在调试器里手动调用一次 `pid_step()`。

**预期**：第一次控制拍不会使用未初始化的上一拍 D 项；停止后再次启动前，积分和上一拍输出不会从旧实验残留。

### 实验 3-2：验证固定周期

1. 不改 PID，只观察 `App_Tick1ms()` 的计数关系。
2. 在调试器或日志中记录 1 ms 调度、5 ms 角度采样、40 ms 单环控制、50 ms 平衡外环的触发点。
3. 保持电机断开或使用 `APP_DEMO_OBSERVE`，不要用闭环结果猜周期。

**预期**：OLED/串口发送可以比控制拍慢，但控制拍不能被 OLED 或串口阻塞拖延。

### 实验 3-3：验证停止和重新启动

1. 在速度或位置模式启动控制器。
2. 按 K1 停止，确认 `command=0`、电机停止。
3. 改变目标后再次启动。
4. 对比启动瞬间的 `integral`、`previous_error` 和 `output`。

**通过标准**：第二次启动不能继承第一次实验的积分或输出；若不能，先检查 `pid_reset()`，不要先改增益。

## 5. 主机验收

```powershell
cd E:\ProjectStm\倒立摆
.\Tests\run_host_tests.ps1
```

测试覆盖：

| 主机测试 | 对应章节 | 通过现象 |
|---|---|---|
| `test_pid_proportional_and_incremental()` | 02、05 | 无饱和序列中位置式和增量式输出一致 |
| `test_pid_integral_features()` | 06 | 积分限幅、分离、变速积分状态符合预期 |
| `test_pid_derivative_and_deadband()` | 07、08 | 微分模式、滤波和死区行为符合配置 |
| `test_pid_output_offsets()` | 08 | 正、负输出偏移的符号和最终限幅正确 |
| `test_cascade()` | 09 | 外环输出先成为内环目标，状态彼此独立 |
| `test_balance_safety()` | 11 | 角度越界时输出立即归零 |
| `test_swingup()` | 12 | 停止、超时、故障和重新启动状态正确 |

主机测试只验证纯 C 控制核心，不证明电机、ADC 或 OLED 已经工作；硬件观测仍按第 04 章执行。

## 6. 排障与故障定位

| 现象 | 检查 |
|---|---|
| 首拍 D 很大 | 是否在第一拍就使用了未初始化的上一误差 |
| 停止后重新启动猛冲 | 是否调用 `pid_reset()` / `pid_prime()` |
| 速度一直为 0 | 40 ms 窗口是否在控制读取后清零 |
| 输出偶尔跳变 | ISR 与主循环是否同时改 PID 状态 |
| 改采样周期后响应异常（如把 5 ms 参数用到 40 ms） | `Ki/Kd` 是离散系数，周期变了必须重新标定 |

## 上一章 / 下一章

[[02 PID基本原理]] · [[04 基础驱动与观测实验]]
