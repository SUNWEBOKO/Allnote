# ESP32 直流电机控制完全指南

> 基于考拉工作室系列视频课程整理，涵盖硬件理论、洞洞板制作、编程基础、PID 闭环控制到麦轮小车实战。

---

## 一、硬件基础

### 1.1 直流减速电机与编码器

直流减速电机内部有两大部分：**直流有刷电机**提供驱动力，**齿轮减速箱**降低转速、增大扭矩。常见的型号如 MG520，额定电压 12V，空载转速约 333 RPM。

电机尾部通常带有一个**霍尔编码器**，用于测量转速和转向。编码器输出两路方波信号——**A 相**和 **B 相**，两者相位相差 90°。这一相位差是判断转向的关键：

- 正转时，A 相上升沿对应 B 相为高电平
- 反转时，A 相上升沿对应 B 相为低电平

每次 A 相上升沿触发中断，读取 B 相电平即可同时完成**计数**和**方向判定**。

### 1.2 MOS 管 H 桥与 TB6612 驱动芯片

直流电机的正反转通过 **H 桥**电路实现。H 桥由四个 MOS 管组成，对角导通控制电流方向：

- Q1/Q4 导通 → 电机正转
- Q2/Q3 导通 → 电机反转
- 同侧 MOS 管不可同时导通（否则短路）

**TB6612** 是一款集成双 H 桥的电机驱动芯片，关键引脚功能：

| 引脚 | 功能 |
|------|------|
| `PWMA` / `PWMB` | PWM 调速输入（两路独立） |
| `AIN1` / `AIN2` | A 电机方向控制 |
| `BIN1` / `BIN2` | B 电机方向控制 |
| `STBY` | 待机控制，高电平使能 |
| `VM` | 电机电源输入（最高 12V） |
| `VCC` | 逻辑电源输入（3.3V / 5V） |

方向控制真值表（以 A 电机为例）：

| AIN1 | AIN2 | 行为 |
|------|------|------|
| 0 | 0 | 悬停（滑行） |
| 0 | 1 | 反转 |
| 1 | 0 | 正转 |
| 1 | 1 | 短路刹车 |

### 1.3 PWM 调速原理

电机的转速与两端平均电压成正比。通过改变 PWM 的**占空比**（0%–100%），即可实现从停止到全速的连续调节。占空比 50% 意味着 MOS 管半开半关，电机获得约一半的电源电压，转速约为全速的一半。

在 ESP32 上，使用 `ledcWrite(channel, duty)` 输出 PWM 信号。占空比范围 0–255（8 位分辨率），对应 0%–100%。

### 1.4 ESP32 引脚分配与外部中断

相比 Arduino UNO（其 ATmega328P 仅有 INT0/INT1 两个专用硬件外部中断引脚 D2/D3，PCINT 虽多但配置复杂、不适合高频编码器读取），**ESP32 几乎所有 GPIO 都支持外部中断**，这为多电机控制提供了极大便利。

外部中断配置使用：

```cpp
attachInterrupt(digitalPinToInterrupt(pin), ISR, RISING);
```

中断服务函数必须加上 `IRAM_ATTR` 属性，确保代码放在 IRAM 中快速执行：

```cpp
void IRAM_ATTR encoderISR() {
  // 读取 B 相电平，判断方向，更新计数
}
```

---

## 二、硬件搭建

### 2.1 洞洞板布线设计

使用 **DIYLC**（Do It Yourself Layout Creator）开源软件进行布线设计。关键步骤：

1. 根据实际尺寸创建洞洞板（本例 18 孔 × 字母 A–X）
2. 放置插接件：SH2.54 胶壳（电机接口）、排针 / 排母（接 Arduino）、TB6612 芯片座
3. 放置 MP1584 降压模块（12V → 5V）
4. 放置接线端子（12V 电源输入）
5. 标记各引脚名称（方便对照）
6. **规划铜线走线**：优先让强电（VM、GND）走板内铜线
7. 无法直接走通的地方用 **跳线（jumper，即飞线）** 连接

