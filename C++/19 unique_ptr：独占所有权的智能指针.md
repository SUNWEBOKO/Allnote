# 19 unique_ptr：独占所有权的智能指针

上一篇：[[18 动态内存分配：new 与 delete]]
下一篇：[[20 shared_ptr：共享所有权的智能指针]]

## 学习目标

完成本章后，你应当能够：

1. 说出原始指针在表达力和释放安全上的两个问题。
2. 用 `std::unique_ptr` 接管 `new` 出来的内存，并说出模板参数写成 `T[]` 表示什么。
3. 用 `std::make_unique` 创建 `unique_ptr`，并说出它省掉了哪一步。
4. 说明为什么 `unique_ptr` 不需要手写 `delete`，以及为什么它不能被复制。
5. 用 `get`、`release`、`reset`、`swap` 完成借用地址、交出所有权、替换对象、交换对象。

## 1 原始指针的两个问题

第 18 章用 `new` / `delete` 走通了"运行时自己申请内存"这条路，也为它列出了四条纪律。回头看这些纪律，会发现它们有一个共同点：**全靠人记住**。现代 C++ 之所以不鼓励直接使用原始指针，主要是两件事：

**一是表达力不够。** 一个 `int*` 只说明"指向某个 `int`"，看不出它指向的是**一个**对象还是**一批**对象的第一个：

```cpp
int* p = new int;        // 指向一个 int
int* q = new int[100];   // 指向 100 个 int 的第一个
```

`p` 和 `q` 的静态类型一模一样，都是 `int*`。"这是 100 个元素"这个信息根本没有出现在类型里，所以释放时该写 `delete` 还是 `delete[]`，编译器只能靠额外分析去猜。同理，函数收到一个 `int*` 参数时，也无法从类型上知道该按一个元素还是按一批元素处理。

**二是释放不安全。** 用 `new` 分配、把地址存进原始指针之后，**没有任何机制能保证程序会在某处释放它**。唯一的保障是"我记得写 `delete`"。而代码里充满了提前 `return`、条件分支、异常跳出，只要有一条路径漏掉了 `delete`，这块内存就再也回不来了。这类程序如果长时间运行、反复分配，内存会持续增长，最终申请不到内存而失败。

## 2 `unique_ptr` 换掉了什么

C++ 给出的解决方向之一，是把"谁负责释放"写进**类型**里。这就是智能指针。本章的主角是 `std::unique_ptr`：

> `std::unique_ptr` 是一个通过指针管理另一个对象的智能指针，并在 `unique_ptr` 超出作用域时释放该对象。

把这句话拆开看，它其实只做了两件事，但都很关键：

- **管理**：它内部保存着那个地址，对外提供访问被管理对象的手段（解引用、下标、`get`）。
- **在超出作用域时释放**：释放动作写在它自己的析构函数里。也就是说，**只要这个对象正常销毁，内存就一定被释放**——不管是 `main` 正常走到结尾、还是中间某处提前 `return`、还是抛异常展开调用栈，析构函数都会被调用。

这正好对应了"独占所有权"这个名字：**一块内存同一时刻只由一个 `unique_ptr` 负责**。谁管这块内存是明确的、唯一的，"什么时候该释放"也就没有歧义了——它管着的那个 `unique_ptr` 消失的时候就是该释放的时候。

于是程序里不再出现 `delete`：责任从"你"转移到了"对象"。

## 3 让 `unique_ptr` 接管一块内存

`unique_ptr` 定义在 `<memory>` 头文件里，用之前要包含它。接管 `new` 出来的内存，写法是把 `new` 的结果交给它：

```cpp
std::unique_ptr<int[]> pointer(new int[10]);
```

这一行拆开看：

| 部分 | 内容 | 说明 |
| --- | --- | --- |
| 类模板 | `std::unique_ptr` | 智能指针的类型，尖括号里写它管理的类型 |
| 类型参数 | `<int[]>` | 管理**一批** `int`。方括号表示数组形式 |
| 变量名 | `pointer` | 和普通变量一样，起什么名字都可以 |
| 构造实参 | `(new int[10])` | 直接放一个 `new` 表达式，把刚分配的内存交给它接管 |

