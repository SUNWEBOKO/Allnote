# 06 迭代器、算法与并行 STL

上一篇：[[05 函数模板与特化]]
下一篇：[[07 vector：动态数组与元素添加]]

## 学习目标

完成本章后，你应当能够：

1. 说出迭代器是什么，用 `begin()`/`end()` 写出遍历循环。
2. 用 `*it` 读写元素，用 `rbegin()`/`rend()` 反向遍历，用偏移圈出任意子区间。
3. 用 `std::sort` 就地排序整个容器或一段子区间，写出等价的 `std::ranges::sort` 写法。
4. 说出 `std::execution` 四种执行策略各自允许做什么。
5. 在 MSYS2 UCRT64 上用 `-ltbb12` 正确链接 TBB 编译运行并行程序，让输出保持确定。

## 1 为什么需要"位置"的抽象

第 03 章遍历 `std::array` 有两种办法：下标 `myArray[i]`，或者范围 `for (auto value : myArray)`。两种都够用，但都带着一个限制：**它们只对"能用整数下标数过去"的容器有效**。

- 下标 `myArray[i]` 要求容器"能按下标随机访问"。这对 `std::array` 成立，对将来会遇到的链表、映射这类容器就不成立——它们的元素在内存里并不连续，根本没有"第 i 个"这种算法。
- 范围 `for` 只能"从头到尾走一遍"，没法表达"处理中间那几个元素"。

而标准库里有一大批通用工具（排序、查找、累加、复制……），它们**不应该**为每种容器各写一遍。要让同一份排序代码既能排 `std::array` 又能排别的容器，它就不能依赖"下标"或"容器类型"，只能依赖一组更小的、所有容器都能提供的操作：

1. **取到一个位置**（通常从"开头"和"末尾"两个位置开始）；
2. **判断两个位置是不是同一个**（以及有没有走到末尾）；
3. **让位置前移一格**；
4. **取出这个位置上的元素**。

把"位置"抽象成一个对象，这四条就是它的全部契约，这个对象就叫**迭代器**（iterator）。容器负责提供"开头"和"末尾"两个迭代器（`begin()` 与 `end()`），算法只按上面四条来写。于是**容器与算法的数量可以各自增长而不互相纠缠**：新增一个容器，只要它提供符合约定的迭代器，所有算法立刻可用；新增一个算法，只要它只使用迭代器的这几种操作，所有容器立刻可用。

**迭代器的主要用途正是与标准库算法配合**：算法接收的不是"容器"，而是一对迭代器——它们圈出一个**值的范围**，算法在这个范围上工作。本章第 7 节的排序算法会把这条线接上；下面几节先把迭代器本身用熟。

## 2 用迭代器写一遍遍历

例程 `E:\CPP_Code\CppFromScratch\ch12_iterators\iterator_basic\iterator_basic.cpp`：

```cpp
std::array<int, 5> myArray {1, 2, 3, 4, 5};

for (auto it = myArray.begin(); it != myArray.end(); ++it)
{
    std::cout << *it << " ";
}

std::cout << std::endl;
```

```text
=== Demo A: iterating with begin() and end() ===
1 2 3 4 5 
```

这就是第 03 章手动 `for` 循环的老框架，三部分换成迭代器而已：

| 循环部位 | 手写下标版 | 迭代器版 | 含义 |
| --- | --- | --- | --- |
| 初始化 | `int i = 0;` | `auto it = myArray.begin();` | 从序列开头开始 |
| 条件 | `i < 5;` | `it != myArray.end();` | 还没走到末尾就继续 |
| 步进 | `++i` | `++it` | 前进一格 |

**关键在 `end()` 的含义：它指向"最后一个元素的下一个位置"，不是最后一个元素。** 这句话决定了循环条件该写 `!=` 而不是 `<=`。好处有两个：

- **长度不再由我们维护**。手写版必须写对 `5`，或者记得用 `myArray.size()`；迭代器版只问"到末尾了吗"，长度多少都不影响循环的写法。
- **空区间也能自然表达**。一个 5 元素的数组和一个空数组用同一套写法：空的时候 `begin() == end()`，循环一次都不进。

`[begin, end)` 这种"左闭右开"的写法是标准库的通用约定。它让"结束"这件事只需要一个位置就能说清，也让"把区间切成两段"变成最简单的拼接：`[a, b)` 加上 `[b, c)` 正好是 `[a, c)`，不重不漏。

`end()` 的含义在例程里当场验证：

```cpp
std::cout << "*(end() - 1) = " << *(myArray.end() - 1) << std::endl;
```

```text
*(end() - 1) = 5
```

`end() - 1` 才是最后一个元素的位置；而 `*end()` 是**越界访问，不允许**（编译器不会拦，运行结果不可信）。

关于写法还有一处要交代。你可能见过把条件写成 `it < myArray.end()`、步进写成 `it += 1` 的代码，本例用的是 `it != myArray.end()` 和 `++it`。两组在本例中都有效，因为 `std::array` 提供的迭代器是**随机访问迭代器**（在 libstdc++ 里它的迭代器其实就是 `int*` 这样的裸指针，所以能比大小、能做 `+` 运算）。但 `!=` 与 `++` 是**所有迭代器都支持**的形式，`<` 与 `+=` 只有随机访问迭代器支持。**写通用的代码时用 `!=` 和 `++`**，能少一类将来换容器才暴露的编译错误。

## 3 解引用：`*it` 拿到的是元素本身

`it` 本身没有能直接打印的"值"——它记录的是位置。取出位置上元素的写法是 `*it`（**解引用**，同一个符号在第 09 章讲指针时还会再见面）。

