# 41 线程：创建、汇合与 jthread

上一篇：[[40 并行 STL 算法：用执行策略加速]]
下一篇：[[42 互斥锁：保护共享资源]]

## 学习目标

完成本章后，你应当能够：

1. 说出启动一个线程必须提供的两样东西：要执行的可调用对象，以及交给它的参数。
2. 创建 `std::thread` 并用 `join` 让主线程等待它结束。
3. 解释不调用 `join` 会发生什么，以及 `std::jthread` 为什么能避免这个后果。
4. 用 `std::vector` 管理一组线程，并让每个线程只写属于自己的数据位置。
5. 说明"顺序不确定但内容必须完整"的含义，并写出输出可以核对的并发程序。

## 1 从执行策略到自己动手

第 40 章的执行策略解决的是"一段标准库算法怎么并行"：加一个参数交给库，剩下的我们不用管。但并行这件事并不总能套进现成的算法形状里——可能要同时处理几批互不相关的数据、一边算一边等网络、或者把一件大活按自己的想法切开。这时需要自己说出"哪些工作可以同时做"。

C++ 里表达这件事最基本的工具是**线程**（thread）。`std::thread` 类表示一个执行线程，线程允许多个函数**并发执行**。也就是说，我们可以把一个函数交给一个新线程，让它和原来的执行流同时往下跑。

程序启动时已经有一条执行流，它从 `main` 开始执行，称为**主线程**。用 `std::thread` 创建的都是额外的执行流。操作系统会把这些执行流分配到处理器的不同核心上，所以"同时"是真的同时，而不只是轮流使用一个核心。

`std::thread` 定义在头文件 `<thread>` 里。第 02 章讲过的规则在这里照旧适用：用到什么东西，就包含它所在的那个头文件。

## 2 创建一个线程

创建一个线程要回答两个问题：**它执行什么**，以及**它的输入是什么**。这两个答案就是 `std::thread` 构造函数的参数。

例程 `E:\CPP_Code\CppFromScratch\ch41_threads\thread_basic\thread_basic.cpp` 里先准备了一件"工作"：

```cpp
void printThreadId(int id)
{
    std::cout << "来自线程：thread id = " << id << std::endl;
}
```

然后在 `main` 里启动一个线程来运行它：

```cpp
std::thread t1(printThreadId, 7);

t1.join();
```

逐部分看这一行构造：

- **第一个实参 `printThreadId`** 是"这个线程要执行什么"。能放进去的东西叫**可调用对象**：普通函数名（这里就是）、第 38 章的函数对象、第 39 章的 lambda 表达式都可以。
- **后面的实参 `7`** 是交给那个函数的输入，按顺序对应它的参数列表，所以 `printThreadId` 收到的 `id` 就是 `7`。参数可以是任意多个，也可以是零个（不传就只写一个可调用对象）。
- **`t1`** 是这个线程对象的名字。构造完成的那一刻，新线程就已经开始执行了；构造函数返回与"新线程开始跑"之间没有先后保证，两者是并发的。

`main` 里创建 `t1` 之后所处的这条执行流就是主线程，它不会因为 `t1` 的存在而停下来等谁。

## 3 汇合：join

新线程一旦启动就和主线程并行前进。这带来一个必须处理的问题：**主线程怎么知道它已经干完了？** 如果主线程需要用线程算出来的结果，它就必须等到那个线程结束。

答案就是 `join`：

```cpp
t1.join();
```

`join` 的含义是：**当前线程（这里是主线程）在这一点阻塞，直到 `t1` 对应的执行流结束，然后继续往下执行**。`join` 调用完之后 `t1` 就不再对应任何执行流（`t1.joinable()` 变成 `false`），**同一个线程对象只能 `join` 一次**。

拿例程里的顺序来看：

```cpp
std::thread t1(printThreadId, 7);

t1.join();
std::cout << "主线程：t1.join() 之后才继续" << std::endl;
```

因为 `join` 写在线程输出与主线程这行输出之间，所以线程那一行的位置是被固定住的：

