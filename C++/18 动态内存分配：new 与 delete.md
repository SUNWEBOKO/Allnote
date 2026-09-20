# 18 动态内存分配：new 与 delete

上一篇：[[17 指针：保存地址的变量]]
下一篇：[[19 unique_ptr：独占所有权的智能指针]]

## 学习目标

完成本章后，你应当能够：

1. 说明为什么有些内存必须在运行时才申请。
2. 用 `new` 表达式申请一块内存，并用指针接住它返回的地址。
3. 用 `delete` 释放自己申请的内存，并说明不释放会带来什么后果。
4. 用 `new[]` 一次申请一批连续对象，并说明它返回的地址指向哪里。
5. 说出 `delete` 和 `delete[]` 的区别，以及写错时的现象。

## 1 为什么需要"运行时才申请内存"

到第 17 章为止，我们用过的内存都来自两种"自动"的方式：

- **局部变量**：进入作用域时产生，离开作用域自动消失。长度在编译期就固定了（`int a;`、`std::array<int, 3> arr;`）。
- **标准库容器**：`std::vector` 在需要更多空间时自己去申请新内存、把元素搬过去、释放旧内存，我们只管 `push_back`；容器销毁时它自己把内存还回去（第 14 章）。

这两种方式都有一个共同前提：**什么时候分配、什么时候释放，都由别人决定**。局部变量由作用域决定，容器由它自己的生命周期决定。

有些场合不满足这个前提。例如：一块缓存要一直留到程序结束；一处代码申请的内存，要交给另一段很远的代码去用，谁都不知道最后是哪个分支先退出；或者要按运行时才知道的大小申请一批数据。这些情况都属于同一类需求——**现在给我一块内存，什么时候还由我说了算**。

理解这件事还有第二个理由：`std::vector` 内部就是靠这套机制工作的。知道 `new` 和 `delete` 怎么做，才知道容器替我们省掉了什么，也才能理解下一章智能指针包住的到底是什么。

## 2 `new` 表达式：申请一块内存

`new` 表达式向运行时申请内存，并且返回这块内存的地址。所以**它的结果必须用指针接住**：

```cpp
int* ptr = new int;
```

这一句做了三件事：

1. 申请一块"装得下一个 `int`"的内存；
2. 在这块内存上构造一个 `int`（本例没有提供初值，所以这块内存里此刻的值是不确定的）；
3. 返回这块内存的地址，类型是 `int*`。

第 3 步决定了接收方的类型：既然交回的是地址，就得用指针变量装，`int x = new int;` 是编译不过的（类型不匹配）。

拿到之后，这块内存的用法和平时的 `int` 完全一样，只是只能通过 `ptr` 访问：

```cpp
*ptr = 242;                              // 先写
std::cout << *ptr << std::endl;          // 读出来是 242
```

注意这里的顺序：`new int` 不初始化，**里面是什么值不确定**，所以不能先读后写。要让它一开始就是 0，标准写法是 `new int()`（带一对空圆括号），这是值初始化。

关于失败的处理也值得记一句：`new` 拿不到内存时不是返回空指针，而是抛出 `std::bad_alloc` 异常，正常路径就此中断。所以 `int* p = new int;` 之后**永远不需要判空**——它要么是一个有效地址，要么根本走不到下一句。

## 3 `delete` 表达式：把内存还回去

自己申请的内存不会自动回收，用完之后必须用 `delete` 表达式交还：

```cpp
delete ptr;      // 释放 ptr 指向的那块内存
```

`delete` 做两件事：销毁这块内存上的对象，然后把内存还给运行时。写法上有一个必须记清的点：**直接把指针交给它，不要写星号**。

```cpp
delete ptr;      // 对：ptr 是地址
delete *ptr;     // 错：*ptr 是 int（一个整数值），不是地址
```

释放之后，指针变量里那个地址值并不会被清掉，它成了**悬垂指针**：指向的内存已经不属于你，再解引用就是未定义行为。所以释放之后要立刻把它置空：

```cpp
delete ptr;
ptr = nullptr;   // 这样至少能靠 ptr == nullptr 判断出它已经失效
```

## 4 不释放会发生什么

如果一块内存在程序运行期间反复申请、从不释放，程序占用的内存就会持续增长，最终申请不到内存、以失败告终。这类问题叫**内存泄漏**（leak），而且它有几个不好对付的特点：

- 编译期、运行期都不会有任何提示，`-Wall` 也管不了它——**它不违反语言规则，只是浪费资源**；
- 症状是"跑得越久越慢、最后挂掉"，和逻辑错误混在一起时很难定位；
- 泄漏的量小的时候，程序照样跑完，测试根本发现不了。

这也正是标准库容器值得优先使用的原因：`std::vector` 的分配和释放都由它自己负责，我们不需要写 `delete`，也就不可能漏写。

## 5 `new[]`：一次申请一批对象

需要十个 `int` 时不必分配十次，在 `new` 后面加方括号写元素个数即可：

```cpp
int* data = new int[10];
```

