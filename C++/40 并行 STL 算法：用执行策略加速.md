# 40 并行 STL 算法：用执行策略加速

上一篇：[[39 Lambda 表达式：就地定义的匿名函数]]
下一篇：[[41 线程：创建、汇合与 jthread]]

## 学习目标

完成本章后，你应当能够：

1. 说出并行算法要利用现代 CPU 的哪两种并行资源。
2. 说出 `std::execution` 里四种执行策略的名字和各自允许做什么。
3. 给 `std::reduce`、`std::sort`、`std::transform`、`std::count_if` 加上执行策略参数。
4. 说明 GCC 上并行算法为什么要链接 TBB，并写对 MSYS2 UCRT64 上的链接参数 `-ltbb12`。
5. 让并行程序的输出保持确定，并说清什么函数不能传给并行算法。

## 1 正确之外，还有快

前面几十章的重心一直是"让程序算对"：类型要对、控制流要对、对象生命周期要对。但一个程序只有"结果正确"是不够的——**它还得在合理的时间里给出结果**。一个几秒钟就该跑完的任务如果花了两三分钟，无论结果多正确都不可用。

谈性能先要看清瓶颈在哪里。今天常见的 CPU 提供了两种并行资源：

- **多核**：一颗处理器里有多个核心，可以同时执行不同的任务。把一份工作切成若干块、让多个核心各算一块，就能缩短总时间。
- **SIMD 指令**（Single Instruction Multiple Data，单指令多数据）：一条指令同时对多个数据做同样的运算。例如向量加法里"逐元素相加"这种操作，一条 SIMD 指令可以顶替好几条普通指令。

要利用这两样东西，传统做法是自己开线程、切数据、合并结果，代码复杂且容易出错。而本章要讲的做法几乎不需要付出这种代价：**把前几章一直在用的标准库算法加上一个"执行策略"参数，让库替你决定怎么并行**。同一个算法、同一行调用，加一个参数就能从单线程执行变成多线程加 SIMD 执行。

## 2 四种执行策略

执行策略定义在头文件 `<execution>` 里，名字都在 `std::execution` 命名空间下，共四种：

| 策略 | 含义 | 引入版本 |
| --- | --- | --- |
| `std::execution::seq` | 不允许并行，也不允许向量化：就是顺序执行 | C++17 |
| `std::execution::par` | 允许并行：算法可以由多个线程同时处理不同部分 | C++17 |
| `std::execution::par_unseq` | 允许并行，并且允许在单个线程内使用向量指令（SIMD） | C++17 |
| `std::execution::unseq` | 只允许向量化，不使用多线程 | C++20 |

读这张表有一个重点：**策略是"许可"，不是"命令"**。写 `par` 的意思是"我允许你用多线程"，库可以按自己的判断决定实际怎么做；写 `seq` 则是明确禁止并行化与向量化——它的行为与不写策略完全一样，所以常用作对照基准。

使用方式很直接：把策略作为调用时的第一个实参。以第 13 章用过的累加为例，`std::accumulate` 的并行版本是 `std::reduce`（定义在 `<numeric>`）：

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

## 3 给 `reduce` 加策略

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
2. **初值 `0LL` 决定累加类型**。这里显式给了 `long long` 字面量，因为 6700 万个数的总和早就超出了 `int` 的范围；写成 `0` 会得到溢出后被截断的错误结果。这与第 03 章的类型规则一致：结果类型由参与运算的类型决定，不是由数据大小决定。
3. **重复 10 轮是为了让耗时差异在 `time` 命令下看得出来**。单轮归约只有百毫秒量级，混在进程启动和内存分配的时间里不容易分辨；重复几轮之后差距就明显了。程序本身只打印求和结果，所以输出仍然完全确定。
4. **`par` 与 `par_unseq` 的结果与 `seq` 逐位相同**。并行改变的是"谁算哪一段"，不改变确定性输入对应的输出。

本机（GCC 16.1.0，`-g`，未开 `-O2`）实测：只保留顺序那 10 轮的版本耗时约 1.63 s；只保留并行与并行向量化两段的版本耗时约 0.44 s（其中还包括约 0.3 s 的填充与分配开销）。真正被策略改变的那部分从约 1.3 s 降到约 0.13 s——**一行调用里多了一个参数，量级上的差别就出来了**。

## 4 并行不只用于累加

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

## 5 让程序真的并起来：TBB 与 `-ltbb12`

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

还有一点要留心：**"能编译能运行"不等于"真的并行了"**。如果某个平台的实现缺少并行后端，加了策略的程序仍然能编译运行，只是策略被忽略、实际仍在单线程执行。所以判断并行是否生效要看耗时对比，而不是看代码里有没有写 `par`。本章两个例程都安排了对照：同一个程序里先跑 `seq` 再跑 `par`，或者把策略换掉重新编译，用 `time` 命令比较。

## 6 并行程序的输出必须仍然可核对

并发程序的执行顺序天生不确定，但这不等于"输出可以随便"。要求是：**输出里与顺序无关的内容必须完整、正确、可复现**。具体做法有三种，本章都用到了：

