# ESP32 面包板电控入门 —— 完整复习文档

> 基于 B站"喵星考拉"系列视频整理。教程以 **WEMOS D1 R32（ESP32）** 为核心，从 UNO 代码移植到常用传感器/执行器逐一覆盖，适合电赛、工程实践入门。

---

## 一、概述与背景

**目标**：用 ESP32 替代老旧的 Arduino UNO，掌握代码移植方法，并独立完成常见传感器和执行器的接线与编程。

**为什么选 ESP32**：
- 双核处理器，性能远超 UNO
- 几乎所有 GPIO 都支持 PWM（UNO 仅 6 路）
- 原生 WiFi + 蓝牙
- 内置 12-bit ADC（UNO 仅 10-bit）
- 价格与 UNO 相当甚至更低

**视频整体路线**：
1. 先用 UNO 完成电位器 → 舵机的控制
2. 演示如何完整移植到 ESP32
3. 基于 ESP32 逐一讲解各传感器/执行器
4. 最后做设备间的联动（超声波 + OLED、MPU6050 + OLED）

---

## 二、材料清单与工具准备

| 序号 | 部件 | 规格 / 说明 |
|------|------|-------------|
| 1 | 面包板 | 760 孔，用于无焊接快速搭建电路 |
| 2 | WEMOS D1 R32 | ESP32 核心板，UNO 相同板型，可直接用 UNO 的扩展板 |
| 3 | USB 数据线 | 连接 D1 R32 到电脑，用于供电和程序烧写 |
| 4 | 面包板电源模块 | 输入 9–12 V DC，输出 5 V / 3.3 V 可选，带开关 |
| 5 | 9 V 电源适配器 | 给面包板供电 |
| 6 | 电位器（滑动变阻器） | 模拟信号输入，演示 ADC 读取 |
| 7 | 舵机 | SG90 或类似，PWM 控制 0–180° 旋转 |
| 8 | SR04 超声波模块 | 2–400 cm 测距，用于避障 |
| 9 | SSD1306 OLED 显示屏 | 128×64 像素，I²C 接口 |
| 10 | MPU6050 陀螺仪模块 | 6 轴（三轴加速度计 + 三轴陀螺仪），I²C 接口 |
| 11 | 4 路巡线传感器 | 光电反射式开关，数字信号输出，带阈值调节 |
| 12 | 4 路独立按键模块 | 数字输入，需自行焊接排针 |
| 13 | 杜邦线（公对公） | 用于面包板上的互连 |
| 14 | 杜邦线（公对母） | 用于连接传感器模块到面包板 |

> **提示**：杜邦线散装买入价格低廉，适合原理验证。但在最终集成的机器人项目中，建议使用带卡扣的防呆端子线，避免振动脱落。

---

## 三、面包板结构详解

### 3.1 基本结构

```
      ┌──────┬──────┬──────┬──────┐
  (+)  │██████│██████│██████│██████│   ← 红色电源轨（整行导通）
  (-)  │██████│██████│██████│██████│   ← 蓝色/绿色地轨（整行导通）
      ├╌╌╌╌╌╌┼╌╌╌╌╌╌┼╌╌╌╌╌╌┼╌╌╌╌╌╌┤
      │ a b c d e │ a b c d e │       ← 每 5 孔一组纵向导通
      │ 1 2 3 4 5 │ 1 2 3 4 5 │
      │ 6 7 8 9 0 │ 6 7 8 9 0 │
      │ 1 2 3 4 5 │ 1 2 3 4 5 │
      │ ...       │ ...       │
      ├╌╌╌╌╌╌┼╌╌╌╌╌╌┼╌╌╌╌╌╌┼╌╌╌╌╌╌┤
  (-)  │██████│██████│██████│██████│   ← 蓝色/绿色地轨
  (+)  │██████│██████│██████│██████│   ← 红色电源轨
      └──────┴──────┴──────┴──────┘
```

### 3.2 导通规则

