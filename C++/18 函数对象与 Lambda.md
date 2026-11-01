# 18 函数对象与 Lambda

上一篇：[[17 类模板、概念与编译时编程]]
下一篇：[[19 并发：线程、锁与原子操作]]

## 学习目标

完成本章后，你应当能够：

1. 说出函数对象是什么，在自己的结构体里重载函数调用运算符 `operator()`，让对象可以像函数一样被调用，并说明 `operator()` 后面的 `const` 和构造函数的 `explicit` 各起什么作用。
2. 把函数对象或 lambda 作为谓词传给 `std::ranges::find_if`，并在使用返回的迭代器前检查它是否到达末尾。
3. 说出 lambda 表达式由哪三个部分组成，每一部分对应函数对象的什么成分，以及 lambda 的类型为什么只能用 `auto` 接住。
4. 按值捕获和按引用捕获外部变量并说出两者在"何时看到变化"上的差别，会在捕获列表里创建只属于这个 lambda 的变量，会用 `mutable` 修改自己的副本。
5. 依据"只在一个地方用一次"还是"反复使用、表达可复用概念"，在 lambda 和具名函数对象之间做出选择。

## 1 函数缺了哪一样东西

第 04 章讲过函数的作用：把一段语句起个名字，需要时按名字调用。函数解决了"代码重复"，但它有一个天生的短板：**函数没有状态**。

看一个具体需求：判断一个数能否被另一个数整除。这个判断写成函数很自然：

```cpp
bool is_divisible(int dividend, int divisor)
{
    return dividend % divisor == 0;
}
```

用起来是 `is_divisible(55, 10)`。问题是每次调用都要把两个参数都带上。如果这个判断要交给标准库算法去反复调用——例如"在一个向量里找出第一个能被 10 整除的元素"——算法只会给被调用的东西传一个参数（当前元素），不会帮你传第二个。这时你只有两条路：

- 把除数写死成另一个专门的函数 `is_divisible_by_ten(int)`，每换一个除数就多写一个函数；
- 把除数放到全局变量里，让函数去读它。

前者无法穷举，后者引入了谁都可能改的全局状态。**缺的东西就是"把除数这个参数提前绑定到一个具体的调用者身上"**，让这个调用者既像函数一样可以被调用，又自带一份属于它自己的数据。

这正是函数对象要解决的问题。

## 2 定义函数对象

回顾第 13 章的运算符重载：运算符本质上就是函数，写 `a + b` 是在调用 `operator+(a, b)`。在可以重载的运算符里有一个特别的——**函数调用运算符 `operator()`**，也就是那对括号。一个类型只要重载了它，这个类型的对象就能写成 `对象(实参)` 的形式，看起来和调用函数完全一样。

标准里的说法很直接：**函数对象就是任何定义了函数调用运算符的对象**。

### 2.1 `operator()` 的写法

例程 `E:\CPP_Code\CppFromScratch\ch38_function_objects\divisible_object\divisible_object.cpp` 里的类型：

```cpp
struct is_divisible
{
    explicit is_divisible(int new_divisor) : divisor(new_divisor)
    {
    }

    bool operator()(int dividend) const
    {
        return dividend % divisor == 0;
    }

    int divisor;
};
```

逐部分说明：

- **`operator()` 也是一个成员函数**，只是它的名字固定为那对括号。写成成员函数意味着调用时隐藏的第一个实参是对象自己（第 11 章讲的 `this`），所以 `obj(55)` 里的 `55` 对应的是括号里的参数 `dividend`。
- **参数列表 `(int dividend)` 就是"每次调用要传进来的输入"**，和普通函数的参数列表含义相同，写法也相同。返回值这里定义为 `bool`：判断的结果只有真、假两种。
- **结尾的 `const`** 表示这个调用不会修改对象的成员。这不是装饰：没有它，`const is_divisible` 对象就不能被调用（编译器会报 `error: no match for call to '(const is_divisible) (int)'`），而且一个"只读不写"的调用者本来就应该标成 `const`。
- **构造函数写成 `explicit`**：除数必须在创建对象时明确给出，写 `is_divisible d = 10;` 这种隐式转换会直接报错 `error: conversion from 'int' to non-scalar type 'is_divisible' requested`。让对象的创建意图清清楚楚，比让编译器偷偷转换要好。
- **成员初始化列表 `: divisor(new_divisor)`** 在第 12 章讲过：它在进入构造函数体之前就给成员赋值，所以函数体本身是空的。

