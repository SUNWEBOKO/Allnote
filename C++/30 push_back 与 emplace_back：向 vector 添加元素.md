# 30 push_back 与 emplace_back：向 vector 添加元素

上一篇：[[29 移动构造函数：自定义类型的资源转移]]
下一篇：[[31 继承与派生类：复用基类的成员]]

## 学习目标

完成本章后，你应当能够：

1. 说出 `push_back` 的两个重载分别在什么情况下被选中，并预判一次添加是复制还是移动。
2. 说明 `emplace_back` 与 `push_back` 在"什么时候造对象"上的根本区别。
3. 用 `emplace_back` 把构造函数的参数直接交给容器，并说出它省掉了哪一步。
4. 说明 `vector` 扩容时已有元素会经历什么，并用 `reserve` 避免重复搬运。
5. 给一个添加元素的场景选对方法，并说出理由。

## 1 为什么要重新看一次添加元素

`std::vector` 是标准库里最常用的容器之一，理由很直接：数组的长度是固定的（第 05 章的 `std::array` 就是），而程序里真正需要的是**长度可变**的数组——数据一条条读进来，装多少要看运行时才知道。`std::vector` 解决的正是这件事，第 14 章已经讲过它的基本用法和 `push_back`。

之所以现在回头再讲一次添加元素，是因为 `push_back` 的含义在有了前面的知识之后才完整。它不只是"往末尾塞一个元素"，而是**在容器的内存里构造一个新元素**；而构造一个对象有多少条路（普通构造、拷贝构造、移动构造，第 24、26、29 章），这里就有多少种可能的开销。本章要做的就是把这几条路认清，再认识另一条更直接的路：`emplace_back`。

## 2 `push_back`：先有对象，再把它放进去

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

`push_back` 有两个重载，第 29 章已经在 `vector` 的语境里用过它们，这里把分工写全：

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

### 2.1 始终存在两块内存

把三条路径放在一起看，会发现一件共同的事：**不管走哪条路，都要先有一个"外面的对象"，再想办法把它弄进容器的内存里。**

- Demo A：`s` 建在 `main` 的栈上，`vector` 在自己的堆内存里拷出一份副本，两块内存内容相同、互相独立。
- Demo B：`t` 还是建在 `main` 的栈上，只是允许被搬空，于是资源（这里是 `x` 的值）被转移到容器里的新对象上。**对象还是构造了两块位置**，只是第二块不用从头计算，而是把第一块的东西接过来。
- Demo C：临时对象连名字都没有，看起来像是"省了一个对象"，但它依然被完整地构造出来了（第一行 `Constructor!`），然后才被搬进容器（第二行 `Move Constructor!`）。

所以 Demo D 才是这三段输出真正要说明的事：**三种写法的最终结果一模一样，`vector` 里都是一个正确的元素。差别只在"新元素是怎么来的"，而不在"它是什么"。**

顺带记住两条实用规则（第 28、29 章反复出现的）：

- **具名对象要搬进容器，必须显式写 `std::move`**，否则编译器按左值处理，会去找拷贝构造函数；
- **函数返回的临时对象和就地构造的临时对象本来就是右值，不用写 `std::move`**；`t.x after the move: 0` 这一行则是移动确实发生了的代价——源对象被清空了。

## 3 `emplace_back`：把参数交给容器，让它就地构造

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

### 3.1 `emplace_back` 的两个容易误解之处

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

### 3.2 一个名字上的提醒

这个概念的标准名字是 **`emplace_back`**（emplace 的意思是"放置于其中"），它做的事通常叫**原地构造**：new 出来的那块内存已经有了，只是还没有对象，于是把对象直接建在那里。它不是"另一种 `push_back`"，也不是"回填"——遇到"就地回填""in-place back"这类说法，认准 `emplace_back` 这个标识符即可。同理，`std::vector` 就是标准库的向量容器，不要和固定长度的"静态数组"（第 05 章的 `std::array`）混为一谈。

## 4 两者怎么选

