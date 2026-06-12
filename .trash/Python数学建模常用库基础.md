# Python 数学建模常用库基础

## 一、这份笔记解决什么问题

数学建模中的 Python 不只是写基础语法，更重要的是能完成一条完整的数据分析与建模链路：

1. 用 `NumPy` 处理数组、矩阵和数值计算。
2. 用 `Pandas` 读取、清洗、筛选、统计和整理表格数据。
3. 用 `Matplotlib` 把数据关系画出来，辅助发现规律和展示结果。
4. 用 `SciPy` 处理优化、拟合、积分、插值、统计检验等数学问题。
5. 必要时用 `scikit-learn` 做回归、分类、聚类、降维和模型评估。

学习顺序建议：

```text
NumPy 数组计算
    -> Pandas 表格处理
    -> Matplotlib 可视化
    -> SciPy 数学建模工具
    -> scikit-learn 机器学习建模
```

---

## 二、环境准备与常用导入

### 1. 安装常用库

```bash
pip install numpy pandas matplotlib scipy scikit-learn openpyxl
```

如果使用 Anaconda，一般已经自带大部分库。

### 2. 建模常用导入模板

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy import integrate, interpolate, optimize, stats
```

常见别名：

| 库 | 常用别名 | 作用 |
|---|---|---|
| `numpy` | `np` | 数组、矩阵、数值计算 |
| `pandas` | `pd` | 表格数据处理 |
| `matplotlib.pyplot` | `plt` | 绘图 |
| `scipy` | 无固定统一别名 | 优化、统计、插值、积分等 |

### 3. 中文显示设置

如果图中需要显示中文，可以先加：

```python
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False
```

其中：

- `SimHei`：黑体，用于显示中文。
- `axes.unicode_minus = False`：防止负号显示异常。

---

## 三、数学建模中的 Python 工作流

一份建模代码通常可以按下面结构组织：

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# 1. 读取数据
df = pd.read_excel("data.xlsx")

# 2. 初步查看
print(df.head())
print(df.info())
print(df.describe())

# 3. 数据清洗
df = df.dropna()

# 4. 特征处理
x = df["x"].to_numpy()
y = df["y"].to_numpy()

# 5. 建模计算
coef = np.polyfit(x, y, deg=1)

# 6. 可视化
plt.scatter(x, y)
plt.plot(x, np.polyval(coef, x))
plt.show()

# 7. 输出结果
df.to_excel("result.xlsx", index=False)
```

核心思路：

```text
读取数据 -> 清洗数据 -> 描述统计 -> 可视化 -> 建模 -> 评估 -> 输出结果
```

---

## 四、NumPy：数组、矩阵与数值计算

### 1. NumPy 的核心对象：`ndarray`

NumPy 的核心是数组 `ndarray`。它比普通 Python 列表更适合数值计算。

```python
import numpy as np

a = np.array([1, 2, 3, 4])
print(a)
print(type(a))
```

输出：

```text
[1 2 3 4]
<class 'numpy.ndarray'>
```

列表和 NumPy 数组的区别：

| 对象 | 特点 |
|---|---|
| Python 列表 | 通用容器，可以混放不同类型，数值计算慢 |
| NumPy 数组 | 专门做数值计算，通常元素类型统一，计算快 |

### 2. 创建数组

```python
import numpy as np

a = np.array([1, 2, 3])
b = np.zeros(5)
c = np.ones((2, 3))
d = np.arange(0, 10, 2)
e = np.linspace(0, 1, 5)
```

含义：

| 写法 | 结果 |
|---|---|
| `np.array([1, 2, 3])` | 由列表创建数组 |
| `np.zeros(5)` | 5 个 0 |
| `np.ones((2, 3))` | 2 行 3 列的全 1 数组 |
| `np.arange(0, 10, 2)` | 从 0 到 10，步长为 2，不包含 10 |
| `np.linspace(0, 1, 5)` | 从 0 到 1 等间隔取 5 个点 |

`arange` 和 `linspace` 的区别：

- `np.arange(start, stop, step)`：关注步长。
- `np.linspace(start, stop, num)`：关注取多少个点，通常包含终点。

### 3. 数组维度和形状

```python
a = np.array([[1, 2, 3], [4, 5, 6]])

print(a.ndim)   # 维度数
print(a.shape)  # 形状
print(a.size)   # 元素总数
print(a.dtype)  # 元素类型
```

