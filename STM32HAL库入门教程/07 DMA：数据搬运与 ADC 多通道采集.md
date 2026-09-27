# 07 DMA：数据搬运与 ADC 多通道采集

## 本章问题

什么时候应该让 DMA 搬数据，怎样保证 CPU 读到的是一批完整而稳定的数据？

第 6 章把单通道的"单次非扫描"走通了；要一次拿到多个通道，规则组就要按 Rank 扫描，而扫描的结果会连续涌进同一个 `DR`，必须有人及时搬走——这正是 DMA 的用武之地。本章先回答 DMA 与 CPU 如何分工、一张"搬运单"要填哪些字段，再用两个实验把这条链路真正跑起来，最后把定时器触发与扫描、DMA 组合成定时可控的多通道采集。

## 学习目标

- 画出 DMA 的源地址、目的地址、宽度、自增和数量。
- 根据请求映射选择 STM32F103 的 DMA 通道。
- 用 HAL 完成一次内存到内存复制。
- 配置 ADC 扫描与 DMA，区分 Normal 和 Circular。
- 用定时器 TRGO 固定多通道采样的触发周期。

## 1. DMA 与 CPU 的分工

DMA（Direct Memory Access，直接存储器访问）是一套按配置自动搬运数据的硬件。CPU 负责设置源地址、目的地址、数据宽度、数量等参数；软件启动或外设请求到来后，DMA 执行传输，并在完成时通过状态位或中断通知 CPU。

| 方式 | CPU 做什么 | 适用场景 | 主要代价 |
| --- | --- | --- | --- |
| 轮询 | 一直检查状态并亲自读写数据 | 低频、短小、流程简单 | 等待期间难做其他任务 |
| 中断 | 每次事件到来后进入 ISR，CPU 亲自读写数据 | 事件频率不高、每次处理量小 | 高频事件会产生大量中断开销 |
| DMA | CPU 配置一次，DMA 按请求搬运一批数据 | 连续采样、串口收发、SPI 数据流 | 配置与缓冲区管理更复杂 |

ADC 多通道扫描时，每个 Rank 的结果都会进入同一个 `ADC1->DR`。若不用 DMA，CPU 必须在通道之间及时读取这个寄存器；使用 DMA 后，每次转换完成产生的请求可以把结果直接写入数组。

DMA 只减少 CPU 参与每一次搬运的次数，不会凭空增加总线带宽。

更准确地说，DMA 和 CPU 共用同一组总线：DMA 每搬一项，都要占一次总线去读源、写目的；CPU 此时若要取指令或访问内存，就得等总线空出来。总线仲裁会让双方轮流使用，所以 DMA 搬运期间 CPU 仍然能运行，只是内存访问可能略微变慢。DMA 的收益来自"一次配置管一批"，而不是"搬运不占任何资源"——数据量很小的时候，偶尔读一个 ADC 值、复制一个小数组，直接用轮询、`memcpy()` 或直接赋值反而更快、更省事。

## 2. 一次 DMA 搬运如何发生

### 2.1 五个步骤

一次完整传输可以按下面的顺序理解：

1. CPU 配置源地址、目的地址、方向、宽度、地址自增、数量、模式和优先级；
2. CPU 使能 DMA 通道；
3. 软件或外设产生 DMA 请求；
4. DMA 完成一次数据读写，并更新地址与剩余计数；
5. 计数归零后置位完成标志，按配置产生传输完成中断。

可以把配置理解成一张搬运单：

| 要回答的问题 | DMA 配置 |
| --- | --- |
| 从哪里取 | 外设地址或源内存地址 |
| 送到哪里 | 外设地址或目的内存地址 |
| 每次搬多宽 | Byte、Half Word、Word |
| 地址是否后移 | Peripheral/Memory Increment |
| 总共搬几项 | 传输数量 |
| 搬完是否重来 | Normal/Circular |
| 冲突时谁先走 | 通道优先级 |

### 2.2 请求决定何时搬

外设通常在"已经可以接收下一项"或"已经产生一个新数据"时发出请求：

- USART 发送数据寄存器空：请求 DMA 写入下一个发送字节；
- USART 收到一个字节：请求 DMA 把接收寄存器内容搬入数组；
- ADC 完成一次转换：请求 DMA 把 `ADC1->DR` 搬入数组；
- 定时器发生更新或捕获事件：请求 DMA 更新定时器寄存器或保存数据。

基本节拍是：

```text
外设事件 -> DMA 请求 -> 搬运一项 -> 剩余计数减 1
```

内存到内存没有外设请求，通常由软件使能通道后开始执行。

### 2.3 STM32F103 的请求映射

以 STM32F103C8T6 为例，芯片只有 DMA1，DMA1 包含 7 个通道。某个外设的请求接到哪个通道由芯片内部硬件映射决定，不能任意改接；例如 ADC1 的请求映射到 `DMA1_Channel1`。

可以把 7 个通道想成 7 条接线固定的传送带：哪个外设的请求接哪条线，出厂时就焊死了。这既是限制也是便利——看到 `DMA1_Channel1`，对照映射表就能直接推断它在为谁服务。本章两个实验恰好都落在 `DMA1_Channel1` 上，无法同时运行，配套工程因此把它们拆成 `01_MemoryCopy` 和 `02_ADC_Scan` 两个独立工程，位于 `E:\ProjectStm\Courses\HAL07_DMA_ADC` 下。

配置后仍要检查：

- 两个外设是否占用了同一个 DMA 通道；
- 方向、地址和宽度是否符合数据路径；
- 使用回调时，是否打开了所用 DMA 通道的 NVIC 中断；
- 目标芯片是否真的具有所需的 DMA 控制器或通道。

同一控制器收到多个请求时，会按软件优先级和通道号规则仲裁。优先级只影响冲突时的服务顺序，不能提高外设本身的数据产生速度。

## 3. 八个关键配置项

### 3.1 传输方向

先画箭头，再选择方向：

| 应用 | 方向 |
| --- | --- |
| ADC 采样 | Peripheral to Memory |
| USART 接收 | Peripheral to Memory |
| USART 发送 | Memory to Peripheral |
| 数组复制 | Memory to Memory |

### 3.2 源地址与目的地址

地址必须指向实际参与传输的数据位置：

- ADC 外设端：`&ADC1->DR`；
- 串口发送外设端：对应 USART 数据寄存器；
- 内存端：数组首地址；
- 内存复制：源数组和目的数组首地址。

