# 47 编译时编程：constexpr 与 consteval

上一篇：[[46 文件读写：用 fstream 操作文件]]
下一篇：[[48 概念：给模板参数加约束]]

## 学习目标

完成本章后，你应当能够：

1. 说出把计算从运行期搬到编译期的动机，以及这样做能省下什么。
2. 写一个 `constexpr` 函数，并说明它为什么既能编译期求值、也能在运行期被调用。
3. 用 `constexpr` 变量和 `static_assert` 在编译期完成并检查计算。
4. 说出 `consteval` 与 `constexpr` 的区别，并判断一个函数该用哪一个。
5. 说出 `constinit` 保证什么、不保证什么。

## 1 为什么把计算搬到编译期

我们一直默认一件事：程序里的算术是在**运行期**做的。变量、循环、函数调用，都在程序跑起来之后执行。

但有一个不对称的事实：**程序编译一次，可能运行很多次**。服务器上常驻的服务、每天定时跑的数据处理脚本、被反复调用的库函数——编译那一次花掉的时间是"一次性成本"，而运行期花掉的时间是"每次运行都要付"的成本。凡是输入在编译期就确定、结果永远不变的计算，都可以提前到编译期做完，把每次运行的开销省掉。

编译期求值还有第二个好处：**错误可以提前到编译期暴露**。一个在运行期才会算出来的越界、溢出或类型不匹配，要等到程序跑到那一行才被发现；把同样的计算放到编译期，编译器在编译时就能报错。

这两种收益有一个共同的代价：编译时间会变长，而且这类计算只能使用编译期就能确定的数据。本章的三个关键字就是围绕"哪些东西可以在编译期求值"展开的。

## 2 `constexpr` 函数

把一个函数声明成 `constexpr`，含义是**这个函数允许在编译期求值**：

```cpp
constexpr int factorial(int n)
{
    return n <= 1 ? 1 : n * factorial(n - 1);
}
```

这里用递归实现阶乘（第 08 章的函数与递归）：$n! = n \times (n-1) \times \cdots \times 1$，基例是 $0! = 1! = 1$，所以 $5! = 120$。

### 2.1 "允许"这两个字很重要

`constexpr` 不等于"必须编译期算"。它真正的含义是：**当一个 `constexpr` 函数的实参本身是常量表达式时，编译器可以在编译期把结果算出来；实参来自运行期数据时，它照样能在运行期被调用。**同一份函数体同时服务这两种场景：

```cpp
constexpr int f5 = factorial(5);     // 实参是常量 → 编译期算出 120

int n = 6;                           // 普通变量，编译期不知道它的值
int f6 = factorial(n);               // 只能在运行期调用
```

这是 `constexpr` 最有价值的地方：写库的人不必为"编译期用"和"运行期用"各写一份实现。它和模板的情形很像——第 10 章的模板让同一份代码服务多种类型，`constexpr` 让同一份代码服务两个求值时机。

### 2.2 怎么确认它真的在编译期算完了

光看输出是看不出来的：编译期算出的 120 和运行期算出的 120 打印出来一模一样。有三种可靠的确认方式。

**第一种是 `static_assert`**（下一节细讲）——它的条件必须在编译期确定，能通过就说明右边的函数确实在编译期求值了。

**第二种是看反汇编。** `objdump -d -C` 会打印出程序的机器指令并还原符号名（`-C` 是 demangle，把修饰过的函数名还原成可读形式）。下面这个完整的小程序只做编译期求值：

```cpp
#include <iostream>

constexpr int factorial(int n)
{
    return n <= 1 ? 1 : n * factorial(n - 1);
}

int main()
{
    constexpr int result = factorial(5);
    std::cout << result << std::endl;
    return 0;
}
```

编译之后反汇编它，`main` 内的指令是这样的（只摘关键几行）：

```text
0000000140001490 <main>:
   14000149d:	c7 45 fc 78 00 00 00 	movl   $0x78,-0x4(%rbp)
   1400014ab:	ba 78 00 00 00       	mov    $0x78,%edx
   1400014b3:	e8 30 00 00 00       	call   1400014e8 <std::ostream::operator<<(int)>
```