### 2.2 状态属于对象

数据成员 `divisor` 是这个函数对象的状态。和全局变量相比，它的关键区别是：**状态属于某一个对象，而不是属于整个程序**。同一个类型可以造出任意多个对象，各带各的除数，彼此互不影响：

```cpp
is_divisible is_divisible_by_ten(10);
is_divisible is_divisible_by_three(3);
```

这两个对象的类型完全相同，但被调用时的行为不同，因为各自内部存着不同的 `divisor`。这也说明函数对象是普通的对象：可以复制、可以作为参数传进函数、可以放进容器、可以在运行时构造（例如从配置里读出除数再构造）。

## 3 像函数一样调用对象

创建对象之后，调用它和调用函数在语法上没有区别。例程的第一段：

```cpp
is_divisible is_divisible_by_ten(10);

std::cout << "is_divisible_by_ten(55) -> " << is_divisible_by_ten(55) << std::endl;
std::cout << "is_divisible_by_ten(50) -> " << is_divisible_by_ten(50) << std::endl;
```

输出：

```text
=== Demo A: an object you can call like a function ===
is_divisible_by_ten(55) -> 0
is_divisible_by_ten(50) -> 1
```

`is_divisible_by_ten(55)` 这一串里，`55` 被送进了 `operator()` 的参数 `dividend`，成员 `divisor`（值为 10）自动参与运算：`55 % 10` 是 5，不等于 0，所以返回 `false`；`50 % 10` 是 0，返回 `true`。`bool` 值交给 `std::cout` 打印出来就是 `0` 和 `1`。

换一个状态就是换一个对象，代码一个字不用改：

```text
=== Demo B: the state lives inside the object ===
is_divisible_by_three(55) -> 0
is_divisible_by_three(51) -> 1
```

`55 % 3` 是 1，`51 % 3` 是 0，与输出一致。同一个对象也可以被反复调用，每次调用各自独立：

```text
=== Demo C: the same object can be called many times ===
is_divisible_by_ten(20) -> 1
is_divisible_by_ten(21) -> 0
```

## 4 把函数对象交给标准库算法

只在 `main` 里手动调用，函数对象的价值还看不出来；真正的用途是把这类"能回答真假的调用者"交给算法，让算法去对一堆元素反复提问。

### 4.1 谓词

第 06 章用过标准库算法：它们接收一对迭代器表示要处理的元素范围。有一部分算法（查找、计数、判断）还需要一个额外的参数，用来回答"这个元素符不符合条件"，这个参数的标准叫法是**谓词**（predicate）：给进去一个元素，它回一个能当真假用的结果。

标准库不关心谓词具体是什么东西，只要求它能写成 `谓词(元素)` 这种调用形式。普通函数可以，函数指针可以，重载了 `operator()` 的对象也可以——因为 `对象(元素)` 本来就是合法调用。这就是为什么函数对象会成为算法最常用的搭档。

### 4.2 `find_if` 的用法

例程 `ch38_function_objects\find_if_object\find_if_object.cpp` 在一个整数向量里查找第一个能被给定除数整除的元素：

```cpp
std::vector<int> my_vector {41, 20, 84, 94, 2, 3};

auto it = std::ranges::find_if(my_vector, is_divisible(10));

if (it != my_vector.end())
{
    std::cout << "first element divisible by 10: " << *it
              << " (index " << std::distance(my_vector.begin(), it) << ")" << std::endl;
}
else
{
    std::cout << "no element divisible by 10" << std::endl;
}
```

四件事值得注意：

