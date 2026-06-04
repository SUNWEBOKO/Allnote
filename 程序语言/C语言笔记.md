# C 语言笔记

> 这份笔记按“能写程序 → 能看懂内存 → 能组织工程 → 能避坑”的顺序整理。  
---

## 1. 学习主线

学 C 不要只把它当成语法清单。C 的价值在于它同时能连接三件事：

- **编译器视角**：源码如何经过预处理、编译、汇编、链接，最后变成可执行文件。
- **内存视角**：变量、数组、指针、字符串、结构体最终都落在内存里的某个位置。
- **工程视角**：通过函数、结构体、函数指针、回调、宏和多文件组织写出可维护的模块。

嵌入式、驱动、RTOS、Linux 内核等场景仍大量使用 C，是因为 C 具备三个特点：

1. **贴近硬件**：能操作地址、寄存器、位、内存布局。
2. **结果可控**：代码体积、执行成本、内存使用相对可预测。
3. **工程能力强**：虽然没有类，但可以用结构体、接口函数、回调、弱符号等方式做模块化设计。

这份笔记的阅读顺序建议：先掌握基础语法，再重点攻克**指针、内存、结构体、宏、工程组织**。

---

## 2. 从源码到可执行文件

C 程序从 `.c` 文件到可执行文件，通常经历四个阶段：

```text
hello.c -> 预处理 -> hello.i -> 编译 -> hello.s -> 汇编 -> hello.o -> 链接 -> 可执行文件
```

| 阶段 | 做什么 | 常见输出 | 常用命令 |
|---|---|---|---|
| 预处理 | 展开 `#include`、`#define`、条件编译 | `.i` | `gcc -E hello.c -o hello.i` |
| 编译 | 语法/语义检查，生成汇编 | `.s` | `gcc -S hello.c -o hello.s` |
| 汇编 | 汇编转机器码 | `.o` | `gcc -c hello.c -o hello.o` |
| 链接 | 合并目标文件和库，解析符号 | 可执行文件 | `gcc hello.o -o hello` |

常用命令：

```bash
# 一步编译并链接
gcc hello.c -o hello

# 多文件编译
gcc main.c uart.c gpio.c -o app

# 显示详细编译过程
gcc -v hello.c -o hello
```

### 2.1 常见错误按阶段定位

| 错误类型 | 常见信息 | 优先排查 |
|---|---|---|
| 预处理错误 | 找不到头文件、宏展开异常 | `#include` 路径、宏定义、条件编译 |
| 编译错误 | syntax error、undeclared identifier | 语法、类型、变量/函数声明 |
| 链接错误 | `undefined reference`、`multiple definition` | 函数未实现、重复定义、库未链接 |

看到 `undefined reference` 或 `multiple definition`，说明源码已经通过编译，问题发生在**链接阶段**。

---

## 3. 最小 C 程序与基本规范

### 3.1 最小程序结构

```c
#include <stdio.h>

int main(void)
{
    printf("hello c\n");
    return 0;
}
```

重点：

- `#include <stdio.h>` 引入标准输入输出声明。
- `main` 是程序入口，一个完整程序只能有一个 `main`。
- `return 0;` 表示程序正常结束。
- 推荐写 `int main(void)`，表示 `main` 不接收参数。

### 3.2 注释怎么写才有价值

```c
// 单行注释

/* 多行注释 */
```

好的注释解释“为什么这样写”，而不是机械翻译代码。

```c
// 等待硬件置位，不能删除 volatile 读取
while ((UART_STATUS & TX_READY) == 0) {
}
```

尤其需要注释的地方：

- 寄存器位操作
- 复杂指针
- 状态机
- 资源申请和失败回滚
- 宏展开有特殊意图的代码

### 3.3 命名与风格

建议统一风格，不要混用多种命名习惯：

```c
int sensor_count;
uint32_t uart_status;
void uart_send_byte(uint8_t data);
```

工程建议：

- 变量定义时尽量初始化。
- 指针初始化为 `NULL`。
- 函数职责单一。
- 驱动层、协议层、业务层分开。
- 复杂逻辑优先拆函数，不要写成一大坨。

---

## 4. 变量、常量与基本类型

### 4.1 变量声明与初始化

变量必须先声明后使用：

```c
int count;          // 声明，未初始化
int number = 100;   // 声明并初始化
number = 200;       // 赋值
```

常见错误：

```c
int a = 10;
int a = 20;      // 错误：重复定义

x = 10;          // 错误：x 未声明
```

连续赋值可以用，但不要写得太绕：

```c
int x, y;
x = y = 10;      // 从右往左：先 y=10，再 x=10
```

### 4.2 标识符与关键字

标识符命名规则：

1. 由字母、数字、下划线组成。
2. 不能以数字开头。
3. 不能是 C 关键字。

```c
int count;       // 合法
int _index;      // 合法
int 3abc;        // 错误
int case;        // 错误，case 是关键字
```

`main` 不是关键字，但它是程序入口函数名，不要拿它做别的用途。

### 4.3 基本类型