- **电源轨**：红（+）线、蓝（-）线各一长条，整行导通
- **元件区**：每一竖列内，同一字母列的 5 个孔是导通的；不同字母列之间断开
- **中槽**：面包板中间的凹槽两侧完全隔离，用于跨接 DIP 芯片

### 3.3 直观理解

撕掉面包板背面的不干胶贴纸，可以看到内部的金属弹片走线：
- 电源轨的弹片是一条直线贯穿整行
- 元件区的弹片是 5 个一组的短条

这个结构是所有面包板通用的，记住 "横通竖断、五孔一组" 即可。

---

## 四、供电与共地（最重要的一步）

### 4.1 安装面包板电源模块

```
电源模块背面有 8 个针脚（左右各 4 个）
          ┌────┬────┬────┬────┐
    左排  │ +  │ -  │ +  │ -  │
          ├────┼────┼────┼────┤
    右排  │ -  │ +  │ -  │ +  │
          └────┴────┴────┴────┘

安装：直接跨骑在面包板左端（或中间），确保每个针脚插入对应孔位
跳线帽位置：插左边 = 5 V 输出，插右边 = 3.3 V 输出
```

- 输入接 9–12 V DC 适配器（2.1 mm 插头）
- 按开关点亮即供电正常

### 4.2 共地操作

```
UNO/ESP32 的 GND  →  面包板蓝色地轨
面包板 5 V(+) 轨  →  面包板电源模块的正极输出
面包板 GND(-) 轨  →  面包板电源模块的负极输出
```

**为什么必须共地？**
- 电压是相对值。单片机判断信号高/低，取决于信号线与地线之间的电位差
- 不共地时，两个板子各自参考自己的地，信号无法正确传输
- **共地 = 统一电压基准**

### 4.3 电源分配

面包板较长时，左右两端的电源轨并不导通。如果需要右端也有电：
- 用杜邦线短接左端红轨 → 右端红轨
- 用杜邦线短接左端蓝轨 → 右端蓝轨

---

## 五、代码移植：UNO → ESP32（核心能力）

### 5.1 UNO 引脚与 ESP32 引脚对照

| 功能 | UNO 引脚 | ESP32 D1 R32 GPIO |
|------|----------|-------------------|
| 数字 I/O (例) | D8, D9 | IO13, IO14 等任意 GPIO |
| 模拟输入 | A0–A5 (标号, 对应 PORTC) | IO4, IO34, IO35, IO36, IO39 |
| PWM | D3, D5, D6, D9, D10, D11 | 几乎所有 GPIO 均支持 |
| I²C SDA | A4 (PC4) | IO21 |
| I²C SCL | A5 (PC5) | IO22 |
| 串口 TX/RX | D0(RX), D1(TX) | IO1(TX), IO3(RX) |

### 5.2 ESP32 D1 R32 的私印错误（重要！）

D1 R32 板子 **左侧模拟引脚附近的丝印标号是错误的**。

- 丝印上标着 `36` `34` `35` `39` 的位置，实际对应的 ADC 通道与标号一致，但布局位置可能让人插错
- **以原理图上的 GPIO 号为准，不要信任 PCB 丝印**

### 5.3 移植三步法

**Step 1 — 改引脚号**

找到所有硬编码的引脚号：
- `pinMode(9, OUTPUT)` → `pinMode(13, OUTPUT)`
- `analogRead(A0)` → `analogRead(4)`
- `myServo.attach(9)` → `myServo.attach(13)`

**Step 2 — 换库**

| 库 | UNO | ESP32 |
|----|-----|-------|
| 舵机 | `<Servo.h>` | `<ESP32Servo.h>` |

安装方法：工具 → 管理库 → 搜索 "ESP32Servo" → 安装

**Step 3 — 调 ADC 范围**

UNO 是 10-bit ADC（0–1023），ESP32 是 12-bit ADC（0–4095）。