布线原则：
- 强电优先走板面铜线
- 编码器信号线尽量远离强电线
- 元件间距保留至少一个焊盘孔
- TB6612 两侧各预留 5 个孔位

焊接时，可用手机拍摄 DIYLC 的**镜像图**，然后对着屏幕焊接背面，避免方向搞反。

### 2.2 元器件清单

| 元器件 | 数量 | 说明 |
|--------|------|------|
| 5×7 cm 洞洞板 | 1+ | 建议多备一块以防报废 |
| TB6612 驱动芯片 | 1 | 双 H 桥 |
| MP1584 降压模块 | 1 | 12V → 5V，给逻辑供电 |
| 排针（公） | 若干 | 连接 Arduino（4pin + 6pin） |
| 排母（母） | 若干 | TB6612 芯片座（可插拔） |
| SH2.54 6pin 胶壳 | 2 | 连接编码电机 |
| 2.54mm 接线端子 | 1 | 12V 电源输入 |
| 单芯铜线 | 1卷 | 走线用 |
| 杜邦线（公对母） | 若干 | 飞线与电源接地 |

### 2.3 焊接流程

**第一步：焊接插接件**

先定位所有插接件（排针、排母、胶壳、接线端子）。每个元件焊法一致：插入孔位 → 翻到背面固定一个焊点 → 调正位置 → 焊完其余引脚。

**第二步：焊接 MP1584 模块**

MP1584 为降压稳压板，输入 12V，输出 5V。注意正负极方向，确认焊接到位。

**第三步：走铜线**

剥线 → 折弯定型 → 剪去多余长度 → 焊两端固定 → 中间补锡加固。铜线走线尽量横平竖直，减少交叉。

**第四步：飞线**

无法通过铜线直接连通的地方，使用带绝缘皮的杜邦线做跳线。本例总共只需要**两根飞线**（STBY 接 VCC、另一路 VCC 对接）。

**第五步：测试**

1. 万用表导通档检查各焊点连通性
2. 上 12V 电源，测 MP1584 输出是否为 5V
3. 插上 TB6612 和 Arduino
4. 写入简单开环程序，验证电机正反转正常

### 2.4 新版 PCB 转接板方案

后续版本推出了**成品 PCB 转接板**，与洞洞板方案的对比如下：

| 维度 | 洞洞板方案 | PCB 转接板方案 |
|------|-----------|---------------|
| 供电方式 | 需独立面包板供电（Arduino → MP1584 → 5V） | 板载 5V 稳压，12V 直供即可同时给 ESP32 供电 |
| 焊接难度 | 高——需手动布线、弯脚、焊铜线、飞线 | 低——直插元件焊接即可，无需飞线 |
| 引线可靠性 | 铜线 + 飞线，长期使用可能松脱 | PCB 覆铜走线，稳定可靠 |
| 接口兼容性 | SH2.54 胶壳 | XH2.54 + PH2.0 双接口，兼容不同电机线 |
| 额外引出 | 无 | 串口 / I²C 单独引出，方便调试扩展 |
| 电源方案 | 12V 适配器或电池 | **PD 诱骗线 + 充电宝 12V 输出**（3C 认证，安全便携） |
| 适用场景 | 学习焊接、低成本原型验证 | 长期项目、竞赛场景、批量制作 |

---

## 三、编程基础

### 3.1 ESP32 定时器配置

ESP32 内置硬件定时器，基于 80MHz APB 时钟（40MHz 晶振倍频），经过 16 位分频器后驱动 64 位计数器。配置方式：

```cpp
hw_timer_t *timer = timerBegin(0, 80, true);          // 分频 80 → 1MHz
timerAttachInterrupt(timer, &timerISR, true);          // 绑定中断
timerAlarmWrite(timer, 50000, true);                   // 50ms 溢出
timerAlarmEnable(timer);                               // 启动
```

- 分频系数 80 → 定时器频率 1MHz（1µs 精度）
- 溢出值 50000 → 每 50ms 触发一次中断
- 第三个参数 `true` 表示自动重载

### 3.2 编码器测速：外部中断 + 方向判定

在定时器中断中，需要知道电机的转速和转角。转速由编码器脉冲数换算得到：

