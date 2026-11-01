# 07 vector：动态数组与元素添加

上一篇：[[06 迭代器、算法与并行 STL]]
下一篇：[[08 引用与传参]]

## 学习目标

完成本章后，你应当能够：

1. 创建并初始化一个 `std::vector`，说出它与 `std::array` 在"长度何时确定"上的区别。
2. 用 `push_back` 与 `pop_back` 在运行时增删元素，并认出空容器上会触发未定义行为的操作。
3. 区分 `size` 与 `capacity`，用 `reserve` 提前预留容量。
4. 说出 `push_back` 两个重载的分工，预判一次添加走复制还是移动。
5. 说出 `emplace_back` 省掉的是哪一步，据此为添加元素的场景选对方法。

## 1 固定长度的容器不够用

第 03 章的 `std::array<int, 5>` 把元素个数写进了类型里：`std::array<int, 5>` 和 `std::array<int, 6>` 是**两个不同的类型**。这带来两个好处——长度是编译期常量，编译器可以据此分配内存、检查越界；也带来一个硬限制：**要放几个元素，写代码的时候就必须定下来**。

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

打印函数 `void print(std::vector<int> values)` 的参数**没有** `&`，所以调用时整个 vector 会被复制一份——这里只是打印，这份复制完全是白花的。第 08 章会给出解决办法（按引用传参），本章先保持写法一致。

## 3 像数组一样访问元素

`std::vector` 的大部分访问接口就是 `std::array` 那一套，用法一模一样：

- `size()`：当前元素个数。返回类型是无符号整数 `size_t`（不是 `int`），这一点后面会专门提。
- `front()` / `back()`：取第一个、最后一个元素的引用。
- `operator[]`：`myVector[0]` 那种写法，**不做边界检查**。
- `at(n)`：按下标取元素，**会做边界检查**，越界时会报告错误（异常机制在后续章节展开）。
- `data()`：拿到指向首个元素的指针；`begin()` / `end()`：第 06 章那对迭代器，同章的 `std::sort(myVector.begin(), myVector.end())` 可以直接用在这个容器上。

`[]` 和 `at` 的选择很直接：下标一定合法时用 `[]`，它更快也更常见；不确定时才用 `at`，宁可多一次检查也不要不声不响地读错内存。

这里有一个必须明确的边界：**对空 vector 调用 `front()`、`back()` 或任何下标都是未定义行为**。空的 `std::vector<int>` 里没有任何元素，`myVector[0]` 不是"返回 0"或"返回空"，而是访问了不属于你的内存——它可能碰巧不崩，也可能读出垃圾值，还可能在别的地方引发难以定位的故障。所以在按下标访问之前，先确认 `size()` 够大。

## 4 增删元素：push_back 与 pop_back

真正让 `std::vector` 区别于 `std::array` 的，是它能在运行时改变大小：

- **`push_back(值)`**：把一个新元素追加到末尾，`size` 加 1。
- **`pop_back()`**：移除末尾那一个元素，`size` 减 1。

例程 `E:\CPP_Code\CppFromScratch\ch14_vector\push_pop\push_pop.cpp` 演示了这一对操作，输出与第 03 章那种"打印—改动—再打印"的节奏一致：

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

为什么不让两者一直相等？因为申请内存这件事很贵：从自由存储区要一块更大的内存，把原来的元素**逐个搬过去**，再把旧内存还掉（第 09 章会看到这套动作的细节）。如果每次 `push_back` 都刚好扩一个位置，那么第 $k$ 次添加都要搬 $k-1$ 个元素，添加 $N$ 个元素总共要搬 $\frac{N(N-1)}{2}$ 次，也就是 $O(N^2)$——插入本该很便宜的操作会变得非常慢。

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

把这张表读成一句话：`size` 每次加 1，`capacity` 只在"已经用满"时才跳一次，而且**大致按 2 倍增长**——0 → 1 是首次分配的例外，从 1 起依次是 1、2、4、8、16。前面看到 size 和 capacity 相等（1 和 1、2 和 2、4 和 4、8 和 8）的那些时刻，就是下一次 `push_back` 必须重新分配的时刻；其他时候空位还够，加进去不花钱。

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

