# 遥控小车 STM32F103C8T6 项目整体计划

## 1. 项目目标

本项目计划制作一辆基于 `STM32F103C8T6` 的遥控小车模型，底盘结构为两个驱动电机加两个万向轮。车辆通过蓝牙接收遥控指令，使用两个直流减速电机完成前进、后退和差速转向；通过编码器 T 法测速实现左右轮速度闭环；通过 `MPU6050` 读取姿态数据，并用互补滤波得到姿态角或短时航向估计；最终采用“角度环输出转向补偿，左右速度环分别跟踪”的控制结构。

当前已有驱动库：

```text
E:\ProjectStm\驱动库\D153C
E:\ProjectStm\驱动库\MPU6050
E:\ProjectStm\驱动库\PID
E:\ProjectStm\驱动库\OLED
E:\ProjectStm\驱动库\蓝牙串口通信
```

本计划以这些驱动库的实际接口和默认外设映射为基础，不重新设计一套和库冲突的引脚方案。

## 2. 总体控制思路

两驱加万向轮的小车更适合采用差速控制。建议不要把“速度环 PID”和“角度环 PID”简单并联后直接输出到两个电机，而是采用更稳定的级联加差速分配结构：

```text
蓝牙指令
   |
   v
目标速度 target_speed
目标航向 target_yaw 或目标转向 target_turn
   |
   v
角度/航向环 PID -> turn_comp
   |
   v
left_target_speed  = target_speed - turn_comp
right_target_speed = target_speed + turn_comp
   |
   v
左轮速度 PID -> left_pwm
右轮速度 PID -> right_pwm
   |
   v
D153C 电机驱动
```

这个结构里，角度环不直接控制电机 PWM，而是生成左右轮的速度差。左右轮速度环再根据实际编码器测速结果输出最终 PWM。这样做的好处是调参逻辑清楚，车体直行、转向、抗扰动都更容易控制。

需要注意的是，`MPU6050` 没有磁力计，因此 `yaw` 只能依靠 `gyro_z` 积分，长期一定会漂移。项目初期建议把角度环理解为短时间航向保持或转向修正，不要把它当成长期绝对朝向控制。

## 3. 已有驱动库接口结论

### 3.1 D153C 电机驱动

电机库文件：

```text
E:\ProjectStm\驱动库\D153C\d153c_motor.c
E:\ProjectStm\驱动库\D153C\d153c_motor.h
```

默认映射：

```c
#define D153C_A_IN1_PORT   GPIOB
#define D153C_A_IN1_PIN    GPIO_PIN_12
#define D153C_A_IN2_PORT   GPIOB
#define D153C_A_IN2_PIN    GPIO_PIN_13
#define D153C_A_PWM_TIM    (&htim3)
#define D153C_A_PWM_CH     TIM_CHANNEL_1

#define D153C_B_IN1_PORT   GPIOB
#define D153C_B_IN1_PIN    GPIO_PIN_14
#define D153C_B_IN2_PORT   GPIOB
#define D153C_B_IN2_PIN    GPIO_PIN_15
#define D153C_B_PWM_TIM    (&htim3)
#define D153C_B_PWM_CH     TIM_CHANNEL_2
```

主要接口：

```c
void d153c_motor_init(void);
void d153c_motor_drive(int id, int16_t duty);
void d153c_motor_coast(int id);
void d153c_motor_brake(int id);
void d153c_motor_invert(int id, bool inv);
int16_t d153c_motor_duty(int id);
```

`d153c_motor_drive()` 的输入范围为 `-1000..1000`。正负号表示方向，绝对值表示占空比大小。库内部会根据 `TIMx->ARR` 自动换算比较值，因此 CubeMX 中 PWM 的 `ARR` 不必固定为 `999`，只要频率合适即可。

### 3.2 D153C T 法测速

T 法测速库文件：

```text
E:\ProjectStm\驱动库\D153C\d153c_speed_t.c
E:\ProjectStm\驱动库\D153C\d153c_speed_t.h
```