DMA 的"外设端"和"存储器端"是控制器接口的两组地址寄存器。内存到内存模式中，两端实际都可以指向 SRAM，但仍分别填到 DMA 的两侧地址寄存器中。

HAL 外设驱动通常会填写外设寄存器地址。例如调用 `HAL_ADC_Start_DMA()` 时，只需提供接收数组和传输数量。

### 3.3 数据宽度

STM32F1 DMA 常用三种宽度：

| CubeMX 名称 | 位宽 | 常见 C 类型 |
| --- | ---: | --- |
| Byte | 8 bit | `uint8_t` |
| Half Word | 16 bit | `uint16_t` |
| Word | 32 bit | `uint32_t` |

12 位 ADC 结果使用 Half Word 即可；USART 一般逐字节收发，通常使用 Byte。外设宽度、内存宽度和数组元素类型应匹配，否则可能发生截断、扩展或地址步长异常。

"匹配"包含两层含义。第一层是宽度一致：外设端读出的位数和写入内存的位数必须一样，12 位结果放进 16 位的 Half Word 才不会丢。第二层是数组类型一致：DMA 只知道"每次搬 N 字节、地址前移 N 字节"，它不认识 C 数组的类型，类型不匹配编译器也不报错，错误要到运行时才在数据里显现。例如宽度选了 Word、数组却是 `uint16_t[4]`，DMA 会按 4 字节步长往内存写 8 个半字的位置，越过数组末尾，把相邻变量一起改写——调试器里的表现就是"数组后面的变量莫名其妙被改了"。

### 3.4 地址自增

每搬运一项后，DMA 可以让地址按数据宽度前移。以 ADC 扫描四个 Rank 为例：

```text
外设端：ADC1->DR -> ADC1->DR -> ADC1->DR -> ADC1->DR
内存端：values[0] -> values[1] -> values[2] -> values[3]
```

因此 ADC 采集通常是：

- 外设地址固定：Peripheral Increment Disable；
- 内存地址递增：Memory Increment Enable。

忘记开启内存自增时，所有结果都会反复覆盖 `values[0]`。内存到内存复制数组时，两端通常都要自增。

### 3.5 传输数量

传输数量表示"搬运多少项"，不是字节总数。Half Word、数量为 `4` 时：

$$4\times 2\,\text{Byte}=8\,\text{Byte}$$

数组有 4 个 `uint16_t` 元素时，传入 `4`，不能传入 `sizeof(adc_values)` 得到的 `8`。可使用：

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

优先级有 Low、Medium、High、Very High 四档，只在多个 DMA 请求竞争时参与仲裁。不能丢样的高速 ADC 或定时器波形更新可设较高，普通串口日志可设较低；不要把所有通道都设为 Very High。优先级不能修复通道冲突、带宽不足或错误的数据宽度。

### 3.8 中断

常见 DMA 中断事件包括：

- Half Transfer：传输到缓冲区一半；
- Transfer Complete：全部传输完成；
- Transfer Error：传输错误。

以数量为 8 的传输为例，三个事件的触发时刻是：

```text
搬完第 4 项（计数从 8 减到 4，缓冲区恰好写满一半）-> Half Transfer
搬完第 8 项（计数归零，通道停止或回绕）          -> Transfer Complete
搬运过程中总线出错                              -> Transfer Error
```

Half Transfer 这个名字由此而来：它精确对应"剩余计数从 $N$ 减到 $N/2$"的时刻，不是模糊的"搬了一半左右"。另外，工程内 `stm32f1xx_hal_dma.c` 的 `HAL_DMA_IRQHandler()` 在 Normal 模式下触发一次 Half Transfer 后会自动关闭这个中断，只有 Circular 模式才每轮都成对触发——这正是 8.3 节双半区方案依赖 Circular 的原因之一。

中断只通知 CPU"某个阶段已经完成"，真正的数据搬运仍由 DMA 执行。回调中只做置标志、复制已稳定半区等短操作；OLED 刷屏、串口格式化和浮点运算放到主循环或任务中。

## 4. 从任务反推配置

拿到任务后，先画数据路径，再回答"谁产生数据、谁消费数据、每次搬多宽、地址是否递增、一批有多少项、CPU 何时读取"，最后才打开 CubeMX 填配置。

### 4.1 任务一：把 `source[8]` 复制到 `destination[8]`

数据路径（两端都是 SRAM）：

```text
source[0..7] -> DMA1_Channel1 -> destination[0..7]
```

| 配置项 | 选择 | 推导理由 |
| --- | --- | --- |
| 方向 | Memory to Memory | 两端都是内存 |
| 外设端地址 | `source` | 源数组填入外设端站点 |
| 存储器端地址 | `destination` | 目的数组位于 SRAM |
| 两端数据宽度 | Word | 元素类型是 `uint32_t` |
| 两端地址自增 | Enable | 依次访问每个数组元素 |
| 传输数量 | `8` | 元素个数，不是字节数 |
| 模式 | Normal | 只复制一轮 |
| 触发 | M2M（软件启动） | 没有外设请求 |

### 4.2 任务二：把 ADC1 四个 Rank 的结果存入 `adc_values[4]`

数据路径：

```text
ADC1->DR（固定地址） -> DMA1_Channel1 -> adc_values[0..3]（递增）
```

| 配置项 | 选择 | 推导理由 |
| --- | --- | --- |
| 方向 | Peripheral to Memory | ADC 寄存器是源 |
| 外设端地址 | `&ADC1->DR` | 所有 Rank 结果都写入同一个 DR |
| 存储器端地址 | `adc_values` | 结果数组位于 SRAM |
| 两端数据宽度 | Half Word | 12 位结果按 16 位读出，对应 `uint16_t` |
| 外设端自增 | Disable | 每次都读同一个 DR |
| 存储器端自增 | Enable | 依次写入数组元素 |
| 传输数量 | `4` | 每帧四个转换结果 |
| 模式 | Normal（单帧）/ Circular（连续） | 由采集节奏决定 |
| 触发 | 硬件请求 | 等待 ADC 每次转换完成 |

两个任务的关键差异是：数组复制是两端都自增、软件触发；ADC 采集是外设端固定、硬件请求。数组下标与通道的对应关系由 Rank 顺序决定，而不是由通道号大小决定。

## 5. HAL 初始化与回调链

### 5.1 CubeMX 配置顺序

1. 先启用产生或消费数据的外设；
2. 在外设的 DMA Settings 中添加请求；
3. 确认 DMA 控制器和通道映射；
4. 设置方向、两端宽度和地址自增；
5. 选择 Normal 或 Circular，并设置优先级；
6. 使用回调时打开对应 DMA 通道的 NVIC 中断；
7. 生成代码后检查 `MX_DMA_Init()`、MSP 中的 `__HAL_LINKDMA` 和 DMA IRQ Handler。

