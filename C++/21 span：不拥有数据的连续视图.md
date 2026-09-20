# 21 span：不拥有数据的连续视图

上一篇：[[20 shared_ptr：共享所有权的智能指针]]
下一篇：[[22 结构体：定义自己的类型]]

## 学习目标

完成本章后，你应当能够：

1. 区分"拥有这块内存"与"只是查看这块内存"两种关系。
2. 说明 `std::span` 表达的是什么，以及它内部记录哪两样信息。
3. 写出一个参数为 `std::span<int>` 的函数，并用它同时接收 `std::vector`、`std::array` 和内置数组。
4. 用"起始位置 + 元素个数"构造 `span`，把它当作容器的某一段来使用。
5. 说明通过 `span` 写入为什么会改动原容器，以及什么情况下 `span` 会变成悬垂视图。

## 1 拥有与只是查看

到本章之前，我们学过的容器都在**拥有一块内存**：

- `std::vector`（第 14 章）自己动态分配内存，对象销毁时自己把内存还回去；
- `std::unique_ptr`（第 19 章）和 `std::shared_ptr`（第 20 章）是管理内存所有权的指针，谁负责释放由所有权规则决定。

"拥有"意味着两件事：**你负责这块内存的分配与释放**，并且**你有权修改它、也有权决定它的大小**。

但有一类需求跟"拥有"无关。假设你在写一个绘图程序，手里已经有一个装满数据的 `std::vector<int>`，现在只想**把其中某一段打印出来**。这个打印函数关心的事情只有一件：它拿到的是**一串连续存放的整数**。它不关心这串整数是 `vector` 提供的、`std::array` 提供的，还是别处的一块内存；它也不会去分配、释放、增删任何元素。

如果硬要让这个函数"接收一个容器"，我们只有两种坏选择：要么把容器类型写死（来一个 `std::array` 就得再写一份同样的函数），要么只接收迭代器，把"容器的开始"和"容器的结束"两个参数都传进来。两种写法都别扭，后面第 3 节会具体看别扭在哪里。

C++20 起，标准库给出了第三种选择：`std::span`。

## 2 span 是什么

**`std::span` 描述了一个可以引用一段连续对象序列的对象，第一个元素从索引 0 开始，长度可以是静态的也可以是动态的。** 它定义在头文件 `<span>` 中（和 `vector` 在 `<vector>` 里、`array` 在 `<array>` 里一样，用什么就要包含什么）。

拆开这句话：

- **"引用"**：`span` 本身不存放元素。它内部只有两样东西——**首元素的地址**和**元素个数**。这两样加起来就足以描述"一段连续的数据"，因为元素是挨着放的，知道头在哪、有几个，剩下每个元素的地址就能算出来。
- **"连续对象序列"**：元素必须是一个挨一个地存放的。`std::vector`、`std::array`、内置数组都满足这一点。这也是 `span` 能用下标 `s[i]` 访问、能算出 `s.data()` 的原因。
- **"首元素从索引 0 开始"**：不管这段数据原本是容器的第几个元素，只要进了 `span`，它在 `span` 里就是第 0 个。
- **"静态或动态长度"**：元素个数可以写进类型里，比如 `std::span<int, 3>`；也可以不写，比如 `std::span<int>`，表示长度在运行期确定。

因此 `span` 提供的是**容器级别的抽象，但不附带所有权**。凡是"连续容器"上顺手的操作，它基本都有：范围 `for` 遍历、下标访问、`.size()`、`.data()`。而它会**接管释放内存**这种责任吗？不会——它从名字到设计都在说"我只是看看，东西不是我的"。

**一个必须记住的结论**：`span` 记的是地址和长度，而不是它自己持有一份数据。所以

- 拷贝一个 `span` 非常便宜，只是复制两个值；
- 反过来，**原数据一旦消失或搬家，`span` 记的地址就失效了**，此时再用它就是未定义行为（第 6 节会专门讲）。

## 3 不用 span 的话，函数参数会变成什么样

回到第 1 节的打印函数。假设我们不用 `span`，想表达"打印这个向量的某一部分"，其实只有下面几种写法。

**写法一：传容器引用，加一个终点下标。**

```cpp
void printSomething(const std::vector<int>& values, int end);
```

只能从 0 打印到 `end`，想打印中间一段就不够了。

**写法二：传容器引用，加起点和终点两个下标。**

