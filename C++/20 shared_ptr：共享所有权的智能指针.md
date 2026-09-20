# 20 shared_ptr：共享所有权的智能指针

上一篇：[[19 unique_ptr：独占所有权的智能指针]]
下一篇：[[21 span：不拥有数据的连续视图]]

## 学习目标

完成本章后，你应当能够：

1. 说出为什么"一块内存只有一个主人"的 `unique_ptr` 不够用。
2. 用 `std::shared_ptr` 创建共享所有权，并说明复制它意味着什么。
3. 用 `use_count()` 观察当前有几个持有者，并说明计数归零才释放的规则。
4. 用 `std::make_shared` 创建共享指针，并说出数组形式需要哪个 C++ 标准。
5. 说出"不要用同一个原始指针构造两个 `shared_ptr`"这条守则的原因和后果。

## 1 为什么还需要另一种智能指针

第 19 章的 `unique_ptr` 管的是"独一份"的所有权：一块内存同一时刻只能有一个主人。它解决的是"这块内存归谁管、什么时候该还"这类有唯一答案的场景。

但程序里还有另一类需求：**同一份数据要被好几处代码用到，而且谁都不知道别人什么时候用完**。例如一份被多处引用的配置数据、一张被多个对象读的纹理、一个被多个模块挂着的缓存条目。这种场景下：

- 不能用 `unique_ptr`：它的所有权是唯一的，把它交给第二个人就意味着第一个人没有了；而直接复制 `unique_ptr` 是编译错误（第 19 章 6 节）。
- 也不该用原始指针：谁持有都行，但**没有任何机制保证最后会有人把它释放掉**，退回了第 18 章那套"靠人记得"的老问题。

要的是第三种语义：**多个持有者共同拥有同一块内存，内存必须一直活着，直到最后一个持有者也不再需要它**。这就是 `std::shared_ptr` 提供的"共享所有权"。

标准库对它的描述是：`std::shared_ptr` 是一种通过指针实现对象共享所有权的智能指针，多个 `shared_ptr` 对象可以共同拥有同一个对象。使用它时，可以保证这块内存**在对该内存的所有引用都消失之前不会被释放或删除**——也就是直到最后一个拥有它的 `shared_ptr` 离开作用域或者主动放手为止。

## 2 引用计数：共享所有权是怎么实现的

`shared_ptr` 能做到"最后一个才释放"，靠的是**引用计数**。它内部有一块共享的计数区域，记录着当前有多少个 `shared_ptr` 在拥有同一个对象：

- 创建一个 `shared_ptr` 管住某块内存时，计数设为 1；
- 每复制出一个新的 `shared_ptr`（指向同一对象），计数加 1；
- 每销毁一个（离开作用域）或主动放手（`reset`），计数减 1；
- **计数减到 0 的那一刻，才去释放被管理的对象。**

复制、销毁这两个动作散落在程序的各个角落，但规则的产出只有一个："还有人需要它，就绝不释放；没人需要了，立刻释放"。这正好补上了原始指针缺失的那一环——**释放时机不再需要人判断，而是由计数自动决定**。

使用上，`shared_ptr` 与 `unique_ptr` 几乎一样：模板参数、创建方式、下标访问都相同。真正的区别只有一条：**`shared_ptr` 可以复制，而且复制是正常操作，不是错误**。

## 3 创建与复制

`shared_ptr` 同样定义在 `<memory>` 里。创建方式与 `unique_ptr` 对照着看：

```cpp
std::shared_ptr<int[]> pointer1(new int[10]);      // 与 unique_ptr 的写法几乎相同
```

类型参数 `<int[]>` 的含义也和上一章一样：管理的是一批 `int`，将来要用 `delete[]` 释放；写错成 `<int>` 就会用 `delete` 去释放一批对象，分配与释放方式不匹配。

区别从下面这一行开始：

```cpp
std::shared_ptr<int[]> pointer2 = pointer1;      // 复制：现在有两个持有者
```

这行代码在 `unique_ptr` 上是编译错误，在 `shared_ptr` 上是完全正常的操作。执行之后：

- 两个 `shared_ptr` 保存的是**同一个地址**，通过任何一个修改数据，用另一个读出来的就是同一个值；
- 内部计数从 1 变成 2；
- 任何一份被销毁都不会立即释放内存——因为还有另一份在用它。

