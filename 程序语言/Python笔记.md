# Python 笔记

## 一、Python 基础认识

Python 是一种**解释型、动态类型、语法简洁**的编程语言，适合初学者入门，也广泛用于数据分析、自动化办公、后端开发、人工智能等方向。

学习 Python 可以按下面几条主线展开：

1. **基础语法**：变量、数据类型、输入输出、运算符
2. **数据结构**：字符串、列表、元组、字典、集合
3. **程序控制**：条件语句、循环
4. **函数**：内置函数、自定义函数
5. **文件与异常**：读写文件、错误处理
6. **面向对象**：类、对象、构造函数、继承
7. **模块与包**：代码组织与复用
8. **第三方库实践**：例如 `openpyxl`

---

## 二、变量与基本数据类型

### 1. 什么是变量

变量可以理解为“有名字的存储空间”，用来保存数据。

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

---

### 2. 常见基本数据类型

#### （1）字符串 `str`

字符串用于表示文本，需要写在引号中。

```python
name = "Alice"
message = 'Hello'
```

#### （2）整数 `int`

整数用于表示没有小数部分的数字。

```python
age = 18
```

#### （3）浮点数 `float`

浮点数用于表示小数。

```python
price = 19.9
```

#### （4）布尔值 `bool`

布尔值只有两个：

```python
True
False
```

布尔值常用于条件判断。

---

### 3. 查看数据类型

可以用 `type()` 查看变量的数据类型。

```python
name = "Alice"
print(type(name))
```

输出：

```python
<class 'str'>
```

---

### 4. 输出与输入

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

#### 输入：`input()`

```python
user_input = input("Enter your name: ")
print(user_input)
print(type(user_input))
```

`input()` 得到的结果**默认都是字符串**。