```cpp
void printSomething(const std::vector<int>& values, int begin, int end);
```

能做，但调用处出现了两个相邻的整数参数，读者必须记得哪个是起点哪个是终点，写反了也照样能编译。

**写法三：传一对迭代器。**

```cpp
void printSomething(std::vector<int>::const_iterator first, std::vector<int>::const_iterator last);
```

调用处是 `printSomething(v.begin(), v.end())` 这类写法，功能没问题，但参数表上写着"两个迭代器"，函数**没有直接说出"我要的是一段连续的数据"**这件事。

三种写法的共同毛病有两个：

1. **参数变成了两三个，而它们本来说的是同一件事**——"要打印的范围"。范围被拆散了，函数签名里就看不见它了。
2. **容器类型被写死在签名里**。`std::vector<int>` 一旦写进参数表，这个函数就只认 `vector<int>`；换成 `std::array<int, 3>` 就得重写一份一模一样的函数。

而"我不关心这些数据从哪来、装在什么容器里，我只关心它是一串连续的整数"——这正好就是 `span` 要说的话。改传一个 `span`，"范围"重新变成了**一个**参数。

## 4 用 span 当参数：同一个函数服务所有连续容器

例程 `E:\CPP_Code\CppFromScratch\ch21_span\span_basic\span_basic.cpp` 里的打印函数（省略注释）：

```cpp
void printSpan(std::span<int> values)
{
    bool first = true;

    for (int value : values)
    {
        if (!first)
        {
            std::cout << " ";
        }

        std::cout << value;
        first = false;
    }

    std::cout << std::endl;
}
```

那个 `first` 标志只干一件小事：**决定当前这个元素前面要不要先打一个空格**，这样行末不会多出一个看不见的空格，输出能和文档里的预期结果逐字符对上。函数本身多了几行，换来的是结果可核对——对照一下另一个例程 `span_extent` 里的写法就能看出区别，那里用了下标循环 `for (std::size_t i = 0; i < values.size(); ++i)` 来达到同样目的。

函数体跟第 08 章打印数组的写法几乎一样——`span` 支持范围 `for`，元素访问方式也和第 05、14 章一致。真正的变化在参数类型上，`std::span<int>` 现在读起来是一句准确的要求：**给我一段连续存放的 `int`，别的我不管。**

调用处更简单，因为**从连续容器到 `span` 的转换是隐式且零拷贝的**：

```cpp
std::vector<int> myVector {1, 2, 3, 4, 5};
printSpan(myVector);          // std::vector -> std::span
```

为什么不用写 `std::span<int>{myVector}`？因为 `vector` 本来就维护着"首地址 + 长度"这两样信息，把它交给 `span` 不需要计算、更不需要复制元素，编译器允许这种转换直接发生。同一个函数还能接收：

| 实参类型 | 为什么可以 |
| --- | --- |
| `std::vector<int>` | 元素连续存放，自带首地址和长度 |
| `std::array<int, 3>` | 同上，长度是类型的一部分 |
| `int rawArray[3]` | 内置数组在内存里就是连续三个 `int`，会退化成首地址 |

**这就是 `span` 最实用的收益：函数只写一次，服务所有连续容器。** 想确认它真的没复制数据，可以比较地址：`view.data()` 交出首元素地址，如果和 `myVector.data()` 相等，说明两者指向的是同一块内存（例程 `span_basic` 的 Demo D 打印了这个比较结果，输出恒为 `true`）。

## 5 只看一部分：起始位置 + 元素个数

`span` 可以做容器做不到的一件事：**把"容器的某一段"单独变成一个对象**。做法是构造 `span` 时给出"从哪里开始"和"看几个元素"：

```cpp
std::vector<int> myVector {1, 2, 3, 4, 5};
std::span<int> firstTwo {myVector.begin(), 2};       // 1 2
std::span<int> middle  {myVector.begin() + 1, 3};    // 2 3 4
```

对照着看这两个例子：`begin()` 是第 0 个元素的位置，所以 `firstTwo` 从下标 0 开始，取 2 个，是 1、2；`begin() + 1` 往后挪一个，指向原来的下标 1，从那里取 3 个，就是下标 1、2、3，即 2、3、4。