`std::vector` 还有 `insert`、`erase`、`resize`、`clear` 等成员函数，分别对应在中间插删、改变长度、清空等操作。它们涉及到元素的移动和迭代器失效的细节，等到用得上时（本章第 7 节起讲 `push_back` 与 `emplace_back` 的区别、后续讲类和构造函数的章节）再展开。

## 7 `push_back`：先有对象，再把它放进去

本节要用到三个后续章节的概念，先给出最小前置，完整机制见第 12、14 章：

- **右值引用 `T&&`**：一种专门绑定"临时对象或即将被搬走的对象"的引用类型，写作 `T&&`；
- **移动构造**：不再逐字节复制源对象，而是把它的资源直接接手过来，形如 `S(S&& other)`，通常比拷贝构造便宜得多；
- **`noexcept`**：写在移动构造函数末尾的承诺——它不抛异常。`vector` 只有在移动构造是 `noexcept` 时才敢用它把元素搬到新内存（本章第 10 节会看到后果）。

第 4 节已经用 `push_back` 完成过追加元素，但它的完整含义要到构造、拷贝与移动构造（第 12、14 章）都登场之后才能看清：`push_back` 不只是"往末尾塞一个元素"，而是**在容器的内存里构造一个新元素**；构造一个对象有多少条路，这里就有多少种可能的开销。本节先把这几条路认清，随后再认识一条更直接的路——`emplace_back`。

例程 `E:\CPP_Code\CppFromScratch\ch30_push_vs_emplace\push_back_forms\push_back_forms.cpp` 里的类型仍然用打印来暴露每一次构造（节选，注释略）：

```cpp
struct S
{
    int x = 0;

    explicit S(int new_x) : x(new_x)
    {
        std::cout << "Constructor! x = " << x << std::endl;
    }

    S(const S& other) : x(other.x)
    {
        std::cout << "Copy Constructor! x = " << x << std::endl;
    }

    S(S&& other) noexcept : x(0)
    {
        std::swap(x, other.x);
        std::cout << "Move Constructor! x = " << x << std::endl;
    }
};
```

`push_back` 有两个重载，它们的参数类型要等右值引用与移动构造（第 14 章）讲完才说得透，这里先把分工写全：

| 重载 | 参数 | 对新元素做的事 |
| --- | --- | --- |
| `void push_back(const T& value)` | `const` 左值引用 | 用 `value` **拷贝构造**新元素 |
| `void push_back(T&& value)` | 右值引用 | 用 `value` **移动构造**新元素 |

于是三种写法对应三条路径：

| 写法 | 实参的值类别 | 走的重载 | 输出 |
| --- | --- | --- | --- |
| `v1.push_back(s)` | 左值 | `push_back(const S&)` | `Constructor!` + `Copy Constructor!` |
| `v2.push_back(std::move(t))` | 右值 | `push_back(S&&)` | `Constructor!` + `Move Constructor!` |
| `v3.push_back(S(30))` | 右值（临时对象） | `push_back(S&&)` | `Constructor!` + `Move Constructor!` |

完整输出：

```text
=== Demo A: push_back with a named lvalue (the copying overload) ===
Constructor! x = 10
Copy Constructor! x = 10
=== Demo B: push_back with std::move (the moving overload) ===
Constructor! x = 20
Move Constructor! x = 20
t.x after the move: 0
=== Demo C: push_back with a temporary (it is already an rvalue) ===
Constructor! x = 30
Move Constructor! x = 30
=== Demo D: all three vectors own the value we asked for ===
v1.size() = 1, v1[0].x = 10
v2.size() = 1, v2[0].x = 20
v3.size() = 1, v3[0].x = 30
```

### 7.1 始终存在两块内存

把三条路径放在一起看，会发现一件共同的事：**不管走哪条路，都要先有一个"外面的对象"，再想办法把它弄进容器的内存里。**

- Demo A：`s` 建在 `main` 的栈上，`vector` 在自己的堆内存里拷出一份副本，两块内存内容相同、互相独立。
- Demo B：`t` 还是建在 `main` 的栈上，只是允许被搬空，于是资源（这里是 `x` 的值）被转移到容器里的新对象上。**对象还是构造了两块位置**，只是第二块不用从头计算，而是把第一块的东西接过来。
- Demo C：临时对象连名字都没有，看起来像是"省了一个对象"，但它依然被完整地构造出来了（第一行 `Constructor!`），然后才被搬进容器（第二行 `Move Constructor!`）。