返回类型仍然是 `int*`，但含义变了：**它指向这 10 个 `int` 中第一个的地址**，剩下 9 个紧跟在后面排在同一块连续内存里。这和在栈上声明 `std::array<int, 10>` 的元素布局是类似的，区别只在这块内存的存活时间由 `delete[]` 决定，而不是由作用域决定。

还需要特别留意一点：**元素个数 10 并没有被记录在任何地方**。`data` 的类型就是 `int*`，和第 17 章那种指向单个 `int` 的指针在类型上完全一样。个数只存在于你脑子里和那个字面量里，这是原始指针表达力不足的典型表现。

因为内存是连续的，拿到首元素地址之后就能像数组一样用下标访问：

```cpp
for (int i = 0; i < 10; ++i)
{
    data[i] = i * i;
}
```

下标与解引用是同一件事的两种写法：

- `data[0]` 等价于 `*(data + 0)`，也就是 `*data`；
- `data[i]` 等价于 `*(data + i)`，含义是"从 `data` 指向的位置往后数第 `i` 个 `int`"。

所以 `*data = 242;` 和 `data[0] = 242;` 完全等效，都改的是第一个元素。

这里顺便解释了第 17 章提过的那条规则：`data + 3` 不是"地址加 3 个字节"，而是"加 3 个 `int` 的距离"，步长由指针指向的类型决定。两个指向同一块内存的指针相减，得到的是"相隔几个元素"，类型是 `ptrdiff_t`：

```cpp
std::cout << (&data[3] - data) << std::endl;   // 3
```

## 6 `delete` 与 `delete[]` 必须和分配方式对应

释放时的语法取决于当初怎么分配的：

| 分配 | 释放 | 说明 |
| --- | --- | --- |
| `new int` | `delete p;` | 销毁一个对象 |
| `new int[10]` | `delete[] p;` | 销毁一批对象 |

如果 `new` 用了方括号而 `delete` 没用，编译器只会去销毁**第一个**对象，剩下的对象不会被正确销毁，整块内存的归还方式也不对，这是未定义行为。GCC 在 `-Wall` 下会对这种明显不匹配的写法给出提示：

```text
warning: 'void operator delete(void*, long long unsigned int)' called on pointer returned from a mismatched allocation function [-Wmismatched-new-delete]
```

这类警告必须当成错误来对待：它指出的不是风格问题，而是一处会让程序在别处崩掉的内存错误。

## 7 一套必须遵守的使用纪律

`new` / `delete` 是把内存管理责任完全交给人的做法，规则不多，但每一条都是硬要求：

1. **成对。** 每一个 `new` 都要有对应的 `delete`，每一个 `new[]` 都要有对应的 `delete[]`。
2. **只释放一次。** 同一块内存 `delete` 两次是未定义行为。实测现象：程序会在第二次 `delete` 处直接异常退出（Windows 上退出码 `0xC0000374`，堆损坏；Linux 上会打印 `free(): double free detected`）。所以释放后立刻把指针置空，也能顺手避免重复释放时手滑。
3. **只释放 `new` 来的内存。** `delete &a;`（`a` 是局部变量）、`delete someArray.data();` 都是错误的：那块内存不归 `new` 管。
4. **不要越过末尾访问。** `data[10]`（合法下标是 0–9）不会报编译错误，运行时也不会立刻报错，这类越界是未定义行为，往往在很远的地方才表现出症状。

只要有一条做不到，就说明这段代码不该用原始指针管理内存，应该改用容器或下一章的智能指针。

## 8 什么时候还是应该用 `vector`

本章的例程是为了看清底层机制，实际写代码时选择的顺序应该反过来：

- **默认优先用 `std::vector`**：需要在运行时决定元素个数、需要增删元素、需要自动释放，它全包了，而且不会漏写 `delete`。
- 元素个数在编译期就固定，用 `std::array`（第 05 章）。
- 只有在需要**确切的、单个对象的动态生命周期**，或者要接一个只接受指针的接口时，才轮到手动分配。而即使是这些场合，接下来两章的 `std::unique_ptr`、`std::shared_ptr` 也能把"释放"这一步重新交给类型系统，不必手写 `delete`。

换句话说，本章的落点是：知道 `new`/`delete` 是什么、为什么会出错，然后**尽量不直接用它们**。

## 9 动手实验

例程在 `E:\CPP_Code\CppFromScratch\ch18_dynamic_memory\` 下，两个程序各占一个文件夹。

### 9.1 实验一：分配一个 `int`

`E:\CPP_Code\CppFromScratch\ch18_dynamic_memory\new_single\new_single.cpp` 演示 `new int` 的三步、通过指针读写、两次分配的地址不同，以及 `delete` 之后立刻置空。

编译运行（在 `E:\CPP_Code\CppFromScratch\ch18_dynamic_memory\new_single` 目录下执行）：

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g new_single.cpp -o new_single.exe
./new_single.exe
```

**预期输出**（逐字符一致）：

```text
=== Demo A: allocate one int with new ===
after *ptr = 242, *ptr = 242
ptr is not a null pointer: 1
a second new returns a different address: 1
after delete and ptr = nullptr, ptr is null: 1
```