输出：

```text
2
(2, 3)
6
int64
```

在数学建模中，`shape` 非常重要。很多报错都来自维度不匹配。

### 4. 改变形状

```python
a = np.arange(12)
b = a.reshape(3, 4)

print(b)
```

输出：

```text
[[ 0  1  2  3]
 [ 4  5  6  7]
 [ 8  9 10 11]]
```

注意：`reshape` 前后元素总数必须一致。

### 5. 索引和切片

```python
a = np.array([10, 20, 30, 40, 50])

print(a[0])     # 10
print(a[-1])    # 50
print(a[1:4])   # [20 30 40]
```

二维数组：

```python
m = np.array([[1, 2, 3], [4, 5, 6]])

print(m[0, 0])   # 第 1 行第 1 列
print(m[1, 2])   # 第 2 行第 3 列
print(m[:, 0])   # 所有行，第 1 列
print(m[0, :])   # 第 1 行，所有列
```

### 6. 条件筛选

```python
a = np.array([1, 5, 8, 10, 3])

print(a > 5)
print(a[a > 5])
```

输出：

```text
[False False  True  True False]
[ 8 10]
```

条件筛选常用于剔除异常值：

```python
data = np.array([10, 12, 13, 1000, 11])
normal_data = data[data < 100]
```

### 7. 向量化计算

NumPy 的重要思想是：尽量对整个数组计算，而不是手写循环。

```python
a = np.array([1, 2, 3])

print(a + 10)
print(a * 2)
print(a ** 2)
```

输出：

```text
[11 12 13]
[2 4 6]
[1 4 9]
```

这叫向量化。建模时应优先使用向量化代码，速度更快，也更简洁。

### 8. 广播机制

广播是指 NumPy 在形状兼容时自动扩展数组进行计算。

```python
a = np.array([[1, 2, 3], [4, 5, 6]])
b = np.array([10, 20, 30])

print(a + b)
```

输出：

```text
[[11 22 33]
 [14 25 36]]
```

这里 `b` 被自动扩展到每一行。

易错点：广播不是随便扩展，维度必须兼容。遇到广播错误时先看 `shape`。

```python
print(a.shape)
print(b.shape)
```

### 9. 常用统计函数

```python
data = np.array([1, 2, 3, 4, 5])

print(np.mean(data))    # 平均值
print(np.median(data))  # 中位数
print(np.std(data))     # 标准差
print(np.var(data))     # 方差
print(np.max(data))     # 最大值
print(np.min(data))     # 最小值
print(np.sum(data))     # 求和
```

二维数组按方向统计：

```python
m = np.array([[1, 2, 3], [4, 5, 6]])

print(np.sum(m, axis=0))  # 按列求和
print(np.sum(m, axis=1))  # 按行求和
```

记忆：

- `axis=0`：沿着行方向压缩，得到每一列的结果。
- `axis=1`：沿着列方向压缩，得到每一行的结果。

### 10. 矩阵和线性代数

数学建模中常见矩阵运算包括矩阵乘法、求逆、解线性方程组、特征值等。

```python
A = np.array([[1, 2], [3, 4]])
B = np.array([[2, 0], [1, 2]])

print(A @ B)         # 矩阵乘法
print(A.T)           # 转置
print(np.linalg.det(A))  # 行列式
print(np.linalg.inv(A))  # 逆矩阵
```

解线性方程组：

$$
A x = b
$$

```python
A = np.array([[2, 1], [1, 3]])
b = np.array([5, 6])

x = np.linalg.solve(A, b)
print(x)
```

不要用 `np.linalg.inv(A) @ b` 作为首选。更推荐 `np.linalg.solve(A, b)`，数值上通常更稳定。

### 11. 随机数

```python
rng = np.random.default_rng(seed=42)

print(rng.random(5))              # 0 到 1 的随机数
print(rng.integers(1, 10, size=5)) # 1 到 9 的随机整数
print(rng.normal(0, 1, size=5))    # 标准正态分布
```

设置 `seed` 的意义：让随机结果可以复现。建模论文或报告中，如果涉及随机模拟，应说明随机种子。

### 12. NumPy 高频易错点

| 易错点 | 正确理解 |
|---|---|
| `*` | 数组对应元素相乘，不是矩阵乘法 |
| `@` | 矩阵乘法 |
| `shape` 不匹配 | 先打印 `.shape` 检查维度 |
| `axis=0` / `axis=1` | `axis=0` 常得到列统计，`axis=1` 常得到行统计 |
| 列向量和一维数组 | `(n,)` 和 `(n, 1)` 不一样 |

