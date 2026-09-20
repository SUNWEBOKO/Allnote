# 46 文件读写：用 fstream 操作文件

上一篇：[[45 随机数：random 库与随机数生成]]
下一篇：[[47 编译时编程：constexpr 与 consteval]]

## 学习目标

完成本章后，你应当能够：

1. 用 `std::ofstream` 把数据写进一个文件。
2. 用 `std::ifstream` 把文件里的数据读回程序，并用 `while (input >> value)` 读到文件末尾。
3. 说明相对路径相对于什么，以及为什么程序的运行目录会影响它。
4. 用 `std::ios::app` 追加写入，并说出它和默认模式的区别。
5. 说出打开文件失败时不检查会有什么后果，以及该检查什么。

## 1 为什么需要文件

到第 45 章为止，程序的所有数据都活在两个地方：变量里和屏幕上。这两处都是**临时的**——程序一退出，变量没了；屏幕上的输出滚过去就找不回来了。

需要让数据活过程序的结束，就得把它写进**文件**：程序算出来的结果要留档，运行日志要能在事后翻看，配置和输入数据要能由外部提供。C++ 标准库把这套能力放在 `<fstream>`（file stream，文件流）头文件里，它提供三种文件流：

| 类型 | 全名 | 用途 |
| --- | --- | --- |
| `std::ofstream` | output file stream | 只写 |
| `std::ifstream` | input file stream | 只读 |
| `std::fstream` | file stream | 又读又写 |

它们的名字由前缀加 `fstream` 组成：`o` 是 output，`i` 是 input。本章用前两种，因为绝大多数场景里"写数据的程序"和"读数据的程序"本来就是分开的。

## 2 写入文件：`std::ofstream`

例程 `write_squares` 把 0 到 9 的平方写进 `squares.txt`，核心只有三行：

```cpp
#include <fstream>
#include <iostream>

int main()
{
    std::ofstream output {"squares.txt"};     // 打开（不存在就新建）

    for (int i = 0; i < 10; ++i)
    {
        output << i * i << " ";               // 和往屏幕上打印写法完全相同
    }
    output << std::endl;

    output.close();                           // 显式关闭
    return 0;
}
```

（节选自例程 `write_squares\write_squares.cpp`，完整版本还包括打开失败的检查。）

### 2.1 文件流与 `std::cout` 是同一类东西

`std::cout` 是输出流，`std::ofstream` 也是输出流，两者共享同一套接口，所以 `<<` 的写法完全一样：数字、字符、字符串、`std::endl` 都能直接往文件里送。这一点是流设计的好处——第 02 章学过的输出写法，换到文件上不需要重新学一遍。

区别只有数据落到哪里：`std::cout` 落到标准输出，`std::ofstream` 落到打开的那个文件。

### 2.2 打开：构造对象就等于打开文件

`std::ofstream output {"squares.txt"};` 这一行做了两件事：构造对象、尝试打开文件。默认的打开模式是 `out | trunc`，含义是"要写，并且把已有内容截断成 0 字节"：

- 文件不存在 → 新建一个（实测运行本程序后当前目录出现了 28 字节的 `squares.txt`）；
- 文件已存在 → 原有内容全部丢失，从头开始写。

**每次运行都会覆盖上次的结果**，这一点必须记住。想保留旧内容要显式指定追加模式（见第 4 节）。

### 2.3 相对路径相对于什么

`"squares.txt"` 是相对路径，它相对于程序**运行时的当前目录**（current working directory，cwd），而不是相对于源码文件或 `.exe` 所在的目录。

```text
cd "E:/CPP_Code/CppFromScratch/ch46_file_io/write_squares"
./write_squares.exe
```

