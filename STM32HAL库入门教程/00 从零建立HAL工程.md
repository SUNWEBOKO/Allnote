# 00 从零建立HAL工程

## 学习目标

- 在 CubeMX 中建立 STM32F103C8T6 工程。
- 用 VS Code 编译并通过 ST-LINK 下载程序。
- 区分 CubeMX 生成代码与自己维护的代码。
- 让板载 LED 周期闪烁。

## 本章问题

怎样从空白 CubeMX 工程建立一个能编译、下载和继续扩展的 HAL 底座？

后续章节都以工程能编译、程序能下载、LED 能受控为基础。本章先跑通这条链路，并把配置、构建和接线问题留在第一个实验中解决。

## 本章完成后得到什么

本章将建立一个可用 VS Code 官方 STM32 插件编译、下载和调试的 STM32F103C8T6 HAL 模板，并厘清 CubeMX 生成文件与用户代码的边界。不必在这一章掌握其他外设。

## 0. 实验准备

### 0.1 硬件

| 物品 | 说明 |
| --- | --- |
| STM32F103C8T6 最小系统板 | 俗称 Blue Pill 的蓝色小板，板载 LED 接在 `PC13` |
| ST-LINK 下载器 | 常见为 ST-LINK V2 蓝色小棒，负责把程序写进芯片 |
| 杜邦线 4 根 | 连接 ST-LINK 与最小系统板 |
| USB 数据线 | 给最小系统板或 ST-LINK 供电 |

本章实验只用板载 LED，不需要面包板和外接元件。

### 0.2 软件

| 软件                   | 用途                  | 本教程基线版本                      |
| -------------------- | ------------------- | ---------------------------- |
| STM32CubeMX          | 图形化配置芯片、生成初始化代码     | 6.17.0                       |
| VS Code + STM32 官方扩展 | 编辑、编译、下载、调试         | 扩展名 `stm32-vscode-extension` |
| STM32Cube FW_F1 固件包  | HAL 库源码，CubeMX 自动管理 | V1.8.7                       |
| ST-LINK 驱动           | 让 Windows 识别下载器     | 随 ST 官网驱动包                   |

版本号来自模板工程的配置基线（见第 3 节的模板基线），前后相差不大的版本一般也能照做；安装 CubeMX 时勾选 F1 系列固件包即可。

### 0.3 阅读代码时会用到的知识

本章代码用到 C 语言的变量和函数；后续章节还会用到指针、结构体和位运算（`&`、`|`、`<<`）。遇到 `GPIO_PIN_5` 这样的宏时，先按所在实验理解它的作用，不必先学完寄存器。接线只需注意电源极性和共地。

## 1. 三个工具怎么分工

初学者最容易混淆的是"我到底在哪个软件里干什么"。整条工作流只有三步：

```text
① 配置芯片          ② 编译               ③ 下载运行
STM32CubeMX    →    VS Code 插件      →   ST-LINK
产出 .c/.h 源码      GCC+CMake 编译        写入芯片并调试
（.ioc 是图纸）      产出 .elf 可执行文件    LED 开始闪烁
```

CubeMX 用于配置芯片并生成初始化代码；`.ioc` 保存引脚和外设配置，之后仍可用它修改工程。VS Code 的 STM32 官方扩展调用编译工具链，将源码构建为 `.elf` 文件。ST-LINK 通过 `SWDIO`、`SWCLK`、`GND` 和供电连接将程序下载到芯片，也用于调试。遇到故障时，先按生成、编译、下载三个环节定位，不必同时改动全部配置。


## 2. 先认识三个目录

| 目录 | 用途 | 是否直接修改 |
|---|---|---|
| `E:\ProjectStm\Courses\HAL00_CMake_Template` | 配套参考模板 | 只读参考 |
| `E:\ProjectStm\MyCode` | 你的个人复刻工程 | 主要修改这里 |
| `E:\ProjectStm\Courses\HAL01_GPIO` 及后续目录 | 各章节参考工程 | 只读对照 |

`Courses` 保持只读，才能在个人工程出现故障时对照原始配置。个人练习放在 `MyCode`，每个实验单独建工程，避免不同章节的外设配置互相影响。

个人复刻建议按章节建立独立目录，与第 1 章起各实验的工程名保持一致：

```text
E:\ProjectStm\MyCode\00_Template               （本章模板）
E:\ProjectStm\MyCode\01_GPIO\01_LED            （第 1 章实验一）
E:\ProjectStm\MyCode\01_GPIO\02_Key_Control_LED（第 1 章实验二）
```

