# 14 vector：长度可变的动态数组

上一篇：[[13 排序算法：标准库算法入门]]
下一篇：[[15 引用：给变量起别名]]

## 学习目标

完成本章后，你应当能够：

1. 说明 `std::array` 的长度为什么必须在编译期确定，以及这在实际问题里会卡在哪一步。
2. 创建并初始化一个 `std::vector`，说出它的模板参数与 `std::array` 的区别。
3. 用 `push_back` 和 `pop_back` 在运行时增加、减少元素个数。
4. 区分 `size` 与 `capacity`，说出空间用尽时会发生什么、代价在哪。
5. 用 `reserve` 提前预留空间避免反复重新分配，用 `shrink_to_fit` 把多余空间还回去。

## 1 固定长度的容器不够用

第 05 章的 `std::array<int, 5>` 把元素个数写进了类型里：`std::array<int, 5>` 和 `std::array<int, 6>` 是**两个不同的类型**。这带来两个好处——长度是编译期常量，编译器可以据此分配内存、检查越界；也带来一个硬限制：**要放几个元素，写代码的时候就必须定下来**。

现实里的数据往往没有这么听话。要处理的数字可能来自文件、来自随机生成、来自用户输入，程序开始跑之前根本不知道总数：也许 10 个，也许 10000 个。这个"运行时才知道长度"的需求，`std::array` 满足不了——它没法先留空，也没法在跑起来之后变长。

有人会说：那我按"最多可能有多少个"开一个大数组，再另外用一个变量记着实际用了几个。能凑合，但代价不小：内存按最坏情况占着（一万个整数的数组只用得上十个，剩下的全浪费），"长度"这个信息被拆成两处（数组本身和那个计数变量），两处一旦对不上，程序就会出错。

更好的办法是换一个容器，它能**随着需要自己长大**。这就是 `std::vector`：在很多方面和 `std::array` 一样，只是它是**动态大小的数组**——长度在运行时可以变化。

## 2 创建 std::vector

`std::vector` 声明在头文件 `<vector>` 里。它的完整模板签名有一长串，但**日常只需要写元素类型**：

```cpp
std::vector<int> myVector {1, 2, 3, 4, 5};
```

和 `std::array` 逐项对照：

| | `std::array<int, 5>` | `std::vector<int>` |
| --- | --- | --- |
| 模板参数 | 元素类型 + 元素个数 | 只有元素类型（分配器有默认值，不用写） |
| 长度何时确定 | 编译期，是类型的一部分 | 运行时可变 |
| 创建后能否增删元素 | 不能 | 能（`push_back`、`pop_back` 等） |
| 内存从哪来 | 对象自己带着（就在对象内部） | 运行时向自由存储区申请，`vector` 对象只保存"指针 + 大小 + 容量" |

所谓"分配器（allocator）"，指的是决定"内存向谁要、怎么要"的那个部件。绝大多数情况用默认的就够了，只有在需要特殊内存管理（比如自定义内存池、多态分配器）时才去指定它，本课程不涉及。

初始化写法与 `std::array` 完全相同：花括号里列出初始元素即可。也可以不给初值：

```cpp
std::vector<int> emptyVector;   // 空 vector：元素个数为 0
```

这里要立刻记住一条与 `std::array` 不同的性质：`std::array<int, 5>` 一旦创建就**已经有 5 个元素**（哪怕没给初值），而 `std::vector<int>` 不给初值就是**一个元素都没有**。

例程 `E:\CPP_Code\CppFromScratch\ch14_vector\vector_basic\vector_basic.cpp` 把创建、初始化、访问放在一起：

```cpp
#include <iostream>
#include <vector>

void print(std::vector<int> values)
{
    for (auto value : values)
    {
        std::cout << value << " ";
    }
    std::cout << std::endl;
}

int main()
{
    std::vector<int> myVector {1, 2, 3, 4, 5};

    print(myVector);

    std::cout << "size = " << myVector.size() << std::endl;
    std::cout << "front = " << myVector.front() << ", back = " << myVector.back() << std::endl;
    std::cout << "myVector[0] = " << myVector[0] << ", myVector.at(1) = " << myVector.at(1) << std::endl;

    std::vector<int> emptyVector;
    std::cout << "emptyVector.size() = " << emptyVector.size() << std::endl;

    return 0;
}
```