| 类型 | 常见大小 | 说明 | `printf` | `scanf` |
|---|---:|---|---|---|
| `char` | 1 | 字符/小整数 | `%c` | `%c` |
| `short` | 2 | 短整型 | `%hd` | `%hd` |
| `int` | 4 | 常用整型 | `%d` | `%d` |
| `long` | 4 或 8 | 平台相关 | `%ld` | `%ld` |
| `long long` | 至少 8 | 长整型 | `%lld` | `%lld` |
| `unsigned int` | 4 | 无符号整型 | `%u` | `%u` |
| `float` | 4 | 单精度浮点 | `%f` | `%f` |
| `double` | 8 | 双精度浮点 | `%f` | `%lf` |

跨平台代码不要假设 `int`、`long` 的大小。嵌入式和协议代码建议使用：

```c
#include <stdint.h>

uint8_t  byte;
uint16_t reg;
uint32_t status;
int32_t  temperature;
uintptr_t addr;
```

### 4.4 `sizeof`

`sizeof` 得到对象或类型占用的字节数：

```c
sizeof(int);
sizeof arr;
sizeof(struct Packet);
```

数组长度常用写法：

```c
int arr[10];
size_t len = sizeof(arr) / sizeof(arr[0]);
```

注意：这个写法只在 `arr` 仍然是数组时成立。数组传进函数后会退化为指针，函数里不能靠 `sizeof(arr)` 算长度。

```c
void print_arr(int arr[], size_t len)   // len 必须额外传入
{
    for (size_t i = 0; i < len; i++) {
        printf("%d ", arr[i]);
    }
}
```

### 4.5 字符、转义字符与字符串结束符

字符本质上是整数编码。常用规律：

```c
'0' ~ '9'  // 连续
'A' ~ 'Z'  // 连续
'a' ~ 'z'  // 连续
```

字符数字转整数：

```c
int x = ch - '0';   // '9' -> 9
```

常见转义字符：

| 转义 | 含义 |
|---|---|
| `\0` | 空字符，字符串结束标记 |
| `\n` | 换行 |
| `\t` | 制表符 |
| `\'` | 单引号 |
| `\"` | 双引号 |
| `\\` | 反斜杠 |

`'\0'` 非常重要：C 字符串必须以它结尾。

### 4.6 浮点数比较

浮点数不适合直接用 `==` 比较，因为很多十进制小数在二进制中不能精确表示。

```c
#include <math.h>

if (fabs(a - b) < 1e-6) {
    // 认为 a 和 b 相等
}
```

---

## 5. 运算符与表达式

### 5.1 算术运算

```c
+   -   *   /   %
```

整数除法会截断小数：

```c
5 / 2      // 2
5.0 / 2    // 2.5
```

`%` 只能用于整数：

```c
10 % 3     // 1
10.0 % 3   // 错误
```

除数不能为 0：

```c
if (b != 0) {
    c = a / b;
}
```

### 5.2 自增自减

| 表达式 | 含义 |
|---|---|
| `++a` | 先加，再使用新值 |
| `a++` | 先使用旧值，再加 |
| `--a` | 先减，再使用新值 |
| `a--` | 先使用旧值，再减 |

```c
int a = 5;
int b = ++a;   // a=6, b=6
int c = a++;   // c=6, a=7
```

不要在一个复杂表达式里多次修改同一个变量：

```c
i = i++ + ++i;   // 未定义行为，不要写
```

### 5.3 关系与逻辑运算

关系运算结果为 `1` 或 `0`：

```c
9 > 8     // 1
7 < 6     // 0
```

`=` 是赋值，`==` 才是判等：

```c
if (x == 5) { }   // 正确
if (x = 5)  { }   // 高危：赋值后条件为真
```

连续比较不是数学写法：

```c
x < y < z          // 错误理解，实际是 (x < y) < z
x < y && y < z     // 正确
```

逻辑运算短路：

```c
if (p != NULL && *p == 10) {
    // p 为空时不会执行 *p
}
```

### 5.4 赋值与复合赋值

```c
a += 2;   // a = a + 2
a -= 2;
a *= 2;
a /= 2;
a %= 2;
```

复杂复合赋值不建议写。能拆就拆：

```c
m *= y;
y -= m;
y += y;
```

可读性比“炫技”更重要。

### 5.5 三目运算符

```c
int max = (a > b) ? a : b;
```

适合简单选择，不适合嵌套过深：

```c
// 不推荐，可读性差
x = a ? (b ? c : d) : e;
```

### 5.6 强制类型转换

```c
(int)3.14      // 3，截断，不四舍五入
```

注意转换时机：

```c
(float)(10 / 4)   // 2.0：先整数除法，再转 float
(float)10 / 4     // 2.5：先把 10 转 float
```

### 5.7 位运算：嵌入式高频

| 运算符 | 含义 |
|---|---|
| `&` | 按位与 |
| `|` | 按位或 |
| `^` | 按位异或 |
| `~` | 按位取反 |
| `<<` | 左移 |
| `>>` | 右移 |

