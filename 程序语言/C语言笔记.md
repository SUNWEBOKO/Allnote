# C 语言笔记
> **本笔记从编译器视角、函数/架构视角、内存/硬件视角** 理解 C，而不是只把 C 当成语法清单。

---

## 0. 学习 C 的总主线：为什么嵌入式开发离不开它

C 语言之所以在嵌入式领域长期占据核心地位，不只是因为“历史悠久”，而是因为它同时具备三种能力：

1. **靠近硬件**：可以直接操作内存、寄存器、位段、地址。
2. **结果可控**：编译过程清晰，代码体积、性能、内存布局都相对可预测。
3. **可以写工程架构**：虽然不是面向对象语言，但依然能借助结构体、函数指针、回调、`void *`、`weak` 等机制写出很强的模块化代码。

所以学 C 时，不要只问“这句语法怎么写”，还要问：

- 编译器会怎么处理它？
- 这段代码会落到哪块内存？
- 它为什么适合驱动、裸机、RTOS、Linux 内核这样的场景？

---

## 0.5 基础知识预备

### 0.5.1 C 语言概述

C 语言由 Dennis Ritchie 于 1972 年在贝尔实验室设计开发，属于面向过程的高级语言，兼具接近硬件的底层操作能力。它是编译型语言，先全部编译成目标代码再执行：

```
编写(.c) → 编译(.obj) → 链接(.exe) → 运行
```

编译程序将源程序翻译成目标代码（二进制机器代码）；链接程序将目标文件与库文件组合成可执行程序。

### 0.5.2 程序基本结构

每个 C 程序从 `main` 函数开始执行，到 `main` 函数结束。一个完整的 C 程序有且只能有一个 `main` 函数。

```c
#include <stdio.h>

int main()
{
    printf("hello c");
    return 0;
}
```

核心：`#include <stdio.h>` 包含标准输入输出头文件（注意不是 `studio.h`）；`main` 是入口；`printf` 输出；`return 0;` 返回操作系统，0 表示正常退出。

**注释：** 单行 `//`，多行 `/* */`。编译时被忽略，不影响执行。

**缺少 main 函数的链接错误：** 编译阶段不报错，链接阶段报 `undefined reference to WinMain@16`（Windows）或 `undefined reference to main`（一般环境）。

### 0.5.3 关键字与标识符

**关键字**是 C 语言本身规定好的特殊含义单词，不能被用来命名变量或函数。常见：`int` `return` `char` `float` `double` `short` `long` `unsigned` `for` `while` `if` `else` `switch` `case` `break` `continue` `void` `struct` `union`。注意 `main` 不是关键字，`include` 也不是关键字。

**标识符**命名规则：
1. 只能由字母、数字和下划线 `_` 构成
2. 不能以数字开头
3. 不能是 C 语言关键字

合法：`x` `sum` `count` `a123` `_str1` `num_2`。不合法：`3abc`（数字开头）、`a+b`（含非法字符）、`case`（关键字）。

### 0.5.4 进制基础

| 进制 | 字符 | 示例 | C 前缀 |
|------|------|------|--------|
| 十进制 | 0~9 | 10 | 无 |
| 八进制 | 0~7 | 017 = 十进制15 | 前导 `0` |
| 十六进制 | 0~9, A~F | 0x10 = 16 | `0x` 或 `0X` |

注意：`010` 是八进制（= 8），`0x10` 是十六进制（= 16）。

### 0.5.5 变量

变量必须先声明后使用：

```c
int count;          // 声明
int number = 100;   // 声明并初始化
number = 200;       // 赋值
```

多个变量同时声明用逗号：`int a, b, c;`。`int a; b; c;` 错误——b 和 c 缺类型。

易错点：
- 不能重复声明：`int a = 10; int a = 20;` 错误
- 声明时不允许连续初始化：`int x = y = 10;`（若 `y` 未声明则错误；已声明时合法但不建议）
- 声明后可连续赋值：`int x, y; x = y = 10;` 正确（从右向左）

### 0.5.6 基本数据类型

不同平台/ABI 下类型大小可能不同。常见 64 位系统分 LP64（Linux/macOS/UNIX）和 LLP64（Windows）两种 ABI。下表为 32 位环境典型值：

| 类型 | 关键字 | 典型字节(32位) | `printf` | `scanf` |
|------|--------|---------------|----------|---------|
| 字符型 | `char` | 1 | `%c` | `%c` |
| 短整型 | `short` | 2 | `%hd` | `%hd` |
| 整型 | `int` | 4 | `%d` | `%d` |
| 长整型 | `long` | 4 或 8（LP64 下 8，LLP64 下 4） | `%ld` | `%ld` |
| 无符号整型 | `unsigned int` | 4 | `%u` | `%u` |
| 单精度浮点 | `float` | 4 | `%f` | `%f` |
| 双精度浮点 | `double` | 8 | `%f` | `%lf` |

> **ABI 速查：** LP64（`int=4, long=8, ptr=8`）用于 Linux/macOS；LLP64（`int=4, long=4, ptr=8`）用于 Windows 64 位。`long long` 保证至少 8 字节。实际大小请用 `sizeof` 确认，勿做硬编码假设。

### 0.5.7 字符型与 ASCII 码

字符在 C 中以整数编码（ASCII 码）存储。三组必须记忆的范围：

| 字符 | ASCII 值 |
|------|---------|
| `'0'` ~ `'9'` | 48 ~ 57 |
| `'A'` ~ `'Z'` | 65 ~ 90 |
| `'a'` ~ `'z'` | 97 ~ 122 |

大小写相差 32：`'a' - 'A' = 32`。字符数字转整数：`c - '0'`（如 `'9'` → 57 - 48 = 9）。

### 0.5.8 转义字符

| 转义 | 含义 |
|------|------|
| `'\0'` | 空字符，数值 0 |
| `'\n'` | 换行 |
| `'\''` | 单引号 |
| `'\"'` | 双引号 |
| `'\\'` | 反斜杠 |

八进制转义：`'\141'`（八进制141 = 十进制97 = `'a'`）。十六进制转义：`'\x6d'`（= `'m'`）。

### 0.5.9 浮点型

```c
float x = 3.14f;     // 4 字节
double y = 3.14;     // 8 字节
```

小数一边为 0 时可省略：`1.` = `1.0`，`.1` = `0.1`。

科学计数法：`2.55e1` = 2.55×10¹ = 25.5，`1.23e4` = 12300，`2.75e-3` = 0.00275。规则：`e` 前后都必须有数字，且后面必须是整数。

### 0.5.10 本章典型例题

**例题1：** C 语言程序从哪里开始执行？
答案：从 `main` 函数开始执行，无论 `main` 是否写在最前面。

**例题2：** 以下说法正确的是？
A. 从第一个定义的函数开始  B. 调用的函数必须在 main 中定义  C. 总是从 main 开始  D. main 必须放在开头
答案：C

**例题3：** 合法标识符是？A. `3ax`  B. `x`  C. `case`  D. `e-2`  E. `union`
答案：B

**例题4：** 下面关于 C 语言数值表示正确的是？
A. `0x10` 是十六进制  B. `010` 是十进制 10  C. `101010` 是二进制  D. `10` 是十六进制
答案：A

**例题5：** 变量声明赋值正确的是？
A. `int x = y = 10;`  B. `int a = 10; int a = 20;`  C. `int x, y; x = y = 10;`  D. `x = 10;`
答案：C

**例题6：** `ch` 是字符型，不正确的赋值是？
A. `ch = 'a+b';`  B. `ch = '\0';`  C. `ch = '7' + '9';`  D. `ch = 5 + 9;`
答案：A（单引号内不能放多个普通字符）

**例题7：** 浮点数说法正确的是？
A. `float` 精度更高  B. `1.23e4` = 12300  C. `int` 能表示浮点数  D. `double` 不能表示负数
答案：B

---

## 1. 编译流程与工具链

C 源程序从源码到可执行文件，通常经历四个阶段：**预处理 -> 编译 -> 汇编 -> 链接**。

### 1.1 流程图示

```text
hello.c -> 预处理 -> hello.i -> 编译 -> hello.s -> 汇编 -> hello.o -> 链接 -> a.out
```

### 1.2 每一阶段详解

| 阶段 | 主要任务 | 输出文件 | 关键工具 |
|------|----------|----------|----------|
| 预处理 | 展开 `#include`、`#define`、条件编译 | `.i` | cpp / gcc -E |
| 编译 | 语法/语义检查，生成汇编 | `.s` | gcc / clang |
| 汇编 | 汇编转机器码 | `.o` | as |
| 链接 | 合并段、解析符号、重定位 | 可执行文件 | ld / gcc |

### 1.3 常用命令

```bash
# 仅预处理
gcc -E hello.c -o hello.i

# 生成汇编
gcc -S hello.c -o hello.s

# 生成目标文件（不链接）
gcc -c hello.c -o hello.o

# 链接成可执行文件
gcc hello.o -o hello

# 一步到位编译
gcc hello.c -o hello

# 查看详细编译过程
gcc -v hello.c -o hello
```

### 1.4 三类常见错误

#### 预处理错误

常见于：

- 头文件找不到
- 条件编译写错
- 宏展开破坏语法

#### 编译错误

常见于：

- 类型不匹配
- 语法错误
- 未声明标识符

#### 链接错误

常见于：

- `undefined reference`
- `multiple definition`
- 缺少库文件或重复定义函数

> 看到 `ld returned ...`、`undefined reference`、`multiple definition` 这类信息，就要优先想到：**问题已经到了链接阶段**。

### 1.5 Linux 下常用开发工具

- **vim**：文本编辑器
- **gcc**：编译器
- **gdb**：调试器

GDB 的核心动作可以概括为四件事：

1. 启动程序
2. 让程序停下来
3. 看现场
4. 改状态再试

常用命令：

```bash
gdb program
b main
r
n
c
p var
set var var = 10
x 0x12345678
info r
disass
```

### 1.6 开发环境与 IDE 操作

**Code::Blocks 项目管理：**
- `.c` 源文件放在项目的 **Sources** 目录下
- `.h` 头文件放在项目的 **Headers** 目录下
- 保存项目：File → Save project

**编译与运行：**
- 编译报错查找：查看 Build log 窗口，关注 `error:` 行
- 缺少 `main` 函数时 Build log 显示 `undefined reference to WinMain@16`（Windows/MinGW）或 `undefined reference to main`（其他环境）
- 控制台窗口一闪而过：`system("pause")` 是 Windows 特有做法，可移植方案是用 IDE 保持终端或调试器启动

**调试操作：**
- 断点：点击行号左侧，程序运行到该行暂停
- 单步执行：逐行观察变量值变化
- 观察变量：将鼠标悬停在变量上，或在 Watches 窗口查看

**常见快捷键：**
- F9：编译并运行
- F8：编译
- 调试：F5（启动）、F7（单步）、Shift+F7（步入函数）

### 1.7 计算机基础补充

**冯·诺依曼体系：** 采用二进制 + 存储程序（程序和数据存储在内存中自动执行）。

**CPU：** 中央处理器，计算机的运算和控制核心。

**硬件与软件：** 硬件是躯壳，软件是灵魂，相互依存。

**系统软件：** 包括操作系统、语言处理程序、数据库管理系统等。

**算法特性：** 有穷性、确定性、可行性、输入、输出。

**程序 = 数据结构 + 算法。** 数据结构组织数据，算法处理数据。

---

## 2. 注释与代码风格

### 2.1 注释类型

```c
// 单行注释

/* 单行块注释 */

/*
   多行注释
   多行注释
*/
```

### 2.2 注释原则

