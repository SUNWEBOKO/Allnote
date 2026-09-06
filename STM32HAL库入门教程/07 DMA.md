# STM32F103 DMA：从数据搬运到 ADC 多通道采集

## 本章闭环

DMA（Direct Memory Access，直接存储器访问）不是一个独立产生数据的外设，而是一套按既定规则搬运数据的硬件。CPU 先告诉 DMA“从哪里取、送到哪里、每次搬多宽、总共搬几次”，随后由外设请求或软件启动搬运；传输结束后，CPU 再读取结果或处理完成事件。

本章围绕三条逐步扩展的链路展开：

```text
内存数组 -> DMA -> 内存数组

ADC 规则组 -> ADC1->DR -> DMA -> 多通道数组

定时器 TRGO -> ADC 扫描 -> DMA 缓冲区 -> 温度/光照等物理量
```

完成本章后，应能：

- 解释 DMA 与轮询、中断之间的区别；
- 根据数据流确定传输方向、地址、自增方式和数据宽度；
- 区分 Normal 与 Circular 模式，并知道内存到内存模式不能使用 Circular；
- 使用 HAL 完成一次内存到内存复制；
- 使用 ADC 扫描模式与 DMA 采集多个通道；
- 根据一致性和采样周期要求选择单帧、连续或定时器触发架构；
- 沿“请求—通道—地址—计数—中断—缓冲区”链路定位故障。

默认芯片为常见的 STM32F103C8T6，开发环境为 STM32CubeMX、STM32CubeIDE 或 Keil 与 STM32 HAL 库。开始前应已掌握 C 数组与指针、GPIO 模拟输入、ADC 规则组和基本中断概念。

## 1. 为什么需要 DMA

### 1.1 CPU 搬运数据的代价

以串口发送为例，若不用 DMA，CPU 需要反复完成：

1. 等待发送数据寄存器空；
2. 从内存读取一个字节；
3. 把字节写入串口数据寄存器；
4. 更新数组下标；
5. 重复以上过程。

ADC 多通道扫描也类似。每个 Rank 转换完成后，结果都进入同一个 ADC 数据寄存器。若 CPU 没有及时读取，下一通道的结果可能覆盖前一结果。

CPU 当然可以通过轮询或中断完成这些工作，但当数据量大、请求频繁或采样周期严格时，CPU 会把大量时间花在机械搬运上。DMA 的价值正是把这类重复操作交给硬件。

### 1.2 轮询、中断与 DMA 的分工

| 方式 | CPU 做什么 | 适用场景 | 主要代价 |
| --- | --- | --- | --- |
| 轮询 | 一直检查状态并亲自读写数据 | 低频、短小、流程简单 | 等待期间难做其他任务 |
| 中断 | 每次事件到来后进入 ISR，CPU 亲自读写数据 | 事件频率不高、每次处理量小 | 高频事件会产生大量中断开销 |
| DMA | CPU 配置一次，DMA 按请求搬运一批数据 | 连续采样、串口收发、SPI 数据流 | 配置与缓冲区管理更复杂 |

DMA 减少的是 CPU 参与每一次搬运的次数，并不会凭空增加总线带宽。DMA、CPU 和其他主设备仍可能竞争总线，因此“使用 DMA”不等于“传输没有成本”。

### 1.3 什么时候不必使用 DMA

下面这些任务通常直接轮询或中断更简单：

- 偶尔读取一个 ADC 值；
- 只发送几个配置字节；
- 数据规模很小，而 DMA 配置时间超过实际复制时间；
- 业务逻辑必须逐字节立即判断，无法形成批量缓冲区。

判断标准不是“外设支不支持 DMA”，而是“DMA 是否真正减少 CPU 重复工作并改善时间确定性”。

## 2. DMA 如何完成一次搬运

### 2.1 CPU 负责配置，DMA 负责执行

一次完整传输可分成五步：

1. CPU 配置源地址、目的地址、方向、宽度、自增、数量、模式和优先级；
2. CPU 使能 DMA 通道；
3. 软件或外设产生 DMA 请求；
4. DMA 完成一次数据读写，并更新地址与剩余计数；
5. 计数归零后置位完成标志，按配置产生传输完成中断。

可以把 DMA 配置理解为一张搬运单：

| 搬运单内容 | DMA 配置 |
| --- | --- |
| 从哪里取 | 外设地址或源内存地址 |
| 送到哪里 | 外设地址或目的内存地址 |
| 每箱多大 | Byte、Half Word、Word |
| 地址是否后移 | Peripheral/Memory Increment |
| 总共搬几箱 | 传输数量 |
| 搬完是否重来 | Normal/Circular |
| 多个请求谁先走 | 通道优先级 |

### 2.2 “外设地址”不一定真是外部设备

DMA 通道有“外设端”和“存储器端”两组地址寄存器，这是控制器接口的命名。常见数据流为：

