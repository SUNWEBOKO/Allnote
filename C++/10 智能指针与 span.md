# 10 智能指针与 span

上一篇：[[09 指针与动态内存]]
下一篇：[[11 结构体与类]]

## 学习目标

完成本章后，你应当能够：

1. 说出原始指针"表达力不足、释放不安全"两个问题及其对应解法。
2. 用 `make_unique` / `make_shared` 创建 `unique_ptr` / `shared_ptr`，分清 `<int[]>` 数组形式与单个对象形式。
3. 用 `use_count()` 观察共享所有权，说明"计数归零才释放"的规则。
4. 遵守两条 `shared_ptr` 守则：不用同一个原始指针构造两个 `shared_ptr`，共享所有权成链不成环。
5. 写出接收 `std::span`（含只读与定长形式）的函数，并判断它何时会变成悬垂视图。

## 1 原始指针的两个问题

第 09 章用 `new` / `delete` 走通了"运行时自己申请内存"这条路，也为它列出了四条纪律。回头看这些纪律，会发现它们有一个共同点：**全靠人记住**。现代 C++ 之所以不鼓励直接使用原始指针，主要是两件事：

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

类型参数必须写 `<int[]>` 而不是 `<int>`：数组形式用的释放方式是 `delete[]`，单个对象形式用的是 `delete`。分配方式（`new int[10]`）和释放方式必须对应，类型参数写对了这一步才对得上。写错成 `<int>` 时，GCC 在本例中不会报警告，但释放时会用 `delete` 去销毁一批对象，行为是错误的。

说“接管”，是因为这一句执行完之后，那个 `new` 出来的地址就没有别的名字了，它只存在于 `unique_ptr` 内部。我们日常操作的对象是 `unique_ptr` 本身，不再需要单独保管那个原始指针。

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

它内部完成分配，并返回一个已经接管该内存的 `unique_ptr`，`new` 关键字就此消失，我们也不用再操心 `delete[]` 该不该写。返回类型由函数模板推导而来，用 `auto` 接最省事（第 02 章 6.4 节的原则：类型可以从表达式看出来就用 `auto`）。

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
2. 编译运行无异常、无崩溃（对照第 09 章的双重释放现象）；
3. 把它替换回第 09 章的原始指针写法，功能完全一样——说明智能指针没有改变使用方式，只是接管了释放责任。

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

这不是限制，而是设计意图的体现：**要转移所有权，就要明确地写出来**，不能不小心复制。转移的手段是 `std::move`，那属于移动语义的内容（第 14 章），本节只要记住"`unique_ptr` 独占，不能复制"。

## 7 什么时候用 `unique_ptr`

选择顺序和第 09 章末尾的建议是一致的：

- **一批数据、需要增删元素** → `std::vector`（第 07 章）。它连"长度"这个信息都替你管着。
- **一个对象，生命周期要动态决定** → `std::unique_ptr`。例如运行时创建、用完就丢的对象。
- **一批固定长度的数据，需要传出去让别人看** → 本章第 18 节的 `std::span`。
- **多个使用者共享同一块数据** → 本章第 8 节的 `std::shared_ptr`。

`unique_ptr` 的定位是"有明确且唯一的主人"的对象。只要场景符合这个描述，用它就比原始指针安全得多，而且没有任何额外的手工步骤——写好 `make_unique` 之后，剩下的交给析构函数。

## 8 为什么还需要另一种智能指针

本章第 7 节把 `unique_ptr` 的定位概括为"有明确且唯一的主人"：一块内存同一时刻只能有一个主人。它解决的是"这块内存归谁管、什么时候该还"这类有唯一答案的场景。

但程序里还有另一类需求：**同一份数据要被好几处代码用到，而且谁都不知道别人什么时候用完**。例如一份被多处引用的配置数据、一张被多个对象读的纹理、一个被多个模块挂着的缓存条目。这种场景下：

- 不能用 `unique_ptr`：它的所有权是唯一的，把它交给第二个人就意味着第一个人没有了；而直接复制 `unique_ptr` 是编译错误（本章第 6 节）。
- 也不该用原始指针：谁持有都行，但**没有任何机制保证最后会有人把它释放掉**，退回了第 09 章那套"靠人记得"的老问题。

要的是第三种语义：**多个持有者共同拥有同一块内存，内存必须一直活着，直到最后一个持有者也不再需要它**。这就是 `std::shared_ptr` 提供的"共享所有权"。