```
// UNO
int angle = map(adc, 0, 1023, 0, 180);

// ESP32
int angle = map(adc, 0, 4095, 0, 180);
```

**Step 4 — 选板型**

工具 → 开发板 → ESP32 → "ESP32 D1 R4 module"（或类似名称，取决于安装的 ESP32 板支持包版本）

### 5.4 移植案例：电位器 → 舵机（完整对照）

#### UNO 版本

```cpp
#include <Servo.h>

Servo myServo;
#define POT_PIN A0
#define SERVO_PIN 9

void setup() {
  myServo.attach(SERVO_PIN);
  Serial.begin(9600);
}

void loop() {
  int adc = analogRead(POT_PIN);       // 0–1023
  int angle = map(adc, 0, 1023, 0, 180);
  myServo.write(angle);
  Serial.print("ADC: "); Serial.println(adc);
  delay(15);
}
```

#### ESP32 移植后

```cpp
#include <ESP32Servo.h>               // ← 换了库

Servo myServo;
#define POT_PIN 4                      // ← UNO A0 → GPIO4
#define SERVO_PIN 13                   // ← UNO D9 → GPIO13

void setup() {
  myServo.attach(SERVO_PIN);
  Serial.begin(9600);
}

void loop() {
  int adc = analogRead(POT_PIN);       // ← 0–4095（自动 12-bit）
  int angle = map(adc, 0, 4095, 0, 180); // ← 范围变了
  myServo.write(angle);
  Serial.print("ADC: "); Serial.println(adc);
  delay(15);
}
```

> 改动量很小——这就是 Arduino 生态的可移植性优势。换引脚、换库、改范围，三步即可。

---

## 六、电位器 — 模拟输入

### 6.1 工作原理

电位器本质是一个分压器：旋转旋钮改变中间抽头的位置，从而输出 0–VCC 之间的连续可调电压。

```
     VCC (5 V)
       │
      ╱
     ╱   ← 碳膜电阻
    ╱
   ╳──── OUT（抽头，电压随旋转变化）
    ╲
     ╲
      ╲
       │
      GND
```

### 6.2 接线（UNO 示例，ESP32 同理）

```
电位器三个引脚（从正面看，旋钮朝上）
  ┌───┐
  │ ○ │  ← 正面旋钮
  └─┬─┘
  │ │ │
  G V O
  N C U
  D C T

  GND  → 面包板蓝轨
  VCC  → 面包板红轨（5 V）
  OUT  → ESP32 GPIO4（带 ADC 功能的引脚）
```

**插入面包板的技巧**：
1. 先将杜邦线插到面包板对应孔位
2. 将电位器三个针脚对准同一列插入
3. 确保针脚完全插入，与内部弹片接触

### 6.3 程序

```cpp
#define POT_PIN 4

void setup() {
  Serial.begin(9600);
}

void loop() {
  int adc = analogRead(POT_PIN);        // 返回 0–4095
  float voltage = adc * (5.0f / 4095.0f); // 换算成实际电压

  Serial.print("ADC: ");
  Serial.print(adc);
  Serial.print("  Voltage: ");
  Serial.print(voltage, 2);             // 保留 2 位小数
  Serial.println(" V");

  delay(100);
}
```

运行后打开串口监视器（波特率 9600），旋转电位器可看到 ADC 值和电压值同步变化。

---

## 七、舵机 — PWM 输出

### 7.1 引脚定义

```
舵机三线（常见颜色编码）
  棕色/黑色 → GND
  红色       → VCC（5–7.2 V，这里用 5 V）
  橙色/黄色 → 信号线（PWM）
```

> 注意：高电压舵机（8.4 V / 12 V）需独立供电，不可直接从面包板电源取电。

### 7.2 接线

```
舵机棕色 → 面包板蓝轨 (GND)
舵机红色 → 面包板红轨 (5 V)
舵机橙色 → ESP32 GPIO13
```

### 7.3 控制原理