这就是共享所有权的具体表现。要注意的是，共享出去的是"引用"，不是内存本身：两个 `shared_ptr` 变量本身各占一点空间（还有一个指向共享计数的内部指针），但它们管理的对象只有一份。

## 4 `use_count()`：看清有几个持有者

`use_count()` 返回当前有多少个 `shared_ptr` 共同拥有同一个对象。它是理解共享所有权最直接的工具，也是排查"到底谁还占着这块内存"时第一个该看的数字：

```cpp
std::cout << pointer1.use_count() << std::endl;      // 有两个持有者时输出 2
```

`reset()` 则是"我这份不要了"：

```cpp
pointer2.reset();                                     // 计数从 2 减到 1
```

注意这里的关键点：**计数减到 1 时内存不会被释放**。原来的数据还在，`pointer1` 照常能读能写。这正是共享所有权要保证的事情——"直到没有更多引用之前，对象不会被提前删掉"。只有计数归零（本例中是程序结束时 `pointer1` 也被销毁）时，那块内存才真正被释放。

想观察"释放发生的时刻"，可以给两个 `shared_ptr` 都安排离开作用域的时机（比如放进一对花括号组成的作用域），计数 2 → 1 → 0，最后一步才等于释放。

## 5 `make_shared`：省掉 `new`

和 `make_unique` 对应的工厂函数是 `std::make_shared`，用法也对应：

```cpp
auto pointer1 = std::make_shared<int[]>(10);     // 分配 10 个 int 的共享数组
```

它传进去的是**元素个数**，内部完成分配并返回一个已经接管该内存的 `shared_ptr`，程序里不用再写 `new`，得到的对象数与 `make_unique<int[]>(10)` 一样是 10 个。

这里有一个**版本要求**必须记住：

- **`make_shared<int[]>(10)`（数组形式）从 C++20 才开始支持**。用旧标准编译这一行会直接报错：

  ```text
  error: no matching function for call to 'make_shared<int []>(int)'
  ```

- 在 C++20 之前，只能写成显式的 `std::shared_ptr<int[]> pointer1(new int[10]);`。功能一样，只是 `new` 得自己写出来。这也解释了为什么老编译器会直接卡在这里：`make_shared` 的数组形式需要编译器同时支持 C++20 的对应改动，较老的版本（例如 g++ 11）即使加了 `-std=c++20` 也可能报同一个"没有匹配的函数"的错，换到 g++ 12 及以上就正常了。

所以本课程从第 09 章起统一使用 `-std=c++20` 编译；如果换了编译器或标准版本，这一行是最先会暴露问题的地方。

另一个和 `make_unique` 相同的好处：分配内存和构造对象一次完成，不会出现"内存已分配但还没交给智能指针"的中间状态。

## 6 常用成员函数

`shared_ptr` 提供的操作与 `unique_ptr` 高度一致，只有 `release` 没有：

| 成员函数 | 作用 | 计数怎么变 |
| --- | --- | --- |
| `use_count()` | 返回当前持有者个数 | 不变 |
| `get()` | 返回内部保存的原始指针，只是借出来看看 | 不变 |
| `reset()` | 当前这一份不再持有该对象 | 减 1；减到 0 时才释放内存 |
| `reset(p)` | 释放原来持有的对象，改为接管 `p` | 旧对象减 1，新对象加 1 |
| `swap(other)` | 交换两个 `shared_ptr` 管理的东西 | 交换后计数跟着对象走 |

数组形式同样有 `operator[]`，所以下标访问的写法和 `unique_ptr` 一模一样：

```cpp
pointer1[3] = 9;                                 // 写
std::cout << pointer2[3] << std::endl;           // 用另一个持有者读出同一个 9
```

**没有 `release()` 是设计上的必然**：`release` 的语义是"我把所有权交出去、自己不再负责"，而共享所有权里根本不存在"唯一的所有权凭证"可以交出去。想让这一份不再持有，用 `reset()`。

**`get()` 借来的地址仍然不能 `delete`**：这块内存可能还有别的持有者，而且 `shared_ptr` 自己会在计数归零时释放它，你再去释放一次就是重复释放。

## 7 把 `shared_ptr` 传给函数

共享所有权的典型用法就是把同一份数据交给多个使用者。把 `shared_ptr` 作为参数传出去时，传的始终只是"一份引用"，而不是内存本身：