---

## 五、Pandas：表格数据处理

### 1. Pandas 的核心对象

Pandas 主要有两个核心对象：

| 对象 | 含义 |
|---|---|
| `Series` | 一列数据 |
| `DataFrame` | 二维表格 |

```python
import pandas as pd

s = pd.Series([10, 20, 30])
df = pd.DataFrame({
    "name": ["A", "B", "C"],
    "score": [85, 90, 78],
})
```

### 2. 读取数据

```python
df = pd.read_csv("data.csv")
df = pd.read_excel("data.xlsx")
```

常用参数：

```python
df = pd.read_csv("data.csv", encoding="utf-8")
df = pd.read_excel("data.xlsx", sheet_name="Sheet1")
```

如果读取中文 CSV 乱码，可以尝试：

```python
df = pd.read_csv("data.csv", encoding="utf-8-sig")
df = pd.read_csv("data.csv", encoding="gbk")
```

优先试 `utf-8-sig`；如果数据来自较旧的中文 Windows 软件，再尝试 `gbk`。

### 3. 初步查看数据

```python
print(df.head())       # 前 5 行
print(df.tail())       # 后 5 行
print(df.shape)        # 行数和列数
print(df.columns)      # 列名
print(df.info())       # 数据类型和缺失情况
print(df.describe())   # 数值列统计摘要
```

拿到新数据后，先不要急着建模。先看：

1. 有多少行、多少列。
2. 每列代表什么含义。
3. 是否有缺失值。
4. 数值列的范围是否异常。
5. 分类变量有哪些类别。

### 4. 选择列和行

选择一列：

```python
score = df["score"]
```

选择多列：

```python
sub = df[["name", "score"]]
```

按位置选择：

```python
print(df.iloc[0, 0])     # 第 1 行第 1 列
print(df.iloc[0:5, :])   # 前 5 行
```

按标签选择：

```python
print(df.loc[0, "score"])
```

### 5. 条件筛选

```python
high = df[df["score"] >= 90]
```

多个条件要用 `&` 或 `|`，每个条件要加括号：

```python
result = df[(df["score"] >= 80) & (df["age"] < 20)]
```

不能写成：

```python
df[df["score"] >= 80 and df["age"] < 20]
```

因为 Pandas 的条件筛选是对一整列逐项判断，不能直接用 Python 的 `and`。

### 6. 缺失值处理

查看缺失值：

```python
print(df.isna().sum())
```

删除缺失值：

```python
df_clean = df.dropna()
```

`dropna()` 会删除任何含缺失值的行。比赛数据中不要机械删除，先判断缺失比例和缺失原因。

填充缺失值：

```python
df["score"] = df["score"].fillna(df["score"].mean())
```

常见策略：

| 场景 | 常用处理 |
|---|---|
| 缺失很少 | 删除对应行 |
| 数值列缺失 | 均值、中位数或模型填补 |
| 分类列缺失 | 众数或单独记为“未知” |
| 缺失本身有意义 | 新增“是否缺失”特征 |

### 7. 新增列

```python
df["total"] = df["math"] + df["english"]
df["passed"] = df["total"] >= 120
```

分段赋值：

```python
df["level"] = "normal"
df.loc[df["score"] >= 90, "level"] = "excellent"
df.loc[df["score"] < 60, "level"] = "failed"
```

### 8. 排序

```python
df_sorted = df.sort_values("score", ascending=False)
```

按多列排序：

```python
df_sorted = df.sort_values(["class", "score"], ascending=[True, False])
```

### 9. 分组统计

```python
result = df.groupby("class")["score"].mean()
print(result)
```

多个统计量：

```python
result = df.groupby("class")["score"].agg(["mean", "max", "min", "count"])
```

多个字段：

```python
result = df.groupby("class")[["math", "english"]].mean()
```

分组统计常用于：

- 不同地区的平均指标。
- 不同年份的总量变化。
- 不同类别的占比和排名。

### 10. 合并表格

```python
merged = pd.merge(df1, df2, on="id", how="left")
```

常见 `how`：

| 参数 | 含义 |
|---|---|
| `inner` | 只保留两边都有的 |
| `left` | 保留左表全部 |
| `right` | 保留右表全部 |
| `outer` | 保留两边全部 |

