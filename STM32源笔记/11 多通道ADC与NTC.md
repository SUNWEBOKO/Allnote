# 11. 多通道 ADC 与 NTC 热敏电阻

> 本节重点：理解 ADC 规则组扫描模式如何在一次触发中依次转换多通道，掌握 DMA 自动搬运多通道结果的方法，以及 NTC 电阻到温度的换算链路。

---

## 本节核心问题

学完本节，需要能回答：

- 规则组（Regular Group）和扫描模式在多通道 ADC 中起什么作用？
- 多通道连续转换时，为什么数据容易被覆盖？DMA 如何解决这个问题？
- DMA 普通模式（Normal）和循环模式（Circular）与 ADC 连续模式如何搭配？
- NTC 温度换算的两步分别是什么？
- `Vrefint` 的作用是什么？怎么用它修正实际参考电压？

---

## 1. 多通道扫描模式

### 1.1 规则组

规则组可理解为"转换队列"：

```text
rank1 → rank2 → rank3 → rank4 → ...
```

每个 rank 指定一个通道，ADC 按 rank 顺序依次完成转换。

### 1.2 本节示例的 4 路通道

| Rank | 通道 | 信号源 |
|------|------|--------|
| 1 | 外部通道 | 电位器分压 |
| 2 | 外部通道 | NTC 热敏电阻分压 |
| 3 | 内部通道 | 片内温度传感器 |
| 4 | 内部通道 | Vrefint 内部参考电压 |

---

## 2. 为什么需要 DMA

### 2.1 问题

规则组**每次只有一个数据寄存器**承接转换结果。多通道连续转换时：

```text
CH1 完成 → 结果写入 DR → CH2 完成 → 覆盖 DR → CH3 完成 → 覆盖 DR → ...
```

程序来不及读取某个通道的结果时，它就被下一个通道的结果覆盖了。

### 2.2 DMA 的优势

DMA 按转换完成的顺序，自动将每次结果搬到内存数组：

```text
CH1 → DMA 搬运到 values[0]
CH2 → DMA 搬运到 values[1]
CH3 → DMA 搬运到 values[2]
CH4 → DMA 搬运到 values[3]
```

数组下标天然与 rank 对齐，不再需要手动区分"当前读的是哪一路"。

---

## 3. CubeMX 配置

### 3.1 ADC 配置

| 配置项 | 设置 |
|--------|------|
| ADC1 通道数 | 4 个 rank |
| 扫描模式 | 使能 |
| 各通道采样时间 | 按通道特性调整（内部通道不能太短） |

### 3.2 DMA 配置

| 配置项 | 设置 |
|--------|------|
| 方向 | `Peripheral → Memory` |
| 外设地址自增 | 不使能 |
| 内存地址自增 | 使能 |
| 数据宽度 | `Half Word (16-bit)`（12-bit ADC 足够） |

### 3.3 DMA 模式选择

| DMA 模式 | 与 ADC 模式的搭配 | 行为 |
|----------|------------------|------|
| Normal | 非连续转换 | 搬完 4 个结果后停，需再次触发 |
| Circular | 连续转换 | 搬满后自动回到数组开头，持续采集 |

---

## 4. HAL 代码实现

### 4.1 基本流程

```c
uint16_t adc_values[4];

HAL_ADCEx_Calibration_Start(&hadc1);                          // 校准
HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_values, 4);          // 启动
```

### 4.2 DMA 传输完成回调

```c
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1)
    {
        // adc_values[0] ~ adc_values[3] 对应 rank1 ~ rank4
        float v_pot   = adc_values[0] * 3.3f / 4095.0f;
        float v_ntc   = adc_values[1] * 3.3f / 4095.0f;
        // adc_values[2] = 内部温度
        // adc_values[3] = Vrefint
    }
}
```

---

## 5. NTC 温度换算

两步换算：

### 5.1 第一步：ADC → NTC 电阻

若电路是“上拉电阻接 $V_{\text{ref}}$、NTC 接地”，电阻换算为：

$$
R_{\text{ntc}} = R_{\text{pullup}} \times \frac{ADC}{4095 - ADC}
$$

### 5.2 第二步：电阻 → 温度（Beta 公式）

$$
\frac{1}{T_K} = \frac{1}{T_0} + \frac{\ln(R_{\text{ntc}} / R_0)}{B}
$$

$$
T_C = T_K - 273.15
$$

其中 $R_0$、$B$ 是 NTC 规格书参数，$R_{\text{pullup}}$ 是电路上拉电阻，$T_K$ 为开尔文温度，$T_C$ 为摄氏温度。

---

## 6. 使用 Vrefint 修正参考电压

固定按 3.3V 换算存在误差（供电波动、线路压降）。利用内部 Vrefint（约 1.2V 基准）反推实际 Vref：

$$
V_{\text{ref,actual}} \approx \frac{1.2 \times 4095}{ADC_{\text{vrefint}}}
$$

$$
V_{\text{channel}} \approx \frac{ADC_{\text{channel}}}{4095} \times V_{\text{ref,actual}}
$$

---

## 7. 高频易错点

1. **DMA 宽度设为 Word 但数组还是 uint16_t**。改了宽度后数组类型必须同步改为 `uint32_t`。

2. **多通道顺序与数组下标不对应**。依赖 rank 顺序判断，一旦 rank 顺序变了就必须调整数组访问逻辑。

3. **内部通道采样时间不足**。内部温度传感器和 Vrefint 需要更长的采样时间。

4. **连续模式下 DMA 用 Normal 模式**。每次 DMA 搬完一帧就停，无法持续采集。

5. **NTC 公式中的参数与实际器件不匹配**。`R0`、`B` 值以 NTC 规格书为准，不同型号差别很大。

---

## 8. 一页速记

### 多通道核心链路
```text
规则组 rank → 扫描模式 → DMA 自动搬运 → 数组按 rank 对齐
```

### 连续采集推荐搭配
```text
ADC Continuous + DMA Circular → 数组自动循环更新
```

### 温度换算两步
```text
ADC → $R_{\text{ntc}}$ → Beta 公式 → $T_C$
```

### 电压修正
```text
Vrefint → Vref_actual → 更精确的通道电压
```

### 核心 API
| 函数 | 用途 |
|------|------|
| `HAL_ADC_Start_DMA(hadc, buf, len)` | ADC + DMA 启动 |
| `HAL_ADC_ConvCpltCallback()` | 转换完成回调 |

### 最重要的一句话
> 多通道 ADC 的核心挑战不是"怎么同时采"，而是"怎么分清楚每个结果属于哪个通道"——DMA 加数组恰好解决了这个问题。

---

## 9. 自测题

1. 规则组的 rank 顺序有什么作用？
2. 为什么多通道连续转换时不用 DMA 会导致数据覆盖？
3. DMA Normal 模式和 Circular 模式分别适合什么场景？
4. NTC 温度换算为什么是两步？Beta 公式中的 R0 和 B 从哪里获得？
5. Vrefint 的作用是什么？为什么固定按 3.3V 换算可能不准？
6. 如果发现 ADC 各通道的数据和 rank 顺序对不上，应该检查哪里？