应用初始化前要确认生成代码已经调用 `MX_GPIO_Init()`、`MX_DMA_Init()`、`MX_ADC1_Init()` 以及使用的 `MX_I2C2_Init()`。DMA 句柄关联或初始化顺序被手工改坏时，外设可能启动了，但没有可用的 DMA 通道。

#### CubeMX 逐项怎么点

以本章实验二为例，把上面的顺序落到 CubeMX 界面上（版本 6.17，不同版本措辞略有差异）：

1. 在 `Analog` 分类中勾选 `ADC1`，在右侧引脚图上把 `PA0`~`PA3` 依次点成 `ADC1_IN0`~`ADC1_IN3`；
2. 打开 `ADC1` 配置页，勾选四个通道，`Number of Conversion` 填 `4`，再在 `Rank 1`~`Rank 4` 的下拉里逐个确认通道顺序；
3. 添加 DMA：进入 `ADC1` 配置页的 `DMA Settings` 标签页，点 `Add`，在 `Select` 下拉中选 `ADC1`；因为 F1 的请求映射固定，选中后通道列会自动显示 `DMA1 Channel 1`，这一列不能改；
4. 在刚出现的这一行里逐列核对：`Mode` 选 `Normal`（连续采集才选 `Circular`）；`Increment Address` 中 `Peripheral` 不勾、`Memory` 勾上；`Data Width` 两端都选 `Half Word`；
5. 打开 `System Core → NVIC` 页，勾选 `DMA1 channel1 global interrupt`（对应 `.ioc` 中的 `DMA1_Channel1_IRQn`）；不用完成回调时可以不勾，实验一就是这样；
6. 打开 `Clock Configuration` 页，确认 ADC 分频为 `/6`，$f_{ADC}=12\,\text{MHz}$（核对方法见 7.3 节）；
7. 点 `GENERATE CODE`。

每个字段填错的后果不会在编译期暴露，要到运行时才显现：

| 填错项 | 典型后果 |
| --- | --- |
| `Memory` 自增没勾 | 所有结果反复写 `adc_values[0]`，其余元素保持 0 或旧值 |
| `Data Width` 选成 `Word` | DMA 按 4 字节步长写数组，数值错位且越过数组末尾 |
| `Mode` 该 `Normal` 选成 `Circular` | DMA 填满后不停止，数组被持续覆盖 |
| 请求没加，或 `Select` 选错外设 | DMA 不会启动，数组始终为 0 |
| NVIC 没勾 | 搬运照常进行，但完成回调不执行，`adc_frame_ready` 永远不置位 |

### 5.2 常用 HAL API

| API | 作用 |
| --- | --- |
| `HAL_DMA_Start()` | 启动普通 DMA 传输 |
| `HAL_DMA_Start_IT()` | 启动 DMA 并允许中断通知 |
| `HAL_DMA_PollForTransfer()` | 轮询等待半传输或全传输完成 |
| `HAL_DMA_IRQHandler()` | 处理 DMA 中断标志并调用回调 |
| `HAL_ADC_Start_DMA()` | 启动 ADC，并把结果交给 DMA |
| `HAL_ADC_Stop_DMA()` | 停止 ADC DMA 采集 |
| `HAL_TIM_Base_Start()` / `HAL_TIM_Base_Stop()` | 启停用于产生 TRGO 的定时器 |

已有 HAL 外设接口时，优先使用 `HAL_ADC_Start_DMA()` 等接口，不要在外设驱动已经封装好后又重复手工配置寄存器。

### 5.3 ADC 完成回调的调用链

```text
DMA1 Channel 1 传输完成
-> DMA1_Channel1_IRQHandler()
-> HAL_DMA_IRQHandler()
-> HAL 内部 ADC DMA 完成处理
-> HAL_ADC_ConvCpltCallback()
```

因此，`HAL_ADC_ConvCpltCallback()` 没有执行时，不仅要查 ADC，也要查 `DMA1_Channel1` 的 NVIC、IRQ Handler 和 DMA 句柄关联。

## 6. 实验一：内存到内存复制

### 6.1 目标与配置

用 DMA 把 `source[8]` 复制到 `destination[8]`，完成后逐项比较。这个小数组用 `memcpy()` 也可能更合适；本实验用于看清 DMA 的地址、数量和重启关系。

| 项目 | 设置 |
| --- | --- |
| 通道 | `DMA1_Channel1` |
| Mode | Normal |
| Direction | Memory to Memory |
| Source Increment | Enable |
| Destination Increment | Enable |
| Source Data Width | Word |
| Destination Data Width | Word |
| Priority | Low |

实验一在 CubeMX 中的添加位置与实验二不同：打开 `System Core → DMA` 页点 `Add`，`Select` 下拉选 `MEM2MEM`，同样会得到 `DMA1 Channel 1`。由于用 `HAL_DMA_PollForTransfer()` 轮询等待完成，本实验不需要勾选 `DMA1 channel1 global interrupt`——配套工程 `01_MemoryCopy` 的中断文件里因此没有 `DMA1_Channel1_IRQHandler()`。这是它与实验二在 NVIC 配置上的唯一差别，也正好演示了"轮询等待"和"中断回调"两种方式。

CubeMX 不同版本可能仍显示 Peripheral/Memory 命名；只要核对源地址、目的地址、宽度和两端自增即可。

### 6.2 最小完整代码

示例使用生成句柄 `hdma_memtomem_dma1_channel1`；若 CubeMX 生成的句柄名不同，以 `dma.c` 中的实际名称为准。

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

在 `main()` 的所有 `MX_xxx_Init()` 完成后调用。Normal 模式重复启动的顺序是：确认上一轮已停止（关闭）→ `HAL_DMA_Start()` 重装计数并使能 → 再次搬运：

```c
/* main() 中：所有 MX_xxx_Init() 之后 */
DMA_CopyOnce();

while (1)
{
    source[0]++;
    DMA_CopyOnce();
    HAL_Delay(1000);
}
```

不要把 Memory-to-Memory 改为 Circular。STM32F1 的内存到内存模式不能使用 Circular，重复复制必须由软件重新启动。

把实验一按"输入 → 处理 → 输出"拆开看：

- 输入：`source[]` 中的 8 个已知初值；
- 处理：`HAL_DMA_Start()` 装载搬运单并使能通道，DMA 自主完成 8 次 Word 搬运；
- 输出：`destination[]` 的内容与 `copy_ok` 标志。