`*it` 的类型不是"元素的一个副本"，而是**元素的引用**。所以它可以出现在赋值号左边，改动会落到容器里真正的数据上。例程 `ch12_iterators\iterator_write\iterator_write.cpp`：

```cpp
for (auto it = myArray.begin(); it != myArray.end(); ++it)
{
    *it *= 10;      // 把每个元素改成原来的 10 倍
}
```

```text
=== Demo D: writing through an iterator ===
before: 1 2 3 4 5 
after : 10 20 30 40 50 
```

这一条是后面很多用法的地基：**算法之所以能"就地"修改区间里的元素**，靠的就是"传给算法的迭代器解引用之后可写"。如果只需要读，容器也能提供只读的迭代器（`cbegin()`/`cend()`），解引用得到的就是只读引用。本章的例程都用可写的 `begin()`/`end()`。

## 4 反向迭代器：不改逻辑，只换方向

有时需要从尾到头遍历。手写下标版要改三处：起点写 `size() - 1`、条件写"不小于 0"、步进写自减。其中"不小于 0"还藏着陷阱——`size()` 返回的是**无符号**类型，`size() - 1` 在空数组上会绕成一个巨大的数，`i >= 0` 又永远为真，于是写出一个越界的死循环。

反向迭代器把这些细节收进容器里。例程 `ch12_iterators\iterator_reverse\iterator_reverse.cpp` 只把 `begin()`/`end()` 换成 `rbegin()`/`rend()`：

```cpp
for (auto it = myArray.rbegin(); it != myArray.rend(); ++it)
{
    std::cout << *it << " ";
}
```

```text
=== Demo B: forward and reverse ===
forward: 1 2 3 4 5 
reverse: 5 4 3 2 1 
```

- `rbegin()` 指向**最后一个元素**，这是反向遍历的起点；
- `rend()` 指向**第一个元素之前的位置**，这是反向遍历的终点；
- `++it` 的含义不变，仍然是"沿当前方向前进一格"，只是在反向迭代器上前进意味着下标变小。

**循环结构一个字都没改**，只换了两个名字，方向就反了。这正是把"位置"抽象出来的收益：方向成了数据的一部分，而不是循环逻辑的一部分。

## 5 偏移：一对迭代器可以圈出任意子区间

只要保持"起点不越过终点"，任意一对同来源的迭代器都能构成一个合法区间——也就是说，**子区间可以像区间本身一样被传递和处理**。例程 `ch12_iterators\iterator_offset\iterator_offset.cpp` 用一个接收一对迭代器的函数来演示：

```cpp
void printRange(auto first, auto last)
{
    for (auto it = first; it != last; ++it)
    {
        std::cout << *it << " ";
    }

    std::cout << std::endl;
}
```

（这个函数用第 05 章的缩写函数模板写法声明模板，因为 `first` 和 `last` 的类型要各自推导。函数体里只用到"能比较、能 `++`、能解引用"这三件事——和标准库算法对迭代器的要求一模一样。）

```cpp
printRange(myArray.begin(), myArray.end());
printRange(myArray.begin() + 1, myArray.end());
printRange(myArray.begin() + 2, myArray.end() - 1);
printRange(myArray.rbegin(), myArray.rend());
printRange(myArray.rbegin() + 2, myArray.rend());
```

```text
=== Demo C: offsets and sub-ranges ===
begin()      to end()    : 1 2 3 4 5 
begin() + 1  to end()    : 2 3 4 5 
begin() + 2  to end() - 1: 3 4 
rbegin()     to rend()   : 5 4 3 2 1 
rbegin() + 2 to rend()   : 3 2 1 
```

逐行看：

- `begin() + 1` 表示"从第 2 个元素开始"，于是丢掉了开头的 `1`。
- `end() - 1` 表示"到最后一个元素之前停下"，于是丢掉了结尾的 `5`。两头一起收，得到的就是中间两个元素 `3 4`。
- 反向迭代器也支持偏移，但方向相反：`rbegin() + 2` 是"从尾部往前数两个"，指向下标 2 上的 `3`，所以输出 `3 2 1`。

**"用一对迭代器表示范围"就是标准库算法的入参形状**，也是子区间能被直接交给算法的原因。不过要记住一条边界：`+`、`-` 这些算术只对**随机访问迭代器**可用，`++`/`--`（以及能用 `--` 的**双向**迭代器）才是更普遍的形式。换句话说，`begin() + 2` 这种写法能不能用，取决于容器的迭代器种类——这是下一节的话题。

## 6 迭代器有种类之分

迭代器不是"一种东西"，而是按能力分成几个等级，从弱到强大致是：**输入迭代器**（只能单遍读）、**输出迭代器**（只能单遍写）、**前向迭代器**（能多遍遍历、但不支持后退）、**双向迭代器**（能 `--`）、**随机访问迭代器**（能 `+`、`-`、比较大小）、**连续迭代器**（元素在内存里连续，`std::array` 属于这一级）。

这套分级解释了两件事：

**第一，为什么有的操作不能用在所有容器上。** `std::array` 的迭代器是随机访问的，所以能 `begin() + 2`、能比较大小、能被需要随机访问的算法使用。换成不提供随机访问的容器，`it + 2` 会直接编译失败。

**第二，为什么不是所有容器都能配合所有算法。** 一个算法如果内部要用 `it + n` 或比较大小，那它就只能接受随机访问迭代器。反过来说，某些容器天生不可能满足这种要求——例如无序容器（哈希表）的迭代器是前向的，而且它保存的元素是"键 + 值"且**键不可修改**（否则哈希表的结构就被破坏了），所以它既不支持排序算法需要的随机访问，也不可能被"就地重排"。这类"哪些容器配哪些算法"的匹配关系，正是迭代器种类在背后规定的事情。

