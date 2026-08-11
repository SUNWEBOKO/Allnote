# Python 笔记

## 一、Python 基础认识

Python 是一种**解释型、动态类型、语法简洁**的编程语言，适合初学者入门，也广泛用于数据分析、自动化办公、后端开发、人工智能等方向。

学习 Python 可以按下面几条主线展开：

1. **基础语法**：变量、数据类型、输入输出、运算符
2. **核心对象**：字符串、列表、元组、字典、集合（本笔记会逐个深入研究）
3. **程序控制**：条件语句、循环
4. **函数**：内置函数、自定义函数、lambda、装饰器、生成器
5. **文件与异常**：读写文件、错误处理
6. **面向对象**：类、对象、构造函数、继承、魔术方法
7. **模块与包**：代码组织与复用
---

## 二、变量与基本数据类型

### 1. 什么是变量

变量可以理解为"有名字的存储空间"，用来保存数据。

```python
name = "Alice"
age = 30
height = 1.75
is_student = True
```

上面定义了 4 个变量：

- `name`：字符串 `str`
- `age`：整数 `int`
- `height`：浮点数 `float`
- `is_student`：布尔值 `bool`

Python 不需要提前声明变量类型，直接赋值即可，解释器会根据值自动判断类型。

### 2. 变量名命名规则

- 只能由字母、数字、下划线组成，且**不能以数字开头**
- 不能使用关键字（如 `if`、`for`、`class` 等）
- 使用小写字母加下划线分隔单词：`user_name`、`total_price`

```python
user_name = "Alice"   # 推荐
total_price = 99.9    # 推荐
2name = "Tom"         # 报错：不能以数字开头
user-name = "Tom"     # 报错：不能包含连字符
class = 1             # 报错：class 是关键字
```

可以用 `keyword.kwlist` 查看全部关键字：

```python
import keyword
print(keyword.kwlist)
```

---

### 3. 常见基本数据类型

#### （1）字符串 `str`

字符串用于表示文本，需要写在引号中。

```python
name = "Alice"
message = 'Hello'
```

#### （2）整数 `int`

整数用于表示没有小数部分的数字。Python 3 中整数没有大小限制。

```python
age = 18
huge = 10 ** 100  # 超大整数也可以
```

#### （3）浮点数 `float`

浮点数用于表示小数。

```python
price = 19.9
```

注意浮点数本质是二进制近似存储，直接比较可能出问题：

```python
print(0.1 + 0.2)          # 0.30000000000000004
print(0.1 + 0.2 == 0.3)   # False
```

需要精确比较时，用 `round()` 或 `math.isclose()`：

```python
print(round(0.1 + 0.2, 2) == 0.3)   # True
import math
print(math.isclose(0.1 + 0.2, 0.3, abs_tol=1e-9))  # True
```

需要精确十进制运算（金额计算）时，用 `decimal` 模块：

```python
from decimal import Decimal
print(Decimal("0.1") + Decimal("0.2"))   # 0.3
```

#### （4）布尔值 `bool`

布尔值只有两个：

```python
True
False
```

注意：`bool` 是 `int` 的子类，`True == 1`、`False == 0`。

```python
print(True + True)   # 2
```

在条件判断中，一些值会被当作"假值"（falsy）：

```python
bool(0)          # False
bool(0.0)        # False
bool("")         # False 空字符串
bool([])         # False 空列表
bool({})         # False 空字典
bool(None)       # False
bool("abc")      # True
bool([1, 2])     # True
```

#### （5）`None` 空值

`None` 表示"什么都没有"，是独立类型 `NoneType`，常用于占位、表示函数无返回值。

```python
x = None
print(x is None)   # True（判断 None 用 is，不要用 ==）
```

---

### 4. 查看数据类型

可以用 `type()` 查看变量的数据类型。

```python
name = "Alice"
print(type(name))
```

输出：

```text
<class 'str'>
```

单引号和双引号都可以表示字符串，字符串内含有引号时注意转义：

```python
print("He said \"hi\"")   # He said "hi"
print('It\'s ok')         # It's ok
print("It's ok")          # 也可以混用引号避免转义
```

---

### 5. 输出与输入

#### 输出：`print()`

```python
name = "Alice"
age = 30

print(name)
print(age)
```

如果要把字符串和数字放在同一句话里，不能直接用 `+` 拼接字符串和整数。

错误写法：

```python
print(name + " is " + age + " years old")
```

因为 `age` 是整数，不能直接和字符串相加。可以使用下面两种写法。

写法 1：强制类型转换

```python
print(name + " is " + str(age) + " years old")
```

写法 2：f-string（推荐）

```python
print(f"{name} is {age} years old")
```

`print()` 的额外参数：

```python
print("a", "b", sep="-")     # a-b，指定分隔符
print("hello", end="")       # 不换行
print("world")
```

#### 输入：`input()`

```python
user_input = input("Enter your name: ")
print(user_input)
print(type(user_input))
```

`input()` 得到的结果**默认都是字符串**。

```python
age = input("Enter your age: ")
print(type(age))  # <class 'str'>
```

如果想把输入结果当作整数使用，需要手动转换：

```python
age = int(input("Enter your age: "))
```

---

## 三、运算符

### 1. 算术运算符

```python
print(10 + 3)   # 13
print(10 - 3)   # 7
print(10 * 3)   # 30
print(10 / 3)   # 3.333...，普通除法始终返回 float
print(10 // 3)  # 3，整除（向下取整）
print(-10 // 3) # -4，注意是向下取整不是截断
print(10 % 3)   # 1，取余
print(10 ** 3)  # 1000，幂运算
```

### 2. 赋值运算符

```python
x = 3
x += 3   # 等价于 x = x + 3
print(x) # 6
```

类似写法还有：

```python
x -= 1
x *= 2
x /= 3
```

### 3. 比较运算符

比较运算的结果是布尔值。

```python
print(3 > 2)    # True
print(3 < 2)    # False
print(3 == 2)   # False
print(3 != 2)   # True
print(3 >= 3)   # True
print(2 <= 5)   # True
```

Python 支持**链式比较**：

```python
age = 20
print(18 <= age < 30)   # True，等价于 18 <= age and age < 30
```

注意 `==`（值相等）与 `is`（身份相同，即同一个对象）的区别：

```python
a = [1, 2, 3]
b = a          # 引用同一个对象
c = [1, 2, 3]  # 内容相同但独立对象

print(a == b)  # True
print(a is b)  # True
print(a == c)  # True
print(a is c)  # False
```

小整数（-5~256）和短字符串会被 Python 缓存，`is` 可能返回 True，但这是实现细节，不应依赖。

### 4. 逻辑运算符

| 运算符 | 含义 |
|---|---|
| `and` | 与：两边都为 `True`，结果才是 `True` |
| `or` | 或：只要有一边为 `True`，结果就是 `True` |
| `not` | 非：对布尔值取反 |

例子：

```python
age = 20
has_id = True

print(age >= 18 and has_id)  # True
print(age < 18 or has_id)    # True
print(not has_id)            # False
```

`and` 和 `or` 返回的不是布尔值，而是**操作数本身**（短路求值）：

```python
print(0 and 100)     # 0：第一个为假，直接返回第一个
print(1 and 100)     # 100：第一个为真，返回第二个
print(0 or 100)      # 100
print(1 or 100)      # 1
```

利用这个特性可以做默认值：