这样运行时，当前目录就是 `write_squares\`，文件生成在那里。如果换到别的目录去执行同一个 `.exe`（例如 `cd ..` 之后再 `./write_squares/write_squares.exe`），文件就会生成在那个新目录里，程序本身不会有任何察觉。**"读不到刚刚写下的文件"十有八九是当前目录不对**，而不是代码的问题。

写绝对路径可以避开这个不确定性，例如 `"E:/CPP_Code/data.txt"`，但这样一来程序就绑死在某个位置上，不适合在不同机器上运行。

### 2.4 什么时候关闭文件

`close()` 做两件事：把流缓冲区里剩下的数据真正写出去、把文件交还给操作系统。不显式调用也不会丢数据——文件流对象在**析构**时会自动关闭（第 25 章讲过析构函数承担的清理职责），`main` 结束时 `output` 被销毁，文件自然被关闭。

显式 `close()` 的价值有两点：写入过程中出错能在这一处就暴露出来；紧接着可以重新打开同一个文件。还有一种更省事的做法是把流对象放进一对花括号里，让作用域结束时的析构替我们关闭（`read_squares` 和 `append_log` 就是这么写的）。

另外，`std::endl` 除了写换行还会**刷新缓冲区**，所以用 `std::endl` 收尾的文件，内容会立即落盘。

### 2.5 文本模式下的换行

文件默认以**文本模式**打开。在 Windows 上，文本模式会把每个 `'\n'` 写成两字节的 `\r\n`（CRLF），读取时再自动还原成一个 `'\n'`。实测例程 `append_log` 生成的 `log.txt`，末尾四个字节是 `t`、`\r`、`\n`——写代码时我们只写了 `std::endl`。这层转换由流对象负责，不用手动处理；但也意味着**同一个文件在 Windows 和 Linux 上字节数不同**（`binary` 模式下才不做任何转换）。

## 3 读取文件：`std::ifstream`

### 3.1 用 `>>` 逐个读入

`std::ifstream` 的用法和 `std::cin` 一致，只是 `>>` 的方向朝着变量，表示"从流里取数据放进变量"：

```cpp
std::ifstream input {"squares.txt"};
int value = 0;

while (input >> value)
{
    std::cout << value << " ";
}
std::cout << std::endl;
```

（节选自例程 `read_squares\read_squares.cpp`。）

`>>` 在取数之前会**自动跳过所有空白字符**：空格、制表符、换行符都算。所以写文件时用来分隔数字的那个空格、以及文件末尾的换行，读取时都不用我们处理。这是 `>>` 与第 3.2 节的 `getline` 最本质的区别。

### 3.2 `while (input >> value)` 为什么能读到文件末尾

`input >> value` 这个表达式的结果是流对象本身，而流对象能被转换成一个布尔值："这次操作成功了没有"。于是循环的含义是：**先读一次，读到了就进循环体，读不到就结束**。

- 读到的一个合法的 `int` → 为真，进入循环；
- 数据读完（遇到文件末尾）→ 为假，循环结束；
- 读到格式不对的内容（比如往 `int` 里读 `"abc"`）→ 同样为假，循环结束。

因为这个写法不依赖"文件里到底有几个数"，读多少算多少，它是处理数字文件的标准写法。例程 `read_squares` 实测：文件里 10 个数，循环执行 10 次，计数 10、求和 285（$0^2 + 1^2 + \dots + 9^2 = 285$）。

### 3.3 `getline`：按整行读取

`std::getline(流, 字符串)` 一次取出一整行，把行尾的换行符丢掉，行内的空格原样保留：

```cpp
std::ifstream in {"log.txt"};
std::string line;

