# 30. CAN 通信入门：硬件连接与 HAL 收发

> 本节重点：先把 CAN 通信跑通。复习时抓住一条主线：**CAN 控制器负责协议，CAN 收发器负责差分电平，所有节点必须同波特率并正确接到同一条 CAN_H/CAN_L 总线上。**

---

## 本节核心问题

学完本节，需要能回答：

- CAN 总线适合解决什么问题？为什么常用于汽车、工业、机器人和电机控制？
- `CAN_TX/CAN_RX` 和 `CAN_H/CAN_L` 是不是同一类信号？中间为什么需要 CAN 收发器？
- CAN 总线两端为什么要接 `120 Ω` 终端电阻？中间节点为什么不要随便接？
- CAN 数据帧入门时最需要关注哪些参数：ID、波特率、采样点、DLC、过滤器？
- CubeMX 中如何根据 CAN 时钟、分频和时间段配置出目标波特率？
- HAL 库中 CAN 的初始化、发送、接收分别有哪些固定步骤？
- 两块 STM32 开发板互发 CAN 数据时，排查顺序是什么？

---

## 1. CAN 是什么

CAN 是 `Controller Area Network` 的缩写，中文常叫**控制器局域网总线**。

它是一种面向多控制器协同的串行通信总线，常见于：

- 汽车电子
- 工业控制
- 机器人底盘 / 云台 / 电机控制
- 多块控制板协同系统
- 传感器、执行器、主控板之间的可靠通信

CAN 的核心特点是：

| 特点 | 复习理解 |
|---|---|
| 多节点 | 一条总线上可以挂多个节点 |
| 共享总线 | 所有节点共用同一对 `CAN_H/CAN_L` |
| 可靠性高 | 有仲裁、错误检测、重发等机制 |
| 抗干扰强 | 使用差分信号，适合复杂电磁环境 |
| 面向消息 | 数据靠 ID 区分含义，不是简单“点对点地址通信” |

入门阶段可以先把 CAN 理解成一个小型通信网络：

```text
节点 A  =====  节点 B  =====  节点 C
      CAN_H / CAN_L 共享总线
```

每个节点都可以发送，也都可以接收。节点收到一帧数据后，再根据帧 ID 判断这帧数据是不是自己需要处理的内容。

---

## 2. CAN 硬件结构

### 2.1 一条 CAN 总线有两根核心信号线

CAN 总线侧通常是两根线：

```text
CAN_H
CAN_L
```

这两根线组成一对**差分信号线**。接收端主要看的是 `CAN_H` 和 `CAN_L` 之间的电压差，而不是只看某一根线相对 GND 的电压。

差分通信的好处是：外界干扰通常会同时影响两根线，二者相减后干扰会被抵消一部分，所以 CAN 比普通单端信号更适合汽车、工业现场、机器人这类电磁环境复杂的场景。

### 2.2 一个 CAN 节点的组成

一个完整 CAN 节点通常包括：

```text
STM32 内部 CAN 控制器  <-->  CAN 收发器  <-->  CAN_H / CAN_L 总线
```

| 部分 | 作用 |
|---|---|
| CAN 控制器 | 位于 MCU 内部，负责 CAN 协议层面的组帧、仲裁、校验、收发邮箱/FIFO 等 |
| CAN 收发器 | 位于 MCU 和总线之间，把 `CAN_TX/CAN_RX` 逻辑信号转换成 `CAN_H/CAN_L` 差分信号 |
| CAN_H/CAN_L | 真正连接所有节点的总线信号线 |

注意：很多 STM32 内部有 CAN 控制器，但**不能说明它可以直接接到 `CAN_H/CAN_L`**。因为 MCU 引脚侧通常是：

```text
CAN_TX
CAN_RX
```

总线侧才是：

```text
CAN_H
CAN_L
```

中间必须经过 CAN 收发器，例如常见的 `TJA1050`、`SN65HVD230` 等模块。原始材料中的 `TGA1050` 应修正为常见型号 `TJA1050`。

---

## 3. 两种常见接线情况

### 3.1 开发板自带 CAN 收发器

如果开发板上已经集成 CAN 收发器，连接时只需要接总线侧信号：