```python
name = input("name: ") or "Anonymous"
# 用户没输入（空字符串为假）时，name 取 "Anonymous"
```

### 5. 成员与身份运算符

```python
print("a" in "abc")     # True
print(2 in [1, 2, 3])   # True
print("key" in {"key": 1})  # True，对字典判断的是【键】
```

### 6. 运算符优先级

从高到低（常用部分）：

| 优先级 | 运算符 |
|---|---|
| 高 | `**` 幂 |
| | `*` `/` `//` `%` |
| | `+` `-` |
| | `<` `<=` `>` `>=` `==` `!=` |
| | `not` |
| | `and` |
| 低 | `or` |

```python
print(2 + 3 * 4)    # 14
print((2 + 3) * 4)  # 20
```

---

## 四、字符串 `str` 深入

字符串是 Python 中最常用的数据类型之一，也是学习后续所有容器（列表、字典等）的基础。

**核心特性：字符串不可变（immutable）**。任何"修改"操作都会生成新字符串，原字符串不变。

```python
s = "abc"
s.upper()
print(s)   # abc，原字符串没有被修改
```

---

### 1. 索引与切片

```python
course = "python for beginners"

print(course[0])    # p
print(course[-1])   # s，负索引从右往左数
print(course[1:])   # ython for beginners
print(course[:5])   # pytho
print(course[0:6])  # python
```

要点：

- 索引从 `0` 开始
- 负数索引表示从右往左数，`-1` 是最后一个字符
- 切片 `start:end` 包含 `start`，**不包含** `end`（左闭右开）

#### 切片完整语法：`s[start:end:step]`

```python
s = "0123456789"

print(s[::2])    # 02468，每隔一个取一个
print(s[1::2])   # 13579
print(s[::-1])   # 9876543210，反转字符串
print(s[2:8:2])  # 246
print(s[::-2])   # 97531
```

切片越界不会报错，会自动截断：

```python
print("abc"[:100])   # abc
print("abc"[5:])     # （空字符串）
```

### 2. 多行字符串

```python
inform = '''
Hello, everybody
This is for beginners
'''

print(inform)
```

三引号可以保留换行格式，适合写多行文本。

### 3. 格式化字符串

#### f-string（推荐）

```python
first = 'Sun'
last = 'Web'
message = f'{first} [{last}] is an engineer'
print(message)
```

f-string 支持表达式：

```python
price = 49.5
qty = 3
print(f"total = {price * qty}")        # total = 148.5
print(f"n = {10 / 3:.2f}")             # n = 3.33，保留两位小数
print(f"{123456789:,}")                # 123,456,789，千分位
print(f"{0.5:.1%}")                    # 50.0%，百分比
print(f"{42:05d}")                     # 00042，补零
print(f"{'center':^10}")               # '  center  '，居中填充
print(f"{'left':<10}|")                # 'left      |'，左对齐
print(f"{'right':>10}")                # '     right'，右对齐
```

#### format 方法

```python
print("{} is {}".format("Sun", "engineer"))                          # 按位置
print("{1} is {0}".format("engineer", "Sun"))                        # 按下标
print("{name} is {job}".format(name="Sun", job="engineer"))          # 按名称
```

#### 旧式 `%` 格式化

```python
print("%s is %d years old" % ("Alice", 30))   # %s 字符串，%d 整数
print("%.2f" % 3.14159)                        # 3.14
```

三种方式中 f-string 最清晰、性能最好，优先使用。

### 4. 常用字符串方法（分组详解）

#### （1）大小写转换

```python
s = "python for beginners"

print(s.upper())        # PYTHON FOR BEGINNERS
print(s.lower())        # python for beginners
print(s.capitalize())   # Python for beginners，首字母大写其余小写
print(s.title())        # Python For Beginners，每个单词首字母大写
print(s.swapcase())     # PYTHON FOR BEGINNERS，大小写互换
```

#### （2）查找类

```python
s = "python for beginners"

print(s.find("o"))         # 4，第一个 o 的位置
print(s.find("z"))         # -1，找不到返回 -1
print(s.rfind("o"))        # 17，从右往左找
print(s.index("o"))        # 4，查找，找不到会抛 ValueError
print(s.count("o"))        # 2，统计出现次数
print("python" in s)       # True，是否包含
print(s.startswith("py"))  # True，是否以...开头
print(s.endswith("rs"))    # True，是否以...结尾
```

`find()` 找不到时返回 `-1`；`index()` 找不到时抛异常；如果只关心是否包含，直接用 `in` 更清晰。

指定查找范围：

```python
print(s.find("o", 5, 15))   # 在第 5~14 个字符之间找 "o"
```

#### （3）判断类（返回布尔值）

```python
print("123".isdigit())     # True，全是数字
print("abc".isalpha())     # True，全是字母
print("abc123".isalnum())  # True，字母或数字
print("   ".isspace())     # True，全是空白
print("abc".islower())     # True，全小写
print("ABC".isupper())     # True，全大写
print("Title Case".istitle())  # True
```

典型应用：判断输入是否为数字

```python
s = input("input a number: ")
if s.isdigit():
    n = int(s)
```

#### （4）拆分与合并

```python
s = "apple,banana,cherry"

print(s.split(","))         # ['apple', 'banana', 'cherry']，按分隔符拆分
print("a b  c".split())     # ['a', 'b', 'c']，不传参时按任意空白拆分
print(s.split(",", 1))      # ['apple', 'banana,cherry']，最多拆 1 次
print(s.rsplit(",", 1))     # ['apple,banana', 'cherry']，从右往左拆

lines = "a\nb\nc"
print(lines.splitlines())   # ['a', 'b', 'c']，按换行拆分

lst = ["2024", "01", "15"]
print("-".join(lst))        # 2024-01-15，用 - 拼接列表
```

`join` 比用 `+` 循环拼接快得多，字符串拼接也推荐 `"".join([...])`。

#### （5）去除空白

```python
s = "  hello  "

print(s.strip())      # "hello"，去掉两端空白
print(s.lstrip())     # "hello  "，去左端
print(s.rstrip())     # "  hello"，去右端
print("**hi**".strip("*"))   # hi，可以指定去掉的字符
```

典型应用：`input()` 拿到的内容常带多余空白

```python
name = input("name: ").strip()
```

#### （6）替换与补全

```python
s = "python for beginners"

print(s.replace("p", "j"))     # jython for beginners，全部替换
print(s.replace("o", "0", 1))  # 指定替换次数

print("42".zfill(5))       # 00042，补 0 到 5 位
print("ab".ljust(5, "-"))  # ab---
print("ab".rjust(5, "-"))  # ---ab
print("ab".center(5, "-")) # -ab--
```

#### （7）字符与编码

```python
print(ord("A"))                 # 65，字符转 Unicode 码点
print(ord("中"))                # 20013
print(chr(65))                  # A，码点转字符
print("abc".encode("utf-8"))    # b'abc'，字符串转字节
print(b"\xe4\xb8\xad".decode("utf-8"))  # 中，字节转回字符串
```

#### （8）字符串方法不修改原字符串

```python
s = "abc"
t = s.replace("a", "A")
print(s)   # abc（原串不变）
print(t)   # Abc（新串）
```

习惯上可以写 `s = s.replace(...)` 来"更新"变量。

---

### 5. 字符串的迭代

```python
for ch in "abc":
    print(ch)
```