1. **`std::ranges::find_if` 在 `<algorithm>` 里**，接收一个范围（这里直接给容器）和一个谓词，返回**指向第一个满足条件元素的迭代器**。它出现在 C++20，编译时要加 `-std=c++20`；若编译器的默认标准低于 C++20，不加 `-std=c++20` 会报 `error: 'std::ranges' has not been declared`。
2. **谓词写成了 `is_divisible(10)`，是一个临时对象**。不需要为它起名字——构造、传给算法、算法用完销毁，一步完成。这正是第 2 节讲的"提前把除数绑定到调用者身上"的用法。
3. **返回的迭代器必须先与 `end()` 比较**。一个都没有满足条件时，返回的就是末尾迭代器，解引用它是未定义行为（可能读到越界数据，也可能直接崩溃）。例程的第三段专门演示了这种情况：向量里没有 11 的倍数，于是走 `else` 分支。
4. **`std::distance` 给出从起点数起的位置**，这里配合输出能把"第几个元素"一起标出来。

运行结果：

```text
=== Demo A: find the first element divisible by 10 ===
first element divisible by 10: 20 (index 1)
=== Demo B: reuse the same type with another divisor ===
first element divisible by 7: 84 (index 2)
=== Demo C: asking for something that is not there ===
no element divisible by 11: it == end()
```

第二段把除数换成 7 再查一遍：41、20 都不满足，84 满足，所以下标是 2。**算法那一行代码完全没变，变的只是传进去的那个对象**——这就是"条件靠对象携带"带来的灵活。

## 5 与普通函数、函数指针的对比

同一件事也可以用普通函数做：

```cpp
bool is_divisible_by_ten(int dividend) { return dividend % 10 == 0; }
```

它的优点是短。但一旦条件需要参数（除数、阈值、目标值……），普通函数就只能靠全局变量把参数传进去，而全局变量是所有代码都能改的，条件和数据就分家了。函数指针能指向不同的函数，却同样**只带得动"函数在哪"，带不动数据**——指针里没有地方放那个除数。

函数对象把两样东西捆成了一个值：

| 方案 | 能携带数据 | 能作为参数传递 | 调用时的形式 |
| --- | --- | --- | --- |
| 普通函数 | 不能（只能靠全局变量） | 可以用函数指针传 | `f(x)` |
| 带状态的函数对象 | 能（数据成员） | 能（对象直接传） | `obj(x)` |

对标准库还有一层额外的意义：函数对象的 `operator()` 是编译期就能确定的函数，编译器通常可以直接把它内联展开，不会因为"通过指针调用"而多一次间接跳转。这也是标准库的风格偏好——大量算法和设施接受的都是"可调用对象"，而不是函数指针。

## 6 样板代码的负担

函数对象好用，但每写一个条件都要付出一整套代码：定义一个类型、加数据成员、写构造函数、写 `operator()`，然后用一次。上面那个 `is_divisible` 一共十几行，用在算法里只有一行。

这些代码是必要的吗？从语言的角度当然可以更短——一个"只在一个地方用一次的条件"，本来不需要名字、也不需要在外层可见。C++11 起提供了专门做这件事的语法：**就地写出的匿名函数对象**，也就是 lambda 表达式。下一节就用它把上面那整套定义压缩成三行。

## 7 从样板代码到 lambda

为了让一个对象"能被调用并携带一个除数"，第 2 节写了这样一个类型：

```cpp
struct is_divisible
{
    explicit is_divisible(int new_divisor) : divisor(new_divisor)
    {
    }

    bool operator()(int dividend) const
    {
        return dividend % divisor == 0;
    }

    int divisor;
};
```

十行代码换来一个"能被调用并带着状态"的东西。它确实解决了问题——把状态提前绑定到调用者身上、然后交给算法反复调用。但用得越多，越能看出其中的浪费：这段类型定义只在一个地方用了一次，它的名字在外层可见，它的成员函数在语义上跟使用点隔了很远。**如果用一次的条件都要写一整套类型，样板代码就压过了逻辑本身。**

C++11 起提供了直接支持：**lambda 表达式**可以在使用它的位置就地写出来，不需要类型名、不需要结构体或类，还能把作用域里的变量带进这个匿名的函数对象里。也就是说，函数对象的能力全部保留，写法缩短到一行。