不要把多个章节的 CubeMX 外设初始化代码混在同一个工程里。原因：每个章节引入的外设不同，混在一起后，一个章节的配置错误会污染所有实验，排查时无法区分是哪一章引入的问题。需要比较不同实验时，复制工程快照；不要复制旧的 `build/` 或 CMake 缓存——里面记录的是旧的绝对路径和编译中间产物，复制过去会导致编译错乱。

## 3. 新建工程：从空白开始

### 3.1 在 CubeMX 中新建（主线）

第一次建议亲手新建一个工程，把"选芯片 → 配引脚 → 配时钟 → 生成代码"整条路走一遍——这是后面每一章都要重复的基本功。逐步执行，关键步骤注明"你会看到什么"：

1. 打开 CubeMX，在首页选择 `ACCESS TO MCU SELECTOR`；
2. 在 `Commercial Part Number` 搜索框输入 `STM32F103C8`，选中 `STM32F103C8Tx`，双击进入配置界面——你会看到一块芯片引脚图，右侧是外设列表；
3. 在 `Pinout & Configuration` 页做三件事：
   - `System Core → RCC`：`HSE` 下拉选 `Crystal/Ceramic Resonator`（使用板载 8 MHz 晶振）；
   - `System Core → SYS`：`Debug` 下拉选 `Serial Wire`——不选它，SWD 下载引脚会被当成普通 GPIO 释放掉，程序将下载不进去；
   - 在芯片图上点 `PC13`，选 `GPIO_Output`（第 7 节的实验用）；
4. 切到 `Clock Configuration` 页把主频配到 72 MHz：`PLL Source Mux` 选 `HSE`，`PLLMul` 选 `x9`，`System Clock Mux` 选 `PLLCLK`；`APB1 Prescaler` 选 `/2`，APB2 保持 `/1`。配置完成后 `HCLK` 应显示 `72`；
5. 切到 `Project Manager` 页：`Project Name` 填 `HAL00_LedBlink`，`Project Location` 选到 `E:\ProjectStm\MyCode`，`Toolchain/IDE` 下拉选 `CMake`；
6. `Code Generator` 页保持默认；
7. 点右上角 `GENERATE CODE`。生成成功后，工程目录里会出现 `.ioc`、`Core/`、`Drivers/`、根 `CMakeLists.txt`、`cmake/`、启动文件和链接脚本——这正是 4.1 节要讲的"CubeMX 管的文件"。

### 3.2 捷径：复制模板工程

时间紧张时也可以复制参考模板起步，配置与 3.1 完全一致：

1. 在文件管理器中把 `E:\ProjectStm\Courses\HAL00_CMake_Template` 整个文件夹复制到 `E:\ProjectStm\MyCode\` 下，重命名为 `HAL00_LedBlink`；
2. 改名必须同步两处：用文本编辑器把根 `CMakeLists.txt` 里的 `set(CMAKE_PROJECT_NAME HAL00_CMake_Template)` 改成新名字；再用 CubeMX 打开 `.ioc`，在 `Project Manager` 页把 `Project Name` 也改成同一个新名字并重新生成——两处名字不一致，后面打开和编译都会混乱，且"工程名 = 章节主题"的系列惯例从源头就断了；
3. 用 VS Code 打开复制后的工程根目录（"文件 → 打开文件夹"，选的是工程根目录本身，不是它的上级或 `build/`）。

无论走哪条路径，本章工程的配置基线如下：

- MCU：STM32F103C8T6（48 引脚，64 KB Flash，20 KB RAM，本教程全系列用同一颗芯片）；
- CubeMX：6.17.0；
- STM32Cube FW_F1：V1.8.7；
- HSE 8 MHz + PLL×9，SysClock 72 MHz（板载 8 MHz 外部晶振，经 9 倍频得到 72 MHz 主频，这是 F103 的标准最高主频，第 3 章专门讲）；
- APB1 36 MHz，APB2 72 MHz（两条低速/高速外设总线，挂在不同总线上的外设时钟不同）；
- PA13/PA14 保留 SWD（这两根是调试下载线，永远不要配置成普通 GPIO，否则程序下载不进去）；
- C11 + GCC + CMake（C 语言标准、编译器和构建系统，均由插件管理）。

## 4. CubeMX 和用户代码的边界

这是本章最重要的概念，直接决定你后面会不会"代码神秘消失"。

### 4.1 CubeMX 负责什么

CubeMX 负责生成：

```text
Core/
Drivers/
startup_stm32f103xb.s
STM32F103XX_FLASH.ld
```

也负责生成 GPIO、TIM、ADC、I2C、USART 等外设的初始化函数。

- `Core/` 是主程序和中断处理所在，`main.c` 就在 `Core/Src/` 里；
- `Drivers/` 是 ST 官方 HAL 库源码，量很大但不需要逐个读，用到哪个函数再看哪个；
- `startup_*.s` 是启动文件，芯片上电后先执行它（初始化堆栈、把中断向量表摆好），再跳进 `main()`；
- `.ld` 是链接脚本，告诉编译器这颗芯片有多少 Flash 和 RAM、代码放在哪。

每次在 CubeMX 里改完配置点 `GENERATE CODE`，上述文件都会按 `.ioc` 图纸重新生成。

### 4.2 自己负责什么

自己编写的代码放在：

```text
User/Inc/
User/Src/
User/Drivers/
```

少量入口改动可以放在：

```c
/* USER CODE BEGIN ... */
/* USER CODE END ... */
```

> 说明：上面 `User/` 目录在新建工程里并不存在，需要自己在工程根目录下创建（第 2 章引入第一个驱动时动手建，并在第 5 节的 CMakeLists 里登记）。

打开 `Core/Src/main.c` 能看到很多 `USER CODE BEGIN n` / `USER CODE END n` 成对注释。重新生成代码时，CubeMX 只重写这些区域**以外**的内容，区域内的代码原样保留。

看一个具体对比：

```c
/* USER CODE BEGIN 2 */
HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);  /* 安全：在区域内 */
/* USER CODE END 2 */
```

```c
HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);  /* 危险：在区域外，
   下次 GENERATE CODE 时这一行会直接消失 */