用 `enumerate` 同时拿索引和字符：

```python
for i, ch in enumerate("abc"):
    print(i, ch)
```

常见易错点：变量名要保持一致，例如 `course` 不要误写成 `couerse`。

---

## 五、列表 `list` 深入

列表是 Python 中最重要的数据结构，特点是：

- **有序**：元素有固定顺序，可通过索引访问
- **可变**：可以增删改元素
- **可异构**：可以存放不同类型的数据

```python
fruits = ["apple", "banana", "cherry"]
mixed = [1, "two", 3.0, True]   # 不同类型混存
nested = [[1, 2], [3, 4]]       # 列表嵌套
```

---

### 1. 访问元素

```python
print(fruits[0])   # apple
print(fruits[1])   # banana
print(fruits[-1])  # cherry
```

索引越界会报 `IndexError`；切片越界不会报错。

### 2. 切片（与字符串规则相同）

```python
nums = [0, 1, 2, 3, 4, 5]

print(nums[1:4])    # [1, 2, 3]
print(nums[:3])     # [0, 1, 2]
print(nums[3:])     # [3, 4, 5]
print(nums[::2])    # [0, 2, 4]
print(nums[::-1])   # [5, 4, 3, 2, 1, 0]，反转
print(nums[::])     # [0, 1, 2, 3, 4, 5]，完整复制
```

注意：`nums[:]` 是**浅拷贝**，得到新列表但元素仍是原对象（见下文"拷贝陷阱"）。

切片还可以**赋值**（批量替换，甚至可以改变长度）：

```python
nums = [0, 1, 2, 3, 4, 5]
nums[1:3] = [10, 20, 30]   # [0, 10, 20, 30, 3, 4, 5]
nums[1:4] = [9]            # [0, 9, 4, 5]
del nums[1:2]              # 删除切片
```

### 3. 修改列表：方法详解

```python
fruits = ["apple", "banana", "cherry"]

fruits.append("orange")            # 末尾添加一个元素
fruits.extend(["kiwi", "mango"])   # 末尾批量添加
fruits.insert(2, "watermelon")     # 在索引 2 处插入
print(fruits)
# ['apple', 'banana', 'watermelon', 'cherry', 'orange', 'kiwi', 'mango']

fruits.remove("apple")             # 删除【第一个】指定值，值不存在报 ValueError
print(fruits.pop())                # 删除并返回最后一个元素 -> mango
print(fruits.pop(1))               # 删除并返回索引 1 的元素 -> banana
del fruits[0]                      # 删除索引 0 的元素（del 是语句不是方法）
print(fruits)
# ['watermelon', 'cherry', 'orange', 'kiwi']

fruits.clear()                     # 清空列表
print(fruits)                      # []
```

查找类方法：

```python
nums = [1, 2, 3, 2, 4]
print(nums.index(2))    # 1，第一个 2 的位置，找不到抛 ValueError
print(nums.count(2))    # 2，统计出现次数
```

排序与反转：

```python
nums = [3, 1, 5]
nums.sort()             # 原地升序排序（修改原列表）
nums.sort(reverse=True) # 原地降序排序
nums.reverse()          # 原地反转
print(nums)             # [5, 3, 1]
```

`sorted()` 是内置函数，返回**新列表**，不改原列表：

```python
nums = [3, 1, 5]
new = sorted(nums)      # 新列表 [1, 3, 5]
print(nums)             # [3, 1, 5]，原列表不变
```

带自定义规则的排序（key 参数）：

```python
words = ["banana", "apple", "Cherry"]
print(sorted(words))                        # ['Cherry', 'apple', 'banana']，大写排前
print(sorted(words, key=str.lower))         # 忽略大小写排序
print(sorted(words, key=len))               # 按长度排序
print(sorted([(1, 9), (2, 1)], key=lambda x: x[1]))  # 按元组第二个元素排序
```

### 4. 列表推导式（list comprehension）

用一行代码快速生成列表，是 Python 最重要的语法之一。

```python
squares = [x ** 2 for x in range(10)]            # [0, 1, 4, ..., 81]
even = [x for x in range(20) if x % 2 == 0]      # 带条件
```

`列表推导式` 等价于普通循环：

```python
squares = []
for x in range(10):
    squares.append(x ** 2)
```

嵌套推导式（二维）：

```python
matrix = [[x * y for x in range(3)] for y in range(3)]
# [[0, 0, 0], [0, 1, 2], [0, 2, 4]]

tuples = [(x, y) for x in range(3) for y in range(3)]  # 双重循环
```

字符串处理：

```python
words = ["Hello", "WORLD", "python"]
lower = [w.lower() for w in words]                  # ['hello', 'world', 'python']
lengths = [len(w) for w in words]                   # [5, 5, 6]
filtered = [w for w in words if len(w) > 4]         # ['Hello', 'WORLD', 'python']
```

如果只是循环不需要结果，用普通循环；如果需要惰性计算，用生成器表达式（见函数章节）。

### 5. 引用与拷贝陷阱（重点）

列表是**可变对象**，赋值的本质是"引用传递"（让两个名字指向同一个列表）。

#### 陷阱 1：直接赋值是别名，不是拷贝

```python
a = [1, 2, 3]
b = a          # a 和 b 指向同一个列表
b.append(4)
print(a)       # [1, 2, 3, 4]，a 也被修改了！
```

#### 陷阱 2：浅拷贝 vs 深拷贝

```python
import copy

a = [[1, 2], [3, 4]]
b = a.copy()          # 浅拷贝：外层是新列表，内层元素还是同一个对象
b[0].append(99)
print(a)              # [[1, 2, 99], [3, 4]]，内层被改到了！

c = copy.deepcopy(a)  # 深拷贝：完全独立
c[0].append(1)
print(a)              # [[1, 2, 99], [3, 4]]，不受影响
```

`copy()`、`list()`、`a[:]` 都是浅拷贝；嵌套结构要独立副本必须 `deepcopy`。

#### 陷阱 3：`[[0] * 3] * 3` 不是 3 行独立的列表

```python
matrix = [[0] * 3] * 3   # 看起来是 3x3 矩阵
matrix[0][0] = 5
print(matrix)            # [[5, 0, 0], [5, 0, 0], [5, 0, 0]]，三行是同一个对象！
```

正确写法：

```python
matrix = [[0] * 3 for _ in range(3)]   # 每行独立
matrix[0][0] = 5
print(matrix)            # [[5, 0, 0], [0, 0, 0], [0, 0, 0]]
```

### 6. 常用遍历技巧

```python
fruits = ["apple", "banana", "cherry"]

for fruit in fruits:
    print(fruit)

for i in range(len(fruits)):        # 同时需要索引时
    print(i, fruits[i])

for i, fruit in enumerate(fruits):  # enumerate 更 Pythonic
    print(i, fruit)

for fruit in reversed(fruits):      # 反转遍历
    print(fruit)
```

同时遍历两个列表用 `zip`：

```python
names = ["a", "b", "c"]
scores = [90, 85, 88]

for name, score in zip(names, scores):
    print(name, score)

print(list(zip(names, scores)))   # [('a', 90), ('b', 85), ('c', 88)]
```

`*` 解包列表：

```python
nums = [1, 2, 3]
print(*nums)      # 1 2 3，等价于 print(1, 2, 3)
a, b, c = nums    # 解包到三个变量
```