```text
外设 -> 内存：ADC1->DR -> adc_values[]
内存 -> 外设：tx_buffer[] -> USARTx->DR
内存 -> 内存：source[] -> destination[]
```

在内存到内存模式中，两端实际都可以指向存储空间，只是仍分别填写到 DMA 的两侧地址寄存器中。

### 2.3 DMA 请求决定“何时搬”

DMA 不会无条件地高速覆盖外设寄存器。外设通常在“已经可以接收下一项”或“已经产生一个新数据”时发出请求：

- USART 发送数据寄存器空：请求 DMA 写入下一个发送字节；
- USART 收到一个字节：请求 DMA 把接收寄存器内容搬入数组；
- ADC 完成一次转换：请求 DMA 把 `ADC1->DR` 搬入数组；
- 定时器发生更新或捕获事件：请求 DMA 更新定时器寄存器或保存数据。

因此，一个 DMA 项的基本节拍是：

```text
外设事件 -> DMA 请求 -> 搬运一项 -> 剩余计数减 1
```

内存到内存没有外设请求，通常由软件使能通道后开始连续执行。

### 2.4 STM32F103 的通道映射

STM32F103C8T6 只有 DMA1，DMA1 包含 7 个通道。某个外设的 DMA 请求接到哪个通道，由芯片内部硬件映射决定，不能任意改接。例如 ADC1 的请求映射到 DMA1 Channel 1。

CubeMX 会根据所选外设自动选择通道，但仍应检查：

- 两个外设是否占用了同一个 DMA 通道；
- 传输方向是否正确；
- NVIC 中断是否为所用通道开启；
- 目标芯片是否真的具有 DMA2 或所需通道。

同一控制器收到多个请求时，会根据软件优先级和通道号规则仲裁。优先级只能决定冲突时谁先服务，不能提高外设本身的数据产生速度。

## 3. 八个关键配置项

### 3.1 传输方向

方向由数据流决定：

| 应用 | 方向 |
| --- | --- |
| ADC 采样 | Peripheral to Memory |
| USART 接收 | Peripheral to Memory |
| USART 发送 | Memory to Peripheral |
| 数组复制 | Memory to Memory |

先画出箭头，再选择方向，比死记 CubeMX 选项更可靠。

### 3.2 源地址与目的地址

地址必须指向实际参与传输的数据位置：

- ADC 外设端：`&ADC1->DR`；
- 串口发送外设端：对应 USART 数据寄存器；
- 内存端：数组首地址；
- 内存复制：源数组和目的数组首地址。

HAL 外设驱动通常会替你填写外设寄存器地址。例如调用 `HAL_ADC_Start_DMA()` 时，只需提供接收数组和传输数量。

### 3.3 数据宽度

STM32F1 DMA 常用三种宽度：

| CubeMX 名称 | 位宽 | 常见 C 类型 |
| --- | ---: | --- |
| Byte | 8 bit | `uint8_t` |
| Half Word | 16 bit | `uint16_t` |
| Word | 32 bit | `uint32_t` |

ADC 为 12 位结果，使用 Half Word 即可；USART 一般逐字节收发，通常使用 Byte。初学阶段应让外设宽度、内存宽度和数组元素类型匹配。

宽度不匹配可能发生截断、扩展或地址步长与预期不一致。除非明确需要数据打包或拆包，否则不要依赖这些隐式行为。

### 3.4 地址自增

每搬运一项后，DMA 可以让地址按数据宽度自动前移。

以 ADC 扫描四个 Rank 为例：

```text
外设端：ADC1->DR -> ADC1->DR -> ADC1->DR -> ADC1->DR
内存端：values[0] -> values[1] -> values[2] -> values[3]
```

因此：

- 外设地址固定：Peripheral Increment Disable；
- 内存地址递增：Memory Increment Enable。

若忘记开启内存自增，所有 ADC 结果会反复覆盖 `values[0]`。

内存到内存复制数组时，两端通常都需要自增。

### 3.5 传输数量

传输数量表示“搬运多少项”，不是字节总数。若宽度为 Half Word、数量为 4，实际搬运：

$$4\times 2\,\text{Byte}=8\,\text{Byte}$$

ADC 扫描的 DMA 数量通常应等于接收数组元素数。数组有 4 个 `uint16_t` 元素时，传入 `4`，不能传入 `sizeof(adc_values)` 得到的 `8`。

更稳妥的写法是：

```c
#define ARRAY_LEN(a) (sizeof(a) / sizeof((a)[0]))

HAL_ADC_Start_DMA(&hadc1,
                  (uint32_t *)adc_values,
                  ARRAY_LEN(adc_values));
```

### 3.6 Normal 与 Circular

**Normal 模式**：