while (std::getline(in, line))
{
    std::cout << line << std::endl;
}
```

（节选自例程 `append_log\append_log.cpp`。）

两种读法的分工很清楚：**文件里是"一堆同类型的值"就用 `>>`，是"一行一条记录"就用 `getline`**。混用要当心一个经典陷阱：`>>` 读到数字就停住，后面的空白（包括换行符）还留在流里，紧接着的 `getline` 会把这一行的剩余部分（常常只剩一个换行）当成一行读出来，看起来就像"凭空多了一个空行"。

### 3.4 流是"消耗品"

一个流读到文件末尾之后就不能接着用了：它已经停在末尾，再读也读不到东西。想从头再读一遍文件，得**新建一个流对象**（或先 `close()` 再 `open()`）：

```cpp
std::ifstream again {"squares.txt"};     // 重新打开，从头开始
```

例程 `read_squares` 里做了两遍读取：第一遍逐个打印，第二遍重新打开做计数与求和。

## 4 打开模式

构造文件流时可以给出第二个参数指定打开模式，常见的几种：

| 模式 | 含义 |
| --- | --- |
| `std::ios::out` | 可写（`ofstream` 的默认值） |
| `std::ios::in` | 可读（`ifstream` 的默认值） |
| `std::ios::trunc` | 打开时清空已有内容（`ofstream` 默认带上它） |
| `std::ios::app` | 追加：写位置总在文件末尾，原有内容保留 |
| `std::ios::ate` | 打开后定位到末尾，但写入位置可以再移动 |
| `std::ios::binary` | 二进制模式，不做换行转换 |

多个模式用按位或连接，例如 `std::ios::out | std::ios::app`。

最常用的是追加模式，写日志几乎总是用它：

```cpp
std::ofstream out {"log.txt", std::ios::app};
```

例程 `append_log` 把这个区别做成了对照实验：先用默认模式写两行（`boot: ok`、`load: ok`），再用 `std::ios::app` 追加一行（`run: start`），读回来共三行；随后又用一次默认模式打开同一个文件写 `reset`，再读回来就**只剩 `reset` 一行**——前面三行被截断掉了。**默认模式是"清空重写"，不是"接着写"**，这是文件读写里最容易搞错的一处。

例程开头还有一句 `std::remove("log.txt");`（来自 `<cstdio>`），它在每次运行前删掉上次留下的文件，让重复运行的结果完全一致。这和随机数那一章固定种子是同一个目的：**让输出可复现、可逐字符比对**。

## 5 打开失败：必须检查

文件打不开是很常见的事：路径写错、文件不存在、目录没有写权限、要写的目录不存在。这时 `ifstream` 和 `ofstream` **既不会抛异常，也不会终止程序**，只是让对象处于"文件没打开"的状态，之后所有读写操作都静默失败。

```cpp
std::ifstream input {"no_such_file.txt"};

if (!input.is_open())
{
    std::cout << "cannot open no_such_file.txt" << std::endl;
    return 1;
}
```

不检查的后果非常隐蔽，例程 `open_failure` 把它实测出来了：读一个不存在的文件，`while (input >> value)` 一次都没进循环，计数结果是 `0`，程序**正常退出、没有任何报错**。如果后面还有一段"根据读到的数据计算结果"的代码，错误会一路传下去，最后表现为"结果是 0 / 是空的"，而真正的原因在几千行之外。

所以规则只有一条：**每次打开文件之后立刻检查 `is_open()`**，打不开就报错返回；写出方向同样要检查（例程里写一个不存在的目录 `no_such_dir/out.txt`，`is_open()` 同样是 `false`）。

顺便说明一个容易混淆的地方：`clear()` 只是把流的状态标志清理干净，**不会**替我们打开文件；想重新尝试打开必须显式调用 `open()`。例程里对同一个错误文件名先 `clear()` 再 `open()`，两次检查的结果都还是"没打开"。

## 6 动手实验

例程在 `E:\CPP_Code\CppFromScratch\ch46_file_io\` 下，四个程序各占一个文件夹。**每个实验都必须在自己的文件夹里运行**：程序里的相对路径相对于当前目录，这样数据文件才会生成在预期位置。

### 6.1 实验一：写入文件（`write_squares`）

```text
cd "E:/CPP_Code/CppFromScratch/ch46_file_io/write_squares"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g write_squares.cpp -o write_squares.exe
./write_squares.exe
```

**预期输出**：

```text
=== write squares into squares.txt ===
wrote 10 values (0^2 .. 9^2) into squares.txt
```

**验收标准**：输出与上面一致；当前目录出现 `squares.txt`，内容为 `0 1 4 9 16 25 36 49 64 81 `（最后一个是行末空格），文件末尾有换行，共 28 字节（10 个数字、10 个空格、换行占 2 字节）。

**改值实验**：把循环上界 `i < 10` 改成 `i < 5`，重新编译运行后 `squares.txt` 应该只包含 `0 1 4 9 16 `——因为默认模式每次都会先把文件清空，所以旧内容不会残留。再把上界改回 10。

**目录验证**：执行 `cd ..`，再从上层目录用相对路径运行同一个 exe：

```text
cd "E:/CPP_Code/CppFromScratch/ch46_file_io"
./write_squares/write_squares.exe
```

会发现 `squares.txt` 这次出现在 `ch46_file_io\` 下面，而不是 `write_squares\` 里——这就是 2.3 节说的"相对路径相对于运行时的当前目录"。验证完把这层多出来的文件删掉，并回到 `write_squares` 目录。

### 6.2 实验二：读回文件（`read_squares`）

```text
cd "E:/CPP_Code/CppFromScratch/ch46_file_io/read_squares"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g read_squares.cpp -o read_squares.exe
./read_squares.exe
```

**预期输出**（两个 `values` / `line` 行末尾各有一个空格）：

```text
=== Demo A: read value by value ===
values: 0 1 4 9 16 25 36 49 64 81 