- 注释应解释“**为什么这样写**”，而不是逐行翻译“这行代码做了什么”。
- 复杂指针、位操作、状态机、资源回滚路径，应该写清设计意图。
- 注释必须跟代码一起维护，过期注释比没注释更危险。

### 2.3 嵌入式代码风格建议

- 变量定义尽量初始化。
- 宏常量、位掩码、寄存器字段尽量命名清晰。
- 函数职责单一。
- 驱动接口与业务逻辑分层。

---

## 3. 预处理与条件编译

所有预处理器命令都以 `#` 开头，并在编译正式开始前执行。

### 3.1 常见预处理指令

| 指令 | 描述 | 示例 |
|------|------|------|
| `#define` | 定义宏 | `#define PI 3.14159` |
| `#include` | 包含头文件 | `#include <stdio.h>` |
| `#ifdef` | 宏已定义则编译 | `#ifdef DEBUG` |
| `#ifndef` | 宏未定义则编译 | `#ifndef HEADER_H` |
| `#if` | 条件编译 | `#if VERSION > 2` |
| `#elif` | 否则若 | `#elif defined(__linux__)` |
| `#else` | 否则 | - |
| `#endif` | 结束条件编译 | - |
| `#error` | 主动产生编译错误 | `#error "需要 C99"` |
| `#pragma` | 编译器特定指令 | `#pragma once` |

### 3.2 头文件保护

```c
#ifndef HEADER_H
#define HEADER_H

/* 头文件内容 */

#endif
```

或：

```c
#pragma once
```

### 3.3 条件编译的典型用途

#### 跨平台适配

```c
#ifdef _WIN32
    #include <windows.h>
#elif defined(__linux__)
    #include <unistd.h>
#elif defined(__APPLE__)
    #include <mach/mach.h>
#endif
```

#### Debug / Release 切换

```c
#include <stdio.h>
int password = 0x37847110;

int main(void) {
#ifdef DEBUG
    printf("debug log: password = %x\n", password);
#else
    printf("release version\n");
#endif
    return 0;
}
```

编译时启用：

```bash
gcc -DDEBUG main.c -o main
```

#### 选择性编译模块

```c
#define USE_FEATURE_A 1
#define USE_FEATURE_B 0

#if USE_FEATURE_A
void feature_a(void) { }
#endif

#if USE_FEATURE_B
void feature_b(void) { }
#endif
```

### 3.4 预处理的本质

预处理是**文本级处理**，不是语义级分析。

这意味着：

- 它功能很强
- 但也很容易埋坑
- 很多宏问题不是“运行时 bug”，而是“展开后代码长得已经不对”

---

## 4. 宏（`#define`）详解

### 4.1 常量宏

```c
#define PI 3.14159
#define MAX_BUFFER_SIZE 1024
#define ERROR_MSG "An error occurred"
```

### 4.2 函数式宏

```c
#define MAX(x, y) ((x) > (y) ? (x) : (y))
#define SQUARE(x) ((x) * (x))
#define SWAP(a, b) do { typeof(a) _t = (a); (a) = (b); (b) = _t; } while(0)  // GNU 扩展：typeof
```

### 4.3 字符串化运算符 `#`

```c
#define PRINT_INT(x) printf(#x " = %d\n", x)
```

### 4.4 标记粘贴运算符 `##`

```c
#define CONCAT(a, b) a ## b
#define MAKE_FUNC(name) int func_##name(void) { return 0; }
```

### 4.5 宏延续运算符 `\`

```c
#define MESSAGE_FOR(a, b) \
    printf(#a " and " #b ": We love you!\n")
```

### 4.6 常用编译器内建宏

| 宏 | 描述 |
|----|------|
| `__DATE__` | 编译日期 |
| `__TIME__` | 编译时间 |
| `__FILE__` | 当前文件名 |
| `__LINE__` | 当前行号 |
| `__func__` / `__FUNCTION__` | 当前函数名 |
| `__STDC__` | 是否符合标准 C |

### 4.7 调试日志宏

```c
#ifdef DEBUG
#define LOG(fmt, ...) \
    fprintf(stderr, "[%s:%d %s] " fmt "\n", \
            __FILE__, __LINE__, __func__, ##__VA_ARGS__)  // GNU 扩展：##__VA_ARGS__
#else
#define LOG(fmt, ...)
#endif
```

### 4.8 宏的三大高频坑

#### 坑 1：宏体不加括号

```c
#define ABC 10 + 2
int a = ABC * 10;   // 实际变成 10 + 2 * 10
```

#### 坑 2：参数不加括号

```c
#define MIN(A, B) (A < B ? A : B)
```

如果 `A` 或 `B` 本身是表达式，优先级可能错乱。

#### 坑 3：参数重复求值

```c
#define MIN(A, B) ((A) < (B) ? (A) : (B))
```

若调用：

```c
MIN(a++, b)
```

可能让 `a++` 执行多次。

### 4.9 更安全的 GNU 风格写法（GNU 扩展，非 ISO C）

```c
#define MIN(A, B) ({             \
    typeof(A) _a = (A);          \
    typeof(B) _b = (B);          \
    _a < _b ? _a : _b;           \
})
```

> 上述写法依赖 GNU 扩展：`typeof` 和语句表达式 `({...})`。若需严格 ISO C 兼容，用 `_Generic`（C11）或内联函数替代。

### 4.10 `#define` 与 `const` 的区别

| 对比项 | `#define` | `const` |
|--------|-----------|---------|
| 生效阶段 | 预处理阶段 | 编译/运行语义阶段 |
| 类型检查 | 无 | 有 |
| 本质 | 文本替换 | 只读对象 |
| 调试友好性 | 一般 | 更好 |

> 工程里能用 `const` 表达“只读语义”的地方，通常优先用 `const`；宏更适合常量表达式、位掩码、条件编译和元编程场景。

---

## 5. 数据类型与 `sizeof`

### 5.1 基本数据类型

| 类型 | 说明 | 典型大小 |
|------|------|----------|
| `char` | 字符型 | 1 字节 |
| `short` | 短整型 | 2 字节以上 |
| `int` | 整型 | 4 字节常见 |
| `long` | 长整型 | 平台相关 |
| `long long` | 更长整型 | 至少 8 字节 |
| `float` | 单精度浮点 | 4 字节 |
| `double` | 双精度浮点 | 8 字节 |
| `void` | 空类型 | 无 |

> 跨平台代码推荐使用 `<stdint.h>` 中的固定宽度类型：`int8_t`、`uint16_t`、`int32_t`、`uint64_t`、`intptr_t` 等。这样不依赖 `int` / `long` 的平台定义。

### 5.2 整型修饰符

```c
short s;
long l;
long long ll;
unsigned int ui;
signed char c;
```

### 5.3 `sizeof` 的本质

`sizeof(x)` 用于查看对象或类型占用的**字节数**。

```c
sizeof(int)
sizeof(arr)
sizeof(struct abc)
```

### 5.4 关于 `sizeof` 的重要理解

- 它关注的是**内存大小**，不是元素个数。
- 它往往在**编译阶段**就能确定。
- 它不是普通函数调用，虽然写法像函数。

### 5.5 数组长度常见写法

```c
int arr[10];
size_t len = sizeof(arr) / sizeof(arr[0]);
```

> 这个写法只在**当前作用域里 arr 仍然是数组**时成立；传参后退化为指针就不成立了。

### 5.6 浮点数比较

浮点数在计算机中用二进制表示，许多十进制小数无法精确表示（如 0.1 是无限循环小数）。用 `==` 直接比较两个浮点数不可靠。

正确方法：**判断两数之差的绝对值是否小于误差阈值。**

```c
#include <math.h>

if (fabs(a - b) < 1e-6) {
    // a 和 b 被认为相等
}
```

**三角形类型判断中的应用：**

```c
int isEquable(double x, double y) {
    return fabs(x - y) < 1e-6;
}

void checkTriangle(double a, double b, double c) {
    if (a + b > c && b + c > a && a + c > b) {
        if (isEquable(a, b) && isEquable(b, c))
            printf("等边三角形");
        else if (isEquable(a, b) || isEquable(b, c) || isEquable(a, c))
            printf("等腰三角形");
        else if (isEquable(a*a + b*b, c*c) ||
                 isEquable(b*b + c*c, a*a) ||
                 isEquable(a*a + c*c, b*b))
            printf("直角三角形");
        else
            printf("一般三角形");
    } else {
        printf("不是三角形");
    }
}
```

---

## 6. 变量、常量与作用域

### 6.1 变量声明与定义

```c
int a;        // 声明并定义
extern int b; // 声明（定义在别处）
```

### 6.2 作用域

- **块作用域**：如函数内部、`if` / `for` / `{}` 内部
- **文件作用域**：函数外定义的全局变量

### 6.3 生命周期

- 自动变量：进入作用域创建，离开作用域销毁
- 静态变量：程序运行期间一直存在
- 动态内存：`malloc` 后存在，`free` 后释放

### 6.4 枚举常量

```c
enum Color {
    RED,
    GREEN,
    BLUE
};
```

### 6.5 用宏定义常量

```c
#define PI 3.14159
```

### 6.6 用 `const` 定义只读对象

```c
const int MAX_SIZE = 100;
```

---

## 7. 运算符与表达式

### 7.1 算术运算符

五种基本算术运算符：`+` `-` `*` `/` `%`

**整数除法截断：** `/` 两边都是整数时执行整数除法，结果舍弃小数部分。

```c
5 / 2   // 结果是 2，不是 2.5
10 / 3  // 结果是 3
```

**浮点除法触发：** 至少一个操作数为浮点数，结果保留小数。

```c
5.0 / 2   // 结果是 2.5
5 / 2.0   // 结果是 2.5
```

**求余 `%`：** 两边必须都是整数。

```c
10 % 3    // 结果是 1
10.0 % 3  // 错误
```

**同级从左到右：**

```c
3 * 20 / 4 % 10    // 60/4=15, 15%10=5, 结果为 5
```

**除零保护：** 整数除法 `/` 和求余 `%` 的除数都不能为 0，否则程序崩溃。

### 7.2 自增与自减

| 表达式 | 行为 | 表达式值 | 变量最终值 |
|--------|------|---------|-----------|
| `++a` | 先加后用 | a+1 | a+1 |
| `a++` | 先用后加 | a（旧值） | a+1 |
| `--a` | 先减后用 | a-1 | a-1 |
| `a--` | 先用后减 | a（旧值） | a-1 |

口诀：加加在前先加后用，加加在后先用后加；减减在前先减后用，减减在后先用后减。

```c
int a = 5;
int b = ++a;   // a=6, b=6
int c = a++;   // a=7, c=6
```

`++` 和 `--` 也可用于 `float`、`double`。

**例题：** `int x=5; printf("%d", x++);` 输出？
答案：5。后置自增先用旧值，输出后 x 变为 6。

### 7.3 赋值与复合赋值

赋值运算符 `=`：把右边值赋给左边变量。左边必须是变量，不能是常量或表达式。

**连续赋值从右向左：**

```c
int x, y;
x = y = 10;   // y=10 → x=y=10
```

注意：声明时不允许连续初始化（`int x = y = 10;` 错误）。

**复合赋值运算符：**

```c
a += 2;   // a = a + 2
a -= 2;   // a = a - 2
a *= 2;   // a = a * 2
a /= 2;   // a = a / 2
a %= 2;   // a = a % 2
```

复杂表达式解题方法：**从右向左，将复合赋值运算符完整展开**。

**例题：** `int m = 5, y = 2;` 计算 `y += y -= m *= y` 后 `y` 的值？
步骤：
1. `m *= y` → m = 5×2 = 10，变为 `y += y -= 10`
2. `y -= 10` → y = 2−10 = −8，变为 `y += −8`
3. `y += −8` → y = −8+(−8) = −16

答案：y = −16