```text
=== Demo A: 启动一个线程并等待它完成 ===
来自线程：thread id = 7
主线程：t1.join() 之后才继续
```

如果把 `join` 换成别的位置——比如让主线程先做一大段自己的活再 `join`——那么"来自线程"这一行就可能出现在前面、中间或后面，取决于两个执行流各自跑得多快。**`join` 的位置决定了输出中哪些先后关系是确定的，哪些是不确定的**，这一点在写并发程序时是首要的清醒认识。

### 3.1 不 join 会怎样

如果创建了线程却从头到尾都没 `join`，那在 `main` 返回、`t1` 被销毁（析构）的时候，它还对着一条还在跑的（或者可能已经跑完但没被汇合的）执行流。此时标准规定：**销毁一个仍处于 joinable 状态的 `std::thread` 会调用 `std::terminate`**，程序直接终止。

把上面例程里的 `t1.join();` 注释掉再编译运行（后面的实验会做这一步），实测输出是：

```text
=== Demo A: 启动一个线程并等待它完成 ===
主线程：t1.join() 之后才继续
=== Demo B: 把结果写回主线程的变量 ===
来自线程：thread id = 7
主线程自己的累加：100000
线程 9 的累加：100000
terminate called without an active exception
```

可以看到两件事：一是"来自线程"那一行跑到了主线程两行输出的**后面**（没有 `join` 就没人约束顺序）；二是程序最后打印了 `terminate called without an active exception` 然后异常结束，退出码不是 `0`。

标准之所以选择直接终止而不是"悄悄帮我们等"，是因为线程对象的析构函数无法体面地处理这件事：等它结束可能等很久，不等又会产生悬垂状态，标准把这个决定权交给了写代码的人——**要么 `join`，要么在别的地方明确交代这条执行流的去向**。本章的规则很简单：**创建的每个 `std::thread` 都要有对应的 `join`。**

## 4 jthread：析构时自动汇合

每次手写 `join` 都要记得"我创建了几个线程、它们各自要在哪里等"，这和第 18 章"每次 `new` 都要配一个 `delete`"是同一类负担。C++20 为此提供了更省心的线程类型 `std::jthread`。

`std::jthread` 的构造方式和 `std::thread` 完全一样（可调用对象 + 参数），区别只有一条：**`jthread` 在析构时会自动汇合**（如果它还在 joinable 状态，析构函数里调用 `join` 之后再继续销毁）。因为它的析构函数总是会执行，所以"忘记 join 导致程序终止"这类事故就不存在了。

"自动汇合发生在什么时候"很关键：**在对象被销毁的那一刻，也就是它所在的作用域结束时**。例程 `ch41_threads\jthread_vector\jthread_vector.cpp` 用一对花括号把这一点变成了可以看见的东西：

```cpp
{
    std::vector<std::jthread> myThreads;

    for (int i = 0; i < 3; ++i)
    {
        myThreads.emplace_back([i]()
        {
            std::cout << "thread id = " << i << std::endl;
        });
    }
}

std::cout << "=== Demo A 结束 ===" << std::endl;
```

`std::vector<std::jthread>` 是可以的：容器只要求元素能被移动，而线程对象可以移动、不能拷贝。上面这段代码里没有任何 `join`，但走出花括号时 `vector` 析构、三个 `jthread` 逐个析构并各自汇合，所以后面那行 `=== Demo A 结束 ===` 一定排在三个线程输出之后。

如果把这里的 `std::jthread` 全部换成 `std::thread`（其他一字不改），编译照样通过，但运行时会立刻看到和 3.1 节一样的 `terminate called without an active exception`——`vector` 析构时销毁了三个还没汇合的线程对象。

### 4.1 参数是怎么进入线程函数的

`std::thread`（以及 `jthread`）会把实参**拷贝**到自己的内部存储里，然后以右值的形式交给线程函数。这条规则有一个直接后果：**形参是引用的函数不能用它来改主线程的变量**。