- 计数归零后停止；
- 缓冲区保持不再变化；
- 需要下一批数据时，由软件重新启动；
- 适合单帧采集、命令式收发和需要稳定快照的任务。

**Circular 模式**：

- 计数归零后自动重装地址和数量；
- 继续覆盖同一缓冲区；
- 适合连续 ADC、持续串口接收和周期波形输出；
- CPU 读取缓冲区时必须考虑 DMA 正在同时改写。

> [!important]
> STM32F1 的 Memory-to-Memory 模式不能与 Circular 模式同时使用。需要重复复制时，应在一次 Normal 传输完成后由软件重新启动。

### 3.7 优先级

优先级有 Low、Medium、High、Very High 四档。它只在多个 DMA 请求竞争时参与仲裁。

设置原则：

- 不能丢样的高速 ADC、定时器波形更新可设较高；
- 普通串口日志可设较低；
- 不要把所有通道都设为 Very High，否则失去区分意义；
- 优先级不能修复通道冲突、带宽不足或错误的数据宽度。

### 3.8 中断

常见 DMA 中断事件包括：

- Half Transfer：传输到缓冲区一半；
- Transfer Complete：全部传输完成；
- Transfer Error：传输错误。

中断的作用是通知 CPU“某个阶段已经完成”，真正的数据搬运仍由 DMA 执行。回调中应只做置标志、切换缓冲区等短操作，OLED 刷屏、串口格式化和浮点运算应放到主循环或任务中。

## 4. CubeMX 与 HAL 的对应关系

### 4.1 CubeMX 配置链

配置 DMA 时建议按以下顺序检查：

1. 先启用产生或消费数据的外设；
2. 在外设的 DMA Settings 中添加请求；
3. 确认自动选择的 DMA 控制器与通道；
4. 设置方向；
5. 设置 Peripheral/Memory Increment；
6. 设置两端数据宽度；
7. 选择 Normal 或 Circular；
8. 设置优先级；
9. 若使用回调，打开对应 DMA 通道的 NVIC 中断；
10. 生成代码后检查 DMA 初始化顺序和 IRQ Handler。

CubeMX 生成的 `MX_DMA_Init()` 通常负责：

- 打开 DMA 控制器时钟；
- 配置 NVIC 优先级；
- 使能 DMA 通道中断。

外设的 MSP 初始化还会用 `__HAL_LINKDMA` 把外设句柄与 DMA 句柄关联。若手工移动或删除生成代码，可能出现 DMA 已初始化但外设找不到 DMA 句柄的情况。

### 4.2 常用 HAL API

| API | 作用 |
| --- | --- |
| `HAL_DMA_Start()` | 启动普通 DMA 传输，不使用中断通知 |
| `HAL_DMA_Start_IT()` | 启动 DMA 并允许中断通知 |
| `HAL_DMA_PollForTransfer()` | 轮询等待半传输或全传输完成 |
| `HAL_DMA_IRQHandler()` | 在 DMA IRQ Handler 中处理标志并调用回调 |
| `HAL_ADC_Start_DMA()` | 启动 ADC，并把 ADC 结果交给 DMA |
| `HAL_ADC_Stop_DMA()` | 停止 ADC DMA 采集 |

外设 DMA API 往往已经封装了通道配置、外设地址和回调链。优先使用 `HAL_ADC_Start_DMA()`、`HAL_UART_Transmit_DMA()` 等外设接口，不要在已有 HAL 封装时重复手工写寄存器。

### 4.3 ADC 完成回调从哪里来

ADC 使用 DMA 时，完成事件的调用链是：

```text
DMA1 Channel 1 传输完成
-> DMA1_Channel1_IRQHandler()
-> HAL_DMA_IRQHandler()
-> HAL 内部 ADC DMA 完成处理
-> HAL_ADC_ConvCpltCallback()
```

因此，`HAL_ADC_ConvCpltCallback()` 没有执行时，不仅要查 ADC，也要查 DMA1 Channel 1 的 NVIC 和 IRQ Handler。

## 5. 实验一：内存到内存单次复制

### 5.1 实验目标

使用 DMA 把 `source[8]` 复制到 `destination[8]`，传输结束后逐项比较，确认 DMA 配置正确。

这个实验只用于建立 DMA 心智模型。对于几十字节的小数组，CPU 的 `memcpy()` 往往更简单，甚至更快；DMA 更适合大块数据或 CPU 可以并行处理其他任务的场景。

### 5.2 CubeMX 配置

在 DMA 中添加 Memory-to-Memory 通道，示例设置如下：

| 项目 | 设置 |
| --- | --- |
| Mode | Normal |
| Direction | Memory to Memory |
| Source Increment | Enable |
| Destination Increment | Enable |
| Source Data Width | Word |
| Destination Data Width | Word |
| Priority | Low |