典型操作：

```c
reg |=  (1U << 3);   // 置位 bit3
reg &= ~(1U << 3);   // 清零 bit3
reg ^=  (1U << 3);   // 翻转 bit3

if (reg & (1U << 3)) {
    // bit3 为 1
}
```

位运算尽量使用无符号类型，例如 `uint32_t`，避免有符号右移和溢出的不确定性。

### 5.8 优先级建议

不建议死背完整优先级表。实战中记住：

```text
一元 > 算术 > 关系 > 逻辑 > 条件 > 赋值 > 逗号
```

不确定时加括号，尤其是宏、位运算、条件表达式。

---

## 6. `printf`、`scanf` 与安全输入

### 6.1 `printf`

```c
printf("A=%d, B=%d\n", a, b);
```

格式控制符必须和参数类型匹配：

| 类型 | 格式 |
|---|---|
| `int` | `%d` |
| `unsigned int` | `%u` |
| `long` | `%ld` |
| `long long` | `%lld` |
| `float` / `double` | `%f` |
| `char` | `%c` |
| 字符串 | `%s` |
| 十六进制 | `%x` / `%X` |
| 指针 | `%p` |
| `size_t` | `%zu` |

宽度与精度：

```c
printf("%5d\n", 10);      // 宽度至少 5，右对齐
printf("%.2f\n", 3.1415); // 保留两位小数
```

### 6.2 `scanf`

普通变量要传地址：

```c
int age;
scanf("%d", &age);
```

字符串数组名本身就是地址：

```c
char name[32];
scanf("%31s", name);   // 最多读 31 个字符，给 \0 留空间
```

必须检查返回值：

```c
int x;
if (scanf("%d", &x) != 1) {
    // 输入不是整数，做错误处理
}
```

`%c` 不会自动跳过空白字符：

```c
char ch;
scanf(" %c", &ch);   // 前面的空格用于跳过换行、空格、Tab
```

### 6.3 更推荐的输入方式：`fgets` + 解析

`scanf` 容易受到缓冲区残留和格式匹配问题影响。复杂输入更推荐：

```c
char line[128];
int x;

if (fgets(line, sizeof(line), stdin) != NULL) {
    if (sscanf(line, "%d", &x) == 1) {
        // 解析成功
    }
}
```

`gets()` 不安全，已经不应该使用。

---

## 7. 控制流：分支与循环

### 7.1 `if` / `else`

```c
if (x > 0) {
    puts("positive");
} else if (x == 0) {
    puts("zero");
} else {
    puts("negative");
}
```

建议即使只有一行也写花括号，减少维护时出错：

```c
if (ready) {
    start();
}
```

警惕空语句：

```c
if (x > 0);   // 错误：if 控制的是空语句
{
    do_work();
}
```

### 7.2 `switch`

```c
switch (state) {
case IDLE:
    start();
    break;

case RUNNING:
    update();
    break;

default:
    reset();
    break;
}
```

要点：

- `switch` 表达式通常是整型、字符型或枚举。
- `case` 后必须是常量表达式。
- 忘记 `break` 会发生 case 穿透。
- 有意穿透时要写注释。

```c
case 10:
case 9:
    grade = 'A';
    break;
```

### 7.3 `while`、`do while`、`for`

`while`：先判断，再执行。

```c
while (condition) {
    work();
}
```

`do while`：至少执行一次。

```c
do {
    read_input();
} while (!valid);
```

`for`：最适合次数明确的循环。

```c
for (int i = 0; i < n; i++) {
    printf("%d\n", i);
}
```

### 7.4 `break` 与 `continue`

| 语句 | 作用 |
|---|---|
| `break` | 退出当前循环或 `switch` |
| `continue` | 跳过本轮循环剩余部分，进入下一轮 |

```c
for (int i = 0; i < 10; i++) {
    if (i % 2 == 0) {
        continue;
    }
    if (i > 7) {
        break;
    }
    printf("%d ", i);  // 1 3 5 7
}
```

### 7.5 `goto` 的合理使用场景

不建议用 `goto` 写普通流程，但在资源清理路径中很实用：

```c
int init_device(void)
{
    int ret = -1;
    void *buf = malloc(1024);
    if (buf == NULL) {
        goto out;
    }

    FILE *fp = fopen("config.txt", "r");
    if (fp == NULL) {
        goto free_buf;
    }

    ret = 0;
    fclose(fp);

free_buf:
    free(buf);
out:
    return ret;
}
```

核心原则：普通逻辑用结构化控制流；多资源失败回滚可以用 `goto` 统一出口。

---

## 8. 函数与模块化

### 8.1 函数的基本形式

```c
int add(int a, int b)
{
    return a + b;
}
```

函数有三件事：

1. 函数名
2. 参数
3. 返回值

函数定义在调用之后时，调用前要有声明：

```c
int add(int a, int b);

int main(void)
{
    int x = add(2, 3);
    return 0;
}

int add(int a, int b)
{
    return a + b;
}
```

### 8.2 参数传递的本质：拷贝

