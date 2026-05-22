# 20. RTC 实时时钟

> 本节重点：理解 STM32F1 的 RTC 在后备域里持续计数的原理，掌握以 UNIX 时间戳为核心的驱动模型——struct tm ↔ timestamp ↔ RTC_CNT。

---

## 本节核心问题

学完本节，需要能回答：

- RTC 为什么能在复位或主电源掉电后继续走时？
- 本驱动为什么把 RTC 计数器当作 UNIX 时间戳使用？
- `WB_RTC_SetTime()` 和 `WB_RTC_GetTime()` 分别怎样读写时间？
- 备份寄存器 `BKP_DR1` 怎样避免每次复位都重设时间？
- 为什么要修改 CubeMX 生成的 `MX_RTC_Init()`？

---

## 1. RTC 的本质

RTC（Real Time Clock）是一个**低功耗秒计数系统**：

```text
RTC 时钟源 → 预分频得到 1Hz → RTC 计数器每秒加 1
```

在 STM32F1 中，RTC 和备份寄存器位于**后备域**。只要后备域有电，RTC 就可以在主程序复位或主电源掉电后继续保存时间。

本驱动的核心设计：

```text
RTC 计数器 = UNIX timestamp
struct tm ⇔ timestamp ⇔ RTC_CNT
```

驱动不使用 HAL 的日期/时间字段，而是直接读写 RTC 的 32 位计数器。

---

## 2. RTC 掉电保持的条件

| 条件 | 说明 |
|------|------|
| 后备域供电 | 主电源 VDD 掉电后，由电池或备用电源维持 |
| RTC 时钟源 | 通常使用 LSE（32.768kHz 外部低速晶振），预分频为 1Hz |

```text
普通复位：RTC 时间不应重置
主电源断开 + 后备电池：RTC 继续走时
后备电池也断开：RTC 计数器和备份寄存器全部丢失
```

### 2.1 STM32 低功耗模式与 RTC

STM32F1 的三种低功耗模式下，RTC 的工作状态不同：

| 模式 | CPU | 外设 | RTC | 唤醒方式 |
|------|-----|------|-----|----------|
| **Sleep** | 暂停 | 保持 | 正常工作 | 任意中断 |
| **Stop** | 停止 | 大部分停止 | **可继续工作** | EXTI 中断（含 RTC 闹钟） |
| **Standby** | 掉电 | 全部掉电 | 可继续（后备域供电） | RTC 闹钟 / 外部复位 |

在实际项目中，RTC 最常见的低功耗用途是：

1. **定时唤醒测量**：进入 Stop 模式 → RTC 闹钟定时唤醒 → 采集传感器数据 → 发完后继续睡眠
2. **掉电时间保持**：主电源断掉后 RTC 在电池下继续走时，重新上电后时间仍然正确

**关键理解**：RTC 的后备域独立于主电源域。即使在 Standby 模式下主电源完全掉电，只要 VBAT 引脚有电（纽扣电池），RTC 和备份寄存器仍能保持。

---

## 3. 驱动库结构

### 3.1 对外接口

| 函数 | 作用 |
|------|------|
| `WB_RTC_Init(void)` | 初始化 RTC，检查备份寄存器标记 |
| `WB_RTC_SetTime(struct tm *time)` | 设置 RTC 时间 |
| `WB_RTC_GetTime(void)` | 获取当前时间，返回 `struct tm *` |

### 3.2 依赖

- `rtc.h`：全局 RTC 句柄 `hrtc`
- `time.h`：`struct tm`、`mktime()`、`localtime()`
- `stm32f1xx_hal_rtc_ex.h`：备份寄存器操作

---

## 4. 时间表示：struct tm 与 UNIX 时间戳

### 4.1 struct tm

```c
struct tm time = {
    .tm_year = 2026 - 1900,   // 年份从 1900 开始
    .tm_mon  = 4,              // 0=1月, 4=5月
    .tm_mday = 1,
    .tm_hour = 14,
    .tm_min  = 0,
    .tm_sec  = 0,
};
```

注意两个易错字段：

| 字段 | 规则 | 示例 |
|------|------|------|
| `tm_year` | 从 1900 算起 | 2026 年写 `2026 - 1900` |
| `tm_mon` | 从 0 开始 | 5 月写 `4` |

### 4.2 UNIX 时间戳

从 `1970-01-01 00:00:00` 开始累计的秒数。

| 转换方向 | 函数 | 用途 |
|----------|------|------|
| struct tm → 秒数 | `mktime()` | 设置时间时用 |
| 秒数 → struct tm | `localtime()` | 读取时间时用 |

---

## 5. 底层计数器读写

### 5.1 读取：防止撕裂

RTC 计数器由 `CNTH`（高 16 位）和 `CNTL`（低 16 位）组成。读时可能跨秒变化：

```text
1. 读 CNTH → high1
2. 读 CNTL
3. 读 CNTH → high2
4. 若 high1 ≠ high2，说明进位发生，用 high2 重新组合
```