所以 Demo D 才是这三段输出真正要说明的事：**三种写法的最终结果一模一样，`vector` 里都是一个正确的元素。差别只在"新元素是怎么来的"，而不在"它是什么"。**

顺带记住两条实用规则（第 14 章反复出现的）：

- **具名对象要搬进容器，必须显式写 `std::move`**，否则编译器按左值处理，会去找拷贝构造函数；
- **函数返回的临时对象和就地构造的临时对象本来就是右值，不用写 `std::move`**；`t.x after the move: 0` 这一行则是移动确实发生了的代价——源对象被清空了。

## 8 `emplace_back`：把参数交给容器，让它就地构造

`push_back` 有一个前提：**参数必须已经是一个对象**。哪怕最终只需要一个新元素，也得先在外面造一个再搬进来。`emplace_back` 去掉的正是这一步：它接收的不是对象，而是**构造一个元素所需要的参数**，然后直接在那块已经属于 `vector` 的内存上把对象造出来。

例程 `E:\CPP_Code\CppFromScratch\ch30_push_vs_emplace\emplace_back_in_place\emplace_back_in_place.cpp` 里的类型有两个成员，构造函数需要两个参数，这样能看清"参数被转发过去"这件事：

```cpp
struct S
{
    int x = 0;
    int y = 0;

    S(int new_x, int new_y) : x(new_x), y(new_y) { /* 打印 */ }
    S(const S& other) : x(other.x), y(other.y) { /* 打印 */ }
    S(S&& other) noexcept : x(0), y(0) { /* 交换并打印 */ }
};
```

对比两种写法：

```cpp
std::vector<S> v1;
v1.push_back(S(1, 2));     // 先造临时对象，再搬进 vector

std::vector<S> v2;
v2.emplace_back(1, 2);     // 直接把 1 和 2 交给 S 的构造函数，在 vector 里原地构造
```

对应的输出是本章最该记住的两段：

```text
=== Demo A: push_back needs a ready-made object ===
Constructor! x = 1, y = 2
Move Constructor! x = 1, y = 2
=== Demo B: emplace_back forwards the arguments instead ===
Constructor! x = 1, y = 2
```

**同样的两行参数，一个用了两次构造，一个只用了一次。** `emplace_back` 少掉的是"临时对象的构造 + 把它搬进容器"这两步，元素本身该做的那一次构造一步也省不掉。

### 8.1 `emplace_back` 的两个容易误解之处

第一，**它不等于"永远不发生拷贝或移动"**。它只是把你给的东西原样转发给构造函数。如果给它的已经是一个 `S` 对象（比如 `std::move(existing)`），那么转发过去就是"用一个右值构造"，走的自然是移动构造函数：

```text
=== Demo D: emplace_back with an existing object still moves ===
Constructor! x = 3, y = 4
Move Constructor! x = 3, y = 4
```

换句话说，`emplace_back` 去掉的是**多余的临时对象**，不是**必要的构造**。

第二，**它的返回值是新元素的引用**（C++17 起），可以接着改这个刚放进去的元素，不必再写一句 `back()` 去把它取回来：

```cpp
std::vector<S> v3;
S& fresh = v3.emplace_back(5, 6);
fresh.x = 50;
fresh.y = 60;
```

```text
=== Demo C: emplace_back returns a reference to the new element ===
Constructor! x = 5, y = 6
after the change: x = 50, y = 60
```

### 8.2 一个名字上的提醒

这个概念的标准名字是 **`emplace_back`**（emplace 的意思是"放置于其中"），它做的事通常叫**原地构造**：new 出来的那块内存已经有了，只是还没有对象，于是把对象直接建在那里。同理，`std::vector` 就是标准库的向量容器，不要和固定长度的"静态数组"（第 03 章的 `std::array`）混为一谈。

## 9 两者怎么选

| 你手上有什么 | 用哪个 | 理由 |
| --- | --- | --- |
| 已经有一个对象，且以后不再需要它 | `push_back(std::move(obj))` | 移动进容器，不复制 |
| 已经有一个对象，但后面还要用 | `push_back(obj)` | 只能复制，容器拿到的是独立副本 |
| 手里只有构造参数 | `emplace_back(args...)` | 省掉临时对象，只做一次构造 |
| 构造参数里带 `explicit` 构造函数 | `emplace_back(args...)` | `push_back` 无法用它做隐式转换 |
| 元素类型不能复制 | 移动进容器：`push_back(std::move(obj))` 或 `emplace_back(std::move(obj))` | 两条路都只要求可移动（第 14 章） |
| 类型既不能复制也不能移动 | `emplace_back(参数)` + 提前 `reserve` | 只要不发生扩容，就不需要搬运已有元素 |