**为什么必须写 `<int[]>` 而不是 `<int>`**：数组形式用的释放方式是 `delete[]`，单个对象形式用的是 `delete`。分配方式（`new int[10]`）和释放方式必须对应，类型参数写对了这一步才对得上。写错成 `<int>` 时，GCC 在本例中不会报警告，但释放时会用 `delete` 去销毁一批对象，行为是错误的。

**为什么说"接管"**：这一句执行完之后，那个 `new` 出来的地址就没有别的名字了，它只存在于 `unique_ptr` 内部。我们日常操作的对象是 `unique_ptr` 本身，不再需要单独保管那个原始指针。

使用方式没有变，数组形式专门提供了 `operator[]`，所以下标照常可用：

```cpp
for (int i = 0; i < 10; ++i)
{
    pointer[i] = i * i;      // 用起来和数组一样
}
```

`unique_ptr` 为数组形式提供下标访问，是它比原始指针更好用的地方之一：拿到 `int*` 时你还得自己记住长度，而这里至少已经表达了"我管的是一批对象"。

## 4 用 `make_unique` 省掉 `new`

上一节的写法里 `new` 是显式写出来的，有两个重复和易错的地方：类型参数（`<int[]>`）和 `new` 表达式（`new int[10]`）必须手动对齐；类型名要写两遍。标准库提供了工厂函数 `std::make_unique` 一步做完：

```cpp
auto pointer = std::make_unique<int[]>(10);      // 分配 10 个 int 的数组
```

它内部完成分配，并返回一个已经接管该内存的 `unique_ptr`，`new` 关键字就此消失，我们也不用再操心 `delete[]` 该不该写。返回类型由函数模板推导而来，用 `auto` 接最省事（第 03 章 7.4 节的原则：类型可以从表达式看出来就用 `auto`）。

这里有一个**必须分清**的区别：

| 写法 | 含义 |
| --- | --- |
| `std::make_unique<int[]>(10)` | 方括号说明要的是**数组**，`10` 是**元素个数**，得到 10 个 `int` |
| `std::make_unique<int>(10)` | 没有方括号，`10` 是这个 `int` 的**初值**，只得到 1 个 `int`，`*one == 10` |

少了方括号就是完全不同的两件事。写错时有一个可用的核对手段：数组形式才能用 `p[i]` 下标，单个对象形式只能 `*p` 解引用，用错会在编译期直接报错。

另外，`make_unique` 还有一个不显眼但真实的好处：分配内存和构造对象由它一次完成，不会出现"内存已经分配但还没交给智能指针"的中间状态——那种状态下如果构造智能指针的过程中抛了异常，这块内存就没人负责了。

## 5 不需要 `delete` 的验证方式

写好的 `unique_ptr` 程序里搜一遍，应该**一个 `delete` 都没有**。释放发生在它析构的时候，可以在`main` 结尾手工验证：在最后打印一行，`main` 返回后指针对象被销毁、内存被释放。这类"什么都不会打印出来的正确行为"没法直接从输出里看到，能做的是对照三条：

1. 源码里没有 `delete` / `delete[]`；
2. 编译运行无异常、无崩溃（对照第 18 章的双重释放现象）；
3. 把它替换回第 18 章的原始指针写法，功能完全一样——说明智能指针没有改变使用方式，只是接管了释放责任。

## 6 常用成员函数：`get`、`release`、`reset`、`swap`

日常使用中，`unique_ptr` 提供的操作不多，但每一个的语义都要清楚：