## 8 lambda 的三个组成部分

把第 2 节的 `is_divisible` 换成 lambda，得到 `ch39_lambdas\lambda_divisible\lambda_divisible.cpp` 里的这一行：

```cpp
auto is_divisible_by_ten = [divisor = 10](int dividend)
{
    return dividend % divisor == 0;
};
```

它由三个部分组成，顺序固定：

| 部分 | 位置 | 作用 | 对应的函数对象成分 |
| --- | --- | --- | --- |
| 捕获列表 | `[divisor = 10]` | 把外部变量或新建的变量带进这个函数对象 | 数据成员 + 构造函数的初始化 |
| 参数列表 | `(int dividend)` | 每次调用时要传进来的输入 | `operator()` 的参数列表 |
| 函数体 | `{ return ...; }` | 真正执行的语句 | `operator()` 的函数体 |

逐项对照第 2 节的代码：

- **捕获列表**是 lambda 独有的部分，其它函数都没有。`divisor = 10` 的意思是"在这个函数对象里新建一个成员 `divisor`，初值取 10"，所以不必再写构造函数和成员声明，也不需要写 `int`——类型由初值 10 推出来。
- **参数列表**和普通函数、和 `operator()` 的参数列表完全一致。这里写 `(int dividend)`，表示每次调用要提供一个待检查的数。
- **函数体**就是原来 `operator()` 里的那条 `return`，一个字都没改。返回值类型同样不写：`return` 后面的表达式类型就是 lambda 的返回类型（这里推成 `bool`）。
- **末尾的分号不能少**。lambda 表达式本身是表达式，整句仍然是一条语句。

第 2 节那个十行的类型定义、构造函数、`operator()`，在功能等价的前提下被这三行取代了。

## 9 捕获列表：lambda 的状态从哪里来

捕获列表是 lambda 的特征所在，它决定了这个函数对象拥有什么状态、这些状态是副本还是别的变量的别名。有三种常用写法。

### 9.1 按值捕获：留下一份快照

捕获列表里只写变量名，就是**按值捕获**：lambda 内部保存这个名字的**一份副本**，副本在 lambda 构造的那一刻取定，之后外面的变量怎么变都与它无关。

例程 `ch39_lambdas\lambda_capture\lambda_capture.cpp` 用两个 lambda 做对照：

```cpp
int threshold = 10;

auto by_value = [threshold](int value)
{
    return value >= threshold;
};

auto by_reference = [&threshold](int value)
{
    return value >= threshold;
};

threshold = 100;
```

输出：

```text
=== Demo A: capture by value takes a snapshot ===
threshold at definition time = 10
threshold now = 100
by_value(50) -> 1
by_reference(50) -> 0
```

同一个参数 50，两个 lambda 给出相反的结果：

- `by_value` 用的是捕获时的快照（10），`50 >= 10` 成立，返回 1；
- `by_reference` 里存的是那个变量的别名，调用时读到的是新值（100），`50 >= 100` 不成立，返回 0。

**按值捕获的语义就是"定义时定格"**：想让 lambda 的行为随后续修改而变，就必须用引用；想让它的行为固定下来（也避免外部乱改影响它），就用值。

### 9.2 按引用捕获：共享同一个变量

在变量名前加 `&` 是按引用捕获。它不复制数据，lambda 内部用的就是外面那个变量本身，因此有两个后果：

- 外部改了值，下次调用立刻能看到（上面实验已验证）；
- 外面的变量一旦销毁，lambda 里存的就是一个失效的引用，再调用它属于未定义行为。

所以按引用捕获适合"在同一个作用域内临时用一下"的场合，比如马上传给算法、调用完就丢掉的 lambda。把按引用捕获的 lambda 存起来、离开原来的作用域之后再调用，是很容易踩的坑。

### 9.3 在捕获列表里新建变量

捕获列表里可以像初始化变量一样写 `名字 = 初值`，这样就给这个匿名函数对象加了一个**只属于它自己**的成员：