=== Demo B: reopen and aggregate ===
count = 10
sum = 285
=== Demo C: same file, read as one line ===
line: 0 1 4 9 16 25 36 49 64 81 
```

Demo A 后面那个空行是程序里单独输出的一次换行，用来把三组输出分开，属于预期现象。

这个例程为了让每个程序都能单独运行，会先在当前目录写一份 `squares.txt` 再读它（真实流程里写入和读取通常是两个独立程序，只要运行目录相同就能看到同一个文件，见 2.3 节）。

**验收标准**：输出与上面逐字符一致；`count` 为 10、`sum` 为 285；`-Wall` 无警告。

**改值实验**：把写入部分的循环上界改成 `i < 4`，可以预判 Demo A 会打印 4 个值（`0 1 4 9`）、`count = 4`、`sum = 14`。改完运行验证，然后改回 `i < 10`。

**对照验证**：把 Demo A 的 `while (input >> value)` 改成 `while (std::getline(input, line))`（`line` 声明为 `std::string`）再编译运行，就能看到区别：`getline` 版本一次性把整行读成字符串，因此循环只执行一次，打印出整行内容而不是逐个数字。验证完改回去。

### 6.3 实验三：追加与截断（`append_log`）

```text
cd "E:/CPP_Code/CppFromScratch/ch46_file_io/append_log"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g append_log.cpp -o append_log.exe
./append_log.exe
```

**预期输出**：

```text
=== Demo C: read back log.txt after two writes ===
1: boot: ok
2: load: ok
3: run: start
=== Demo E: read back after truncating write ===
1: reset
=== end ===
```

**验收标准**：输出与上面一致；重复运行结果完全相同（程序开头会用 `std::remove` 删掉旧文件）。

**改值实验**：把第二次写入的模式参数去掉，写成 `std::ofstream out {"log.txt"};`，可以预判 Demo C 读回来只剩一行 `1: run: start`——因为这次打开就把前面两行清空了，Demo E 不受影响（它读的是最后那次写入的结果）。改完运行验证"默认模式 = 清空重写"，然后补回 `std::ios::app`。

### 6.4 实验四：打开失败（`open_failure`）

```text
cd "E:/CPP_Code/CppFromScratch/ch46_file_io/open_failure"
"E:/msys64/ucrt64/bin/g++.exe" -std=c++20 -Wall -g open_failure.cpp -o open_failure.exe
./open_failure.exe
```

**预期输出**：

```text
=== Demo A: open a file that does not exist ===
input.is_open() = false
count = 0
=== Demo B: clear() then open() again ===
after clear(): input.is_open() = false
after open():  input.is_open() = false
=== Demo C: read from an existing file ===
numbers = 3, sum = 60
=== Demo D: writing into a missing directory ===
output.is_open() = false
```

**验收标准**：输出与上面逐字符一致；能说出 `count = 0` 之后程序为什么"看起来成功了"。

**改值实验**：把 Demo A 里的文件名换成 `output.is_open()` 那个例子里真实存在的文件（`existing.txt`），可以预判 `is_open()` 变成 `true`，`count` 变成 3——同一段代码，唯一的差别就是文件在不在。

**清理**：本实验会在当前目录生成 `existing.txt`。四个实验跑完，可以把三个数据文件（`squares.txt`、`log.txt`、`existing.txt`）和所有 `.exe` 都删掉，仓库里只留 `.cpp`。

## 7 常见错误与排查

| 报错或现象 | 原因 | 处理 |
| --- | --- | --- |
| `error: variable 'std::ofstream output' has initializer but incomplete type`（后面跟着 `note: 'std::ofstream' is defined in header '<fstream>'; this is probably fixable by adding '#include <fstream>'`） | 忘了包含 `<fstream>`，只写了 `<iostream>` | 在文件开头加 `#include <fstream>` |
| `error: no match for 'operator<<' (operand types are 'std::ifstream' {aka 'std::basic_ifstream<char>'} and 'int')` | 把读文件写成了写文件，`input << value;` | 输入流用 `>>`、输出流用 `<<`；方向写反时编译器会列出一长串候选，只要看第一行的类型就够了 |
| 程序运行完没有任何输出，也不报错，计数结果是 0 | 文件没打开（路径错、文件不存在），而且没有检查 `is_open()` | 打开之后立刻 `if (!input.is_open()) { ... return 1; }` |
| 明明刚写过文件，读的时候却说打不开 | 读写两次运行时的**当前目录**不同，或写入的 `squares.txt` 在别的目录里 | 先确认 cwd（`cd` 到数据文件所在目录再运行），或统一用同一个运行目录 |
| 文件里旧的内容没了，只剩最近一次写入的 | `ofstream` 打开时默认模式带 `trunc`，会把文件清空 | 要保留旧内容就加 `std::ios::app`，例如 `std::ofstream out {"log.txt", std::ios::app};` |
| 读的时候"凭空多了一行空的" | 先用了 `>>` 读数，换行符还留在流里，紧接着的 `getline` 把它当成了一整行 | `>>` 与 `getline` 不要混用：一堆同类型的值用 `>>`，一行一条记录用 `getline` |
| 第二个循环一个数都读不到 | 同一个流已经读到末尾，不能接着用 | 新建一个流对象重新打开文件，或先 `close()` 再 `open()` |
| 文件写出来了，但内容看起来只有一半 | 程序异常终止，缓冲区里的数据还没落盘 | 显式 `close()`，或用 `std::endl` 收尾（它会刷新缓冲区） |
| 同一个流已经读到文件末尾，`input.eof()` 却输出 `0`，`input.fail()` 也一直是 `false` | 运行时加载到的 `libstdc++-6.dll` 不是编译时用的那一个（Git Bash 里 `/mingw64/bin` 排在 `/e/msys64/ucrt64/bin` 前面，于是先找到了 Git 自带的那份），此时流的状态查询会失真 | 这不影响 `while (input >> value)`、`is_open()` 这类按结果判断的写法（本章例程只用这些）；要查状态标志，把 `/e/msys64/ucrt64/bin` 放到 PATH 最前面再运行，或编译时加 `-static-libstdc++ -static-libgcc` |
| 想在别的机器上直接双击运行 `.exe`，结果文件生成在别处 | 双击运行时的工作目录是 exe 所在目录，而命令行运行时是当前 shell 所在目录 | 明确"程序在哪里运行"和"文件写到哪里"，必要时改用绝对路径或把路径作为参数传入 |

## 8 本章验收

1. 四个例程都编译通过、`-Wall` 无警告，输出与 6.1–6.4 节逐字符一致。
2. 能说清 `std::ofstream output {"squares.txt"};` 这一行做了哪两件事，以及默认模式下"文件已存在"会发生什么。
3. 能回答：相对路径相对于什么？为什么在别的目录运行同一个 `.exe` 会在别处生成文件？`while (input >> value)` 什么时候结束？
4. 完成过 6.3 的改值实验，能说出 `std::ios::app` 与默认模式的差别。
5. 能说出不检查 `is_open()` 会导致什么后果，并写出检查与提前返回的三行代码。