**最后一条实用建议**：如果只是要把整个容器从头到尾走一遍，**用范围 `for` 更好**——它更短、更不容易写错循环条件（第 03 章）。迭代器的价值在另外两处：需要**部分区间**时，需要把**范围交给别人处理**时（进入算法世界以后，这会是常态）。

迭代器把容器和算法接在了一起，现在轮到算法登场。标准库里现成的算法成百上千，下面从最常用的排序开始。

## 7 不重复造轮子

到本章第 6 节为止，我们手上的工具是"容器"：`std::array` 负责把一批同类型的元素连续地存在一起。但存数据本身从来不是目的——真正要做的是一件件事：找出最大值、把顺序理一遍、查某个值在不在里面。这些**对数据做的操作**，标准库也准备好了现成的一套，放在**算法库**里。

用现成算法最直接的理由就是不必重复造轮子。排序谁都能自己写：冒泡排序几十行，选择排序更短。但自己写出来的版本，通常在正确性和性能上都不如标准库的实现——标准库的实现是被无数程序用过、被反复优化过的。当然，总有例外情形（特殊的数据分布、特殊的硬件、需要自己控制内存分配），那时才值得自己动手；在例外出现之前，先把标准库用对。

算法库和容器库是一对搭档：**容器负责用某种形式表示数据，算法负责对这些数据做操作**；两者能接在一起的原因，就是本章第 1 至 6 节讲的**迭代器**——算法不直接认容器，它只认迭代器。所以 `std::sort` 不关心你给它的是一段 `std::array`、一段 `std::vector`，还是别的什么，它只要求"从这个位置到那个位置"这一对迭代器。

## 8 第一个算法：std::sort

算法库的入口是头文件 `<algorithm>`，`std::sort` 就声明在这里。它最基本的用法是：

```cpp
template<class RandomIt>
void sort(RandomIt first, RandomIt last);
```

先看它做了什么，再看这个签名里的每个词。例程 `E:\CPP_Code\CppFromScratch\ch13_stl_algorithms\sort_int\sort_int.cpp`：

```cpp
#include <algorithm>
#include <array>
#include <iostream>

void print(auto container)
{
    for (auto value : container)
    {
        std::cout << value << " ";
    }
    std::cout << std::endl;
}

int main()
{
    std::array<int, 7> myArray {5, 3, 2, 1, 2, 85, 2};

    std::cout << "=== before sort ===" << std::endl;
    print(myArray);

    std::sort(myArray.begin(), myArray.end());

    std::cout << "=== after sort ===" << std::endl;
    print(myArray);

    return 0;
}
```

打印函数写成 `void print(auto container)`：参数写 `auto` 就是第 05 章的函数模板的一种简写（C++20 起可以直接这样写），于是同一个 `print` 既能打印 7 个元素的数组，也能打印 6 个元素的数组，不需要为每种长度各写一份。这里的参数**没有** `&`，也就是第 04 章的按值传参——调用时整个数组会被复制一份。元素少时无所谓；等第 08 章学了按引用传参，这里可以去掉这次复制。

三点要看清：

- **排序是就地完成的。** `std::sort` 直接改动 `myArray` 里的元素，不返回任何值。所以不能写成 `myArray = std::sort(...)`，编译会报 `error: conversion from 'void' to non-scalar type ... requested`。
- **首尾两个参数都是迭代器。** `myArray.begin()` 指向第一个元素，`myArray.end()` 指向**最后一个元素的后面一个位置**。这一对迭代器表示要排序的范围，正好覆盖整个数组。
- **排序不会改变元素个数。** 它是把原来的元素按要求重新排列，不会删掉重复的值。所以排序前后的元素个数必须一样，这一点正好可以用来检查有没有写错范围。

## 9 范围是左闭右开的 [first, last)

上一节的 `last` 指向的是"最后一个元素的**下一个**位置"，它本身不参与排序。这个约定在本章第 2 节讲迭代器时已经出现过，写公式就是：

$$[\text{first}, \text{last})$$

左端的方括号表示包含 `first` 指向的元素，右端的圆括号表示不包含 `last` 指向的元素。为什么要这么别扭？因为它带来两个好用的性质：`last - first` 正好等于这段范围里的元素个数；而且相邻两段范围可以首尾相接而不重叠——`[begin, mid)` 和 `[mid, end)` 拼起来就是 `[begin, end)`。

既然范围是由两个迭代器给出的，就完全不必是"整个容器"：给 `begin()` 加上偏移量就能掐出其中一段。例程 `E:\CPP_Code\CppFromScratch\ch13_stl_algorithms\sort_subrange\sort_subrange.cpp` 只排中间三个元素：

```cpp
int main()
{
    std::array<int, 6> myArray {9, 4, 7, 1, 3, 8};

    std::cout << "=== before sort ===" << std::endl;
    print(myArray);

    std::sort(myArray.begin() + 1, myArray.begin() + 4);

    std::cout << "=== after sort [begin + 1, begin + 4) ===" << std::endl;
    print(myArray);

    return 0;
}
```

（`print` 函数与上例相同，这里只保留 `main` 以突出范围参数。）

`begin() + 1` 指向下标 1 的元素（值 4），`begin() + 4` 指向下标 4 的元素（值 3）。因为 `last` 不参与排序，被排序的是下标 **1、2、3** 这三个元素（值 4、7、1），它们被排成 1、4、7。下标 0 的 9 和下标 4、5 的 3、8 原地不动。