打印函数 `void print(std::vector<int> values)` 的参数**没有** `&`，所以调用时整个 vector 会被复制一份——这里只是打印，这份复制完全是白花的。第 16 章会给出解决办法（按引用传参），本章先保持写法一致。

## 3 像数组一样访问元素

`std::vector` 的大部分访问接口就是 `std::array` 那一套，用法一模一样：

- `size()`：当前元素个数。返回类型是无符号整数 `size_t`（不是 `int`），这一点后面会专门提。
- `front()` / `back()`：取第一个、最后一个元素的引用。
- `operator[]`：`myVector[0]` 那种写法，**不做边界检查**。
- `at(n)`：按下标取元素，**会做边界检查**，越界时会报告错误（异常机制在后续章节展开）。
- `data()`：拿到指向首个元素的指针；`begin()` / `end()`：第 12 章那对迭代器，第 13 章的 `std::sort(myVector.begin(), myVector.end())` 可以直接用在这个容器上。

`[]` 和 `at` 的选择很直接：下标一定合法时用 `[]`，它更快也更常见；不确定时才用 `at`，宁可多一次检查也不要不声不响地读错内存。

这里有一个必须明确的边界：**对空 vector 调用 `front()`、`back()` 或任何下标都是未定义行为**。空的 `std::vector<int>` 里没有任何元素，`myVector[0]` 不是"返回 0"或"返回空"，而是访问了不属于你的内存——它可能碰巧不崩，也可能读出垃圾值，还可能在别的地方引发难以定位的故障。所以在按下标访问之前，先确认 `size()` 够大。

## 4 增删元素：push_back 与 pop_back

真正让 `std::vector` 区别于 `std::array` 的，是它能在运行时改变大小：

- **`push_back(值)`**：把一个新元素追加到末尾，`size` 加 1。
- **`pop_back()`**：移除末尾那一个元素，`size` 减 1。

例程 `E:\CPP_Code\CppFromScratch\ch14_vector\push_pop\push_pop.cpp` 演示了这一对操作，输出与第 08 章那种"打印—改动—再打印"的节奏一致：

```text
=== original ===
1 2 3 4 5 
=== after push_back(6) ===
1 2 3 4 5 6 
=== after pop_back() ===
1 2 3 4 5 
```

两点值得记住：

- `pop_back()` **不返回**被删掉的那个值，它只产生"末尾少了一个元素"这个效果。如果那个值还需要用，必须在删之前先用 `back()` 取出来存好。
- 对**空** vector 调用 `pop_back()` 是未定义行为。删之前先确认 `size() > 0`，这是删除操作的通用规则，`std::vector` 不例外。

`push_back` 的平均代价是**常数时间**（记为均摊 $O(1)$），但这个"均摊"是有来历的——下节就讲清楚为什么。

## 5 size 与 capacity：底层到底分配了多少

很多人第一次用 `std::vector` 都会问同一个问题：既然长度可以随时变，那底层内存是怎么管的？要回答它，必须把两个概念分开：

- **size（大小）**：容器里**实际有几个元素**。这是"逻辑上"的大小，就是你 `push_back` 了几次、`pop_back` 了几次算出来的。
- **capacity（容量）**：底层**已经申请了能放几个元素的空间**。这是"物理上"准备好的位置数，通常大于等于 size。

为什么不让两者一直相等？因为申请内存这件事很贵：从自由存储区要一块更大的内存，把原来的元素**逐个搬过去**，再把旧内存还掉（第 18 章会看到这套动作的细节）。如果每次 `push_back` 都刚好扩一个位置，那么第 $k$ 次添加都要搬 $k-1$ 个元素，添加 $N$ 个元素总共要搬 $\frac{N(N-1)}{2}$ 次，也就是 $O(N^2)$——插入本该很便宜的操作会变得非常慢。