### 7.4 关系运算符

| 运算符 | 含义 |
|--------|------|
| `>` `<` `>=` `<=` | 大于/小于/大于等于/小于等于 |
| `==` `!=` | 等于/不等于 |

**致命混淆：** `=` 是赋值，`==` 是判等。`if (a = 5)` 永远为真。

**关系表达式的值：** 成立为 `1`，不成立为 `0`，类型为 `int`。

```c
9 > 8     // 结果为 1
7 < 6     // 结果为 0
```

**连续比较陷阱：** `x < y < z` 在 C 中计算为 `(x < y) < z`。

```c
int x = 1, y = 0, z = 2;
x < y < z   // (1<0)=0, (0<2)=1，最终为 1
```
正确表示区间：`x < y && y < z`

### 7.5 逻辑运算符与短路原则

三种逻辑运算符：`&&`（与）、`||`（或）、`!`（非）

- `&&`：全真才真，一假全假
- `||`：一真即真，全假才假
- `!`：真变假，假变真

**非零即为真：** 任何非零数值被视为真，只有 0 和 0.0 为假。`!6` 结果为 0。

**短路原则：**
- `A && B`：A 为假时不再计算 B
- `A || B`：A 为真时不再计算 B

```c
int a = 1, b = 5, c = 3, d = 2, m = 2, n = 2;
(m = a > b) && (n = c > d);   // a>b 为假，m=0，&& 短路，n 保持 2
```

**例题1：** 表达式 `(5>3)+(2<4)` 的值是？
答案：2。`5>3` 得 1，`2<4` 得 1，1+1=2。

**例题2：** 表达式 `!0 + !5` 的值是？
答案：1。`!0 = 1`，`!5 = 0`，1+0=1。

**例题3：** `int x = 0, y = 5; if ((x == 10) && (y = 20));` 执行后 y 的值是？
答案：5。`x==10` 为假，`&&` 短路，`y=20` 不执行。

### 7.6 三目运算符

```c
条件 ? 表达式1 : 表达式2
```

条件为真取表达式1，为假取表达式2。

```c
int max = (a > b) ? a : b;
```

条件运算符右结合，可嵌套：`1 ? (0 ? 3 : 2) : 4` 结果为 2。

### 7.7 逗号表达式与强制类型转换

**逗号表达式：** `(表达式1, 表达式2, ..., 表达式n)`，从左到右依次计算，整个表达式的值等于最右边表达式的值。

```c
z = (2, 3, 4);      // z = 4
z = 2, 3, 4;        // z = 2（赋值优先级高于逗号）
```

**强制类型转换：** `(类型)表达式`

```c
(int)3.14      // 结果为 3（截断，不四舍五入）
```

错误写法：`int(3.14)`、`int(f)`（应为 `(int)f`）。

注意 `(float)(10/4)` 与 `(float)10/4` 的区别：
- `(float)(10/4)` → 先 10/4=2，再转 float 得 2.0
- `(float)10/4` → 先 10 转 10.0，再 10.0/4=2.5

**例题：** 执行 `x = (a=3, b=a--);` 后，x、a、b 的值依次是？
步骤：`a=3` → `b=a--`（b=3，a 变为 2）。逗号表达式值为 3，赋给 x。
答案：x=3, a=2, b=3

### 7.8 运算符优先级汇总（从高到低）

| 优先级 | 类别 | 运算符 | 结合性 |
|--------|------|--------|--------|
| 1（最高） | 一元 | `++` `--` `!` `(类型)` | 右→左 |
| 2 | 算术乘除 | `*` `/` `%` | 左→右 |
| 3 | 算术加减 | `+` `-` | 左→右 |
| 4 | 关系比较 | `>` `>=` `<` `<=` | 左→右 |
| 5 | 关系判等 | `==` `!=` | 左→右 |
| 6 | 逻辑与 | `&&` | 左→右 |
| 7 | 逻辑或 | `\|\|` | 左→右 |
| 8 | 条件 | `?:` | 右→左 |
| 9 | 赋值 | `=` `+=` `-=` 等 | 右→左 |
| 10 | 逗号 | `,` | 左→右 |

**总规律：** 一元 > 算术 > 关系 > 逻辑 > 条件 > 赋值 > 逗号

### 7.9 位运算符（嵌入式高频）

`&`、`|`、`^`、`~`、`<<`、`>>`

#### 位运算的典型用途

- 寄存器置位 / 清位
- 掩码提取
- 位段组合
- 标志位管理

示例：

```c
reg |= (1U << 3);   // 置位第 3 位
reg &= ~(1U << 3);  // 清零第 3 位
if (reg & (1U << 3)) { }
```

### 7.10 访问类运算符

- `()`：函数调用
- `[]`：数组访问
- `*`：解引用
- `&`：取地址
- `.`：访问结构体成员
- `->`：访问结构体指针成员

---

## 7.11 格式化输入输出：printf 与 scanf

### 7.11.1 printf 基本用法

使用前需包含 `#include <stdio.h>`。

两种形式：固定输出 `printf("Hello World");` 和带格式控制符 `printf("这个整型数值是%d", 123);`。

一般格式：`printf("格式字符串", 参数1, 参数2, ...);`

格式字符串包含普通字符（原样输出）和格式控制符（占位符，被参数依次替换）。**格式控制符和后面的参数必须数量对应、类型匹配、顺序一致。**

```c
printf("A=%d, B=%d", 12, 34);  // 输出：A=12, B=34
```

### 7.11.2 常用格式控制符

| 数据类型 | 控制符 | 说明 |
|----------|--------|------|
| `int` | `%d` | 十进制整数 |
| `long` | `%ld` | 长整型 |
| `unsigned int` | `%u` | 无符号十进制 |
| `float` / `double` | `%f` | 浮点数，默认 6 位小数 |
| `char` | `%c` | 单个字符 |
| 字符串 | `%s` | 字符串 |
| 十六进制（小写） | `%x` | 如 15 → f |
| 十六进制（大写） | `%X` | 如 15 → F |
| 八进制 | `%o` | 如 8 → 10 |
| 百分号 | `%%` | 输出一个 `%` |

注意：`printf` 中 `float` 传参自动提升为 `double`，两者都用 `%f`。`scanf` 中 `float` 用 `%f`，`double` 必须用 `%lf`。

### 7.11.3 宽度与精度控制

```c
printf("A=%5d", 10);       // 输出：A=   10（宽度至少5，右对齐）
printf("B=%.2f", 3.1415);  // 输出：B=3.14（保留两位小数）
```

`%5d`：输出宽度至少 5 字符，不足左边补空格，默认右对齐。`%.2f`：保留小数点后 2 位。`%5.2f` 组合使用。

### 7.11.4 scanf 基本用法

从键盘读取数据并保存到变量：`scanf("格式字符串", 地址列表);`

```c
scanf("%d", &age);
```

**核心规则：普通变量必须加 `&`（取地址符）。** 缺少 `&` 会导致未定义行为。

**必须检查返回值：** `scanf` 返回成功匹配并赋值的项数，0 表示格式不匹配，EOF 表示输入结束。不检查返回值会导致使用未初始化数据：

```c
int x;
if (scanf("%d", &x) != 1) {
    // 错误处理或清空缓冲区重试
}
```

```c
scanf("%d", age);   // 错误——缺少 &
```

**例外：** 字符串数组名本身是地址，不加 `&`：`char str[20]; scanf("%s", str);`

**`fgets` 安全输入：** 能读取含空格的整行且不会缓冲区溢出。

```c
char str[100];
fgets(str, sizeof(str), stdin);
```

`fgets` 会读入末尾换行符 `'\n'`，可手动去除：

```c
for (i = 0; str[i] != '\0'; i++)
    if (str[i] == '\n') { str[i] = '\0'; break; }
```

`gets()` 不安全，禁止使用。

**读取含空格的字符串：** `%s` 遇空格停止，可用 `%[^\n]`：

```c
scanf("%99[^\n]", str);   // 最多读 99 个字符，遇换行停止
```

### 7.11.5 scanf 格式匹配陷阱

`scanf` 格式字符串中的普通字符必须与输入一致：

```c
scanf("%d,%d", &a, &b);    // 输入必须带逗号：10,20
```

**`%c` 不跳过空白的陷阱：**

```c
int a; char ch;
scanf("%d", &a);           // 输入 65 后按回车
scanf("%c", &ch);          // 读取到的是回车 '\n'，不是 'A'
```

解决：`scanf(" %c", &ch);` —— 在 `%c` 前加空格跳过空白。或用 `getchar()` 吃掉回车。

### 7.11.6 指定输入宽度

```c
int x, y, z;
scanf("%2d%4d%d", &x, &y, &z);
// 输入 1234567 → x=12, y=3456, z=7
```

`%2d` 表示最多读取 2 位数字，多出的留在缓冲区。

### 7.11.7 典型例题

**例题1：** `int x = 017;`，`printf("%d\n", x)` 和 `printf("%o\n", x)` 分别输出？
分析：`017` 是八进制 = 15。`%d` 输出 15，`%o` 输出 17。
答案：第一行 15，第二行 17。

**例题2：** 读入 `10,20` 的正确语句是？
A. `scanf("%d", &a, &b)`  B. `scanf("%d,%d", &a, &b)`  C. `scanf("%d,%d", a, b)`  D. `scanf("%d,%d", &a)`
答案：B。

**例题3：** `printf("%c", 65);` 是否正确？
答案：正确。`%c` 输出字符，65 对应 `'A'`。

---

## 8. 控制流

三种基本结构：**顺序结构**（从上到下逐条执行）、**分支结构**（根据条件选择路径）、**循环结构**（重复执行某段代码）。

### 8.1 条件语句

```c
if (x > 0) {
    puts("positive");
} else if (x == 0) {
    puts("zero");
} else {
    puts("negative");
}
```

**花括号规则：** `if` 或 `else` 后面只有一条语句时可省略花括号；多条语句时必须用。

**悬空 else 问题：** `else` 总是与它前面最近的、尚未配对的 `if` 配对（与缩进无关）。

```c
// else 与 if (c < d) 配对，不是与 if (a < b)
if (a < b)
    if (c < d)
        x = 1;
else
    x = 2;

// 花括号可强制配对
if (a < b) {
    if (c < d)
        x = 1;
} else {
    x = 2;
}
```

**常见语法错误：**
- `if (条件) ;` 后面直接加分号，相当于 if 控制了一条空语句
- `if` 后忘记花括号导致逻辑混乱

### 8.2 `switch`

```c
switch (表达式) {
    case 常量1:
        语句;
        break;
    case 常量2:
        语句;
        break;
    default:
        默认语句;
        break;
}
```

重要规则：
- `switch` 表达式必须是整型、字符型或枚举类型
- `case` 后面必须是常量表达式，不能是变量或区间
- `break` 跳出当前 `switch`，若无 `break` 会发生 **case 穿透**
- `default` 处理所有未匹配情况，位置可任意

**case 穿透：** 某 `case` 后无 `break`，程序会继续执行后续 case 直到遇到 `break` 或 switch 结束。

```c
switch (x) {
    case 1:
        printf("A\n");   // 无 break
    case 2:
        printf("B\n");   // 有 break
        break;
}
// x=1 时输出 A 然后 B（穿透）
```

**利用穿透实现多值共用：**

```c
switch (score / 10) {
    case 10:
    case 9:  grade = 'A'; break;
    case 8:  grade = 'B'; break;
    case 7:  grade = 'C'; break;
    case 6:  grade = 'D'; break;
    default: grade = 'F'; break;
}
```

**内层 switch 的 break 只跳出内层，不跳出外层。**

**嵌套 switch 例题：**