默认映射：

```c
#define D153C_T_A_IC_TIM              (&htim2)
#define D153C_T_A_IC_CH               TIM_CHANNEL_1

#define D153C_T_B_IC_TIM              (&htim4)
#define D153C_T_B_IC_CH               TIM_CHANNEL_1
```

主要接口：

```c
void d153c_speed_t_init(void);
void d153c_speed_t_capture_callback(TIM_HandleTypeDef *htim);
void d153c_speed_t_update_timeout(uint32_t timeout_ms);

float d153c_speed_t_rps(int id);
float d153c_speed_t_rpm(int id);
uint32_t d153c_speed_t_period_us(int id);
bool d153c_speed_t_valid(int id);
```

这个 T 法测速库的关键点是：`TIM2_CH1` 和 `TIM4_CH1` 只作为输入捕获边沿触发源，真实周期计算使用 `DWT->CYCCNT` 生成的微秒时间戳。也就是说，`TIM2/TIM4` 的计数周期不是测速精度核心，但必须能稳定产生输入捕获中断。

默认编码器参数：

```c
#define D153C_PPR                  13.0f
#define D153C_REDUCTION            30.0f
#define D153C_T_EDGE_MULTIPLE      1.0f
```

如果你的电机编码器参数不是 `13PPR`、减速比不是 `30`，需要修改这里，否则速度值会整体不准。

### 3.3 MPU6050

MPU6050 库文件：

```text
E:\ProjectStm\驱动库\MPU6050\mpu6050.c
E:\ProjectStm\驱动库\MPU6050\mpu6050.h
```

主要接口：

```c
MPU6050_Status MPU6050_Init(I2C_HandleTypeDef *hi2c);
MPU6050_Status MPU6050_ReadData(MPU6050_Data *data);
```

数据结构：

```c
typedef struct
{
  float ax_g;
  float ay_g;
  float az_g;
  float temperature_c;
  float gx_dps;
  float gy_dps;
  float gz_dps;
} MPU6050_Data;
```

库默认初始化为：

```text
加速度量程：±4g
陀螺仪量程：±500 dps
采样率相关配置：SMPLRT_DIV = 0x09
低通滤波配置：CONFIG = 0x03
```

### 3.4 OLED

OLED 库文件：

```text
E:\ProjectStm\驱动库\OLED\oled.c
E:\ProjectStm\驱动库\OLED\oled.h
```

主要接口：

```c
void OLED_Init(void *hi2c);
void OLED_NewFrame(void);
void OLED_ShowFrame(void);
void OLED_Printf(uint8_t x, uint8_t y, OLED_ColorMode color, const char *fmt, ...);
```

OLED 驱动使用硬件 I2C，设备地址为 `0x78`。它采用先写显存再整帧刷新的方式，`OLED_ShowFrame()` 会进行较多 I2C 阻塞传输，因此不要放在中断里执行。

### 3.5 蓝牙串口通信

蓝牙库文件：

```text
E:\ProjectStm\驱动库\蓝牙串口通信\bluetooth_serial.c
E:\ProjectStm\驱动库\蓝牙串口通信\bluetooth_serial.h
```

主要接口：

```c
void BluetoothSerial_Init(UART_HandleTypeDef *huart);
void BluetoothSerial_SendString(const char *string);
void BluetoothSerial_Printf(const char *format, ...);
void BluetoothSerial_OnUartRxCplt(UART_HandleTypeDef *huart);
```

接收数据包格式：

```text
[内容]
```

例如：

```text
[F]
[B]
[L]
[R]
[S]
[V:1.2,T:0.3]
```

库中已经定义了 `HAL_UART_RxCpltCallback()`，因此工程中不要在其他文件重复定义同名 UART 回调，否则会出现链接冲突。若后续还有其他串口设备，需要统一改造回调分发。

### 3.6 PID