C 的函数参数传递本质上都是拷贝。

值传递不会修改外部变量：

```c
void inc(int x)
{
    x++;
}
```

地址传递可以通过指针修改外部对象：

```c
void inc(int *x)
{
    if (x != NULL) {
        (*x)++;
    }
}
```

交换两个变量：

```c
void swap(int *a, int *b)
{
    int tmp = *a;
    *a = *b;
    *b = tmp;
}
```

### 8.3 返回多个结果

C 函数只能直接返回一个值。需要多个结果时，常用指针参数：

```c
int divide(int a, int b, int *q, int *r)
{
    if (b == 0 || q == NULL || r == NULL) {
        return -1;
    }

    *q = a / b;
    *r = a % b;
    return 0;
}
```

### 8.4 递归

递归必须包含：

- 终止条件
- 递推关系

```c
int fact(int n)
{
    if (n <= 1) {
        return 1;
    }
    return n * fact(n - 1);
}
```

递归会消耗栈空间。嵌入式中栈小，深递归要谨慎。

### 8.5 函数指针与回调

函数名本质上可以看作函数入口地址。

```c
int add(int a, int b) { return a + b; }
int (*fp)(int, int) = add;
```

回调把“行为”交给调用方决定：

```c
void process(int a, int b, int (*op)(int, int))
{
    printf("%d\n", op(a, b));
}
```

通用接口常见写法：

```c
typedef void (*event_cb_t)(void *ctx, int event);

void register_callback(event_cb_t cb, void *ctx);
```

`void *` 用来抽象数据，函数指针用来抽象行为。

### 8.6 推荐的函数风格

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

- 入口先校验参数。
- 返回值表达成功或失败。
- 函数只做一件事。
- 命名体现模块和动作。

---

## 9. 数组、字符串与指针

这部分是 C 的核心。数组、字符串和指针不要分开死记，它们本质上都和**连续内存 + 地址访问**有关。

### 9.1 一维数组

```c
int a[5] = {1, 2, 3, 4, 5};
```

要点：

- 下标从 0 开始。
- 最后一个元素是 `a[4]`。
- 访问 `a[5]` 是越界。
- 部分初始化时，剩余元素自动补 0。

```c
int b[5] = {1, 2};   // {1, 2, 0, 0, 0}
```

遍历：

```c
for (size_t i = 0; i < sizeof(a) / sizeof(a[0]); i++) {
    printf("%d\n", a[i]);2
}
```

### 9.2 二维数组

```c
int mat[2][3] = {
    {1, 2, 3},
    {4, 5, 6}
};
```

二维数组按行连续存储。`mat[i][j]` 的偏移是：

```text
i * 列数 + j
```

省略维度时只能省略第一维：

```c
int a[][3] = {{1, 2, 3}, {4, 5, 6}};  // 正确
// int b[2][] = ...                   // 错误
```

### 9.3 指针基础

指针变量保存地址：

```c
int a = 10;
int *p = &a;
printf("%d\n", *p);   // 解引用，得到 a 的值
```

访问指针前先问两件事：

1. 这个地址是否有效？
2. 应该按什么类型解释这块内存？

```c
int *p = NULL;
if (p != NULL) {
    printf("%d\n", *p);
}
```

### 9.4 指针运算

```c
int arr[5] = {1, 2, 3, 4, 5};
int *p = arr;

p++;    // 前进一个 int，不是一个字节
```

`a[i]` 等价于 `*(a + i)`：

```c
printf("%d\n", a[2]);       // 3
printf("%d\n", *(a + 2));   // 3
```

### 9.5 数组名与指针不是一回事

```c
int a[5] = {0};
int *p = a;

sizeof(a);   // 整个数组大小，如 20
sizeof(p);   // 指针变量大小，32 位为 4，64 位为 8
```

数组名多数表达式中会退化为首元素地址，但它不是普通指针变量，不能这样写：

```c
// a++;   // 错误
p++;      // 正确
```

`arr` 和 `&arr` 数值可能相同，但类型不同：

```c
int arr[10];
arr;    // int *，指向 arr[0]
&arr;   // int (*)[10]，指向整个数组
```

### 9.6 指针数组与数组指针

```c
int *pa[10];     // 指针数组：数组里有 10 个 int *
int (*ap)[10];   // 数组指针：指向“含 10 个 int 的数组”
```

读复杂声明时，从变量名出发，优先看右边，再看左边。

### 9.7 字符串

C 字符串是以 `\0` 结尾的字符数组：

```c
char s[] = "hello";
```

实际内存：

```text
'h' 'e' 'l' 'l' 'o' '\0'
```

字符串常量与字符数组不同：

```c
char *p = "hello";     // 指向只读字符串常量，不要修改
char arr[] = "hello";  // 拷贝到数组，可以修改

// p[0] = 'H';          // 未定义行为
arr[0] = 'H';           // 正确
```

常用字符串函数：

```c
strlen(s);
strcmp(a, b);
strchr(s, 'x');
strstr(s, "abc");
snprintf(buf, sizeof(buf), "%s", src);
```