- 编码器精度：电机每转输出 N 个脉冲（具体取决于编码器型号）
- 测速公式：`speed_rpm = (pulse_count / N) * (60 / time_interval_s)`

注意：编码器标称 PPR（Pulse Per Revolution）通常指 **A 相一个完整周期**内的脉冲数。若同时采集 A、B 两相的上升沿和下降沿（4 倍频），程序中的 `N` 应取 `PPR × 4`。例如 11 线编码器 PPR = 11，4 倍频后每转计数值 N = 44，测速公式中的 `N` 应填 44。

外部中断服务函数根据 A/B 相 90° 相位差判定转向：

```cpp
void IRAM_ATTR encoderISR() {
  if (digitalRead(B_PIN) == HIGH) {
    pulse_count++;   // 正转
  } else {
    pulse_count--;   // 反转
  }
}
```

### 3.3 M/T 法：超低速测速

低速情况下，传统**M 法**（固定时间计数）和**T 法**（固定角度计时）各有局限：

- **M 法（定时测频）**：适合高速，低速时脉冲少，分辨率差
- **T 法（定角测时）**：适合低速，高速时时间分辨率差

**M/T 法**组合两者优势：

1. 低频定时器（如 50ms）发出测速指令
2. 高频定时器（如 1µs 分辨率）持续计数
3. 下一个编码器中断到来时，**同时**采集编码器脉冲差和高频定时器时间差
4. 精确计算速度：`speed = pulse_diff / N / (time_diff / 1e6) * 60`

关键实现要点：
- 高频定时器指针需要传递给 Encoder 类
- 使用标记位控制采样时机（收到测速指令后等待编码器中断到来才计算）
- 防零除保护（`time_diff` 接近 0 时跳过本次计算）

```cpp
// M/T 法测速实现（低频定时器 + 编码器中断配合采样）
volatile bool speed_ready = true;
volatile int64_t last_pulse = 0;
volatile uint32_t last_time = 0;

// 低频定时器中断（50ms）—— 发起测速请求
void timerISR() {
  speed_ready = false;   // 置标志，等待编码器中断采样
}

// 编码器中断 —— 同时采样脉冲差和时间差
void IRAM_ATTR encoderISR() {
  if (digitalRead(B_PIN) == HIGH) count++;
  else count--;

  if (!speed_ready) {
    int64_t pulse_diff = count - last_pulse;
    uint32_t now = micros();
    uint32_t time_diff = now - last_time;

    if (time_diff > 100) {   // 防零除
      current_speed = (double)pulse_diff / PPR
                    / (time_diff / 1e6) * 60.0;
    }

    last_pulse = count;
    last_time = now;
    speed_ready = true;
  }
}
```

实测效果对比：
- 60 RPM → 精度提升到 ±0.05 RPM
- 30 RPM → 稳定运行
- 10 RPM → 仍可控制
- 极限可达 3 RPM

### 3.4 面向对象的电机控制库封装

将直流电机控制封装为 `DCmotor` 类，包含以下接口：

```cpp
class DCmotor {
public:
  void attach(int pin1, int pin2, int pwmPin);
  void setSpeed(int direction, int value);   // 带方向
  void setSpeed(int value);                  // 保持当前方向
  void invertDirection(bool invert);
  void stop();       // 悬空停
  void brake();      // 短路刹车
  bool isAttached();
  bool isSetDirection();
private:
  int _pin1, _pin2, _pwmPin;
  bool _invertFlag;
  bool _attached;
};
```

`setSpeed` 内部使用异或（XOR）实现方向取反：

```cpp
int actualDir = direction ^ _invertFlag;
```

封装后，主程序只需：

```cpp
DCmotor motor1;
motor1.attach(PIN1, PIN2, PWM_PIN);
motor1.setSpeed(0, 150);  // 正转，占空比 150/255
```

---

## 四、PID 闭环控制

### 4.1 开环 vs 闭环

**开环控制**：只发送 PWM 信号给电机，不采集反馈。优点是简单稳定，缺点是无法抵抗负载变化（上坡减速、下坡加速）。