Arduino 的 Servo 库封装了 PWM 信号生成：
- `myServo.attach(pin)`：将指定引脚与舵机对象绑定
- `myServo.write(angle)`：写入角度 0–180°
- 库自动生成 50 Hz（周期 20 ms）的 PWM，脉宽 0.5–2.5 ms 对应 0–180°

### 7.4 程序

```cpp
#include <ESP32Servo.h>

Servo myServo;
#define SERVO_PIN 13

void setup() {
  myServo.attach(SERVO_PIN);
}

void loop() {
  myServo.write(0);      // 转到 0°
  delay(1000);
  myServo.write(90);     // 转到 90°
  delay(1000);
  myServo.write(180);    // 转到 180°
  delay(1000);
}
```

> 首次上电时舵机会"抖一下"，这是正常的初始化过程。

---

## 八、电位器 → 舵机联动（完整综合例）

### 8.1 原理

读取电位器模拟电压 → `map()` 映射到 0–180° → `myServo.write(角度)`

### 8.2 完整程序

```cpp
#include <ESP32Servo.h>

Servo myServo;
#define POT_PIN 4
#define SERVO_PIN 13

void setup() {
  myServo.attach(SERVO_PIN);
  Serial.begin(9600);
}

void loop() {
  int adc = analogRead(POT_PIN);           // 0–4095
  int angle = map(adc, 0, 4095, 0, 180);  // 映射到角度

  myServo.write(angle);

  // 打印调试信息
  Serial.print("ADC: ");
  Serial.print(adc);
  Serial.print("  Angle: ");
  Serial.println(angle);

  delay(15);  // 舵机控制建议 15–20 ms 间隔
}
```

### 8.3 常见问题

- 舵机抖动剧烈：检查供电是否充足，舵机大角度转动时瞬间电流可能达 1 A 以上，建议舵机单独供电
- 角度反向：检查 `map()` 的输入输出范围是否写反，或交换电位器的 VCC 和 GND 接线
- 只有两个极限位置、没有中间角度：确认使用的是 PWM 引脚，UNO 上需要用带 `~` 标记的引脚

---

## 九、ADC 噪声与滑动平均滤波（工程实用技能）

### 9.1 现象

ESP32 的 12-bit ADC 在电位器不动时，串口读数也会有 ±60 左右的跳动。这是因为：
- 芯片内部 ADC 电路精度有限（ESP32 ADC 的线性度和噪声表现并不理想）
- 面包板上的电磁干扰
- 电源纹波

### 9.2 解决方案：N 次采样取平均

**原理**：噪声通常是零均值的随机信号，多次采样取平均后噪声分量相互抵消，信号分量保留。

**实现**：
```cpp
#define POT_PIN 4
const int N = 10;                     // 采样次数

void setup() {
  Serial.begin(115200);
}

void loop() {
  unsigned int sum = 0;

  for (int i = 0; i < N; i++) {
    sum += analogRead(POT_PIN);
    delay(10);                        // 每次采样间隔 10 ms
  }

  int adc = sum / N;                  // 取平均值

  Serial.println(adc);
  delay(10);                          // 整体的控制周期 ≈ 110 ms
}
```

### 9.3 效果对比

| 指标 | 滤波前 | 滤波后（N=10） |
|------|--------|----------------|
| 静止时波动范围 | ±60 | ±20 |
| 控制周期 | 100 ms | 110 ms |
| 实现难度 | — | 加一个 for 循环 |

### 9.4 在联动代码中嵌入滤波

```cpp
#include <ESP32Servo.h>

Servo myServo;
#define POT_PIN 4
#define SERVO_PIN 13
const int N = 10;

void setup() {
  myServo.attach(SERVO_PIN);
  Serial.begin(115200);
}

void loop() {
  unsigned int sum = 0;
  for (int i = 0; i < N; i++) {
    sum += analogRead(POT_PIN);
    delay(10);
  }
  int adc = sum / N;
  int angle = map(adc, 0, 4095, 0, 180);

  myServo.write(angle);
  Serial.println(angle);
}
```