```text
开发板 CAN_H  ->  总线 CAN_H
开发板 CAN_L  ->  总线 CAN_L
GND           ->  对方 GND（建议共地）
```

这种情况下，板子内部通常已经完成：

```text
STM32 CAN_TX/CAN_RX -> CAN 收发器 -> CAN_H/CAN_L
```

### 3.2 开发板没有 CAN 收发器

如果开发板没有板载 CAN 收发器，就要外接收发器模块：

```text
STM32 CAN_TX  ->  CAN 收发器 TXD
STM32 CAN_RX  ->  CAN 收发器 RXD
CAN 收发器 CAN_H  ->  总线 CAN_H
CAN 收发器 CAN_L  ->  总线 CAN_L
STM32 GND / 收发器 GND / 对方 GND 共地
```

最容易错的地方：

```text
错误：STM32 CAN_TX / CAN_RX 直接接 CAN_H / CAN_L
正确：STM32 CAN_TX / CAN_RX 先接 CAN 收发器，再由收发器接 CAN_H / CAN_L
```

---

## 4. 终端电阻

### 4.1 为什么要接终端电阻

CAN 总线两端通常需要各接一个：

$$
120\ \Omega
$$

终端电阻的作用是改善总线信号质量，减少信号反射，提高通信稳定性。尤其是总线较长、波特率较高、节点较多时，终端电阻更重要。

### 4.2 终端电阻接在哪里

终端电阻只接在**总线物理两端**。

例如三节点结构：

```text
[120Ω] 节点 A  =====  节点 B  =====  节点 C [120Ω]
```

- 节点 A 和节点 C 位于总线两端：需要终端电阻。
- 节点 B 是中间节点：不要再接终端电阻。

如果多个模块都默认焊了 `120 Ω`，一接上总线就可能导致等效电阻过小，进而影响通信。因此使用 CAN 模块前要看清楚：

- 模块是否自带 `120 Ω` 电阻。
- 是否可以通过跳帽/焊盘断开终端电阻。
- 当前模块在总线中是端点还是中间节点。

---

## 5. CAN 数据帧入门

CAN 是以**帧**为单位传输数据的。完整 CAN 帧内部有仲裁段、控制段、数据段、CRC 段、ACK 段等，入门阶段先抓住工程配置里最常用的几个字段。

### 5.1 帧 ID

标准 CAN 帧使用 `11 bit` 标识符，也就是标准 ID：

```text
范围：0x000 ~ 0x7FF
```

ID 可以理解为一帧数据的“名字”或“功能编号”。例如：

```text
0x123：测试数据
0x201：电机 1 控制命令
0x301：传感器反馈数据
```

CAN 更像“广播消息”：一帧数据发到总线上，所有节点都可能看到；节点根据 ID 判断是否处理。

### 5.2 波特率

同一条 CAN 总线上的所有节点必须使用相同波特率。常见值：

```text
125 kbps
250 kbps
500 kbps
1 Mbps
```

如果一个节点是 `500 kbps`，另一个节点是 `250 kbps`，基本无法正常通信。

### 5.3 采样点

CAN 在每个 bit 时间内会选择一个位置采样总线电平，这个位置叫**采样点**。常见推荐范围大约是：

$$
75\% \sim 85\%
$$

采样点过早或过晚都可能影响通信稳定性。入门实验中，只要计算结果落在这个范围附近，一般可以先用于验证通信。

### 5.4 数据长度 DLC

经典 CAN 一帧最多携带：

$$
8\ \text{Byte}
$$

HAL 中通常通过 `DLC` 指定数据长度。例如发送 8 字节：

```text
01 02 03 04 05 06 07 08
```

### 5.5 过滤器

CAN 总线共享通信线路，一个节点可能会收到很多不同 ID 的帧。过滤器用于决定哪些帧可以进入接收 FIFO。

入门测试可以先配置成“不过滤”，也就是尽量接收总线上的所有数据帧；等通信跑通后，再按 ID 精确过滤。

---

## 6. CubeMX 中的 CAN 配置主线

CubeMX 中启用 CAN 时，重点关注：