标准库对它的描述是：`std::shared_ptr` 是一种通过指针实现对象共享所有权的智能指针，多个 `shared_ptr` 对象可以共同拥有同一个对象。使用它时，可以保证这块内存**在对该内存的所有引用都消失之前不会被释放或删除**——也就是直到最后一个拥有它的 `shared_ptr` 离开作用域或者主动放手为止。

## 9 引用计数：共享所有权是怎么实现的

`shared_ptr` 能做到"最后一个才释放"，靠的是**引用计数**。它内部有一块共享的计数区域，记录着当前有多少个 `shared_ptr` 在拥有同一个对象：

- 创建一个 `shared_ptr` 管住某块内存时，计数设为 1；
- 每复制出一个新的 `shared_ptr`（指向同一对象），计数加 1；
- 每销毁一个（离开作用域）或主动放手（`reset`），计数减 1；
- **计数减到 0 的那一刻，才去释放被管理的对象。**

复制、销毁这两个动作散落在程序的各个角落，但规则的产出只有一个："还有人需要它，就绝不释放；没人需要了，立刻释放"。这正好补上了原始指针缺失的那一环——**释放时机不再需要人判断，而是由计数自动决定**。

使用上，`shared_ptr` 与 `unique_ptr` 几乎一样：模板参数、创建方式、下标访问都相同。真正的区别只有一条：**`shared_ptr` 可以复制，而且复制是正常操作，不是错误**。

## 10 创建与复制

`shared_ptr` 同样定义在 `<memory>` 里。创建方式与 `unique_ptr` 对照着看：

```cpp
std::shared_ptr<int[]> pointer1(new int[10]);      // 与 unique_ptr 的写法几乎相同
```

类型参数 `<int[]>` 的含义也和本章第 3 节一样：管理的是一批 `int`，将来要用 `delete[]` 释放；写错成 `<int>` 就会用 `delete` 去释放一批对象，分配与释放方式不匹配。

区别从下面这一行开始：

```cpp
std::shared_ptr<int[]> pointer2 = pointer1;      // 复制：现在有两个持有者
```

这行代码在 `unique_ptr` 上是编译错误，在 `shared_ptr` 上是完全正常的操作。执行之后：

- 两个 `shared_ptr` 保存的是**同一个地址**，通过任何一个修改数据，用另一个读出来的就是同一个值；
- 内部计数从 1 变成 2；
- 任何一份被销毁都不会立即释放内存——因为还有另一份在用它。

这就是共享所有权的具体表现。要注意的是，共享出去的是"引用"，不是内存本身：两个 `shared_ptr` 变量本身各占一点空间（还有一个指向共享计数的内部指针），但它们管理的对象只有一份。

## 11 `use_count()`：看清有几个持有者

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

## 12 `make_shared`：省掉 `new`

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

所以本课程从第 04 章起统一使用 `-std=c++20` 编译；如果换了编译器或标准版本，这一行是最先会暴露问题的地方。

另一个和 `make_unique` 相同的好处：分配内存和构造对象一次完成，不会出现"内存已分配但还没交给智能指针"的中间状态。

## 13 常用成员函数

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

## 14 把 `shared_ptr` 传给函数

共享所有权的典型用法就是把同一份数据交给多个使用者。把 `shared_ptr` 作为参数传出去时，传的始终只是"一份引用"，而不是内存本身：

```cpp
void printValue(std::shared_ptr<int[]> p, int index)
{
    std::cout << p.use_count() << std::endl;     // 函数执行期间多了一份引用
    std::cout << p[index] << std::endl;
}
```

形参写成 `shared_ptr`（按值传递）时，实参是被**复制**进来的：函数执行期间多一份引用，`use_count()` 比调用前大 1；函数返回、形参销毁，计数再减回去。这正好说明共享所有权的语义——函数里拿到的和自己手里的是同一份，函数不会因为持有它就阻止别人释放，也不会在返回时把它释放掉。

值得注意的是，**按值传递 `shared_ptr` 并不是日常推荐写法**：每复制一次都要对引用计数做一次原子增减，代价不小。更常见的做法是传 `const std::shared_ptr<T>&`（第 08 章的"只读引用"），只有在确实需要"持有这份引用"时才按值传。

## 15 两条必须记住的守则

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

## 16 与其它方案的选择

| 需求 | 方案 | 位置 |
| --- | --- | --- |
| 一批可变长度的数据 | `std::vector` | 第 07 章 |
| 一个对象，生命周期动态决定，主人唯一 | `std::unique_ptr` | 本章第 7 节 |
| 一份数据被多处使用，没人能确定谁最后用完 | `std::shared_ptr` | 本章第 8 节 |
| 只想传递一段连续数据、不参与所有权 | `std::span` | 本章第 18 节 |