### 5.2 写入：写保护与 RTOFF

```text
1. RTC_EnterInitMode()：等待 RTOFF，关写保护
2. 写 CNTH（高 16 位）
3. 写 CNTL（低 16 位）
4. RTC_ExitInitMode()：开写保护，等待完成
```

```c
WRITE_REG(hrtc->Instance->CNTH, TimeCounter >> 16U);
WRITE_REG(hrtc->Instance->CNTL, TimeCounter & RTC_CNTL_RTC_CNT);
```

---

## 6. 备份寄存器与初始化标记

驱动定义初始化标记：

```c
#define RTC_INIT_FLAG 0x2333
```

`WB_RTC_Init()` 的核心逻辑：

```text
读 BKP_DR1
  ├─ 等于 0x2333 → 跳过初始化，不重设时间
  └─ 不等于 0x2333 → 初始化 RTC → 设默认时间 → 写 0x2333
```

解决的问题：

- 避免每次复位都把时间重设成固定值
- 避免复位时重复初始化 RTC 导致走时短暂停顿
- 用后备寄存器区分"第一次上电"和"普通复位"

---

## 7. 为什么要改 MX_RTC_Init()

```c
void MX_RTC_Init(void)
{
    hrtc.Instance = RTC;
    hrtc.Init.AsynchPrediv = RTC_AUTO_1_SECOND;
    hrtc.Init.OutPut = RTC_OUTPUTSOURCE_ALARM;
    WB_RTC_Init();  // 由 WB_RTC_Init 决定是否调 HAL_RTC_Init()
    return;

    /* CubeMX 原本的 HAL_RTC_Init() 不再每次都执行 */
}
```

- `hrtc` 基本参数仍在 `MX_RTC_Init()` 中配置
- 是否调用 `HAL_RTC_Init()` 交给 `WB_RTC_Init()` 根据备份寄存器决定
- 注意 CubeMX 重新生成代码可能覆盖此修改

---

## 8. 典型使用流程

```c
// 初始化（内部判断是否首次）
MX_RTC_Init();

// 设置时间
struct tm t = {
    .tm_year = 2026 - 1900,
    .tm_mon  = 4,
    .tm_mday = 1,
    .tm_hour = 14,
    .tm_min  = 0,
    .tm_sec  = 0,
};
WB_RTC_SetTime(&t);

// 读取时间
struct tm *now = WB_RTC_GetTime();
printf("%04d-%02d-%02d %02d:%02d:%02d\r\n",
       now->tm_year + 1900,
       now->tm_mon + 1,
       now->tm_mday,
       now->tm_hour,
       now->tm_min,
       now->tm_sec);
```

---

## 9. 高频易错点

1. **每次复位都重设时间**。没有用备份寄存器做初始化标记。

2. **忘记改 `MX_RTC_Init()`**。每次复位都 `HAL_RTC_Init()`，可能重置时间或影响走时。

3. **`tm_year` 和 `tm_mon` 理解错误**。`tm_year` 从 1900 起算，`tm_mon` 从 0 开始。

4. **写 RTC 计数器前不等待 RTOFF**。不检查上一次写操作是否完成就写入新值。

5. **读高低位时不防进位**。可能读到撕裂值（高低位来自不同秒）。

6. **后备电池断开后还期待时间保持**。后备域没电，RTC 和 BKP 全部丢失。

7. **长期保存 `localtime()` 返回的指针**。它指向库内部静态缓冲区，后续调用会被覆盖。

---

## 10. 一页速记

### 驱动模型
```text
struct tm ⇔ UNIX timestamp ⇔ RTC_CNT
```

### 设置时间
```text
mktime() 转秒数 → 写 CNTH/CNTL
```

### 读取时间
```text
读 CNTH/CNTL → localtime() 转 struct tm
```

### 初始化标记
```text
BKP_DR1 = 0x2333
读到 0x2333 → 跳过 HAL_RTC_Init() 和默认设时
```

### 掉电保持前提
```text
后备域有电 + RTC 时钟源正常
```

### 最重要的一句话
> RTC 不是一个"时钟芯片"，而是一个"秒计数器"——真正让 RTC 变得直观的是驱动层的时间戳转换逻辑。

---

## 11. 自测题

1. 本驱动为什么不用 HAL 的日期时间字段，而直接读写 RTC 计数器？
2. `WB_RTC_SetTime()` 从 struct tm 到 RTC 计数器经历了哪几步？
3. `WB_RTC_GetTime()` 返回的是 struct tm 的指针，使用上需要注意什么？
4. 读取 CNTH/CNTL 时为什么要读两次高位？
5. 写 RTC 计数器前后为什么要处理写保护和 RTOFF？
6. `RTC_INIT_FLAG = 0x2333` 写在哪里？解决什么问题？
7. 为什么需要修改 `rtc.c` 中的 `MX_RTC_Init()`？
8. `tm_year = 2026 - 1900`、`tm_mon = 4` 分别表示哪一年哪一月？