`0x78` 就是十六进制的 120——编译器把结果直接写进了指令，**没有 `call factorial`**，运行期不需要再做任何计算。

例程 `factorial_constexpr` 同时包含编译期与运行期两种用法，反汇编它能看到两边的差别：

```text
   1400014a6:	c7 45 fc 78 00 00 00 	movl   $0x78,-0x4(%rbp)   # Demo A：120 直接写成常量
   14000150a:	c7 45 f8 06 00 00 00 	movl   $0x6,-0x8(%rbp)    # Demo B：n = 6
   140001516:	e8 b5 16 00 00 00    	call   140002bd0 <factorial(int)>   # Demo B：运行期真的调用
```

**第三种是看时间**：把同样的计算跑上几百万次，对比编译期版本与运行期版本的耗时。这种方式受优化等级影响很大，不如前两种可靠。

### 2.3 函数体里能写什么

C++11 刚引入 `constexpr` 时限制很严：函数体只能是一条 `return` 表达式。现在这些限制已经放开，`constexpr` 函数里可以有：

- 局部变量与赋值；
- `if`、`switch`、循环；
- 递归调用自己；
- 调用其他 `constexpr` 函数。

只有一条底线：**所有参与计算的量都必须是编译期能确定的**。一旦函数体里碰了运行期才有的东西（读文件、调 `std::random_device`、用输入的值），这次调用就不能在编译期完成——`constexpr` 函数在这种情况下会退回运行期执行；而在**必须**是常量的位置（`constexpr` 变量的初始化、`static_assert` 的条件），编译器会直接报错。

### 2.4 溢出边界

阶乘增长极快，用 `int` 装的时候要盯着边界：

$$\text{12!} = 479001600 \quad \text{（还在 int 范围内）}, \qquad \text{13!} = 6227020800 \quad \text{（已超出）}$$

本机的 `int` 上限是 $2147483647$，所以 `factorial(13)` 开始溢出。溢出是有符号整数的未定义行为，编译期求值也躲不开这个限制——它只是把错误提前到了编译期而已。这类"范围有限"的计算，正是 `static_assert` 最该守住的地方。

## 3 `constexpr` 变量与 `static_assert`

### 3.1 `constexpr` 变量

`constexpr` 写在变量前面，要求**用常量表达式初始化**：

```cpp
constexpr int f5 = factorial(5);        // 合法：右边是常量表达式
int n = 5;
constexpr int bad = factorial(n);       // 非法：n 不是常量表达式
```

第二行会编译失败，报错是：

```text
error: the value of 'n' is not usable in a constant expression
note: 'int n' is not const
```

`constexpr` 变量隐含 `const`：它的值不能再改。因为编译期就已经定下来了，所以它能被用在**要求写死常量**的地方，例如数组长度、`std::array` 的第二个模板参数、`case` 标签：

```cpp
std::array<int, factorial(4)> buffer {};     // 长度 24，编译期确定
```

### 3.2 `static_assert`：把检查放到编译期

`static_assert(条件, "说明")` 在编译期检查一个常量表达式，条件为假就直接**编译失败**。它不产生任何运行期代码：

```cpp
static_assert(factorial(5) == 120, "5! should be 120");
static_assert(factorial(0) == 1, "0! should be 1");
```

写错时的报错非常直接：

```text
error: static assertion failed: 5! should be 120
  • the comparison reduces to '(120 == 121)'
```

最后一行会告诉你编译器实际算出来的两个值，定位问题不用猜。`static_assert` 只能放在能写声明的地方，但它和 `constexpr` 一样，把"我心里认为这里应该是多少"变成了编译器负责执行的规则。

### 3.3 在编译期造一张表

`constexpr` 函数体里可以循环、可以操作 `std::array`，所以"在编译期算出一张查找表"是很自然的用法：

```cpp
constexpr std::array<int, 10> makeSquares()
{
    std::array<int, 10> result {};

    for (int i = 0; i < 10; ++i)
    {
        result[static_cast<std::size_t>(i)] = i * i;
    }

    return result;
}

constexpr std::array<int, 10> squares = makeSquares();   // 全局的编译期常量表

static_assert(squares[9] == 81, "squares[9] should be 81");
```