**结果解释**：第三行比较的是两次 `new` 的地址是否"不同"，结果是 `1`，说明每次分配都是独立的一块内存。第四行说明 `delete` 不会自动清空指针——置空是我们手动做的，也必须手动做。程序输出里没有出现具体地址数字，因为地址每次运行都可能变化。

**验收标准**：编译 `-Wall` 无警告，输出与上面逐行一致；`grep` 一遍源码，`new` 与 `delete` 的个数能对上（这里是 2 个 `new`、2 个 `delete`）。

**改值实验**：把 `*ptr = 242;` 里的 242 改成 `7 * 6`。重新编译运行前先预测第二行：应该是 `after *ptr = 242, *ptr = 42`——注意输出的提示文字里写的还是 242，因为它只是一段固定字符串，变的是后面那个值。这一步的作用是分清"提示文字"和"被打印的值"。

### 9.2 实验二：分配一批 `int` 并正确释放

`E:\CPP_Code\CppFromScratch\ch18_dynamic_memory\new_array\new_array.cpp` 演示 `new int[10]` 返回首元素地址、下标的连续性、下标与解引用等价、指针相减，以及 `delete[]`。

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g new_array.cpp -o new_array.exe
./new_array.exe
```

**预期输出**（逐字符一致）：

```text
=== Demo A: allocate 10 ints with new[] ===
data[0] = 0
data[3] = 9
data[9] = 81
data[3] and *(data + 3): 9 9
after *data = 242, data[0] = 242
&data[3] minus data = 3
=== Demo B: new[] must be matched by delete[] ===
after delete[] and data = nullptr, data is null: 1
```

**结果解释**：`data[3] = 9` 和 `data[9] = 81` 对应 `i * i`（3 的平方、9 的平方）。`data[3] and *(data + 3): 9 9` 两个值相同，说明下标就是指针算术加解引用。`after *data = 242, data[0] = 242` 说明 `*data` 就是第一个元素。`&data[3] minus data = 3` 说明指针相减得到的是"元素的个数差"，而不是字节数差。

**验收标准**：编译 `-Wall` 无警告，输出与上面逐行一致；把 `delete[] data;` 改成 `delete data;` 重新编译，应看到 `[-Wmismatched-new-delete]` 警告——确认后改回来，编译必须重新回到零警告。

## 10 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| `warning: 'void operator delete(void*, long long unsigned int)' called on pointer returned from a mismatched allocation function [-Wmismatched-new-delete]` | 用 `new[]` 分配却用 `delete` 释放 | 改成 `delete[]`；反之 `new int` 只能用 `delete` |
| `error: invalid conversion from 'int*' to 'int'` | 用 `int` 变量接住了 `new` 的返回值 | `new` 交回的是地址，必须用指针接：`int* p = new int;` |
| `error: invalid use of array with unspecified bounds` | 写 `new int[]` 却没给元素个数 | 方括号里必须写个数：`new int[10]` |
| `warning: 'void operator delete(void*, std::size_t)' called on unallocated object 'a' [-Wfree-nonheap-object]` | 释放的不是 `new` 来的内存，例如对局部变量写 `delete &a;` | 只释放 `new`/`new[]` 返回的地址；局部变量由作用域负责 |
| 程序在 `delete` 那一行异常退出，退出码 `0xC0000374`（Linux 上 `free(): double free detected in tcache 2`） | 同一块内存被 `delete` 了两次 | 释放后立刻 `ptr = nullptr;`；检查是否有多条路径重复释放 |
| 程序在解引用指针处异常退出，退出码 `0xC0000005`（Linux 上 `Segmentation fault`） | `delete` 之后继续使用这个指针（悬垂指针） | `delete` 与置空成对写；之后的代码用 `ptr != nullptr` 判断 |
| 程序跑一段时间后变慢并最终失败，编译无警告 | 只 `new` 没有 `delete`，内存泄漏 | 核对 `new`/`delete` 是否成对；能用容器就改用 `std::vector` |
| 读到离奇的整数（例如 `after *ptr = 242, *ptr = 242` 里第一次读却是别的数） | `new int` 不初始化，先读后写读到的是不确定的值 | 先写后读；需要初值就用 `new int()` 值初始化 |
| 程序在远处崩溃，出问题的其实是数组下标写到了 10（合法范围 0–9） | `new int[10]` 的元素个数没有被类型记录，越界不会立刻报错 | 自己维护长度并严格检查下标；需要长度信息时用 `std::vector` 或第 21 章的 `std::span` |

## 11 本章验收

1. 两个例程编译通过、`-Wall` 无警告，输出与 9.1、9.2 节逐行一致。
2. 能说出 `int* ptr = new int;` 这一句里的三个动作，并说明为什么接收方必须是指针。
3. 能解释 `new int[10]` 返回的地址指向哪里、为什么 `data[0]` 和 `*data` 是同一个东西。
4. 能说出 `delete` 与 `delete[]` 的区别，以及写错时报的警告文本。
5. 完成过 9.2 节的 `delete` / `delete[]` 错配实验，能说明为什么本章例程写完还要提醒"优先用 `std::vector`"。