判断的依据是**所有权**："谁负责释放"这个问题有唯一答案就用 `unique_ptr`；答案取决于多个使用者，就用 `shared_ptr`；如果这个问题根本不需要回答（用完就丢、容器自己管），说明不该用指针。

## 17 拥有与只是查看

到此为止，我们见过的内存管理方案——`std::vector`、`unique_ptr`、`shared_ptr`——全都在**拥有一块内存**：

- `std::vector`（第 07 章）自己动态分配内存，对象销毁时自己把内存还回去；
- `std::unique_ptr`（本章第 2 节）和 `std::shared_ptr`（本章第 8 节）是管理内存所有权的指针，谁负责释放由所有权规则决定。

"拥有"意味着两件事：**你负责这块内存的分配与释放**，并且**你有权修改它、也有权决定它的大小**。

但有一类需求跟"拥有"无关。假设你在写一个绘图程序，手里已经有一个装满数据的 `std::vector<int>`，现在只想**把其中某一段打印出来**。这个打印函数关心的事情只有一件：它拿到的是**一串连续存放的整数**。它不关心这串整数是 `vector` 提供的、`std::array` 提供的，还是别处的一块内存；它也不会去分配、释放、增删任何元素。

如果硬要让这个函数"接收一个容器"，我们只有两种坏选择：要么把容器类型写死（来一个 `std::array` 就得再写一份同样的函数），要么只接收迭代器，把"容器的开始"和"容器的结束"两个参数都传进来。两种写法都别扭，后面第 19 节会具体看别扭在哪里。

C++20 起，标准库给出了第三种选择：`std::span`。

## 18 span 是什么

**`std::span` 描述了一个可以引用一段连续对象序列的对象，第一个元素从索引 0 开始，长度可以是静态的也可以是动态的。** 它定义在头文件 `<span>` 中（和 `vector` 在 `<vector>` 里、`array` 在 `<array>` 里一样，用什么就要包含什么）。

拆开这句话：

- **"引用"**：`span` 本身不存放元素。它内部只有两样东西——**首元素的地址**和**元素个数**。这两样加起来就足以描述"一段连续的数据"，因为元素是挨着放的，知道头在哪、有几个，剩下每个元素的地址就能算出来。
- **"连续对象序列"**：元素必须是一个挨一个地存放的。`std::vector`、`std::array`、内置数组都满足这一点。这也是 `span` 能用下标 `s[i]` 访问、能算出 `s.data()` 的原因。
- **"首元素从索引 0 开始"**：不管这段数据原本是容器的第几个元素，只要进了 `span`，它在 `span` 里就是第 0 个。
- **"静态或动态长度"**：元素个数可以写进类型里，比如 `std::span<int, 3>`；也可以不写，比如 `std::span<int>`，表示长度在运行期确定。

因此 `span` 提供的是**容器级别的抽象，但不附带所有权**。凡是"连续容器"上顺手的操作，它基本都有：范围 `for` 遍历、下标访问、`.size()`、`.data()`。而它会**接管释放内存**这种责任吗？不会——它从名字到设计都在说"我只是看看，东西不是我的"。

**一个必须记住的结论**：`span` 记的是地址和长度，而不是它自己持有一份数据。所以

- 拷贝一个 `span` 非常便宜，只是复制两个值；
- 反过来，**原数据一旦消失或搬家，`span` 记的地址就失效了**，此时再用它就是未定义行为（第 22 节会专门讲）。

## 19 不用 span 的话，函数参数会变成什么样

回到第 17 节的打印函数。假设我们不用 `span`，想表达"打印这个向量的某一部分"，其实只有下面几种写法。

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

## 20 用 span 当参数：同一个函数服务所有连续容器

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

函数体跟第 04 章打印数组的写法几乎一样——`span` 支持范围 `for`，元素访问方式也和第 03、07 章一致。真正的变化在参数类型上，`std::span<int>` 现在读起来是一句准确的要求：**给我一段连续存放的 `int`，别的我不管。**

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

## 21 只看一部分：起始位置 + 元素个数

`span` 可以做容器做不到的一件事：**把"容器的某一段"单独变成一个对象**。做法是构造 `span` 时给出"从哪里开始"和"看几个元素"：

```cpp
std::vector<int> myVector {1, 2, 3, 4, 5};
std::span<int> firstTwo {myVector.begin(), 2};       // 1 2
std::span<int> middle  {myVector.begin() + 1, 3};    // 2 3 4
```

