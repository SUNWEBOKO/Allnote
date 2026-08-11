# Python 数据分析与 AI 常用库


## 一、环境准备

安装：

```bash
pip install numpy pandas matplotlib
```

（更推荐用 Anaconda 管理环境，见深度学习笔记的 Anaconda 章节）

导入惯例（全行业统一写法）：

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
```

检查版本：

```python
print(np.__version__)    # 2.x
print(pd.__version__)
```

---

## 二、NumPy：数值计算数组

Python 的 list 也能存数，但大数组上逐元素操作慢得离谱。numpy 的 `ndarray` 是**同类型数据的连续内存块**，配合 C 语言实现，快 10~100 倍。

### 1. 创建数组

```python
import numpy as np

arr = np.array([1, 2, 3, 4])            # 从列表创建
mat = np.array([[1, 2], [3, 4]])        # 二维数组（矩阵）
print(arr.shape)                        # (4,) 形状
print(mat.shape)                        # (2, 2)

zeros = np.zeros((2, 3))                # 全 0
ones = np.ones((2, 3))                  # 全 1
full = np.full((2, 2), 7)               # 全部填充 7
eye = np.eye(3)                         # 单位矩阵
print(np.arange(10))                    # [0 1 2 ... 9]，类似 range
print(np.arange(1, 10, 2))              # [1 3 5 7 9]
print(np.linspace(0, 1, 5))             # [0.   0.25 0.5  0.75 1.  ] 等间隔 5 个数
print(np.random.rand(3))                # 3 个 [0,1) 均匀随机数
print(np.random.randint(1, 7, size=10)) # 10 个 1~6 随机整数（掷骰子）
print(np.random.randn(3))               # 3 个标准正态分布随机数
```

注意：`np.array(1,2,3)` 是错的，要传一个列表；`np.zeros(2,3)` 也要加括号。

### 2. 形状操作

```python
arr = np.arange(12)
print(arr.reshape(3, 4))     # 变为 3 行 4 列（元素总数必须一致）
print(arr.reshape(2, -1))    # -1 自动推断：2 行若干列
print(arr.reshape(-1, 6))    # 自动推断为 2 行

flat = mat.flatten()         # 展平成一维（复制）
ravel = mat.ravel()          # 展平（尽量用视图，省内存）

print(mat.T)                 # 转置
print(mat.shape)             # 查看形状
print(mat.size)              # 元素总数
print(mat.ndim)              # 维度数
```

### 3. 索引与切片（比 list 更强大）

```python
a = np.array([10, 20, 30, 40, 50])
print(a[1])        # 20
print(a[-1])       # 50
print(a[1:4])      # [20 30 40]
print(a[::-1])     # 反转

m = np.arange(12).reshape(3, 4)
print(m[1])          # 第 1 行
print(m[1, 2])       # 第 1 行第 2 列（逗号写法，不用 [1][2]）
print(m[:, 1])       # 第 1 列（: 表示所有行）
print(m[1:, :2])     # 第 1 行起、前 2 列的子矩阵
print(m[::2, ::2])   # 隔行隔列取

m[0, 0] = 99         # 按位置修改
```

**布尔掩码筛选**（数据分析最常用的数据筛选方式）：

```python
scores = np.array([58, 92, 75, 66, 83])
mask = scores >= 60          # [False  True  True  True  True]
print(scores[mask])          # [92 75 66 83] 达标的人
print(scores[scores >= 90])  # 一行写法
print((scores >= 60) & (scores < 80))   # 与运算（元素级用 & 不是 and）
```

**花式索引**（用整数数组取值）：

```python
a = np.array([10, 20, 30, 40])
print(a[[0, 2, 2]])      # [10 30 30]
```

### 4. 向量化运算（核心优势）

对每个元素做同样运算，**不用写循环**：

```python
a = np.array([1, 2, 3])
b = np.array([4, 5, 6])