PID 库文件：

```text
E:\ProjectStm\驱动库\PID\pid.c
E:\ProjectStm\驱动库\PID\pid.h
```

主要接口：

```c
void PID_Init(PID_t *pid, float kp, float ki, float kd, float out_min, float out_max);
void PID_Reset(PID_t *pid);
float PID_UpdateValue(PID_t *pid, float target, float actual);
```

这是位置式 PID：

```text
Out(k) = Kp * e(k) + Ki * Σe(i) - Kd * [Actual(k) - Actual(k-1)]
```

速度环输出建议限幅为 `-1000..1000`，可以直接接入 `d153c_motor_drive()`。

## 4. CubeMX 配置计划

### 4.1 芯片与基础设置

芯片型号：

```text
STM32F103C8T6
```

基础配置：

```text
SYS -> Debug: Serial Wire
RCC -> HSE: Crystal/Ceramic Resonator
SYSCLK: 72 MHz
APB1: 36 MHz
APB2: 72 MHz
```

如果你的开发板没有外部晶振，则使用 HSI 也可以先跑通，但时间精度和串口稳定性会差一些。常见 Blue Pill / 最小系统板一般有 8MHz HSE。

### 4.2 引脚与外设总表

建议最终资源分配：

```text
PA0   -> TIM2_CH1    左轮 T 法测速输入
PA6   -> TIM3_CH1    左电机 PWM
PA7   -> TIM3_CH2    右电机 PWM
PA9   -> USART1_TX   蓝牙 TX
PA10  -> USART1_RX   蓝牙 RX

PB6   -> TIM4_CH1    右轮 T 法测速输入
PB10  -> I2C2_SCL    MPU6050 + OLED
PB11  -> I2C2_SDA    MPU6050 + OLED
PB12  -> GPIO_Output 左电机 IN1
PB13  -> GPIO_Output 左电机 IN2
PB14  -> GPIO_Output 右电机 IN1
PB15  -> GPIO_Output 右电机 IN2

TIM1  -> Base Timer  1ms 系统调度
```

重要原因：`TIM4_CH1` 默认在 `PB6`，而 `I2C1_SCL` 也默认在 `PB6`。为了避免冲突，MPU6050 和 OLED 建议共用 `I2C2`，即 `PB10/PB11`。

### 4.3 TIM3 电机 PWM

CubeMX 中打开：

```text
TIM3 -> Clock Source: Internal Clock
TIM3 -> Channel1: PWM Generation CH1
TIM3 -> Channel2: PWM Generation CH2
```

推荐参数：

```text
Prescaler: 0
Counter Period: 3599
Counter Mode: Up
Clock Division: No Division
Auto-reload preload: Disable
```

当 `TIM3` 时钟为 `72MHz` 时：

```text
PWM频率 = 72MHz / (0 + 1) / (3599 + 1) = 20kHz
```

20kHz PWM 通常听感更安静，也适合直流电机驱动。

### 4.4 电机方向 GPIO

配置为：

```text
PB12 -> GPIO_Output
PB13 -> GPIO_Output
PB14 -> GPIO_Output
PB15 -> GPIO_Output
```

参数：

```text
GPIO output level: Low
GPIO mode: Output Push Pull
GPIO Pull-up/Pull-down: No pull-up and no pull-down
Maximum output speed: Low 或 Medium
```

上电默认全低，避免电机突然动作。

### 4.5 TIM2 和 TIM4 输入捕获测速

左轮：

```text
TIM2 -> Clock Source: Internal Clock
TIM2 -> Channel1: Input Capture direct mode
PA0  -> TIM2_CH1
```

右轮：

```text
TIM4 -> Clock Source: Internal Clock
TIM4 -> Channel1: Input Capture direct mode
PB6  -> TIM4_CH1
```

输入捕获建议参数：

```text
Polarity Selection: Rising Edge
IC Selection: Direct
Prescaler: No division
Input Filter: 0 起步，若干扰严重再加滤波
```