对照着看这两个例子：`begin()` 是第 0 个元素的位置，所以 `firstTwo` 从下标 0 开始，取 2 个，是 1、2；`begin() + 1` 往后挪一个，指向原来的下标 1，从那里取 3 个，就是下标 1、2、3，即 2、3、4。

于是 `span` 里的下标和原容器的下标之间有一个固定关系：**`span[i]` 就是原容器的 `原起点下标 + i`**。上面 `middle` 的 `middle[0]` 是原容器的下标 1，`middle[2]` 是原容器的下标 3。注意 `middle` 本身只有 0、1、2 三个下标，**用 `span` 自己的下标访问时永远从 0 开始**，这一点和第 18 节"首元素从索引 0 开始"是同一件事。

有了这个能力，第 19 节那个函数签名可以一直保持只有一个参数：

```cpp
printSpan(myVector);                                    // 整个向量
printSpan(std::span<int> {myVector.begin(), 2});        // 前两个
printSpan(std::span<int> {myVector.begin() + 1, 3});    // 中间三个
```

需要打印的范围在**调用处**决定，函数内部一行都不用改，也不需要知道这段数据是整块还是截出来的。这正是 `span` 的构造函数里"从一段值范围构造"那条规则带来的好处：只要能表示成"起点 + 个数"或"起点 + 终点"，就能变成 `span`。

## 22 不拥有数据，意味着什么

`span` 不拥有数据，这句话有两面。好的一面是零拷贝、参数只有一个；需要时刻警惕的一面是**它只是记录地址，不保证那地址还有效**。

**第一面：通过 span 写入，改的就是原数据。**

```cpp
std::span<int> middle {myVector.begin() + 1, 3};
middle[0] = 99;              // 等于写 myVector[1] = 99
```

这里没有"同步"也没有"传递"——`span` 和 `vector` 说的本来就是同一块内存（例程 `span_subview` 的 Demo C 打印了整个 `vector`，可以看到 2 变成了 99）。这一点和引用（第 08 章）的道理相通：别名不是副本，改一处就是改那一处。

**第二面：原数据消失或搬家之后，span 就成了悬垂视图。**

`span` 记下的是一个地址。如果那个地址背后的数据没了，`span` 不会收到任何通知，也不会自动变空。典型场景有两个：

- **数据本来就是个临时对象**。从临时的 `vector` 构造出 `span`，语句结束后这个临时的 `vector` 已经销毁，`span` 记的地址也就无效了。
- **容器搬家了**。`vector` 的容量用满时会重新申请一块更大的内存，把元素搬过去，原来的地址就作废了。此时旧的 `span` 仍然指着那块已经被释放的内存。

这两种情况编译器**都不会报错**，程序可能继续打印出乱七八糟的值、也可能直接崩溃——这就是未定义行为最典型的形态（和"函数漏了 `return` 却能编译"一样，属于"能跑、结果不可信"的一类问题）。判断规则很简单：**`span` 的生命周期必须短于它所指数据的生命周期，并且在这期间不能让容器重新分配**。写函数时，`span` 作为参数是安全的——调用期间实参容器一定活着；把 `span` 存进别的对象、或者在容器 `push_back` 之后继续用旧 `span`，才需要格外小心。

## 23 固定长度与只读：两个常见的参数写法

**固定长度：把长度写进类型。**

```cpp
void printFixed(std::span<int, 3> values);
```

第二个模板参数是元素个数，它是**类型的一部分**，所以"长度为 3"这件事由编译器负责检查：传进来一段长度不对的数据，编译直接失败，不会拖到运行时才发现（改值实验见 24.9 节）。省略第二个参数时长度是动态的，也就是前面一直用的 `std::span<int>`。

**只读：把元素类型写成 `const`。**

```cpp
void printReadOnly(std::span<const int> values);
```

元素类型是 `const int`，意思是"我只看，不改写"。它的好处有三层：

1. 读函数的签名就能知道它不会修改数据，不必去读函数体；
2. `const std::vector<int>` 这类只读容器**只能**转成 `std::span<const int>`，转不成 `std::span<int>`；把参数写成只读版本，能接收的实参范围更大；
3. `std::span<int>` 可以隐式转换成 `std::span<const int>`，反过来不行——这保证了"只读"这层承诺不会被绕过。

