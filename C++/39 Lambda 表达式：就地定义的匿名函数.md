# 39 Lambda 表达式：就地定义的匿名函数

上一篇：[[38 函数对象：重载函数调用运算符]]
下一篇：[[40 并行 STL 算法：用执行策略加速]]

## 学习目标

完成本章后，你应当能够：

1. 说出 lambda 表达式由哪三个部分组成，以及每一部分对应函数对象的什么。
2. 按值捕获和按引用捕获外部变量，并说出两者在"何时看到变化"上的差别。
3. 在捕获列表里直接创建只属于这个 lambda 的变量。
4. 把 lambda 直接写在算法调用处当谓词，替换掉上一章手写的函数对象。
5. 说明 lambda 的类型为什么只能用 `auto` 接住。

## 1 上一章留下的样板代码

第 38 章为了让一个对象"能被调用并携带一个除数"，写了这样一个类型：

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

C++11 起提供了直接支持：**lambda 表达式**可以在使用它的位置就地写出来，不需要类型名、不需要结构体或类，还能把作用域里的变量带进这个匿名的函数对象里。也就是说，上一章的能力全部保留，写法缩短到一行。

## 2 lambda 的三个组成部分

把上一章的 `is_divisible` 换成 lambda，得到 `ch39_lambdas\lambda_divisible\lambda_divisible.cpp` 里的这一行：

```cpp
auto is_divisible_by_ten = [divisor = 10](int dividend)
{
    return dividend % divisor == 0;
};
```

它由三个部分组成，顺序固定：

| 部分 | 位置 | 作用 | 对应上一章的函数对象 |
| --- | --- | --- | --- |
| 捕获列表 | `[divisor = 10]` | 把外部变量或新建的变量带进这个函数对象 | 数据成员 + 构造函数的初始化 |
| 参数列表 | `(int dividend)` | 每次调用时要传进来的输入 | `operator()` 的参数列表 |
| 函数体 | `{ return ...; }` | 真正执行的语句 | `operator()` 的函数体 |

逐项对照上一章的代码：

- **捕获列表**是 lambda 独有的部分，其它函数都没有。`divisor = 10` 的意思是"在这个函数对象里新建一个成员 `divisor`，初值取 10"，所以不必再写构造函数和成员声明，也不需要写 `int`——类型由初值 10 推出来。
- **参数列表**和普通函数、和 `operator()` 的参数列表完全一致。这里写 `(int dividend)`，表示每次调用要提供一个待检查的数。
- **函数体**就是原来 `operator()` 里的那条 `return`，一个字都没改。返回值类型同样不写：`return` 后面的表达式类型就是 lambda 的返回类型（这里推成 `bool`）。
- **末尾的分号不能少**。lambda 表达式本身是表达式，整句仍然是一条语句。

上一章那个十行的类型定义、构造函数、`operator()`，在功能等价的前提下被这三行取代了。

## 3 捕获列表：lambda 的状态从哪里来

捕获列表是 lambda 的特征所在，它决定了这个函数对象拥有什么状态、这些状态是副本还是别的变量的别名。有三种常用写法。

### 3.1 按值捕获：留下一份快照

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

### 3.2 按引用捕获：共享同一个变量

在变量名前加 `&` 是按引用捕获。它不复制数据，lambda 内部用的就是外面那个变量本身，因此有两个后果：

- 外部改了值，下次调用立刻能看到（上面实验已验证）；
- 外面的变量一旦销毁，lambda 里存的就是一个失效的引用，再调用它属于未定义行为。

所以按引用捕获适合"在同一个作用域内临时用一下"的场合，比如马上传给算法、调用完就丢掉的 lambda。把按引用捕获的 lambda 存起来、离开原来的作用域之后再调用，是很容易踩的坑。

### 3.3 在捕获列表里新建变量

捕获列表里可以像初始化变量一样写 `名字 = 初值`，这样就给这个匿名函数对象加了一个**只属于它自己**的成员：

```cpp
auto is_divisible_by_ten = [divisor = 10](int dividend)
{
    return dividend % divisor == 0;
};
```

好处是这个名字不会跑到外层作用域去，也不会和外面的同名变量互相干扰。这种写法既能用字面量初始化（`divisor = 10`），也能用外层变量初始化（`divisor = candidate`，相当于给外层变量拍一张快照并另起一个名字），因此它同时替代了上一章"数据成员 + 构造函数"两件事。

### 3.4 `mutable`：允许修改自己那份副本

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

## 4 匿名，但仍然有类型

lambda 的类型由编译器生成，是一个**没有名字的类类型**——这也是它被称为"匿名函数对象"的原因。由此带来几条实际影响：

- 想接住它只能用 `auto`，或者把它当作模板参数传出去。写不出类型名，也不必写。
- 两个字面完全一样的 lambda 也是**不同的类型**，所以 `decltype(f)` 那一套名字只有编译器自己知道，它们之间不能互相赋值。
- 因为它本质上就是一个类，前面讲过的规则都适用：捕获的变量就是它的数据成员，函数体就是 `operator()` 的函数体，参数和返回值规则与普通函数相同。

理解这一点之后，"lambda 是语法糖"这句话就具体了：它糖化出来的正是上一章那个手写的函数对象。

## 5 把 lambda 交给算法