1. 选择并启用 `CAN1`。
2. 确认 `CAN_TX`、`CAN_RX` 引脚复用正确。
3. 确认这两个引脚确实连接到了 CAN 收发器。
4. 查看 CAN 控制器输入时钟。
5. 配置 `Prescaler`、`BS1/TS1`、`BS2/TS2`、`SJW`。
6. 生成工程后，在用户代码中配置过滤器并启动 CAN。

常见 CubeMX 参数名可能写作：

| 参数 | 含义 |
|---|---|
| `Prescaler` | CAN 时钟预分频系数 |
| `Time Quantum in Bit Segment 1` / `BS1` / `TS1` | 采样点前的时间段 |
| `Time Quantum in Bit Segment 2` / `BS2` / `TS2` | 采样点后的时间段 |
| `SJW` | 同步跳转宽度，用于重新同步 |

入门实验中，如果没有特殊要求，`SJW` 可先设为 `1`。

---

## 7. 波特率与采样点计算

### 7.1 波特率公式

STM32 bxCAN 常见计算方式：

$$
\text{BaudRate}=\frac{f_{\text{CAN}}}{\text{Prescaler}\times(1+TS1+TS2)}
$$

其中：

- $f_{\text{CAN}}$：CAN 控制器输入时钟。
- $\text{Prescaler}$：预分频系数。
- $TS1$：位时间段 1。
- $TS2$：位时间段 2。
- 公式中的 `1` 对应同步段 `Sync Segment`。

### 7.2 500 kbps 示例

假设：

```text
f_CAN = 42 MHz
Prescaler = 6
TS1 = 10
TS2 = 3
```

代入：

$$
\text{BaudRate}=\frac{42\,000\,000}{6\times(1+10+3)}
$$

先算分母：

$$
6\times(1+10+3)=6\times14=84
$$

所以：

$$
\text{BaudRate}=\frac{42\,000\,000}{84}=500\,000\ \text{bps}=500\ \text{kbps}
$$

### 7.3 采样点公式

$$
\text{Sample Point}=\frac{1+TS1}{1+TS1+TS2}\times100\%
$$

继续使用上面的参数：

$$
\text{Sample Point}=\frac{1+10}{1+10+3}\times100\%=\frac{11}{14}\times100\%\approx78.6\%
$$

`78.6%` 落在常见推荐范围内，可以作为入门实验配置。原始材料中出现过 `87.6%` 的说法，与该组参数不一致；按公式应为约 `78.6%`。

---

## 8. HAL 初始化流程

使用 HAL 库时，CAN 真正能工作前通常要完成：

```text
CubeMX 生成 MX_CAN_Init()
        ↓
配置 CAN 过滤器
        ↓
HAL_CAN_Start()
        ↓
开始发送 / 接收
```

### 8.1 接收全部 ID 的过滤器示例

下面示例用于入门测试：尽量接收所有标准帧/扩展帧。实际工程中应根据 ID 需求配置过滤规则。

```c
void CAN_User_Init(void)
{
    CAN_FilterTypeDef filter = {0};

    filter.FilterBank = 0;
    filter.FilterMode = CAN_FILTERMODE_IDMASK;
    filter.FilterScale = CAN_FILTERSCALE_32BIT;

    // ID 和 Mask 全为 0：入门测试时相当于不过滤，方便先确认通信链路。
    filter.FilterIdHigh = 0x0000;
    filter.FilterIdLow = 0x0000;
    filter.FilterMaskIdHigh = 0x0000;
    filter.FilterMaskIdLow = 0x0000;

    filter.FilterFIFOAssignment = CAN_RX_FIFO0;
    filter.FilterActivation = ENABLE;

    // 双 CAN 外设芯片才需要特别关注此项；单 CAN 入门实验通常保持 CubeMX/HAL 示例值即可。
    filter.SlaveStartFilterBank = 14;

    HAL_CAN_ConfigFilter(&hcan1, &filter);
    HAL_CAN_Start(&hcan1);
}
```

复习时记住两句话：

- 没有配置过滤器，CAN 可能启动了也收不到数据。
- 没有调用 `HAL_CAN_Start()`，CAN 外设不会真正开始工作。

---

## 9. CAN 发送流程

### 9.1 发送需要的核心函数