| 成员函数 | 作用 | 所有权怎么变 |
| --- | --- | --- |
| `get()` | 返回内部保存的原始指针，**只是借出来看看** | 不变，仍由 `unique_ptr` 负责释放 |
| `release()` | 交出原始指针，同时把自己置为空 | **不再归它管**，释放责任回到调用者 |
| `reset(p)` | 释放当前管着的对象，改为接管 `p` | 旧的释放掉，新的归它管 |
| `reset()` | 不带参数，等于提前释放 | 置为空，相当于手动触发一次析构 |
| `swap(other)` | 交换两个 `unique_ptr` 管理的东西 | 交换谁管哪块内存，值不动 |

几条使用要点：

- **`get()` 借来的地址不能 `delete`。** 那块内存仍然归 `unique_ptr` 管，它会在合适的时机释放；你再去释放一次就是重复释放。`get()` 的正确用途是交给只接受原始指针的接口。
- **`release()` 之后必须自己负责。** 它做的是"我不想管了，地址给你"，`unique_ptr` 从此不再释放这块内存。如果拿到地址之后既没手动 `delete`、也没交给别的管理者，就是内存泄漏。
- **`reset()` 是提前释放的手段。** 想让内存尽早还回去（而不是等到作用域结束）就用它，不带参数的形式最直观。

还有一条硬规则：**`unique_ptr` 不能被复制**。复制意味着两个 `unique_ptr` 都认为自己该释放同一块内存，"独占"立刻被破坏，所以标准库直接把它的拷贝构造函数标记为删除。下面这种写法编译不过：

```cpp
auto p1 = std::make_unique<int>(5);
auto p2 = p1;         // 编译错误：use of deleted function ...
```

这不是限制，而是设计意图的体现：**要转移所有权，就要明确地写出来**，不能不小心复制。转移的手段是 `std::move`，那属于移动语义的内容（第 28 章），本章只要记住"`unique_ptr` 独占，不能复制"。

## 7 什么时候用 `unique_ptr`

选择顺序和第 18 章末尾的建议是一致的：

- **一批数据、需要增删元素** → `std::vector`（第 14 章）。它连"长度"这个信息都替你管着。
- **一个对象，生命周期要动态决定** → `std::unique_ptr`。例如运行时创建、用完就丢的对象。
- **一批固定长度的数据，需要传出去让别人看** → 第 21 章的 `std::span`。
- **多个使用者共享同一块数据** → 下一章的 `std::shared_ptr`。

`unique_ptr` 的定位是"有明确且唯一的主人"的对象。只要场景符合这个描述，用它就比原始指针安全得多，而且没有任何额外的手工步骤——写好 `make_unique` 之后，剩下的交给析构函数。

## 8 动手实验

例程在 `E:\CPP_Code\CppFromScratch\ch19_unique_ptr\` 下，三个程序各占一个文件夹。

### 8.1 实验一：接管 `new` 出来的数组

`E:\CPP_Code\CppFromScratch\ch19_unique_ptr\unique_ptr_new\unique_ptr_new.cpp` 演示 `unique_ptr<int[]>(new int[10])` 的写法、下标访问，以及整段程序没有 `delete`。

编译运行（在 `E:\CPP_Code\CppFromScratch\ch19_unique_ptr\unique_ptr_new` 目录下执行）：

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g unique_ptr_new.cpp -o unique_ptr_new.exe
./unique_ptr_new.exe
```

**预期输出**（逐字符一致）：

```text
=== Demo A: unique_ptr manages a dynamic array ===
pointer[4] = 16
pointer[7] = 49
=== Demo B: no delete anywhere in this program ===
main is about to end, the array will be freed automatically
```

**结果解释**：`pointer[4] = 16`、`pointer[7] = 49` 是 4 和 7 的平方，说明下标访问和原始指针数组一样可用，而填写这些值的循环里没有任何与释放相关的代码。程序里一个 `delete` 都没有——这是本章要看的重点。

**验收标准**：编译 `-Wall` 无警告，输出与上面逐行一致；在源文件里搜索 `delete`，结果应为 0 处（注释里提到的除外）。