配套工程 `01_MemoryCopy` 的实际写法与上面的教学版略有差异（代码事实）：`source` 声明为 `static const`（链接后位于 Flash，DMA 一样能读），`destination` 与 `copy_ok` 都是 `static` 变量；`main()` 只在初始化后调用一次 `DMA_CopyOnce()`，随后在 `while (1)` 里闪烁 PC13 作为"程序还活着"的心跳。验证方式不是 OLED，而是调试器：下载后在 Watch 窗口添加 `copy_ok` 和 `destination`，应看到 `copy_ok == 1`、`destination` 与源数据逐项相同。教学版每秒改一次 `source[0]` 再重拷，是为了让"重启一次 Normal 传输"的流程反复可见；工程版只复制一次，把重心放在静态观察上。

### 6.3 预期现象

- `destination[]` 与 `source[]` 完全相同；
- `copy_ok == 1`；
- DMA 通道剩余传输计数归零。

现象与原因的对应关系：

| 如果看到 | 说明 |
| --- | --- |
| `copy_ok == 1` | 搬运单五要素（地址、方向、宽度、自增、数量）全部生效 |
| `destination` 全 0 且 `copy_ok == 0` | DMA 没有真正启动：确认 `MX_DMA_Init()` 在 `DMA_CopyOnce()` 之前执行，`HAL_DMA_Start()` 返回值是否 `HAL_OK` |
| 程序停在 `Error_Handler()` | `HAL_DMA_Start()` 或 `HAL_DMA_PollForTransfer()` 返回了非 `HAL_OK`，常见于上一轮尚未结束就再次启动 |
| 只有部分元素正确 | 两端自增或传输数量与数组长度不一致 |
| 改成 Circular 后行为异常 | STM32F1 内存到内存模式不允许 Circular，属于预期禁止项 |

## 7. 实验二：ADC 扫描加 DMA 单帧采集

### 7.1 单帧数据链

先用 Normal 模式验证通道顺序和数据边界：

```text
启动一次 ADC DMA
-> ADC 按 Rank 扫描一轮
-> DMA 填满数组
-> DMA 自动停止
-> 回调只置位
-> 主循环处理稳定数组
-> 软件重新启动下一轮
```

把"DMA 填满数组"再拆细一点，缓冲区是一拍一拍落位的：

```text
软件启动：HAL_ADC_Start_DMA() 使能 ADC 与 DMA
第 1 拍：Rank 1（PA0）转换完成 -> DMA 把 ADC1->DR 写入 adc_values[0]
第 2 拍：Rank 2（PA1）转换完成 -> DMA 写入 adc_values[1]
第 3 拍：Rank 3（PA2）转换完成 -> DMA 写入 adc_values[2]
第 4 拍：Rank 4（PA3）转换完成 -> DMA 写入 adc_values[3]，计数归零
        -> DMA 停止并触发完成中断 -> HAL_ADC_ConvCpltCallback() 置位
```

每一拍的触发者都是"该 Rank 转换完成"这个事件，所以写入下标顺序严格等于 Rank 顺序：`adc_values[0]` 一定是 Rank 1 的结果，与该通道是几号通道无关。整帧在内存端表现为"数组从前往后逐个更新"，全部写完才有一次回调——这正是 Normal 模式下"回调时数组已冻结"的原因。

### 7.2 接线与 Rank 规划

一种四外部通道实验可使用：

| Rank | ADC 通道 | 示例输入 | 数组位置 |
| ---: | --- | --- | --- |
| 1 | IN0 / PA0 | 电位器 | `adc_values[0]` |
| 2 | IN1 / PA1 | 光敏分压 | `adc_values[1]` |
| 3 | IN2 / PA2 | NTC 分压 | `adc_values[2]` |
| 4 | IN3 / PA3 | 红外接收分压 | `adc_values[3]` |

外部模拟量必须与开发板共地、输入不超范围，GPIO 配置为 Analog；传感器接法以开发板原理图为准。

若使用片内温度传感器或 VREFINT，它们只在 `ADC1` 上有效；`ADC2` 的 `CH16`/`CH17` 没有可用内部信号源。内部通道的采样时间下限与 VREFINT 换算见 10.3 节。

无论选择哪些通道，都先固定 Rank，再固定数组含义；数组顺序跟随 Rank，不跟随通道号大小。

### 7.3 ADC 与 DMA 配置

ADC1（CubeMX）：

1. 开启所需通道；
2. Number of Conversion 设为 `4`；
3. 设置 Rank 1 到 Rank 4；
4. Scan Conversion Mode 开启；
5. Continuous Conversion Mode 关闭；
6. 外部触发先使用 Software Start；
7. 为每个通道设置足够的采样时间；
8. 检查 ADC 时钟不超过目标芯片限制。

第 8 条如何核对？F103 的 ADC 时钟上限是 14 MHz（第 6 章 3.2 节），PCLK2 为 72 MHz，所以必须分频 `/6` 得到 $f_{ADC}=12\,\text{MHz}$。配套工程 `02_ADC_Scan` 的 `SystemClock_Config()` 末尾有这一块（代码事实）：

```c
/* 02_ADC_Scan/Core/Src/main.c：SystemClock_Config() 末尾 */
PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_ADC;
PeriphClkInit.AdcClockSelection = RCC_ADCPCLK2_DIV6;
if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
{
    Error_Handler();
}
```

对应的 `.ioc` 记录了 `RCC.ADCPRE=RCC_ADCPCLK2_DIV6` 与 `RCC.ADCFreq_Value=12000000`。第 6 章记录过一个真实教训：时钟树上的数字只是图纸，早期生成代码里并没有这段，ADC 实际按复位默认分频超规运行，后来补上分频才修复。复刻本章工程时，除了看时钟页显示 12 MHz，还要打开生成后的 `main.c` 确认 `SystemClock_Config()` 末尾真的有 `RCC_ADCPCLK2_DIV6` 这几行——图纸与代码两头都要核对，缺任何一边都可能在数据手册的限制之外运行。

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
| Priority | High |
| NVIC | Enable |

生成代码后核对三个落点（代码事实，来自配套工程 `02_ADC_Scan`）：`dma.c` 中的 DMA 句柄名为 `hdma_adc1_dma1_channel1`，方向、宽度、自增与上表一致；`adc.c` 的 `HAL_ADC_MspInit()` 末尾有 `__HAL_LINKDMA(hadc, DMA_Handle, hdma_adc1_dma1_channel1)`，它把 DMA 句柄挂到 ADC 句柄上；`stm32f1xx_it.c` 中有 `DMA1_Channel1_IRQHandler()`，内部调用 `HAL_DMA_IRQHandler(&hdma_adc1_dma1_channel1)`。三个落点缺了任何一个，实验二都会只搬数据、不进回调。