**闭环控制**：通过编码器采集实际转速，比较期望值与实际值的误差，用控制器调整 PWM 输出。这样当负载增大导致转速下降时，控制器会自动增大 PWM 来补偿。

### 4.2 P/I/D 三个分量

**P——比例控制器（Proportional）**

$$u_P = K_P \times e(t)$$

- 误差越大，输出越大，响应快
- 缺点：存在**静差**（稳态误差），即误差为 0 时比例项也为 0，无法完全消除偏差

**I——积分控制器（Integral）**

$$u_I = K_I \times \int e(t) \, dt$$

- 对误差的累积起作用，响应慢但能消除静差
- 缺点：积分过大会导致**超调**和震荡

**D——微分控制器（Differential）**

$$u_D = K_D \times \frac{de(t)}{dt}$$

- 对误差的变化率响应，预测误差趋势
- 缺点：放大高频噪声，导致系统抖动
- 在电机速度控制中一般不用 D 项（电机本身有机械阻尼）

### 4.3 离散 PID 代码实现

计算机是数字系统，需将 PID 离散化：

```cpp
// 全局变量
double target_speed;          // 目标速度
double current_speed;         // 当前速度
double speed_error;           // 当前误差
double speed_integral;        // 误差积分
double last_speed_error;      // 上一次误差

double KP = 2.0, KI = 0.0, KD = 0.0;
int pwm_output;

// 定时器中断中执行（50ms 周期）
void timerISR() {
  // 1. 获取当前速度（来自编码器）
  current_speed = getSpeed();

  // 2. 计算误差
  speed_error = target_speed - current_speed;

  // 3. 积分项（deltaT = 0.05s）
  speed_integral += speed_error * 0.05;

  // 4. 微分项
  double derivative = (speed_error - last_speed_error) / 0.05;

  // 5. PID 输出
  double pid_out = KP * speed_error + KI * speed_integral + KD * derivative;

  // 6. 输出限幅 [-255, 255]
  pwm_output = constrain((int)pid_out, -255, 255);

  // 7. 输出到电机
  if (pwm_output >= 0) {
    motor.setSpeed(0, pwm_output);
  } else {
    motor.setSpeed(1, -pwm_output);
  }

  // 8. 更新上一误差
  last_speed_error = speed_error;
}
```

**调参经验**：
- 先调 KP：从小到大，直到系统出现轻微震荡，然后退回到稳定值
- 再加 KI：从 0.1 开始逐步增大，观察静差消除速度和超调量
- 电机速度控制中一般不加 KD
- 积分饱和时需考虑**积分限幅**（对 `speed_integral` 设上下限）

### 4.4 全链路封装：30 行代码跑双电机 PID

将电机控制拆分为三个层次封装：

**层次一：DCmotor（输出层）**
- `attach` 绑定引脚
- `setSpeed` 控制方向与占空比
- `invertDirection` / `stop` / `brake`

**层次二：Encoder（输入层）**
- `attach` 绑定编码器引脚
- 中断服务函数使用**静态成员函数 + this 指针**技巧，解决类成员函数不能直接作为中断回调的问题：

```cpp
class Encoder {
public:
  void attach(int pinA, int pinB) {
    _pinA = pinA; _pinB = pinB;
    pinMode(pinA, INPUT); pinMode(pinB, INPUT);
    attachInterruptArg(digitalPinToInterrupt(pinA), isrStatic, this, RISING);
  }

  static void IRAM_ATTR isrStatic(void* arg) {
    ((Encoder*)arg)->isr();
  }

  void IRAM_ATTR isr() {
    if (digitalRead(_pinB) == HIGH) count++;
    else count--;
  }

  int64_t getCount() { return count; }
private:
  int _pinA, _pinB;
  volatile int64_t count = 0;
};
```

**层次三：CloseLoopMotor（闭环层）**
内部组合 DCmotor 和 Encoder，提供完整的闭环控制接口：

```cpp
class CloseLoopMotor {
public:
  void attach(int pin1, int pin2, int pwmPin, int encA, int encB) {
    motor.attach(pin1, pin2, pwmPin);
    encoder.attach(encA, encB);
  }
  void setTargetSpeed(double speed);
  void setPID(double kp, double ki, double kd);
  void update();              // 测速 → 误差 → PID → 输出
};
```