```c
int x = 1, y = 0, a = 0, b = 0;
switch (x) {
    case 1:
        switch (y) {
            case 0: a++; break;
            case 1: b++; break;
        }
    case 2:
        a++; b++; break;
}
// x=1 进 case 1, y=0 进内层 case 0 → a=1。内层 break 结束内层。外层 case 1 无 break，贯穿到 case 2，a++ 和 b++。
// 结果：a=2, b=1
```

### 8.3 循环语句

#### while

```c
while (条件) {
    循环体;
}
```

**先判断，后执行。** 条件一开始为假，循环体一次都不执行。

**`while (k = 0)` 陷阱：** 这是赋值不是判等，值为 0（假），循环体不执行。

```c
int k = 10;
while (k = 0)   // 赋值，结果为 0，循环体不执行
    k--;
// 最终 k = 0
```

#### do-while

```c
do {
    循环体;
} while (条件);
```

**先执行一次，再判断。** 循环体至少执行一次。末尾 `while` 后面必须有分号 `;`。

典型场景：输入验证、菜单选择。

```c
do {
    printf("请输入一个正数：");
    scanf("%d", &x);
} while (x <= 0);
```

**密码锁示例：**

```c
#define PASSWORD 2026
int input, correct = 0, wrong = 0;
do {
    scanf("%d", &input);
    if (input == PASSWORD) { correct++; wrong = 0; }
    else                   { wrong++;  correct = 0; }
} while (correct < 2 && wrong < 5);

if (correct >= 2) printf("Unlocked!\n");
else              printf("Blocked.\n");
```

#### for

```c
for (初始化; 循环条件; 循环更新) {
    循环体;
}
```

执行顺序：**初始化（一次）→ 条件判断 → 循环体 → 更新 → 条件判断 → ……**

```c
for (i = 1; i <= 5; i++) {
    printf("%d", i);          // 输出 1 2 3 4 5
}
```

注意：
- for 括号中用分号分隔三部分，不能用逗号
- 各部分可省略，但分号不能省：`for (;;)` 是死循环
- for 也是先判断后执行

#### 循环嵌套

外层循环执行 1 次，内层循环执行完整一轮。总次数 = 各层次数乘积。

```c
for (i = 0; i < 3; i++) {
    for (j = 0; j < 4; j++) {
        printf("*");          // 共 3×4 = 12 个 *
    }
}
```

### 8.4 `break` / `continue`

| 语句 | 作用范围 | 效果 |
|------|---------|------|
| `break` | 循环、switch | 立即退出整个循环或 switch |
| `continue` | 循环 | 跳过本轮剩余语句，进入下一次循环 |

```c
for (i = 0; i < 5; i++) {
    if (i == 3) break;       // i=3 退出整个循环
    printf("%d ", i);         // 输出 0 1 2
}

for (i = 0; i < 5; i++) {
    if (i == 2) continue;    // i=2 跳过后面语句
    printf("%d ", i);         // 输出 0 1 3 4
}
```

注意：`break` 只退出最近一层循环。在 `for` 中执行 `continue` 后仍会执行更新表达式。

**例题（break + continue 综合）：**

```c
for (i = 1; i <= 10; i++) {
    if (i % 2 == 0) continue;
    if (i == 9) break;
    printf("%d", i);
}
// 跳出偶数，i=9 时 break。输出：1 3 5 7
```

### 8.5 循环综合例题

**例题1：** `while` 连续比较陷阱：

```c
int a = 1, b = 2, c = 2, t;
while (a < b < c) {
    t = a; a = b; b = t; c--;
}
printf("%d%d%d", a, b, c);
```

分析：`a < b < c` 等价于 `(a < b) < c`。第一次：1<2 为真(1)，1<2 为真，交换后 a=2,b=1,c=1。第二次：2<1 为假(0)，0<1 为真，交换后 a=1,b=2,c=0。第三次：1<2 为真(1)，1<0 为假退出。
答案：120

**例题2：** do-while 后置自减：

```c
int a = 1, b = 10;
do {
    b = b - a;
    a++;
} while (b-- < 0);
printf("a=%d, b=%d", a, b);
```

分析：先执行 b=10-1=9, a=2。判断 `b-- < 0`：b=9 < 0 为假，判断后 b 自减为 8。
答案：a=2, b=8

### 8.6 `goto`

很多教材把 `goto` 写得很可怕，但工程里它在**失败回滚路径**特别有用。

```c
p1 = malloc(...);
if (!p1) goto out;

p2 = malloc(...);
if (!p2) goto free_p1;

p3 = malloc(...);
if (!p3) goto free_p2;

// 使用 p1, p2, p3 正常逻辑

free(p3);
free_p2:
    free(p2);
free_p1:
    free(p1);
out:
    return result;
```

> 在资源申请、错误回退、驱动初始化失败清理路径中，`goto` 反而可能让代码更清楚。结构化程序设计通常不推荐 goto，合理使用场景：多层嵌套循环的统一错误处理、资源清理的集中处理。

```c
for (int i = 0; i < 10; i++) {
    for (int j = 0; j < 10; j++) {
        if (error_condition) goto cleanup;
    }
}
cleanup:
    // 资源清理代码
```

---

## 9. 函数

### 9.1 函数的三大属性

1. 函数名
2. 输入参数
3. 返回值

```c
int add(int a, int b) {
    return a + b;
}
```

### 9.2 函数名的本质

函数名本质上是一个**地址标签**，这也是函数指针成立的根本原因。

### 9.3 参数传递的本质

参数传递本质上是**拷贝**。

- 值传递：传副本
- 地址传递：通过地址操作原对象

### 9.4 值传递

```c
void inc(int x) {
    x++;
}
```

不会改到外部实参。

### 9.5 地址传递

```c
void inc(int *x) {
    (*x)++;
}
```

可修改外部变量。

### 9.6 返回多个值

```c
void divide(int a, int b, int *q, int *r) {
    *q = a / b;
    *r = a % b;
}
```

### 9.7 可变参数函数

```c
#include <stdarg.h>

int sum(int count, ...) {
    va_list args;
    va_start(args, count);

    int total = 0;
    for (int i = 0; i < count; i++) {
        total += va_arg(args, int);
    }

    va_end(args);
    return total;
}
```

### 9.8 函数指针

```c
int add(int a, int b) { return a + b; }
int (*fp)(int, int) = add;
```

### 9.9 回调函数

```c
void process(int a, int b, int (*op)(int, int)) {
    printf("%d\n", op(a, b));
}
```

### 9.10 `void *` + 回调：做通用接口

```c
typedef void (*swap_func_t)(void *, void *);

void swap_generic(swap_func_t func, void *a, void *b) {
    func(a, b);
}
```

> `void *` 负责抽象“数据”，函数指针负责抽象“行为”。

### 9.11 `weak` 弱连接函数

在驱动设计中很常见：

```c
__attribute__((weak)) void board_init(void) {
    // 默认实现（GNU/Clang 扩展，非 ISO C）
}
```

如果用户工程里再定义一个同名强符号函数，默认实现会被覆盖。

#### 典型用途

- 默认钩子函数
- 板级初始化
- 中断回调默认实现
- 框架保底行为

### 9.12 函数声明（函数原型）

如果函数定义在调用之后，调用前必须写函数声明：

```c
int add(int x, int y);     // 函数声明

int main() {
    int a = add(2, 3);     // 调用
    return 0;
}

int add(int x, int y) {    // 函数定义
    return x + y;
}
```

声明中参数名可省略：`int add(int, int);`。函数声明也可写在 `main` 内部，但规范做法是写在文件顶部。

**函数不能嵌套定义，但可嵌套调用。** 有返回值的函数可以不接收返回值：`fn(2, 3);` 语法正确，只是返回值被忽略。

**void 函数：** 返回类型 `void` 表示不返回值。可写空 `return;` 提前退出。

**返回类型自动截断：** `return` 表达式类型与声明不一致时自动转换。如 `int f() { return 3.14; }` 实际返回 3。

### 9.13 递归

递归函数包含两个要素：
- **递推公式：** 问题拆解为更小的同类问题
- **终止条件：** 不再递归的条件（base case）

```c
// 阶乘
int fact(int n) {
    if (n <= 1) return 1;
    return n * fact(n - 1);
}

// 1 到 n 的和
int sum(int n) {
    if (n == 1) return 1;
    return n + sum(n - 1);
}
```

递归调用在栈上分配空间，层数过深会导致栈溢出。递归必须要有终止条件。

### 9.14 常用算法函数

**最大公约数（辗转相除法）：**

```c
int gcd(int a, int b) {
    int r;
    while (b != 0) {
        r = a % b;
        a = b;
        b = r;
    }
    return a;
}
```

最小公倍数：`a * b / gcd(a, b)`

**素数判断：**

```c
int isPrime(int n) {
    if (n <= 1) return 0;
    for (int i = 2; i * i <= n; i++)
        if (n % i == 0) return 0;
    return 1;
}
```

**水仙花数（三位数，各位立方和等于本身）：**

```c
int isArmstrong(int n) {
    int sum = 0, temp = n, digit;
    while (temp != 0) {
        digit = temp % 10;
        sum += digit * digit * digit;
        temp /= 10;
    }
    return sum == n;
}
// 结果：153, 370, 371, 407
```

**两位数合并：** 将 a=45, b=12 合并为 4251（千位 a 十位，百位 b 个位，十位 a 个位，个位 b 十位）

```c
int merge(int a, int b) {
    return (a/10)*1000 + (b%10)*100 + (a%10)*10 + (b/10);
}
```

### 9.15 复合函数调用

```c
int fn(int a, int b) {
    return a > b ? a : b;    // 返回较大值
}
int main() {
    int x = 3, y = 8, z = 6;
    int result = fn(fn(x, y), 2 * z);    // fn(8, 12) = 12
}
```

核心：**先算最内层函数，再把返回值代入外层。**

### 9.16 函数典型例题

**例题1：** 以下代码输出什么？

```c
void func(int x) { x = 10; printf("%d,", x); }
int main() {
    int x = 20;
    func(x);
    printf("%d", x);
}
```
答案：10,20。值传递，形参修改不影响实参。

**例题2：** `int f(int n) { return n + f(n - 1); }` 存在什么问题？
答案：缺少递归终止条件，导致栈溢出。

**例题3：** 以下代码输出什么？

```c
void set(int *p, int v) { *p = v; }
int main() {
    int x = 5;
    set(&x, 100);
    printf("%d", x);
}
```
答案：100。通过指针参数间接修改 x。

---

## 10. 数组

### 10.1 一维数组

```c
int arr[5] = {1, 2, 3, 4, 5};
```

### 10.2 数组长度

```c
size_t len = sizeof(arr) / sizeof(arr[0]);
```

### 10.3 数组名的本质

数组名不是普通变量，更像一个**常量标签**，代表这块连续内存。

```c
char arr[20];
// arr = "hello";   // 错误，数组名不能做左值
```

### 10.4 `arr` 与 `&arr`

- `arr`：首元素地址
- `&arr`：整个数组地址

它们数值可能相同，但类型和指针运算语义不同。

### 10.5 数组作为函数参数

```c
void print_arr(int arr[], int len) {
    for (int i = 0; i < len; i++) {
        printf("%d ", arr[i]);
    }
}
```

### 10.6 多维数组

```c
int mat[2][3] = {
    {1, 2, 3},
    {4, 5, 6}
};
```

### 10.7 二维数组访问

```c
mat[i][j]
*(*(mat + i) + j)
```

### 10.8 一维数组的初始化和遍历

```c
int number[5];                // 定义整型数组，5 个元素
int a[5] = {1, 2, 3, 4, 5};  // 完整初始化
int b[5] = {1, 2};            // 部分初始化，b[2]~b[4] 自动补 0，即 {1,2,0,0,0}
int c[] = {1, 2, 3};          // 省略长度，自动推断为 3
```