谓词的位置和上一章完全一样——算法只要求能写成 `谓词(元素)` 的形式。例程 `lambda_divisible\lambda_divisible.cpp` 把 `find_if` 的第二个参数换成了 lambda：

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

结果与第 38 章用函数对象得到的完全一致（20 是第一个能被 10 整除的元素），而且 lambda 也是个普通对象，直接调用它的写法和调用函数对象毫无区别（`Demo A` 两行）。

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

## 6 什么时候用 lambda，什么时候用具名类型

两者的能力对等，选择取决于这个条件会被怎么用：

- **只在一个地方用一次**（典型场景就是紧跟着传给某个算法）：用 lambda。条件和使用点挨在一起，不需要起名字，也不会污染外层作用域。
- **要反复使用多次、要起名字表达意图、或者需要明确写出类型**：用第 38 章那样的具名类型或普通函数。一个"能被 10 整除"的规则如果是整个模块共用的概念，给它一个名字比在每个调用点重复写一遍 lambda 更清楚。
- **需要在调用之间保持状态**：两种都可以（lambda 靠捕获或 `mutable`），但如果状态的含义比较复杂，写成具名类型更容易读、也便于加注释和别的成员函数。

一句话概括：lambda 让"一次性条件"不再需要付出定义类型的代价，而具名类型仍然是表达"可复用概念"的工具。

## 7 动手实验

例程在 `E:\CPP_Code\CppFromScratch\ch39_lambdas\` 下，三个程序各占一个文件夹，都是单文件自包含。

### 7.1 实验一：用 lambda 替换函数对象

`lambda_divisible\lambda_divisible.cpp` 用 `[divisor = 10](int dividend)` 这个 lambda 完成第 38 章函数对象的全部工作：直接调用两次，再作为谓词传给 `std::ranges::find_if`。

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

**验收标准**：输出逐字符与上面一致；`-Wall` 无警告；能指着 `[divisor = 10](int dividend) { return dividend % divisor == 0; }` 分别说出捕获列表、参数列表、函数体各是哪一段，以及它替换掉了上一章的哪些代码。

**改值实验**：把捕获列表里的 `divisor = 10` 改成 `divisor = 7`，重新编译运行。预期 `Demo A` 两行都变成 `-> 0`（55 除以 7 余 6，50 除以 7 余 1），`Demo B` 打印出 `first element divisible by 10: 84`——84 是向量里第一个 7 的倍数，其中 `divisible by 10` 只是写死在输出字符串里的文字，不会跟着变。看完改回 `10`。

### 7.2 实验二：lambda 与函数对象结果一致

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

### 7.3 实验三：三种捕获方式与 `mutable`

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

## 8 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| `error: 'divisor' is not captured`，附 `note: the lambda has no capture-default` | 捕获列表写成了空的 `[]`，函数体里却用了外部变量 | 在捕获列表里写出该变量：`[divisor]`、`[&divisor]` 或 `[divisor = 10]` |
| `error: increment of read-only variable 'c'` | 按值捕获的变量在 lambda 内是只读的，却对它做了 `++` | 在参数列表后加 `mutable`（注意改的是副本），或改为按引用捕获 |
| `error: inconsistent types 'int' and 'double' deduced for lambda return type` | 函数体里有多个 `return`，各自推导出的类型不同 | 让所有 `return` 的表达式类型一致，或统一显式转换 |
| `error: expected ',' or ';' before 'std'`（指向 lambda 的右花括号之后） | 整个 lambda 表达式后面漏了分号 | 在 `};` 处补上分号；lambda 是表达式，这一行仍是一条语句 |
| `error: 'y' was not declared in this scope`（指向捕获列表里的名字） | 捕获列表里写了作用域中不存在的变量名 | 核对拼写，或确认该变量确实在 lambda 定义之前已声明 |
| 程序在调用 lambda 时输出乱值或崩溃 | 按引用捕获的局部变量已经销毁，lambda 里留下失效引用 | 只在原作用域内使用按引用捕获的 lambda；需要保存就改成按值捕获 |
| 想让 lambda 里的状态在新调用之间累加，结果每次都从初值开始 | 每次调用的是**另一个** lambda 对象（例如在函数里临时构造），或该状态被按值捕获后又没有 `mutable` | 把 lambda 存进一个变量并反复调用同一个对象；需要修改副本时加 `mutable` |
| `error: no match for 'operator=' (operand types are 'main()::<lambda(int)>' and 'main()::<lambda(int)>')` | 试图把一个 lambda 赋给另一个写法相同的 lambda；每个 lambda 都是互不相同的匿名类型 | 各自用 `auto` 接住即可，不要相互赋值；需要统一处理时让调用方接受可调用对象（例如算法的谓词参数） |

## 9 本章验收

1. 三个例程编译通过、`-Wall` 无警告，输出与 7.1、7.2、7.3 节的预期一致。
2. 能默写一个带捕获的 lambda，并指出其中哪一段对应函数对象的哪个成分。
3. 能说清按值捕获与按引用捕获的区别，并举出"外部改动后行为不同"的例子。
4. 能解释 `mutable` 的作用，以及为什么 `calls so far` 会累加而外面的 `counter` 始终是 0。
5. 能说出把 lambda 当谓词传给 `std::ranges::find_if` 时，返回的迭代器为什么必须先与 `end()` 比较。