```c
HAL_CAN_AddTxMessage();
HAL_CAN_GetTxMailboxesFreeLevel();
```

| 函数 | 作用 |
|---|---|
| `HAL_CAN_AddTxMessage()` | 把待发送帧放入 CAN 发送邮箱 |
| `HAL_CAN_GetTxMailboxesFreeLevel()` | 查询发送邮箱空闲数量 |

STM32 CAN 控制器通常有 3 个发送邮箱。调用 `HAL_CAN_AddTxMessage()` 后，数据先进入邮箱，再由 CAN 控制器根据总线状态自动发送。

### 9.2 入门发送函数

```c
uint8_t CAN_Send(uint32_t id, uint8_t *data, uint8_t len)
{
    CAN_TxHeaderTypeDef tx_header = {0};
    uint32_t tx_mailbox;
    uint32_t tick_start;

    if (len > 8)
    {
        return 1;   // 经典 CAN 一帧最多 8 字节
    }

    tx_header.StdId = id;
    tx_header.ExtId = 0;
    tx_header.IDE = CAN_ID_STD;          // 标准帧
    tx_header.RTR = CAN_RTR_DATA;        // 数据帧
    tx_header.DLC = len;
    tx_header.TransmitGlobalTime = DISABLE;

    if (HAL_CAN_AddTxMessage(&hcan1, &tx_header, data, &tx_mailbox) != HAL_OK)
    {
        return 2;
    }

    // 入门实验可以短暂轮询；正式工程建议改成中断、状态机或带超时的非阻塞逻辑。
    tick_start = HAL_GetTick();
    while (HAL_CAN_GetTxMailboxesFreeLevel(&hcan1) != 3)
    {
        if (HAL_GetTick() - tick_start > 10)
        {
            return 3;   // 超时，避免死等
        }
    }

    return 0;
}
```

关键字段：

| 字段 | 作用 |
|---|---|
| `StdId` | 标准帧 ID，范围 `0x000 ~ 0x7FF` |
| `IDE = CAN_ID_STD` | 使用标准帧 |
| `RTR = CAN_RTR_DATA` | 发送数据帧，不是远程帧 |
| `DLC` | 数据长度，经典 CAN 最大 8 |
| `data` | 实际发送的数据数组 |

---

## 10. CAN 接收流程

### 10.1 接收需要的核心函数

```c
HAL_CAN_GetRxFifoFillLevel();
HAL_CAN_GetRxMessage();
```

| 函数 | 作用 |
|---|---|
| `HAL_CAN_GetRxFifoFillLevel()` | 判断接收 FIFO 里是否已有数据 |
| `HAL_CAN_GetRxMessage()` | 从接收 FIFO 取出一帧数据 |

CAN 控制器收到数据后，不会自动进入用户变量，而是先进入接收 FIFO。程序必须主动检查并取出。

### 10.2 入门接收函数

```c
uint8_t CAN_Receive(uint32_t *id, uint8_t *data, uint8_t *len)
{
    CAN_RxHeaderTypeDef rx_header = {0};

    if (HAL_CAN_GetRxFifoFillLevel(&hcan1, CAN_RX_FIFO0) == 0)
    {
        return 1;   // 当前没有新数据
    }

    if (HAL_CAN_GetRxMessage(&hcan1, CAN_RX_FIFO0, &rx_header, data) != HAL_OK)
    {
        return 2;   // 读取失败
    }

    *id = rx_header.StdId;
    *len = rx_header.DLC;

    return 0;
}
```

接收时重点看三件事：

```text
收到的 ID 是多少？
收到的数据长度是多少？
收到的数据内容是否与发送端一致？
```

---

## 11. 两块开发板互发测试

### 11.1 测试目标

两块板互发数据，验证四个方向：

1. 自己工程能发送。
2. 对方例程能接收。
3. 对方例程能发送。
4. 自己工程能接收。

原始材料中，一块板烧录自己写的 CAN 工程，另一块板烧录正点原子的 CAN 例程。这个方案适合入门验证，因为对方例程可以作为“已知较可靠”的参照。

### 11.2 自己发送，对方接收

流程：