### 7.4 最小完整代码

将下面内容放入 `main.c` 对应的 CubeMX 用户代码区：头文件放 `Includes`，数组和标志放 `PV`，函数原型放 `PFP`，函数与回调放 `USER CODE 4`，初始化放 `USER CODE 2`，主循环处理放 `while (1)` 内的用户代码区。

```c
/* USER CODE BEGIN Includes */
#include "main.h"
#include "adc.h"
#include "dma.h"
#include <stdint.h>
#include <stdio.h>
#include "oled.h"
/* USER CODE END Includes */

/* USER CODE BEGIN PV */
#define ADC_CHANNEL_COUNT 4U

uint16_t adc_values[ADC_CHANNEL_COUNT] = {0};
volatile uint8_t adc_frame_ready = 0U;
volatile uint8_t adc_frame_error = 0U;
/* USER CODE END PV */

/* USER CODE BEGIN PFP */
static void ADC_StartOneFrame(void);
/* USER CODE END PFP */

/* USER CODE BEGIN 4 */
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
/* USER CODE END 4 */
```

初始化和主循环如下。`main()` 中应先完成 GPIO、DMA、ADC 和 I2C 初始化，再执行 OLED 初始化和第一次采集：

```c
/* USER CODE BEGIN 2 */
OLED_Init();

if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
    Error_Handler();
}
ADC_StartOneFrame();
/* USER CODE END 2 */

/* USER CODE BEGIN WHILE */
while (1)
{
    if (adc_frame_ready != 0U)
    {
        uint16_t potentiometer;
        uint16_t light;
        uint16_t ntc;
        uint16_t infrared;
        char text[16];

        adc_frame_ready = 0U;

        /* Normal 模式已经停止，当前数组是一帧稳定数据。 */
        potentiometer = adc_values[0];
        light         = adc_values[1];
        ntc           = adc_values[2];
        infrared      = adc_values[3];

        OLED_NewFrame();
        snprintf(text, sizeof(text), "PA0:%4u",
                 (unsigned int)potentiometer);
        OLED_PrintASCIIString(0, 0, text, &afont16x8,
                              OLED_COLOR_NORMAL);
        snprintf(text, sizeof(text), "PA1:%4u", (unsigned int)light);
        OLED_PrintASCIIString(0, 16, text, &afont16x8,
                              OLED_COLOR_NORMAL);
        snprintf(text, sizeof(text), "PA2:%4u", (unsigned int)ntc);
        OLED_PrintASCIIString(0, 32, text, &afont16x8,
                              OLED_COLOR_NORMAL);
        snprintf(text, sizeof(text), "PA3:%4u", (unsigned int)infrared);
        OLED_PrintASCIIString(0, 48, text, &afont16x8,
                              OLED_COLOR_NORMAL);
        OLED_ShowFrame();

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
/* USER CODE END WHILE */
```

配套工程 `02_ADC_Scan` 的实际代码与上面同构，另有几处小差异（代码事实）：`main()` 在 `OLED_Init()` 之前先用 `HAL_I2C_IsDeviceReady(&hi2c2, 0x78U, 3U, 100U)` 确认 OLED 在线，失败即进入 `Error_Handler()`；探测前多一句 `HAL_Delay(20U)` 给模块上电稳定时间；显示缓冲 `text` 的长度是 20；显示代码直接使用 `adc_values[0..3]`，不另拷贝到局部变量。缓冲区长度只影响 `snprintf` 的上限，不影响 DMA 数据链。

`OLED_NewFrame()`、`OLED_PrintASCIIString()` 和 `afont16x8` 沿用第 2 章的 OLED 接口。没有 OLED 时，也可以在调试器的 Watch 窗口观察 `adc_values[0..3]`。回调只置位，主循环在 Normal DMA 停止后读取数组：

```text
Start -> DMA Busy -> Complete Callback -> Frame Ready
-> Process Stable Frame -> Start Again
```

### 7.5 预期现象

- 转动电位器，`adc_values[0]` 在 `0~4095` 范围内变化；
- 遮挡光敏电阻时，`adc_values[1]` 按分压接法上升或下降；
- 握住 NTC 后，`adc_values[2]` 缓慢变化，而不是瞬间大幅跳变；
- 靠近或遮挡红外接收器时，`adc_values[3]` 变化；
- 只操作一个传感器时，其他数组下标不应交换。

若四个数都变化但含义错位，优先检查 Rank 顺序，不要先改数组下标掩盖配置错误。

把常见现象与原因对应起来：

| 如果看到 | 最可能说明 |
| --- | --- |
| 四个下标都随各自传感器变化 | Rank 顺序、采样时间与 DMA 配置都正确 |
| 转动电位器，`adc_values[0]` 不动，其余三个有值 | Rank 1 对应的通道或引脚接错，回看 7.2 节的表 |
| 数值含义整体错位一格 | Rank 顺序与数组下标的假定不一致，或 `Number of Conversion` 不是 4 |
| 全部为 0 且不刷新 | 采集链路没走通，按 12.1 节逐级检查 |
| 数值抖动大、偶尔跳变 | 采样时间不够或模拟端噪声，参考第 6 章采样时间一节 |
| 只刷新一次就停住 | Normal 模式一帧结束后没有重新启动，检查 `ADC_StartOneFrame()` 是否还在主循环里被调用 |

## 8. 连续采集：ADC Continuous 与 DMA Circular

### 8.1 两个循环要匹配

若希望 ADC 自由连续扫描，可以配置：

- ADC Continuous Conversion Mode：Enable；
- DMA Mode：Circular。

如果采样必须由定时器固定周期触发，ADC Continuous 可以关闭，使用"定时器触发 + Circular DMA"。Continuous 不是 Circular 的必要条件。

启动一次后：

```text
ADC：Rank1 -> Rank2 -> Rank3 -> Rank4 -> Rank1 -> ...
DMA： [0]  ->  [1]  ->  [2]  ->  [3]  ->  [0]  -> ...
```

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
{
    Error_Handler();
}

if (HAL_ADC_Start_DMA(&hadc1,
                      (uint32_t *)adc_values,
                      ADC_CHANNEL_COUNT) != HAL_OK)
{
    Error_Handler();
}