> 滑动平均是嵌入式系统中最基础、最实用的滤波方法，适合对采样速率要求不高的慢变信号。

---

## 十、SR04 超声波传感器

### 10.1 引脚定义

| SR04 引脚 | 说明 | 接 ESP32 |
|-----------|------|----------|
| VCC | 5 V 供电 | 面包板红轨 |
| GND | 地 | 面包板蓝轨 |
| Trig | 触发信号输入（单片机 → 模块） | GPIO14 |
| Echo | 回波信号输出（模块 → 单片机） | GPIO27 |

### 10.2 测距原理

```
单片机 Trig 发 10 μs 高电平
    ┌─────────────────┐
    │                 │
    ─┘                 └─────────
    ↑ 10 μs

模块内部发出 8 个 40 kHz 超声波脉冲，等待回波

Echo 引脚输出高电平，宽度 = 超声波往返时间
    ┌───────────────────────────────────┐
    │                                   │
    ─┘                                   └─────────
    ↑ duration = pulseIn(ECHO, HIGH)

距离 = duration × 声速 ÷ 2
     = duration × 0.034 cm/μs ÷ 2
     = duration × 0.017 cm/μs
```

### 10.3 接线注意

- SR04 插面包板时注意方向：VCC 在左、GND 在右，不要插反（插反会烧毁模块）
- 尽量用短的杜邦线，长线会引入干扰

### 10.4 程序

```cpp
#define TRIG 14
#define ECHO 27

void setup() {
  Serial.begin(9600);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
}

void loop() {
  // 1. 确保 Trig 低电平
  digitalWrite(TRIG, LOW);
  delayMicroseconds(5);

  // 2. 发 10 μs 高电平触发
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);

  // 3. 读回波脉宽（单位 μs）
  long duration = pulseIn(ECHO, HIGH);

  // 4. 换算为距离：duration × 0.034 / 2
  float distance = duration * 0.034f / 2.0f;

  // 5. 输出
  Serial.print(distance);
  Serial.println(" cm");

  delay(100);
}
```

### 10.5 函数详解：`pulseIn()`

```
pulseIn(pin, value, timeout)
- pin: 要读取的引脚
- value: 要测量的电平（HIGH 或 LOW）
- timeout: 超时时间（默认 1 秒），超出返回 0
```

当 `pulseIn(ECHO, HIGH)` 被调用时：
1. 等待 ECHO 变为 HIGH，记录时间
2. 等待 ECHO 变回 LOW，再次记录时间
3. 返回两次的时间差（μs）

### 10.6 常见问题

- 读数不稳定：杜邦线松动引起，重新插拔
- 读数一直为 0：检查 Trig 和 Echo 是否接反
- 读数偏大/偏小：声速 340 m/s 是标准值（15°C 时），温度变化会影响声速，精度要求高时需做温度补偿

---

## 十一、SSD1306 OLED 屏幕（I²C 总线设备）

### 11.1 I²C 总线要点

- **SCL（Serial Clock）**：时钟线，由主机（ESP32）控制
- **SDA（Serial Data）**：数据线，双向传输
- **总线特性**：一条总线上可以挂多个设备，每个设备有唯一的 7 位地址
- ESP32 的 I²C 引脚固定为：**SDA → GPIO21, SCL → GPIO22**

### 11.2 接线

```
OLED      ESP32
────────────────
GND   →   GND
VDD   →   5 V（注意此模块 VDD 是 VCC 的意思）
SCK   →   GPIO22（SCL）
SDA   →   GPIO21（SDA）
```

> **重要**：正负极接错会烧屏幕，上电前务必用万用表确认。

### 11.3 安装库

工具 → 管理库 → 搜索安装以下两个库：
1. `Adafruit SSD1306` — 屏幕驱动
2. `Adafruit GFX` — 图形与文字渲染

### 11.4 地址确认

