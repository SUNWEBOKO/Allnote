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
#define SWAP(a, b) do { typeof(a) _t = (a); (a) = (b); (b) = _t; } while(0)
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
            __FILE__, __LINE__, __func__, ##__VA_ARGS__)
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

### 4.9 更安全的 GNU 风格写法

```c
#define MIN(A, B) ({             \
    typeof(A) _a = (A);          \
    typeof(B) _b = (B);          \
    _a < _b ? _a : _b;           \
})
```

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

`+`、`-`、`*`、`/`、`%`

### 7.2 关系运算符

`==`、`!=`、`>`、`<`、`>=`、`<=`

### 7.3 逻辑运算符

`&&`、`||`、`!`

### 7.4 赋值运算符

`=`、`+=`、`-=`、`*=`、`/=`、`%=` 等

### 7.5 三目运算符

```c
int max = (a > b) ? a : b;
```

### 7.6 位运算符（嵌入式高频）

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

### 7.7 访问类运算符

- `()`：函数调用
- `[]`：数组访问
- `*`：解引用
- `&`：取地址
- `.`：访问结构体成员
- `->`：访问结构体指针成员

---

## 8. 控制流

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

### 8.2 `switch`

```c
switch (state) {
case 0:
    break;
case 1:
    break;
default:
    break;
}
```

### 8.3 循环语句

```c
for (int i = 0; i < 10; i++) { }
while (flag) { }
do { } while (cond);
```

### 8.4 `break` / `continue` / `return`

- `break`：跳出当前循环或 `switch`
- `continue`：结束本轮循环，进入下一轮
- `return`：结束整个函数

### 8.5 `goto`

很多教材把 `goto` 写得很可怕，但工程里它在**失败回滚路径**特别有用。

```c
p1 = malloc(...);
if (!p1) return -1;

p2 = malloc(...);
if (!p2) goto fail_1;

p3 = malloc(...);
if (!p3) goto fail_2;

free(p3);
fail_2:
free(p2);
fail_1:
free(p1);
```

> 在资源申请、错误回退、驱动初始化失败清理路径中，`goto` 反而可能让代码更清楚。

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
    // 默认实现
}
```

如果用户工程里再定义一个同名强符号函数，默认实现会被覆盖。

#### 典型用途

- 默认钩子函数
- 板级初始化
- 中断回调默认实现
- 框架保底行为

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

### 10.8 动态数组

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

### 11.10 常见指针错误

1. 未初始化指针
2. 野指针
3. 空指针解引用
4. 越界访问
5. `free` 后继续使用
6. 返回局部变量地址

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

### 12.5 安全性提醒

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

### 13.5 `packed` 属性

```c
struct __attribute__((packed)) Packet {
    char type;
    int len;
};
```

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
typedef unsigned char uint8_t;

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

建议把变量放到寄存器中，但现代编译器通常会自行优化，实际意义已经不大。

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

### 14.5 `const`

`const` 更准确的理解不是“常量”，而是 **read only（只读）**。

```c
const int a = 10;
int const b = 20;
```

### 14.6 `const` 指针的三种常见写法

```c
const int *p;        // 不能通过 p 改 *p
int * const p2 = &x; // p2 本身不可改指向
const int * const p3 = &x; // 两者都不可改
```

### 14.7 `volatile`

告诉编译器：**这个变量的值可能在程序控制之外发生变化，不要把对它的读写随意优化掉。**

```c
volatile unsigned char buff;
while (buff == 0) {
    // 等待硬件更新
}
```

#### 典型场景

- 硬件寄存器
- 中断共享变量
- 并发共享标志位

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
int *p = malloc(sizeof(int));
if (p == NULL) {
    return;
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

### 17.4 调试建议

- 用 `gcc -g` 生成调试信息
- 用 `gdb` 看断点、变量、调用栈
- 借助日志宏带上 `__FILE__`、`__LINE__`、`__func__`
- 先定位是“编译期、链接期还是运行期”问题

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
abs(), fabs(), sqrt(), pow(), sin(), cos(), tan(), log(), exp()
```

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