标准库的做法是**一次多要一些**，让后面若干次 `push_back` 都能直接用现成的空位。例程 `E:\CPP_Code\CppFromScratch\ch14_vector\size_capacity\size_capacity.cpp` 在每次 `push_back` **之前**打印 `size` 和 `capacity`，空 vector 连加 10 个元素：

```cpp
std::vector<int> myVector;

for (int i = 0; i < 10; i = i + 1)
{
    std::cout << "before #" << (i + 1) << ": size = " << myVector.size()
              << ", capacity = " << myVector.capacity() << std::endl;

    myVector.push_back(i);
}
```

实际输出（实测于 GCC 16 的 libstdc++）：

```text
=== 10 push_back calls without reserve ===
before #1: size = 0, capacity = 0
before #2: size = 1, capacity = 1
before #3: size = 2, capacity = 2
before #4: size = 3, capacity = 4
before #5: size = 4, capacity = 4
before #6: size = 5, capacity = 8
before #7: size = 6, capacity = 8
before #8: size = 7, capacity = 8
before #9: size = 8, capacity = 8
before #10: size = 9, capacity = 16
after the loop: size = 10, capacity = 16
```

把这张表读成一句话：`size` 每次加 1，`capacity` 只在"已经用满"时才跳一次，而且**直接翻倍**——0、1、2、4、8、16。前面看到 size 和 capacity 相等（1 和 1、2 和 2、4 和 4、8 和 8）的那些时刻，就是下一次 `push_back` 必须重新分配的时刻；其他时候空位还够，加进去不花钱。

于是总账变漂亮了：添加 $N$ 个元素时，虽然偶尔要搬一大堆元素，但每次重新分配都把容量翻倍，搬运的总次数是 $N + \frac{N}{2} + \frac{N}{4} + \cdots < 2N$，也就是 $O(N)$；分摊到 $N$ 次插入上，每次插入的平均成本是个常数，这就是"均摊 $O(1)$"。

**扩容倍数不是标准规定的。** 标准只说 `push_back` 均摊常数时间，具体扩多少由实现自己定。这里用的 libstdc++（GCC 附带的 C++ 标准库）取 2 倍，别的实现可能取 1.5 倍，序列不同但"按倍数增长"这个性质相同。所以不要写出"容量一定是 2 的幂"这类假设。

**重新分配还有第二个后果，而且更容易咬人：所有指向容器元素的迭代器、指针和引用都会失效。** 重新分配意味着元素已经被搬到另一块内存，原来那些还指着旧地址的迭代器就成了野指针，再拿它们去访问就是未定义行为。规则可以记成：**只要可能发生 `push_back` 等修改大小的操作，就不要把之前拿到的迭代器或引用长期存着用**。

## 6 reserve 与 shrink_to_fit：把容量也管起来

既然重新分配的代价集中体现在"翻倍之前的那几次插入"上，那能不能提前把空间一次要够？可以，这就是 `reserve(n)`：它把容量一次性扩到**至少**能放 $n$ 个元素，但**一个元素都不放进去**——它改的是 `capacity`，不是 `size`。例程 `E:\CPP_Code\CppFromScratch\ch14_vector\reserve_shrink\reserve_shrink.cpp` 先 `reserve(10)`，再跑同一个 10 次循环：

```text
=== reserve(10), then 10 push_back calls ===
before #1: size = 0, capacity = 10
before #2: size = 1, capacity = 10
before #3: size = 2, capacity = 10
before #4: size = 3, capacity = 10
before #5: size = 4, capacity = 10
before #6: size = 5, capacity = 10
before #7: size = 6, capacity = 10
before #8: size = 7, capacity = 10
before #9: size = 8, capacity = 10
before #10: size = 9, capacity = 10
after the loop: size = 10, capacity = 10
```

容量一路停在 10，中途一次重新分配都没有。要注意第一行的 `size = 0, capacity = 10`：`reserve` 之后容器仍然是**空的**，只是"准备好了 10 个位置"。所以 `reserve` 不能替代 `push_back`，也不能让你马上访问 `myVector[0]`。