SSD1306 的 I²C 地址通常是 **0x3C**。
- Adafruit 的示例程序默认写的是 0x3D
- **务必改成 0x3C**，否则 `display.begin()` 会失败

### 11.5 基本显示程序

```cpp
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1     // ESP32 不用硬件 RESET 引脚

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

void setup() {
  Serial.begin(9600);

  // 初始化，地址 0x3C
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("SSD1306 初始化失败！");
    while (1);  // 失败则死循环
  }

  display.clearDisplay();
  display.display();
}

void loop() {
  // 空循环，屏幕内容由 setup 绘制
}
```

### 11.6 绘图与文字

**清屏与刷新**：
```
display.clearDisplay();    // 清空缓冲区
// ... 在这里绘制内容 ...
display.display();         // 将缓冲区内容刷新到屏幕上
```

**画像素点**：
```
display.drawPixel(x, y, SSD1306_WHITE);
```

**画线**：
```
display.drawLine(x0, y0, x1, y1, SSD1306_WHITE);
```

**画矩形**：
```
display.drawRect(x, y, w, h, SSD1306_WHITE);       // 空心
display.fillRect(x, y, w, h, SSD1306_WHITE);        // 实心
```

**画圆**：
```
display.drawCircle(x, y, r, SSD1306_WHITE);
```

**显示文字**：
```
display.setTextSize(size);          // 1=小字, 2=大字
display.setTextColor(SSD1306_WHITE);
display.setCursor(x, y);            // 起点坐标
display.println("Hello World!");    // 自动换行
```

### 11.7 综合实例：画井字 + 显示文字

```cpp
void setup() {
  Serial.begin(9600);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    while (1);
  }

  display.clearDisplay();

  // 画井字：2 竖 2 横
  display.drawLine(32, 0, 32, 63, SSD1306_WHITE);
  display.drawLine(95, 0, 95, 63, SSD1306_WHITE);
  display.drawLine(0, 15, 127, 15, SSD1306_WHITE);
  display.drawLine(0, 47, 127, 47, SSD1306_WHITE);

  // 对角线交叉
  display.drawLine(0, 0, 127, 63, SSD1306_WHITE);
  display.drawLine(127, 0, 0, 63, SSD1306_WHITE);

  // 显示文字
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 16);
  display.print("Koala Studio");

  display.display();
}

void loop() {}
```

---

## 十二、超声波 + OLED 联调（组合实战）

### 12.1 目标

将超声波测得的距离实时显示在 OLED 屏上，取代串口监视器的功能，实现 "手持/独立运行"。

### 12.2 接线

两个模块并联在同一 I²C 总线 + 电源上：

```
OLED         ESP32
GND    →     GND
VDD    →     5 V
SCK    →     GPIO22 (SCL)
SDA    →     GPIO21 (SDA)

超声波        ESP32
VCC    →     5 V (与 OLED 共用)
GND    →     GND (与 OLED 共用)
Trig   →     GPIO14
Echo   →     GPIO27
```

### 12.3 完整程序

```cpp
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// === 引脚定义 ===
#define TRIG 14
#define ECHO 27

// === OLED 配置 ===
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

void setup() {
  Serial.begin(9600);

  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed");
    while (1);
  }
  display.clearDisplay();
}

void loop() {
  // --- 超声波测距 ---
  digitalWrite(TRIG, LOW);
  delayMicroseconds(5);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);

  long duration = pulseIn(ECHO, HIGH);
  float distance = duration * 0.034f / 2.0f;

  // --- 串口输出（调试用） ---
  Serial.print(distance);
  Serial.println(" cm");

  // --- OLED 显示 ---
  display.clearDisplay();
  display.setTextSize(2);                 // 大字体
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 20);               // 屏幕居中偏上
  display.print(distance, 1);             // 1 位小数
  display.println(" cm");
  display.display();

  delay(100);
}
```

### 12.4 代码要点