不同 CubeMX 版本对两端的命名可能仍显示 Peripheral/Memory。只要核对生成的源地址、目的地址、自增和宽度即可。

### 5.3 HAL 代码

CubeMX 生成的句柄名可能类似 `hdma_memtomem_dma1_channel1`，以实际工程为准。

```c
#include "main.h"
#include <stdint.h>

#define COPY_COUNT 8U

uint32_t source[COPY_COUNT] =
{
    0x11111111U, 0x22222222U, 0x33333333U, 0x44444444U,
    0x55555555U, 0x66666666U, 0x77777777U, 0x88888888U
};

uint32_t destination[COPY_COUNT] = {0};
volatile uint8_t copy_ok = 0U;

static void DMA_CopyOnce(void)
{
    HAL_StatusTypeDef status;
    uint32_t i;

    status = HAL_DMA_Start(&hdma_memtomem_dma1_channel1,
                           (uint32_t)source,
                           (uint32_t)destination,
                           COPY_COUNT);
    /* 传输数量按元素计数，不是按字节计数。 */

    if (status != HAL_OK)
    {
        Error_Handler();
    }

    status = HAL_DMA_PollForTransfer(&hdma_memtomem_dma1_channel1,
                                     HAL_DMA_FULL_TRANSFER,
                                     HAL_MAX_DELAY);

    if (status != HAL_OK)
    {
        Error_Handler();
    }

    copy_ok = 1U;
    for (i = 0U; i < COPY_COUNT; i++)
    {
        if (destination[i] != source[i])
        {
            copy_ok = 0U;
            break;
        }
    }
}
```

在所有 `MX_xxx_Init()` 完成后调用一次：

```c
DMA_CopyOnce();
```

调试器中应看到：

- `destination[]` 与 `source[]` 完全相同；
- `copy_ok == 1`；
- DMA 通道剩余传输计数归零。

### 5.4 重复复制的正确方式

若源数组更新后需要再次复制，应等待前一轮完成，再调用一次 `HAL_DMA_Start()`。Normal 模式下每次启动完成一批数据：

```c
while (1)
{
    source[0]++;
    DMA_CopyOnce();
    HAL_Delay(1000);
}
```

不要把 Memory-to-Memory 改为 Circular。循环复制不仅不符合 STM32F1 DMA 的使用限制，也容易让 DMA 持续占用总线并反复覆盖目的数组。

## 6. 实验二：ADC 扫描加 DMA 单帧采集

### 6.1 为什么先学习单帧模式

初学多通道 ADC 时，最容易混淆的是：

- 数组下标与 Rank 对不上；
- DMA 还在写，CPU 就开始读；
- Continuous 与 Circular 只打开了一个；
- 在中断中执行大量显示和换算。

因此先采用一条边界清楚的链路：

```text
启动一次 ADC DMA
-> ADC 按 Rank 扫描一轮
-> DMA 填满数组
-> DMA 自动停止
-> 回调只置位
-> 主循环处理稳定数组
-> 软件重新启动下一轮
```

此时 DMA 停止后数组不会继续变化，最适合验证通道顺序和数据处理。

### 6.2 接线与 Rank 规划

一种四外部通道实验可使用：

| Rank | ADC 通道 | 示例输入 | 数组位置 |
| ---: | --- | --- | --- |
| 1 | IN0 / PA0 | 电位器 | `adc_values[0]` |
| 2 | IN1 / PA1 | 光敏分压 | `adc_values[1]` |
| 3 | IN2 / PA2 | NTC 分压 | `adc_values[2]` |
| 4 | IN3 / PA3 | 红外接收分压 | `adc_values[3]` |

也可以按开发板原理图配置为电位器、NTC、片内温度传感器和 VREFINT。无论选哪些通道，都必须先固定 Rank，再固定数组含义；数组顺序跟随 Rank，不跟随通道号大小。

所有外部模拟量必须满足：

- 与开发板共地；
- 输入电压不超出允许范围；
- GPIO 配置为 Analog；
- 分压阻值与采样时间匹配；
- 传感器接法以原理图为准。

### 6.3 ADC 与 DMA 配置

ADC1：

1. 开启所需通道；
2. Number of Conversion 设为 `4`；
3. 设置 Rank 1 到 Rank 4；
4. Scan Conversion Mode 开启；
5. Continuous Conversion Mode 关闭；
6. 外部触发先使用 Software Start；
7. 为每个通道设置足够的采样时间；
8. 检查 ADC 时钟不超过目标芯片限制。

DMA：

| 项目 | 设置 |
| --- | --- |
| Request | ADC1 |
| Channel | DMA1 Channel 1 |
| Direction | Peripheral to Memory |
| Peripheral Increment | Disable |
| Memory Increment | Enable |
| Peripheral Data Width | Half Word |
| Memory Data Width | Half Word |
| Mode | Normal |
| NVIC | Enable |