```cpp
void printValue(std::shared_ptr<int[]> p, int index)
{
    std::cout << p.use_count() << std::endl;     // 函数执行期间多了一份引用
    std::cout << p[index] << std::endl;
}
```

形参写成 `shared_ptr`（按值传递）时，实参是被**复制**进来的：函数执行期间多一份引用，`use_count()` 比调用前大 1；函数返回、形参销毁，计数再减回去。这正好说明共享所有权的语义——函数里拿到的和自己手里的是同一份，函数不会因为持有它就阻止别人释放，也不会在返回时把它释放掉。

值得注意的是，**按值传递 `shared_ptr` 并不是日常推荐写法**：每复制一次都要对引用计数做一次原子增减，代价不小。更常见的做法是传 `const std::shared_ptr<T>&`（第 16 章的"只读引用"），只有在确实需要"持有这份引用"时才按值传。

## 8 两条必须记住的守则

**第一条：永远不要用同一个原始指针构造两个 `shared_ptr`。**

```cpp
int* raw = new int(5);
std::shared_ptr<int> a(raw);
std::shared_ptr<int> b(raw);      // 错！这样会得到两套互不知情的计数
```

这段代码能编译，`a.use_count()` 和 `b.use_count()` 打印出来都是 1。问题在于两个 `shared_ptr` 各自维护一份计数（各为 1），都以为自己该释放这块内存，于是析构时同一块内存被释放两次。实测现象是程序在销毁这两个指针时直接异常退出（Windows 上退出码 `0xC0000374`，堆损坏；Linux 上会打印 `free(): double free detected`）。

正确做法只有一种：**用 `make_shared` 创建，拿到之后凡是需要多一个持有者的地方一律"复制 `shared_ptr`"**，不再碰原始指针。如果内存是别人 `new` 好了交给你的，那就在刚拿到的那一刻立刻交给 `shared_ptr`（`std::shared_ptr<T> a(raw);`），之后 `raw` 就不要再用于构造第二个 `shared_ptr`。

**第二条：互相持有会形成环，环上的对象永远不会被释放。**

如果对象 A 里有一个 `shared_ptr` 指向 B，B 里也有一个 `shared_ptr` 指向 A，那么即使外面没有任何人在用它们，A 和 B 的计数也都至少是 1，谁都不会先释放。这是引用计数模型的固有性质，不是使用错误，但它造成的后果和内存泄漏一样。绕过它需要"不增加计数的引用"这类工具，超出了本章范围；现阶段只要记住：**共享所有权要成链，不要成环**。

## 9 与其它方案的选择

| 需求 | 方案 | 章节 |
| --- | --- | --- |
| 一批可变长度的数据 | `std::vector` | 第 14 章 |
| 一个对象，生命周期动态决定，主人唯一 | `std::unique_ptr` | 第 19 章 |
| 一份数据被多处使用，没人能确定谁最后用完 | `std::shared_ptr` | 本章 |
| 只想传递一段连续数据、不参与所有权 | `std::span` | 第 21 章 |

判断的依据是**所有权**："谁负责释放"这个问题有唯一答案就用 `unique_ptr`；答案取决于多个使用者，就用 `shared_ptr`；如果这个问题根本不需要回答（用完就丢、容器自己管），说明不该用指针。

## 10 动手实验

例程在 `E:\CPP_Code\CppFromScratch\ch20_shared_ptr\` 下，三个程序各占一个文件夹。

### 10.1 实验一：两个持有者与计数变化

`E:\CPP_Code\CppFromScratch\ch20_shared_ptr\shared_ptr_basic\shared_ptr_basic.cpp` 演示 `shared_ptr<int[]>` 接管 `new int[10]`、复制后的计数、其中一个 `reset()` 之后另一个仍然有效。

编译运行（在 `E:\CPP_Code\CppFromScratch\ch20_shared_ptr\shared_ptr_basic` 目录下执行）：

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g shared_ptr_basic.cpp -o shared_ptr_basic.exe
./shared_ptr_basic.exe
```

**预期输出**（逐字符一致）：

```text
=== Demo A: two shared_ptr objects own the same array ===
pointer1.use_count() = 2
pointer1 and pointer2 point to the same memory: 1
=== Demo B: one of them lets go early ===
after pointer2.reset(), pointer1.use_count() = 1
the array is still alive: pointer1[3] = 9
```