- `display.clearDisplay()` 放在每次 loop 开头，避免重影
- 先用串口输出（调试方便），确定测距正常后再打开 OLED
- OLED 不支持倒退覆盖，每次重新全屏刷新

---

## 十三、MPU6050 陀螺仪（6 轴 IMU）

### 13.1 传感器能力

| 类型 | 测量量 | 用途 |
|------|--------|------|
| 加速度计 | X/Y/Z 三轴加速度 (m/s²) | 检测倾斜、震动、自由落体 |
| 陀螺仪 | X/Y/Z 三轴角速度 (°/s) | 检测旋转、积分可得角度 |

### 13.2 I²C 接线（与 OLED 并联）

由于 I²C 是总线，MPU6050 可以直接与 OLCD 并联：

```
MPU6050       ESP32
VCC     →     5 V (与 OLED 共用)
GND     →     GND (与 OLED 共用)
SCL     →     GPIO22 (与 OLED 共用)
SDA     →     GPIO21 (与 OLED 共用)
```

> I²C 总线上的每个设备有独立地址：SSD1306 是 0x3C，MPU6050 是 0x68，不会冲突。

### 13.3 安装库

1. `Adafruit MPU6050`
2. `Adafruit Sensor`（依赖库，自动安装或手动安装）

### 13.4 程序框架

```cpp
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

Adafruit_MPU6050 mpu;

void setup() {
  Serial.begin(9600);

  if (!mpu.begin()) {
    Serial.println("MPU6050 not found");
    while (1);
  }
}

void loop() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  Serial.print("Accel X: "); Serial.print(a.acceleration.x);
  Serial.print(" Y: ");      Serial.print(a.acceleration.y);
  Serial.print(" Z: ");      Serial.println(a.acceleration.z);

  Serial.print("Gyro  X: "); Serial.print(g.gyro.x);
  Serial.print(" Y: ");      Serial.print(g.gyro.y);
  Serial.print(" Z: ");      Serial.println(g.gyro.z);

  Serial.println();
  delay(200);
}
```

### 13.5 结合 OLED 显示

```cpp
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

Adafruit_MPU6050 mpu;
Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
  Serial.begin(9600);

  if (!mpu.begin()) { while (1); }
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { while (1); }

  display.setRotation(0);
  display.clearDisplay();
}

void loop() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);

  display.print("A:");
  display.print(a.acceleration.x, 1); display.print(" ");
  display.print(a.acceleration.y, 1); display.print(" ");
  display.println(a.acceleration.z, 1);

  display.print("G:");
  display.print(g.gyro.x, 1); display.print(" ");
  display.print(g.gyro.y, 1); display.print(" ");
  display.println(g.gyro.z, 1);

  display.display();
  delay(100);
}
```

### 13.6 物理量观察

- **静止水平放置**：Z 轴加速度 ≈ 9.8 m/s²（重力加速度），X/Y 接近 0
- **倾斜 45°**：Z 轴约 6.9 m/s²，X 或 Y 轴约 6.9 m/s²（sin 45° = cos 45° ≈ 0.707）
- **旋转**：陀螺仪对应轴输出非零角速度
- **绕 Z 轴旋转**：Z 轴 gyro 输出正负交替（旋转方向不同）

### 13.7 关于姿态解算

MPU6050 原始输出是加速度和角速度，**不能直接得到欧拉角（pitch/roll/yaw）**。需要：
1. 加速度计通过反正切求 pitch 和 roll（静态精度好，动态受震动影响大）
2. 陀螺仪积分求角度（动态响应快，但有零漂累积误差）
3. 互补滤波 / Mahony 滤波 / Madgwick 滤波 融合两者数据

本教程作为入门，只演示原始数据读取。姿态解算属于进阶内容。

---

## 十四、4 路巡线传感器

### 14.1 原理

- 每个通道是一个 **光电反射式开关**
- 红外 LED 发射光，光敏三极管接收反射光
- 白色表面反射强 → 输出低电平（0）
- 黑色表面反射弱 → 输出高电平（1）
- 每个通道有独立的阈值调节电位器