```cpp
auto is_divisible_by_ten = [divisor = 10](int dividend)
{
    return dividend % divisor == 0;
};
```

好处是这个名字不会跑到外层作用域去，也不会和外面的同名变量互相干扰。这种写法既能用字面量初始化（`divisor = 10`），也能用外层变量初始化（`divisor = candidate`，相当于给外层变量拍一张快照并另起一个名字），因此它同时替代了第 2 节"数据成员 + 构造函数"两件事。

### 9.4 `mutable`：允许修改自己那份副本

按值捕获来的成员在 lambda 内部是只读的。如果想让它能被修改，就在参数列表后面加 `mutable`：

```cpp
int counter = 0;

auto count_calls = [counter]() mutable
{
    ++counter;
    return counter;
};
```

输出：

```text
=== Demo C: mutable lets the lambda change its own copy ===
calls so far: 1
calls so far: 2
calls so far: 3
counter outside is still 0
```

三次调用各自在**同一个副本**上累加，所以打印出 1、2、3；而外面的 `counter` 一直是 0——被改的从来只是 lambda 自己那份。这说明 lambda 确实像函数对象一样拥有独立的状态：状态活在对象里，每次调用都在同一个对象上进行。

## 10 匿名，但仍然有类型

lambda 的类型由编译器生成，是一个**没有名字的类类型**——这也是它被称为"匿名函数对象"的原因。由此带来几条实际影响：

- 日常用 `auto` 接住（也可用 `decltype` 命名；无捕获的 lambda 还能转成函数指针），也可以把它当作模板参数传出去。类型名写不出来，也不必写。需要把不同的 lambda 存进类型统一的容器或接口时，再引入类型擦除（`std::function`）。
- 两个字面完全一样的 lambda 也是**不同的类型**，所以 `decltype(f)` 那一套名字只有编译器自己知道，它们之间不能互相赋值。
- 因为它本质上就是一个类，前面讲过的规则都适用：捕获的变量就是它的数据成员，函数体就是 `operator()` 的函数体，参数和返回值规则与普通函数相同。

理解这一点之后，"lambda 是语法糖"这句话就具体了：它糖化出来的正是第 2 节那个手写的函数对象。

## 11 把 lambda 交给算法

谓词的位置和本章第 4 节完全一样——算法只要求能写成 `谓词(元素)` 的形式。例程 `lambda_divisible\lambda_divisible.cpp` 把 `find_if` 的第二个参数换成了 lambda：

```cpp
auto it = std::ranges::find_if(my_vector, is_divisible_by_ten);
```

输出：

```text
vector: 41 20 84 94 2 3
=== Demo A: call the lambda directly ===
is_divisible_by_ten(55) -> 0
is_divisible_by_ten(50) -> 1
=== Demo B: pass the lambda to std::ranges::find_if ===
first element divisible by 10: 20
```

结果与本章第 4 节用函数对象得到的完全一致（20 是第一个能被 10 整除的元素），而且 lambda 也是个普通对象，直接调用它的写法和调用函数对象毫无区别（`Demo A` 两行）。

条件写在算法调用的同一行，读代码时不需要在文件里跳来跳去地找"那个谓词到底是什么"——这是 lambda 在可读性上的直接收益。例程 `lambda_vs_functor\lambda_vs_functor.cpp` 把两种写法并排放在一起做验证：

```text
vector: 41 20 84 94 2 3
=== Demo A: a hand written function object ===
struct is_divisible: first element divisible by 7: 84
=== Demo B: the same condition as a lambda ===
lambda: first element divisible by 7: 84
=== Demo C: both give the same answer ===
results match: 1
```

两条查找返回同一个迭代器（`results match: 1`），因为编译器为 lambda 生成的那个匿名类，和你手写的函数对象做的是同一件事。

## 12 什么时候用 lambda，什么时候用具名类型

两者的能力对等，选择取决于这个条件会被怎么用：