print(a + 10)        # [11 12 13]
print(a * 2)         # [2 4 6]
print(a + b)         # [5 7 9]，逐元素相加
print(a * b)         # [4 10 18]，逐元素相乘（不是矩阵乘法！）
print(a ** 2)        # [1 4 9]
print(np.sqrt(a))    # [1.         1.41421356 1.73205081]
print(np.sin(a), np.log(a), np.exp(a))   # 通用函数 ufunc 全家桶
print(a @ b)         # 32，矩阵乘法（@ 运算符）
print(np.dot(a, b))  # 32，同上
```

对比写法（能体现 numpy 的价值）：

```python
# 慢：纯 Python 循环
total = sum(x ** 2 for x in range(1_000_000))

# 快：numpy 向量化
big = np.arange(1_000_000)
total = (big ** 2).sum()
```

### 5. 广播机制（Broadcasting）

不同形状的数组运算时，numpy 自动把小数组"扩展"成匹配的形状：

```python
m = np.array([[1, 2, 3],
              [4, 5, 6]])
print(m + 100)                  # 标量加到每个元素
v = np.array([10, 20, 30])
print(m + v)                    # 每行都加上 v
# [[11 22 33]
#  [14 25 36]]

col = np.array([[10], [20]])
print(m + col)                  # 每列都加上 col
# [[11 12 13]
#  [24 25 26]]
```

规则：两个数组的维度**从后往前**对齐，要么相等、要么其中一个是 1，就可以广播。

### 6. 统计与聚合

```python
data = np.array([3, 1, 4, 1, 5, 9, 2, 6])

print(data.sum())        # 31
print(data.mean())       # 3.875 均值
print(data.max())        # 9
print(data.min())        # 1
print(data.std())        # 标准差
print(data.var())        # 方差
print(data.argmax())     # 5，最大值所在下标
print(data.argmin())     # 1
print(np.median(data))   # 3.5
print(np.cumsum(data))   # 累加 [3 4 8 9 14 23 25 31]
print(data.clip(2, 6))   # 截断到 [2,6] 范围
```

二维数组按轴聚合：

```python
m = np.arange(6).reshape(2, 3)      # [[0 1 2] [3 4 5]]
print(m.sum())          # 15，全部
print(m.sum(axis=0))    # [3 5 7]，按列（压掉行方向）
print(m.sum(axis=1))    # [3 12]，按行
```

`np.where`（类 SQL 的 CASE WHEN）：

```python
scores = np.array([58, 92, 75])
result = np.where(scores >= 60, "pass", "fail")
print(result)      # ['fail' 'pass' 'pass']
```

`np.sort` 与 `np.unique`：

```python
a = np.array([3, 1, 2, 1])
print(np.sort(a))        # [1 1 2 3]
print(np.unique(a))      # [1 2 3]，去重并排序
```

### 7. 一个 n 维数组的实战小例

```python
# 模拟 5 名学生在 3 门课的成绩（5 行 3 列）
scores = np.random.randint(50, 100, size=(5, 3))

print("每位学生的总分：", scores.sum(axis=1))
print("每门课的平均分：", scores.mean(axis=0))
print("最高分出现在：", scores.argmax())        # 展平后的下标
```

---

## 三、Pandas：表格数据处理

pandas 是数据分析的核心。两个主角：

- **Series**：带索引的一维数组（像带标签的 list）
- **DataFrame**：带行列标签的二维表格（像 Excel 表）

```python
import pandas as pd
```

### 1. 创建 Series

```python
s = pd.Series([10, 20, 30], index=["a", "b", "c"])
print(s)
# a    10
# b    20
# c    30

print(s["b"])        # 20，按索引取
print(s.iloc[0])     # 10，按位置取（不要用 s[0]，偶数索引已被弃用）
print(s * 2)         # 向量化
```

### 2. 创建 DataFrame

```python
df = pd.DataFrame({
    "name": ["Alice", "Bob", "Carol"],
    "age": [24, 30, 28],
    "score": [88, 92, 79],
})
```

从列表的列表创建（指定列名、索引），用不同名字避免覆盖上面的 `df`：

```python
df2 = pd.DataFrame(
    [[1, 2], [3, 4]],
    columns=["x", "y"],
    index=["row1", "row2"],
)
```

### 3. 快速浏览

```python
df.head()        # 前 5 行
df.tail(3)       # 后 3 行
df.info()        # 每列类型、缺失值概况
df.describe()    # 数值列统计摘要（mean/std/min/四分位）
df.shape         # (行数, 列数)
df.columns       # 列名
df.dtypes        # 每列类型
```

### 4. 读取与写入文件

```python
df = pd.read_csv("sales.csv")                    # 最常用
# df = pd.read_excel("sales.xlsx", sheet_name="Sheet1")
# df = pd.read_json("data.json")