### 14.2 接线

```
巡线模块接头定义（从上到下）
  ┌──────────┐
  │   GND    │ ← 黑色线 → 面包板蓝轨
  │   X4     │ ← 通道 4 输出 → GPIO26
  │   X3     │ ← 通道 3 输出 → GPIO25
  │   X2     │ ← 通道 2 输出 → GPIO17
  │   X1     │ ← 通道 1 输出 → GPIO16
  │   VCC    │ ← 红色线 → 面包板红轨 (5 V)
  └──────────┘
```

杜邦线（公对母）一端接传感器插针，另一端插面包板跳线。

### 14.3 程序

```cpp
#define X1 16
#define X2 17
#define X3 25
#define X4 26

void setup() {
  Serial.begin(9600);
  pinMode(X1, INPUT);
  pinMode(X2, INPUT);
  pinMode(X3, INPUT);
  pinMode(X4, INPUT);
}

void loop() {
  int s1 = digitalRead(X1);
  int s2 = digitalRead(X2);
  int s3 = digitalRead(X3);
  int s4 = digitalRead(X4);

  // 打印 4 位二进制状态
  Serial.print(s1); Serial.print(" ");
  Serial.print(s2); Serial.print(" ");
  Serial.print(s3); Serial.print(" ");
  Serial.println(s4);

  delay(100);
}
```

### 14.4 阈值调节方法

在每个传感器的背面有一个蓝色电位器。调试方法：

1. 将模块放在 **白色区域**，旋转电位器直到指示灯灭（输出 0）
2. 将模块放在 **黑色区域**，确认指示灯亮（输出 1）
3. 如果不满足，微调电位器直到黑白分明

更精确的方式：结合 OLED 实时显示每个通道的读数，一边观察一边调节。

---

## 十五、总结与知识图谱

### 15.1 信号类型分类

| 信号类型 | 方向 | 示例 | 函数 |
|----------|------|------|------|
| 数字输入 | 外设 → 单片机 | 按键、巡线 | `digitalRead()` |
| 数字输出 | 单片机 → 外设 | LED | `digitalWrite()` |
| 模拟输入 | 外设 → 单片机 | 电位器 | `analogRead()` |
| 模拟输出 | 单片机 → 外设 | （本教程未涉及，见下文） | `analogWrite()` / LEDC |
| 通信 | 双向 | I²C（OLED, MPU6050） | Wire 库 |
| 脉冲测量 | 外设 → 单片机 | 超声波 | `pulseIn()` |
| PWM 输出 | 单片机 → 外设 | 舵机 | Servo 库 |

### 15.2 关键技能清单

- [x] 面包板结构识别与导通规则
- [x] 面包板电源模块安装与跳线设置
- [x] 共地操作
- [x] 从 UNO 到 ESP32 的代码移植三步法
- [x] 电位器接线与模拟信号读取
- [x] 舵机接线与 PWM 控制
- [x] `map()` 映射函数的使用
- [x] ADC 噪声认识与滑动平均滤波
- [x] SR04 超声波测距原理与编程
- [x] `pulseIn()` 函数的理解
- [x] I²C 总线概念与 OLED 驱动
- [x] OLED 绘图基础（点、线、矩形、圆、文字）
- [x] 超声波 + OLED 联调
- [x] MPU6050 加速度计 + 陀螺仪数据读取
- [x] I²C 总线多设备并联
- [x] 巡线传感器调试与阈值设定

### 15.3 进阶方向预告

本教程未涉及但后续视频将覆盖的内容：

- **步进电机控制**：加减速算法、寄存器操作
- **直流电机控制**：H 桥驱动、PWM 调速
- **编码器读取**：定时器捕获、正交解码
- **PID 控制**：闭合反馈环路
- **洞洞板焊接**：自制两路编码器 + PID 转接板