什么时候用 `reserve`？**已经知道大概要放多少个元素的时候**，比如"这个循环正好跑 10 次、每次加一个"。这时预留可以彻底避免中途的搬运。反过来，如果根本不知道要放多少，就别凭感觉猜一个数——预留过多会白占内存，还得不到好处。

容量只会自己涨，不会自己降：`pop_back` 只减 `size`，内存还留着。如果确定容器不会再变大，可以用 `shrink_to_fit()` 把多余空间还回去，让容量降到与大小一致。同一个例程里删掉 5 个元素再收缩：

```text
=== after 5 pop_back calls ===
contents: 0 1 2 3 4 
size = 5, capacity = 10
=== after shrink_to_fit() ===
size = 5, capacity = 5
```

注意标准对 `shrink_to_fit` 的措辞是"**请求**把容量降到和大小一样"，并没有强制实现必须照办——因为它可能带来一次重新分配和整体搬运。本例的 libstdc++ 确实收缩了，但换一个实现、换一种情形（比如 `size` 和 `capacity` 本来就相等），结果不保证一模一样。所以它适合在"确实要还内存"的地方用，不适合当作每一步都要精确成立的操作。

`std::vector` 还有 `insert`、`erase`、`resize`、`clear` 等成员函数，分别对应在中间插删、改变长度、清空等操作。它们涉及到元素的移动和迭代器失效的细节，等到用得上时（第 30 章讲 `push_back` 与 `emplace_back` 的区别、后续讲类和构造函数的章节）再展开。

## 7 动手实验

例程在 `E:\CPP_Code\CppFromScratch\ch14_vector\` 下，四个程序各占一个文件夹、都能独立编译运行。

命令模板（三行，先 `cd` 进例程目录，再编译、运行）：

```text
cd "E:/CPP_Code/CppFromScratch/ch14_vector/vector_basic"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g vector_basic.cpp -o vector_basic.exe
./vector_basic.exe
```

后面几个实验只替换路径和文件名。

### 7.1 实验一：创建、初始化与访问

源码 `vector_basic\vector_basic.cpp`。

**预期输出**（第一行每个数字后面跟一个空格，所以行末还有一个空格）：

```text
1 2 3 4 5 
size = 5
front = 1, back = 5
myVector[0] = 1, myVector.at(1) = 2
emptyVector.size() = 0
```

**验收标准**：五行与上面逐字符一致；能回答"`std::vector<int> myVector {1, 2, 3, 4, 5};` 这一行报出的 `size` 是 5，而 `std::vector<int> emptyVector;` 报出的 `size` 是 0"。

**改值实验**：把初始化列表改成 `{42}`，同时预测并核对输出：第一行只剩一个 42（后面跟一个空格），`size` 应变 1，`front` 和 `back` 都应变 42。改回原值。

**边界实验**：把初始化列表整个删掉，让 `myVector` 也变成一个空 vector（写成 `std::vector<int> myVector;`）。程序仍然能编译，但此时 `front()` 和 `back()` 是在**空 vector** 上取元素——第 3 节说过这是未定义行为，程序可能打印出垃圾值。这个实验只用于看清"编译通过不等于行为正确"，不要把它留在代码里；看完把初始化列表加回来，重新编译确认输出恢复。

### 7.2 实验二：追加与删除

源码 `push_pop\push_pop.cpp`。

**预期输出**：

```text
=== original ===
1 2 3 4 5 
=== after push_back(6) ===
1 2 3 4 5 6 
=== after pop_back() ===
1 2 3 4 5 
```

**验收标准**：三行数据与 4 节给出的一致，第二行多出 6，第三行又回到 5 个元素。

**改值实验**：把 `push_back(6)` 改成连续两次 `push_back(6)`，预测输出（第一段 5 个、第二段 7 个、第三段回到 5 个）并核对；再把 `pop_back()` 也调用两次，第三段应变成 `1 2 3 4 `。

### 7.3 实验三：观察 size 与 capacity

源码 `size_capacity\size_capacity.cpp`，空 vector 连加 10 个元素并打印过程。

**预期输出**：与第 5 节列出的 12 行完全一致（`before #4` 时容量跳到 4、`before #6` 时跳到 8、`before #10` 时跳到 16）。