数学建模中经常需要把多个数据源按地区、年份、编号合并。

### 11. 数据透视表

```python
pivot = pd.pivot_table(
    df,
    values="score",
    index="class",
    columns="gender",
    aggfunc="mean",
)
```

数据透视表适合做交叉统计，例如：

- 不同地区、不同年份的平均收入。
- 不同类别、不同等级的数量。
- 不同方案、不同指标的评分。

### 12. 时间数据

```python
df["date"] = pd.to_datetime(df["date"])
df["year"] = df["date"].dt.year
df["month"] = df["date"].dt.month
```

按月份统计：

```python
monthly = df.groupby("month")["sales"].sum()
```

如果日期作为索引：

```python
df = df.set_index("date")
monthly = df.resample("ME")["sales"].sum()
```

### 13. 导出结果

```python
df.to_csv("result.csv", index=False, encoding="utf-8-sig")
df.to_excel("result.xlsx", index=False)
```

如果要给 Excel 用户打开中文 CSV，`utf-8-sig` 往往比 `utf-8` 更稳。

### 14. Pandas 高频易错点

| 易错点 | 正确做法 |
|---|---|
| 条件筛选用 `and` | 用 `&`，并给每个条件加括号 |
| 修改筛选后的临时表 | 优先用 `.loc[row_condition, col] = value` |
| 忘记 `index=False` | 导出 Excel/CSV 时常加 `index=False` |
| 数字被读成字符串 | 用 `pd.to_numeric()` 转换 |
| 日期是字符串 | 用 `pd.to_datetime()` 转换 |
| 缺失值不处理就建模 | 先 `isna().sum()` 检查 |

---

## 六、Matplotlib：画图与结果展示

### 1. 基本绘图结构

```python
import matplotlib.pyplot as plt

plt.figure(figsize=(6, 4))
plt.plot([1, 2, 3], [2, 4, 6])
plt.xlabel("x")
plt.ylabel("y")
plt.title("Line Plot")
plt.grid(True)
plt.show()
```

常见结构：

```text
创建画布 -> 画图 -> 设置标题/坐标轴/图例 -> 显示或保存
```

### 2. 折线图

折线图适合展示随时间或序号变化的趋势。

```python
x = np.arange(1, 6)
y = np.array([2, 3, 5, 4, 7])

plt.plot(x, y, marker="o")
plt.xlabel("时间")
plt.ylabel("指标")
plt.title("指标变化趋势")
plt.grid(True)
plt.show()
```

### 3. 散点图

散点图适合观察两个变量之间是否相关。

```python
x = np.array([1, 2, 3, 4, 5])
y = np.array([2, 4, 5, 4, 7])

plt.scatter(x, y)
plt.xlabel("x")
plt.ylabel("y")
plt.title("散点图")
plt.show()
```

### 4. 柱状图

柱状图适合比较不同类别的数值。

```python
names = ["A", "B", "C"]
values = [10, 15, 8]

plt.bar(names, values)
plt.xlabel("类别")
plt.ylabel("数值")
plt.title("类别对比")
plt.show()
```

### 5. 直方图

直方图适合观察数据分布。

```python
data = np.random.default_rng(42).normal(0, 1, 1000)

plt.hist(data, bins=30)
plt.xlabel("取值")
plt.ylabel("频数")
plt.title("数据分布")
plt.show()
```

### 6. 箱线图

箱线图适合观察中位数、离散程度和异常值。

```python
rng = np.random.default_rng(42)
data = [rng.normal(0, 1, 100), rng.normal(1, 1.5, 100)]

plt.boxplot(data, tick_labels=["A", "B"])
plt.ylabel("数值")
plt.title("箱线图")
plt.show()
```

旧教程中可能使用 `labels` 参数；新版本 Matplotlib 更推荐使用 `tick_labels`。

### 7. 热力图

热力图常用于展示相关系数矩阵或二维强度分布。

```python
matrix = np.array([[1.0, 0.8, 0.3], [0.8, 1.0, 0.5], [0.3, 0.5, 1.0]])

plt.imshow(matrix, cmap="viridis")
plt.colorbar()
plt.title("相关系数热力图")
plt.show()
```

### 8. 多子图