例如：

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
print(10 / 3)   # 3.333...
print(10 // 3)  # 3，整除
print(10 % 3)   # 1，取余
print(10 ** 3)  # 1000，幂运算
```

---

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

---

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

---

### 4. 逻辑运算符

```python
and   # 与：两边都为 True，结果才是 True
or    # 或：只要有一边为 True，结果就是 True
not   # 非：取反
```

例子：

```python
age = 20
has_id = True

print(age >= 18 and has_id)  # True
print(age < 18 or has_id)    # True
print(not has_id)            # False
```

---

## 四、字符串

字符串是 Python 中最常用的数据类型之一。

### 1. 基本访问

```python
course = "python for beginners"

print(course[0])    # p
print(course[-1])   # s
print(course[1:])   # ython for beginners
print(course[:5])   # pytho
print(course[0:6])  # python
```

要点：

- 索引从 `0` 开始。
- 负数索引表示从右往左数。
- 切片 `start:end` 包含 `start`，不包含 `end`。

---

### 2. 多行字符串

```python
inform = '''
Hello, everybody
This is for beginners
'''

print(inform)
```

三引号可以保留换行格式，适合写多行文本。

---

### 3. 格式化字符串

f-string 是最常用、也最清晰的字符串格式化方式。

```python
first = 'Sun'
last = 'Web'
message = f'{first} [{last}] is an engineer'

print(message)
```

---

### 4. 常用字符串方法

```python
course = "python for beginners"

print(len(course))              # 字符串长度
print(course.upper())           # 全部转大写
print(course.lower())           # 全部转小写
print(course.find('o'))         # 查找字符位置
print(course.replace('p', 'j')) # 替换字符
print('python' in course)       # 判断是否包含
```

常见易错点：变量名要保持一致，例如 `course` 不要误写成 `couerse`。

---

## 五、列表 `list`

列表是 Python 中非常重要的数据结构，特点是：

- 有序
- 可修改
- 可以存放不同类型的数据

```python
fruits = ["apple", "banana", "cherry"]
```

---

### 1. 访问元素

```python
print(fruits[0])   # apple
print(fruits[1])   # banana
print(fruits[-1])  # cherry
```

---

### 2. 修改列表

```python
fruits.append("orange")          # 在末尾添加
fruits.pop(2)                    # 删除索引为 2 的元素
fruits.insert(2, "watermelon")   # 在索引 2 处插入
fruits.sort(reverse=True)        # 降序排序
```

---

### 3. 列表运算

```python
print([1, 2] + [3, 4])  # [1, 2, 3, 4]
```

`+` 可以拼接两个列表。

---

### 4. 二维列表

```python
matrix = [[1, 2, 3], [4, 5, 6]]
print(matrix[1][1])  # 5
```

二维列表可以理解为“列表里面还有列表”。

---

### 5. 常用列表方法总结

```python
nums = [3, 1, 5]

nums.append(10)     # 末尾添加
nums.insert(1, 99)  # 指定位置插入
nums.remove(5)      # 删除指定值
nums.pop()          # 删除最后一个元素
nums.clear()        # 清空列表
nums.sort()         # 升序排序
nums.reverse()      # 反转
print(len(nums))    # 长度
```

---

### 6. 遍历列表

```python
fruits = ["apple", "banana", "cherry"]

for fruit in fruits:
    print(fruit)
```

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

---

### 2. 拆包

```python
coordinates = (10, 20)
x, y = coordinates

print(x)  # 10
print(y)  # 20
```

这叫“拆包”，可以把容器中的值一次性赋给多个变量。

---

## 七、字典 `dict`

字典是“键值对”结构，基本形式如下：

```python
person = {"name": "Bob", "age": 25}
```

其中：

- `"name"` 是键（key）
- `"Bob"` 是值（value）

---

### 1. 访问数据

```python
print(person["name"])  # Bob
```

---

### 2. 添加与修改

字符串键必须加引号，否则 Python 会把它当作变量名。

错误写法：

```python
person[height] = 173
person.pop(age)
```

正确写法：

```python
person["height"] = 173
person.pop("age")
```

---

### 3. 常用操作

```python
person = {"name": "Bob", "age": 25}

person["height"] = 173  # 添加
person["age"] = 26      # 修改

print(person.keys())    # 所有键
print(person.values())  # 所有值
print(person.items())   # 所有键值对
```

---

### 4. 遍历字典

```python
for key, value in person.items():
    print(f"{key}: {value}")
```

注意：循环体必须缩进。

---

## 八、集合 `set`

集合的特点：

- 元素无序
- 元素不重复
- 常用于去重

```python
unique_numbers = {1, 2, 3, 2}
print(unique_numbers)  # {1, 2, 3}
```

---

### 1. 去重

```python
nums = [1, 2, 2, 3, 3, 3]
print(set(nums))  # {1, 2, 3}
```

---

### 2. 成员判断

```python
s = {1, 2, 3}
print(2 in s)  # True
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
elif age > 13:
    print("Teenager")
else:
    print("Child")
```

结构说明：

- `if`：如果条件成立
- `elif`：否则如果
- `else`：否则

Python 用**缩进**表示代码块，不使用大括号。

---

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

```python
0
1
2
3
4
```

`range(5)` 表示从 `0` 到 `4`。

还可以指定开始和结束：

```python
for i in range(1, 6):
    print(i)
```

输出为 `1` 到 `5`。

---

### 3. `while` 循环

`while` 循环适合“只要条件成立就一直重复”的场景。

```python
count = 0

while count < 5:
    print(count)
    count += 1
```

---

### 4. `break` 和 `continue`

#### `break`：直接结束整个循环

```python
for i in range(10):
    if i == 5:
        break
    print(i)
```

输出：

```python
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

```python
0
1
3
4
```

---

## 十、函数

函数的本质是：**把某段功能封装起来，方便反复调用。**

---

### 1. 为什么要用函数

如果一段代码会反复使用，就不要一遍遍重写，而应该封装成函数。函数可以让代码更清晰，也更容易维护。

---

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
abs(x)        # 绝对值
chr(x)        # 将 ASCII/Unicode 编码转为字符
ord(x)        # 返回字符对应编码
round(x, n)   # 四舍五入到小数点后 n 位
max(lst)      # 最大值
min(lst)      # 最小值
open(file)    # 打开文件
```

---

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

---

### 4. 函数的核心概念

#### （1）参数

参数是函数接收的数据。

```python
def add(a, b):
    return a + b
```

`a` 和 `b` 就是参数。

#### （2）返回值

返回值是函数执行后交回来的结果。

```python
result = add(3, 5)
print(result)  # 8
```

#### （3）默认参数

```python
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"
```

如果调用时不传 `greeting`，函数会使用默认值 `"Hello"`。

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

---

### 2. 读文件

```python
with open("diary.txt", "r", encoding="utf-8") as f:
    content = f.read()
    print(content)
```

说明：

- `"r"`：读取模式
- `f.read()`：一次性读取全部内容

---

### 3. 为什么用 `with open(...)`

`with open(...)` 可以在文件使用完后自动关闭文件，比手动打开和关闭更安全，也更规范。

---

### 4. 其他常见模式

- `"a"`：追加写入
- `"rb"`：按二进制读取
- `"wb"`：按二进制写入

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

---

### 2. 输入异常

```python
try:
    age = int(input("Age: "))
    print(age)
except ValueError:
    print("Invalid value")
```

如果用户输入的是 `"abc"`，就会触发 `ValueError`。

---

### 3. 异常处理的意义

异常处理不是为了“掩盖错误”，而是为了：

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

---

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

---

### 3. 包 `package`

包可以理解成“存放多个模块的文件夹”。

通常包中会有一个 `__init__.py` 文件。旧版本 Python 对它要求更严格；新版本即使没有这个文件，也常能识别包。学习阶段先按“包里通常有 `__init__.py`”来理解最稳妥。

导入方式：

```python
import package.module
```

或者：

```python
from package.module import func
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
```

---

## 十五、面向对象编程 OOP

面向对象是一种组织代码的思想。它强调把现实中的事物抽象成“对象”，再用对象保存数据和执行行为。

---

### 1. 类和对象

- **类（class）**：模板
- **对象**：根据模板创建出来的具体实例

例如：“人”是类，“张三”是对象。

---

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

---

### 3. `self` 是什么

`self` 代表“当前对象本身”。

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

---

### 4. 构造函数 `__init__`

构造函数用于在对象创建时初始化属性。

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def move(self):
        print("move")

    def draw(self):
        print("draw")

point = Point(10, 20)

print(point.x)
print(point.y)
```

这里：

- `self.x = x`：把传入的参数保存到对象属性中
- 对象一创建，就会自动执行 `__init__`

---

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

---

### 6. 继承

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

---

### 7. `pass` 的作用

`pass` 表示“先占一个位置，什么都不做”。

当语法上必须写点东西，但暂时没有内容时，就可以写 `pass`。

---

## 十六、容易混淆的知识点

### 1. 列表和元组的区别

- 列表 `list`：可修改，用 `[]`
- 元组 `tuple`：不可修改，用 `()`

---

### 2. 字典和集合的区别

- 字典 `dict`：键值对，形如 `{"name": "Tom"}`
- 集合 `set`：只有值，且不重复，形如 `{1, 2, 3}`

---

### 3. `=` 和 `==` 的区别

- `=`：赋值
- `==`：比较是否相等

例如：

```python
x = 5
print(x == 5)  # True
```

---

### 4. `input()` 的结果永远是字符串

```python
num = input("请输入数字：")
print(type(num))  # str
```

如果要做数值运算，必须先转换类型：

```python
num = int(input("请输入数字："))
```

---

## 十七、`openpyxl` 项目实践

### 1. `openpyxl` 基础知识

`openpyxl` 是 Python 中用来读写 Excel `.xlsx` 文件的第三方库。它适合做自动化办公，例如批量读取表格、修改单元格、写入计算结果、设置格式、生成简单图表等。

安装：

```bash
pip install openpyxl
```

导入时常见写法：

```python
import openpyxl as xl
```

---

### 2. 工作簿、工作表和单元格

理解 `openpyxl` 时，可以先记住三个核心对象：

- **工作簿 Workbook**：一个 Excel 文件，也就是整个 `.xlsx` 文件
- **工作表 Worksheet**：Excel 文件中的一个表，例如 `Sheet1`
- **单元格 Cell**：表格里的具体格子，例如 `A1`、`B2`

```python
import openpyxl as xl

wb = xl.load_workbook("transactions.xlsx")  # 打开工作簿
sheet = wb["Sheet1"]                        # 选择工作表

print(sheet["A1"].value)                    # 读取 A1 单元格
print(sheet.cell(row=2, column=3).value)     # 读取第 2 行第 3 列
```

---

### 3. 行和列的编号

在 `openpyxl` 中，行号和列号都是从 **1** 开始的，不是从 0 开始。

例如：

- 第 1 行：Excel 中的第一行
- 第 1 列：A 列
- 第 2 列：B 列
- 第 3 列：C 列
- 第 4 列：D 列

所以：

```python
sheet.cell(row, 3)
```

表示读取当前行的第 3 列，也就是 C 列。

---

### 4. 读取、写入和保存

读取单元格用 `.value`：

```python
price = sheet.cell(row=2, column=3).value
```

写入单元格也是修改 `.value`：

```python
sheet.cell(row=2, column=4).value = price * 0.9
```

修改 Excel 后一定要保存，否则文件不会真正变化：

```python
wb.save("transactions_updated.xlsx")
```

---

### 5. 常用属性

```python
print(wb.sheetnames)       # 查看所有工作表名称
print(sheet.max_row)       # 表格中有多少行
print(sheet.max_column)    # 表格中有多少列
```

其中 `sheet.max_row` 很常用，因为遍历 Excel 数据时，经常需要知道最后一行在哪里。

---

### 6. 项目目标

这个 Excel 小项目的功能是：

1. 打开 Excel 文件
2. 读取表格中第三列的价格
3. 计算打 9 折后的价格
4. 把结果写入第四列
5. 根据第四列数据生成柱状图
6. 保存文件

---

### 7. 项目代码整理版

```python
import openpyxl as xl
from openpyxl.chart import BarChart, Reference


def process_workbook(filename):
    wb = xl.load_workbook(filename)
    sheet = wb["Sheet1"]

    # 计算折后价格并写入第 4 列
    for row in range(2, sheet.max_row + 1):
        cell = sheet.cell(row, 3)
        corrected_price = cell.value * 0.9
        sheet.cell(row, 4).value = corrected_price

    # 选择第 4 列数据作为图表数据源
    values = Reference(
        sheet,
        min_row=2,
        max_row=sheet.max_row,
        min_col=4,
        max_col=4,
    )

    chart = BarChart()
    chart.add_data(values)
    sheet.add_chart(chart, "E2")

    wb.save(filename)


process_workbook("transactions.xlsx")
```

---

### 8. 项目注意点

#### （1）函数名拼写

函数名建议写成：

```python
def process_workbook(filename):
    ...
```

`process` 表示“处理”，`workbook` 表示“工作簿”。

#### （2）覆盖原文件

```python
wb.save(filename)
```

这会直接覆盖原 Excel 文件。如果不想覆盖，建议另存为：

```python
wb.save("transactions_updated.xlsx")
```

#### （3）为什么从第 2 行开始

通常第 1 行是表头，所以数据从第 2 行开始。

#### （4）为什么读第 3 列

假设原始价格在 C 列，所以读取第 3 列：

```python
cell = sheet.cell(row, 3)
```

#### （5）为什么写第 4 列

把打折后的价格写到 D 列：

```python
sheet.cell(row, 4).value = corrected_price
```

---

### 9. 这个项目体现的知识

这个项目综合用了很多基础知识：

- 函数定义
- 循环
- 变量
- 模块导入
- 第三方库使用
- 文件处理
- 数据写入
- 图表生成

它是一个很典型的“从基础语法走向实际应用”的练习。

---

## 十八、学习 Python 时的规范建议

### 1. 注意缩进

Python 用缩进区分代码块，缩进错了程序就可能报错。

```python
if age >= 18:
    print("Adult")
```

这里 `print` 前面必须缩进。

---

### 2. 变量名不要拼错

例如：

- `course` 不要写成 `couerse`
- `engineer` 不要写成 `enginner`
- `process_workbook` 不要写成 `proceses_workbook`

小拼写错误非常容易导致程序报错。

---

### 3. 字典键名要加引号

字典中如果写的是字符串键，必须加引号：

```python
person["height"] = 173
```

不能写成：

```python
person[height] = 173
```

除非 `height` 本身是一个已经定义好的变量。

---

### 4. 代码最好加空格，保持可读性

```python
x = 3
x += 3
print(x)
```

清晰的排版能减少阅读和调试成本。

---

## 十九、复习总框架

学 Python 时，可以在脑子里建立这样一张结构图：

### 第一层：数据

- 变量
- 字符串
- 数字
- 布尔值

### 第二层：容器

- 列表
- 元组
- 字典
- 集合

### 第三层：流程

- `if`
- `for`
- `while`
- `break` / `continue`

### 第四层：封装

- 函数
- 模块
- 包

### 第五层：工程能力

- 文件操作
- 异常处理
- 面向对象
- 第三方库

这样复习时，知识点会更容易归位。

---

## 二十、精炼记忆结论

### 1. Python 基本特点

- 语法简洁
- 动态类型
- 解释执行

### 2. 四种基本数据类型

- `str`
- `int`
- `float`
- `bool`

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

### 6. 面向对象三大基础

- 类
- 对象
- 继承

### 7. 文件与异常

- 文件：实现数据持久化
- 异常：防止程序直接崩溃