用一句话概括：**有现成的对象就用 `push_back`，只有参数就用 `emplace_back`。** 至于"`emplace_back` 一定更快"，更准确的说法是：**它少了一次临时对象的构造与转移**。对于 `int` 这种构造成本几乎为零的元素，或者元素个数很少的情况，两者的差别小到测不出来；元素构造成本越高（比如元素是容器、字符串、持有堆内存的类），省下的那一次转移越可观。

## 10 所有添加方式都要面对的一件事：扩容

`vector` 的长度可变，靠的是内部三样东西：一块按需申请的内存、已用长度（`size()`）、总容量（`capacity()`）。添加元素时如果 `size()` 追上了 `capacity()`，容器必须**另申请一块更大的内存，把已有元素搬过去，再释放旧内存**——这个过程叫扩容（reallocation）。它和 `push_back`、`emplace_back` 都有关系，因为它会把**已有的**元素挪动一遍。

例程 `E:\CPP_Code\CppFromScratch\ch30_push_vs_emplace\reallocation_and_reserve\reallocation_and_reserve.cpp` 里的类型不打印日志，而是把三类操作各数一次（`constructions`、`copies`、`moves`），这样"多出来的构造"就变成一个可以直接比较的数字。`main` 里连续添加五个元素，并打印每一步的 `size` 与 `capacity`：

```text
=== Demo A: push_back without reserve ===
push_back 0: size = 1, capacity = 1
push_back 1: size = 2, capacity = 2
push_back 2: size = 3, capacity = 4
push_back 3: size = 4, capacity = 4
push_back 4: size = 5, capacity = 8
constructions = 5, copies = 0, moves = 12
v1 holds: 0 1 2 3 4
=== Demo B: the same five pushes with reserve ===
push_back 0: size = 1, capacity = 5
push_back 1: size = 2, capacity = 5
push_back 2: size = 3, capacity = 5
push_back 3: size = 4, capacity = 5
push_back 4: size = 5, capacity = 5
constructions = 5, copies = 0, moves = 5
v2 holds: 0 1 2 3 4
```

逐项算清 Demo A 的 `moves = 12`：五次 `push_back(S(i))` 各包含一次"临时对象 → 元素"的移动，共 5 次；剩下 7 次来自扩容搬运——`1 → 2` 搬 1 个，`2 → 4` 搬 2 个，`4 → 8` 搬 4 个。`capacity` 那一列（1、2、4、4、8）就是扩容发生的位置：每次快满时容量翻倍。

`copies = 0` 这一项同样值得看：这 12 次移动**全部走了移动构造函数，一次复制都没有**。这不是巧合，而是第 14 章那条规则的回报——只有当元素的移动构造函数是 `noexcept` 时，`vector` 才敢用移动把元素搬到新内存；如果它可能抛异常，容器为了不出"搬了一半失败"的局面，只能退回去复制。

Demo B 只多了一句 `v2.reserve(5);`：**提前把容量要到 5**。之后五次添加都不再触发扩容，`capacity` 一直是 5，搬运次数从 7 降到 0，只剩下 5 次必要的移动。这就是"已知要装多少个元素时先 `reserve`"的道理。

需要注意 `reserve` 与 `resize` 的区别：**`reserve` 只改容量，不改长度**，元素一个都没有；`resize` 改的是长度，会真的构造出元素。`reserve(5)` 之后 `size()` 仍然是 0，此时用 `v[0]` 访问是越界（未定义行为），要添加元素还是得靠 `push_back` / `emplace_back`。

## 11 动手实验