df.to_csv("output.csv", index=False)             # 写入（不带行号）
df.to_excel("output.xlsx", index=False)
```

参数：`encoding="utf-8"` 处理中文；`dtype={"age": int}` 指定类型。

### 5. 数据选择：`[]` / `loc` / `iloc`

| 写法 | 含义 |
|---|---|
| `df["col"]` | 取一列（Series） |
| `df[["a", "b"]]` | 取多列（DataFrame） |
| `df.loc[row_label, col_label]` | 按**标签**取 |
| `df.iloc[row_pos, col_pos]` | 按**位置**取 |
| `df[df["age"] > 25]` | 布尔筛选（最常用！） |

```python
df["name"]                       # 一列
df[["name", "score"]]            # 两列

df.loc[1]                        # 标签为 1 的一行
df.loc[1, "score"]               # 第 1 行第 score 列
df.loc[df["name"] == "Alice"]    # 找叫 Alice 的行
df.iloc[0]                       # 第 0 行
df.iloc[0, 2]                    # 第 0 行第 2 列
df.iloc[1:3, 0:2]                # 子表

elders = df[df["age"] >= 28]     # 布尔筛选
good = df[(df["score"] >= 80) & (df["age"] < 30)]   # 多条件：& 不能用 and
```

新增列（计算列）：

```python
df["grade"] = df["score"] // 10 + 1           # 新列
df["double_score"] = df["score"] * 2
df["full"] = df["name"] + " (" + df["age"].astype(str) + ")"
```

### 6. 缺失值处理

```python
df.isna().sum()      # 每列缺失数量
df.dropna()          # 删除含缺失的行
df.dropna(subset=["score"])   # 只按某列判断删除
df.fillna(0)         # 缺失值填 0
df["age"].fillna(df["age"].mean())   # 用该数值列的均值填充
df["age"].ffill()    # 用上一个有效值填充（前向填充）
```

### 7. 重复值

```python
df.duplicated().sum()          # 重复行数
df.drop_duplicates()           # 去重
df.drop_duplicates(subset=["name"])   # 按列去重，保留第一个
```

### 8. 排序与排名

```python
df.sort_values("score")                     # 升序
df.sort_values("score", ascending=False)    # 降序
df.sort_values(["age", "score"], ascending=[True, False])   # 多列排序
df["rank"] = df["score"].rank()             # 排名
```

### 9. 分组聚合 `groupby`（最有价值的操作）

```python
# 统计每个部门的人数和平均薪资
salary = pd.DataFrame({
    "dept": ["IT", "HR", "IT", "HR", "IT"],
    "salary": [10000, 8000, 12000, 7500, 11000],
})

print(salary.groupby("dept")["salary"].mean())
# dept
# HR     7750.0
# IT    11000.0

print(salary.groupby("dept").agg({"salary": ["mean", "max", "min", "count"]}))
# 多种聚合一起算

print(salary.groupby("dept")["salary"].sum())    # 求和
```

`agg` 可以一次算多个统计量，结果是一个多层索引 DataFrame。

```python
# 分组后的 apply：对每组做自定义处理
result = salary.groupby("dept")["salary"].apply(lambda x: x.max() - x.min())
```

### 10. 合并与连接

```python
df1 = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
df2 = pd.DataFrame({"id": [1, 3], "score": [90, 60]})

pd.concat([df1, df2])                    # 纵向拼接（行拼接）
pd.concat([df1, df2], axis=1)            # 横向拼接（列拼接）