这里有个容易犯的错：**只排了一段，却以为整个数组都排好了。** 排序后数组是 `9 1 4 7 3 8`，从头到尾看并不是升序。要整体有序就必须让范围覆盖整个容器。

## 10 为什么 std::sort 要求随机访问迭代器

模板签名的注释里，参数类型写的是 `RandomIt`——这个名字不是随便起的，它表示**随机访问迭代器**（random access iterator）。本章第 6 节讲过迭代器是分级的：`std::array`、`std::vector` 给出的迭代器是随机访问级，能 `+ n`、能 `-`、能比较大小；而链式结构的迭代器只能一步一步往前走。

`std::sort` 为什么非要随机访问级？因为它不能只靠单向扫描工作：它要在范围内反复地"取中间位置、把元素分成两半、再对两半递归处理"，这个过程中一直在做"跳到第 k 个元素"这种随机跳转。只支持 `++` 的迭代器根本表达不了这种访问。所以：

- 给 `std::sort` 传链表的迭代器会直接编译失败（错误信息是一堆模板匹配失败的细节，核心是"不满足随机访问迭代器的要求"）；
- 链式结构如果想排序，用它自己的成员函数 `std::list::sort`，那是另一套实现。

**复杂度。** `std::sort` 的最坏与平均情况都要做 $O(N\log N)$ 次比较（libstdc++ 用的是内省排序 introsort），其中 $N$ 是范围里的元素个数。这个数字的来历是：每次把范围一分为二只需要 $O(N)$ 的划分工作，分成 $\log N$ 层，所以总量是 $N\log N$。对 7 个元素这种规模，排序快得看不出来；但对一百万个元素，$N\log N$ 和 $N^2$ 的差距是数量级的。

**不稳定的排序。** 所谓"稳定"，指相等元素的相对次序在排序后保持不变。`std::sort` **不保证**这一点：例程里三个 2，排序后仍然彼此相邻，但它们之间的先后关系没有任何保证。如果相等元素的原始次序有意义（比如先按分数排、再按班级排，希望同分的保持原先的输入顺序），要用 `std::stable_sort`，它牺牲一点速度换取稳定性。这两种算法的用法完全一样，把名字换掉即可。

## 11 C++20 的范围算法

只用 `std::sort` 已经能干活，但每次都要写一对迭代器还是有点啰嗦：绝大多数时候我们想做的正是"把这个容器排一下"，写 `myArray.begin(), myArray.end()` 只是为了把这件事说清楚，还平白多出写错的机会（两个迭代器写反、算偏移量时多算一格）。

C++20 给算法库加了一层**范围**版本：同一批算法在 `std::ranges` 命名空间下又出现了一次，这些新版本可以**直接把容器整体接收进去**。这就是"受限算法"的想法——用概念（concept）把参数的要求写进签名里，既能接收整个范围，也能在出问题时给出更清楚的报错。例程 `E:\CPP_Code\CppFromScratch\ch13_stl_algorithms\ranges_sort\ranges_sort.cpp`：

```cpp
#include <algorithm>
#include <array>
#include <iostream>

int main()
{
    std::array<int, 7> myArray {5, 3, 2, 1, 2, 85, 2};

    std::ranges::sort(myArray);

    std::array<int, 6> subset {9, 4, 7, 1, 3, 8};

    std::ranges::sort(subset.begin() + 1, subset.begin() + 4);

    return 0;
}
```

（上例省略了打印语句，完整源码见例程。）

两个要点：

- `std::ranges::sort(myArray)` 做的事和 `std::sort(myArray.begin(), myArray.end())` **完全一样**，只是写法更短、更贴近"把容器排一下"这个意图。
- 范围版本并不是只能收容器：它同样有接收一对迭代器的重载。需要只排一部分时，就退回和 `std::sort` 相同的写法，效果不变。

这两套算法都声明在 `<algorithm>` 里，不需要额外的头文件。区别在编译器支持：范围算法是 C++20 才有的，用低于 C++20 的标准去编译 `std::ranges::sort(a);` 会报 `error: 'std::ranges' has not been declared`。本课程的编译命令统一带 `-std=c++20`，就是为了让这些新东西立即可用。

到这里，`std::sort` 已经能正确地把数据排好。但一个程序只有"结果正确"是不够的——它还得在合理的时间里给出结果。同一批算法，其实还能跑得更快。

## 12 正确之外，还有快

到上一节为止，本章的重心一直是"让程序算对"：迭代器要用对、范围要给对、排序结果要能核对。一个几秒钟就该跑完的任务如果花了两三分钟，无论结果多正确都不可用。

谈性能先要看清瓶颈在哪里。今天常见的 CPU 提供了两种并行资源：

- **多核**：一颗处理器里有多个核心，可以同时执行不同的任务。把一份工作切成若干块、让多个核心各算一块，就能缩短总时间。
- **SIMD 指令**（Single Instruction Multiple Data，单指令多数据）：一条指令同时对多个数据做同样的运算。例如向量加法里"逐元素相加"这种操作，一条 SIMD 指令可以顶替好几条普通指令。

要利用这两样东西，传统做法是自己开线程、切数据、合并结果，代码复杂且容易出错。而本节要讲的做法几乎不需要付出这种代价：**把本章前面各节一直在用的标准库算法加上一个"执行策略"参数，让库替你决定怎么并行**。同一个算法、同一行调用，加一个参数就能从单线程执行变成多线程加 SIMD 执行。

## 13 四种执行策略

执行策略定义在头文件 `<execution>` 里，名字都在 `std::execution` 命名空间下，共四种：