NVIC：

```text
TIM2 global interrupt: Enable
TIM4 global interrupt: Enable
```

工程代码里需要添加：

```c
void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim)
{
    d153c_speed_t_capture_callback(htim);
}
```

### 4.6 I2C2 连接 MPU6050 和 OLED

CubeMX 中打开：

```text
I2C2
PB10 -> I2C2_SCL
PB11 -> I2C2_SDA
```

建议参数：

```text
I2C Speed Mode: Standard Mode
I2C Clock Speed: 100000 Hz
```

等 MPU6050 和 OLED 都稳定后，可以再尝试 `400kHz`。调试初期建议先用 `100kHz`，问题更少。

硬件上需要确认：

```text
SCL/SDA 有上拉电阻
MPU6050 地址通常为 0x68 或 0x69
OLED 地址库中写的是 0x78，即 8bit 地址格式
```

### 4.7 USART1 蓝牙

CubeMX 中打开：

```text
USART1 -> Mode: Asynchronous
PA9  -> USART1_TX
PA10 -> USART1_RX
```

参数：

```text
Baud Rate: 9600 或蓝牙模块实际波特率
Word Length: 8 Bits
Parity: None
Stop Bits: 1
```

NVIC：

```text
USART1 global interrupt: Enable
```

初始化时调用：

```c
BluetoothSerial_Init(&huart1);
```

### 4.8 TIM1 1ms 系统调度

`TIM1` 用作系统周期调度，不直接做耗时任务。

CubeMX 中打开：

```text
TIM1 -> Clock Source: Internal Clock
```

不需要开启 PWM 通道。

若 `TIM1` 时钟为 `72MHz`，配置：

```text
Prescaler: 7199
Counter Period: 9
Counter Mode: Up
Clock Division: No Division
Auto-reload preload: Disable
```

计算：

```text
计数频率 = 72MHz / (7199 + 1) = 10kHz
溢出周期 = (9 + 1) / 10kHz = 1ms
```

NVIC：

```text
TIM1 update interrupt: Enable
```

代码启动：

```c
HAL_TIM_Base_Start_IT(&htim1);
```

周期回调只置标志位：

```c
volatile uint8_t flag_5ms = 0;
volatile uint8_t flag_10ms = 0;
volatile uint8_t flag_100ms = 0;

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    static uint16_t tick_1ms = 0;

    if (htim->Instance == TIM1)
    {
        tick_1ms++;

        if ((tick_1ms % 5) == 0)
        {
            flag_5ms = 1;
        }

        if ((tick_1ms % 10) == 0)
        {
            flag_10ms = 1;
        }

        if ((tick_1ms % 100) == 0)
        {
            flag_100ms = 1;
        }

        if (tick_1ms >= 1000)
        {
            tick_1ms = 0;
        }
    }
}
```

主循环中执行实际任务：

```c
while (1)
{
    if (flag_5ms)
    {
        flag_5ms = 0;
        /* MPU6050 读取 + 互补滤波 */
    }

    if (flag_10ms)
    {
        flag_10ms = 0;
        /* 速度更新 + PID + 电机输出 */
    }

    if (flag_100ms)
    {
        flag_100ms = 0;
        /* OLED 刷新 */
    }
}
```

## 5. 推荐软件模块结构

建议将代码分成 BSP、Module、App 三层。初期可以不分太细，但至少不要把所有逻辑堆进 `main.c`。

推荐结构：

```text
Core
├─ Inc
│  ├─ app_control.h
│  ├─ app_task.h
│  ├─ remote.h
│  ├─ attitude.h
│  └─ control_pid.h
│
├─ Src
│  ├─ app_control.c
│  ├─ app_task.c
│  ├─ remote.c
│  ├─ attitude.c
│  └─ control_pid.c
│
Drivers_User
├─ D153C
├─ MPU6050
├─ PID
├─ OLED
└─ Bluetooth
```