### 7. 二维列表

```python
matrix = [[1, 2, 3], [4, 5, 6]]
print(matrix[1][1])  # 5，先取第 1 行，再取第 1 个元素
```

遍历二维列表：

```python
for row in matrix:
    for item in row:
        print(item, end=" ")
    print()

for i, row in enumerate(matrix):
    for j, item in enumerate(row):
        print(f"matrix[{i}][{j}] = {item}")
```

### 8. 列表的性能提示

- `append` / `pop()`（末尾操作）是 O(1)，很快
- `insert(0, x)` / `pop(0)`（头部操作）是 O(n)，要移动所有元素
- `in` 判断成员是 O(n)；频繁成员判断用集合 `set`
- Python 的 `list` 本质是**动态数组**，元素在内存中连续存放；插入删除会牵动后续元素。与链表等结构的详细对比见 [[Python数据结构与算法]]

---

## 六、元组 `tuple`

元组和列表很像，但**元组不可修改**。

```python
coordinates = (10, 20)
print(coordinates[0])  # 10
```

---

### 1. 元组的意义

当某些数据不希望被修改时，用元组更合适，例如：

- 坐标
- 日期
- 固定配置
- 字典的键（元组可哈希，列表不行）

### 2. 单元素元组

只有一个元素的元组必须写逗号：

```python
single = (10,)
not_tuple = (10)

print(type(single))     # <class 'tuple'>
print(type(not_tuple))  # <class 'int'>
```

括号本身不是关键，逗号才是元组语法的核心。

### 3. 拆包（解构）

```python
coordinates = (10, 20)
x, y = coordinates

print(x)  # 10
print(y)  # 20
```

这叫"拆包"，可以把容器中的值一次性赋给多个变量。

拆包进阶（`*` 收集多余元素）：

```python
first, *rest, last = (1, 2, 3, 4, 5)
print(first)   # 1
print(rest)    # [2, 3, 4]
print(last)    # 5

a, b = b, a    # 经典的交换写法，本质就是元组拆包
```

### 4. 元组的"不可变"陷阱

元组本身不能增删改，但如果元组里装的是**可变对象**（如列表），那个对象的内容仍然可以变：

```python
t = (1, 2, [3, 4])
t[2].append(5)   # 元组本身没变，但里面的列表变了
print(t)         # (1, 2, [3, 4, 5])
```

### 5. 命名元组 `namedtuple`

给元组字段起名字，像对象一样用属性访问：

```python
from collections import namedtuple

Point = namedtuple("Point", ["x", "y"])
p = Point(10, 20)

print(p.x)          # 10，属性访问
print(p[0])         # 10，下标访问也行
print(p._asdict())  # {'x': 10, 'y': 20}，转字典
```

### 6. 元组的常用操作

```python
t = (1, 2, 3, 2, 1)
print(len(t))          # 5
print(t.count(2))      # 2，统计出现次数
print(t.index(3))      # 2，第一个 3 的下标
print(2 in t)          # True
print(t + (5, 6))      # (1, 2, 3, 2, 1, 5, 6)，拼接
print(t * 2)           # 重复
print(t[::2])          # 切片和列表一样
```

扩展：函数返回多个值时 Python 实际返回的就是元组：

```python
def divmod_result(a, b):
    return a // b, a % b   # 其实返回了 (q, r) 元组

q, r = divmod_result(10, 3)
```

---

## 七、字典 `dict`

字典是"键值对"结构，基本形式如下：

```python
person = {"name": "Bob", "age": 25}
```

其中：

- `"name"` 是键（key）
- `"Bob"` 是值（value）

要点：键必须**可哈希**（不可变类型），值可以是任意类型。列表不能当键，元组可以。

---

### 1. 访问数据

```python
print(person["name"])           # Bob
print(person.get("name"))       # Bob
print(person.get("height"))     # None，键不存在不报错
print(person.get("height", 0))  # 0，指定默认值
```

`person["key"]` 与 `person.get("key")` 的区别：键不存在时前者抛 `KeyError`，后者返回 `None` 或默认值。判断键是否存在用 `in`：

```python
print("name" in person)   # True
```

### 2. 添加与修改

字符串键必须加引号，否则 Python 会把它当作变量名。

错误写法：

```python
person[height] = 173
person.pop(age)
```

正确写法：

```python
person["height"] = 173     # 键不存在就是添加
person["age"] = 26         # 键已存在就是修改
person.setdefault("city", "Unknown")  # 键不存在才写入
person.pop("age")          # 删除并返回，键不存在报 KeyError
person.pop("age", None)    # 删除，不存在返回默认值
del person["name"]         # 删除（del 语句）
person.clear()             # 清空
```

批量更新 `update`：

```python
p1 = {"name": "Bob", "age": 25}
p2 = {"age": 30, "city": "SH"}
p1.update(p2)              # p1 变成 {"name": "Bob", "age": 30, "city": "SH"}
```

合并成新字典（Python 3.9+ 的 `|` 运算符）：

```python
merged = p1 | p2
```

### 3. 视图对象

```python
person = {"name": "Bob", "age": 25}

print(person.keys())    # dict_keys(['name', 'age'])
print(person.values())  # dict_values(['Bob', 25])
print(person.items())   # dict_items([('name', 'Bob'), ('age', 25)])
```

视图会**跟随字典变化**，遍历时最好先 `list()` 固化，避免"字典在遍历时被修改"的报错：

```python
for k in list(person.keys()):
    ...
```

### 4. 遍历字典

```python
for key, value in person.items():
    print(f"{key}: {value}")

for key in person:        # 等价于遍历 keys()
    print(key)
```

注意：循环体必须缩进。

### 5. 字典推导式

```python
squares = {x: x ** 2 for x in range(5)}   # {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}

names = ["Alice", "Bob"]
lengths = {name: len(name) for name in names}   # {'Alice': 5, 'Bob': 3}

# 过滤
prices = {"apple": 3, "banana": 5, "cherry": 8}
cheap = {k: v for k, v in prices.items() if v < 6}   # {'apple': 3, 'banana': 5}
```

### 6. 键排序

```python
d = {"b": 2, "a": 1, "c": 3}

for k in sorted(d):          # 按键排序
    print(k, d[k])

for k in sorted(d, key=lambda x: d[x]):   # 按值排序
    print(k, d[k])
```

### 7. `collections` 里的专业字典

`defaultdict`：访问不存在的键时不报错，自动创建默认值

```python
from collections import defaultdict

counts = defaultdict(int)      # 默认值类型 int，自动初始化为 0
words = ["a", "b", "a", "c", "a", "b"]
for w in words:
    counts[w] += 1             # 不需要先判断 w 是否存在
print(counts)                  # defaultdict(<class 'int'>, {'a': 3, 'b': 2, 'c': 1})

groups = defaultdict(list)     # 默认空列表
for w in words:
    groups[w].append(len(w))
```

`Counter`：专门做频次统计

```python
from collections import Counter

c = Counter("abracadabra")
print(c)                       # Counter({'a': 5, 'b': 2, 'r': 2, ...})
print(c.most_common(2))        # [('a', 5), ('b', 2)]，出现最多的前两名
print(c["z"])                  # 0，不存在的键返回 0
```

`OrderedDict`：在 3.7 之前用于保证插入顺序；**Python 3.7+ 普通字典本身已有序**，一般不需要。

---