| 策略 | 含义 | 引入版本 |
| --- | --- | --- |
| `std::execution::seq` | 不允许并行，也不允许向量化：就是顺序执行 | C++17 |
| `std::execution::par` | 允许并行：算法可以由多个线程同时处理不同部分 | C++17 |
| `std::execution::par_unseq` | 允许并行，并且允许在单个线程内使用向量指令（SIMD） | C++17 |
| `std::execution::unseq` | 只允许向量化，不使用多线程 | C++20 |

读这张表有一个重点：**策略是"许可"，不是"命令"**。写 `par` 的意思是"我允许你用多线程"，库可以按自己的判断决定实际怎么做；写 `seq` 则是明确禁止并行化与向量化——它的行为与不写策略完全一样，所以常用作对照基准。

使用方式很直接：把策略作为调用时的第一个实参。以前面各节用过的标准库算法为例，`std::accumulate` 的并行版本是 `std::reduce`（定义在 `<numeric>`）：

```cpp
std::reduce(std::execution::par, first, last, init);   // 策略在最前面
```

`par_unseq` 带来一条额外的硬性限制，**必须记住**：传给算法的函数里不能加锁（使用互斥量）、不能分配内存、不能依赖任何共享状态。原因是同一个线程里可能同时有多个元素正在被处理，这些操作的顺序完全不保证。所以下面这类写法在 `par_unseq` 下是错的：

```cpp
// 错误示范：在并行（尤其是 par_unseq）下这是数据竞争
std::for_each(std::execution::par_unseq, v.begin(), v.end(),
              [&total](int value)
              {
                  total += value;      // 多个线程同时改 total，结果不可预测
              });
```

需要"每个元素各自算，最后合并"时，正确做法是让算法本身负责合并（`std::reduce`）或者让每个元素只依赖自己（`std::transform`），而不是让多个执行体去改同一个变量。

还有一条容易踩的坑：**C++20 的 `std::ranges` 版本算法不接受执行策略**。`std::ranges::sort(v, std::execution::par)` 是编译不过的（后面错误表里有原文），要用并行就必须用经典迭代器版本 `std::sort(std::execution::par, first, last)`。

## 14 给 `reduce` 加策略

例程 `E:\CPP_Code\CppFromScratch\ch40_parallel_algorithms\reduce_seq_vs_par\reduce_seq_vs_par.cpp` 用一个约 6700 万元素的整数向量（`1 << 26`，约 256 MB）做累加，三种策略各跑 10 轮：

```cpp
const std::size_t element_count = std::size_t {1} << 26;
const int rounds = 10;

long long seq_checksum = 0;
for (int round = 0; round < rounds; ++round)
{
    seq_checksum += std::reduce(std::execution::seq, my_vector.begin(), my_vector.end(), 0LL);
}
```

运行结果：

```text
vector size = 67108864
rounds = 10
=== Demo A: sum with the sequential policy ===
seq checksum = 2013265860
=== Demo B: sum with the parallel policy ===
par checksum = 2013265860
=== Demo C: sum with the parallel unsequenced policy ===
par_unseq checksum = 2013265860
=== Demo D: the three policies agree ===
all checksums equal: 1
```

四点说明：

1. **`std::reduce` 与 `std::accumulate` 做的是同一件事**：把区间里的元素累加到一个初值上。区别是 `reduce` 允许以任意顺序合并元素（这正是它能并行、能向量化的前提），因此它要求这个合并操作满足结合律与交换律。整数加法满足，所以三种策略得到的结果完全相同。
2. **初值字面量决定累加类型**。`std::reduce` 的返回类型由初值决定：这里的 `0LL` 是 `long long` 字面量，于是每轮结果以 `long long` 返回，再累加到同样为 `long long` 的 checksum 上。**在这条例程里，即便把初值写成 `0`（`int`），结果也不会变**——单轮和是 201326586、十轮合计 2013265860，都还在 `int` 的范围内。初值的意义在于**决定累加用什么类型**：当总和确实可能超出 `int` 时（比如第 15 节那条 `sorted sum ≈ 2.1e11`），就必须显式写成 `long long` 字面量，否则会溢出截断。这与第 02 章的类型规则一致：结果类型由参与运算的类型决定，不是由数据大小决定。
3. **重复 10 轮是为了让耗时差异在 `time` 命令下看得出来**。单轮归约只有百毫秒量级，混在进程启动和内存分配的时间里不容易分辨；重复几轮之后差距就明显了。程序本身只打印求和结果，所以输出仍然完全确定。
4. **`par` 与 `par_unseq` 的结果与 `seq` 逐位相同**。并行改变的是"谁算哪一段"，不改变确定性输入对应的输出。

本机（GCC 16.1.0，`-g`，未开 `-O2`）实测：只保留顺序那 10 轮的版本耗时约 1.63 s；只保留并行与并行向量化两段的版本耗时约 0.44 s（其中还包括约 0.3 s 的填充与分配开销）。真正被策略改变的那部分从约 1.3 s 降到约 0.13 s——**一行调用里多了一个参数，量级上的差别就出来了**。

## 15 并行不只用于累加

同一套机制可以用在别的算法上。例程 `ch40_parallel_algorithms\par_sort_transform\par_sort_transform.cpp` 在一个约 400 万元素的向量上依次做了三件事：

```cpp
// 并行排序
std::sort(std::execution::par, my_vector.begin(), my_vector.end());

// 并行就地改写：每个元素只依赖自己
std::transform(std::execution::par_unseq, my_vector.begin(), my_vector.end(), my_vector.begin(),
               [](int value)
               {
                   return value * 2 + 1;
               });

// 并行计数
long long even_count = std::count_if(std::execution::par, my_vector.begin(), my_vector.end(),
                                     [](int value)
                                     {
                                         return value % 2 == 0;
                                     });
```