例程 `thread_basic.cpp` 里的 `addMany(int times, int& result)` 的第二个形参是引用，所以调用处必须写：

```cpp
std::thread t2(addMany, 100000, std::ref(threadResult));
```

`std::ref` 的作用是"把这个变量按引用交出去，不要拷贝"。如果这里直接写 `threadResult`，编译时会失败：

```text
error: static assertion failed: std::thread arguments must be invocable after conversion to rvalues
```

这条信息不好读，但记住结论就够了：**想让线程改到外面的变量，就把那个变量用 `std::ref` 包起来**（`std::ref` 来自 `<functional>`，第 16 章按引用传参的那套规则在这里以"显式声明引用"的形式出现）。

还有一条更要紧的约束：**被引用的对象必须活得比线程长**。如果传给线程的是某个局部变量的引用，而那个局部变量所在的作用域先结束，线程再访问它就是访问已经销毁的对象（悬垂引用）。本章用到的引用对象都是 `main` 里的变量或全局变量，它们活到程序结束，所以安全。

### 4.2 主线程与线程各自算各自的

例程的 Demo B 让两边各做一份独立的计算，最后再合并：

```cpp
int threadResult = 0;
std::thread t2(addMany, 100000, std::ref(threadResult));

int mainResult = 0;

for (int i = 0; i < 100000; ++i)
{
    mainResult += 1;
}

t2.join();
std::cout << "主线程自己的累加：" << mainResult << std::endl;
std::cout << "线程 9 的累加：" << threadResult << std::endl;
```

输出是固定的两行 `100000`。这里有两点值得停下来看：

- 两个执行流从头到尾没有碰过同一个变量：主线程写 `mainResult`，线程写 `threadResult`。**没有共享的写操作，就没有需要协调的东西**，这是并发程序最好写、也最好核对的一种形态。
- `join` 写在了读取 `threadResult` **之前**。如果在 `join` 之前就读，读到的可能还是 `0`，因为那时线程可能一次都还没写回去。**共享数据必须在汇合之后读**，这是本章最重要的时序规则。

## 5 让并发程序的输出可以核对

前面几段已经把并发程序最反直觉的地方暴露出来了：**输出顺序不确定**。例程 `jthread_vector.cpp` 的 Demo A 让三个线程各自打印一行 `thread id = N`，其中一次实测的输出是这样的：

```text
=== Demo A: 三个线程直接写 std::cout ===
thread id = thread id = 0
1thread id = 
2
=== Demo A 结束 ===
```

三个线程的三段输出咬在了一起，`thread id =` 和数字被拆散到不同的行上。原因并不神秘：`std::cout << "thread id = " << i << std::endl;` 这一句在机器层面是**四次**插入运算（三次 `<<` 加一次换行），而线程切换可以发生在任意两条指令之间。三个线程同时执行这四次运算，插入的先后顺序就完全解释了上面那堆混乱。

同样的程序再运行几次，也可能得到"三行整齐依次出现"的结果，例如：

```text
=== Demo A: 三个线程直接写 std::cout ===
thread id = 2
thread id = 1
thread id = 0
```

**这说明"这次看起来很清楚"完全不能作为并发程序正确的证据**——同样的一段代码只是这次没有撞上而已。

所以要定一条判断标准，把"顺序"和"内容"分开看：

> **顺序不确定是可以接受的，内容必须完整正确。**
>
> "内容完整正确"指的是：该出现的每一份结果都出现了，且每个值都对。比如上面这段，正确的内容是"`thread id = 0`、`thread id = 1`、`thread id = 2` 各出现一次"，至于它们谁先谁后、有没有混在同一行，不属于正确性问题。

按这个标准，我们可以把并发程序的输出写成**可核对**的形状。本章例程用的是两种写法：

**写法一：每个线程只写属于自己的位置。** `jthread_vector.cpp` 的 Demo B 给每个线程分配一个字符串格子：