```

为什么要遵守这条边界？CubeMX 每次按 `.ioc` 重新生成代码，可能覆盖自动生成区域中的手写内容；而 `USER CODE` 区域和自己创建的 `User/` 目录用于保留手写代码。修改配置后若功能突然消失，先检查代码原先写在什么位置。

不要把长期维护的驱动直接写进 CubeMX 自动生成区域。OLED、传感器这类成百上千行的驱动统一放 `User/Drivers/`，只在 `USER CODE` 区域留几行调用。

### 4.3 改了配置如何重新生成

在 CubeMX 中完成修改后，点右上角 `GENERATE CODE` 按钮（或菜单 `Project → Generate Code`）。生成成功后 CubeMX 会询问是否直接打开工程，选否即可，回到 VS Code 重新编译。重新生成不影响 `User/` 目录和 `USER CODE` 区域内的内容。

## 5. CMakeLists 只登记自己的内容

先理解“登记”：CMake 根据源文件列表决定编译哪些 `.c` 文件。文件即使已经放进工程目录，未加入编译目标也不会参与链接。

CubeMX 生成的 `cmake/stm32cubemx/CMakeLists.txt` 管理 Core 源文件。根目录 `CMakeLists.txt` 主要登记自己新增的源文件、头文件目录和驱动库：

```cmake
target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    User/Src/main_app.c
    User/Drivers/OLED/OLED.c
)

target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    User/Inc
    User/Drivers/OLED
)
```

逐块解释：

- `target_sources(... PRIVATE ...)`：把括号里列出的 `.c` 文件加入编译清单。你每写一个新的 `.c` 文件，就要在这里加一行路径；
- `target_include_directories(... PRIVATE ...)`：告诉编译器"去这些目录找 `#include` 的头文件"。漏了它，编译时会报 `fatal error: xxx.h: No such file or directory`；
- 如果驱动已经编译成独立库，再使用 `target_link_libraries()` 加入库目标；
- 每个源文件只登记一次，重复登记会产生重复定义错误。