（节选自例程 `constexpr_table\constexpr_table.cpp`。）

命名空间作用域上的 `constexpr` 变量会在**静态初始化**阶段就位，内容直接存在可执行文件的只读数据段里，程序启动时不需要执行任何计算。用它的时候可以是运行期：例程里用普通变量 `int index = 6;` 去访问 `squares[index]`，得到 36，说明"编译期造数据"和"运行期用数据"是两件互不冲突的事。

查表法在需要反复计算同一组值的场景（三角函数近似、CRC 校验、颜色转换）里很实用：算一次、用无数次。

## 4 `consteval`：强制编译期求值

`constexpr` 是"允许"，`consteval` 是"必须"。用 `consteval` 声明的函数叫**立即函数**（immediate function），每一次调用都必须在编译期求值，没有运行期版本可退：

```cpp
consteval int square(int x)
{
    return x * x;
}

constexpr int limit = square(10);     // 合法：实参是常量
int n = 5;
std::cout << square(n);               // 非法：n 不是常量表达式
```

第二段代码的报错是：

```text
error: call to consteval function 'square(n)' is not a constant expression
error: the value of 'n' is not usable in a constant expression
note: 'int n' is not const
```

第一种错误（`call to consteval function ... is not a constant expression`）只在 `consteval` 上出现，看到它就能确定问题是"这个调用拿不到编译期可用的实参"。

`consteval` 的用途是**把"只能编译期做的事"写进接口**。一个典型的例子是编译期的字符串检查、编译期的单位换算表构造——这些函数的返回值必须参与后续的编译期计算，如果允许它在运行期被调用，那类代码就会在别处报出更难懂的错。用 `consteval` 声明，误用的代价从"错误发生在很远的地方"变成"错误就在这一行"。

## 5 `constinit`：只保证静态初始化

`constinit` 管的是另一件事：它要求变量在**程序启动之前**（静态初始化阶段）就完成初始化。

```cpp
constinit int counter = 100;      // 静态初始化，但它不是常量
```

它的两个要点：

- **它不表示变量是常量。** `counter` 可以被修改，例程里 `counter += 1;` 之后打印出 101。这一点和 `constexpr` 变量完全相反。
- **它要求初始化表达式是常量表达式。** 写成运行期才能确定的值会编译失败：

```text
error: 'constinit' variable 'counter' does not have a constant initializer
error: call to non-'constexpr' function 'std::random_device::result_type std::random_device::operator()()'
```

`constinit` 解决的是"静态初始化顺序"问题：多个全局对象之间的初始化顺序在跨编译单元时没有保证，一个全局对象用另一个还没初始化好的全局对象来初始化，就会读到无意义的值。给它加 `constinit`，编译器会强制要求它的初始化不依赖任何运行期逻辑，从根上排除这类问题。这一点本章只需要知道语义边界：**`constinit` 是"初始化时机"的约束，与"能不能改"无关。**

## 6 三者对照与选择

| 关键字 | 用在哪 | 要求 | 值能不能改 | 典型用途 |
| --- | --- | --- | --- | --- |
| `constexpr` 函数 | 函数 | 允许编译期求值，也可以在运行期调用 | —— | 既能编译期用、也能运行期用的通用计算（阶乘、表格构造） |
| `constexpr` 变量 | 变量 | 必须用常量表达式初始化 | 不能（隐含 `const`） | 编译期常量、表格、用作数组长度 |
| `consteval` | 函数 | 每次调用都必须在编译期求值 | —— | 只应存在于编译期的计算，把误用挡在编译期 |
| `constinit` | 变量 | 必须静态初始化（初始化是常量表达式） | 能改 | 全局状态、需要在启动前就绪且运行期会变化的变量 |

选择思路很直接：

1. 需要一个"编译期就知道、之后不变"的值 → `constexpr` 变量；
2. 需要一个既能编译期求值、又能在运行期用运行期数据调用的函数 → `constexpr` 函数；
3. 需要一个"只能在编译期用"的函数 → `consteval`；
4. 需要一个"启动前就初始化好、但之后会被修改"的全局变量 → `constinit`。