```cpp
std::vector<std::string> lines(3);

{
    std::vector<std::jthread> myThreads;

    for (int i = 0; i < 3; ++i)
    {
        myThreads.emplace_back([i, &lines]()
        {
            lines[i] = "thread id = " + std::to_string(i) + " 完成";
        });
    }
}

for (const std::string& line : lines)
{
    std::cout << line << std::endl;
}
```

每个线程只写 `lines[i]` 这一个元素，彼此不碰同一个格子；等所有线程汇合之后，由主线程按 `0`、`1`、`2` 的固定顺序读出来打印。输出每次运行都完全一致：

```text
=== Demo B: 每个线程只写自己的格子 ===
thread id = 0 完成
thread id = 1 完成
thread id = 2 完成
汇总：共运行 3 个线程
```

这里还顺带说明了一个常见疑问：**多个线程同时写同一个 `std::vector` 的不同元素是安全的**。竞争只发生在"同一个内存位置"上，而不同元素各自有独立的存储位置。反过来，如果某个线程让 `vector` 扩容（比如在别的线程还在写元素时 `push_back`），那些元素会被搬到新内存上，原本的"位置"就变了，这时就不再安全——所以这种分片写法要求**先在并发开始前把容器的大小定好，线程运行期间不扩容、不增删元素**。

**写法二：线程只做计算，结果按固定顺序汇总。** 例程 `thread_results.cpp` 里四个线程各算一个值写进 `results[i]`，全部汇合之后主线程按顺序打印并求和：

```text
=== 4 个线程分别计算结果 ===
=== 按固定顺序汇总 ===
worker 0: 1 * 10 = 10
worker 1: 2 * 10 = 20
worker 2: 3 * 10 = 30
worker 3: 4 * 10 = 40
合计：100
```

**让线程只写自己的那一份、由主线程统一输出**，是把"并发"和"可核对"两件事同时做到的最简单办法。需要严格执行"每一行必须完整不被打断"时（例如日志），要用第 42 章的互斥锁把整行输出变成一段不可打断的临界区。

## 6 动手实验

例程在 `E:\CPP_Code\CppFromScratch\ch41_threads\` 下，三个程序各占一个文件夹，每个 `.cpp` 都是单文件自包含的（自己带全部 `#include`，可以单独编译运行）。

编译命令的模板（先 `cd` 进例程所在目录）：

```text
E:\msys64\ucrt64\bin\g++.exe -std=c++20 -Wall -g thread_basic.cpp -o thread_basic.exe
./thread_basic.exe
```

关于链接参数：本章的线程程序在 MSYS2 UCRT64 上**不需要任何额外链接参数**（不需要 `-pthread`，也不需要第 40 章并行算法用的 `-ltbb12`）。如果将来换到别的平台或编译器，视频里提到的那种"编译时提示缺 pthread 相关符号、需要加链接选项"的情况才可能出现。

### 6.1 实验一：`thread_basic` 创建、传参、join

`thread_basic\thread_basic.cpp` 里定义了 `void printThreadId(int id)` 与 `void addMany(int times, int& result)`，`main` 里分别用它们启动了 `t1`（`join` 紧跟在后面）和 `t2`（`join` 放在主线程做完自己的活之后）。

**预期输出**（逐字符与实测一致，多次运行都相同）：

```text
=== Demo A: 启动一个线程并等待它完成 ===
来自线程：thread id = 7
主线程：t1.join() 之后才继续
=== Demo B: 把结果写回主线程的变量 ===
主线程自己的累加：100000
线程 9 的累加：100000
```

**验收标准**：输出与上面逐字符一致；编译时 `-Wall` 没有警告。

**改值实验**：把 `main` 里那个 `for (int i = 0; i < 100000; ++i)` 的 `100000` 改成 `200000`，**先预测**输出会变成哪样，再重新编译运行。实测结果：

```text
=== Demo A: 启动一个线程并等待它完成 ===
来自线程：thread id = 7
主线程：t1.join() 之后才继续
=== Demo B: 把结果写回主线程的变量 ===
主线程自己的累加：200000
线程 9 的累加：100000
```