**改值实验**：把打印的两个下标从 4、7 改成 2、8。重新编译运行前先预测：应该是 `pointer[2] = 4` 与 `pointer[8] = 64`，即 `i * i`。这能验证填充循环和下标访问确实是同一套索引。

### 8.2 实验二：用 `make_unique` 创建

`E:\CPP_Code\CppFromScratch\ch19_unique_ptr\unique_ptr_make\unique_ptr_make.cpp` 演示 `make_unique<int[]>(10)` 的写法（`new` 完全消失），以及管理单个对象时写 `<int>` 的对照。

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g unique_ptr_make.cpp -o unique_ptr_make.exe
./unique_ptr_make.exe
```

**预期输出**（逐字符一致）：

```text
=== Demo A: make_unique builds the array for us ===
pointer[5] = 25
pointer[9] = 81
the resource is owned by one unique_ptr: 1
=== Demo B: managing a single int instead of an array ===
*one = 7
```

**结果解释**：`pointer[5] = 25` 与 `pointer[9] = 81` 是 5 和 9 的平方。`the resource is owned by one unique_ptr: 1` 是用 `pointer != nullptr` 确认它确实管着一个有效对象（`new` 失败时不会走到这里，所以这个判断在这里是"确认"而不是"防御"）。Demo B 的 `*one = 7` 说明单个对象形式用 `<int>`、用解引用取值。

**验收标准**：编译 `-Wall` 无警告，输出与上面逐行一致；能说清 `make_unique<int[]>(10)` 与 `make_unique<int>(10)` 的区别。

**改值实验**：这个实验分三步，每一步都先预测再验证。

1. 只把 `std::make_unique<int[]>(10)` 的 `10` 改成 `20`。预期输出**完全不变**：`pointer[5] = 25`、`pointer[9] = 81`，因为这两个下标在两个版本里都合法。
2. 再把打印的那一行从 `pointer[5]` 改成 `pointer[15]`（字符串里的 `pointer[5]` 和后面真正取值的那处一起改）。预期得到 `pointer[15] = 0`——**不是** 225。原因是填充循环只写了 `0` 到 `9`，15 号元素从来没被赋值；这里读到 0 是因为 `make_unique<int[]>(n)` 会把新数组做值初始化（相当于 `new int[n]()`），没写过的元素都是 0。
3. 最后把循环里的 `i < 10` 也改成 `i < 20`，重新编译运行，这时才会得到 `pointer[15] = 225`。

三步走下来能看清一件事：**元素个数只存在于那个字面量里**，没有任何机制替你检查"下标和长度是否匹配"。漏改循环时程序既不报错也不警告，只是安静地给出 0。原始指针和 `unique_ptr` 都还没解决这个表达力问题，第 21 章的 `span` 才把长度补进类型里。

### 8.3 实验三：`get` / `release` / `reset` / `swap`

`E:\CPP_Code\CppFromScratch\ch19_unique_ptr\unique_ptr_api\unique_ptr_api.cpp` 逐个演示四个成员函数的语义。

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g unique_ptr_api.cpp -o unique_ptr_api.exe
./unique_ptr_api.exe
```

**预期输出**（逐字符一致）：

```text
=== Demo A: get() borrows the address ===
*p.get() = 7
p is not null: 1
*raw = 7
=== Demo B: release() gives up ownership ===
after release, p is null: 1
*rel = 7
=== Demo C: reset() replaces the managed object ===
after reset(new int(9)), *p = 9
after reset(), p is null: 1
=== Demo D: swap() exchanges the managed objects ===
before swap: *a = 1, *b = 2
after swap: *a = 2, *b = 1
```

**结果解释**：Demo A 里 `get()` 之后 `p` 仍然非空，说明所有权没变。Demo B 里 `release()` 之后 `p` 变成了空指针，而地址被交到 `rel` 手里——所以程序里紧接着自己 `delete rel;`，这一段是全书少数需要手写 `delete` 的地方，因为它已经脱离智能指针的管理。Demo C 里两次 `reset` 分别演示"替换"和"提前释放"。Demo D 的 `after swap: *a = 2, *b = 1` 说明交换的是谁管哪块内存。