```python
fig, axes = plt.subplots(1, 2, figsize=(10, 4))

axes[0].plot([1, 2, 3], [1, 4, 9])
axes[0].set_title("折线图")

axes[1].bar(["A", "B", "C"], [3, 5, 2])
axes[1].set_title("柱状图")

plt.tight_layout()
plt.show()
```

`fig, axes = plt.subplots()` 是更规范的写法，适合复杂图。

### 9. 保存图片

```python
plt.savefig("figure.png", dpi=300, bbox_inches="tight")
```

常用参数：

| 参数 | 作用 |
|---|---|
| `dpi=300` | 提高图片清晰度 |
| `bbox_inches="tight"` | 减少边缘空白 |

建模论文中通常需要保存高分辨率图片。

### 10. 图形选择

| 目的 | 推荐图形 |
|---|---|
| 看趋势 | 折线图 |
| 看相关关系 | 散点图 |
| 比较类别 | 柱状图 |
| 看分布 | 直方图、箱线图 |
| 看矩阵关系 | 热力图 |
| 看模型拟合效果 | 散点图 + 拟合曲线 |

---

## 七、SciPy：优化、拟合、统计和数学工具

### 1. SciPy 适合做什么

`SciPy` 是建立在 `NumPy` 之上的科学计算库。数学建模中常用它处理：

- 方程求根
- 函数最小化
- 曲线拟合
- 数值积分
- 插值
- 统计分布和检验
- 距离计算

### 2. 方程求根

求解：

$$
x^2 - 2 = 0
$$

```python
from scipy import optimize


def f(x):
    return x ** 2 - 2


root = optimize.root_scalar(f, bracket=[0, 2])
print(root.root)
```

`bracket=[0, 2]` 表示在区间 $[0,2]$ 中寻找根。

### 3. 函数最小化

求函数：

$$
f(x) = (x - 3)^2 + 2
$$

的最小值。

```python
from scipy import optimize


def f(x):
    return (x - 3) ** 2 + 2


result = optimize.minimize_scalar(f)
print(result.x)
print(result.fun)
```

输出中的：

- `result.x`：取得最小值时的 $x$。
- `result.fun`：最小函数值。

### 4. 多变量优化

```python
from scipy import optimize


def f(v):
    x, y = v
    return (x - 1) ** 2 + (y + 2) ** 2


result = optimize.minimize(f, x0=[0, 0])
print(result.x)
print(result.fun)
```

其中 `x0` 是初始猜测值。多变量优化常用于：

- 参数估计
- 最小误差拟合
- 目标函数最优化
- 带约束优化问题

### 5. 曲线拟合

假设模型为：

$$
y = a e^{b x}
$$

```python
import numpy as np
from scipy import optimize


def model(x, a, b):
    return a * np.exp(b * x)


x = np.array([1, 2, 3, 4, 5])
y = np.array([2.7, 7.4, 20.1, 54.6, 148.4])

params, covariance = optimize.curve_fit(model, x, y, p0=[1, 1])

print(params)
```

其中：

- `model` 是假设的函数形式。
- `params` 是拟合得到的参数。
- `p0` 是参数初始猜测。

### 6. 数值积分

计算：

$$
\int_0^1 x^2\,dx
$$

```python
from scipy import integrate


def f(x):
    return x ** 2


value, error = integrate.quad(f, 0, 1)
print(value)
print(error)
```

`quad` 返回两个值：

- 积分近似值。
- 误差估计。

### 7. 插值

插值用于根据已知离散点估计中间点。

```python
import numpy as np
from scipy.interpolate import CubicSpline

x = np.array([0, 1, 2, 3])
y = np.array([0, 1, 4, 9])

spline = CubicSpline(x, y)
print(spline(1.5))
```

常见选择：

| 方法 | 适合场景 |
|---|---|
| `np.interp` | 一维线性插值，简单稳定 |
| `CubicSpline` | 三次样条插值，曲线更平滑 |
| `PchipInterpolator` | 保形插值，减少过冲 |

`interp1d` 还能在旧代码中见到，但 SciPy 官方已把它标为 legacy；新笔记和新项目优先用更明确的插值类或 `np.interp`。

### 8. 统计分布

```python
from scipy import stats

print(stats.norm.cdf(1.96))      # 标准正态分布累计概率
print(stats.norm.ppf(0.975))     # 分位数
print(stats.t.mean(df=10))       # t 分布均值
```

常见用途：

- 查概率。
- 求分位点。
- 做假设检验。
- 拟合概率分布。