例程分布在两个目录：`E:\CPP_Code\CppFromScratch\ch14_vector\`（实验一至实验四）与 `E:\CPP_Code\CppFromScratch\ch30_push_vs_emplace\`（实验五至实验七），各占一个文件夹、都能独立编译运行。

命令模板（三行，先 `cd` 进例程目录，再编译、运行）：

```text
cd "E:/CPP_Code/CppFromScratch/ch14_vector/vector_basic"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g vector_basic.cpp -o vector_basic.exe
./vector_basic.exe
```

实验二至实验四只替换路径和文件名；实验五至实验七的编译命令在各小节单独列出。

### 实验一：创建、初始化与访问

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

### 实验二：追加与删除

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

**验收标准**：三行数据与第 4 节给出的一致，第二行多出 6，第三行又回到 5 个元素。

**改值实验**：把 `push_back(6)` 改成连续两次 `push_back(6)`，此时一共有 7 个元素，第二段输出变成 `1 2 3 4 5 6 6 `。再想让最后一段回到 `1 2 3 4 `，总共要调用 **3** 次 `pop_back()`（删掉新加的两个 6 和原来的 5）；只调用一次只能删掉末尾一个元素。先预测各段元素个数（5 → 7 → 4），再编译运行核对，然后还原。

### 实验三：观察 size 与 capacity

源码 `size_capacity\size_capacity.cpp`，空 vector 连加 10 个元素并打印过程。

**预期输出**：与第 5 节列出的 12 行完全一致（`before #4` 时容量跳到 4、`before #6` 时跳到 8、`before #10` 时跳到 16）。

**验收标准**：输出逐字符一致；能指着某一行说出"这里发生了重新分配"，以及为什么下一次不会立刻再分配。

**改值实验**：把循环条件 `i < 10` 改成 `i < 5`，先预测 `before #5` 那一行的容量是 4 还是 8，再运行核对（应为 4，因为容量 4 还没用满，第 5 个元素正好放进去）。想清楚为什么"size 到 4 时还没重新分配"这一点，再改回去。

### 实验四：reserve 与 shrink_to_fit

源码 `reserve_shrink\reserve_shrink.cpp`。

**预期输出**：与第 6 节列出的三段输出逐字符一致，共 17 行。

**验收标准**：第一段所有行的 `capacity` 都是 10（一次重新分配都没有）；`pop_back` 之后 `size` 降到 5 而 `capacity` 仍是 10；`shrink_to_fit` 之后两者都是 5。

**改值实验**：把 `reserve(10)` 改成 `reserve(3)`。预测：前 3 个元素进来时容量停在 3，第 4 个元素进来时必须重新分配，容量会跳起来（本例 libstdc++ 扩容后是 6）。运行核对，然后想清楚这个实验说明了什么——`reserve` 给的是"至少这么多"，给少了照样会重新分配。改回 `reserve(10)`。

### 实验五：`push_back` 的三条路径（`push_back_forms`）

`push_back_forms\push_back_forms.cpp` 分别用左值、`std::move(左值)`、临时对象各调一次 `push_back`。

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g push_back_forms.cpp -o push_back_forms.exe
./push_back_forms.exe
```

**预期现象**：输出与第 7 节的十四行逐字符一致。

**验收标准**：`-Wall` 无警告；能对 Demo A、B、C 各说出"选中的是哪个重载、用的是哪个构造函数"，并解释 Demo D 为什么三种写法结果相同。

**改值实验**：把 Demo C 的 `v3.push_back(S(30));` 改成两行：

```cpp
S temp(30);
v3.push_back(temp);       // 故意不写 std::move
```

先判断输出会变成什么。预期是 Demo C 的第二行从 `Move Constructor! x = 30` 变成 **`Copy Constructor! x = 30`**，Demo D 的 `v3[0].x` 仍然是 `30`——临时对象一旦被赋给一个有名字的变量（`temp`），它就是左值了，不写 `std::move` 就退回复制。**这是使用 `push_back` 时最容易犯的一个错误：把"造出来的对象"存进变量之后再 `push_back`，忘了 `std::move`。** 改完编译运行核对，然后还原。

**第二个改值实验**：把 `main` 里 `S s(10);` 改成 `S s(77);`，预期 Demo A 的两行都变成 `x = 77`，Demo D 的 `v1[0].x` 变成 `77`，其余各段完全不动——改的只是这个对象的值，不影响"哪条路径被走到"。

### 实验六：`emplace_back` 原地构造（`emplace_back_in_place`）

`emplace_back_in_place\emplace_back_in_place.cpp` 对比"先造对象再搬"与"直接转发参数"。

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g emplace_back_in_place.cpp -o emplace_back_in_place.exe
./emplace_back_in_place.exe
```