1. 自己工程初始化 CAN。
2. 通过 shell 命令或按键触发发送。
3. 指定 CAN ID、数据长度和数据内容。
4. 对方开发板观察接收结果。
5. 如果收到的数据和发送数据一致，说明发送链路基本成功。

例如发送：

```text
ID: 0x123
Data: 01 02 03 04 05 06 07
```

对方能看到同样 ID 和数据，就说明自己工程发送成功、对方接收成功。

### 11.3 对方发送，自己接收

流程：

1. 对方开发板通过按键或例程发送 CAN 数据。
2. 自己工程轮询或中断接收 FIFO。
3. 打印收到的 ID、DLC、Data。
4. 对比数据是否一致。

调试时注意进制显示：

```text
十进制 10 = 十六进制 0x0A
十进制 15 = 十六进制 0x0F
十进制 16 = 十六进制 0x10
```

发送端和接收端显示格式不同，不一定代表数据错了，要先统一进制再判断。

---

## 12. 常见错误与排查顺序

### 12.1 高频易错点

| 错误 | 现象 | 纠正 |
|---|---|---|
| 没有 CAN 收发器 | 总线完全不通 | 确认 MCU 与 `CAN_H/CAN_L` 之间有收发器 |
| `CAN_TX/CAN_RX` 直接接 `CAN_H/CAN_L` | 无法通信，甚至可能损坏接口 | `CAN_TX/RX -> 收发器 -> CAN_H/L` |
| `CAN_H` 和 `CAN_L` 接反 | 通信失败 | 两端 `CAN_H` 对 `CAN_H`，`CAN_L` 对 `CAN_L` |
| 没有终端电阻 | 通信不稳定，波特率高时更明显 | 总线两端各接 `120 Ω` |
| 中间节点也接终端电阻 | 等效电阻过小，通信异常 | 只保留物理两端终端电阻 |
| 波特率不一致 | 完全收不到或错误帧增多 | 所有节点配置同一波特率 |
| 采样点不合适 | 偶发错误、距离稍长就不稳 | 先选 `75% ~ 85%` 左右 |
| 忘记配置过滤器 | 启动了也收不到 | 先配置“接收全部 ID”验证链路 |
| 忘记 `HAL_CAN_Start()` | CAN 不工作 | 过滤器配置后调用 `HAL_CAN_Start()` |
| 只启动 CAN，不读 FIFO | 数据到 FIFO 后没人取 | 调用 `HAL_CAN_GetRxFifoFillLevel()` 和 `HAL_CAN_GetRxMessage()` |

### 12.2 推荐排查顺序

CAN 不通时，按从硬件到软件的顺序查：

1. 板子是否真的有 CAN 收发器。
2. `CAN_H`、`CAN_L` 是否对应连接。
3. GND 是否共地。
4. 总线两端是否各有一个 `120 Ω` 终端电阻。
5. 两边波特率是否一致。
6. CubeMX 中 CAN 引脚复用是否对应实际硬件。
7. `Prescaler/TS1/TS2/SJW` 是否算出目标波特率和合理采样点。
8. 是否调用 `HAL_CAN_ConfigFilter()`。
9. 是否调用 `HAL_CAN_Start()`。
10. 发送 ID、DLC、数据内容是否符合预期。
11. 接收端是否真的从 FIFO 里取出了数据。
12. 打印显示是否存在十进制/十六进制误判。

---

## 13. 快速实践流程

从零跑通 CAN，可以按下面步骤：

1. 确认开发板是否带 CAN 收发器。
2. 没有收发器就外接 `TJA1050`、`SN65HVD230` 等模块。
3. 正确连接：
   - `CAN_TX -> 收发器 TXD`
   - `CAN_RX -> 收发器 RXD`
   - `收发器 CAN_H -> 总线 CAN_H`
   - `收发器 CAN_L -> 总线 CAN_L`
   - `GND` 共地
4. 总线两端接 `120 Ω` 终端电阻。
5. CubeMX 启用 `CAN1`。
6. 配置目标波特率，例如 `500 kbps`。
7. 计算并确认采样点，例如约 `78.6%`。
8. 生成工程。
9. 在用户代码中配置 CAN 过滤器。
10. 调用 `HAL_CAN_Start()`。
11. 用 `HAL_CAN_AddTxMessage()` 发送数据。
12. 用 `HAL_CAN_GetRxFifoFillLevel()` + `HAL_CAN_GetRxMessage()` 接收数据。
13. 两块板互发，确认 ID、DLC、Data 全部一致。