运行结果：

```text
vector size = 4194304
=== Demo A: sort with the parallel policy ===
first five: 0 0 0 0 0
last five: 100002 100002 100002 100002 100002
sorted sum = 209719315253
=== Demo B: transform with the parallel unsequenced policy ===
sum after transform (2x + 1) = 419442824810
=== Demo C: count with the parallel policy ===
even numbers after transform = 0
=== Demo D: every step was reproducible ===
checksum = 419442824810
```

几个要点：

- **`std::sort` 是并行的理想对象**，因为它"结果唯一"：无论区间怎么切、各段怎么排序、最后怎么合并，排好之后的序列只有一种正确答案。本机实测 400 万元素的排序：顺序约 373 ms，并行约 42 ms。
- **`std::transform` 就地改写是安全的**，前提是每个元素只依赖自己（这里 `f(x) = 2x + 1`）。危险的是让这个函数去读写别的元素或者任何共享状态。
- **数据的生成方式必须是确定的**。例程用 `(i * 2654435761u) % 100003u` 造出一串固定值，同一个下标永远得到同一个数，所以每次运行的输出完全一样。这一点对并行程序尤其重要：**并行已经引入了"顺序不确定"，输入的确定性就是结果可比对的前提**。
- **`Demo C` 的结果是 0，这是可以预判的**。`2x + 1` 一定是奇数，所以变换后偶数个数必然为 0。这种"已知答案的复核"是验证并行代码的常规手段：一旦出现别的数字，就说明逻辑有问题或者出现了数据竞争。
- **`Demo D` 的校验和与 `Demo B` 的总和相等**，说明几个步骤都能重复得到同一结果。

## 16 让程序真的并起来：TBB 与 `-ltbb12`

标准只规定了执行策略的语义，没规定实现怎么把线程开出来。GCC 的做法是**把并行算法交给 TBB 实现**：

- **TBB**（Threading Building Blocks）是线程构建块库，`libstdc++` 里的并行算法后端就建立在它之上；
- 因此从 GCC 9 起，只要使用 `<execution>` 与执行策略，**就必须在链接时把 TBB 连上**；
- 在 MSYS2 UCRT64 上，TBB 的库文件名是 `libtbb12.dll.a`（TBB 2023.0.0），所以链接参数是 **`-ltbb12`**，不是 `-ltbb`。