### 9. SciPy 高频易错点

| 易错点 | 说明 |
|---|---|
| 优化问题没有初值 | 多变量优化通常需要合理初值 |
| 曲线拟合函数参数顺序错 | `model(x, a, b, ...)` 中自变量通常放第一个 |
| 忘记检查拟合效果 | 参数拟合后要画图或算误差 |
| 根区间不含变号点 | `root_scalar` 的 `bracket` 要包含根 |

---

## 八、scikit-learn：建模与评估入门

### 1. 它适合做什么

`scikit-learn` 常用于机器学习建模：

- 回归：预测连续值。
- 分类：预测类别。
- 聚类：无监督分组。
- 降维：压缩特征、可视化高维数据。
- 模型评估：训练集、测试集、误差指标。

### 2. 建模基本流程

```python
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score


X = df[["feature1", "feature2"]]
y = df["target"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

model = LinearRegression()
model.fit(X_train_scaled, y_train)

y_pred = model.predict(X_test_scaled)

print(mean_squared_error(y_test, y_pred))
print(r2_score(y_test, y_pred))
```

关键原则：

- `fit_transform` 只用于训练集。
- 测试集只能用 `transform`。
- 不能先对全体数据标准化再划分训练集和测试集，否则会造成数据泄漏。
- 线性模型、距离模型、聚类模型常需要标准化；树模型通常不依赖特征尺度。

### 3. 常见模型

| 任务 | 常用模型 |
|---|---|
| 线性回归 | `LinearRegression` |
| 岭回归 | `Ridge` |
| Lasso 回归 | `Lasso` |
| 逻辑回归 | `LogisticRegression` |
| 决策树 | `DecisionTreeClassifier` / `DecisionTreeRegressor` |
| 随机森林 | `RandomForestClassifier` / `RandomForestRegressor` |
| K 均值聚类 | `KMeans` |
| 主成分分析 | `PCA` |

### 4. 回归评估指标

| 指标 | 含义 |
|---|---|
| MSE | 均方误差，越小越好 |
| RMSE | 均方根误差，和原数据单位一致 |
| MAE | 平均绝对误差 |
| $R^2$ | 拟合优度，越接近 1 越好 |

RMSE 计算：

```python
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
```

### 5. 分类评估指标

```python
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

print(accuracy_score(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))
print(classification_report(y_test, y_pred))
```

常见指标：

| 指标 | 含义 |
|---|---|
| accuracy | 准确率 |
| precision | 查准率 |
| recall | 召回率 |
| F1-score | precision 和 recall 的综合 |

---

## 九、数学建模常用小模板

### 1. 读取、检查、清洗模板

```python
import pandas as pd

df = pd.read_excel("data.xlsx")

print(df.head())
print(df.shape)
print(df.info())
print(df.describe())
print(df.isna().sum())

df = df.dropna()
```

### 2. 异常值处理模板

使用四分位距 IQR：

```python
q1 = df["value"].quantile(0.25)
q3 = df["value"].quantile(0.75)
iqr = q3 - q1

lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

df_clean = df[(df["value"] >= lower) & (df["value"] <= upper)]
```

### 3. 标准化模板

手写标准化：

```python
x = df["value"]
z = (x - x.mean()) / x.std()
```

使用 `scikit-learn`：

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
```

标准化常用于：

- 多指标评价。
- 聚类。
- 距离计算。
- 梯度类模型。

### 4. 相关性分析模板

```python
corr = df.corr(numeric_only=True)
print(corr)

plt.imshow(corr, cmap="coolwarm")
plt.colorbar()
plt.xticks(range(len(corr.columns)), corr.columns, rotation=45)
plt.yticks(range(len(corr.columns)), corr.columns)
plt.title("相关系数矩阵")
plt.tight_layout()
plt.show()
```

注意：相关不等于因果。相关性只能说明变量同步变化程度，不能直接证明一个变量导致另一个变量。

### 5. 线性拟合模板

```python
import numpy as np
import matplotlib.pyplot as plt

x = df["x"].to_numpy()
y = df["y"].to_numpy()

k, b = np.polyfit(x, y, deg=1)
y_fit = k * x + b

plt.scatter(x, y, label="原始数据")
plt.plot(x, y_fit, color="red", label=f"y={k:.2f}x+{b:.2f}")
plt.legend()
plt.grid(True)
plt.show()
```

### 6. 多项式拟合模板

```python
coef = np.polyfit(x, y, deg=2)
y_fit = np.polyval(coef, x)