还有一条工程上的提醒：把计算搬到编译期，代价是编译时间变长、可调试性下降（编译期算出来的值在调试器里没有调用栈可看）。真正值得搬的是那些"结果固定、调用频繁、开销可见"的计算，而不是把所有函数都标上 `constexpr`。

## 7 动手实验

例程在 `E:\CPP_Code\CppFromScratch\ch47_constexpr\` 下，三个程序各占一个文件夹。

### 7.1 实验一：`constexpr` 函数的两种用法（`factorial_constexpr`）

```text
cd "E:/CPP_Code/CppFromScratch/ch47_constexpr/factorial_constexpr"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g factorial_constexpr.cpp -o factorial_constexpr.exe
./factorial_constexpr.exe
```

**预期输出**：

```text
=== Demo A: evaluated at compile time ===
factorial(5) = 120
=== Demo B: same function, called at run time ===
factorial(6) = 720
=== Demo C: nested constant expressions ===
factorial(factorial(3)) = 720
=== Demo D: use it where a constant is required ===
buffer.size() = 24
```

**验收标准**：输出与上面逐字符一致；`-Wall` 无警告；Demo C 的 `factorial(factorial(3)) = factorial(6) = 720` 能自己推出来；Demo D 的 `buffer.size()` 是 24，因为 `factorial(4) = 24` 被用作 `std::array` 的长度。

**对照实验（本实验的重点）**：反汇编这个可执行文件，观察编译期结果被直接写进指令：

```text
"E:/msys64/ucrt64/bin/objdump.exe" -d -C factorial_constexpr.exe
```

在输出的 `<main>:` 段里找 `0x78`（十六进制的 120）和 `call ... <factorial(int)>`：前者是 Demo A 编译期算好的结果，后者是 Demo B 在运行期真的调用了函数。同一个 `factorial` 函数，两种求值时机在机器指令层面留下了不同的痕迹。

**改值实验**：把 `constexpr int f5 = factorial(5);` 换成 `factorial(3)`，并同步把 `static_assert` 里的 `factorial(5) == 120` 改成 `factorial(3) == 6`，重新编译运行。可以预判 Demo A 输出 6，反汇编里那个常量变成 `0x6`。改回去。

**边界验证**：把 `static_assert(factorial(5) == 120, "5! should be 120");` 里的 120 改成 121，重新编译，会看到：

```text
error: static assertion failed: 5! should be 120
  • the comparison reduces to '(120 == 121)'
```

编译器把两边算出来的值直接告诉了我们。注意这是**编译错误**，程序根本生成不出来——这正是把检查放在编译期的价值。看完改回 120。

### 7.2 实验二：编译期造表（`constexpr_table`）

```text
cd "E:/CPP_Code/CppFromScratch/ch47_constexpr/constexpr_table"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g constexpr_table.cpp -o constexpr_table.exe
./constexpr_table.exe
```

**预期输出**（`squares` 那一行末尾有一个空格）：

```text
=== Demo A: a table built at compile time ===
squares: 0 1 4 9 16 25 36 49 64 81 
=== Demo B: fib(10) verified by static_assert ===
fib(10) = 55
=== Demo C: index a compile-time table at run time ===
squares[6] = 36
```

**验收标准**：输出与上面一致；能说出 `squares` 这张表里的数字是在什么时候算出来的（答案：编译期，程序启动时不需要计算）。

**改值实验**：把 `static_assert(squares[9] == 81, ...)` 改成 `squares[9] == 82`，重新编译。可以预判会失败，并且报错信息里同样会给出`the comparison reduces to` 的实际值对照——说明这个断言是真的在编译期读那张表检查的，不是走过场。改回去。

### 7.3 实验三：`consteval` 与 `constinit`（`consteval_constinit`）

```text
cd "E:/CPP_Code/CppFromScratch/ch47_constexpr/consteval_constinit"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g consteval_constinit.cpp -o consteval_constinit.exe
./consteval_constinit.exe
```

**预期输出**：

```text
=== Demo A: consteval is evaluated at compile time ===
square(7) = 49
square(9) = 81
=== Demo B: constinit is only about initialization ===
counter = 100
counter after += 1 = 101
=== Demo C: constexpr variables are read-only ===
limit = 100
```

**验收标准**：输出与上面逐字符一致；能回答"为什么 `counter` 能加 1，而 `limit` 不能"。

**边界验证**：在 `main` 里加两行 `int n = 5;` 和 `std::cout << square(n) << std::endl;`，重新编译，会看到：

```text
error: call to consteval function 'square(n)' is not a constant expression
error: the value of 'n' is not usable in a constant expression
note: 'int n' is not const
```

如果把 `square` 前面的 `consteval` 换成 `constexpr`，同样的调用就能编译通过并且在运行期执行——这就是两个关键字的全部差别。看完把这两行删掉。

**改值实验**：把 `constinit int counter = 100;` 改成 `constinit int counter = std::random_device {}();`（并在文件开头加上 `#include <random>`），重新编译会看到：