while (1)
{
    /* adc_values[] 持续保存最近收到的 4 个样本。 */
    HAL_Delay(100);
}
```

Continuous + Circular 适合观察慢变化量，但不保证 CPU 每次读到的四个元素来自同一轮扫描。给异步更新的数组加 `volatile` 只能约束编译器访问，不能保证帧一致性。

### 8.2 半新半旧数据

例如 CPU 正在读取：

```text
values[0]：第 20 轮
values[1]：第 20 轮
```

此时 DMA 已开始第 21 轮并改写后两个位置，就可能得到：

```text
values[0]：第 20 轮
values[1]：第 21 轮
```

对慢变化显示通常不明显；对控制、记录和算法输入则必须处理。关闭 CPU 中断不能阻止 DMA 改写内存，所以"关中断后复制数组"不等价于冻结 DMA。

### 8.3 DMA 双半区与 CPU 快照

四通道扫描时，Circular DMA 可以连续保存两组结果：

```c
uint16_t adc_dma_buffer[8];
```

DMA 写完前 4 个元素触发 Half Transfer，写完后 4 个触发 Transfer Complete。刚写完的半区在下一次回绕前不会被覆盖，因此回调可快速复制该半区，再由主循环处理。

双半区只解决 DMA 的写入边界，不保证慢速主循环永远来得及。若下一次回调到达前仍未取走，快照仍会被覆盖；连续显示或控制应使用带就绪标志的快照/队列，或改用 Normal 模式在每帧结束后停 DMA。

## 9. 定时器触发：让采样周期可控

### 9.1 为什么要定时触发

Continuous 模式会在上一轮结束后立即开始下一轮，采样率由 ADC 时钟、各通道采样时间和转换时间共同决定。若用主循环软件触发，间隔更不可控：循环体里刷屏快慢、`HAL_Delay` 前后做了多少事、中断来了多少次，都会让采样间隔抖动。采样间隔一抖：

- 记录波形时横轴没有意义，画出来的曲线会被拉伸压缩；
- 做 FFT 时，只有等时间间隔的样本才能正确对应到频率；
- 做控制（比如 PID）时，积分和微分都假设固定周期，周期抖动会让参数整定失效。

解决思路是把"什么时候转"交给一个不受 CPU 干扰的硬件：定时器周期性产生更新事件，通过 `TRGO`（Trigger Output）信号在芯片内部直接连到 ADC 的触发输入：

```text
TIMx Update/TRGO
-> ADC 规则组外部触发
-> 按 Rank 扫描一帧
-> 每次 EOC 请求 DMA
-> 缓冲区
```

### 9.2 定时器的配置

以 TIM3 每 1 ms 产生一次触发为例。假设系统时钟为 `72 MHz`、APB1 预分频为 `/2`，则 `PCLK1 = 36 MHz`。STM32F1 在 APB 预分频不为 `1` 时，定时器时钟为 `2 × PCLK1`（第 03、05 章讲过的倍频规则）：

$$f_{TIM}=2\times36\,\text{MHz}=72\,\text{MHz}$$

更新事件频率为：

$$f_{update}=\frac{f_{TIM}}{(PSC+1)(ARR+1)}$$

选择 `PSC = 71`、`ARR = 999`：计数频率 1 MHz，每 1000 个计数更新一次，即 1 kHz、1 ms。CubeMX 中 TIM3 的 `Clock Source` 选 `Internal Clock`，`Parameter Settings` 填上面两个值，再把 `Trigger Event Selection`（TRGO）设为 `Update Event`。生成的初始化核心代码：

```c
TIM_HandleTypeDef htim3;