如果你想先走最小闭环，也可以先只写：

```text
app_control.c/h
remote.c/h
attitude.c/h
```

其余直接调用已有驱动库。

## 6. 各模块职责

### 6.1 remote 遥控解析模块

职责：

```text
读取 Bluetooth_RxPacket
解析蓝牙命令
生成目标速度和目标转向
处理停止、刹车、模式切换
```

初期命令建议：

```text
[F] -> 前进
[B] -> 后退
[L] -> 左转
[R] -> 右转
[S] -> 停止
```

后期升级：

```text
[V:1.20,T:0.30]
```

含义：

```text
V -> 目标线速度或轮速
T -> 目标转向量
```

建议接口：

```c
void Remote_Update(void);
float Remote_GetTargetSpeed(void);
float Remote_GetTargetTurn(void);
uint8_t Remote_IsStop(void);
```

### 6.2 attitude 姿态解算模块

职责：

```text
读取 MPU6050_Data
计算 pitch / roll
校准 gyro 零偏
用互补滤波融合加速度计和陀螺仪
短时间积分 gyro_z 得到 yaw_est
```

推荐接口：

```c
void Attitude_Init(void);
void Attitude_Update(float dt);
float Attitude_GetPitch(void);
float Attitude_GetRoll(void);
float Attitude_GetYaw(void);
float Attitude_GetYawRate(void);
```

互补滤波初始形式：

```c
angle = alpha * (angle + gyro_rate * dt) + (1.0f - alpha) * accel_angle;
```

推荐参数：

```text
dt = 0.005s
alpha = 0.96 到 0.98
```

### 6.3 control_pid PID 管理模块

职责：

```text
集中初始化 PID 参数
集中保存左速度环、右速度环、航向环
提供统一的控制计算接口
```

建议 PID 实例：

```c
static PID_t pid_left_speed;
static PID_t pid_right_speed;
static PID_t pid_yaw;
```

建议接口：

```c
void ControlPID_Init(void);
void ControlPID_Reset(void);
float ControlPID_LeftSpeed(float target, float actual);
float ControlPID_RightSpeed(float target, float actual);
float ControlPID_Yaw(float target, float actual);
```

初始限幅建议：

```text
左速度 PID 输出：-1000 到 1000
右速度 PID 输出：-1000 到 1000
角度 PID 输出：按目标速度单位限幅，例如 -0.5 到 0.5 rps
```

### 6.4 app_control 总控制模块

职责：

```text
读取遥控目标
读取轮速
读取姿态
计算角度环输出
生成左右轮目标速度
计算左右速度环输出
调用电机驱动输出
处理急停和安全保护
```

核心控制伪代码：

```c
void AppControl_Update10ms(void)
{
    float target_speed = Remote_GetTargetSpeed();
    float target_turn = Remote_GetTargetTurn();

    d153c_speed_t_update_timeout(200);

    float left_actual = d153c_speed_t_rps(D153C_MOTOR_A);
    float right_actual = d153c_speed_t_rps(D153C_MOTOR_B);

    float yaw = Attitude_GetYaw();
    float turn_comp = ControlPID_Yaw(target_turn, yaw);

    float left_target = target_speed - turn_comp;
    float right_target = target_speed + turn_comp;

    float left_pwm = ControlPID_LeftSpeed(left_target, left_actual);
    float right_pwm = ControlPID_RightSpeed(right_target, right_actual);

    d153c_motor_drive(D153C_MOTOR_A, (int16_t)left_pwm);
    d153c_motor_drive(D153C_MOTOR_B, (int16_t)right_pwm);
}
```

如果初期还没接姿态，可以先令：

```c
turn_comp = Remote_GetTargetTurn();
```

这样可以先实现差速遥控，之后再把角度 PID 接进去。

### 6.5 app_task 周期任务模块

推荐周期：