```text
error: 'constinit' variable 'counter' does not have a constant initializer
```

`constinit` 要求初始化必须在启动前完成，而 `random_device` 只能在运行期取值，两者直接冲突。看完还原。

## 8 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| `error: the value of 'n' is not usable in a constant expression` + `note: 'int n' is not const` | 用普通变量去初始化 `constexpr` 变量：`constexpr int r = factorial(n);` | 把实参改成常量表达式，或者去掉变量的 `constexpr`（改回运行期求值） |
| `error: call to consteval function 'square(n)' is not a constant expression` | 用运行期的值去调用 `consteval` 函数 | 立即函数只能吃常量：要么把实参改成常量表达式，要么把这个函数声明成 `constexpr`（允许两用） |
| `error: static assertion failed: 5! should be 120` + `• the comparison reduces to '(120 == 121)'` | `static_assert` 的条件不成立 | 按报错里给的实际值定位；注意这是编译错误，程序不会生成 |
| `error: 'constinit' variable 'counter' does not have a constant initializer` + `error: call to non-'constexpr' function ...` | `constinit` 变量的初值来自运行期（如 `std::random_device`） | `constinit` 只要求"启动前完成初始化"，初值必须是常量表达式；要运行期取值就去掉 `constinit` |
| `error: 'constexpr' function ... called in a constant expression` / 想用 `constexpr` 变量当数组长度却报错 | 该函数体里有运行期操作（读文件、取随机数、访问非 const 数据） | 常量表达式里只能用编译期可确定的量；把这类计算留在运行期 |
| `error: assignment of read-only variable 'limit'` | 试图修改 `constexpr` 变量 | `constexpr` 变量隐含 `const`，不能改；需要"启动前初始化但之后可改"就用 `constinit` |
| 程序输出与预期一致，但反汇编里仍有 `call factorial` | 程序里同时存在运行期调用（例程的 Demo B 就是），那一处必然要调用 | 只有编译期求值的那几处会变成常量；对照反汇编时按行号对应到具体语句 |
| 阶乘结果莫名其妙变成负数 | `int` 溢出：13! 已超出 `int` 范围，溢出是未定义行为 | 用 `static_assert` 守住输入范围，或改用 `long long` / `std::uint64_t`（仍要注意上限） |
| 编译时间明显变长 | 把大量计算搬到了编译期，而且可能在编译期被反复求值 | 只搬"结果固定、调用频繁"的计算；必要时用 `constexpr` 变量把结果缓存一次 |

## 9 本章验收

1. 三个例程都编译通过、`-Wall` 无警告，输出与 7.1–7.3 节逐字符一致。
2. 能在 `objdump -d -C` 的输出里指出 Demo A 的 `0x78` 与 Demo B 的 `call factorial`，并解释这两处的差别。
3. 能回答：`constexpr` 函数的"允许"是什么意思？`constexpr` 变量为什么不能改？`consteval` 和 `constexpr` 的差别是什么？`constinit` 保证什么、不保证什么？
4. 完成过 7.1 的 `static_assert` 边界实验，能读懂 `the comparison reduces to '(120 == 121)'` 这行提示。
5. 能说出把计算搬到编译期的两个好处与两个代价。