## 八、集合 `set`

集合的特点：

- 元素无序
- 元素不重复
- 常用于去重、成员判断、集合运算

```python
unique_numbers = {1, 2, 3, 2}
print(unique_numbers)  # 重复的 2 只保留一个，显示顺序不固定
```

注意：空集合必须写 `set()`，`{}` 是空字典。

```python
s = set()
```

---

### 1. 去重

```python
nums = [1, 2, 2, 3, 3, 3]
print(set(nums))  # {1, 2, 3}
```

### 2. 成员判断

```python
s = {1, 2, 3}
print(2 in s)   # True
```

集合的 `in` 是 O(1)，列表的 `in` 是 O(n)。大数据量成员判断优先用集合。

### 3. 增删操作

```python
s = {1, 2, 3}
s.add(4)          # 添加
s.add(4)          # 已存在则无效果
s.update([5, 6])  # 批量添加
s.remove(3)       # 删除，不存在抛 KeyError
s.discard(99)     # 删除，不存在也不报错
s.pop()           # 随机删除一个并返回
s.clear()         # 清空
```

### 4. 集合运算

```python
a = {1, 2, 3, 4}
b = {3, 4, 5, 6}

print(a | b)          # 并集 {1, 2, 3, 4, 5, 6}
print(a & b)          # 交集 {3, 4}
print(a - b)          # 差集 {1, 2}，a 有 b 没有
print(a ^ b)          # 对称差 {1, 2, 5, 6}，不同时属于两边的
print(a >= {1, 2})    # 是否为超集
print({1, 2} <= a)    # 是否为子集
```

### 5. 集合推导式

```python
squares = {x ** 2 for x in range(5)}    # {0, 1, 4, 9, 16}
```

### 6. `frozenset` 不可变集合

普通 `set` 可变、不可哈希，不能作字典键；`frozenset` 不可变、可哈希：

```python
fs = frozenset([1, 2, 3])
d = {fs: "frozen"}     # 可以当字典键
```

### 7. 集合元素的哈希要求

集合里只能放**可哈希**（不可变）类型：数字、字符串、元组可以；列表、字典、集合不行。

```python
s = {1, "a", (2, 3)}   # OK
# s = {1, [2]}         # TypeError: unhashable type
```

---

## 九、流程控制

程序并不总是从上到下顺序执行，经常需要根据条件做判断，或者重复执行某段代码。

---

### 1. 条件语句 `if`

```python
age = 18

if age >= 18:
    print("Adult")
elif age >= 13:
    print("Teenager")
else:
    print("Child")
```

结构说明：

- `if`：如果条件成立
- `elif`：否则如果
- `else`：否则

Python 用**缩进**表示代码块，不使用大括号。

三元表达式（单行条件赋值）：

```python
status = "adult" if age >= 18 else "minor"
```

### 2. `for` 循环

`for` 循环适合遍历列表、字符串、字典等可迭代对象。

```python
fruits = ["apple", "banana", "cherry"]

for fruit in fruits:
    print(fruit)
```

#### `range()` 的用法

```python
for i in range(5):
    print(i)
```

输出：

```text
0
1
2
3
4
```

`range(5)` 表示从 `0` 到 `4`。

还可以指定开始、结束、步长：

```python
for i in range(1, 6):      # 1 到 5
    print(i)

for i in range(0, 10, 2):  # 0, 2, 4, 6, 8
    print(i)

for i in range(10, 0, -2): # 10, 8, 6, 4, 2 倒着走
    print(i)
```

#### `for-else`（循环正常结束才执行）

```python
for i in range(5):
    if i == 10:
        break
else:
    print("循环没有被打断")   # break 过就不会执行这里
```

### 3. `while` 循环

`while` 循环适合"只要条件成立就一直重复"的场景。

```python
count = 0

while count < 5:
    print(count)
    count += 1
```

`while` 必须保证条件最终会变为假，否则是死循环。

### 4. `break` 和 `continue`

#### `break`：直接结束整个循环

```python
for i in range(10):
    if i == 5:
        break
    print(i)
```

输出：

```text
0
1
2
3
4
```

#### `continue`：结束当前这一轮，进入下一轮

```python
for i in range(5):
    if i == 2:
        continue
    print(i)
```

输出：

```text
0
1
3
4
```

### 5. `try` 循环配合输入校验的经典写法

```python
while True:
    s = input("Enter a number: ")
    if s.isdigit():
        break
print(f"got {s}")
```

---

## 十、函数

函数的本质是：**把某段功能封装起来，方便反复调用。**

---

### 1. 为什么要用函数

如果一段代码会反复使用，就不要一遍遍重写，而应该封装成函数。函数可以让代码更清晰，也更容易维护。

### 2. 内置函数

Python 已经自带很多函数，例如：

```python
print()
input()
int()
float()
str()
abs()
round()
max()
min()
len()
type()
```

常用内置函数说明：

```python
x = -5
print(abs(x))             # 5，绝对值
print(chr(65))            # A，编码转字符
print(ord("A"))           # 65，字符转编码
print(round(3.14159, 2))  # 3.14，四舍五入到小数点后 2 位
print(max([3, 1, 5]))     # 5，最大值
print(min([3, 1, 5]))     # 1，最小值
print(sum([3, 1, 5]))     # 9，求和
```

### 3. 自定义函数

```python
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"
```

调用：

```python
print(greet("Alice"))
print(greet("David", "Welcome"))
```

### 4. 参数机制

#### （1）位置参数与关键字参数

```python
def add(a, b):
    return a + b

result = add(3, 5)             # 按位置传参
result = add(a=3, b=5)         # 按关键字传参，更清晰
result = add(3, b=5)           # 位置参数要在关键字参数之前
```

#### （2）默认参数

```python
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"
```

如果调用时不传 `greeting`，函数会使用默认值 `"Hello"`。

**默认参数不要直接写可变对象**，例如列表或字典。需要默认空列表时，用 `None` 再在函数内部创建：

```python
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

如果写成 `def add_item(item, items=[]):`，所有不传 `items` 的调用会**共享同一个列表**，产生难以察觉的 bug。

#### （3）可变参数 `*args`

接收任意多个位置参数，打包成元组：

```python
def total(*args):
    return sum(args)

print(total(1, 2, 3, 4))   # 10
```

#### （4）关键字可变参数 `**kwargs`

接收任意多个关键字参数，打包成字典：

```python
def show_info(**kwargs):
    for k, v in kwargs.items():
        print(f"{k} = {v}")

show_info(name="Bob", age=25)
```

星号还可以用于"强制关键字参数"和解包调用：

```python
def f(a, b, *, c):     # c 必须用关键字传入
    ...

nums = [3, 5]
add(*nums)             # 解包列表调函数，等价于 add(3, 5)
d = {"a": 1, "b": 2}
add(**d)               # 解包字典，等价于 add(a=1, b=2)
```

### 5. 返回值

返回值是函数执行后交回来的结果。

```python
result = add(3, 5)
print(result)  # 8
```

没有 `return` 的函数返回 `None`。也可以返回多个值（实际是元组）：

```python
def min_max(nums):
    return min(nums), max(nums)

lo, hi = min_max([3, 1, 5])   # lo=1, hi=5
```

### 6. 匿名函数 `lambda`

只能写单个表达式的小函数，常用于需要"一次性小函数"的场景：

```python
add = lambda a, b: a + b
print(add(3, 5))   # 8