**验收标准**：编译 `-Wall` 无警告，输出与上面逐行一致；能说出 `get()` 和 `release()` 在所有权上的差别。

**改值实验**：把 Demo D 中 `a.swap(b);` 注释掉。预测：`after swap:` 那一行会打印 `*a = 1, *b = 2`，与 `before swap:` 相同。这直接说明"值没有变，变的是谁来管"。

## 9 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| `error: use of deleted function 'std::unique_ptr<_Tp, _Dp>::unique_ptr(const std::unique_ptr<_Tp, _Dp>&) [with _Tp = int; _Dp = std::default_delete<int>]'` | 试图复制 `unique_ptr`：`auto p2 = p1;` | 独占所有权不允许复制；要转移得用 `std::move`（第 28 章） |
| 同一条 `use of deleted function` 出现在函数调用处 | 把 `unique_ptr` 按值传给函数，实参会复制一份 | 参数改成引用（`const std::unique_ptr<T>&`），或按需用 `std::move` 明确转移 |
| `error: conversion from 'int*' to non-scalar type 'std::unique_ptr<int>' requested` | 用 `=` 直接拿 `new` 的结果初始化：`std::unique_ptr<int> p = new int(5);` | 改成直接初始化 `std::unique_ptr<int> p(new int(5));`，或直接用 `auto p = std::make_unique<int>(5);` |
| `error: 'class std::unique_ptr<int [], std::default_delete<int []> >' has no member named 'use_count'` | 把 `unique_ptr` 当 `shared_ptr` 用 | `use_count` 是下一章 `shared_ptr` 的成员；`unique_ptr` 的"计数"永远是 1 或 0，用 `p != nullptr` 判断即可 |
| `error: no match for 'operator[]' (operand types are 'std::unique_ptr<int, std::default_delete<int> >' and 'int')` | 用 `<int>` 管理一批对象，然后写 `p[i]` | 数组形式必须写 `<int[]>`（或 `make_unique<int[]>(n)`） |
| `error: 'make_unique' is not a member of 'std'` | 忘了 `#include <memory>` | 加上 `#include <memory>`；`unique_ptr`、`shared_ptr` 都在这个头文件里 |
| `error: 'unique_ptr' is not a member of 'std'` | 同上，或写成了小写 `uniqueptr` 之类的错拼 | 补上头文件，并核对拼写（`std::unique_ptr`，中间有下划线） |
| 程序崩溃、退出码 `0xC0000374`（Linux 上 `free(): double free detected`） | 用 `get()` 拿到地址之后又 `delete` 了一次 | 只借不用还：`get()` 的结果不要交给 `delete` |
| 内存持续增长，编译无警告 | 用了 `release()` 之后忘了自己 `delete` | `release()` 只在"要把所有权交给别人"时使用，交出前后要想清谁来释放 |
| 写成 `std::unique_ptr<int> p(new int[10]);`，程序能编译 | 类型参数与分配方式不匹配：用 `delete` 去释放一批对象 | 管理数组要写 `<int[]>`；或者用 `make_unique<int[]>(10)` 让两者自动对齐 |

## 10 本章验收

1. 三个例程编译通过、`-Wall` 无警告，输出与 8.1–8.3 节逐行一致。
2. 能说出原始指针的两个问题（表达力不足、释放不安全），并说明 `unique_ptr` 分别怎么应对。
3. 能解释 `std::unique_ptr<int[]> pointer(new int[10]);` 里 `<int[]>` 的含义，以及写错成 `<int>` 会发生什么。
4. 能说出 `make_unique<int[]>(10)` 与 `make_unique<int>(10)` 的区别，并解释为什么 `unique_ptr` 不能复制。
5. 能区分 `get()`、`release()`、`reset()`、`swap()` 四个操作在所有权上的变化，并完成过 8.3 节的 `swap` 实验。