### 6.4 最小完整代码

```c
#include "main.h"
#include <stdint.h>

#define ADC_CHANNEL_COUNT 4U

uint16_t adc_values[ADC_CHANNEL_COUNT] = {0};
volatile uint8_t adc_frame_ready = 0U;
volatile uint8_t adc_frame_error = 0U;

static void ADC_StartOneFrame(void)
{
    if (HAL_ADC_Start_DMA(&hadc1,
                          (uint32_t *)adc_values,
                          ADC_CHANNEL_COUNT) != HAL_OK)
    {
        Error_Handler();
    }
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1)
    {
        /* 回调中只置位，数组处理放到主循环。 */
        adc_frame_ready = 1U;
    }
}

void HAL_ADC_ErrorCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1)
    {
        adc_frame_error = 1U;
    }
}
```

初始化和主循环：

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
    Error_Handler();
}
ADC_StartOneFrame();

while (1)
{
    if (adc_frame_ready != 0U)
    {
        uint16_t potentiometer;
        uint16_t light;
        uint16_t ntc;
        uint16_t infrared;

        adc_frame_ready = 0U;

        /* Normal 模式已经停止，当前数组是一帧稳定数据。 */
        potentiometer = adc_values[0];
        light         = adc_values[1];
        ntc           = adc_values[2];
        infrared      = adc_values[3];

        /*
         * 在这里完成 OLED 显示、串口输出或物理量换算。
         * 不要把这些耗时操作放进回调。
         */

        HAL_Delay(100);
        ADC_StartOneFrame();
    }

    if (adc_frame_error != 0U)
    {
        adc_frame_error = 0U;
        HAL_ADC_Stop_DMA(&hadc1);
        ADC_StartOneFrame();
    }
}
```

这段代码的关键不是变量名，而是状态闭环：

```text
Start -> DMA Busy -> Complete Callback -> Frame Ready
-> Process Stable Frame -> Start Again
```

### 6.5 验收现象

- 转动电位器，对应数组元素应在 `0~4095` 范围内明显变化；
- 遮挡光敏电阻时，对应值应按分压接法上升或下降；
- 握住 NTC 后，数值应缓慢变化，而不是瞬间大幅跳变；
- 靠近或遮挡红外接收器时，对应值应变化；
- 只操作一个传感器时，其他数组下标不应交换。

若四个数都变化但含义错位，优先检查 Rank，而不是先改数组下标掩盖配置错误。

## 7. 连续采集：ADC Continuous 与 DMA Circular

### 7.1 两个循环必须相互匹配

若希望 ADC 不停扫描，应同时配置：

- ADC Continuous Conversion Mode：Enable；
- DMA Mode：Circular。

启动一次后：

```text
ADC：Rank1 -> Rank2 -> Rank3 -> Rank4 -> Rank1 -> ...
DMA： [0]  ->  [1]  ->  [2]  ->  [3]  ->  [0]  -> ...
```

```c
HAL_ADCEx_Calibration_Start(&hadc1);

if (HAL_ADC_Start_DMA(&hadc1,
                      (uint32_t *)adc_values,
                      ADC_CHANNEL_COUNT) != HAL_OK)
{
    Error_Handler();
}