```text
1ms   -> TIM1 中断置标志
5ms   -> MPU6050 读取和姿态更新
10ms  -> 轮速超时更新、PID 运算、电机输出
100ms -> OLED 刷新和蓝牙调试输出
```

不要在中断里做：

```text
I2C 读取 MPU6050
OLED_ShowFrame
printf / 蓝牙发送
复杂浮点计算
```

中断里只置标志，主循环里跑任务。

## 7. 初始化顺序建议

`main.c` 中 HAL 和 CubeMX 自动初始化后，用户初始化建议顺序：

```c
HAL_Init();
SystemClock_Config();

MX_GPIO_Init();
MX_I2C2_Init();
MX_USART1_UART_Init();
MX_TIM1_Init();
MX_TIM2_Init();
MX_TIM3_Init();
MX_TIM4_Init();

d153c_motor_init();
d153c_speed_t_init();
BluetoothSerial_Init(&huart1);
MPU6050_Init(&hi2c2);
OLED_Init(&hi2c2);

ControlPID_Init();
Attitude_Init();

HAL_TIM_Base_Start_IT(&htim1);
```

如果发现电机一上电有异常动作，可把 `d153c_motor_init()` 提前到 GPIO 和 TIM3 初始化之后，并确保方向脚默认低电平。

## 8. 分阶段开发路线

### 阶段 1：电机开环验证

目标：

```text
确认 TIM3 PWM 正常
确认 PB12~PB15 方向控制正常
确认 d153c_motor_drive() 正负号方向正确
```

测试方法：

```c
d153c_motor_drive(D153C_MOTOR_A, 300);
d153c_motor_drive(D153C_MOTOR_B, 300);
HAL_Delay(1000);
d153c_motor_drive(D153C_MOTOR_A, -300);
d153c_motor_drive(D153C_MOTOR_B, -300);
HAL_Delay(1000);
d153c_motor_drive(D153C_MOTOR_A, 0);
d153c_motor_drive(D153C_MOTOR_B, 0);
```

若左右轮方向相反，不要急着改接线，可以先用：

```c
d153c_motor_invert(D153C_MOTOR_A, true);
d153c_motor_invert(D153C_MOTOR_B, true);
```

### 阶段 2：蓝牙遥控开环

目标：

```text
手机或串口助手发送 [F] [B] [L] [R] [S]
小车能前进、后退、左转、右转、停止
```

建议占空比从 `250` 或 `300` 起步，不要一开始给满。

### 阶段 3：T 法测速验证

目标：

```text
TIM2_CH1 和 TIM4_CH1 输入捕获中断正常
d153c_speed_t_rps() 能读到非零速度
d153c_speed_t_valid() 状态合理
```

必须添加：

```c
void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim)
{
    d153c_speed_t_capture_callback(htim);
}
```

周期调用：

```c
d153c_speed_t_update_timeout(200);
```

OLED 显示建议：

```text
L: 左轮 rpm
R: 右轮 rpm
Lv/Rv: valid 状态
```

### 阶段 4：左右轮速度闭环

目标：

```text
给定目标 rps，左右轮能稳定跟踪
车辆能以较稳定速度直行
```

调参顺序：

```text
先 Ki = 0, Kd = 0，只调 Kp
Kp 到有响应但不过度震荡
再加少量 Ki 消除静差
最后视情况加 Kd 抑制变化
```

建议先单轮悬空调，再双轮落地调。

### 阶段 5：MPU6050 与互补滤波

目标：

```text
MPU6050 初始化成功
加速度和角速度读数合理
pitch/roll 静止稳定
gyro_z 静止零偏可校准
```

启动时建议静止 1 到 2 秒，采样陀螺仪平均值作为零偏。

### 阶段 6：短时航向环

目标：

```text
直行时用 yaw 或 yaw_rate 修正偏航
转向时能产生合理左右速度差
```

推荐先做 `yaw_rate` 控制，再做 `yaw` 积分控制：