**结果解释**：第一行 `2` 说明复制确实让持有者变成了两个。第二行的 `1`（真）说明两个 `shared_ptr` 的地址相同，是同一块内存。第四行 `1` 说明 `reset()` 后计数减了 1；最后一行 `pointer1[3] = 9` 证明内存没有被提前释放——这正是共享所有权要保证的事情。程序里没有任何 `delete`。

**验收标准**：编译 `-Wall` 无警告，输出与上面逐行一致；能说出为什么 `pointer2.reset()` 之后数组仍然可以访问。

**改值实验**：把 `pointer2.reset();` 那一行删掉。预测：`after pointer2.reset(), ...` 那一行会变成 `pointer1.use_count() = 2`，最后一行仍然是 `pointer1[3] = 9`。注意提示文字里写的是 `pointer2.reset()`，它只是固定字符串，变的是后面的计数。

### 10.2 实验二：`make_shared` 与按值传参

`E:\CPP_Code\CppFromScratch\ch20_shared_ptr\make_shared_array\make_shared_array.cpp` 演示 `make_shared<int[]>(10)`（`new` 消失）、两个持有者共享，以及把 `shared_ptr` 按值传进函数时计数加一。

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g make_shared_array.cpp -o make_shared_array.exe
./make_shared_array.exe
```

**预期输出**（逐字符一致）：

```text
=== Demo A: make_shared builds the shared array ===
pointer1.use_count() = 2
pointer1[3] = 9, pointer2[3] = 9
=== Demo B: passing a copy into a function adds one reference ===
inside printValue, use_count() = 3
printValue read pointer1[6] = 36
back in main, use_count() = 2
```

**结果解释**：`pointer1[3] = 9, pointer2[3] = 9` 是同一块内存被两个名字读到的同一个值。函数内计数 `3`（原来是 2，形参复制进来加 1），返回后回到 `2`，说明函数里的那份引用是临时的。`printValue read pointer1[6] = 36` 是 6 的平方，说明函数能读到调用方写进去的数据。

**验收标准**：编译 `-Wall` 无警告，输出与上面逐行一致；能说出为什么函数内的计数是 3 而不是 2。

**改值实验**：把 `printValue(pointer1, 6);` 里的索引 `6` 改成 `8`。预测：该行输出变成 `printValue read pointer1[8] = 64`（8 的平方），计数两行不变——因为计数只与"有几个持有者"有关，和数据本身无关。再进一步：把函数形参改成 `const std::shared_ptr<int[]>&`，预期计数变成 2（不再复制）。这一条如果尝试，注意函数名里的 `printValue` 提示文字不用改。

### 10.3 实验三：`get` / `swap` / `reset`

`E:\CPP_Code\CppFromScratch\ch20_shared_ptr\shared_ptr_api\shared_ptr_api.cpp` 演示借用地址、交换管理对象、以及 `reset()` 让出一份引用后计数归零与归一的区别。

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g shared_ptr_api.cpp -o shared_ptr_api.exe
./shared_ptr_api.exe
```

**预期输出**（逐字符一致）：

```text
=== Demo A: two shared_ptr sharing one int ===
*a = 5, a.use_count() = 2
a and b point to the same object: 1
*a.get() = 5
=== Demo B: swap() exchanges the managed objects ===
before swap: *a = 5, *c = 9
after swap: *a = 9, *c = 5
now c shares its object with b, c.use_count() = 2
=== Demo C: reset() drops one owner ===
before reset: a.use_count() = 1, c.use_count() = 2
after reset: c.use_count() = 0, a.use_count() = 1
the object a still owns is alive: *a = 9
```

**结果解释**：Demo A 中 `b` 是 `a` 的副本，计数为 2。Demo B 中 `swap` 交换的是"谁管哪块内存"，两个值的位置对调；交换后 `c` 管的正是原来和 `b` 共享的那个对象，所以 `c.use_count()` 是 2。Demo C 中 `c.reset()` 让 `c` 不再持有任何东西（计数 0），而 `a` 管的对象完全不受影响——`*a` 仍然是 9。

**验收标准**：编译 `-Wall` 无警告，输出与上面逐行一致；能解释 `after reset: c.use_count() = 0, a.use_count() = 1` 这两处计数为什么不相关（它们管着不同的对象）。