忘记登记的典型症状：编译报 ``undefined reference to `oled_init'``——函数明明写了、头文件也包含了，就是因为 `.c` 文件没进编译清单。

## 6. VS Code 官方 STM32 插件流程

1. 用 VS Code 打开工程根目录，不要打开 `build/` 目录；
2. 打开 STM32 官方插件，让它读取 CubeMX 生成的 CMake 配置；
3. 选择 `Debug` 配置（位于底部状态栏或 CMake 侧边栏；`Debug` 带调试信息，适合学习阶段）；
4. 使用插件的 Build/编译按钮（也可按 `F7`），底部输出面板会滚动显示编译进度；
5. 确认编译输出中生成 `.elf`（输出末尾出现 `Build finished` 且无 `error`；`.elf` 在 `build/Debug/` 下，具体路径以输出面板显示为准）；
6. 连接 ST-LINK 后，使用插件的 Download/Flash 或 Debug 功能下载；
7. 复位后观察程序现象。

ST-LINK 与最小系统板的接线（4 根线，注意共地）：

```text
ST-LINK   →   最小系统板
SWDIO     →   SWDIO (PA13)
SWCLK     →   SWCLK (PA14)
GND       →   GND
3.3V      →   3.3V
```

工具链、HAL 库、启动文件和 CMake 预设由 CubeMX 与插件处理。新手不需要手动编写编译命令。

## 7. 第一个最小实验：LED 闪烁

### 7.1 实验目标

只用板载 LED，验证整条工具链是通的。代码只验证三件事：

```text
CubeMX 是否生成 GPIO 初始化
→ VS Code 插件是否能编译
→ ST-LINK 是否能下载和运行
```

板载 LED 接在 `PC13`，且是低电平点亮：引脚输出 `0` 时 LED 亮，输出 `1` 时灭（板载 LED 阳极经限流电阻接电源、阴极接 `PC13`，电流从电源流经 LED 灌入引脚，所以拉低才亮）。为什么第一次实验选它？因为不用接任何线，排除接线因素。

### 7.2 CubeMX 配置

1. 在 `.ioc` 的芯片图上点击 `PC13` 引脚，选 `GPIO_Output`；
2. 此时引脚变为绿色。右键 `PC13` → `Enter User Label` 可以给它起名（可选）；
3. 在 `GPIO` 详细配置里确认：`GPIO output level` 选 `High`（上电默认灭），`GPIO Mode` 为 `Output Push Pull`，`GPIO Pull-up/Pull-down` 为 `No pull-up and no pull-down`，`Maximum output speed` 为 `Low`；
4. 点 `GENERATE CODE`，回到 VS Code。

各配置项的含义现在只需记住结论，原理在第 1 章展开：推挽输出是最普通的输出方式，能主动输出高低电平；初始 `High` 让 LED 上电时保持熄灭；低速档对 LED 完全够用。第 1 章的参考工程会改用开漏输出，对本实验的现象没有影响，差别在第 1 章展开。

### 7.3 写代码

打开 `Core/Src/main.c`，找到 `while (1)`。CubeMX 生成的骨架是空的：

```c
while (1)
{
    /* USER CODE END WHILE */
    /* USER CODE BEGIN 3 */
}
```

把两行用户代码写进循环体后应类似：

```c
/* USER CODE BEGIN WHILE */
while (1)
{
    HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);  /* 翻转 PC13 电平：亮变灭，灭变亮 */
    HAL_Delay(500U);                         /* 阻塞等待 500 毫秒 */
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
}
/* USER CODE END 3 */
```

逐行说明：

- `HAL_GPIO_TogglePin()` 是 HAL 库提供的"翻转"函数，每调用一次，`PC13` 电平取反一次，LED 亮灭状态切换一次；
- `HAL_Delay(500)` 让 CPU 原地等待 500 ms，期间什么都不做。它是入门阶段最方便的延时手段，缺点是"干等"（阻塞），后面的章节会换成定时器等不阻塞的方式。

### 7.4 编译、下载、观察

1. 按 Build，确认输出 `Build finished`；
2. 确认 ST-LINK 四根线接好、板子通电；
3. 点 Download/Flash，输出面板显示下载进度直至完成；
4. 观察板载 LED：应当每 500 ms 亮灭交替，稳定闪烁。

完成下载后，板载 LED 应每 500 ms 切换一次亮灭状态；这同时验证了 GPIO 初始化、编译和下载链路。

### 7.5 LED 不闪时的三个检查

| 现象 | 最可能原因 | 处理 |
| --- | --- | --- |
| 编译就失败 | 代码写在了 `USER CODE` 区域外，或区域标记被破坏 / 源文件未登记 | 检查代码位置；看第 5 节登记方法 |
| 编译成功但下载失败 | ST-LINK 没接好、驱动没装、引脚被占用 | 检查 4 根线与驱动；确认 PA13/PA14 保持 SWD |
| 下载成功但 LED 常亮/常灭 | 初始电平设错或 `HAL_Delay` 单位误解 | 确认初始 `High`；确认延时 500 是毫秒不是秒 |

更深入的故障排查在第 1 章的"常见故障排查"一节。

## 8. 本章验收

- [ ] `MyCode` 中有自己命名的新工程（不是与参考模板同名的副本）；
- [ ] VS Code 能打开工程并识别 CMake 配置；
- [ ] Debug 编译成功；
- [ ] ST-LINK 能下载和复位；
- [ ] LED 按预期工作（500 ms 闪烁）；
- [ ] 能指出哪些文件由 CubeMX 生成；
- [ ] 能只在根 `CMakeLists.txt` 中登记自己的源文件。

下一篇：[[01 GPIO：引脚、八种模式与 HAL 读写]]