nums = [(1, 5), (3, 2), (2, 4)]
print(sorted(nums, key=lambda x: x[1]))   # 按第二个元素排序

print(list(map(lambda x: x ** 2, [1, 2, 3])))   # [1, 4, 9]
print(list(filter(lambda x: x % 2 == 0, [1, 2, 3, 4])))  # [2, 4]
```

注意：`map`/`filter` 返回迭代器，用 `list()` 才能直接看到内容。

### 7. 作用域与 `LEGB`

Python 查找变量的顺序：`Local`（局部）→ `Enclosing`（外层函数）→ `Global`（全局）→ `Built-in`（内置）。

```python
x = 10            # 全局变量

def outer():
    x = 20        # 外层函数变量（Enclosing）
    def inner():
        x = 30    # 局部变量（Local）
        print(x)  # 30
    inner()
    print(x)      # 20

print(x)          # 10
```

在函数内部修改全局变量需要 `global`：

```python
counter = 0

def inc():
    global counter
    counter += 1
```

（更推荐的做法是把状态封装进类或容器，少用 `global`。）

### 8. 闭包（closure）

内层函数引用了外层函数的变量，并且外层函数把这个内层函数返回出去，就形成了闭包。外层变量不会随函数结束而消失：

```python
def make_counter():
    count = 0
    def add():
        nonlocal count   # 修改外层函数的变量
        count += 1
        return count
    return add

c1 = make_counter()
print(c1())   # 1
print(c1())   # 2
```

闭包的典型用途：计数器、装饰器、工厂函数（生成带特定配置的函数）。

### 9. 装饰器（decorator）

装饰器是"包裹函数"的函数：不修改原函数代码，而是给原函数增加额外行为。

```python
import time

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time() - start:.4f}s")
        return result
    return wrapper

@timer              # 等价于 slow_fn = timer(slow_fn)
def slow_fn():
    time.sleep(0.1)
    return 42

print(slow_fn())    # 会先打印耗时，再输出 42
```

装饰器破坏了原函数的名字和文档字符串，用 `functools.wraps` 修复：

```python
from functools import wraps

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ...
    return wrapper
```

Python 自带常用装饰器：`@staticmethod`、`@classmethod`、`@property`（见 OOP 章节）、`@functools.lru_cache`（缓存计算结果，见算法笔记动态规划章节）。

### 10. 递归

函数调用自己就是递归，必须要有**终止条件**：

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

递归常用于树、图、分治等场景（见 [[Python数据结构与算法]]）。

注意：Python 默认递归深度限制约 1000 层，超出抛 `RecursionError`；需要更多时用迭代或显式栈，不建议调高 `sys.setrecursionlimit`。

### 11. 生成器 `yield` 与迭代器

`yield` 让函数变成生成器：每次调用 `next()`（或被 `for` 遍历）才往下执行一段，逐个产出值，**不必一次性算完**，省内存：

```python
def countdown(n):
    while n > 0:
        yield n
        n -= 1

for x in countdown(3):
    print(x)   # 3, 2, 1

# 对比：range 就是懒加载的；list(range(10**7)) 会一次性占几十 MB 内存
```

生成器表达式（惰性版的推导式）：

```python
squares_gen = (x ** 2 for x in range(10))   # 生成器
squares_list = [x ** 2 for x in range(10)]  # 列表

print(sum(squares_gen))   # 285，生成器只能从头遍历一次
```

可迭代对象（iterable）与迭代器（iterator）的关系：`for` 会先对对象调用 `iter()` 拿到迭代器，再反复 `next()`，直到 `StopIteration`。

```python
lst = [1, 2, 3]
it = iter(lst)
print(next(it))   # 1
print(next(it))   # 2
```

---

## 十一、文件操作

程序经常需要读写文件，例如文本、日志、配置等。

---

### 1. 写文件

```python
with open("diary.txt", "w", encoding="utf-8") as f:
    f.write("Today was sunny\n")
```

说明：

- `"w"`：写入模式
- 如果文件不存在，会创建文件
- 如果文件已存在，会**覆盖原内容**
- `encoding="utf-8"` 保证中文不乱码，务必写上

### 2. 读文件

```python
with open("diary.txt", "r", encoding="utf-8") as f:
    content = f.read()      # 一次性读取全部
    print(content)
```

按行读取（大文件推荐，不一次性占内存）：

```python
with open("diary.txt", "r", encoding="utf-8") as f:
    for line in f:          # 文件本身就是可迭代的
        print(line.strip()) # strip 去掉行尾换行
```

```python
with open("diary.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()   # 读取为列表，每行一个元素
```

### 3. 为什么用 `with open(...)`

`with open(...)` 可以在文件使用完后自动关闭文件，比手动打开和关闭更安全，也更规范。避免使用 `f = open(...)` 后忘记 `f.close()`。

多个文件一起打开：

```python
with open("a.txt", encoding="utf-8") as fa, open("b.txt", "w", encoding="utf-8") as fb:
    fb.write(fa.read())
```

### 4. 其他常见模式

- `"a"`：追加写入（不会覆盖已有内容）
- `"r+"`：读写
- `"rb"`：按二进制读取
- `"wb"`：按二进制写入

### 5. JSON 读写（最常用格式之一）

```python
import json

data = {"name": "Bob", "age": 25, "skills": ["python", "sql"]}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)   # 写