merged = df1.merge(df2, on="id", how="inner")   # 内连接
#    id name  score
# 0   1    A   90.0
```

`how` 的取值：`inner`（交集）、`outer`（并集）、`left`（左表全留）、`right`（右表全留）。

### 11. `apply` / `map` 逐元素处理

```python
df["name_upper"] = df["name"].apply(str.upper)      # 每行/每元素应用函数
df["score_tag"] = df["score"].apply(lambda x: "高" if x >= 90 else "中低")

df["dept_short"] = df["name"].map({"Alice": "A", "Bob": "B"})   # 字典映射
```

### 12. 时间序列（简介）

```python
dates = pd.date_range("2024-01-01", periods=5, freq="D")
ts = pd.Series([1, 2, 3, 4, 5], index=dates)

print(ts.resample("2D").sum())    # 按 2 天重采样求和
print(ts.shift(1))                # 向后平移一天（算涨跌常用）
print(ts.diff())                  # 差分（相邻差值）
```

### 13. 链式操作示例（一气呵成）

```python
result = (
    pd.read_csv("sales.csv")
    .dropna()
    .query("amount > 0")                 # 类 SQL 筛选
    .assign(month=lambda d: pd.to_datetime(d["date"]).dt.month)   # 新增月份列
    .groupby("month")["amount"]
    .sum()
)
```

---

## 四、Matplotlib：数据可视化

matplotlib 能画折线、散点、柱状、直方图等。核心心智模型：**`figure`（画布）→ `axes`（子图区）→ 绘图函数**。

```python
import matplotlib.pyplot as plt
```

### 1. 最简单的一幅图

```python
x = [1, 2, 3, 4, 5]
y = [2, 4, 1, 8, 5]

plt.plot(x, y)          # 折线图
plt.show()              # 显示（交互环境可省略）
```

### 2. 常用图类型

```python
import numpy as np

x = np.linspace(0, 10, 100)

plt.figure(figsize=(8, 5))        # 画布大小（英寸）

plt.plot(x, np.sin(x), label="sin")       # 折线
plt.plot(x, np.cos(x), label="cos", linestyle="--", linewidth=2)

plt.scatter([1, 2, 3], [4, 5, 6], color="red")   # 散点
plt.bar(["A", "B", "C"], [10, 20, 15])          # 柱状
plt.hist(np.random.randn(1000), bins=30)        # 直方图

plt.title("标题")              # 标题
plt.xlabel("x 轴")
plt.ylabel("y 轴")
plt.legend()                   # 显示图例（配合 label）
plt.grid(alpha=0.3)            # 网格
# plt.savefig("fig.png", dpi=150, bbox_inches="tight")   # 保存
plt.show()
```

画布上同时画多种图是可以叠加的，多次调用 plot 即可。

### 3. 子图 `subplots`

```python
fig, axes = plt.subplots(2, 2, figsize=(10, 8))   # 2 行 2 列，axes 是数组

axes[0, 0].plot([1, 2, 3], [1, 4, 9])
axes[0, 0].set_title("线性")
axes[0, 1].bar(["a", "b"], [3, 7])
axes[1, 0].scatter(np.random.randn(50), np.random.randn(50))
axes[1, 1].hist(np.random.randn(500), bins=20)

# 自动调整间距，防止标题重叠
plt.tight_layout()
plt.show()
```

### 4. 与 pandas / numpy 配合

DataFrame 直接画图（pandas 内置 matplotlib 接口）：

```python
import pandas as pd

df = pd.DataFrame({
    "month": ["1月", "2月", "3月", "4月"],
    "sales": [120, 240, 180, 300],
})

plt.bar(df["month"], df["sales"], color="skyblue")
plt.title("月度销售额")
plt.ylabel("销售额")
plt.show()
```

```python
# 多序列对比（每个日期 3 条线）
daily = pd.DataFrame({
    "day": pd.date_range("2024-01-01", periods=7, freq="D"),
    "cpu": [40, 55, 50, 70, 65, 80, 75],
    "mem": [60, 58, 62, 66, 70, 72, 74],
}).set_index("day")