**下标从 0 开始：** `number[0]` 是第一个元素。遍历时为 `for (i = 0; i < n; i++)`，不是 `i <= n`。

### 10.9 一维数组常见操作

**求最值：**

```c
int a[] = {3, 1, 4, 1, 5, 9};
int max = a[0];
for (i = 1; i < 6; i++)
    if (a[i] > max) max = a[i];
// max = 9
```

**选择排序：**

```c
for (i = 0; i < n - 1; i++) {
    minIndex = i;
    for (j = i + 1; j < n; j++)
        if (a[j] < a[minIndex]) minIndex = j;
    if (minIndex != i) {
        temp = a[i]; a[i] = a[minIndex]; a[minIndex] = temp;
    }
}
```

**筛选法求素数（埃氏筛）：**

```c
int isPrime[101];
for (i = 0; i <= 100; i++) isPrime[i] = 1;
isPrime[0] = isPrime[1] = 0;
for (i = 2; i * i <= 100; i++)
    if (isPrime[i])
        for (j = i * i; j <= 100; j += i)
            isPrime[j] = 0;
```

**数字反转：**

```c
int n = 12345, rev = 0;
while (n > 0) {
    rev = rev * 10 + n % 10;
    n /= 10;
}
// rev = 54321
```

### 10.10 二维数组初始化

```c
int a[2][3] = {{1, 2, 3}, {4, 5, 6}};   // 嵌套花括号
int b[2][3] = {1, 2, 3, 4, 5, 6};        // 按行优先顺序
int c[2][3] = {{1, 2}, {4}};              // 部分初始化 → {{1,2,0}, {4,0,0}}
```

**省略第一维：** 可省略行数，不能省略列数。

```c
int d[][3] = {{1,2,3}, {4,5,6}};   // 正确
int e[2][] = {{1,2,3}, {4,5,6}};   // 错误——列数不能省略
```

**行优先存储：** 先存第 0 行所有列，再存第 1 行所有列。

### 10.11 二维数组常见操作

**杨辉三角：**

```c
int a[10][10];
for (i = 0; i < 10; i++) a[i][0] = a[i][i] = 1;
for (i = 2; i < 10; i++)
    for (j = 1; j < i; j++)
        a[i][j] = a[i-1][j-1] + a[i-1][j];
```

**矩阵转置：**

```c
for (i = 0; i < 3; i++)
    for (j = 0; j < 3; j++)
        b[j][i] = a[i][j];
```

### 10.12 动态数组

```c
int *arr = malloc(n * sizeof(int));
if (arr == NULL) {
    return;
}
free(arr);
arr = NULL;
```

---

## 11. 指针

### 11.1 指针基础

指针变量里存放的是**地址**。

```c
int a = 10;
int *p = &a;
printf("%d\n", *p);
```

### 11.2 指针与指针变量的区别

- **指针**：通常指地址值
- **指针变量**：存这个地址的变量

### 11.3 指针大小

- 32 位系统：通常 4 字节
- 64 位系统：通常 8 字节

### 11.4 访问指针前必须先问两件事

1. 这块内存有没有权限访问？
2. 应该按什么类型规则解释它？

### 11.5 指针运算

```c
int arr[5] = {1, 2, 3, 4, 5};
int *p = arr;
p++;   // 前进一个 int 单位，而不是单纯加 1 字节
```

### 11.6 指针数组与数组指针

```c
int *pa[10];   // 指针数组：10 个元素，每个元素是 int *
int (*ap)[10]; // 数组指针：指向含 10 个 int 的数组
```

### 11.7 `void *` 指针

```c
void *p;
int a = 10;
p = &a;
printf("%d\n", *(int *)p);
```

### 11.8 `NULL` 指针

```c
int *p = NULL;
if (p != NULL) {
    printf("%d\n", *p);
}
```

### 11.9 多级指针

```c
int **pp;
```

理解：

- `pp` 是一个指针变量
- `*pp` 仍然是一个指针
- `**pp` 才是最终对象

### 11.10 指针与数组的等价关系

```c
int a[5] = {1, 2, 3, 4, 5};
int *p = a;              // 等价于 p = &a[0]

printf("%d", *p);        // a[0] → 1
printf("%d", *(p + 2));  // a[2] → 3
printf("%d", *(a + 2));  // a[2] → 3
```

`a[i]` 完全等价于 `*(a + i)`。`p++` 使指针移动到下一个元素（跳过 `sizeof(类型)` 字节）。

**`sizeof` 的区别：**

```c
int a[5] = {0};
int *p = a;
sizeof(a);     // 20（整个数组大小，5×4=20）
sizeof(p);     // 4 或 8（指针变量本身的大小）
```

**数组名 vs 指针：** 数组名是常量指针，不能自增自减；指针变量可以。

### 11.11 指针作为函数参数（模拟引用传递）

```c
void swap(int *px, int *py) {
    int temp = *px;
    *px = *py;
    *py = temp;
}

int main() {
    int a = 3, b = 5;
    swap(&a, &b);     // a=5, b=3
}
```

函数原型区分：`void swap(int x, int y);` 是传值；`void swap(int *x, int *y);` 是传指针，可修改实参。

### 11.12 指针实现矩阵转置

```c
int a[3][4], b[4][3];
int *p1 = &a[0][0];
int *p2 = &b[0][0];

for (i = 0; i < 3; i++)
    for (j = 0; j < 4; j++)
        *(p2 + j * 3 + i) = *(p1 + i * 4 + j);
```

二维数组在内存中按行连续存储，`a[i][j]` 偏移为 `i * 列数 + j`。

### 11.13 指针常见错误

1. 未初始化指针（野指针）
2. 空指针解引用
3. 越界访问
4. `free` 后继续使用
5. 返回局部变量地址
6. 数组参数 `sizeof` 失效：函数内 `sizeof(arr)/sizeof(arr[0])` 算不出长度

### 11.14 典型例题

**例题1：** 定义指向整型变量的指针，正确语法是？
A. `int p*;`  B. `int *p;`  C. `pointer int p;`  D. `int &p;`
答案：B

**例题2：** 对于数组 `int a[5]`，`a[i]` 等价于？
A. `*a + i`  B. `*(a + i)`  C. `a + i`  D. `&a[i]`
答案：B

**例题3：** `int *p = NULL;` 中 NULL 的作用是？
A. 指向地址 0  B. 初始化为空，不指向有效地址  C. 申请动态内存  D. 释放指针
答案：B

**例题4：** `sizeof(a)` 和 `sizeof(p)` 在 `int a[5]; int *p = a;` 中分别代表？
答案：`sizeof(a)=20`，`sizeof(p)=4`（32 位系统）。a 是整个数组，p 是指针变量本身。

---

## 12. 字符串

### 12.1 字符串本质

C 字符串本质上是以 `\0` 结尾的字符数组。

```c
char s[] = "hello";
```

实际内存里包含：`'h' 'e' 'l' 'l' 'o' '\0'`

### 12.2 字符串常量与字符数组

```c
char *p = "hello";     // 指向只读数据段
char arr[] = "hello";  // 拷贝到本地数组
```

`p[0] = 'H';` 可能触发段错误；而 `arr[0] = 'H';` 合法。

### 12.3 常用字符串函数

```c
strlen(), strcpy(), strncpy(), strcat(), strncat(), strcmp(), strchr(), strstr()
```

### 12.4 字符串处理示例

```c
#include <stdio.h>
#include <string.h>

int main(void) {
    char s[32] = "hello";
    strcat(s, " world");
    printf("len = %zu, str = %s\n", strlen(s), s);
    return 0;
}
```

### 12.5 字符类型统计

```c
char str[80];
fgets(str, sizeof(str), stdin);
int upper = 0, lower = 0, digit = 0, space = 0, other = 0;
for (i = 0; str[i] != '\0'; i++) {
    if      (str[i] >= 'A' && str[i] <= 'Z') upper++;
    else if (str[i] >= 'a' && str[i] <= 'z') lower++;
    else if (str[i] >= '0' && str[i] <= '9') digit++;
    else if (str[i] == ' ') space++;
    else if (str[i] != '\n') other++;
}
```

### 12.6 字符串操作（不用库函数）

**字符串连接：**

```c
char s1[80], s2[40];
int i, j;
for (i = 0; s1[i] != '\0'; i++);        // 找到 s1 末尾
for (j = 0; s2[j] != '\0'; j++) {
    s1[i] = s2[j]; i++;
}
s1[i] = '\0';
```

**大小写转换：**

```c
if (str[i] >= 'A' && str[i] <= 'Z')
    str[i] = str[i] + 32;     // 大写转小写（+32）
// 小写转大写：str[i] - 32
```

**删除字符串中指定字符：**

```c
int i, j = 0;
for (i = 0; str[i] != '\0'; i++)
    if (str[i] != ch)
        str[j++] = str[i];
str[j] = '\0';
```

**单词统计：**

```c
int words = 0, inWord = 0;
for (i = 0; str[i] != '\0'; i++) {
    if (str[i] != ' ' && str[i] != '\n' && str[i] != '\t') {
        if (inWord == 0) { words++; inWord = 1; }
    } else inWord = 0;
}
```

### 12.7 安全性提醒

- 使用 `strcpy`、`strcat` 时必须确认目标缓冲区足够大。
- 更推荐 `snprintf`、`strncpy`、手动限制长度。

---

## 13. 结构体、联合体、枚举与 `typedef`

### 13.1 结构体 `struct`

```c
struct Student {
    char name[20];
    int age;
    float score;
};
```

### 13.2 结构体使用

```c
struct Student s = {"Tom", 20, 95.5f};
printf("%s %d %.1f\n", s.name, s.age, s.score);
```

### 13.3 结构体指针

```c
struct Student *ps = &s;
printf("%s\n", ps->name);
```

### 13.4 结构体内存对齐

结构体成员往往受对齐规则影响：

```c
struct A {
    char c;
    int i;
};
```

其大小通常不等于 `1 + 4 = 5`，可能会因为对齐而更大。

### 13.5 `packed` 属性（GNU/Clang 扩展，非 ISO C）

```c
#include <stdint.h>

struct __attribute__((packed)) Packet {
    char type;
    int len;
};
```

> `__attribute__((packed))` 是 GCC/Clang 扩展。MSVC 使用 `#pragma pack(push, 1)` / `#pragma pack(pop)`。

#### 适用场景

- 通信协议
- 外设寄存器映射
- 二进制打包格式

### 13.6 联合体 `union`

```c
union Data {
    int i;
    float f;
    char str[20];
};
```

特点：多个成员共享同一块内存，大小通常等于最大成员大小。

### 13.7 枚举 `enum`

```c
enum State {
    IDLE,
    RUNNING,
    ERROR
};
```

### 13.8 `typedef`

```c
#include <stdint.h>   // 使用标准固定宽度类型，不要手写 typedef

typedef struct {
    int x;
    int y;
} Point;
```

#### 与 `#define` 的区别

- `typedef` 是类型别名
- `#define` 是文本替换

### 13.9 复杂类型声明与右左原则

```c
int a;           // 整型变量
int *a;          // 指向 int 的指针
int **a;         // 指向指针的指针
int a[10];       // 10 个 int 的数组
int *a[10];      // 指针数组
int (*a)[10];    // 数组指针
int (*a)(int);   // 函数指针
int (*a[10])(int); // 函数指针数组
```

> 读复杂声明时，从变量名出发，按“右左右左”读，通常更容易看懂。

---

## 14. 存储类、`const` 与 `volatile`

### 14.1 `auto`

默认自动变量，通常很少显式写出。

### 14.2 `register`