谨慎使用 `strcpy`、`strcat`，必须确认目标缓冲区足够大。更推荐 `snprintf` 或带长度限制的写法。

### 9.8 指针常见错误

| 错误 | 示例 | 后果 |
|---|---|---|
| 未初始化指针 | `int *p; *p = 1;` | 野指针写入 |
| 空指针解引用 | `int *p = NULL; *p = 1;` | 崩溃或未定义行为 |
| 数组越界 | `a[5]` 访问 `int a[5]` | 破坏相邻内存 |
| 释放后继续使用 | `free(p); *p = 1;` | 悬空指针 |
| 返回局部变量地址 | `return &x;` | 生命周期结束后访问 |
| 函数内 `sizeof(arr)` | 数组参数退化为指针 | 算不出数组长度 |

---

## 10. 结构体、联合体、枚举与 `typedef`

### 10.1 结构体

结构体把相关数据组织在一起：

```c
struct Student {
    char name[20];
    int age;
    float score;
};

struct Student s = {"Tom", 20, 95.5f};
```

结构体指针访问成员：

```c
struct Student *ps = &s;
printf("%s\n", ps->name);
```

### 10.2 结构体作为模块状态

工程中常把模块状态放进结构体，再通过函数操作：

```c
struct uart_dev {
    uint32_t base;
    uint32_t baudrate;
    int opened;
};

int uart_open(struct uart_dev *dev);
int uart_write(struct uart_dev *dev, const uint8_t *buf, size_t len);
```

这就是 C 中常见的“封装”。

### 10.3 结构体对齐

结构体大小不一定等于成员大小简单相加：

```c
struct A {
    char c;
    int i;
};
```

它通常不是 5 字节，因为 `int` 需要按地址对齐，中间可能有 padding。

查看偏移：

```c
#include <stddef.h>

printf("%zu\n", offsetof(struct A, i));
```

通信协议、寄存器映射、二进制文件格式中，要特别注意结构体布局。

### 10.4 联合体

联合体多个成员共享同一块内存：

```c
union Data {
    int i;
    float f;
    char bytes[4];
};
```

常用于：

- 节省内存
- 协议字段复用
- 寄存器或数据包解释

但不要滥用联合体做类型转换，可能触发严格别名问题。

### 10.5 枚举

枚举适合表示状态、类型、事件：

```c
enum State {
    STATE_IDLE,
    STATE_RUNNING,
    STATE_ERROR
};
```

比直接使用魔法数字更清晰。

### 10.6 `typedef`

```c
typedef struct {
    int x;
    int y;
} Point;
```

`typedef` 是类型别名，不是文本替换；`#define` 是预处理文本替换。

建议：不要给基本类型乱起别名。协议、硬件、平台相关类型优先使用 `<stdint.h>`。

---

## 11. 存储期、作用域与内存模型

### 11.1 作用域

| 类型 | 说明 |
|---|---|
| 块作用域 | `{}` 内部可见 |
| 文件作用域 | 函数外定义，从定义处到文件末尾可见 |
| 函数原型作用域 | 函数声明参数名范围 |

### 11.2 生命周期

| 对象 | 生命周期 | 常见位置 |
|---|---|---|
| 局部自动变量 | 进入块创建，离开块销毁 | 栈 |
| `static` 局部变量 | 程序运行期间一直存在 | 静态区 |
| 全局变量 | 程序运行期间一直存在 | 静态区 |
| 动态内存 | `malloc` 后存在，`free` 后释放 | 堆 |

### 11.3 `static`

修饰局部变量：延长生命周期。

```c
void count(void)
{
    static int n = 0;
    n++;
    printf("%d\n", n);
}
```

修饰全局变量或函数：限制在当前 `.c` 文件可见。

```c
static int module_state;
static void helper(void);
```

工程里建议：不需要暴露给其他文件的全局变量和函数，都加 `static`。

### 11.4 `extern`

`extern` 表示变量或函数定义在别处：

```c
extern int g_value;
```

更推荐通过函数接口访问模块内部状态，而不是到处 `extern` 全局变量。

### 11.5 `const`

`const` 表示只读语义：

```c
const int max_size = 100;
```

指针相关写法：

```c
const int *p;          // 不能通过 p 修改 *p
int * const p2 = &x;   // p2 不能改指向
const int * const p3 = &x;  // 指向和值都受限
```

口诀：`const` 修饰谁，谁不能被改。

### 11.6 `volatile`

`volatile` 告诉编译器：这个对象可能被当前程序控制之外的东西修改，不要随意优化读写。

```c
volatile uint32_t *status = (volatile uint32_t *)0x40000000;
while ((*status & 0x01) == 0) {
}
```

典型场景：

- 硬件寄存器
- 中断服务程序与主循环共享的标志
- 信号处理相关变量

注意：`volatile` 不是线程同步机制。它不保证原子性，也不保证多线程内存顺序。

### 11.7 内存分区