**改值实验**：把 `auto c = std::make_shared<int>(9);` 改成 `std::shared_ptr<int> c = b;`（让 `c` 从创建起就和 `a`、`b` 共享同一个对象）。预测并验证下面几行：

- `before swap: *a = 5, *c = 5`——不再有值为 9 的那个对象；
- `after swap: *a = 5, *c = 5`——`a` 和 `c` 本来就管着同一个对象，交换等于什么都没换；
- `now c shares its object with b, c.use_count() = 3`——三份引用指向同一个对象；
- Demo C 变成 `before reset: a.use_count() = 3, c.use_count() = 3`、`after reset: c.use_count() = 0, a.use_count() = 2`、`the object a still owns is alive: *a = 5`。

这个实验把"谁管哪块内存"（计数和交换要看的东西）和"内存里的值"（`*a` 看到的东西）彻底分开了。

## 11 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| 程序在退出时崩溃，退出码 `0xC0000374`（Linux 上 `free(): double free detected`），且 `use_count()` 打印出来都是 1 | 用同一个原始指针构造了两个 `shared_ptr`，形成两套独立的计数 | 用 `make_shared` 创建；要多一个持有者就复制 `shared_ptr`，不要再碰原始指针 |
| `error: no matching function for call to 'make_shared<int []>(int)'` / `error: no type named 'type' in 'struct std::enable_if<false, int []>'` | 用 C++17 或更早的标准编译了 `make_shared<int[]>(n)` | 数组形式的 `make_shared` 需要 C++20：加 `-std=c++20`；或改写成 `std::shared_ptr<int[]> p(new int[n]);` |
| `error: 'class std::shared_ptr<int>' has no member named 'release'` | 把 `shared_ptr` 当 `unique_ptr` 用 | `release` 是 `unique_ptr` 独有的；共享所有权下用 `reset()` 让出一份引用 |
| `error: conversion from 'int*' to non-scalar type 'std::shared_ptr<int>' requested` | 用 `=` 直接拿 `new` 的结果初始化：`std::shared_ptr<int> p = new int(5);` | 改成 `std::shared_ptr<int> p(new int(5));`，或直接用 `auto p = std::make_shared<int>(5);` |
| `error: 'make_shared' is not a member of 'std'` | 忘了 `#include <memory>` | 补上 `#include <memory>` |
| `error: no match for 'operator[]' (operand types are 'std::shared_ptr<int>' and 'int')` | 类型参数写成了 `<int>`，却用 `p[i]` 下标访问 | 管理一批对象要写 `<int[]>`（或 `make_shared<int[]>(n)`） |
| 内存持续增长、`use_count()` 始终降不到 0，编译无警告 | 两个对象互相持有 `shared_ptr`，形成环 | 共享所有权要成链不要成环；环上的引用计数永远至少为 1 |
| 用 `get()` 得到的地址去 `delete`，程序崩溃 | 那块内存仍由 `shared_ptr` 管理，会在计数归零时再释放一次 | `get()` 只用来把地址交给外部接口，绝不手工释放 |
| 把 `shared_ptr` 按值传参后，`use_count()` 比预期大 1，函数返回后又降回去 | 这是复制的正常现象：每一份引用都会计数 | 只读用途改成 `const std::shared_ptr<T>&`；按值传参只在确实要持有时使用 |
| `use_count()` 打印出 0 就以为内存已经释放了 | 0 表示这个指针自己不再持有对象，不代表它曾管理的对象此刻是否已被释放 | 计数要配合具体对象看：同一对象的所有持有者计数之和才是判断依据 |

## 12 本章验收

1. 三个例程编译通过、`-Wall` 无警告，输出与 10.1–10.3 节逐行一致。
2. 能说出 `unique_ptr` 与 `shared_ptr` 在所有权上的区别，并说明为什么共享所有权必须靠引用计数实现。
3. 能解释 `pointer1.use_count() = 2` 与复制 `shared_ptr` 之间的关系，以及 `reset()` 之后计数为何从 2 变成 1、内存为何还在。
4. 能说出 `make_shared<int[]>(10)` 需要的 C++ 标准版本，以及用旧标准编译时的报错文本。
5. 能说明"用同一个原始指针构造两个 `shared_ptr`"会发生什么，并完成过 10.3 节的计数改值实验。