建议把变量放到寄存器中，但现代编译器通常会自行优化，实际意义已经不大。需注意 `register` 变量不能取地址（&），这是语义级限制而非优化提示。

### 14.3 `static`

#### 修饰局部变量

延长生命周期，函数多次调用时值会保留。

```c
void func(void) {
    static int cnt = 0;
    cnt++;
    printf("%d\n", cnt);
}
```

#### 修饰全局变量 / 函数

把可见范围限制在当前源文件。

### 14.4 `extern`

```c
extern int g_value;
```

表示该变量定义在别处，这里只是引用。

### 14.5 变量存储类别汇总

| 存储类别 | 生命周期 | 作用域 | 初始化 | 存储位置 |
|----------|---------|--------|--------|---------|
| `auto`（默认） | 函数调用期间 | 函数内部 | 每次调用 | 栈区 |
| `static` 局部 | 程序运行期间 | 函数内部 | 只一次 | 静态区 |
| `static` 全局 | 程序运行期间 | 文件内部 | 只一次 | 静态区 |
| `register` | 函数调用期间 | 函数内部 | 每次调用 | 寄存器 |
| `extern` | 程序运行期间 | 多文件 | 只一次 | 静态区 |

**全局变量：** 在所有函数之外定义，从定义处到文件末尾可见。方便数据共享，但易造成副作用。

### 14.6 `const`

`const` 更准确的理解不是“常量”，而是 **read only（只读）**。

```c
const int a = 10;
int const b = 20;
```

### 14.7 `const` 指针的三种常见写法

```c
const int *p;        // 不能通过 p 改 *p
int * const p2 = &x; // p2 本身不可改指向
const int * const p3 = &x; // 两者都不可改
```

### 14.8 `volatile`

告诉编译器：**这个变量的值可能在程序控制之外发生变化，不要把对它的读写随意优化掉。**

```c
volatile unsigned char buff;
while (buff == 0) {
    // 等待硬件更新
}
```

#### 典型场景

- 硬件寄存器
- 中断共享变量（单核单线程上下文中）
- 信号处理函数中访问的全局标志

> **注意：** `volatile` 不是线程同步机制。它不保证原子性、不保证内存序、不能替代互斥锁或原子操作。多线程共享标志位应使用 `_Atomic`（C11）或平台同步原语。

#### `const` 与 `volatile` 的区别

- `const`：强调“不要改”
- `volatile`：强调“它可能会变，别乱优化”

---

## 15. 内存模型与动态内存

C 语言最核心的能力之一，就是从**内存视角**看代码。

### 15.1 内存分区概览

常见分区：

- 代码段（text）
- 只读数据段（rodata）
- 全局数据段（data / bss）
- 堆（heap）
- 栈（stack）

### 15.2 代码段

- 存放程序指令
- 通常只读
- 整个程序运行期有效

### 15.3 只读数据段

典型对象：字符串常量。

```c
char *s = "hello";
```

`s` 在栈上，但 `"hello"` 通常在只读数据段。

### 15.4 全局数据段

- 全局变量
- `static` 局部变量

特点：程序整个运行期有效，可读可写。

### 15.5 栈

- 函数调用时分配
- 函数返回时自动回收
- 可读可写
- 生命周期短

#### 常见错误

返回局部数组地址：

```c
char *bad(void) {
    char buf[32] = "hello";
    return buf;   // 错误
}
```

### 15.6 堆

- 运行时通过 `malloc` / `calloc` / `realloc` 分配
- 通过 `free` 释放
- 生命周期由程序员控制

```c
// 假设在返回 int 的函数中，应 return -1 或对应错误码
int *p = malloc(sizeof(int));
if (p == NULL) {
    return -1;
}
*p = 100;
free(p);
p = NULL;
```

### 15.7 动态内存函数

```c
void *malloc(size_t size);
void *calloc(size_t n, size_t size);
void *realloc(void *ptr, size_t size);
void free(void *ptr);
```

### 15.8 两类常见内存问题

#### 栈溢出

- 递归没有出口
- 局部变量过大

#### 堆缓冲区溢出

- 分配空间太小
- 拷贝数据过长

例如：

```c
char *str = malloc(5);
strcpy(str, "hello world");  // 越界
```

### 15.9 内存管理最佳实践

- `malloc` 后马上判空
- `free` 后设为 `NULL`
- 申请与释放成对出现
- 长生命周期模块明确内存所有权

---

## 16. 文件操作与多文件工程

### 16.1 文件打开与关闭

```c
FILE *f = fopen("file.txt", "r");
if (f == NULL) {
    perror("fopen");
    return -1;
}
fclose(f);
```

### 16.2 文件打开模式

| 模式 | 说明 |
|------|------|
| `r` | 只读 |
| `w` | 只写，覆盖或创建 |
| `a` | 追加写 |
| `r+` | 读写 |
| `w+` | 读写，覆盖或创建 |
| `a+` | 读写，追加模式 |

### 16.3 常用文件读写函数

```c
fgetc(), fputc()
fgets(), fputs()
fprintf(), fscanf()
fread(), fwrite()
```

### 16.4 二进制文件示例

```c
struct Data {
    int id;
    char name[20];
};

struct Data d = {1, "test"};
FILE *f = fopen("data.bin", "wb");
fwrite(&d, sizeof(d), 1, f);
fclose(f);
```

### 16.5 多文件编程示例

**mymath.h**

```c
#ifndef MYMATH_H
#define MYMATH_H

int add(int a, int b);
int sub(int a, int b);

#endif
```

**mymath.c**

```c
#include "mymath.h"

int add(int a, int b) { return a + b; }
int sub(int a, int b) { return a - b; }
```

**main.c**

```c
#include <stdio.h>
#include "mymath.h"

int main(void) {
    printf("%d\n", add(3, 5));
    return 0;
}
```

编译：

```bash
gcc main.c mymath.c -o program
```

---

## 17. 错误处理与调试

### 17.1 返回值检查

```c
FILE *f = fopen("file.txt", "r");
if (f == NULL) {
    perror("fopen");
    return 1;
}
```

### 17.2 `errno`

```c
#include <errno.h>
#include <string.h>

if (f == NULL) {
    printf("错误: %s\n", strerror(errno));
}
```

### 17.3 `assert`

```c
#include <assert.h>

int divide(int a, int b) {
    assert(b != 0);
    return a / b;
}
```

### 17.4 程序测试

**测试只能证明程序有错，不能证明程序无错**（Dijkstra）。

**白盒测试：** 基于程序内部逻辑结构设计测试用例，覆盖所有执行路径、检查边界条件。

**黑盒测试：** 基于功能规格说明，不关心内部实现，从用户角度验证功能。

**调试技巧：**
- 在关键位置插入 `printf` 输出中间结果
- 使用断言 `assert` 检测逻辑错误

### 17.5 随机数生成

```c
#include <stdlib.h>
#include <time.h>

int main() {
    srand(time(NULL));           // 用当前时间做种子
    int magic = rand() % 100 + 1; // 1~100 的随机数
}
```

**生成 [min, max] 范围随机整数：** `rand() % (max - min + 1) + min`

例：[10, 99] → `rand() % 90 + 10`

注意：
- 不调用 `srand()` 默认种子为 1，每次产生相同序列
- **不要在循环中多次调用 `srand()`**——每秒内多次调用会得到相同种子
- 常见错误：`rand() % 100 + 10` 生成的是 [10, 109]，不是 [10, 99]

**猜数游戏综合示例：**

```c
int magic, guess, counter = 0;
srand(time(NULL));
magic = rand() % 100 + 1;

do {
    printf("第%d次猜测: ", counter + 1);
    scanf("%d", &guess);
    counter++;

    if (guess > magic)      printf("太大了！\n");
    else if (guess < magic) printf("太小了！\n");
    else {
        printf("恭喜你，猜对了！答案就是 %d\n", magic);
        break;
    }
} while (guess != magic && counter < 10);

if (counter == 10 && guess != magic)
    printf("正确答案是 %d\n", magic);
```

---

## 18. 嵌入式 / 工程化视角下的 C 设计

C 虽然是面向过程语言，但完全可以写出有层次的工程代码。

### 18.1 用结构体模拟“封装”

- 用结构体保存状态
- 用函数操作状态
- 对外只暴露接口

### 18.2 用结构体嵌套模拟“继承”

把公共基类部分放在前面，派生结构体在此基础上扩展。

### 18.3 用函数指针表模拟“多态”

```c
struct uart_ops {
    int (*init)(void *dev);
    int (*write)(void *dev, const char *buf, int len);
};
```

不同设备填不同实现，上层逻辑只依赖接口。

### 18.4 回调 + `void *` 做抽象接口

非常适合：

- 驱动框架
- 事件系统
- 通用容器
- 中间件适配层

### 18.5 `weak` 做默认实现 + 用户覆盖

很适合：

- 板级初始化
- 中断回调
- 默认配置函数

### 18.6 SOLID 在 C 中如何理解

虽然 SOLID 来自面向对象设计，但其思想对 C 也适用。

#### 单一职责原则

一个模块只做一类事。

#### 开闭原则

新增功能优先靠扩展，不要总改主干。

#### 里氏替换原则

抽象接口一旦定义，具体实现不应破坏原有语义。

#### 接口隔离原则

不要设计一个“大而全”的接口逼所有设备都实现。

#### 依赖倒置原则

高层逻辑依赖抽象接口，而不是具体硬件驱动。

> 对嵌入式来说，这些原则不是“为了优雅而优雅”，而是为了让代码更容易移植、扩展和维护。

### 18.7 结构化程序设计原则

三种基本控制结构：顺序、选择、循环。结构化设计强调"单入口单出口"，但在资源清理路径中合理使用 `goto`（如前文 8.6 节）能让代码更清晰。现代工程实践更注重**可维护性**和**退出策略一致性**，而非僵化地禁止多返回点。

**模块化设计核心原则：高内聚、低耦合**
- 高内聚：模块内部元素紧密相关，每个模块完成单一功能
- 低耦合：模块间依赖最小化，通过清晰接口通信

**设计方法：** 自顶向下、逐步求精；信息隐藏；单一职责原则。

**算法描述方法对比：**

| 方法 | 优点 | 缺点 |
|------|------|------|
| 自然语言 | 可读性好 | 精确性低、易产生歧义 |
| 传统流程图 | 直观 | 不适合结构化设计 |
| N-S 图（盒图） | 最适合结构化设计 | — |
| 伪代码 | 最容易转换为代码 | — |

**递归与迭代对比：**

| 方式 | 优点 | 缺点 |
|------|------|------|
| 递归 | 代码简洁，符合数学定义 | 可能栈溢出，时空效率低 |
| 迭代 | 效率高，不会栈溢出 | 有时逻辑不如递归直观 |

---

## 19. 高频面试题与易错点

### 19.1 用 `#define` 表示一年多少秒

```c
#define SECOND_OF_YEAR (365 * 24 * 3600UL)
```

考点：

- 宏展开
- 括号
- 溢出风险
- `UL` 含义

### 19.2 `MIN` 宏有什么问题

```c
#define MIN(A, B) A <= B ? A : B
```

问题：

- 宏体未整体加括号
- 参数未加括号
- 参数可能被重复求值

### 19.3 `const` 到底是不是常量

更准确地说，`const` 是“只读语义”，不是绝对不可改的神圣常量。

### 19.4 `signed` 与 `unsigned` 混合运算

混用时要特别小心隐式转换，不要靠数学直觉，必须看类型提升规则。

### 19.5 `arr` 和 `&arr` 的区别

- 值看起来可能一样
- 但类型和运算规则完全不同

### 19.6 为什么 `volatile` 常用于寄存器

因为寄存器值可能被硬件异步改写，编译器不能把它当普通变量随便优化。

### 19.7 为什么函数返回局部数组地址是错的