plt.scatter(x, y)
plt.plot(x, y_fit, color="red")
plt.show()
```

注意：多项式次数越高，不一定越好。次数过高容易过拟合。

### 7. 最小二乘曲线拟合模板

```python
import numpy as np
from scipy.optimize import curve_fit


def model(x, a, b, c):
    return a * np.exp(b * x) + c


params, _ = curve_fit(model, x, y, p0=[1, 0.1, 0])
y_fit = model(x, *params)
```

### 8. 排名与综合评价模板

如果所有指标都是“越大越好”，可以先标准化再加权求和：

```python
cols = ["指标1", "指标2", "指标3"]
weights = np.array([0.4, 0.3, 0.3])

X = df[cols]
denom = X.max() - X.min()
X_norm = (X - X.min()) / denom.replace(0, 1)

df["score"] = X_norm.to_numpy() @ weights
df = df.sort_values("score", ascending=False)
```

如果某一列最大值等于最小值，它不能提供区分度；上面用 `replace(0, 1)` 避免除以 0。

如果某个指标是“越小越好”，应先正向化：

```python
X_norm["成本"] = (X["成本"].max() - X["成本"]) / (X["成本"].max() - X["成本"].min())
```

### 9. 距离计算模板

```python
from scipy.spatial.distance import cdist

A = np.array([[0, 0], [1, 1]])
B = np.array([[2, 2], [3, 3]])

dist = cdist(A, B, metric="euclidean")
print(dist)
```

距离常用于：

- 聚类。
- 选址问题。
- 路径问题。
- 相似度分析。

---

## 十、完整小例子：读取数据、拟合、画图、输出

下面用一组模拟数据演示完整流程。

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# 1. 构造模拟数据
rng = np.random.default_rng(42)
x = np.linspace(0, 10, 50)
y = 2.5 * x + 3 + rng.normal(0, 2, size=x.size)

df = pd.DataFrame({
    "x": x,
    "y": y,
})

# 2. 查看数据
print(df.head())
print(df.describe())

# 3. 线性拟合
k, b = np.polyfit(df["x"], df["y"], deg=1)
df["y_fit"] = k * df["x"] + b

# 4. 计算误差
df["error"] = df["y"] - df["y_fit"]
mse = np.mean(df["error"] ** 2)

print(f"k = {k:.4f}")
print(f"b = {b:.4f}")
print(f"MSE = {mse:.4f}")

# 5. 可视化
plt.figure(figsize=(6, 4))
plt.scatter(df["x"], df["y"], label="原始数据")
plt.plot(df["x"], df["y_fit"], color="red", label="拟合直线")
plt.xlabel("x")
plt.ylabel("y")
plt.title("线性拟合示例")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# 6. 保存结果
df.to_excel("fit_result.xlsx", index=False)
```

这个例子对应的建模思路：

1. 先把数据整理成表格。
2. 判断变量关系，选择线性模型。
3. 用最小二乘思想拟合参数。
4. 用误差指标判断拟合效果。
5. 用图展示模型与原数据的关系。
6. 保存结果，方便写论文或报告。

---

## 十一、数学建模比赛中的常见数据任务

### 1. 数据预处理

常见操作：

- 缺失值处理。
- 异常值处理。
- 单位统一。
- 时间格式转换。
- 文本类别编码。
- 指标正向化。
- 标准化或归一化。

### 2. 探索性分析

常见问题：

- 哪些变量均值较高？
- 哪些变量波动较大？
- 哪些变量之间相关？
- 是否存在明显异常点？
- 不同类别之间差异是否明显？

常用工具：

- `df.describe()`
- `df.groupby()`
- `df.corr()`
- 折线图、散点图、箱线图、热力图

### 3. 建模

常见建模类型：

| 问题 | 常用方法 |
|---|---|
| 预测连续数值 | 线性回归、多项式回归、随机森林回归 |
| 判断类别 | 逻辑回归、决策树、随机森林 |
| 综合评价 | 标准化、熵权法、TOPSIS、层次分析法 |
| 分类分组 | KMeans、层次聚类 |
| 变量降维 | PCA |
| 最优方案 | 线性规划、非线性规划、整数规划 |
| 曲线趋势 | 最小二乘拟合、指数拟合、插值 |

### 4. 结果解释

建模不是只输出一个数。报告中通常需要说明：