void MX_TIM3_Init(void)
{
    TIM_MasterConfigTypeDef master = {0};

    htim3.Instance = TIM3;
    htim3.Init.Prescaler = 71U;
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim3.Init.Period = 999U;
    if (HAL_TIM_Base_Init(&htim3) != HAL_OK)
    {
        Error_Handler();
    }

    master.MasterOutputTrigger = TIM_TRGO_UPDATE;
    master.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
    if (HAL_TIMEx_MasterConfigSynchronization(&htim3, &master) != HAL_OK)
    {
        Error_Handler();
    }
}
```

`MasterOutputTrigger = TIM_TRGO_UPDATE` 是关键一行：它把"更新事件"路由到 TRGO（片内信号），每次计数到 ARR 并溢出归零时发出一个触发脉冲。`.ioc` 中对应的关键行：`TIM3.Prescaler=71`、`TIM3.Period=999`、`TIM3.MasterOutputTrigger=TIM_TRGO_UPDATE`。

### 9.3 ADC 侧与启动顺序

把 7.3 节配置里的软件触发换成定时器触发：ADC1 的 `External Trigger Conversion Source` 选 `T3_TRGO`，生成代码对应 `hadc1.Init.ExternalTrigConv = ADC_EXTERNALTRIGCONV_T3_TRGO`（`.ioc` 中 `ADC1.ExternalTrigConv=ADC_EXTERNALTRIGCONV_T3_TRGO`）。

单通道定时触发的可运行工程是第 6 章提到的 `HAL06_ADC\03_TimerTrigger`：TIM3 TRGO 触发 ADC1，主循环用 `HAL_ADC_PollForConversion()` 读值，PC13 每次转换完成翻转一次。把它与本章实验二的扫描 + DMA 组合，就得到定时触发的多通道采集。无论单通道还是多通道，启动顺序都是"校准 ADC -> 启动 ADC（DMA）-> 启动 TIM3"：

```c
if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK ||
    HAL_ADC_Start_DMA(&hadc1,
                      (uint32_t *)adc_values,
                      ADC_CHANNEL_COUNT) != HAL_OK ||
    HAL_TIM_Base_Start(&htim3) != HAL_OK)
{
    Error_Handler();
}
```

`HAL_ADC_Start()` / `HAL_ADC_Start_DMA()` 只在启动顺序里调用一次：它们让 ADC 进入"等待触发"状态，此后每次转换都由 TIM3 的 TRGO 发起。进入主循环后不要再手动触发，否则会在硬件节拍之外额外插入转换，打乱固定周期。`HAL_TIM_Base_Start()` 之前定时器不计数，所以它必须最后启动——先让 ADC 与 DMA 就绪、再打开触发源，也不会丢失第一个触发事件。

- 配合 **Circular**：数组填满后从头继续接收后续定时触发；
- 配合 **Normal**：数组填满一帧后 DMA 停止，定时器继续运行也不会自动重启 DMA；Normal 单帧的完整顺序是：停止 TIM3，处理完整帧，重新启动 ADC DMA，再启动 TIM3。

### 9.4 周期约束：一帧预算

若一次 TRGO 触发多个 Rank，必须保证一帧转换时间小于触发周期：

$$T_{frame}=\sum_{i=1}^{N}\left(T_{sample,i}+12.5\right)T_{ADC}$$

直观理解：第 6 章 4.1 节算的是"一个通道要多久"，多通道扫描就是把每个通道的时间加起来；一帧还没转完，下一次触发又来了，两帧数据就会撞车。例如 4 个通道都使用 `55.5` 周期、$f_{ADC}=12\,\text{MHz}$：

$$T_{frame}=4\times\frac{55.5+12.5}{12\,\text{MHz}}\approx22.67\,\mu\text{s}$$

`22.67 μs < 1 ms`，每 1 ms 触发一帧有充足余量；压缩触发周期时要重新计算并留出裕量。定时器 TRGO 的具体可用映射以目标芯片参考手册和 CubeMX 选项为准。

## 10. 从数组到物理量

DMA 搬进 `adc_values[]` 的只是 ADC 原码。这一节把常用的三类换算集中讲完。换算放在主循环里做，不要放进 DMA 完成回调——Normal 模式回调置位后数组已冻结，可直接处理；Circular 模式应先按 8.3 节的思路取得一致的一帧，再换算。

### 10.1 原码转电压

外部通道的电压换算沿用第 6 章 2.1 节的公式：

$$V_{in}\approx\frac{ADC\_Code}{4095}\times 3.3\,\text{V}$$

整数毫伏版（先转 `uint32_t` 防溢出，`+2047U` 做四舍五入补偿）：

```c
voltage_mv = ((uint32_t)code * 3300U + 2047U) / 4095U;
```

### 10.2 NTC 原码转温度

NTC（负温度系数热敏电阻）自己不输出电压，必须与固定电阻 $R_F$ 组成分压电路，ADC 测中点电压再反解。分压方向决定公式，先看接线：

| 接线 | 由原码反解 NTC 阻值 |
| --- | --- |
| $R_F$ 接 $VDDA$，NTC 接地 | $R_T=R_F\frac{ADC}{4095-ADC}$ |
| NTC 接 $VDDA$，$R_F$ 接地 | $R_T=R_F\frac{4095-ADC}{ADC}$ |

NTC 在下臂时升温使电压减小——"电压与温度方向相反"由接线决定，不是 ADC 错误。NTC 模块要用模拟输出 `AO`；比较器输出 `DO` 已把连续电压压成高低两个状态，信息丢失，不能接 ADC。

阻值到温度用 Beta 模型近似：

$$\frac{1}{T}=\frac{1}{T_0}+\frac{1}{B}\ln\left(\frac{R_T}{R_0}\right),\qquad T_{^\circ\mathrm{C}}=T-273.15$$

其中 $T$、$T_0$ 用开尔文，$R_0$ 是 $T_0$ 下的阻值，$B$ 是厂家参数——只知道"10 kΩ"确定不了温度曲线。以 $R_F=10\,\text{k}\Omega$ 接 VDDA、NTC 接地、原码 `1500`、$B=3950$ 为例：$R_T\approx10\,000\times\frac{1500}{4095-1500}\approx5.78\,\text{k}\Omega$，$T\approx37.9^\circ\text{C}$。

"原码 -> 阻值 -> 温度"可封装成一个短函数（无效码返回 `NAN`，不给显示和控制送垃圾值）：

```c
#include <math.h>
#include <stdint.h>