---

## 14. 一页速记

### 14.1 硬件主线

```text
STM32 CAN_TX/CAN_RX -> CAN 收发器 -> CAN_H/CAN_L 总线
```

不要把 `CAN_TX/CAN_RX` 直接接到 `CAN_H/CAN_L`。

### 14.2 终端电阻

```text
[120Ω] 节点 A ===== 节点 B ===== 节点 C [120Ω]
```

只在总线物理两端接，中间节点不要随便接。

### 14.3 入门配置五件套

| 配置 | 记忆点 |
|---|---|
| ID | 标准帧 `11 bit`，范围 `0x000 ~ 0x7FF` |
| 波特率 | 同一总线所有节点必须一致 |
| 采样点 | 常见取 `75% ~ 85%` 左右 |
| DLC | 经典 CAN 最多 `8 Byte` |
| 过滤器 | 入门先全接收，跑通后再按 ID 过滤 |

### 14.4 波特率公式

$$
\text{BaudRate}=\frac{f_{\text{CAN}}}{\text{Prescaler}\times(1+TS1+TS2)}
$$

示例：

```text
f_CAN = 42 MHz
Prescaler = 6
TS1 = 10
TS2 = 3
```

得到：

$$
\text{BaudRate}=500\ \text{kbps}
$$

### 14.5 采样点公式

$$
\text{Sample Point}=\frac{1+TS1}{1+TS1+TS2}\times100\%
$$

当 `TS1 = 10`、`TS2 = 3`：

$$
\text{Sample Point}\approx78.6\%
$$

### 14.6 HAL 函数速记

```c
// 初始化阶段
HAL_CAN_ConfigFilter(&hcan1, &filter);
HAL_CAN_Start(&hcan1);

// 发送
HAL_CAN_AddTxMessage(&hcan1, &tx_header, data, &tx_mailbox);
HAL_CAN_GetTxMailboxesFreeLevel(&hcan1);

// 接收
HAL_CAN_GetRxFifoFillLevel(&hcan1, CAN_RX_FIFO0);
HAL_CAN_GetRxMessage(&hcan1, CAN_RX_FIFO0, &rx_header, data);
```

---

## 15. 自测题

1. 为什么 STM32 有 CAN 控制器，也通常不能直接接 `CAN_H/CAN_L`？
2. `CAN_TX/CAN_RX` 与 `CAN_H/CAN_L` 分别位于哪一侧？
3. 一条 CAN 总线上有 4 个节点，终端电阻应该接几个？接在哪里？
4. 如果 `f_CAN = 42 MHz`，`Prescaler = 6`，`TS1 = 10`，`TS2 = 3`，波特率是多少？采样点是多少？
5. 经典 CAN 一帧最多能传几个字节？HAL 中用哪个字段设置？
6. 为什么入门测试时常把过滤器配置成“接收所有 ID”？
7. 如果已经 `HAL_CAN_Start()`，但还是收不到数据，软件上下一步应该检查什么？
8. 发送端显示 `0x0A`，接收端显示 `10`，这一定是错误吗？为什么？

### 参考答案

1. MCU 内部 CAN 控制器输出的是 `CAN_TX/CAN_RX` 逻辑信号，总线需要 `CAN_H/CAN_L` 差分信号，中间要经过 CAN 收发器转换。
2. `CAN_TX/CAN_RX` 在 MCU 与收发器之间；`CAN_H/CAN_L` 在收发器与总线之间。
3. 接 2 个，分别接在总线物理两端。
4. 波特率为 `500 kbps`；采样点约为 `78.6%`。
5. 最多 `8 Byte`；HAL 中用 `DLC` 设置。
6. 先排除过滤规则导致的接收问题，方便验证硬件和基础收发链路。
7. 检查过滤器是否配置、FIFO 是否有数据、是否调用 `HAL_CAN_GetRxMessage()` 取数据。
8. 不一定。`0x0A` 是十六进制，等于十进制 `10`。