| 你手上有什么 | 用哪个 | 理由 |
| --- | --- | --- |
| 已经有一个对象，且以后不再需要它 | `push_back(std::move(obj))` | 移动进容器，不复制 |
| 已经有一个对象，但后面还要用 | `push_back(obj)` | 只能复制，容器拿到的是独立副本 |
| 手里只有构造参数 | `emplace_back(args...)` | 省掉临时对象，只做一次构造 |
| 构造参数里带 `explicit` 构造函数 | `emplace_back(args...)` | `push_back` 无法用它做隐式转换 |
| 元素类型不能复制 | 移动进容器：`push_back(std::move(obj))` 或 `emplace_back(std::move(obj))` | 两条路都只要求可移动（第 29 章） |
| 类型既不能复制也不能移动 | `emplace_back(参数)` + 提前 `reserve` | 只要不发生扩容，就不需要搬运已有元素 |

用一句话概括：**有现成的对象就用 `push_back`，只有参数就用 `emplace_back`。** 至于"`emplace_back` 一定更快"，更准确的说法是：**它少了一次临时对象的构造与转移**。对于 `int` 这种构造成本几乎为零的元素，或者元素个数很少的情况，两者的差别小到测不出来；元素构造成本越高（比如元素是容器、字符串、持有堆内存的类），省下的那一次转移越可观。

## 5 所有添加方式都要面对的一件事：扩容

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

`copies = 0` 这一项同样值得看：这 12 次移动**全部走了移动构造函数，一次复制都没有**。这不是巧合，而是第 29 章那条规则的回报——只有当元素的移动构造函数是 `noexcept` 时，`vector` 才敢用移动把元素搬到新内存；如果它可能抛异常，容器为了不出"搬了一半失败"的局面，只能退回去复制。

Demo B 只多了一句 `v2.reserve(5);`：**提前把容量要到 5**。之后五次添加都不再触发扩容，`capacity` 一直是 5，搬运次数从 7 降到 0，只剩下 5 次必要的移动。这就是"已知要装多少个元素时先 `reserve`"的道理。

需要注意 `reserve` 与 `resize` 的区别：**`reserve` 只改容量，不改长度**，元素一个都没有；`resize` 改的是长度，会真的构造出元素。`reserve(5)` 之后 `size()` 仍然是 0，此时用 `v[0]` 访问是越界（未定义行为），要添加元素还是得靠 `push_back` / `emplace_back`。

## 6 动手实验

三个例程都在 `E:\CPP_Code\CppFromScratch\ch30_push_vs_emplace\` 下，各占一个文件夹。

### 6.1 实验一：`push_back` 的三条路径（`push_back_forms`）

`push_back_forms\push_back_forms.cpp` 分别用左值、`std::move(左值)`、临时对象各调一次 `push_back`。

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g push_back_forms.cpp -o push_back_forms.exe
./push_back_forms.exe
```

**预期现象**：输出与 2 节的十四行逐字符一致。

**验收标准**：`-Wall` 无警告；能对 Demo A、B、C 各说出"选中的是哪个重载、用的是哪个构造函数"，并解释 Demo D 为什么三种写法结果相同。

**改值实验**：把 Demo C 的 `v3.push_back(S(30));` 改成两行：

```cpp
S temp(30);
v3.push_back(temp);       // 故意不写 std::move
```

先判断输出会变成什么。预期是 Demo C 的第二行从 `Move Constructor! x = 30` 变成 **`Copy Constructor! x = 30`**，Demo D 的 `v3[0].x` 仍然是 `30`——临时对象一旦被赋给一个有名字的变量（`temp`），它就是左值了，不写 `std::move` 就退回复制。**这就是本章最容易犯的一个错误：把"造出来的对象"存进变量之后再 `push_back`，忘了 `std::move`。** 改完编译运行核对，然后还原。

**第二个改值实验**：把 `main` 里 `S s(10);` 改成 `S s(77);`，预期 Demo A 的两行都变成 `x = 77`，Demo D 的 `v1[0].x` 变成 `77`，其余各段完全不动——改的只是这个对象的值，不影响"哪条路径被走到"。

### 6.2 实验二：`emplace_back` 原地构造（`emplace_back_in_place`）

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

### 6.3 实验三：扩容与 `reserve`（`reallocation_and_reserve`）