**怎么选**：参数只读取数据时，写成 `std::span<const T>`；需要修改数据时，写 `std::span<T>`；只有当"长度固定"本身是函数要求的一部分、并且希望编译期就卡住错误时，才把长度写进类型（`std::span<T, N>`）。至于 `span` 和"传引用"的取舍：`std::vector<int>&` 表达"我就要这个向量本身"，`std::span<int>` 表达"我只要一段连续的 int"，**当函数真的不需要知道容器类型时，`span` 是更准确的表达**。

## 24 动手实验

### 24.1 实验一（unique_ptr）：接管 `new` 出来的数组

例程在 `E:\CPP_Code\CppFromScratch\ch19_unique_ptr\` 下，三个程序各占一个文件夹。

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

**结果解释**：`pointer[4] = 16`、`pointer[7] = 49` 是 4 和 7 的平方，说明下标访问和原始指针数组一样可用，而填写这些值的循环里没有任何与释放相关的代码。程序里一个 `delete` 都没有——这是本节要看的重点。

**验收标准**：编译 `-Wall` 无警告，输出与上面逐行一致；在源文件里搜索 `delete`，结果应为 0 处（注释里提到的除外）。

**改值实验**：把打印的两个下标从 4、7 改成 2、8。重新编译运行前先预测：应该是 `pointer[2] = 4` 与 `pointer[8] = 64`，即 `i * i`。这能验证填充循环和下标访问确实是同一套索引。

### 24.2 实验二（unique_ptr）：用 `make_unique` 创建

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

三步走下来能看清一件事：**元素个数只存在于那个字面量里**，没有任何机制替你检查"下标和长度是否匹配"。漏改循环时程序既不报错也不警告，只是安静地给出 0。原始指针和 `unique_ptr` 都还没解决这个表达力问题，本章第 18 节的定长 `std::span<T, N>` 才把长度补进类型里（动态长度的 `std::span<int>` 例外，它的长度仍在运行期确定）。

### 24.3 实验三（unique_ptr）：`get` / `release` / `reset` / `swap`

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

### 24.4 实验一（shared_ptr）：两个持有者与计数变化

例程在 `E:\CPP_Code\CppFromScratch\ch20_shared_ptr\` 下，三个程序各占一个文件夹。

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

### 24.5 实验二（shared_ptr）：`make_shared` 与按值传参

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

### 24.6 实验三（shared_ptr）：`get` / `swap` / `reset`

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

### 24.7 实验一（span）：一个函数服务三种容器（`span_basic`）

三个例程都在 `E:\CPP_Code\CppFromScratch\ch21_span\` 下，各占一个文件夹。编译器用 MSYS2 的 GCC，`span` 是 C++20 的特性，**必须带 `-std=c++20`**（更老的编译器可能根本不支持）。

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

**改值实验**：把 `std::array<int, 3> myArray {7, 8, 9};` 这一整行改成 `std::array<int, 4> myArray {7, 8, 9, 10};`——注意**类型参数也要从 3 改成 4**。如果只改花括号里的值、把类型参数留成 `3`，按字面执行会直接报 `too many initializers for 'std::array<int, 3>'`。改对以后再编译运行，**先自己预判**：`printSpan` 完全没改，Demo B 的输出会变成什么？应该是 `7 8 9 10`。这直接说明函数的参数类型写 `std::span<int>` 之后，它对容器长度、容器种类都不再敏感。

### 24.8 实验二（span）：只看一部分，并且改动它（`span_subview`）

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

**改值实验**：把构造 `middle` 的 `myVector.begin() + 1` 改成 `myVector.begin()`（不偏移），`middle[0] = 99;` 这一句不动，重新编译运行。**预判**：Demo B 会变成 `1 2 3`，Demo C 会变成 `99 2 3 4 5`（被改写的是第一个元素），Demo D 也会跟着从 `99 3 4` 变成 `99 2 3`——`middle` 现在从原容器的下标 0 开始，`middle[0]` 就是那个被改成 99 的第一个元素。核对后能确认"`span` 的下标从 0 开始、映射到原容器起点"这条规则。

### 24.9 实验三（span）：固定长度与只读视图（`span_extent`）

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

**改值实验一**：把 `void printFixed(std::span<int, 3> values)` 里的 `3` 改成 `4`，其他不动，重新编译。**预判**：这一步编译不过，因为 `std::array<int, 3>` 和 `std::span<int, 3>` 都转不成 `std::span<int, 4>`。实际报错是两条（第一条即关键信息）：

```text
error: could not convert 'myArray' from 'std::array<int, 3>' to 'std::span<int, 4>'
error: could not convert 'fixed' from 'span<[...],3>' to 'span<[...],4>'
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