第一行累加变成 `200000`，而第二行没变——因为线程那一份的循环次数写在线程的参数里（`addMany` 的 `100000`）。两边的循环次数是各自独立的，这也是"两个线程各算各的"最直观的证据。

**去掉 join 的实验**：把 `t1.join();` 注释掉，重新编译运行。实测输出为：

```text
=== Demo A: 启动一个线程并等待它完成 ===
主线程：t1.join() 之后才继续
=== Demo B: 把结果写回主线程的变量 ===
来自线程：thread id = 7
主线程自己的累加：100000
线程 9 的累加：100000
terminate called without an active exception
```

注意这里有两个变化：线程那一行跑到主线程输出之后了（没有 `join` 的约束），程序最后异常终止（退出码非 `0`）。看完把 `join` 恢复。

### 6.2 实验二：`jthread_vector` 一组线程与自动汇合

`jthread_vector\jthread_vector.cpp` 里有两段：Demo A 让三个 `jthread` 直接往 `std::cout` 写，Demo B 改成"每个线程写自己的格子、主线程按固定顺序打印"。

**预期输出**：Demo B 的部分以及前后两行标题每次运行都完全一致，Demo A 的三行不确定。下面是一次实测的完整输出（Demo A 恰好咬在一起的那一种）：

```text
=== Demo A: 三个线程直接写 std::cout ===
thread id = thread id = 0
1thread id = 
2
=== Demo A 结束 ===
=== Demo B: 每个线程只写自己的格子 ===
thread id = 0 完成
thread id = 1 完成
thread id = 2 完成
汇总：共运行 3 个线程
```

**验收标准**（把顺序和内容分开判断）：

1. 除了 Demo A 那一段，其余每一行都与上面列出的完全一致；
2. Demo A 那一段里 `0`、`1`、`2` 三个数字各出现一次（不管它们被排成几行、会不会咬在一起）；
3. 连续运行 10 次，"汇总：共运行 3 个线程"这一行每次都在最后，且永远是 `3`；
4. 编译时 `-Wall` 没有警告。

**观察顺序实验**：把 Demo A 那一段整体放在 `for` 里再跑十几次（或者干脆多运行几次程序），你会看到三种不同的结果：三行顺序打乱、三行顺序正好递增、以及上面那种咬在一起的输出。**这三种都是这份代码的正常表现**——因为三个线程被同时交给操作系统调度，谁先拿到 CPU、每次拿到多久，取决于当时系统里还有谁在抢 CPU。

**改值实验**：把 Demo B 里 `std::vector<std::string> lines(3);` 的 `3` 和循环里的 `i < 3` 一起改成 `5`，**先预测**会多输出哪几行，再重新编译运行。预期会多出 `thread id = 3 完成`、`thread id = 4 完成` 两行，最后一行变成 `汇总：共运行 5 个线程`。

**换类型实验**：把两处 `std::jthread` 都改成 `std::thread`（其余一字不改），重新编译运行。实测程序会在 Demo A 结束前后立刻打印：

```text
terminate called without an active exception
```

原因是 `vector` 析构时销毁了三个还没有汇合的 `std::thread` 对象。看完改回 `jthread`。

### 6.3 实验三：`thread_results` 结果按固定顺序汇总

`thread_results\thread_results.cpp` 里四个线程各自把 `(i + 1) * 10` 写进 `results[i]`，主线程在全部汇合后按固定顺序打印并求和。

**预期输出**（逐字符与实测一致，每次运行都相同）：

```text
=== 4 个线程分别计算结果 ===
=== 按固定顺序汇总 ===
worker 0: 1 * 10 = 10
worker 1: 2 * 10 = 20
worker 2: 3 * 10 = 30
worker 3: 4 * 10 = 40
合计：100
```

**验收标准**：输出与上面逐字符一致；`-Wall` 无警告。

**改值实验**：把 `const int workerCount = 4;` 改成 `5`，先预测新输出，再重新编译运行。实测：