**最终主程序仅需 30 行**：

```cpp
#include "CloseLoopMotor.h"

CloseLoopMotor motorL, motorR;

void setup() {
  motorL.attach(13, 12, 14, 26, 27);
  motorR.attach(25, 33, 32, 34, 35);
  motorL.setPID(2.0, 5.0, 0.0);
  motorR.setPID(2.0, 5.0, 0.0);

  motorL.setTargetSpeed(60);
  motorR.setTargetSpeed(60);

  hw_timer_t *timer = timerBegin(0, 80, true);
  timerAttachInterrupt(timer, &timerISR, true);
  timerAlarmWrite(timer, 50000, true);   // 50ms
  timerAlarmEnable(timer);
}

void loop() {
  // 主程序不需要再写任何控制逻辑
}

void timerISR() {
  motorL.update();
  motorR.update();
}
```

---

## 五、综合实战：麦轮小车

### 5.1 四路电机控制板与通信接口

四轮小车需要四路驱动，使用**四路电机控制板**，通信接口二选一：

- **I²C**：SCL / SDA
- **UART**：RX → IO17，TX → IO16

使用提供的电机库，只需两行即可初始化四路电机：

```cpp
motor.init();   // 初始化
controlSpeed(500, 500, 500, 500);  // 四轮速度，范围 -1000~1000
```

通过上位机可以测试和调参：
- `$refresh#` — 查询参数
- `$speed:500,0,0,0#` — 单独设置某轮速度

### 5.2 麦轮运动学

麦轮小车通过四个麦克纳姆轮的斜辊方向组合实现**全向移动**。常见轮序配置（从左上顺时针）：

| 轮 | 辊子方向 |
|----|---------|
| 左前 FL | `/`  |
| 右前 FR | `\` |
| 左后 BL | `\` |
| 右后 BR | `/` |

基本运动模式：

| 运动 | FL | FR | BL | BR |
|------|----|----|----|----|
| 前进 | + | + | + | + |
| 后退 | - | - | - | - |
| 左转 | - | + | - | + |
| 右转 | + | - | + | - |
| 左平移 | - | + | + | - |
| 右平移 | + | - | - | + |

### 5.3 蓝牙遥控实现

1. 宏定义开启蓝牙功能：`#define BLE_ENABLE`
2. 调用 `BLE_control()` 启动
3. 手机使用 **e 调试 APP** 或其他蓝牙串口工具，建立摇杆组件
4. 摇杆坐标映射为麦轮速度向量，发送给 ESP32
5. ESP32 解析指令后调用 `controlSpeed()` 驱动四轮

遥控指令格式示例：

```
方向: 左平移 → 数据: -500, 500, 500, -500
方向: 前进 → 数据: 500, 500, 500, 500
```

---

## 六、常见问题与排查

### 电机不转
- 检查电源：MP1584 是否输出 5V？VM 是否有 12V？
- 检查 STBY：是否已接 VCC 使能？
- 检查电机线：SH2.54 胶壳是否插紧？

### 转速失控（跑飞）
- 编码器方向反了：检查 A/B 相接线，或调用 `invertDirection(true)`
- PID 极性反了：误差是 `target - current` 还是 `current - target`？

### 电机抖动 / 震荡
- KP 太大：降低比例系数
- KI 太大：降低积分系数或增加积分限幅
- 编码器数据噪声：检查屏蔽，缩短编码器线长度

### 低速不稳
- 编码器分辨率不够：考虑 M/T 法测速
- 电机本身低速扭矩不足：选用减速比更大的电机
- 编码器线数（PPR）决定理论最低可测转速。例如 50ms 测速周期下，11 线编码器（PPR = 11，4 倍频后 N = 44）在 60 RPM 时每周期仅捕获约 2–3 个脉冲，30 RPM 以下计数分辨率的相对误差急剧增大。若目标低速 ≤ 30 RPM，建议选用更高线数编码器（如 500 PPR）或改用 M/T 法。