| 区域 | 存放内容 | 生命周期 |
|---|---|---|
| 代码段 text | 程序指令 | 整个程序 |
| 只读数据 rodata | 字符串常量、只读常量 | 整个程序 |
| data / bss | 全局变量、静态变量 | 整个程序 |
| 栈 stack | 局部变量、函数调用信息 | 函数调用期间 |
| 堆 heap | 动态分配内存 | 手动控制 |

例子：

```c
char *p = "hello";      // p 在栈上，"hello" 通常在只读区
char arr[] = "hello";   // arr 在当前作用域的栈上或静态区，取决于定义位置
```

---

## 12. 动态内存管理

### 12.1 基本函数

```c
#include <stdlib.h>

void *malloc(size_t size);
void *calloc(size_t n, size_t size);
void *realloc(void *ptr, size_t size);
void free(void *ptr);
```

使用示例：

```c
int *arr = malloc(n * sizeof(arr[0]));
if (arr == NULL) {
    return -1;
}

// 使用 arr

free(arr);
arr = NULL;
```

### 12.2 分配大小写法

推荐：

```c
int *p = malloc(n * sizeof(*p));
```

这样即使 `p` 类型变化，也不容易忘记改 `sizeof`。

### 12.3 `realloc` 安全写法

不要直接覆盖原指针：

```c
int *tmp = realloc(arr, new_n * sizeof(arr[0]));
if (tmp == NULL) {
    // arr 仍然有效，可以继续释放或使用
    free(arr);
    return -1;
}
arr = tmp;
```

### 12.4 常见问题

| 问题 | 示例 | 避免方法 |
|---|---|---|
| 内存泄漏 | `malloc` 后未 `free` | 明确所有权，成对释放 |
| 重复释放 | `free(p); free(p);` | 释放后置 `NULL` |
| 越界写 | 分配 5 字节写入 20 字节 | 分配前计算容量 |
| Use After Free | `free(p); *p = 1;` | 释放后不再使用 |
| 整数溢出 | `malloc(n * size)` 溢出 | 分配前检查乘法 |

分配前检查乘法溢出：

```c
if (n > SIZE_MAX / sizeof(*p)) {
    return -1;
}
p = malloc(n * sizeof(*p));
```

---

## 13. 预处理、宏与条件编译

预处理发生在编译之前，是文本级处理。

### 13.1 常见指令

| 指令 | 用途 |
|---|---|
| `#include` | 包含头文件 |
| `#define` | 定义宏 |
| `#if` / `#ifdef` / `#ifndef` | 条件编译 |
| `#else` / `#elif` / `#endif` | 条件分支 |
| `#error` | 主动报编译错误 |
| `#pragma` | 编译器特定指令 |

### 13.2 头文件保护

```c
#ifndef UART_H
#define UART_H

int uart_init(void);
int uart_send(const char *s);

#endif
```

或使用：

```c
#pragma once
```

`#pragma once` 简洁，但不是 ISO C 标准；大多数现代编译器支持。

### 13.3 常量宏

```c
#define UART_BASE       0x40000000U
#define UART_TX_READY   (1U << 3)
```

如果只是普通只读值，优先考虑 `const`；如果用于条件编译、数组长度、位掩码、寄存器地址，宏仍然很常见。

### 13.4 函数式宏

```c
#define SQUARE(x)   ((x) * (x))
#define MAX(a, b)   ((a) > (b) ? (a) : (b))
```

宏的基本安全规则：

1. 宏体整体加括号。
2. 参数每次使用都加括号。
3. 避免参数重复求值。

危险例子：

```c
#define MIN(a, b) ((a) < (b) ? (a) : (b))

int x = MIN(i++, j);  // i++ 可能执行多次
```

能用 `static inline` 函数解决的地方，优先用函数：

```c
static inline int min_int(int a, int b)
{
    return a < b ? a : b;
}
```

### 13.5 调试日志宏

```c
#ifdef DEBUG
#define LOG(fmt, ...) \
    fprintf(stderr, "[%s:%d %s] " fmt "\n", \
            __FILE__, __LINE__, __func__, ##__VA_ARGS__)
#else
#define LOG(fmt, ...)
#endif
```

说明：`##__VA_ARGS__` 是 GNU 扩展，严格 ISO C 下不可移植。

### 13.6 条件编译

跨平台：

```c
#ifdef _WIN32
    #include <windows.h>
#elif defined(__linux__)
    #include <unistd.h>
#endif
```

Debug / Release：

```c
#ifdef DEBUG
    LOG("value=%d", value);
#endif
```

编译时定义宏：

```bash
gcc -DDEBUG main.c -o main
```

---

## 14. 多文件工程、文件操作与调试

### 14.1 多文件组织

**uart.h**：声明接口。

```c
#ifndef UART_H
#define UART_H

#include <stddef.h>
#include <stdint.h>

int uart_init(void);
int uart_write(const uint8_t *buf, size_t len);

#endif
```

**uart.c**：实现接口。