while (1)
{
    /* adc_values[] 始终保存最近一次附近的结果。 */
    HAL_Delay(100);
}
```

Continuous + Circular 适合观察电位器、光敏电阻、NTC 等慢变化量，但它并不自动保证 CPU 每次读取到的四个值来自同一轮扫描。

若主循环直接轮询这个由 DMA 异步更新的数组，应通过 `volatile` 或受控的读取接口让编译器感知外部修改。但 `volatile` 只约束编译器访问，不能保证四个元素属于同一轮扫描。

### 7.2 为什么可能读到“半新半旧”的数组

假设 CPU 正在读取：

```text
values[0]：第 20 轮
values[1]：第 20 轮
```

此时 DMA 已开始第 21 轮并改写后两个位置，就可能形成混合帧。对慢变化的显示数据，这种差异通常不明显；对控制、记录和算法输入，则必须处理一致性。

可选方法：

1. 使用本章的 Normal 单帧模式，传输完成后再处理；
2. 使用长度为两帧的缓冲区，在 Half/Complete 回调中复制已经完成的半区；
3. 在更高性能系列上使用硬件双缓冲，并处理数据缓存一致性。

仅关闭 CPU 中断不能阻止 DMA 改写内存，所以“关中断后复制数组”并不等价于冻结 DMA。

### 7.3 两帧缓冲的思路

四通道扫描时，可准备 8 个元素：

```c
uint16_t adc_dma_buffer[8];
uint16_t adc_snapshot[4];
```

DMA 写完前 4 个元素触发 Half Transfer，写完后 4 个触发 Transfer Complete。CPU 在对应回调中快速复制已经完成的半区，再在主循环处理 `adc_snapshot`。这种方法适合吞吐量较高的连续采集，但不作为本章首个实现。

## 8. 定时器触发：让采样周期可控

### 8.1 Continuous 模式的局限

Continuous 模式会在上一轮结束后立刻开始下一轮，采样率由 ADC 时钟、各通道采样时间和转换时间共同决定。它适合“尽快获取最新值”，却不适合“严格每 1 ms 采一帧”。

需要固定采样周期时，使用：

```text
TIMx Update/TRGO
-> ADC 规则组外部触发
-> 按 Rank 扫描一帧
-> 每次 EOC 请求 DMA
-> 缓冲区
```

### 8.2 一帧采样时间必须小于触发周期

STM32F1 12 位 ADC 的单通道转换时间可写为：

$$T_{channel}=(T_{sample}+12.5)T_{ADC}$$

四个通道的一帧时间近似为：

$$T_{frame}=\sum_{i=1}^{4}(T_{sample,i}+12.5)T_{ADC}$$

若所有通道使用 $55.5$ 周期采样时间，$f_{ADC}=12\,\text{MHz}$：

$$T_{frame}=4\times\frac{55.5+12.5}{12\,\text{MHz}}
\approx 22.67\,\mu\text{s}$$

定时器触发周期必须大于一帧实际转换时间，并留出足够裕量。若每 $1\,\text{ms}$ 触发一次，这个时间预算是充足的。

### 8.3 推荐配置

| ADC 选项 | 设置 |
| --- | --- |
| Scan Conversion | Enable |
| Continuous Conversion | Disable |
| External Trigger | 目标 TIMx TRGO |
| DMA | Circular 或按帧 Normal |

| 定时器选项 | 设置 |
| --- | --- |
| Clock Source | Internal Clock |
| TRGO | Update Event |
| PSC/ARR | 根据目标帧率计算 |

启动顺序通常为：

```c
HAL_ADCEx_Calibration_Start(&hadc1);
HAL_ADC_Start_DMA(&hadc1,
                  (uint32_t *)adc_values,
                  ADC_CHANNEL_COUNT);
HAL_TIM_Base_Start(&htim3);
```

先让 ADC 与 DMA 就绪，再启动定时器，避免丢失第一个触发事件。具体触发源可用性必须以目标型号参考手册和 CubeMX 选项为准。

## 9. 综合应用：NTC 阻值与温度

### 9.1 先确认分压方向

NTC 的阻值随温度升高而下降，但 ADC 电压是上升还是下降，取决于 NTC 位于分压器上臂还是下臂。

若固定电阻 $R_F$ 接 $VDDA$，NTC $R_T$ 接地，ADC 测量中点：

$$V_{out}=V_{DDA}\frac{R_T}{R_F+R_T}$$

温度升高时 $R_T$ 下降，因此 $V_{out}$ 和 ADC 原码都下降。反解为：

$$R_T=R_F\frac{V_{out}}{V_{DDA}-V_{out}}$$

当分压电源与 ADC 参考电压同为 $VDDA$ 时，可直接使用 ADC 原码：

$$R_T=R_F\frac{ADC}{4095-ADC}$$

若 NTC 接 $VDDA$、固定电阻接地，则公式相反：

$$R_T=R_F\frac{4095-ADC}{ADC}$$

因此不能只凭“握住后数值下降”判断程序对错，必须先查原理图。

### 9.2 Beta 模型

已知 NTC 在参考温度 $T_0$ 下的标称阻值 $R_0$ 和 Beta 值 $B$，可用：

$$
\frac{1}{T}
=
\frac{1}{T_0}
+
\frac{1}{B}\ln\left(\frac{R_T}{R_0}\right)
$$

其中 $T$ 与 $T_0$ 必须使用开尔文温度。摄氏温度为：

$$T_{^\circ C}=T-273.15$$

以常见的 $R_0=10\,\text{k}\Omega$、$T_0=25^\circ\text{C}=298.15\,\text{K}$、$B=3950\,\text{K}$ 为例。若 $R_F=10\,\text{k}\Omega$、NTC 位于下臂、ADC 原码为 $1500$：

$$
R_T
=10\,000\times\frac{1500}{4095-1500}
\approx 5780\,\Omega
$$

$$
T
=
\left[
\frac{1}{298.15}
+
\frac{1}{3950}\ln\left(\frac{5780}{10\,000}\right)
\right]^{-1}
-273.15
\approx 37.9^\circ\text{C}
$$

这个例子说明：NTC 变热后阻值下降，在该接法下 ADC 原码也下降。

### 9.3 C 函数

```c
#include <math.h>
#include <stdint.h>