daily.plot(figsize=(8, 4), marker="o")     # 两列各画一条线，自动图例
plt.title("一周负载")
plt.show()
```

柱状图 + 分组聚合的组合（数据分析高频操作）：

```python
def plot_dept_salary(salary_df):
    avg = salary_df.groupby("dept")["salary"].mean()
    avg.plot(kind="bar", color=["#4C72B0", "#DD8452"])
    plt.title("各部门平均工资")
    plt.ylabel("平均薪资")
    plt.xticks(rotation=0)
    plt.show()
```

### 5. 样式与中文

```python
plt.style.available          # 查看可选样式
plt.style.use("ggplot")      # 使用样式
```

**中文显示**：Windows 默认字体不含中文，需指定字体（否则中文显示为方块）：

```python
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]   # Windows 微软雅黑
plt.rcParams["axes.unicode_minus"] = False              # 正常显示负号
```

其他常用 rcParams：

```python
plt.rcParams["figure.figsize"] = (8, 5)
plt.rcParams["figure.dpi"] = 100
```

### 6. 保存图片

```python
plt.savefig("output.png", dpi=150, bbox_inches="tight")
# png / jpg / pdf / svg 都可以
```

`bbox_inches="tight"` 去掉多余的留白。

---

## 五、综合实战：完整数据分析流程

把三个库串起来的典型工作流：**读数据 → 清洗 → 探索统计 → 可视化 → 结论**。

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

np.random.seed(42)   # 固定随机种子，结果可复现
n = 200
# 造一份模拟销售数据
sales = pd.DataFrame({
    "city": np.random.choice(["北京", "上海", "广州", "深圳"], n),
    "product": np.random.choice(["手机", "电脑", "耳机"], n),
    "amount": np.random.randint(100, 5000, n).astype(float),
})
# 故意制造一些缺失值演示清洗
sales.loc[np.random.choice(sales.index, 10), "amount"] = np.nan

# ---- 1. 清洗 ----
clean = sales.dropna().copy()          # copy() 避免修改原始数据的视图链
clean["amount"] = clean["amount"].round(2)

# ---- 2. 探索统计 ----
print(clean.describe())
print(clean.groupby("city")["amount"].sum().sort_values(ascending=False))

# ---- 3. 可视化 ----
fig, axes = plt.subplots(1, 3, figsize=(14, 4))

city_sum = clean.groupby("city")["amount"].sum()
axes[0].bar(city_sum.index, city_sum.values, color="skyblue")
axes[0].set_title("各城市销售额")

prod_mean = clean.groupby("product")["amount"].mean()
axes[1].bar(prod_mean.index, prod_mean.values, color="orange")
axes[1].set_title("各产品平均客单价")

axes[2].hist(clean["amount"], bins=30, color="green", alpha=0.7)
axes[2].set_title("订单金额分布")

plt.tight_layout()
plt.savefig("sales_analysis.png", dpi=150, bbox_inches="tight")
plt.show()

# ---- 4. 结论 ----
print("总销售额：", clean["amount"].sum())
print("三城市中销售额最高的是：", city_sum.idxmax())
```

---

## 六、延伸：AI 常用库衔接

### 1. scikit-learn（传统机器学习）

numpy/pandas 准备好数据后，交给 sklearn 训练模型，模式非常统一：

```python
from sklearn.linear_model import LinearRegression

# X: 特征（numpy 数组），y: 标签
model = LinearRegression()
model.fit(X, y)            # 训练
pred = model.predict(X)    # 预测
```

### 2. PyTorch（深度学习）

深度学习部分见 深度学习 目录下的 [[00-PyTorch简介与课程概述]] 系列笔记，数据加载与预处理完全建立在 numpy 之上（`torch.from_numpy`）。

### 3. 学习路线建议

```text
Python 基础（[[Python笔记]]）
  → numpy（数组运算）
  → pandas（数据处理）
  → matplotlib（可视化）
  → sklearn（传统机器学习）
  → PyTorch（深度学习）
```

三大库掌握到"能独立完成一份数据到图表的分析报告"就算达标，之后学 AI 框架会非常顺畅。