正确的编译命令：

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g par_sort_transform.cpp -ltbb12 -o par_sort_transform.exe
```

写错参数会发生什么，实测如下：

- 写成 `-ltbb`：`cannot find -ltbb: No such file or directory`，随后是 `collect2.exe: error: ld returned 1 exit status`。MSYS2 里没有名为 `libtbb.dll.a` 的文件，`-ltbb` 自然找不到。
- 完全不写链接参数：只得到一行 `collect2.exe: error: ld returned 1 exit status`（这个数字也可能是 `5`），**不告诉你缺的是哪个库**。这是本章最难查的一类错误，因为它看起来像是代码问题。
- 编译通过了还不够，**运行时还要能找到 `libtbb12.dll`**。这个动态库在 `E:\msys64\ucrt64\bin` 下，如果它不在运行时的搜索路径里，程序会启动失败：Git Bash 下表现为没有任何输出、退出码 127；Windows 上对应的失败码是 `0xC0000135`（找不到 DLL）。

安装 TBB 的命令（MSYS2 UCRT64 环境）：

```text
pacman -S mingw-w64-ucrt-x86_64-tbb
```

还有一点要留心：**"能编译能运行"不等于"真的并行了"**。如果某个平台的实现缺少并行后端，加了策略的程序仍然能编译运行，只是策略被忽略、实际仍在单线程执行。所以判断并行是否生效要看耗时对比，而不是看代码里有没有写 `par`。本节两个例程都安排了对照：同一个程序里先跑 `seq` 再跑 `par`，或者把策略换掉重新编译，用 `time` 命令比较。

## 17 并行程序的输出必须仍然可核对

并发程序的执行顺序天生不确定，但这不等于"输出可以随便"。要求是：**输出里与顺序无关的内容必须完整、正确、可复现**。具体做法有三种，本节都用到了：

1. **只打印与顺序无关的量**：总和、计数（例程中的 `sorted sum`、`even numbers after transform`）。
2. **先汇总、再打印事先排好序的结果**：排序后的前五个与后五个元素（`first five` / `last five`）。
3. **用 `seq` 与 `par` 互相校验**：同一个输入跑两遍，比较结果是否相等（`all checksums equal: 1`、`results match` 这类输出）。

反过来说，下面这些写法会让输出无法核对，属于应当避免的：

- 让传给算法的函数去修改共享变量（数据竞争）：结果取决于线程调度，可能每次不同，也可能看起"正常"却在某个规模下出错；
- 在 `par_unseq` 下加锁或分配内存：允许向量化的策略明确禁止这些操作；
- 用不满足结合律的操作配合 `reduce`：最典型的是浮点加法——`(a + b) + c` 与 `a + (b + c)` 的舍入结果可能不同，于是"并行和"与"顺序和"会有微小差异。整数运算没有这个问题，但对浮点数据必须把初值和累加类型都看清楚。

还有一条性能上的提醒：**并行不是越多越好**。切分任务、启动线程、合并结果都要花时间，元素很少时这些开销会盖过收益，甚至比顺序执行更慢。数据量足够大时再考虑并行，并且用 `time` 验证，而不是凭感觉。

## 18 动手实验

### 实验一：`begin()`/`end()` 遍历

例程都在 `E:\CPP_Code\CppFromScratch\ch12_iterators\` 下，四个程序各占一个文件夹，每个 `.cpp` 都是自包含的单文件。四个程序都以 `std::array<int, 5> myArray {1, 2, 3, 4, 5};` 开场，便于互相对照。

```text
cd "E:/CPP_Code/CppFromScratch/ch12_iterators/iterator_basic"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g iterator_basic.cpp -o iterator_basic.exe
./iterator_basic.exe
```

**预期输出**（第一行末尾有一个空格）：

```text
=== Demo A: iterating with begin() and end() ===
1 2 3 4 5 
*(end() - 1) = 5
```

**验收标准**：输出与上面逐字符一致，`-Wall` 无警告。

**改值实验**：把数组初值改成 `{10, 20, 30, 40, 50}`，先预测两行输出再运行，应为：

```text
=== Demo A: iterating with begin() and end() ===
10 20 30 40 50 
*(end() - 1) = 50
```

**边界实验**：把循环条件改成 `it <= myArray.end()`，重新编译运行。`-Wall` **不会**报任何警告，但输出会多出一个每次都不同的数字（例如某次的 `117`，再次运行可能变成别的值）——因为 `it` 走到 `end()` 时解引用访问了数组之外的内存，属于未定义行为。看完把条件改回 `it != myArray.end()`。

### 实验二：解引用可写

```text
cd "E:/CPP_Code/CppFromScratch/ch12_iterators/iterator_write"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g iterator_write.cpp -o iterator_write.exe
./iterator_write.exe
```

**预期输出**（每行末尾有一个空格）：

```text
=== Demo D: writing through an iterator ===
before: 1 2 3 4 5 
after : 10 20 30 40 50 
```

**验收标准**：`after` 行正好是 `before` 行的每个元素乘 10，`-Wall` 无警告。

**改值实验**：把 `*it *= 10;` 改成 `*it += 100;`，预测 `after` 行应为 `101 102 103 104 105 `；再把这一行改成 `*it = 0;`，`after` 行应为 `0 0 0 0 0 `。两次都说明 `*it` 落在容器真正的元素上，不是副本。

### 实验三：反向遍历

```text
cd "E:/CPP_Code/CppFromScratch/ch12_iterators/iterator_reverse"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g iterator_reverse.cpp -o iterator_reverse.exe
./iterator_reverse.exe
```

**预期输出**（每行末尾有一个空格）：

```text
=== Demo B: forward and reverse ===
forward: 1 2 3 4 5 
reverse: 5 4 3 2 1 
```

**验收标准**：`reverse` 行与 `forward` 行元素顺序完全相反，`-Wall` 无警告。

**改值实验**：把数组初值改成 `{2, 4, 6, 8, 10}`，`forward` 行应为 `2 4 6 8 10 `、`reverse` 行应为 `10 8 6 4 2 `。另一个可以立刻做的改动：**先把 `reverse` 那一行的条件改成 `it <= myArray.rend()` 试试**——它会给出和实验一一样的教训：编译无警告，结果不可信。看完还原。

### 实验四：偏移与子区间

```text
cd "E:/CPP_Code/CppFromScratch/ch12_iterators/iterator_offset"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g iterator_offset.cpp -o iterator_offset.exe
./iterator_offset.exe
```

**预期输出**（每行末尾有一个空格）：

```text
=== Demo C: offsets and sub-ranges ===
begin()      to end()    : 1 2 3 4 5 
begin() + 1  to end()    : 2 3 4 5 
begin() + 2  to end() - 1: 3 4 
rbegin()     to rend()   : 5 4 3 2 1 
rbegin() + 2 to rend()   : 3 2 1 
```

**验收标准**：五行区间与说明相符，`-Wall` 无警告。

**改值实验**：把第三行的 `myArray.begin() + 2` 改成 `myArray.begin() + 3`，区间变成 `[begin()+3, end()-1)`，即只含下标 3 一个元素，预期输出 `4 `（一个数字加一个空格）。把最后一行的 `rbegin() + 2` 改成 `rbegin() + 4`，它指向下标 0 上的 `1`，输出应为 `1 `。

### 实验五：排序整个数组

例程在 `E:\CPP_Code\CppFromScratch\ch13_stl_algorithms\` 下，三个程序各占一个文件夹，都不依赖其他文件。

编译运行命令统一是这个形状（三行，`cd` 到例程目录后编译再运行）：

```text
cd "E:/CPP_Code/CppFromScratch/ch13_stl_algorithms/sort_int"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g sort_int.cpp -o sort_int.exe
./sort_int.exe
```

后面三个实验只把路径和文件名换掉。

源码 `sort_int\sort_int.cpp`，在 `main` 里创建 `std::array<int, 7> myArray {5, 3, 2, 1, 2, 85, 2};`，排序前后各打印一次。

**预期输出**（注意每个数字后面跟一个空格，所以两行数据行的行末也各有一个空格）：

```text
=== before sort ===
5 3 2 1 2 85 2 
=== after sort ===
1 2 2 2 3 5 85 
```

**验收标准**：两行数据分别是 `5 3 2 1 2 85 2 ` 和 `1 2 2 2 3 5 85 `（含行末空格），升序成立，三个 2 一个不少，编译 `-Wall` 无警告。

**改值实验**：把初值改成 `{3, 1, 2}`，同时把类型改成 `std::array<int, 3>`。预测输出的第二行数据是什么，再编译运行核对（应为 `1 2 3 `）。改回原值，确认输出恢复。

### 实验六：只排一部分

源码 `sort_subrange\sort_subrange.cpp`，排序范围是 `[myArray.begin() + 1, myArray.begin() + 4)`。

**预期输出**：

```text
=== before sort ===
9 4 7 1 3 8 
=== after sort [begin + 1, begin + 4) ===
9 1 4 7 3 8 
```

**验收标准**：第二行数据为 `9 1 4 7 3 8 `。能指着它说出被排序的是哪三个元素（下标 1、2、3），以及下标 4 的 3 为什么没动（它是 `last` 指向的元素，不参与排序）。

**改值实验**：把第二个实参改成 `myArray.begin() + 6`，也就是让范围变成整个数组，预测并核对输出——这次整行应当是整体升序 `1 3 4 7 8 9 `。想清楚为什么下标 0 的 9 这次会被排到末尾，然后改回原样。

### 实验七：范围版本的写法

源码 `ranges_sort\ranges_sort.cpp`，用 `std::ranges::sort` 分别排整个容器和一段范围。

**预期输出**：

```text
=== std::ranges::sort on the whole container ===
5 3 2 1 2 85 2 
1 2 2 2 3 5 85 
=== std::ranges::sort on a subrange ===
9 4 7 1 3 8 
9 1 4 7 3 8 
```

**验收标准**：四行数据与上面逐字符一致；能说出 `std::ranges::sort(myArray)` 等价于哪一句 `std::sort` 调用。

**改值实验**：把第二处的 `std::ranges::sort(subset.begin() + 1, subset.begin() + 4);` 换成 `std::ranges::sort(subset);`，预测并核对输出（整行升序 `1 3 4 7 8 9 `）。这样就能看清"范围版本"的两种调用形式只是同一件事的两种写法。

### 实验八：三种执行策略的累加

例程在 `E:\CPP_Code\CppFromScratch\ch40_parallel_algorithms\` 下，两个程序各占一个文件夹，都是单文件自包含。**两者的编译命令都必须带 `-ltbb12`**。

`reduce_seq_vs_par\reduce_seq_vs_par.cpp` 在约 6700 万个整数上分别用 `seq`、`par`、`par_unseq` 各累加 10 轮，最后比较三者是否相等。

```text
cd "E:\CPP_Code\CppFromScratch\ch40_parallel_algorithms\reduce_seq_vs_par"
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g reduce_seq_vs_par.cpp -ltbb12 -o reduce_seq_vs_par.exe
./reduce_seq_vs_par.exe
```

**预期输出**：

```text
vector size = 67108864
rounds = 10
=== Demo A: sum with the sequential policy ===
seq checksum = 2013265860
=== Demo B: sum with the parallel policy ===
par checksum = 2013265860
=== Demo C: sum with the parallel unsequenced policy ===
par_unseq checksum = 2013265860
=== Demo D: the three policies agree ===
all checksums equal: 1
```

**验收标准**：输出逐字符与上面一致；`-Wall` 无警告；`all checksums equal: 1` 说明三种策略给出同一个结果。

**耗时验证**：用 `time ./reduce_seq_vs_par.exe` 运行整个程序（本机约 1.8 s）。想看单段耗时，可以临时把 `Demo B`、`Demo C` 两段的 `for` 循环注释掉再编译运行：只剩顺序归约时约 1.6 s，只剩并行两段时约 0.44 s（其中约 0.3 s 是向量填充的开销）。耗时数字每台机器不同、每次运行也会有波动，但结果的数值始终相同。

**改值实验**：把 `const int rounds = 10;` 改成 `20`，重新编译运行。预期输出里的 `rounds = 20`，三个 checksum 都变成 `4026531720`（正好是原来的 2 倍），`all checksums equal` 仍为 `1`。

### 实验九：并行排序、改写与计数

`par_sort_transform\par_sort_transform.cpp` 在约 400 万元素的向量上并行排序、并行改写、并行计数。**注意 `-ltbb12` 写错或漏掉的后果**（见本章第 16 节）。

```text
cd "E:\CPP_Code\CppFromScratch\ch40_parallel_algorithms\par_sort_transform"
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g par_sort_transform.cpp -ltbb12 -o par_sort_transform.exe
./par_sort_transform.exe
```

**预期输出**：

```text
vector size = 4194304
=== Demo A: sort with the parallel policy ===
first five: 0 0 0 0 0
last five: 100002 100002 100002 100002 100002
sorted sum = 209719315253
=== Demo B: transform with the parallel unsequenced policy ===
sum after transform (2x + 1) = 419442824810
=== Demo C: count with the parallel policy ===
even numbers after transform = 0
=== Demo D: every step was reproducible ===
checksum = 419442824810
```

**验收标准**：输出逐字符与上面一致；`-Wall` 无警告；能说明为什么 `Demo C` 必然输出 `0`，以及为什么 `Demo D` 的校验和必然等于 `Demo B` 的总和。多次运行程序，输出应完全一致。

**改值实验**：把 `element_count` 从 `std::size_t {1} << 22` 改成 `std::size_t {1} << 24`（元素数变成 4 倍），重新编译运行。预期输出变成 `vector size = 16777216`，`first five` 与 `last five` 仍是 `0 0 0 0 0` 和 `100002 100002 100002 100002 100002`（数据取值范围没变），而 `sorted sum = 838877303159`、`sum after transform (2x + 1) = 1677771383534`、`checksum = 1677771383534`。同时用 `time` 看总耗时：本机从约 0.15 s 增到约 0.36 s。排序本身的差距更明显——本机实测 400 万元素时顺序排序约 373 ms、并行排序约 42 ms；1600 万元素时顺序排序约 1538 ms、并行排序约 155 ms。