因为局部数组位于栈上，函数返回后生命周期结束。

### 19.8 `malloc` 之后为什么一定要判空

因为分配可能失败；嵌入式尤其资源紧张，不能假设永远成功。

---

## 20. 常见陷阱与最佳实践

### 20.1 常见错误

1. 数组越界
2. 空指针解引用
3. 野指针
4. 悬空指针
5. 内存泄漏
6. 字符串缓冲区不足
7. 混用有符号和无符号类型
8. 宏副作用
9. 把 `const` 当绝对常量
10. 忘记 `volatile` 导致优化错误

### 20.2 最佳实践

```c
int sum = 0;
int *ptr = NULL;
const int MAX_SIZE = 100;
```

- 所有变量尽量初始化
- 指针初始化为 `NULL`
- 动态内存申请后立即判空
- `free` 后置 `NULL`
- 用 `const` 表达只读语义
- 用 `volatile` 标记可能被外部改变的对象
- 宏参数和宏体都加括号
- 复杂资源清理路径允许使用 `goto`
- 接口设计优先小而清晰
- 驱动层和业务层解耦

### 20.3 一个推荐的函数风格

```c
int uart_send(struct uart_dev *dev, const uint8_t *buf, size_t len)
{
    if (dev == NULL || buf == NULL || len == 0) {
        return -1;
    }

    // 核心逻辑

    return 0;
}
```

特点：

- 入口先做参数校验
- 返回值表达成功 / 失败
- 命名清楚
- 职责明确

### 20.4 核心概念对比表

| 对比项 | 区别 | 典型场景 |
|--------|------|----------|
| **值传递 vs 地址传递** | 值传递复制数据，不改变实参；地址传递传指针，可修改实参 | 值传递用于读；地址传递用于写（如 swap） |
| **auto vs static 局部变量** | auto 每次调用重新初始化；static 只初始化一次，调用结束不销毁 | auto 做临时计算；static 做累计计数 |
| **break vs continue** | break 跳出整个循环；continue 跳过本轮剩余语句进入下一轮 | break 满足条件时提前结束；continue 跳过不合格元素 |
| **白盒测试 vs 黑盒测试** | 白盒看内部逻辑路径；黑盒看输入输出规格 | 白盒测分支覆盖；黑盒测边界值 |
| **递归 vs 迭代** | 递归函数自调用，代码简洁但栈开销大；迭代用循环，效率高 | 递归适合树/分治（汉诺塔、斐波那契）；迭代适合线性计算 |
| **全局变量 vs 局部变量** | 全局在整个文件/程序可见，生命周期全程；局部只在函数内部，调用时分配 | 全局用于多函数共享数据；局部用于封装隔离 |

### 20.5 高频易错点分类

**编译错误：**

| 易错点 | 典型错误 | 正确做法 |
|--------|----------|----------|
| do-while 漏分号 | `do { } while (条件)` 末尾漏 `;` | 加 `;` |
| switch 表达式类型 | 用 float 作 switch 表达式 | 必须是整型或 char |
| 函数缺少原型 | 定义在 main 之后，调用处报错 | 调用前加声明 |
| continue 误用于 switch | 在 switch 中写 `continue` | `continue` 只能用于循环 |

**运行时错误：**

| 易错点 | 典型错误 | 正确做法 |
|--------|----------|----------|
| 数组越界 | `int a[5]; a[5] = 10;` 编译通过 | 下标不超过 size-1 |
| 野指针解引用 | `int *p; *p = 10;` | 初始化为 NULL |
| 递归缺基 | 递归函数无终止条件 | 必须写 base case |
| 字符数组忘加 `\0` | 手动构造字符串后输出乱码 | 保证末尾有 `'\0'` |
| 死循环 | 循环条件永远为真 | 检查循环变量是否更新 |

**逻辑陷阱：**

| 易错点 | 典型错误 | 正确做法 |
|--------|----------|----------|
| 整数除法截断 | 期望 `10/4=2.5` | `10.0/4` 或 `(float)10/4` |
| `=` 与 `==` 混淆 | `if (x = 5)` | `if (x == 5)` |
| scanf 缺 `&` | `scanf("%d", d)` | `scanf("%d", &d)` |
| 后置自增误解 | 以为 `x++` 输出新值 | 先用旧值再自增 |
| 强制转换时机 | `(float)(10/4)` 得 2.0 | `(float)10/4` |
| 数组下标从 0 开始 | `for(i=1; i<=n; i++)` 访问 `a[i]` | `for(i=0; i<n; i++)` |
| 传值不能修改实参 | 写 `swap(a, b)` | 用指针 `swap(&a, &b)` |
| 数组参数 sizeof 失效 | 函数内 `sizeof(arr)/sizeof(arr[0])` | 额外传长度参数 |
| case 穿透 | 忘记写 `break` | 检查是否需要 `break` |
| 悬空 else | else 与错误的外层 if 配对 | 用 `{}` 明确层级 |
| 关系表达式连写 | `a < b < c` | `a < b && b < c` |
| 浮点数比较 | 直接用 `==` | `fabs(a - b) < 1e-6` |
| break 只退最内层 | 嵌套循环中期望 break 退出所有 | 用标志变量或 `goto` |
| 随机数范围 | `rand() % 100 + 10` 生成 [10, 109] | `rand() % 90 + 10` 才是 [10, 99] |
| `fgets` 换行符残留 | 直接用 `fgets` 读入包含 `\n` | 手动去除结尾换行符 |

### 20.6 速记口诀

```
等于判断用双等，赋值单等要分清
短路只在&&||，左边定了右边停
switch 穿透靠 break，case 后面常量跟
悬空 else 找最近，花括号来保平安
浮点比较用 fabs，直接等于行不通
关系结果只有 01，非零为真要记牢
else-if 找第一个，多个条件只取一

加加在前先加后用，加加在后先用后加
减减在前先减后用，减减在后先用后减

数组下标从零起，最大下标减一记
数组名是常指针，不能加减不能改
sizeof 测整数组，函数传参只传址

整除截断要当心，浮点除法转一边
强制转换需括号，类型写在表达前
逗号表达取最右，赋值逗号优先级

分号结尾不能忘，花括号包多语句
main 是入口不能缺，stdio 是 I/O 头
```

---

## 21. C 标准库常用函数速查

### 21.1 标准输入输出

```c
printf(), scanf(), puts(), putchar(), getchar(), fprintf(), fscanf()
```

### 21.2 字符串处理

```c
strlen(), strcpy(), strncpy(), strcat(), strncat(), strcmp(), strchr(), strstr(), snprintf()
```

### 21.3 内存管理

```c
malloc(), calloc(), realloc(), free(), memset(), memcpy(), memmove(), memcmp()
```

### 21.4 字符处理

```c
isalnum(), isalpha(), isdigit(), islower(), isupper(), tolower(), toupper()
```

### 21.5 数学函数

```c
#include <math.h>
fabs(), fabsf(), fabsl(), sqrt(), pow(), sin(), cos(), tan(), log(), exp()
```

> `abs()` / `labs()` / `llabs()` 属于 `<stdlib.h>`，不要与 `<math.h>` 混淆。

### 21.6 时间日期

```c
#include <time.h>
time(), clock(), strftime(), localtime()
```

---

## 22. 最后的总结：怎样才算真正学会了 C

如果只是会写：

- `if`
- `for`
- `printf`
- 函数

那还只是“会用语法”。

真正学会 C，至少要能同时从这三个角度看代码：

1. **编译器视角**：它会如何展开、翻译、链接？
2. **函数/架构视角**：它的接口、职责、扩展方式是否合理？
3. **内存/硬件视角**：它会访问哪块内存、生命周期怎样、有没有越界和权限风险？

当你开始习惯这样思考时，C 就不再只是“基础语言”，而会变成你做嵌入式、驱动、底层开发时最顺手的一把工具。

---

## 23. 未定义行为（UB）速查

> 未定义行为（Undefined Behavior, UB）指 C 标准未作任何规定的代码行为。出现 UB 时，程序可能崩溃、产生错误结果，也可能"刚好正确"——这是最危险的。以下为常见 UB 来源。

### 23.1 有符号整数溢出

```c
#include <limits.h>

int a = INT_MAX;
a++;             // UB：有符号溢出
unsigned b = 0;
b--;             // 正确：无符号整型回绕是定义行为
```

使用无符号类型做位运算和模运算可避免此问题。

### 23.2 越界访问

```c
int arr[5];
arr[5] = 10;     // UB：越界（下标最大为 4）
```

编译不报错，但运行时可能破坏相邻内存。

### 23.3 空指针 / 野指针解引用

```c
int *p = NULL;
*p = 10;         // UB：空指针解引用
```

### 23.4 严格别名（Strict Aliasing）

不同类型的指针不得指向同一块内存（`char *` 例外）：

```c
int x = 42;
float *f = (float *)&x;
*f = 3.14f;      // UB：通过 float * 修改 int 对象
```

### 23.5 移位越界

```c
int a = 1;
a <<= 32;        // UB：移位量 >= 类型位宽
a >>= -1;        // UB：负移位量
```

### 23.6 修改字符串常量

```c
char *p = "hello";
p[0] = 'H';      // UB：字符串常量通常位于只读段
```

### 23.7 同一表达式中多次修改同一变量（无序列点）

```c
int i = 0;
i = i++ + ++i;   // UB：i 在两个序列点之间被多次修改
```

### 23.8 有符号右移（实现定义行为）

标准不规定有符号右移是算术移位（补符号位）还是逻辑移位（补 0），依赖实现。

> **实践建议：** 位运算操作全部使用无符号类型（`uint32_t` 等），避免有符号右移歧义。

### 23.9 变参函数类型不匹配

```c
printf("%d", 3.14);   // UB：%d 期望 int，实际传 double
```

`printf`/`scanf` 格式字符串必须与参数类型完全匹配。

### 23.10 返回局部变量地址

```c
int *bad(void) {
    int x = 0;
    return &x;   // UB：返回后局部变量已销毁
}
```

---

## 24. VLA 与柔性数组成员

### 24.1 变长数组（VLA, C99 起可选）

VLA 的长度在运行时确定，而非编译期：

```c
void process(int n) {
    int arr[n];          // VLA：运行时确定大小
    for (int i = 0; i < n; i++)
        arr[i] = i;
}
```

**限制与注意：**

- C99 引入，C11 起改为**可选**特性（不支持 VLA 的编译器可定义 `__STDC_NO_VLA__`）
- VLA 分配在栈上，过大可能导致**栈溢出**
- 不能用于全局或 `static` 变量
- `sizeof` 对 VLA 在运行时求解，而非编译期

```c
int n = 5;
int vla[n];
printf("%zu\n", sizeof(vla));   // 运行时计算：5 * sizeof(int)
```

> **嵌入式注意：** 裸机或 RTOS 环境栈空间有限，VLA 可能带来栈溢出风险，谨慎使用。

### 24.2 柔性数组成员（FAM, C99）

结构体的最后一个成员可以是不完整数组类型：

```c
#include <stddef.h>
#include <stdlib.h>

struct flex_array {
    size_t count;
    int data[];            // 柔性数组成员，不占结构体大小
};

// 分配
size_t n = 10;
struct flex_array *fa = malloc(sizeof(struct flex_array) + n * sizeof(int));
fa->count = n;
for (size_t i = 0; i < n; i++)
    fa->data[i] = (int)i;

// 释放
free(fa);
```

**关键规则：**

- FAM 必须是结构体**最后一个**成员
- 结构中至少有一个其他命名成员
- `sizeof` 不包含 FAM 的大小
- 只能用 `malloc` / `calloc` / `realloc` 分配（不能用静态或栈分配）
- 相较于"指针 + 单独 malloc"方式，FAM 将元数据和数据放在同一块内存中，减少碎片、提升局部性