**预期现象**：完整输出如下，共十六行：

```text
=== Demo A: push_back needs a ready-made object ===
Constructor! x = 1, y = 2
Move Constructor! x = 1, y = 2
=== Demo B: emplace_back forwards the arguments instead ===
Constructor! x = 1, y = 2
=== Demo C: emplace_back returns a reference to the new element ===
Constructor! x = 5, y = 6
after the change: x = 50, y = 60
=== Demo D: emplace_back with an existing object still moves ===
Constructor! x = 3, y = 4
Move Constructor! x = 3, y = 4
=== Demo E: the vectors hold what we asked for ===
v1[0]: x = 1, y = 2
v2[0]: x = 1, y = 2
v3[0]: x = 50, y = 60
v4[0]: x = 3, y = 4
```

Demo A 用了两次构造，Demo B 只用了一次；Demo C 说明返回值可以直接改；Demo D 说明传进去的是现成对象时照旧走移动。

**验收标准**：`-Wall` 无警告；能说出 Demo A 与 Demo B 的输出行数为什么不同；能解释 Demo D 里 `emplace_back` 为什么还是调用了移动构造函数。

**改值实验**：把 Demo B 的 `v2.emplace_back(1, 2);` 改成 `v2.emplace_back(1.5, 2);`，先判断结果。预期是**照旧编译通过**（`-Wall` 也不报），输出仍然是 `Constructor! x = 1, y = 2`——`emplace_back` 把实参原样转发给构造函数，`double → int` 这一步隐式转换静默发生，小数部分被直接丢掉。这正是参数转发的一个坑：**参数类型不对时不会报错，只会按隐式转换处理**；要表达"确实要转换"就写清楚（例如先算好一个 `int`），别让它悄悄发生。看完还原。

**必做实验**：把 Demo B 改成 `v2.emplace_back(S(1, 2));`（把参数换成一个现成的对象），**预判**：输出从一行变回两行（`Constructor!` + `Move Constructor!`）——**写了 `emplace_back` 却把对象先造好再传进去，等于什么也没省。** 看完还原。

### 实验七：扩容与 `reserve`（`reallocation_and_reserve`）

`reallocation_and_reserve\reallocation_and_reserve.cpp` 用计数把扩容的代价量出来。

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g reallocation_and_reserve.cpp -o reallocation_and_reserve.exe
./reallocation_and_reserve.exe
```

**预期现象**：输出与第 10 节的十六行逐字符一致（无 `reserve` 时 `moves = 12`，有 `reserve` 时 `moves = 5`，`copies` 两次都是 0）。容量序列（1、2、4、4、8）由本机 libstdc++ 的扩容策略决定，换成别的标准库实现可能不同，但"扩容会把已有元素搬走"这一条不变。

**验收标准**：`-Wall` 无警告；能自己算出 Demo A 的 `moves` 由"5 次必要移动 + 7 次扩容搬运"组成；能说出 `copies = 0` 与移动构造函数的 `noexcept` 之间的关系。

**改值实验**：把两个循环的上限从 5 改成 3，其余不动。先判断结果。预期变为：

```text
=== Demo A: push_back without reserve ===
push_back 0: size = 1, capacity = 1
push_back 1: size = 2, capacity = 2
push_back 2: size = 3, capacity = 4
constructions = 3, copies = 0, moves = 6
v1 holds: 0 1 2
=== Demo B: the same five pushes with reserve ===
push_back 0: size = 1, capacity = 5
push_back 1: size = 2, capacity = 5
push_back 2: size = 3, capacity = 5
constructions = 3, copies = 0, moves = 3
v2 holds: 0 1 2
```

Demo A 的 6 次移动 = 3 次必要移动 + `1 → 2`、`2 → 4` 两次扩容搬运的 1 + 2 个元素；Demo B 有 `reserve(5)` 不扩容，所以只剩 3 次必要移动。改完编译运行核对，然后还原。

**必做实验**：把 `S(S&& other) noexcept` 里的 `noexcept` 删掉，重新编译运行。**预判**：两个 Demo 的 `copies` 都不再是 0，`moves` 也会变小——移动构造函数不再承诺不抛异常，`vector` 在扩容时只好退回去复制元素。这条实验直接说明了第 14 章为什么要给移动构造函数加 `noexcept`。看完还原。