```text
遥控左转/右转 -> 目标 yaw_rate
PID_YawRate(target_yaw_rate, actual_gz) -> turn_comp
```

这个比直接控制积分出来的 `yaw` 更不怕漂移，调起来也更轻。

### 阶段 7：完整遥控协议与显示

目标：

```text
支持速度大小
支持转向大小
支持停止
支持 OLED 显示调试变量
```

OLED 建议显示：

```text
第 1 页：
Lrpm / Rrpm
Ltgt / Rtgt
Lpwm / Rpwm

第 2 页：
Pitch / Roll
Gz / Yaw
Mode / BT
```

## 9. 初始 PID 参数建议

PID 参数一定要实车调，这里只给起点。

速度环：

```text
Kp: 100 到 300
Ki: 2 到 20
Kd: 0 到 20
OutMin: -1000
OutMax: 1000
```

如果速度单位使用 `rps`，目标速度初期建议：

```text
0.5 rps 到 2.0 rps
```

角速度环：

```text
Kp: 0.01 到 0.1
Ki: 0
Kd: 0 到 0.01
输出限幅：根据速度单位设置，例如 -0.8 到 0.8 rps
```

航向角环：

```text
Kp: 0.02 到 0.2
Ki: 0
Kd: 0 到 0.02
输出限幅：例如 -0.8 到 0.8 rps
```

调参时优先保证速度环稳定。速度环不稳时，不要急着上角度环。

## 10. 关键风险与处理

### 10.1 I2C1 与 TIM4_CH1 冲突

`TIM4_CH1` 默认是 `PB6`，`I2C1_SCL` 默认也是 `PB6`。本项目建议使用 `I2C2`，即 `PB10/PB11`。

### 10.2 UART 回调重复定义

蓝牙库已经定义：

```c
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
```

如果你自己再写一个同名函数，会链接失败。后续若要扩展多个串口，建议把蓝牙库里的回调改成统一分发函数。

### 10.3 T 法低速超时

低速时脉冲间隔很长，速度可能停留在旧值。需要周期调用：

```c
d153c_speed_t_update_timeout(200);
```

超时时间可以根据最低可接受速度调整。

### 10.4 MPU6050 yaw 漂移

MPU6050 没磁力计，`yaw` 长期积分会漂。建议优先用 `gyro_z` 做角速度环，或只做短时间航向保持。

### 10.5 OLED 刷新阻塞

`OLED_ShowFrame()` 会通过 I2C 刷整帧，不能放在中断中。建议 `100ms` 刷一次，调试够用。

### 10.6 F103C8T6 RAM 和 Flash 有限

OLED 字库文件较大，若编译后 Flash 紧张，可以裁剪字体、减少图片资源、减少 `printf` 浮点输出。

## 11. 最小可运行闭环

第一版最小闭环建议只包含：

```text
TIM3 PWM
PB12~PB15 方向控制
USART1 蓝牙
D153C 电机驱动
```

实现目标：

```text
[F] 前进
[B] 后退
[L] 左转
[R] 右转
[S] 停止
```

第二版加入：

```text
TIM2/TIM4 T 法测速
OLED 显示左右轮速度
```

第三版加入：

```text
左右轮速度 PID
```

第四版加入：

```text
MPU6050 + 互补滤波 + 角速度/航向修正
```

这个顺序能把问题拆开，避免电机、测速、姿态、PID、蓝牙同时出问题时无法定位。

## 12. 后续可以直接编写的代码骨架

下一步适合先写以下文件：

```text
remote.c / remote.h
attitude.c / attitude.h
control_pid.c / control_pid.h
app_control.c / app_control.h
app_task.c / app_task.h
```

主循环最终保持简单：

```c
while (1)
{
    AppTask_Run();
}
```

`AppTask_Run()` 内部根据 `flag_5ms`、`flag_10ms`、`flag_100ms` 分发任务。这样 `main.c` 不会越来越乱，后续调 PID、改协议、加 OLED 页面都比较好维护。