1. 为什么选择这个模型。
2. 数据经过了哪些处理。
3. 参数或权重有什么含义。
4. 模型效果如何。
5. 模型有什么局限。
6. 结果对实际问题有什么解释。

---

## 十二、学习路线建议

### 第一阶段：能处理表格

目标：

- 会读 Excel / CSV。
- 会看 `head()`、`info()`、`describe()`。
- 会处理缺失值和异常值。
- 会筛选、排序、分组统计。

重点库：

- `Pandas`
- `NumPy`

### 第二阶段：能画分析图

目标：

- 会画折线图、散点图、柱状图、直方图、箱线图。
- 会设置标题、标签、图例、网格。
- 会保存高清图片。

重点库：

- `Matplotlib`

### 第三阶段：能做基础建模

目标：

- 会线性拟合、多项式拟合。
- 会标准化和归一化。
- 会计算误差指标。
- 会用 `curve_fit` 做非线性拟合。

重点库：

- `NumPy`
- `SciPy`
- `scikit-learn`

### 第四阶段：能写完整分析流程

目标：

- 能把读取、清洗、分析、建模、画图、导出写成一个完整脚本。
- 能把关键结果整理进论文。
- 能解释模型假设、参数意义和局限。

---

## 十三、速查表

### 1. NumPy 速查

| 需求 | 写法 |
|---|---|
| 创建数组 | `np.array([...])` |
| 等差数组 | `np.arange(start, stop, step)` |
| 等间隔取点 | `np.linspace(start, stop, num)` |
| 改变形状 | `a.reshape(m, n)` |
| 平均值 | `np.mean(a)` |
| 标准差 | `np.std(a)` |
| 矩阵乘法 | `A @ B` |
| 解线性方程组 | `np.linalg.solve(A, b)` |
| 随机数生成器 | `np.random.default_rng(seed)` |

### 2. Pandas 速查

| 需求 | 写法 |
|---|---|
| 读 CSV | `pd.read_csv("data.csv")` |
| 读 Excel | `pd.read_excel("data.xlsx")` |
| 前几行 | `df.head()` |
| 数据概况 | `df.info()` |
| 统计摘要 | `df.describe()` |
| 缺失值统计 | `df.isna().sum()` |
| 删除缺失值 | `df.dropna()` |
| 条件筛选 | `df[df["col"] > 0]` |
| 分组统计 | `df.groupby("group")["value"].mean()` |
| 导出 Excel | `df.to_excel("result.xlsx", index=False)` |

### 3. Matplotlib 速查

| 需求 | 写法 |
|---|---|
| 折线图 | `plt.plot(x, y)` |
| 散点图 | `plt.scatter(x, y)` |
| 柱状图 | `plt.bar(names, values)` |
| 直方图 | `plt.hist(data, bins=30)` |
| 标题 | `plt.title("标题")` |
| 坐标轴 | `plt.xlabel("x")` / `plt.ylabel("y")` |
| 图例 | `plt.legend()` |
| 网格 | `plt.grid(True)` |
| 保存图片 | `plt.savefig("fig.png", dpi=300, bbox_inches="tight")` |

### 4. SciPy 速查

| 需求 | 写法 |
|---|---|
| 方程求根 | `optimize.root_scalar(f, bracket=[a, b])` |
| 一元最小化 | `optimize.minimize_scalar(f)` |
| 多元最小化 | `optimize.minimize(f, x0=[...])` |
| 曲线拟合 | `optimize.curve_fit(model, x, y)` |
| 数值积分 | `integrate.quad(f, a, b)` |
| 插值 | `CubicSpline(x, y)` / `np.interp(x_new, x, y)` |
| 正态分布概率 | `stats.norm.cdf(x)` |

---

## 十四、最后的复习主线

数学建模中的 Python 可以用一句话概括：

> 用 `Pandas` 管表格，用 `NumPy` 算数值，用 `Matplotlib` 画关系，用 `SciPy` 解数学问题，用 `scikit-learn` 做可复用的模型流程。

最重要的不是背函数，而是形成稳定流程：

```text
数据从哪里来？
数据是否干净？
变量之间有什么关系？
应该选择什么模型？
模型参数如何求？
模型效果如何评价？
结果如何解释和展示？
```

只要每次建模都按这条链路推进，Python 工具就不会是一堆零散函数，而会变成解决问题的完整工具箱。