static float NTC_CodeToCelsius(uint16_t code)
{
    const float rf_ohm = 10000.0f;    /* 上臂固定电阻 */
    const float r0_ohm = 10000.0f;    /* T0 下的标称阻值 */
    const float t0_kelvin = 298.15f;  /* 25 ℃ */
    const float beta = 3950.0f;

    if (code == 0U || code >= 4095U)
    {
        return NAN;   /* 0=对地短路，4095=开路/未接，都不是有效分压 */
    }

    float resistance = rf_ohm * (float)code / (4095.0f - (float)code);
    float temperature_kelvin = 1.0f /
        ((1.0f / t0_kelvin) + logf(resistance / r0_ohm) / beta);

    return temperature_kelvin - 273.15f;
}
```

换用其他 NTC 时，必须同时替换 `rf_ohm`、`r0_ohm`、`beta`、参考温度和分压方向。NTC 自热、电阻误差、VREF 误差和 Beta 近似都会影响结果，看趋势比追绝对值更实际。

### 10.3 用 VREFINT 修正实际 VDDA 与内部通道采样时间

换算式成立的前提是"尺子上的满量程刻度画得准"，而 3.3 V 轨的实际电压谁也说不准。STM32F103 在片内集成了一个约 `1.20 V` 的基准源（VREFINT，数据手册范围 `1.16~1.24 V`），接在 ADC1 的 Channel 17：把这条"标准线"也量一遍，就能反推 VDDA 实际多长——推导思路与 2.1 节相反，是"已知真实电压，反解 VREF"：

$$V_{DDA}\approx V_{REFINT}\frac{2^N-1}{ADC_{VREFINT}},\qquad
V_{in}\approx\frac{ADC_{in}}{2^N-1}V_{DDA}$$

整数毫伏版（`+ vrefint_code / 2U` 仍是四舍五入补偿）：

```c
if (vrefint_code == 0U)
{
    vdd_mv = 0U;   /* 读取失败或无效码 */
}
else
{
    vdd_mv = (1200U * 4095U + vrefint_code / 2U) / vrefint_code;
}
```

`Vref` 的读数通常落在 `3200~3400 mV` 之间的某个稳定值；即使 VDDA 真是 3.300 V，它一般也不会恰好停在 3300——这更多反映 VREFINT 自身的个体差异，而不是电源真的不准。F103 没有 F0/F4/L4 等系列那样的 `VREFINT_CAL` 出厂标定数据，把 `1.20 V` 当固定常数只能得到近似补偿；需要更高精度时，用外部基准源或逐板标定。

内部通道的信号源是片内电路，内阻比外部引脚大，采样时间下限更高：VREFINT 约 `5.1 μs`，片内温度传感器约 `17.1 μs`——在 $f_{ADC}=12\,\text{MHz}$ 下分别对应至少 `71.5` 档（约 5.96 μs）和 `239.5` 档（约 19.96 μs）。扫描时让每个 Rank 使用自己的采样档位，不能把外部通道的 `55.5` 档直接套给内部通道。片内温度传感器只适合观察变化趋势，换算按数据手册给出的 25°C 典型电压和温度系数进行。

## 11. 本章验收

- [ ] 能说明每个 DMA 通道的源、目标和方向；
- [ ] 内存复制实验的数据前后已对比；
- [ ] ADC DMA 数组的 Rank 顺序已记录；
- [ ] CPU 不会在 DMA 正在写入时误读半帧；
- [ ] 能区分 DMA 配置、回调和数组所有权问题。

## 12. 故障定位

### 12.1 数组始终为 0

沿数据链检查：

```text
传感器输出
-> GPIO 是否为 Analog
-> ADC 通道与 Rank
-> ADC 是否启动
-> DMA1 Channel 1 是否使能
-> 外设地址与内存地址
-> 数组是否被程序重新清零
```

同时确认 `MX_DMA_Init()` 已执行，初始化顺序没有被手工改坏。

### 12.2 只有第一个数组元素变化

最常见原因是 Memory Increment 没有开启。DMA 每次都写 `adc_values[0]`，后续元素保持旧值。

### 12.3 四个值都有，但通道对应错误

检查 Rank 顺序、Number of Conversion、CubeMX 重新生成后的 Rank 是否变化，以及数组注释是否仍与配置一致。真正决定顺序的是 Rank，不是 `ADC_CHANNEL_0` 这样的通道名称。

### 12.4 数值截断、错位或数组越界

检查：

- ADC DMA 两端是否都是 Half Word；
- 数组是否为 `uint16_t[]`；
- 传输数量是否为元素数而不是字节数；
- 数组长度是否至少等于 DMA 数量；
- HAL API 要求的指针强制转换是否只改变类型，没有改变真实内存布局。

### 12.5 完成回调不执行

依次检查：

1. DMA1 Channel 1 的 NVIC 是否启用；
2. `DMA1_Channel1_IRQHandler()` 是否存在；
3. IRQ Handler 是否调用 `HAL_DMA_IRQHandler()`；
4. ADC 句柄是否通过 `__HAL_LINKDMA` 关联 DMA；
5. 回调函数名和参数是否正确；
6. DMA 是否真的完成了规定数量的传输。

### 12.6 第二次启动返回 `HAL_BUSY`

通常是上一轮仍在进行，或完成状态尚未收尾。工程内 `stm32f1xx_hal_dma.c` 的 `HAL_DMA_Start()` 在通道未回到就绪状态时直接返回 `HAL_BUSY`，不会等待。不要在 ADC DMA 仍 Busy 时重复调用 Start。Normal 单帧应遵守：

```text
Start -> Complete -> Process -> Start
```

### 12.7 连续模式数据不稳定

可能原因包括：

- Normal 模式加单帧采集，主循环没有重新启动——这是"只采一次就停"最常见的原因，对照 7.1 节的单帧数据链；
- ADC Continuous 开启，但 DMA 仍为 Normal；
- DMA Circular 开启，但 ADC 只转换一轮且没有新触发；
- CPU 读取时 DMA 正在覆盖数组；
- 采样时间过短，传感器源阻抗较高；
- 串口或 OLED 刷新改变了观察节拍；
- 模拟电源、接地或布线噪声较大。

先用 Normal 单帧模式验证每个 Rank，再切换连续模式，可以区分配置错误、缓冲区一致性和硬件噪声。

### 12.8 DMA 通道冲突

若 ADC、USART、I2C 或定时器同时使用 DMA，查芯片请求映射表。一个固定通道不能在同一时间服务两个互相冲突的外设请求；可让低流量外设改用中断、调整外设实例，或重新规划引脚和 DMA 资源。

### 12.9 内存复制实验失败

实验一的排查入口与实验二不同：它没有外设参与，问题只可能出在 DMA 配置、启动和等待三个环节，按症状定位：

- `destination` 全 0：确认 `MX_DMA_Init()` 在 `DMA_CopyOnce()` 之前执行；`HAL_DMA_Start()` 的返回值是否为 `HAL_OK`；源、目的地址传的是数组首地址，而不是误写成了 `&source[1]` 之类的元素地址；
- 卡死在 `HAL_DMA_PollForTransfer()`：通道没有真正跑起来，用调试器查看 `hdma_memtomem_dma1_channel1.State` 与剩余计数，再核对宽度、方向与模式；
- 第二次复制返回 `HAL_BUSY`：见 12.6 节，Normal 模式每次启动前必须等上一轮完成；
- `destination` 数据错位或截断：两端宽度与数组元素类型不一致，回到 3.3 节的匹配规则；
- 编译报 `hdma_memtomem_dma1_channel1` 未定义：调用处没有 `#include "dma.h"`，或句柄名与 CubeMX 实际生成的不一致（以 `dma.c` 中的名称为准）。

### 12.10 定时触发没有发生或节拍不对

按 9.1 节的触发链从定时器侧向 ADC 侧核对：

1. 定时器实际时钟：APB 预分频不为 1 时定时器时钟为 APB 的 2 倍（第 3 章）；
2. 重算 `(PSC+1)×(ARR+1)`；
3. TRGO 是否选择 Update Event（`TIM_TRGO_UPDATE`）；
4. ADC 外部触发源是否对应 `ADC_EXTERNALTRIGCONV_T3_TRGO`；
5. 启动顺序是否为"校准 -> ADC（DMA）-> TIM3"，主循环中没有再插入软件触发；
6. 实际 $f_{ADC}$ 按 3.2 节核对（分频配置见第 6 章）。

频率相差 2 倍或 6 倍，几乎都出在第 1、4 步。另一类症状是"触发频率正确但多通道帧不完整"：一帧转换时间超过触发周期，两帧数据撞车——按 9.4 节重算各 Rank 采样时间之和，确保 `T_frame < T_trigger`，必要时缩短采样档位或降低触发频率。

### 12.11 内部通道（VREFINT/温度传感器）读数明显不合理

内部通道只连接在 `ADC1` 上，按顺序核对：

1. 使用的实例确为 ADC1（`ADC2` 的 Channel 16/17 没有内部信号源）；
2. 采样时间是否分别至少 `71.5`、`239.5` 周期（10.3 节）；
3. 是否误用了 F103 不存在的 `VREFINT_CAL`/`TS_CAL` 出厂标定值；
4. 原码为 `0` 或 `4095` 时应判为无效（10.2 节的 `NAN` 分支），而不是继续换算。

上一篇：[[06 ADC：量化、采样时间与单次转换]] ｜ 下一篇：[[08 串口通信：轮询、中断、DMA 与蓝牙协议]]