**验收标准**：输出逐字符一致；能指着某一行说出"这里发生了重新分配"，以及为什么下一次不会立刻再分配。

**改值实验**：把循环条件 `i < 10` 改成 `i < 5`，先预测 `before #5` 那一行的容量是 4 还是 8，再运行核对（应为 4，因为容量 4 还没用满，第 5 个元素正好放进去）。想清楚为什么"size 到 4 时还没重新分配"这一点，再改回去。

### 7.4 实验四：reserve 与 shrink_to_fit

源码 `reserve_shrink\reserve_shrink.cpp`。

**预期输出**：与第 6 节列出的三段输出逐字符一致，共 17 行。

**验收标准**：第一段所有行的 `capacity` 都是 10（一次重新分配都没有）；`pop_back` 之后 `size` 降到 5 而 `capacity` 仍是 10；`shrink_to_fit` 之后两者都是 5。

**改值实验**：把 `reserve(10)` 改成 `reserve(3)`。预测：前 3 个元素进来时容量停在 3，第 4 个元素进来时必须重新分配，容量会跳起来（本例 libstdc++ 扩容后是 6）。运行核对，然后想清楚这个实验说明了什么——`reserve` 给的是"至少这么多"，给少了照样会重新分配。改回 `reserve(10)`。

## 8 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| `error: 'vector' is not a member of 'std'` 并附注 `note: 'std::vector' is defined in header '<vector>'` | 忘了 `#include <vector>`（`<iostream>` 里没有它） | 加上 `#include <vector>` |
| `error: no matching function for call to 'std::vector<int>::push_back()'` | `push_back` 必须给出要添加的值 | 补上实参，例如 `v.push_back(6);` |
| `error: no matching function for call to 'push_back(const char [6])'`，并附注 `invalid conversion from 'const char*' to 'std::vector<int>::value_type' {aka 'int'}` | 往 `std::vector<int>` 里塞字符串——元素类型必须与模板参数一致 | 放进正确类型的数据，或改用 `std::vector<std::string>`（第 03 章的类型规则同样适用） |
| `warning: comparison of integer expressions of different signedness: 'int' and 'std::vector<int>::size_type' {aka 'long long unsigned int'} [-Wsign-compare]` | `size()` 返回的是无符号的 `size_t`，与 `int` 比较时符号不同 | 让循环变量也用同一类型（`for (std::size_t i = 0; i < v.size(); ++i)`），或者直接用范围 `for` |
| `error: conversion from 'std::vector<int>' to non-scalar type 'std::array<int, 3>' requested` | 把 `std::vector` 当 `std::array` 用，两者是不同类型，不能互相赋值 | 统一用一个容器类型；长度不再固定时用 `std::vector` |
| 程序在访问 `myVector[5]`、`front()`、`back()` 时崩溃或读出莫名其妙的值 | 下标越界，或对空 vector 取了首尾元素——这些操作都不检查边界 | 访问前确认 `size()` 够大；不确定时用 `at()`（会检查） |
| 对空 vector 调用 `pop_back()` | `pop_back` 要求容器非空，空时是未定义行为，未必报错 | 删除前先判断 `size() > 0` |
| 用 `reserve` 之后马上访问 `myVector[0]` | `reserve` 只改容量，不加元素，此时 `size` 仍为 0 | 先用 `push_back` 把元素加进去，`reserve` 只是提前准备空间 |

## 9 本章验收

1. 四个例程都编译通过、`-Wall` 零警告，运行输出与 7.1 至 7.4 节的预期输出逐字符一致。
2. 能说出 `std::vector<int>` 与 `std::array<int, 5>` 在"长度何时确定"和"能否增删元素"上的区别。
3. 能用自己的话解释 `size` 与 `capacity` 的区别，并说明容量翻倍为什么能把 `push_back` 的均摊代价压到常数。
4. 能说出 `reserve` 与 `shrink_to_fit` 各改的是哪一个量，以及"请求收缩"为什么不是保证。
5. 完成过 7.3、7.4 的改值实验，能先预测 `capacity` 的变化再运行核对。