1. **只打印与顺序无关的量**：总和、计数（例程中的 `sorted sum`、`even numbers after transform`）。
2. **先汇总、再打印事先排好序的结果**：排序后的前五个与后五个元素（`first five` / `last five`）。
3. **用 `seq` 与 `par` 互相校验**：同一个输入跑两遍，比较结果是否相等（`all sums equal: 1`、`results match` 这类输出）。

反过来说，下面这些写法会让输出无法核对，属于应当避免的：

- 让传给算法的函数去修改共享变量（数据竞争）：结果取决于线程调度，可能每次不同，也可能看起"正常"却在某个规模下出错；
- 在 `par_unseq` 下加锁或分配内存：允许向量化的策略明确禁止这些操作；
- 用不满足结合律的操作配合 `reduce`：最典型的是浮点加法——`(a + b) + c` 与 `a + (b + c)` 的舍入结果可能不同，于是"并行和"与"顺序和"会有微小差异。整数运算没有这个问题，但对浮点数据必须把初值和累加类型都看清楚。

还有一条性能上的提醒：**并行不是越多越好**。切分任务、启动线程、合并结果都要花时间，元素很少时这些开销会盖过收益，甚至比顺序执行更慢。数据量足够大时再考虑并行，并且用 `time` 验证，而不是凭感觉。

## 7 动手实验

例程在 `E:\CPP_Code\CppFromScratch\ch40_parallel_algorithms\` 下，两个程序各占一个文件夹，都是单文件自包含。**两者的编译命令都必须带 `-ltbb12`**。

### 7.1 实验一：三种执行策略的累加

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

### 7.2 实验二：并行排序、改写与计数

`par_sort_transform\par_sort_transform.cpp` 在约 400 万元素的向量上并行排序、并行改写、并行计数。**注意 `-ltbb12` 写错或漏掉的后果**（见第 5 节与第 8 节）。

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

## 8 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| `collect2.exe: error: ld returned 1 exit status`（数字也可能是 `5`），此外没有任何提示 | 使用了执行策略却没链接 TBB | 在编译命令末尾加上 `-ltbb12`；这一行不提示缺哪个库，是本章最容易被误判成代码错误的报错 |
| `cannot find -ltbb: No such file or directory`，随后 `collect2.exe: error: ld returned 1 exit status` | 链接参数写成了 `-ltbb` | MSYS2 UCRT64 上库文件名是 `libtbb12.dll.a`，必须写 `-ltbb12` |
| 程序编译成功但运行后无任何输出，退出码 127（Windows 上为 `0xC0000135`） | 运行时找不到 `libtbb12.dll` | 让 `E:\msys64\ucrt64\bin` 出现在 PATH 前部（Git Bash 下可执行 `export PATH="/e/msys64/ucrt64/bin:$PATH"`），或直接在 MSYS2 UCRT64 的终端里运行 |
| `error: 'std::execution' has not been declared; did you mean 'std::exception'?` | 忘了 `#include <execution>` | 补上头文件；策略也在这个头文件里 |
| `error: no match for call to '(__pstl::execution::v1::parallel_policy) (int&, int&)'`，并伴随若干 `error: static assertion failed` | 把执行策略写到了参数列表末尾，被当成了二元操作 | 策略是第一个实参：`std::reduce(std::execution::par, first, last, init)` |
| `error: no match for call to '(const std::ranges::__sort_fn) (std::vector<int>&, const __pstl::execution::v1::parallel_policy&)'` | 试图给 `std::ranges` 版本算法加执行策略，它没有这样的重载 | 改用经典迭代器版本：`std::sort(std::execution::par, v.begin(), v.end())` |
| 结果每次运行都不一样，或与 `seq` 的结果对不上 | 传给算法的函数改动了共享数据（数据竞争），或用 `reduce` 做了不满足结合律的运算（如浮点加法） | 让每个元素只依赖自己；需要合并时用 `std::reduce` 自己完成；把 `seq` 当作校验基准逐步比对 |
| 元素很少时并行反而更慢 | 切分、调度、合并的开销没有被数据量摊平 | 小规模数据用 `seq`（或不写策略）；并行只在数据量足够大时才有收益，并用 `time` 实测确认 |

## 9 本章验收

1. 两个例程编译通过（命令里带 `-ltbb12`）、`-Wall` 无警告，输出与 7.1、7.2 节的预期一致，且重复运行结果完全相同。
2. 能说出 `seq`、`par`、`par_unseq`、`unseq` 各自允许什么、分别从哪个标准版本开始提供。
3. 能解释 GCC 上并行算法为什么必须链接 TBB，以及 `-ltbb12` 与 `-ltbb` 的差别；能说出不写链接参数时的报错为什么难查。
4. 能举例说明哪些写法会让 `par_unseq` 下的结果不可预测（加锁、分配内存、改动共享变量），以及为什么整数 `reduce` 的结果与顺序执行一致而浮点加法不一定。
5. 完成过两个改值实验，能提前预判输出变化并用 `time` 观察耗时的量级差别。