with open("data.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)     # 读回字典

s = json.dumps(data, ensure_ascii=False)   # 转字符串
d = json.loads(s)                          # 字符串转对象
```

注意 `ensure_ascii=False` 才能让中文以原文显示，而不是 `\uXXXX` 转义。

### 6. CSV 读写

```python
import csv

with open("scores.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["name", "score"])
    writer.writerow(["Alice", 90])

with open("scores.csv", "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:     # row 是每行的列表
        print(row)
```

### 7. `pathlib` 现代路径操作（推荐）

```python
from pathlib import Path

p = Path("data/report.txt")
print(p.exists())          # 是否存在
print(p.name)              # report.txt
print(p.stem)              # report
print(p.suffix)            # .txt
print(p.parent)            # data

content = p.read_text(encoding="utf-8")    # 代替 open
p.write_text("hello", encoding="utf-8")

p.mkdir(exist_ok=True)     # 创建目录
```

---

## 十二、异常处理

程序运行时可能报错，比如：

- 除以 `0`
- 输入的不是数字
- 文件不存在

如果不处理，程序就会中断。异常处理可以让程序更稳定。

---

### 1. 基本结构

```python
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Cannot divide by zero!")
finally:
    print("Cleanup code")
```

含义：

- `try`：尝试执行某段代码
- `except`：出错时执行的处理逻辑
- `finally`：无论是否出错都会执行
- `else`：没有出错时才执行（在 `except` 之后）

```python
try:
    age = int(input("Age: "))
except ValueError:
    print("Invalid value")
else:
    print(f"valid age {age}")    # 只有没出错才执行
finally:
    print("always runs")
```

### 2. 捕获更精确的异常类型

```python
try:
    with open("missing.txt") as f:
        content = f.read()
except FileNotFoundError:
    print("文件不存在")
except PermissionError:
    print("没有权限")
```

一个 `except` 可以同时捕获多个异常，并拿到异常对象：

```python
try:
    x = int("abc")
except (ValueError, TypeError) as e:
    print(f"出错了：{e}")
```

不建议直接 `except:` 或 `except Exception:` 吞掉所有错误，初学阶段优先捕获明确的异常类型。

### 3. 异常层级

常见异常的继承关系：

```text
BaseException
 └── Exception
      ├── ValueError        （int("abc")）
      ├── TypeError         （1 + "a"）
      ├── ZeroDivisionError （1 / 0）
      ├── IndexError        （列表越界）
      ├── KeyError          （字典键不存在）
      ├── FileNotFoundError （文件不存在）
      ├── AttributeError    （访问不存在的属性/方法）
      └── RecursionError    （递归太深）
```

捕获父类 `Exception` 能兜住所有子类错误。

### 4. 主动抛出异常 `raise`

校验失败时主动报错，比返回一个奇怪的值更规范：

```python
def set_age(age):
    if age < 0:
        raise ValueError("age must be >= 0")
    return age
```

### 5. 自定义异常

```python
class BalanceError(Exception):
    pass

def withdraw(balance, amount):
    if amount > balance:
        raise BalanceError("余额不足")
    return balance - amount
```

自定义异常让错误语义清晰，也方便按类型捕获。

### 6. 异常处理的意义

异常处理不是为了"掩盖错误"，而是为了：

1. 防止程序直接崩溃
2. 给用户更友好的提示
3. 便于调试和维护

---

## 十三、模块与包

当代码越来越多时，不适合全部写在一个文件里，这时就需要用**模块**和**包**组织代码。

---

### 1. 模块

一个 `.py` 文件就是一个模块。

例如有一个文件 `tools.py`：

```python
def add(a, b):
    return a + b
```

在另一个文件中可以这样导入：

```python
import tools

print(tools.add(2, 3))
```

### 2. 导入方式

写法 1：导入整个模块

```python
import math

print(math.ceil(2.9))
print(math.floor(2.9))
```

写法 2：从模块中导入指定内容

```python
from math import ceil, floor

print(ceil(2.9))
print(floor(2.9))
```

写法 3：别名

```python
import numpy as np
import pandas as pd
```

`if __name__ == "__main__"`：只有直接运行本文件时才执行，被 import 时不执行（防止导入时副作用）：

```python
def main():
    print("running")

if __name__ == "__main__":
    main()
```

### 3. 包 `package`

包可以理解成"存放多个模块的文件夹"。通常包中会有一个 `__init__.py` 文件（Python 3.3+ 命名空间包即使没有也常能识别，但加上最稳妥）。

导入方式：

```python
import package.module
```

或者：

```python
from package.module import func
```

### 4. 安装第三方库

```bash
pip install numpy
pip install -r requirements.txt   # 按文件批量安装
```

导出当前环境依赖：

```bash
pip freeze > requirements.txt
```

推荐在**虚拟环境**中开发，避免全局环境混乱：

```bash
python -m venv .venv        # 创建虚拟环境
.venv\Scripts\activate      # Windows 激活
pip install ...             # 装进虚拟环境
```

### 5. 常用标准库速览

| 模块 | 用途 |
|---|---|
| `math` | 数学函数 |
| `random` | 随机数 |
| `datetime` | 日期时间 |
| `json` / `csv` | 数据格式 |
| `re` | 正则表达式 |
| `collections` | 专业容器（defaultdict、Counter、deque） |
| `itertools` | 迭代工具（排列组合、无限迭代） |
| `os` / `sys` / `pathlib` | 系统与路径 |
| `functools` | 函数工具（wraps、lru_cache） |

```python
import random
print(random.randint(1, 6))     # 1~6 随机整数
print(random.choice(["a", "b"]))  # 随机选一个
random.shuffle([1, 2, 3])       # 原地洗牌

from datetime import datetime
print(datetime.now())                     # 当前时间
print(datetime.now().strftime("%Y-%m-%d %H:%M"))  # 格式化
```

---

## 十四、数学库 `math`

Python 标准库中的 `math` 模块提供了很多数学函数。

```python
import math

print(math.ceil(2.9))   # 向上取整，结果 3
print(math.floor(2.9))  # 向下取整，结果 2
print(math.sqrt(16))    # 开平方，结果 4.0
print(math.pi)          # 圆周率
print(math.pow(2, 3))   # 8.0，幂（比 ** 慢但可读性好）
print(math.log(100, 10))# 2.0，以 10 为底
print(math.fabs(-3.5))  # 3.5
print(math.factorial(5))# 120
print(math.isclose(0.1 + 0.2, 0.3))  # True，浮点比较正确姿势
```

`math.floor` 与 `//` 结果一致（对负数都是向下取整）；`trunc` 才是向零截断。

---

## 十五、面向对象编程 OOP

面向对象是一种组织代码的思想。它强调把现实中的事物抽象成"对象"，再用对象保存数据和执行行为。

---

### 1. 类和对象

- **类（class）**：模板
- **对象**：根据模板创建出来的具体实例

例如："人"是类，"张三"是对象。

### 2. 定义类

```python
class Point:
    def move(self):
        print("move")

    def draw(self):
        print("draw")
```

创建对象：

```python
point1 = Point()
point1.x = 10

print(point1.x)
point1.draw()
```

这里：

- `Point` 是类
- `point1` 是对象
- `draw()`、`move()` 是方法
- `x` 是属性

### 3. `self` 是什么

`self` 代表"当前对象本身"。

```python
class Person:
    def talk(self):
        print("hello")
```

当你写：

```python
p = Person()
p.talk()
```

本质上相当于：

```python
Person.talk(p)
```

所以实例方法的第一个参数通常要写 `self`。

### 4. 构造函数 `__init__`

构造函数用于在对象创建时初始化属性。

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

point = Point(10, 20)
print(point.x)
print(point.y)
```

这里：

- `self.x = x`：把传入的参数保存到对象属性中
- 对象一创建，就会自动执行 `__init__`

### 5. 示例：`Person` 类

```python
class Person:
    def __init__(self, name):
        self.name = name

    def talk(self):
        print(f"Hi, I am {self.name}")

john = Person("John Smith")
john.talk()
```

### 6. `__str__` 让 print 输出更友好

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __str__(self):
        return f"Person({self.name}, {self.age})"

p = Person("Bob", 25)
print(p)   # Person(Bob, 25)，而不是 <__main__.Person object at 0x...>
```

### 7. 属性封装与 `@property`

约定：`_name` 表示"内部属性，别直接碰"。用 `@property` 提供受控的读写接口：

```python
class Circle:
    def __init__(self, radius):
        self._radius = radius

    @property
    def radius(self):            # 读取
        return self._radius

    @radius.setter
    def radius(self, value):     # 写入（带校验）
        if value <= 0:
            raise ValueError("radius must be positive")
        self._radius = value

    @property
    def area(self):              # 只读计算属性
        return 3.14159 * self._radius ** 2

c = Circle(5)
print(c.radius)     # 5，像普通属性一样访问
c.radius = 10       # 走 setter（顺便做了校验）
print(c.area)       # 314.159...
```

注意：Python 没有真正的私有属性，"`_` 开头是约定"，"`__` 双下划线"只是名称改写，仍可访问，不要依赖它做真正的私有。

### 8. 类的特殊方法（魔术方法）

`__str__`（用户可读）、`__repr__`（程序员调试）、`__len__`（len()）、`__eq__`（==）、`__lt__`（<）、`__getitem__`（下标访问）、`__call__`（对象当函数调用）等：

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __len__(self):
        return 2

print(Point(1, 2) == Point(1, 2))   # True（没有 __eq__ 时比的是对象地址）
print(len(Point(1, 2)))             # 2
```

### 9. 继承

继承的作用是：**复用已有类的功能，并在此基础上扩展。**

```python
class Mammal:
    def walk(self):
        print("walk")

class Dog(Mammal):
    def bark(self):
        print("bark")

class Cat(Mammal):
    pass
```

这里：

- `Dog` 和 `Cat` 继承了 `Mammal`
- 它们都可以调用 `walk()`
- `Dog` 还额外拥有 `bark()` 方法

```python
dog = Dog()
dog.walk()
dog.bark()
```

子类可以重写父类方法，并用 `super()` 调用父类版本：

```python
class Animal:
    def __init__(self, name):
        self.name = name

class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name)   # 先初始化父类属性
        self.breed = breed
```

### 10. 多态

不同类的对象有同名方法，调用时各自执行自己的版本：

```python
class Dog(Animal):
    def sound(self):
        return "Woof"

class Cat(Animal):
    def sound(self):
        return "Meow"

for a in [Dog("a"), Cat("b")]:
    print(a.sound())   # Woof / Meow
```

### 11. 类方法 / 静态方法

```python
class Student:
    total = 0                     # 类属性（所有实例共享）

    def __init__(self, name):
        self.name = name
        Student.total += 1

    @classmethod                  # 类方法：第一个参数是类本身
    def get_total(cls):
        return cls.total

    @staticmethod                 # 静态方法：与类和实例都无关的工具函数
    def is_name_valid(name):
        return len(name) > 0

print(Student.get_total())
```

### 12. `dataclass` 快速定义数据类

自动生成 `__init__`、`__repr__`、`__eq__`：

```python
from dataclasses import dataclass

@dataclass
class Student:
    name: str
    age: int
    score: float = 0.0

s1 = Student("Alice", 20, 95.5)
s2 = Student("Alice", 20, 95.5)
print(s1)               # 自动有友好的 __repr__
print(s1 == s2)         # True，自动按字段比较
```

### 13. `pass` 的作用

`pass` 表示"先占一个位置，什么都不做"。

当语法上必须写点东西，但暂时没有内容时，就可以写 `pass`。

---

## 十六、容易混淆的知识点

### 1. 列表和元组的区别

- 列表 `list`：可变，用 `[]`
- 元组 `tuple`：不可变，用 `()`

### 2. 字典和集合的区别

- 字典 `dict`：键值对，形如 `{"name": "Tom"}`
- 集合 `set`：只有值，且不重复，形如 `{1, 2, 3}`

### 3. `=` 和 `==` 的区别

- `=`：赋值
- `==`：比较是否相等

```python
x = 5
print(x == 5)  # True
```

### 4. `==` 和 `is` 的区别

- `==`：比较**值**是否相等
- `is`：比较**是不是同一个对象**

```python
a = [1, 2]
b = [1, 2]
print(a == b)   # True
print(a is b)   # False
```

`None` 的判断约定用 `is`：`x is None`。

### 5. `input()` 的结果永远是字符串

```python
num = input("请输入数字：")
print(type(num))  # str
```

如果要做数值运算，必须先转换类型：

```python
num = int(input("请输入数字："))
```

### 6. 深浅拷贝（再次强调）

- 可变对象 `=` 赋值：两个名字指向同一个对象
- `copy()` / `[:]`：浅拷贝，嵌套内容仍共享
- `copy.deepcopy()`：彻底独立

### 7. 可变默认参数陷阱

```python
def add_item(item, items=[]):   # 错误写法
    items.append(item)
    return items
```

改为 `items=None`，函数内再创建空列表。

### 8. 遍历列表时不要删除元素

```python
nums = [1, 2, 3, 4, 5]
for x in nums:        # 边遍历边删除会跳元素
    if x % 2 == 0:
        nums.remove(x)
```

正确做法：遍历副本或收集后统一删除：

```python
nums = [x for x in nums if x % 2 != 0]
```

### 9. 除法的坑

- `/` 总是返回浮点数
- `//` 是向下取整整除（负数要注意）
- `%` 取余结果符号跟随除数（Python 里是右操作数）

```python
print(7 / 2)    # 3.5
print(7 // 2)   # 3
print(-7 // 2)  # -4
print(-7 % 2)   # 1
```

---

## 十七、代码规范建议

### 1. 注意缩进

Python 用缩进区分代码块，缩进错了程序就可能报错。

```python
if age >= 18:
    print("Adult")
```

这里 `print` 前面必须缩进。

### 2. 变量名不要拼错

例如：

- `course` 不要写成 `couerse`
- `engineer` 不要写成 `enginner`

小拼写错误非常容易导致程序报错。

### 3. 字典键名要加引号

```python
person["height"] = 173
```

不能写成 `person[height] = 173`，除非 `height` 本身是一个已经定义好的变量。

### 4. 代码风格（PEP 8 要点）

- 变量/函数用 `snake_case`，类用 `CamelCase`
- 逗号、运算符两侧加空格：`x = a + b`
- 每行不超过 ~79 字符
- 常量用全大写：`MAX_SIZE = 100`

```python
x = 3
x += 3
print(x)
```

清晰的排版能减少阅读和调试成本。

---

## 十八、复习总框架

学 Python 时，可以在脑子里建立这样一张结构图：

### 第一层：数据

- 变量
- 字符串
- 数字（int / float / bool / None）

### 第二层：容器

- 列表（可变、有序）
- 元组（不可变、有序）
- 字典（键值对）
- 集合（去重、无序）

### 第三层：流程

- `if` / `elif` / `else`
- `for` / `while`
- `break` / `continue`

### 第四层：封装

- 函数（参数、返回值、lambda、闭包、装饰器、生成器）
- 模块 / 包

### 第五层：工程能力

- 文件操作（文本 / JSON / CSV）
- 异常处理
- 面向对象（类 / 继承 / 魔术方法 / dataclass）

### 第六层：进阶方向

- 数据结构与算法（链表、栈、队列、树、图、排序、DP）→ [[Python数据结构与算法]]
- 数据分析与 AI 常用库（numpy / pandas / matplotlib）→ [[Python数据分析与AI常用库]]

这样复习时，知识点会更容易归位。

---

## 十九、精炼记忆结论

### 1. Python 基本特点

- 语法简洁
- 动态类型
- 解释执行

### 2. 基本数据类型

- `str`、`int`、`float`、`bool`、`None`

### 3. 四种常用数据结构

- 列表：有序、可变
- 元组：有序、不可变
- 字典：键值对
- 集合：无序、不重复

### 4. 两类循环

- `for`：适合遍历
- `while`：适合条件重复

### 5. 函数作用

- 封装代码
- 提高复用性
- 方便维护

### 6. 面向对象核心

- 类 / 对象 / 继承
- `__init__`、`__str__`、`@property`、`dataclass`

### 7. 文件与异常

- 文件：实现数据持久化（`with open` + `encoding="utf-8"`）
- 异常：防止程序直接崩溃（优先捕获明确类型）

### 8. 三条最重要的 Python 习惯

- 用 f-string 格式化
- 用列表/字典/集合推导式
- 优先 `with`、`enumerate`、`zip`、`for ... in` 而非下标循环