```text
=== 5 个线程分别计算结果 ===
=== 按固定顺序汇总 ===
worker 0: 1 * 10 = 10
worker 1: 2 * 10 = 20
worker 2: 3 * 10 = 30
worker 3: 4 * 10 = 40
worker 4: 5 * 10 = 50
合计：150
```

多出 `worker 4` 一行，合计变成 `150`——线程数、`results` 的大小、循环次数都由 `workerCount` 一处决定，改一个值就整体跟着变。

## 7 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| `error: 'thread' is not a member of 'std'`（后面常跟一句 `note: 'std::thread' is defined in header '<thread>'`） | 没有包含 `<thread>` | 在文件顶部加 `#include <thread>` |
| `error: 'jthread' is not a member of 'std'`，并有 `note: 'std::jthread' is only available from C++20 onwards` | 编译标准低于 C++20 | 编译命令加 `-std=c++20`；`jthread` 是 C++20 才有的类型 |
| 程序运行到最后打印 `terminate called without an active exception` 并异常结束 | 创建的 `std::thread` 没有 `join`，它被销毁时仍是 joinable 状态，标准规定此时调用 `std::terminate` | 给每个 `std::thread` 都补上 `join`；或者改用 `std::jthread` 让它自动汇合 |
| `error: static assertion failed: std::thread arguments must be invocable after conversion to rvalues` | 把变量直接传给了形参为引用的线程函数，而线程会把参数拷贝一份 | 用 `std::ref(变量)` 明确表示按引用传（需要 `#include <functional>`） |
| `error: use of deleted function 'std::thread::thread(const std::thread&)'` | 试图拷贝一个线程对象（例如 `std::thread t2 = t1;`） | 线程对象只可移动不可拷贝；要管理多个线程就用 `std::vector` 配合 `emplace_back` 就地构造 |
| `terminate called after throwing an instance of ...`，或线程里算出的结果莫名其妙 | 线程函数访问了已经销毁的局部对象（悬垂引用） | 确保被线程引用的对象活得比线程长，例如放在 `main` 的作用域里或用全局变量 |
| 线程算出来的变量在主线程里还是初值 | 在 `join` 之前就读取了共享数据 | 把所有对共享结果的读取都放到 `join` 之后（或作用域结束之后） |
| 输出被两个线程咬在一起，同一行里混着不同线程的内容 | 一行输出由多次 `<<` 组成，线程切换插在中间 | 这是本章实验里要观察的正常现象；要保证整行不被打断，用第 42 章的互斥锁，或者按第 5 节的两种写法让主线程统一输出 |
| 生成的 `exe` 一运行就立刻退出、什么也不打印（退出码 `127`） | 程序找不到 MSYS2 的运行时 DLL（`libstdc++-6.dll`、`libgcc_s_seh-1.dll`；用 `jthread` 的程序还需要 `libwinpthread-1.dll`） | 在 MSYS2 的 UCRT64 shell 里运行，或把 `E:\msys64\ucrt64\bin` 加入 `PATH` 后运行 |

## 8 本章验收

1. 三个例程都编译通过、`-Wall` 无警告，输出与 6.1、6.2、6.3 节一致（Demo A 那一段按"内容完整"而不是"顺序固定"来判断）。
2. 能对一个 `std::thread t1(printThreadId, 7);` 逐部分说明：哪一个实参告诉线程"做什么"，哪些实参是它的输入，`7` 为什么能传进去。
3. 能回答四个问题：`join` 做了什么？不写 `join` 会发生什么、为什么？`jthread` 与 `thread` 的区别是什么？为什么往线程里传引用要用 `std::ref`？
4. 完成过 6.1 节的"去掉 join"实验与 6.2 节的"换类型实验"，能说出两次 `terminate called without an active exception` 分别是怎么来的。
5. 能说清"顺序不确定但内容必须完整"的判定方式，并指出 6.2 节 Demo A 里哪些部分属于"允许变化"，哪些部分属于"必须正确"。