```c
// 对比：传统指针方式（两次分配）
struct ptr_based {
    size_t count;
    int *data;
};

// FAM 方式（一次分配）
struct fam_based {
    size_t count;
    int data[];
};
```

---

## 25. `restrict` 关键字

`restrict` 是类型限定符（C99），告诉编译器：**通过该指针访问的对象，不会通过其他指针被同时访问。**

```c
void vector_add(int *restrict c, const int *restrict a, const int *restrict b, int n) {
    for (int i = 0; i < n; i++)
        c[i] = a[i] + b[i];
}
```

这里 `restrict` 保证 `c` 指向的区域不会被 `a` 或 `b` 访问，使编译器能更好地优化（矢量化和指令调度）。

**违反承诺的后果：** 如果实际传入重叠区域，结果是未定义行为。

```c
int arr[5] = {1,2,3,4,5};
vector_add(arr, arr, arr, 5);   // UB：c, a, b 指向重叠区域
```

**常用场景：**

- `memcpy` 的声明中使用 `restrict`（而 `memmove` 不用）
- 数学库中的向量 / 矩阵运算
- DSP 和 SIMD 优化代码

```c
// memcpy 原型（src 和 dst 不能重叠）
void *memcpy(void *restrict dst, const void *restrict src, size_t n);
// memmove 原型（允许重叠）
void *memmove(void *dst, const void *src, size_t n);
```

---

## 26. 对齐、布局与 ABI

### 26.1 基本对齐规则

每个对象类型都有**对齐要求**——地址必须是某个值的倍数。常见对齐：

| 类型 | 典型对齐 |
|------|---------|
| `char` | 1 字节 |
| `short` | 2 字节 |
| `int`, `float` | 4 字节 |
| `double` | 8 字节（32位下可能为 4） |
| `void *` | 4 或 8 字节 |

### 26.2 结构体对齐与 padding

```c
#include <stddef.h>

struct S {
    char  c;      // 偏移 0
    int   i;      // 偏移 4（有 3 字节 padding）
    short s;      // 偏移 8
};                 // 总大小 12（末尾有 2 字节 padding 对齐到 4 的倍数）
```

使用 `offsetof` 宏查看成员偏移：

```c
#include <stddef.h>
printf("offset of i = %zu\n", offsetof(struct S, i));  // 通常输出 4
```

### 26.3 `_Alignas` 与 `_Alignof`（C11）

```c
#include <stdalign.h>   // 提供 alignas / alignof 宏

printf("alignment of double = %zu\n", alignof(double));

// 指定更严格的对齐
struct alignas(64) cache_line {
    int data[16];
};  // 该结构体按 64 字节对齐（适合缓存行）
```

### 26.4 不同 ABI 的布局差异

| ABI | `int` | `long` | `void *` | `long long` | 常见平台 |
|-----|-------|--------|----------|-------------|---------|
| ILP32 | 4 | 4 | 4 | 8 | x86-32, ARM-32 |
| LP64 | 4 | 8 | 8 | 8 | Linux/macOS 64-bit |
| LLP64 | 4 | 4 | 8 | 8 | Windows 64-bit |

> 跨平台代码应使用 `<stdint.h>` 中的 `int32_t` / `int64_t` / `intptr_t` 等固定宽度类型，避免依赖 `int` / `long` 的具体大小。

### 26.5 调用约定简介

| 约定 | 平台 | 特点 |
|------|------|------|
| `cdecl` | x86-32 | 调用者清理栈，支持可变参数 |
| `stdcall` | Win32 | 被调用者清理栈，不可变参 |
| `fastcall` | 各平台 | 前几个参数通过寄存器传递 |
| System V | x86-64 / ARM64 | 参数通过寄存器传递（如 RDI, RSI, RDX...） |
| Microsoft x64 | x86-64 Windows | 参数通过 RCX, RDX, R8, R9 传递 |

```c
// Windows 上显式指定调用约定
__attribute__((stdcall)) void win_api(void);  // GCC/MinGW
__stdcall void win_api(void);                  // MSVC
```

---

## 27. C11 原子操作与线程安全

### 27.1 原子类型（`_Atomic`）

```c
#include <stdatomic.h>

atomic_int counter = 0;
atomic_flag flag = ATOMIC_FLAG_INIT;
```

### 27.2 基本操作

```c
atomic_int val = ATOMIC_VAR_INIT(0);  // C11 初始化（C17 起不推荐用宏）

atomic_store(&val, 42);
int x = atomic_load(&val);
int old = atomic_fetch_add(&val, 1);   // 原子自增，返回旧值
```

### 27.3 `volatile` vs `_Atomic`

```c
volatile int flag;     // 防止编译器优化读写，但非原子、无顺序保证
atomic_int a_flag;     // 原子操作 + 内存序（默认 memory_order_seq_cst）
```

> **关键区别：** `volatile` 不解决并发问题。多线程共享数据必须用 `_Atomic` 或互斥锁。

### 27.4 内存序（Memory Order）

```c
atomic_store_explicit(&val, 1, memory_order_release);
int x = atomic_load_explicit(&val, memory_order_acquire);
```

| 内存序 | 说明 |
|--------|------|
| `memory_order_relaxed` | 仅保证原子性，无顺序约束 |
| `memory_order_acquire` | 防止之后读写操作重排到 load 之前 |
| `memory_order_release` | 防止之前读写操作重排到 store 之后 |
| `memory_order_acq_rel` | acquire + release（用于 RMW 操作） |
| `memory_order_seq_cst` | 全局顺序一致（默认） |

**经典用例（release-acquire 实现标志传递）：**

```c
atomic_int ready = 0;
int data = 0;

// 线程 A——生产者
data = 42;
atomic_store_explicit(&ready, 1, memory_order_release);

// 线程 B——消费者
while (atomic_load_explicit(&ready, memory_order_acquire) == 0)
    ;
printf("%d\n", data);   // 保证读到 42
```

> 对大多数场景，使用默认的 `memory_order_seq_cst` 即可；仅在性能热点才考虑降级到 weaker order。误用 weak order 导致的 bug 极难排查。

### 27.5 互斥锁替代方案

```c
#include <threads.h>   // C11（可选，实际多使用 POSIX threads）
mtx_t mutex;
mtx_init(&mutex, mtx_plain);
mtx_lock(&mutex);
// 临界区
mtx_unlock(&mutex);
mtx_destroy(&mutex);
```

> 嵌入式或跨平台环境更常用 POSIX threads（`<pthread.h>`）或平台原生 API。

---

## 28. 安全编码清单

### 28.1 输入验证

- `scanf` 系列**必须检查返回值**：`if (scanf("%d", &x) != 1) { /* 错误处理 */ }`
- 使用 `fgets` + `sscanf` 替代裸 `scanf`，避免缓冲区残留问题
- `snprintf` 替代 `sprintf`，指定缓冲区大小
- 所有外部输入（文件、网络、命令行）都应视为不可信

### 28.2 缓冲区安全

```c
// 错误：未限制长度
char buf[10];
strcpy(buf, user_input);           // 危险

// 正确：限制拷贝长度
strncpy(buf, user_input, sizeof(buf) - 1);
buf[sizeof(buf) - 1] = '\0';      // strncpy 可能不追加 \0

// 最佳：snprintf
snprintf(buf, sizeof(buf), "%s", user_input);
```

### 28.3 `strncpy` 语义陷阱

`strncpy` 在源串长度 >= n 时**不追加 `\0`**，且会填充剩余字节为 `\0`（效率低）。

```c
char dst[10];
strncpy(dst, "hello world", sizeof(dst));   // dst 无 \0！
// 安全做法：
dst[sizeof(dst) - 1] = '\0';
```

### 28.4 整数安全

```c
size_t a = SIZE_MAX;
size_t b = 2;
if (a + b < a) {   // 检查无符号溢出回绕
    // 溢出
}

// 分配时检查乘积溢出
size_t n = 100, sz = sizeof(int);
if (n > SIZE_MAX / sz) {
    /* 溢出，无法安全分配 */
}
int *p = malloc(n * sz);
```

### 28.5 资源管理

- `malloc` / `calloc` / `realloc` 后立即判空
- `free` 后建议置 `NULL`（不能防止别名悬空，但有助于调试）
- 文件 / 锁 / 句柄等资源：在同一个函数中申请和释放，避免资源泄漏
- 复杂资源路径优先用 `goto` 或 RAII 风格（通过 `cleanup` 属性等）集中清理

### 28.6 错误传播

```c
int do_work(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return -1;

    int ret = process(f);   // 子函数返回 0 成功，负值失败
    fclose(f);
    return ret;
}
```

每层函数都应：
1. 检查下层返回值
2. 清理本层资源
3. 向上传播错误码（或记录日志）

### 28.7 危险函数速查

| 危险函数 | 问题 | 替代方案 |
|---------|------|---------|
| `gets()` | 无法限制输入长度（C11 已移除） | `fgets()` |
| `strcpy()` | 不检查目标容量 | `strncpy()` + 手动置 `\0` / `snprintf()` |
| `strcat()` | 不检查目标剩余容量 | `strncat()` |
| `sprintf()` | 不检查输出长度 | `snprintf()` |
| `scanf("%s", buf)` | 无边界控制 | `fgets()` + `sscanf()` 或宽度限定 `scanf("%99s", buf)` |
| `system()` | 平台相关、注入风险 | POSIX `exec()` 系列或直接代码逻辑 |
| `rand()` | 质量低、可预测 | POSIX `random()` 或平台 CSPRNG |

---

## 29. 编译器扩展可移植性对照

### 29.1 常用 GNU 扩展与标准 C 替代

| GNU 扩展 | 用途 | 标准 C 替代 |
|----------|------|------------|
| `typeof(x)` | 获取表达式类型 | `_Generic`（C11）；C23 已正式标准化 `typeof` |
| `({ ... })` 语句表达式 | 在宏中安全求值 | `_Generic` / 内联 `static inline` 函数 |
| `##__VA_ARGS__` | 空变参时去除前逗号 | 需要显式处理（标准 C 不直接支持） |
| `__attribute__((packed))` | 禁止结构体填充 | `_Static_assert` + `sizeof` 验证（非完全等价） |
| `__attribute__((weak))` | 弱符号定义 | 无标准等价物（依赖链接器） |
| `__attribute__((aligned(n)))` | 指定对齐 | `_Alignas`（C11） |
| `__attribute__((section(".name")))` | 放到指定段 | 无标准替代 |
| `__builtin_expect(expr, 1)` | 分支预测提示 | `[[likely]]` / `[[unlikely]]`（C23） |
| `__builtin_constant_p(expr)` | 编译期常量检测 | 无标准替代 |

### 29.2 MSVC 特有与移植方案

| 用途 | MSVC | GCC/Clang | 移植策略 |
|------|------|-----------|---------|
| 禁止填充 | `#pragma pack(push, 1)` / `#pragma pack(pop)` | `__attribute__((packed))` | 条件宏 |
| 内联汇编 | `__asm { ... }` | `asm("...")` | 条件宏 + 统一接口函数 |
| 函数声明 | `__declspec(dllimport/export)` | `__attribute__((visibility("default")))` | 条件宏 |
| 分支提示 | `__assume(cond)` | `__builtin_expect` | 条件宏 |

```c
// 条件宏示例：packed 属性跨平台
#ifdef _MSC_VER
  #define PACKED_STRUCT(name) \
      __pragma(pack(push, 1)) struct name __pragma(pack(pop))
#else
  #define PACKED_STRUCT(name) \
      struct __attribute__((packed)) name
#endif

PACKED_STRUCT(Packet) {
    char type;
    int len;
};
```