于是 `span` 里的下标和原容器的下标之间有一个固定关系：**`span[i]` 就是原容器的 `原起点下标 + i`**。上面 `middle` 的 `middle[0]` 是原容器的下标 1，`middle[2]` 是原容器的下标 3。注意 `middle` 本身只有 0、1、2 三个下标，**用 `span` 自己的下标访问时永远从 0 开始**，这一点和第 2 节"首元素从索引 0 开始"是同一件事。

有了这个能力，第 3 节那个函数签名可以一直保持只有一个参数：

```cpp
printSpan(myVector);                                    // 整个向量
printSpan(std::span<int> {myVector.begin(), 2});        // 前两个
printSpan(std::span<int> {myVector.begin() + 1, 3});    // 中间三个
```

需要打印的范围在**调用处**决定，函数内部一行都不用改，也不需要知道这段数据是整块还是截出来的。这正是 `span` 的构造函数里"从一段值范围构造"那条规则带来的好处：只要能表示成"起点 + 个数"或"起点 + 终点"，就能变成 `span`。

## 6 不拥有数据，意味着什么

`span` 不拥有数据，这句话有两面。好的一面是零拷贝、参数只有一个；需要时刻警惕的一面是**它只是记录地址，不保证那地址还有效**。

**第一面：通过 span 写入，改的就是原数据。**

```cpp
std::span<int> middle {myVector.begin() + 1, 3};
middle[0] = 99;              // 等于写 myVector[1] = 99
```

这里没有"同步"也没有"传递"——`span` 和 `vector` 说的本来就是同一块内存（例程 `span_subview` 的 Demo C 打印了整个 `vector`，可以看到 2 变成了 99）。这一点和引用（第 15 章）的道理相通：别名不是副本，改一处就是改那一处。

**第二面：原数据消失或搬家之后，span 就成了悬垂视图。**

`span` 记下的是一个地址。如果那个地址背后的数据没了，`span` 不会收到任何通知，也不会自动变空。典型场景有两个：

- **数据本来就是个临时对象**。从临时的 `vector` 构造出 `span`，语句结束后这个临时的 `vector` 已经销毁，`span` 记的地址也就无效了。
- **容器搬家了**。`vector` 的容量用满时会重新申请一块更大的内存，把元素搬过去，原来的地址就作废了。此时旧的 `span` 仍然指着那块已经被释放的内存。

这两种情况编译器**都不会报错**，程序可能继续打印出乱七八糟的值、也可能直接崩溃——这就是未定义行为最典型的形态（和"函数漏了 `return` 却能编译"一样，属于"能跑、结果不可信"的一类问题）。判断规则很简单：**`span` 的生命周期必须短于它所指数据的生命周期，并且在这期间不能让容器重新分配**。写函数时，`span` 作为参数是安全的——调用期间实参容器一定活着；把 `span` 存进别的对象、或者在容器 `push_back` 之后继续用旧 `span`，才需要格外小心。

## 7 固定长度与只读：两个常见的参数写法

**固定长度：把长度写进类型。**

```cpp
void printFixed(std::span<int, 3> values);
```

第二个模板参数是元素个数，它是**类型的一部分**，所以"长度为 3"这件事由编译器负责检查：传进来一段长度不对的数据，编译直接失败，不会拖到运行时才发现（改值实验见 8.3 节）。省略第二个参数时长度是动态的，也就是前面一直用的 `std::span<int>`。

**只读：把元素类型写成 `const`。**

```cpp
void printReadOnly(std::span<const int> values);
```

元素类型是 `const int`，意思是"我只看，不改写"。它的好处有三层：

1. 读函数的签名就能知道它不会修改数据，不必去读函数体；
2. `const std::vector<int>` 这类只读容器**只能**转成 `std::span<const int>`，转不成 `std::span<int>`；把参数写成只读版本，能接收的实参范围更大；
3. `std::span<int>` 可以隐式转换成 `std::span<const int>`，反过来不行——这保证了"只读"这层承诺不会被绕过。

**怎么选**：参数只读取数据时，写成 `std::span<const T>`；需要修改数据时，写 `std::span<T>`；只有当"长度固定"本身是函数要求的一部分、并且希望编译期就卡住错误时，才把长度写进类型（`std::span<T, N>`）。至于 `span` 和"传引用"的取舍：`std::vector<int>&` 表达"我就要这个向量本身"，`std::span<int>` 表达"我只要一段连续的 int"，**当函数真的不需要知道容器类型时，`span` 是更准确的表达**。

## 8 动手实验