`reallocation_and_reserve\reallocation_and_reserve.cpp` 用计数把扩容的代价量出来。

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g reallocation_and_reserve.cpp -o reallocation_and_reserve.exe
./reallocation_and_reserve.exe
```

**预期现象**：输出与 5 节的十六行逐字符一致（无 `reserve` 时 `moves = 12`，有 `reserve` 时 `moves = 5`，`copies` 两次都是 0）。容量序列（1、2、4、4、8）由本机 libstdc++ 的扩容策略决定，换成别的标准库实现可能不同，但"扩容会把已有元素搬走"这一条不变。

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

**必做实验**：把 `S(S&& other) noexcept` 里的 `noexcept` 删掉，重新编译运行。**预判**：两个 Demo 的 `copies` 都不再是 0，`moves` 也会变小——移动构造函数不再承诺不抛异常，`vector` 在扩容时只好退回去复制元素。这条实验直接说明了第 29 章为什么要给移动构造函数加 `noexcept`。看完还原。

## 7 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| `error: no matching function for call to 'std::vector<S>::push_back(int)'`（附注 `no known conversion for argument 1 from 'int' to 'const S&'`） | `push_back` 要的是对象，不是构造参数；构造函数的参数进不了 `push_back` | 用 `emplace_back(1, 2)` 把参数交给容器，或先造好对象再 `push_back` |
| `error: no matching function for call to 'std::vector<S>::emplace_back(<brace-enclosed initializer list>)'` | 写成了 `v.emplace_back({1, 2})`：花括号列表没有类型，`emplace_back` 无法推导该转发什么 | 直接写参数：`v.emplace_back(1, 2);` |
| `error: no matching function for call to 'construct_at(std::unique_ptr<int>*&, const std::unique_ptr<int>&)'`（报错链里出现 `push_back(const value_type&)`） | 把具名的 `unique_ptr` 直接 `push_back`，选中了需要复制的重载（第 28 章） | 加 `std::move`：`v.push_back(std::move(ptr));`，或改用 `emplace_back(std::move(ptr))` |
| `reserve(5)` 之后用 `v[0]` 读写，结果乱或崩溃 | `reserve` 只改容量、不改长度，此时 `size()` 仍是 0，下标越界 | 用 `push_back` / `emplace_back` 真正添加元素；要"先有 5 个元素"就用 `resize(5)` |
| 加了元素之后，之前保存的引用、指针或迭代器变得不可用 | 扩容把元素搬到了新内存，旧地址上的对象已经销毁 | 扩容可能发生时就别长期保存这些引用；已知元素个数先用 `reserve` 固定容量 |
| 用 `emplace_back` 却没有变快 | 参数本身就是先造好的对象（`emplace_back(S(1, 2))`），临时对象照旧出现 | 把构造参数直接传进去：`emplace_back(1, 2)`；有现成对象时用 `push_back(std::move(obj))` 更直白 |
| 扩容时元素的复制次数远多于移动次数 | 元素的移动构造函数没有标 `noexcept`，`vector` 不敢用移动搬元素（第 29 章 3 节） | 给移动构造函数加 `noexcept` |
| `emplace_back` 的实参类型与构造函数不匹配，程序却不报错，只是值不对 | 参数被原样转发给构造函数，标准允许的隐式转换会静默发生（例如 `double` 传给 `int` 参数时小数被丢掉） | 传参前把值算成正确的类型，或在构造参数处做显式转换（`static_cast<int>(1.5)`） |
| 往 `vector` 里加元素时，输出里始终是 `Copy Constructor!` | 传的是具名左值，且没有 `std::move`；或该类型压根没有移动构造函数 | 确实不再需要该对象就写 `std::move`；需要移动构造函数则按第 29 章自己实现 |

## 8 本章验收

1. 三个例程都编译通过，`-Wall` 无警告，输出与 2、3、5 节的预期现象逐字符一致。
2. 能说出 `push_back` 两个重载的参数类型，并预判 `push_back(s)`、`push_back(std::move(s))`、`push_back(S(30))` 三种写法各自调用哪个构造函数。
3. 能用一句话说清 `push_back` 与 `emplace_back` 的区别（前者要现成对象、后者接收构造参数），并指出 `emplace_back` 省掉的是哪一步。
4. 能说出扩容时已有元素会经历什么，以及为什么 `copies = 0` 依赖于移动构造函数的 `noexcept`。
5. 完成过 6.2 的必做实验与 6.3 的 `noexcept` 实验，能解释"写了 `emplace_back` 反而没省"和"删掉 `noexcept` 之后就出现复制"这两个现象。