static float NTC_CodeToResistance(uint16_t adc_code,
                                  float fixed_resistance)
{
    if (adc_code == 0U)
    {
        return 0.0f;
    }

    if (adc_code >= 4095U)
    {
        return INFINITY;
    }

    /* 固定电阻接 VDDA，NTC 接 GND。 */
    return fixed_resistance
           * (float)adc_code
           / (4095.0f - (float)adc_code);
}

static float NTC_ResistanceToCelsius(float resistance,
                                     float resistance_at_25c,
                                     float beta)
{
    const float t0_kelvin = 298.15f;
    float t_kelvin;

    if (resistance <= 0.0f)
    {
        return NAN;
    }

    t_kelvin = 1.0f
               / ((1.0f / t0_kelvin)
                  + logf(resistance / resistance_at_25c) / beta);

    return t_kelvin - 273.15f;
}
```

使用示例：

```c
float ntc_resistance;
float ntc_temperature;

ntc_resistance = NTC_CodeToResistance(adc_values[2], 10000.0f);
ntc_temperature = NTC_ResistanceToCelsius(ntc_resistance,
                                          10000.0f,
                                          3950.0f);
```

工程中必须把 $R_0$、$R_F$ 和 $B$ 替换为实际 NTC 参数。若使用 `printf` 输出浮点数，还需按工具链设置启用浮点格式化。NTC 自热、固定电阻误差、参考电压噪声和 Beta 模型近似都会影响最终温度。

## 10. VREFINT 与片内温度通道

### 10.1 VREFINT 的作用

若默认使用 $3.3\,\text{V}$ 换算 ADC，而实际 $VDDA$ 为 $3.28\,\text{V}$，所有外部通道都会产生比例误差。STM32F103 提供约 $1.2\,\text{V}$ 的内部参考通道，可由其原码近似反推 $VDDA$：

$$V_{DDA}\approx V_{REFINT}\frac{4095}{ADC_{VREFINT}}$$

再计算外部输入：

$$V_{in}\approx V_{DDA}\frac{ADC_{in}}{4095}$$

$V_{REFINT}$ 存在芯片个体差异，把典型值 $1.2\,\text{V}$ 当作绝对精确值只能得到近似补偿。精度要求高时，应依据目标芯片提供的校准信息或使用外部精密参考。

### 10.2 内部通道需要足够采样时间

片内温度传感器与 VREFINT 都不是低阻抗外部电压源，需要满足数据手册给出的最小采样时间。选择步骤是：

1. 查目标型号数据手册中的采样时间要求；
2. 根据 $f_{ADC}$ 换算为 ADC 周期数；
3. 在 CubeMX 中选择不低于要求的档位；
4. 把该通道的一致性和噪声纳入实验验收。

不要简单选择“最接近”的较小档位。例如计算得到至少 $61.2$ 周期时，应选择 $71.5$ 而不是 $55.5$。

片内温度传感器更适合观察芯片温度变化趋势，不应直接替代经过标定的高精度温度传感器。

## 11. 故障定位

### 11.1 数组始终为 0

按以下链路检查：

```text
传感器输出
-> GPIO 是否为 Analog
-> ADC 通道与 Rank
-> ADC 是否启动
-> DMA1 Channel 1 是否使能
-> 外设地址与内存地址
-> 数组是否被程序重新清零
```

同时确认 `MX_DMA_Init()` 已执行，并且初始化顺序没有被手工改坏。

### 11.2 只有第一个数组元素变化

最常见原因是 Memory Increment 没有开启。DMA 每次都写 `adc_values[0]`，后续元素保持旧值。

### 11.3 四个值都有，但通道对应错误

检查：

- Rank 顺序；
- Number of Conversion；
- CubeMX 重新生成代码后 Rank 是否变化；
- 数组注释是否仍与配置一致。

不要假设 `ADC_CHANNEL_0` 必然放在数组第 0 项，真正决定顺序的是 Rank。

### 11.4 数值错位、截断或数组越界

检查：

- ADC DMA 两端是否都是 Half Word；
- 数组是否为 `uint16_t[]`；
- 传输数量是否为元素数而不是字节数；
- 数组长度是否至少等于 DMA 数量；
- HAL API 要求的指针强制转换是否只改变类型，没有改变真实内存布局。

### 11.5 完成回调不执行

检查：

1. DMA1 Channel 1 NVIC 是否启用；
2. `DMA1_Channel1_IRQHandler()` 是否存在；
3. IRQ Handler 是否调用 `HAL_DMA_IRQHandler()`；
4. ADC 句柄是否通过 `__HAL_LINKDMA` 关联 DMA；
5. 回调函数名和参数是否完全正确；
6. DMA 是否真的完成了规定数量的传输。

### 11.6 第二次启动返回 HAL_BUSY

通常是上一轮仍在进行，或完成状态尚未正确收尾。不要在 ADC DMA 仍 Busy 时重复调用 Start。

单帧模式应遵守：

```text
Start -> Complete -> Process -> Start
```

### 11.7 连续模式数据不稳定

可能原因包括：

- ADC Continuous 开启，但 DMA 仍为 Normal；
- DMA Circular 开启，但 ADC 每次只转换一轮且没有新触发；
- CPU 读取时 DMA 正在覆盖数组；
- 采样时间过短，传感器源阻抗较高；
- 串口/OLED 刷新造成观察节拍混乱，但实际采集正常；
- 模拟电源、接地或布线噪声较大。

先用 Normal 单帧模式验证每个 Rank，再切换连续模式，可显著缩小排错范围。

### 11.8 DMA 通道冲突

若 ADC、USART、I2C 或定时器同时使用 DMA，需查参考手册的请求映射表。一个固定通道不能在同一时间服务两个互相冲突的外设请求。

解决方法包括：

- 某个低流量外设改用中断；
- 调整所用外设实例；
- 重新规划功能与引脚；
- 选择具有更多 DMA 资源的芯片。

## 12. 架构选择

| 需求 | 推荐架构 | 缓冲区特性 |
| --- | --- | --- |
| 偶尔读一个传感器 | ADC 轮询 | 单值，最简单 |
| 偶尔读取多个通道 | 扫描 + DMA Normal | 一帧完成后稳定 |
| 持续显示慢变量 | Continuous + Circular | 始终更新，可能混合帧 |
| 固定周期采集一帧 | TIM TRGO + 扫描 + DMA | 周期确定 |
| 连续记录波形 | TIM TRGO + DMA Circular + 半/全回调 | 需要分块处理 |
| 小数组偶尔复制 | `memcpy()` | 通常无需 DMA |
| 大块复制且 CPU 有其他任务 | DMA Normal + 完成通知 | 需管理并发访问 |

选择 DMA 架构时，依次回答：

1. 数据由谁产生，谁消费？
2. 每次搬运宽度是多少？
3. 地址应固定还是递增？
4. 一批数据有多少项？
5. 数据是单批还是连续流？
6. CPU 何时可以安全读取缓冲区？
7. 是否需要固定采样周期？
8. 多个 DMA 请求是否冲突？

## 13. 自测题

1. DMA 相比中断，减少了 CPU 的哪一部分工作？
2. ADC1 多通道扫描时，为什么外设地址不递增而内存地址递增？
3. `uint16_t adc_values[4]` 使用 Half Word 传输时，DMA 数量应填 `4` 还是 `8`？
4. 为什么 STM32F1 的内存到内存重复复制不能直接配置 Circular？
5. ADC Continuous 开启而 DMA 使用 Normal，会发生什么？
6. `HAL_ADC_ConvCpltCallback()` 不执行时，为什么要检查 DMA IRQ？
7. 为什么关闭 CPU 中断不能保证 Circular DMA 数组不再变化？
8. 四通道每通道耗时 $6\,\mu\text{s}$，要每 $20\,\mu\text{s}$ 触发一帧是否可行？
9. NTC 温度升高后 ADC 原码一定下降吗？
10. DMA 适合所有小数据复制吗？

**答案要点**：

1. DMA 代替 CPU 完成每一项数据寄存器与内存之间的重复读写；
2. ADC 结果始终来自同一个 DR，而各 Rank 结果要依次写入不同数组元素；
3. 填 `4`，数量是元素项数，不是字节数；
4. STM32F1 明确限制 Memory-to-Memory 与 Circular 组合，应在 Normal 完成后软件重启；
5. DMA 填满一次后停止，而 ADC 仍继续转换，后续结果不再进入数组；
6. ADC DMA 完成回调由 DMA Channel IRQ 经 HAL 调用链触发；
7. DMA 是独立总线主设备，屏蔽 CPU 中断不会停止 DMA；
8. 不可行，一帧需约 $24\,\mu\text{s}$，已经超过触发周期；
9. 不一定，方向取决于 NTC 在分压器中的位置；
10. 不适合，小数据可能由 `memcpy()` 或直接赋值更简单。

## 本章小结

DMA 的核心不是记住某个 HAL 函数，而是先画清数据流：

```text
谁产生请求
-> 从哪个地址读
-> 向哪个地址写
-> 每次搬多宽
-> 地址是否递增
-> 总共搬几项
-> 搬完停止还是重装
-> CPU 何时接管结果
```

内存到内存实验建立了 DMA 的基本搬运模型；ADC 扫描实验进一步说明了外设请求、固定寄存器地址、数组递增和完成回调的配合；Continuous、Circular 与定时器触发则把“能采到数据”提升为“能按正确节拍、正确边界管理数据”。

对初学工程，优先从 Normal 单帧闭环开始。只有在通道顺序、数据宽度、数组长度和回调链都验证正确后，再进入 Circular、半传输回调和连续流处理。