```c
#include "uart.h"

static int initialized;

int uart_init(void)
{
    initialized = 1;
    return 0;
}

int uart_write(const uint8_t *buf, size_t len)
{
    if (!initialized || buf == NULL || len == 0) {
        return -1;
    }
    return 0;
}
```

**main.c**：使用接口。

```c
#include "uart.h"

int main(void)
{
    uart_init();
    return 0;
}
```

编译：

```bash
gcc main.c uart.c -o app
```

### 14.2 文件操作

```c
FILE *fp = fopen("data.txt", "r");
if (fp == NULL) {
    perror("fopen");
    return -1;
}

fclose(fp);
```

常见模式：

| 模式 | 含义 |
|---|---|
| `r` | 只读，文件必须存在 |
| `w` | 只写，覆盖或创建 |
| `a` | 追加写 |
| `rb` / `wb` | 二进制读/写 |

常用函数：

```c
fgetc(), fputc();
fgets(), fputs();
fprintf(), fscanf();
fread(), fwrite();
```

二进制读写结构体时要注意：结构体 padding、大小端、ABI 差异可能导致跨平台不兼容。

### 14.3 错误处理

返回值必须检查：

```c
FILE *fp = fopen(path, "r");
if (fp == NULL) {
    perror("fopen");
    return -1;
}
```

`errno`：

```c
#include <errno.h>
#include <string.h>

printf("error: %s\n", strerror(errno));
```

`assert` 适合检查程序员错误，不适合处理用户输入错误：

```c
#include <assert.h>

int divide(int a, int b)
{
    assert(b != 0);
    return a / b;
}
```

### 14.4 调试建议

常用思路：

1. 能复现问题。
2. 缩小问题范围。
3. 观察输入、输出、中间状态。
4. 检查边界条件、空指针、数组越界、资源释放路径。

GDB 常用动作：

```bash
gdb ./app
b main
run
next
step
print var
backtrace
continue
```

---

## 15. 嵌入式与工程化 C

### 15.1 用结构体做封装

```c
struct led {
    uint32_t gpio_base;
    uint32_t pin;
};

int led_on(struct led *dev);
int led_off(struct led *dev);
```

结构体保存状态，函数操作状态，对外只暴露接口。

### 15.2 用函数指针表做接口

```c
struct uart_ops {
    int (*init)(void *dev);
    int (*write)(void *dev, const uint8_t *buf, size_t len);
};

struct uart_dev {
    void *base;
    const struct uart_ops *ops;
};
```

上层代码只依赖 `ops`，底层可以换不同芯片实现。

### 15.3 回调 + `void *`

```c
typedef void (*rx_callback_t)(void *ctx, const uint8_t *data, size_t len);

void uart_set_rx_callback(rx_callback_t cb, void *ctx);
```

`ctx` 用来把用户自己的上下文传回回调函数，避免依赖全局变量。

### 15.4 弱符号

```c
__attribute__((weak)) void board_init(void)
{
    // 默认实现
}
```

用户可以在自己的工程中定义同名强符号覆盖默认实现。

常用于：

- 板级初始化
- 中断回调默认函数
- 框架钩子

注意：这是 GCC/Clang 扩展，不是 ISO C 标准。

### 15.5 寄存器访问

```c
#define UART_BASE   0x40000000UL
#define UART_DR     (*(volatile uint32_t *)(UART_BASE + 0x00))
#define UART_SR     (*(volatile uint32_t *)(UART_BASE + 0x04))

#define UART_SR_TX_READY   (1U << 7)

void uart_putc(char c)
{
    while ((UART_SR & UART_SR_TX_READY) == 0) {
    }
    UART_DR = (uint32_t)c;
}
```

关键点：

- 寄存器必须用 `volatile`。
- 位操作使用无符号常量。
- 宏命名体现寄存器和位含义。

### 15.6 ABI、对齐与可移植性

常见 ABI 差异：

| ABI | `int` | `long` | 指针 | 常见平台 |
|---|---:|---:|---:|---|
| ILP32 | 4 | 4 | 4 | 32 位 ARM/x86 |
| LP64 | 4 | 8 | 8 | Linux/macOS 64 位 |
| LLP64 | 4 | 4 | 8 | Windows 64 位 |

跨平台建议：

- 用 `<stdint.h>` 的固定宽度类型。
- 用 `%zu` 打印 `size_t`。
- 不把指针强转成 `int`。
- 协议结构不要直接依赖编译器默认结构体布局。

### 15.7 进阶内容怎么取舍

以下内容重要，但不建议在初学阶段展开太深：

| 内容 | 什么时候学 |
|---|---|
| VLA 变长数组 | 理解栈风险后再看，嵌入式慎用 |
| 柔性数组成员 | 写高性能变长结构体时学习 |
| `restrict` | 做性能优化、DSP/SIMD 时学习 |
| C11 `_Atomic` | 写多线程或无锁代码时学习 |
| 编译器扩展 | 写底层、驱动、跨平台库时学习 |

本笔记保留这些概念的定位，不展开成繁重语法表。

---

## 16. 常见未定义行为与安全清单