三个例程都在 `E:\CPP_Code\CppFromScratch\ch21_span\` 下，各占一个文件夹。编译器用 MSYS2 的 GCC，`span` 是 C++20 的特性，**必须带 `-std=c++20`**（更老的编译器可能根本不支持）。

### 8.1 实验一：一个函数服务三种容器（`span_basic`）

`span_basic\span_basic.cpp` 里定义了 `void printSpan(std::span<int> values)`，`main` 里分别用 `std::vector<int>`、`std::array<int, 3>`、内置数组 `int rawArray[3]` 调用同一个函数，最后用地址比较验证没有拷贝。

```text
cd "E:/CPP_Code/CppFromScratch/ch21_span/span_basic"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g span_basic.cpp -o span_basic.exe
./span_basic.exe
```

**预期输出**（分隔符只在元素之间插入，行末没有多余空格）：

```text
=== Demo A: 传入整个 vector ===
1 2 3 4 5
=== Demo B: 同一个函数接收 std::array ===
7 8 9
=== Demo C: 同一个函数接收内置数组 ===
4 5 6
=== Demo D: span 只是视图，没有复制数据 ===
true
```

**验收标准**：四段输出逐字符一致；编译 `-Wall` 无警告。Demo D 的 `true` 是"`span` 与 `vector` 指向同一块内存"的直接证据——如果 `span` 悄悄复制了一份数据，这里就该是 `false`。

**改值实验**：把 `std::array<int, 3> myArray {7, 8, 9};` 改成 `{7, 8, 9, 10}`，重新编译运行。**先自己预判**：`printSpan` 完全没改，Demo B 的输出会变成什么？再运行核对——应该是 `7 8 9 10`。这直接说明函数的参数类型写 `std::span<int>` 之后，它对容器长度、容器种类都不再敏感。

### 8.2 实验二：只看一部分，并且改动它（`span_subview`）

`span_subview\span_subview.cpp` 用 `{myVector.begin(), 2}` 和 `{myVector.begin() + 1, 3}` 构造两段视图，然后通过 `middle[0] = 99;` 写入，再打印原 `vector` 和这个 `span` 本身。

```text
cd "E:/CPP_Code/CppFromScratch/ch21_span/span_subview"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g span_subview.cpp -o span_subview.exe
./span_subview.exe
```

**预期输出**：

```text
=== Demo A: 从 vector 开头取 2 个元素 ===
1 2
=== Demo B: 从第二个元素开始取 3 个 ===
2 3 4
=== Demo C: 通过 span 写入，原 vector 跟着变 ===
1 99 3 4 5
=== Demo D: 再打印这个 3 元素的 span 本身 ===
99 3 4
```

**验收标准**：四段输出逐字符一致，编译 `-Wall` 无警告。Demo C 里 `2` 变成 `99`、而其他元素没动，说明 `middle[0]` 落的正是 `myVector[1]` 这个位置。

**改值实验**：把构造 `middle` 的 `myVector.begin() + 1` 改成 `myVector.begin()`（不偏移），`middle[0] = 99;` 这一句不动，重新编译运行。**预判**：Demo B 会变成 `1 2 3`，Demo C 会变成 `99 2 3 4 5`（被改写的是第一个元素）。核对后能确认"`span` 的下标从 0 开始、映射到原容器起点"这条规则。

### 8.3 实验三：固定长度与只读视图（`span_extent`）

`span_extent\span_extent.cpp` 定义了 `printFixed(std::span<int, 3>)`（长度写进类型）和 `printReadOnly(std::span<const int>)`（只读），并演示了从 `vector` 显式构造固定长度 `span`。

```text
cd "E:/CPP_Code/CppFromScratch/ch21_span/span_extent"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g span_extent.cpp -o span_extent.exe
./span_extent.exe
```

**预期输出**：

```text
=== Demo A: 固定 3 个元素的 span ===
长度：3
10 20 30
=== Demo B: 从 vector 里取固定长度的前 3 个，并改写第一个 ===
长度：3
100 2 3
=== Demo C: span<const int> 只读视图 ===
长度：5
100 2 3 4 5
```

**验收标准**：三段输出逐字符一致，编译 `-Wall` 无警告。Demo C 打印出的 `100` 是 Demo B 通过 `fixed[0] = 100;` 写进 `vector` 的值，说明固定长度的 `span` 也一样是视图、不是副本。

**改值实验一**：把 `void printFixed(std::span<int, 3> values)` 里的 `3` 改成 `4`，其他不动，重新编译。**预判**：这一步编译不过，因为 `std::array<int, 3>` 转不成 `std::span<int, 4>`。实际报错是：

```text
error: could not convert 'myArray' from 'std::array<int, 3>' to 'std::span<int, 4>'
```

看完把 `3` 改回去。

**改值实验二**：在 `main` 的最后加两行，让只读接口吃一个只读容器：

```cpp
const std::vector<int> myConstVector {7, 8, 9};
printReadOnly(myConstVector);
```

重新编译运行，能正常打印出 `长度：3` 和 `7 8 9`——**`std::span<const int>` 能接收只读容器**。接着把 `printReadOnly` 的参数从 `std::span<const int>` 改成 `std::span<int>`（去掉 `const`），重新编译就会失败：

```text
error: could not convert 'myConstVector' from 'const std::vector<int>' to 'std::span<int, 18446744073709551615>'
```

（`18446744073709551615` 就是 `std::dynamic_extent` 的值，也就是"长度在运行期确定"；GCC 有时把这个默认参数展开打印出来。）报错的原因是 `const std::vector<int>` 里的元素是只读的，交给一个"可以写"的视图就相当于允许改写只读数据。注意反过来的方向是允许的：普通的 `std::vector<int>` 既能满足 `std::span<int>`，也能满足 `std::span<const int>`（这就是 Demo C 里 `myVector` 能传给 `printReadOnly` 的原因）。**把只读参数写成 `std::span<const int>`，能接收的实参最多**，看完把改动还原。

## 9 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| `error: could not convert 'myArray' from 'std::array<int, 3>' to 'std::span<int, 4>'` | 形参写了固定长度，实参长度不对（长度是类型的一部分） | 让两边长度一致，或把形参改成动态长度的 `std::span<int>` |
| `error: could not convert 'c' from 'const std::vector<int>' to 'std::span<int>'`（GCC 也可能把动态长度展开成 `std::span<int, 18446744073709551615>`） | 形参是可写的 `std::span<int>`，实参却是只读容器（元素是 `const int`） | 只读函数把参数写成 `std::span<const int>`；或去掉实参的 `const`（前提是函数确实要写） |
| `error: 'span' is not a member of 'std'` | 忘了 `#include <span>` | 补上头文件；GCC 会附一句提示：`note: 'std::span' is defined in header '<span>'` |
| `error: no matching function for call to 'std::span<int>::span(<brace-enclosed initializer list>)'` | 想直接写 `std::span<int> s {1, 2, 3};`——`span` 没有接收元素列表的构造函数 | `span` 是视图，元素必须先有地方放：先用 `std::vector<int>` 或 `std::array<int, 3>` 存起来，再从这个容器构造 `span` |
| `error: assignment of read-only location` | 参数是 `std::span<const int>`，函数体里却对它赋值 | 需要写入就把参数改成 `std::span<int>`；不需要写入就删掉那句赋值 |
| 编译通过，但打印出来是乱码或程序崩溃 | `span` 悬垂：原数据已销毁，或 `vector` 扩容后旧 `span` 还在用 | 保证 `span` 不活得比数据长；容器可能扩容时不要保存旧 `span`，需要重新构造 |
| 程序正常运行，但 `span` 改了数据后原容器"没变" | 其实改的是另一份数据（例如误从临时容器或副本构造了 `span`） | 用 `.data()` 比较地址确认指向同一块内存 |
| `error: could not convert 'v' from 'std::vector<double>' to 'std::span<int>'` | 元素类型不匹配：`std::span<int>` 只能接收连续的 `int` | 统一元素类型（如把参数改成 `std::span<double>` 或 `std::span<const double>`） |

## 10 本章验收

1. 三个例程编译通过、`-Wall` 无警告，输出与 8.1、8.2、8.3 节的预期逐字符一致。
2. 能说明 `span` 内部只记录哪两样信息，并据此解释"为什么拷贝 `span` 很便宜"。
3. 能写出一个参数为 `std::span<const int>` 的打印函数，并用 `std::vector`、`std::array`、内置数组各调用一次。
4. 能解释 `std::span<int> middle {myVector.begin() + 1, 3};` 里每个部分的作用，并说出 `middle[0]` 对应 `myVector` 的哪个下标。
5. 能说出两种会让 `span` 变成悬垂视图的情形，以及为什么这种错误编译器不会报。