- **只在一个地方用一次**（典型场景就是紧跟着传给某个算法）：用 lambda。条件和使用点挨在一起，不需要起名字，也不会污染外层作用域。
- **要反复使用多次、要起名字表达意图、或者需要明确写出类型**：用第 2 节那样的具名类型或普通函数。一个"能被 10 整除"的规则如果是整个模块共用的概念，给它一个名字比在每个调用点重复写一遍 lambda 更清楚。
- **需要在调用之间保持状态**：两种都可以（lambda 靠捕获或 `mutable`），但如果状态的含义比较复杂，写成具名类型更容易读、也便于加注释和别的成员函数。

一句话概括：lambda 让"一次性条件"不再需要付出定义类型的代价，而具名类型仍然是表达"可复用概念"的工具。

## 13 动手实验

### 13.1 实验一：定义并调用函数对象

例程在 `E:\CPP_Code\CppFromScratch\ch38_function_objects\` 下，两个程序各占一个文件夹，都是单文件自包含。`divisible_object\divisible_object.cpp` 里定义了 `struct is_divisible`，`main` 创建两个不同除数的对象并分别调用。

```text
cd "E:\CPP_Code\CppFromScratch\ch38_function_objects\divisible_object"
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g divisible_object.cpp -o divisible_object.exe
./divisible_object.exe
```

**预期输出**：

```text
=== Demo A: an object you can call like a function ===
is_divisible_by_ten(55) -> 0
is_divisible_by_ten(50) -> 1
=== Demo B: the state lives inside the object ===
is_divisible_by_three(55) -> 0
is_divisible_by_three(51) -> 1
=== Demo C: the same object can be called many times ===
is_divisible_by_ten(20) -> 1
is_divisible_by_ten(21) -> 0
```

**验收标准**：输出逐字符与上面一致；`-Wall` 无警告；能指着 `bool operator()(int dividend) const` 这一行说明哪部分是运算符名、哪部分是参数列表、哪部分是返回值类型。

**改值实验**：把 `is_divisible is_divisible_by_ten(10);` 里的 `10` 改成 `5`，重新编译运行。预期 `Demo A` 两行都变成 `-> 1`（55 和 50 都能被 5 整除），`Demo B` 两行不变，`Demo C` 的 `(20) -> 1` 不变、`(21) -> 0` 不变（21 除以 5 余 1）。改动只影响那一个对象的判断结果。

### 13.2 实验二：把函数对象作为谓词传给算法

`find_if_object\find_if_object.cpp` 用 `std::ranges::find_if` 在 `{41, 20, 84, 94, 2, 3}` 中查找，并检查返回的迭代器。

```text
cd "E:\CPP_Code\CppFromScratch\ch38_function_objects\find_if_object"
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g find_if_object.cpp -o find_if_object.exe
./find_if_object.exe
```

**预期输出**：

```text
vector: 41 20 84 94 2 3
=== Demo A: find the first element divisible by 10 ===
first element divisible by 10: 20 (index 1)
=== Demo B: reuse the same type with another divisor ===
first element divisible by 7: 84 (index 2)
=== Demo C: asking for something that is not there ===
no element divisible by 11: it == end()
```

**验收标准**：输出与上面一致；`-Wall` 无警告；能说明为什么 Demo C 走的是 `else` 分支，以及如果不判断 `it != my_vector.end()` 会发生什么。

**改值实验**：把 Demo A 里的 `is_divisible(10)` 改成 `is_divisible(11)`，重新编译运行。预期 Demo A 段不再打印数值，而是输出 `no element divisible by 10`——因为 `{41, 20, 84, 94, 2, 3}` 里没有 11 的倍数，`find_if` 返回了末尾迭代器。看完改回 `10`。

### 13.3 实验三：用 lambda 替换函数对象

例程在 `E:\CPP_Code\CppFromScratch\ch39_lambdas\` 下，三个程序各占一个文件夹，都是单文件自包含。`lambda_divisible\lambda_divisible.cpp` 用 `[divisor = 10](int dividend)` 这个 lambda 完成本章第 2 节函数对象的全部工作：直接调用两次，再作为谓词传给 `std::ranges::find_if`。

```text
cd "E:\CPP_Code\CppFromScratch\ch39_lambdas\lambda_divisible"
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g lambda_divisible.cpp -o lambda_divisible.exe
./lambda_divisible.exe
```

**预期输出**：

```text
vector: 41 20 84 94 2 3
=== Demo A: call the lambda directly ===
is_divisible_by_ten(55) -> 0
is_divisible_by_ten(50) -> 1
=== Demo B: pass the lambda to std::ranges::find_if ===
first element divisible by 10: 20
```

**验收标准**：输出逐字符与上面一致；`-Wall` 无警告；能指着 `[divisor = 10](int dividend) { return dividend % divisor == 0; }` 分别说出捕获列表、参数列表、函数体各是哪一段，以及它替换掉了本章第 2 节的哪些代码。

**改值实验**：把捕获列表里的 `divisor = 10` 改成 `divisor = 7`，重新编译运行。预期 `Demo A` 两行都变成 `-> 0`（55 除以 7 余 6，50 除以 7 余 1），`Demo B` 打印出 `first element divisible by 10: 84`——84 是向量里第一个 7 的倍数，其中 `divisible by 10` 只是写死在输出字符串里的文字，不会跟着变。看完改回 `10`。

### 13.4 实验四：lambda 与函数对象结果一致

`lambda_vs_functor\lambda_vs_functor.cpp` 对同一个条件写出两种实现，再用 `std::ranges::find_if` 各查一次，最后比较两个迭代器是否相同。

```text
cd "E:\CPP_Code\CppFromScratch\ch39_lambdas\lambda_vs_functor"
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g lambda_vs_functor.cpp -o lambda_vs_functor.exe
./lambda_vs_functor.exe
```

**预期输出**：

```text
vector: 41 20 84 94 2 3
=== Demo A: a hand written function object ===
struct is_divisible: first element divisible by 7: 84
=== Demo B: the same condition as a lambda ===
lambda: first element divisible by 7: 84
=== Demo C: both give the same answer ===
results match: 1
```

**验收标准**：`results match: 1` 说明两种写法返回同一个迭代器；`-Wall` 无警告；能说出这段代码里 lambda 版本比结构体版本少了哪些成分（类型名、构造函数、成员函数）。

**改值实验**：把 `int divisor = 7;` 改成 `int divisor = 2;`，同时把 `is_divisible(7)` 改成 `is_divisible(2)`，重新编译运行。预期两段查找都打印 `20`（20 是向量里第一个偶数），`results match` 仍为 `1`。

### 13.5 实验五：三种捕获方式与 `mutable`

`lambda_capture\lambda_capture.cpp` 依次演示按值捕获、按引用捕获、捕获列表里新建变量，以及 `mutable` 修改自己副本的效果。

```text
cd "E:\CPP_Code\CppFromScratch\ch39_lambdas\lambda_capture"
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g lambda_capture.cpp -o lambda_capture.exe
./lambda_capture.exe
```

**预期输出**：

```text
=== Demo A: capture by value takes a snapshot ===
threshold at definition time = 10
threshold now = 100
by_value(50) -> 1
by_reference(50) -> 0
=== Demo B: create a new variable in the capture list ===
is_divisible_by_ten(20) -> 1
is_divisible_by_ten(21) -> 0
=== Demo C: mutable lets the lambda change its own copy ===
calls so far: 1
calls so far: 2
calls so far: 3
counter outside is still 0
```

**验收标准**：输出与上面一致；`-Wall` 无警告；能解释 `by_value(50) -> 1` 与 `by_reference(50) -> 0` 为什么相反，以及第 3 行打印的 `counter outside is still 0` 说明了什么。

**改值实验**：把 `threshold = 100;` 改成 `threshold = 30;`，重新编译运行。预期 `by_value(50) -> 1` 不变（快照仍是 10），而 `by_reference(50) -> 1`——按引用捕获读到的新值是 30，`50 >= 30` 成立。再想一步：如果改成 `threshold = 5;`，两行都会是 `1`，此时两种捕获方式在这个例子上恰好表现一致，但原因不同。