未定义行为（UB）指 C 标准不规定后果的行为。程序可能崩溃，也可能“看起来正常”，但不能依赖。

### 16.1 高频 UB

| 问题 | 示例 | 说明 |
|---|---|---|
| 数组越界 | `a[5]` 访问 `int a[5]` | 最大下标是 4 |
| 空指针解引用 | `*NULL` | 无效地址访问 |
| 野指针 | 未初始化指针直接用 | 地址不可控 |
| 返回局部变量地址 | `return &x;` | 函数返回后 x 已销毁 |
| 修改字符串常量 | `char *p="hi"; p[0]='H';` | 字符串常量通常只读 |
| 有符号整数溢出 | `INT_MAX + 1` | UB |
| 移位越界 | `1 << 32` | 移位数不能超过位宽 |
| 格式化参数不匹配 | `printf("%d", 3.14);` | 类型不匹配 |
| 同一表达式多次修改 | `i = i++ + ++i;` | 求值顺序问题 |

### 16.2 安全编码清单

输入：

- `scanf` 检查返回值。
- 读字符串限制长度。
- 优先用 `fgets` + `sscanf` 处理复杂输入。

内存：

- `malloc` 后判空。
- 分配前检查乘法溢出。
- `free` 后不再使用该指针。
- 明确谁申请、谁释放。

字符串：

- 禁止 `gets()`。
- 避免裸 `strcpy`、`strcat`。
- 推荐 `snprintf`。
- 手动构造字符串时保证 `\0` 结尾。

指针：

- 初始化为 `NULL`。
- 解引用前确认有效。
- 不返回局部变量地址。
- 不访问已释放内存。

工程：

- 不需要外部访问的函数和全局变量加 `static`。
- 宏参数和宏体加括号。
- 位运算尽量用无符号类型。
- 硬件寄存器用 `volatile`。
- 资源清理路径保持一致。

### 16.3 最容易写错的点

| 易错点 | 错误写法 | 正确写法 |
|---|---|---|
| 判等 | `if (x = 5)` | `if (x == 5)` |
| 区间判断 | `0 < x < 10` | `0 < x && x < 10` |
| `scanf` | `scanf("%d", x)` | `scanf("%d", &x)` |
| 字符输入 | `scanf("%c", &ch)` | `scanf(" %c", &ch)` |
| 数组遍历 | `i <= n` | `i < n` |
| 数组参数长度 | 函数内 `sizeof(arr)` | 额外传 `len` |
| 浮点比较 | `a == b` | `fabs(a-b) < eps` |
| 字符串修改 | 修改字符串常量 | 用字符数组 |
| `realloc` | `p = realloc(p, n)` | 先存到 `tmp` |

---

## 17. 标准库常用函数速查

### 17.1 输入输出 `<stdio.h>`

```c
printf(), scanf();
fprintf(), fscanf();
puts(), putchar(), getchar();
fgets(), fputs();
fopen(), fclose();
fread(), fwrite();
perror();
```

### 17.2 字符串 `<string.h>`

```c
strlen();
strcmp();
strncmp();
strchr();
strstr();
memset();
memcpy();
memmove();
memcmp();
```

`memcpy` 要求源和目标不重叠；重叠时用 `memmove`。

### 17.3 字符处理 `<ctype.h>`

```c
isdigit();
isalpha();
isalnum();
isspace();
tolower();
toupper();
```

### 17.4 动态内存与工具 `<stdlib.h>`

```c
malloc();
calloc();
realloc();
free();
atoi();
strtol();
qsort();
bsearch();
```

需要可靠解析数字时，优先 `strtol`，少用 `atoi`，因为 `atoi` 不好判断错误。

### 17.5 数学 `<math.h>`

```c
fabs();
sqrt();
pow();
sin();
cos();
log();
exp();
```

链接数学库时部分环境需要：

```bash
gcc main.c -lm
```

---

## 18. 学习总结

C 语言真正难的地方，不是 `if`、`for`、`printf`，而是这些问题：

- 这段代码经过预处理和编译后实际是什么？
- 这个变量存在哪里，生命周期到什么时候？
- 这个指针指向的内存是否有效？
- 数组是否越界，字符串是否有 `\0`？
- 宏展开后是否仍然符合预期？
- 模块接口是否清楚，是否隐藏了不该暴露的细节？
- 在嵌入式场景下，寄存器、位操作、`volatile`、对齐和 ABI 是否考虑到了？

掌握 C 的关键不是背更多语法，而是形成三种习惯：

1. **从编译器角度看代码**：宏如何展开，符号如何链接。
2. **从内存角度看代码**：对象在哪里，谁拥有，什么时候失效。
3. **从工程角度看代码**：接口是否稳定，模块是否低耦合，错误路径是否可靠。

后续复习优先级建议：

```text
指针 / 数组 / 字符串
→ 结构体 / 内存布局
→ 函数接口 / 多文件工程
→ 宏 / 条件编译
→ 动态内存 / 错误处理
→ 嵌入式寄存器 / volatile / 回调
```
