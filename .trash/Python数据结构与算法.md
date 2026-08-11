# Python 数据结构与算法


## 一、复杂度分析（Big-O）

### 1. 为什么需要复杂度

数据规模变大时，不同算法的耗时差异巨大。复杂度描述的是**运行时间/内存随输入规模 n 增长的趋势**，忽略常数。

### 2. 常见复杂度（从快到慢）

| 记号 | 名称 | 例子 |
|---|---|---|
| O(1) | 常数时间 | 数组按下标访问、字典/集合查询 |
| O(log n) | 对数时间 | 二分查找 |
| O(n) | 线性时间 | 顺序查找、遍历 |
| O(n log n) | 线性对数 | 归并排序、快速排序（平均） |
| O(n²) | 平方时间 | 冒泡排序、双重循环 |
| O(2ⁿ) | 指数时间 | 暴力枚举子集 |
| O(n!) | 阶乘 | 全排列 |

判断顺序：只看**增长最快**的项：O(3n² + 2n + 1) ≈ O(n²)。

### 3. 时间 vs 空间

- **时间复杂度**：做了什么（步数）
- **空间复杂度**：用了多少额外内存

以空间换时间是算法优化常见思路（如动态规划、哈希表）。

---

## 二、数组（Python 的 list）

### 1. 动态数组原理

Python 的 `list` 本质是**动态数组**：底层是一块连续内存，容量不够时自动扩容（通常翻倍）。所以：

- 按下标访问：O(1)
- 末尾 append / pop：平均 O(1)
- 头部/中间插入删除：O(n)，需要搬移后续元素
- 按值查找 `in`：O(n)

```python
arr = [1, 2, 3]
arr.append(4)        # O(1)
x = arr[0]           # O(1)
arr.insert(0, 0)     # O(n)，全员右移
```

### 2. 什么时候不用 list

- 频繁在头部/中间插入：用链表（见下）或 `collections.deque`
- 频繁成员判断：用 `set`（哈希，O(1)）
- 数值计算大矩阵：用 numpy（见分析库笔记）

---

## 三、链表 Linked List

### 1. 节点与链表结构

链表由一个个 **节点** 串成，每个节点存数据 + 指向下一个节点的指针。内存不连续，靠指针连接。

```python
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

# 手动串起 3 个节点
a = Node(1)
b = Node(2)
c = Node(3)
a.next = b
b.next = c
```

### 2. 单链表的完整实现

```python
class LinkedList:
    def __init__(self):
        self.head = None

    def append(self, data):          # 尾部添加
        new_node = Node(data)
        if self.head is None:
            self.head = new_node
            return
        cur = self.head
        while cur.next:
            cur = cur.next
        cur.next = new_node

    def prepend(self, data):         # 头部添加 O(1)
        new_node = Node(data)
        new_node.next = self.head
        self.head = new_node

    def delete(self, data):          # 删除第一个匹配的节点
        if self.head is None:
            return
        if self.head.data == data:
            self.head = self.head.next
            return
        cur = self.head
        while cur.next and cur.next.data != data:
            cur = cur.next
        if cur.next:
            cur.next = cur.next.next   # 跳过被删节点

    def search(self, data):          # 查找
        cur = self.head
        while cur:
            if cur.data == data:
                return True
            cur = cur.next
        return False

    def __len__(self):
        count = 0
        cur = self.head
        while cur:
            count += 1
            cur = cur.next
        return count

    def __str__(self):
        values = []
        cur = self.head
        while cur:
            values.append(str(cur.data))
            cur = cur.next
        return " -> ".join(values) + " -> None"
```

测试：

```python
ll = LinkedList()
ll.append(1)
ll.append(2)
ll.prepend(0)
print(ll)          # 0 -> 1 -> 2 -> None
ll.delete(1)
print(ll)          # 0 -> 2 -> None
print(ll.search(2))  # True
print(len(ll))     # 2
```

### 3. 反转链表（高频面试题）

三个指针依次翻转，最后 `head` 指向 `prev`：

```python
def reverse(head):
    prev = None
    cur = head
    while cur:
        nxt = cur.next    # 先保存下一个
        cur.next = prev   # 指针反转
        prev = cur
        cur = nxt
    return prev           # prev 是新的头

# 用法：ll.head = reverse(ll.head)
```

或者用递归：

```python
def reverse_recursive(head):
    if head is None or head.next is None:
        return head
    new_head = reverse_recursive(head.next)
    head.next.next = head   # 让下一个节点指回自己
    head.next = None
    return new_head
```

### 4. 快慢指针找中间节点 / 判断环

```python
def find_middle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next        # 走一步
        fast = fast.next.next   # 走两步
    return slow                 # 快指针到头时，慢指针在中点

def has_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:        # 快指针追上了慢指针
            return True
    return False
```

### 5. 双向链表与循环链表（简介）

- **双向链表**：节点多一个 `prev` 指针，删除节点时不需要找前驱，O(1) 完成（但每个节点内存更大）。Python 的 `collections.deque` 就是双向链表实现的。
- **循环链表**：尾节点的 `next` 指回头节点，常用于轮转调度、约瑟夫环问题。

### 6. 数组 vs 链表对比

| 操作 | 数组 list | 链表 |
|---|---|---|
| 按下标访问 | O(1) ✅ | O(n) ❌ |
| 末尾插入 | O(1) ✅ | O(n)（需遍历）❌ |
| 头部插入 | O(n) ❌ | O(1) ✅ |
| 中间插入（已有指针） | O(n) ❌ | O(1) ✅ |
| 内存 | 连续，省 | 每节点有指针开销 |
| 缓存友好 | 好 | 差 |

一句话：**索引访问多 → 用数组；频繁头部/中间插入删除 → 用链表**。

---

## 四、栈 Stack

### 1. 概念

**后进先出（LIFO）**：只能从栈顶放入（push）、取出（pop）。像一摞盘子。

Python 里直接用 list 实现即可（`append` / `pop` 都是 O(1)）：

```python
stack = []
stack.append(1)      # push
stack.append(2)
stack.append(3)
print(stack.pop())   # 3
print(stack.pop())   # 2
print(stack[-1])     # peek 看一眼栈顶不取出
```

### 2. 经典应用：括号匹配

```python
def is_balanced(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack
```

```python
print(is_balanced("(a[b]{c})"))   # True
print(is_balanced("[(])"))        # False
```

### 3. 经典应用：逆波兰表达式求值

后缀表达式 `3 4 +` = 3 + 4：

```python
def eval_rpn(tokens):
    stack = []
    for t in tokens:
        if t in "+-*/":
            b = stack.pop()
            a = stack.pop()
            if t == "+": stack.append(a + b)
            elif t == "-": stack.append(a - b)
            elif t == "*": stack.append(a * b)
            else: stack.append(a / b)
        else:
            stack.append(int(t))
    return stack[0]

print(eval_rpn(["3", "4", "+", "2", "*"]))   # 14
```

### 4. 用栈实现的功能

- 括号匹配、HTML 标签配对
- 表达式求值（中缀转后缀）
- 函数调用栈（递归的本质就是系统栈）
- 浏览器前进后退、编辑器撤销

---

## 五、队列 Queue

### 1. 概念

**先进先出（FIFO）**：队尾入、队头出，像排队窗口。

用 `collections.deque`（底层是双向链表，两端操作都 O(1)）：

```python
from collections import deque

q = deque()
q.append(1)      # 队尾入队
q.append(2)
q.append(3)
q.popleft()      # 队头出队 -> 1
q.popleft()      # 2
```

不要用 list 当队列：`list.pop(0)` 是 O(n)。

### 2. 环形队列（原理）

数组实现队列时，出队不搬移元素，而是让 `head` 指针后移，`head` 走到底后绕回开头，这就是环形队列，可复用空间：

```python
class CircularQueue:
    def __init__(self, size):
        self.size = size
        self.data = [None] * size
        self.head = self.tail = 0

    def push(self, x):
        if (self.tail + 1) % self.size == self.head:
            raise OverflowError("queue full")
        self.data[self.tail] = x
        self.tail = (self.tail + 1) % self.size

    def pop(self):
        if self.head == self.tail:
            raise IndexError("empty")
        x = self.data[self.head]
        self.data[self.head] = None
        self.head = (self.head + 1) % self.size
        return x
```

### 3. 双端队列 deque 常用方法

```python
from collections import deque

d = deque([1, 2, 3])
d.append(4)        # 尾部
d.appendleft(0)    # 头部
d.pop()
d.popleft()
d.rotate(1)        # 整体右移一位
print(list(d))
```

deque 常用于**滑动窗口**问题：窗口内只保留候选值，窗口移动时两端进出。

### 4. 优先级队列 `heapq`（堆）

按**优先级**出队，而不是入队顺序。Python 的 `heapq` 实现的是小顶堆：

```python
import heapq

heap = []
heapq.heappush(heap, 3)
heapq.heappush(heap, 1)
heapq.heappush(heap, 2)
smallest = heapq.heappop(heap)    # 1，永远先弹最小
```

常用操作：

```python
nums = [5, 3, 8, 1]
heapq.heapify(nums)                 # 原地建堆 O(n)
print(heapq.heappushpop(nums, 2))   # push 后弹出最小
print(heapq.nlargest(2, nums))      # 最大的两个
print(heapq.nsmallest(2, nums))     # 最小的两个

# 大顶堆技巧：存负数
heap = []
heapq.heappush(heap, -5)
heapq.heappush(heap, -1)
print(-heapq.heappop(heap))   # 5
```

应用：Top-K 问题（在一个大数据流里维护最大的 K 个，用大小为 K 的小顶堆）、Dijkstra 最短路径、任务调度。

---

## 六、树 Tree

### 1. 基本概念

- **节点**：树的基本单位；**根**：没有父节点的节点
- **父节点 / 子节点 / 兄弟节点 / 叶子节点**（没有子节点）
- **子树**：任意节点连同它下面的分支
- **深度**：从根到该节点的边数
- **满二叉树 / 完全二叉树**：堆、数组存储时的常见形态

### 2. 二叉树的节点定义

```python
class TreeNode:
    def __init__(self, val):
        self.val = val
        self.left = None
        self.right = None
```

手动构造上图：

```python
root = TreeNode(1)
root.left = TreeNode(2)
root.right = TreeNode(3)
root.left.left = TreeNode(4)
root.left.right = TreeNode(5)
"""
        1
       / \
      2   3
     / \
    4   5
"""
```

### 3. 深度优先遍历 DFS（前序 / 中序 / 后序）

区别在于**根节点何时被访问**：

```python
def preorder(node):        # 前序：根 -> 左 -> 右
    if node is None:
        return []
    return [node.val] + preorder(node.left) + preorder(node.right)

def inorder(node):         # 中序：左 -> 根 -> 右（BST 结果是升序！）
    if node is None:
        return []
    return inorder(node.left) + [node.val] + inorder(node.right)

def postorder(node):       # 后序：左 -> 右 -> 根
    if node is None:
        return []
    return postorder(node.left) + postorder(node.right) + [node.val]
```

```python
print(preorder(root))    # [1, 2, 4, 5, 3]
print(inorder(root))     # [4, 2, 5, 1, 3]
print(postorder(root))   # [4, 5, 2, 3, 1]
```

用显式**栈**实现前序（避免递归深度限制）：

```python
def preorder_iter(root):
    if root is None:
        return []
    result = []
    stack = [root]
    while stack:
        node = stack.pop()
        result.append(node.val)
        if node.right:      # 先压右，再压左（栈后进先出）
            stack.append(node.right)
        if node.left:
            stack.append(node.left)
    return result
```

### 4. 广度优先遍历 BFS（层序遍历）

用**队列**，一层一层从上到下、从左到右：

```python
from collections import deque

def level_order(root):
    if root is None:
        return []
    result = []
    q = deque([root])
    while q:
        level_size = len(q)      # 当前层有这么多节点
        level = []
        for _ in range(level_size):
            node = q.popleft()
            level.append(node.val)
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
        result.append(level)     # 每一层单独一个列表
    return result

print(level_order(root))   # [[1], [2, 3], [4, 5]]
```

### 5. 二叉搜索树 BST

性质：**左子树所有值 < 根 < 右子树所有值**（假设无重复）。

```python
def bst_insert(root, val):
    if root is None:
        return TreeNode(val)
    if val < root.val:
        root.left = bst_insert(root.left, val)
    else:
        root.right = bst_insert(root.right, val)
    return root

def bst_search(root, val):
    if root is None or root.val == val:
        return root
    if val < root.val:
        return bst_search(root.left, val)
    return bst_search(root.right, val)

def bst_min(node):           # 最小在左下角
    while node.left:
        node = node.left
    return node

def bst_delete(root, val):
    if root is None:
        return None
    if val < root.val:
        root.left = bst_delete(root.left, val)
    elif val > root.val:
        root.right = bst_delete(root.right, val)
    else:
        if root.left is None:      # 无左子：用右子树顶替
            return root.right
        if root.right is None:     # 无右子：用左子树顶替
            return root.left
        successor = bst_min(root.right)     # 有两个孩子：用右子树最小节点顶替
        root.val = successor.val
        root.right = bst_delete(root.right, successor.val)
    return root
```

```python
tree = None
for v in [5, 3, 7, 2, 4, 8]:
    tree = bst_insert(tree, v)
print(inorder(tree))              # [2, 3, 4, 5, 7, 8] 中序一定有序
print(bst_search(tree, 4).val)    # 4
tree = bst_delete(tree, 3)
print(inorder(tree))              # [2, 4, 5, 7, 8]
```

- 查找 / 插入 / 删除平均 O(log n)
- 若按有序序列插入会退化成链表，变成 O(n)，此时需要用平衡树（AVL、红黑树），Python 中可直接用 `bisect` 模块或 `sortedcontainers`。

### 6. 最大深度（经典例题）

```python
def max_depth(root):
    if root is None:
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))
```

### 7. 堆 Heap（概念回顾）

- **完全二叉树** + **父节点 ≤ 子节点**（小顶堆）就是堆
- `heapq` 已经封装好，直接用它，无需手写（见队列章节）
- 应用：优先队列、堆排序、Top-K

---

## 七、图 Graph

### 1. 图的表示

图 = 顶点（vertex）+ 边（edge）。两种常用表示：

**邻接表**（推荐，Python 里用字典）：

```python
graph = {
    "A": ["B", "C"],
    "B": ["A", "D"],
    "C": ["A", "D"],
    "D": ["B", "C"],
}
```

有向带权图：

```python
weighted = {
    "A": [("B", 5), ("C", 2)],
    "B": [("D", 1)],
    "C": [("D", 3)],
}
```

**邻接矩阵**（顶点少、边稠密时）：

```python
#      A  B  C  D
mat = [
    [0, 1, 1, 0],   # A
    [1, 0, 0, 1],   # B
    [1, 0, 0, 1],   # C
    [0, 1, 1, 0],   # D
]
```

### 2. 深度优先遍历 DFS

**走到底再回头**。递归版：

```python
def dfs_recursive(graph, node, visited=None):
    if visited is None:
        visited = set()
    visited.add(node)
    print(node, end=" ")          # 访问
    for nxt in graph[node]:
        if nxt not in visited:
            dfs_recursive(graph, nxt, visited)
```

显式栈版（迭代）：

```python
def dfs_iterative(graph, start):
    visited = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        print(node, end=" ")
        for nxt in graph[node]:   # 逆序压栈，保证顺序与递归一致
            if nxt not in visited:
                stack.append(nxt)
```

```python
graph = {
    "A": ["B", "C"],
    "B": ["A", "D", "E"],
    "C": ["A", "F"],
    "D": ["B"],
    "E": ["B", "F"],
    "F": ["C", "E"],
}
dfs_recursive(graph, "A")   # A B D E F C
```

### 3. 广度优先遍历 BFS

**一层一层扩散**，用队列。BFS 走出的路径天然就是**无权图的最短路径**：

```python
from collections import deque

def bfs(graph, start):
    visited = {start}
    q = deque([start])
    while q:
        node = q.popleft()
        print(node, end=" ")
        for nxt in graph[node]:
            if nxt not in visited:
                visited.add(nxt)
                q.append(nxt)
```

```python
bfs(graph, "A")   # A B C D E F
```

### 4. 无权图最短路径（BFS 记录路径）

```python
def shortest_path(graph, start, target):
    q = deque([start])
    visited = {start}
    prev = {start: None}          # 记录每个点从哪来
    while q:
        node = q.popleft()
        if node == target:
            path = []
            while node is not None:
                path.append(node)
                node = prev[node]
            return path[::-1]
        for nxt in graph[node]:
            if nxt not in visited:
                visited.add(nxt)
                prev[nxt] = node
                q.append(nxt)
    return None
```

### 5. 带权图最短路径 Dijkstra（简介）

思路：每次从未处理节点中选**当前距离最小**的，松弛它的邻居。用优先队列（堆）实现。

```python
import heapq

def dijkstra(graph, start):
    dist = {node: float("inf") for node in graph}
    dist[start] = 0
    pq = [(0, start)]              # (当前距离, 节点)
    while pq:
        d, node = heapq.heappop(pq)
        if d > dist[node]:         # 过期条目，跳过
            continue
        for nxt, w in graph[node]:
            new_d = d + w
            if new_d < dist[nxt]:  # 松弛
                dist[nxt] = new_d
                heapq.heappush(pq, (new_d, nxt))
    return dist
```

```python
wg = {
    "A": [("B", 4), ("C", 2)],
    "B": [("C", 1), ("D", 5)],
    "C": [("D", 8), ("E", 10)],
    "D": [("E", 2)],
    "E": [],
}
print(dijkstra(wg, "A"))   # {'A': 0, 'B': 4, 'C': 2, 'D': 9, 'E': 11}
```

注意：Dijkstra 要求边权非负；有负权边用 Bellman-Ford。

### 6. 拓扑排序（有向无环图，简介）

思路：每次找一个**入度为 0** 的节点输出并删除它的出边。可用于课程安排、任务依赖。

```python
def topo_sort(graph):
    from collections import deque
    indegree = {node: 0 for node in graph}
    for node in graph:
        for nxt in graph[node]:
            indegree[nxt] += 1
    q = deque([n for n in graph if indegree[n] == 0])
    order = []
    while q:
        node = q.popleft()
        order.append(node)
        for nxt in graph[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                q.append(nxt)
    return order if len(order) == len(graph) else None   # None 说明有环
```

---

## 八、查找算法

### 1. 顺序查找（线性查找）

从头到尾逐个比较。数据**无序**时唯一选择。

```python
def linear_search(arr, target):
    for i, x in enumerate(arr):
        if x == target:
            return i
    return -1
```

- 时间复杂度：O(n)
- Python 的 `list.index()`、`in` 底层就是线性查找

### 2. 二分查找（折半查找）

**前提：数组必须已排序**。每次比较中间元素，把搜索范围缩小一半。

迭代版：

```python
def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
```

递归版：

```python
def binary_search_rec(arr, target, low=0, high=None):
    if high is None:
        high = len(arr) - 1
    if low > high:
        return -1
    mid = (low + high) // 2
    if arr[mid] == target:
        return mid
    if arr[mid] < target:
        return binary_search_rec(arr, target, mid + 1, high)
    return binary_search_rec(arr, target, low, mid - 1)
```

```python
print(binary_search([1, 3, 5, 7, 9, 11], 7))    # 3
print(binary_search([1, 3, 5, 7, 9, 11], 4))    # -1
```

- 时间复杂度：O(log n)
- 注意：`mid = (low + high) // 2` 用向下取整；`low <= high` 的边界条件最容易写错，建议自己在纸上推一遍
- Python 自带 `bisect` 模块："在有序序列中找插入位置"

```python
import bisect
arr = [1, 3, 5, 7, 9]
print(bisect.bisect_left(arr, 6))   # 3，6 应该插在索引 3 处
print(bisect.bisect_left(arr, 5))   # 2，返回最左边的插入点
print(bisect.bisect_right(arr, 5))  # 3，返回最右边的插入点
```

### 3. 查找算法对比

| 算法 | 条件 | 时间复杂度 |
|---|---|---|
| 顺序查找 | 无 | O(n) |
| 二分查找 | 有序 | O(log n) |
| 哈希查找（set/dict） | 元素可哈希 | O(1) |
| 二叉搜索树 | 建树合理 | O(log n) |

---

## 九、搜索算法（DFS 与 BFS 再总结）

上一章已在树和图里演示过。这里统一定位：

| | DFS 深度优先 | BFS 广度优先 |
|---|---|---|
| 数据结构 | 栈（或递归） | 队列 |
| 行为 | 一条路走到底再回头 | 一层层扩散 |
| 适用 | 连通性、路径枚举、回溯 | 无权图最短路径、层序 |
| 时间 | O(V+E) | O(V+E) |

```python
# 统一的框架模板（图，用「已访问集合」防止死循环）
def dfs(graph, start):
    visited, stack = set(), [start]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        for nxt in graph[node]:
            if nxt not in visited:
                stack.append(nxt)

def bfs(graph, start):
    from collections import deque
    visited, q = {start}, deque([start])
    while q:
        node = q.popleft()
        for nxt in graph[node]:
            if nxt not in visited:
                visited.add(nxt)
                q.append(nxt)
```

---

## 十、排序算法

### 1. 冒泡排序 Bubble Sort

相邻比较，大的往后冒。每一轮把当前最大元素"沉"到末尾：

```python
def bubble_sort(arr):
    n = len(arr)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:      # 本轮没有交换，已经有序
            break
    return arr
```

最好 O(n)，平均/最坏 O(n²)，稳定。

### 2. 选择排序 Selection Sort

每轮选最小的放到最前面：

```python
def selection_sort(arr):
    n = len(arr)
    for i in range(n - 1):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
        arr[i], arr[min_idx] = arr[min_idx], arr[i]   # 交换到正确位置
    return arr
```

无论什么情况都是 O(n²)，不稳定（交换可能破坏稳定性）。

### 3. 插入排序 Insertion Sort

像打扑克牌：把每张牌插入到已排序部分正确的位置：

```python
def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]   # 大的往后挪
            j -= 1
        arr[j + 1] = key
    return arr
```

最好 O(n)（几乎有序时），平均/最坏 O(n²)，稳定。小规模数据最快的简单排序。

### 4. 归并排序 Merge Sort（分治）

把数组一分为二，各自排好，再合并两个有序数组。**稳定、稳定 O(n log n)**，但需要 O(n) 额外空间：

```python
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    i = j = 0
    result = []
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

print(merge_sort([3, 1, 4, 1, 5, 9, 2, 6]))
```

分治三步骤：**分解 → 递归求解 → 合并结果**。

### 5. 快速排序 Quick Sort（分治 + 枢轴）

选一个基准（pivot），把比它小的放左边、大的放右边，再递归排两边。**平均 O(n log n)（绝大多数场景最快的通用排序之一）**，最坏 O(n²)（已有序且枢轴选最值时），不稳定，原地进行。

```python
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]          # 取中间值做基准，避免最坏情况
    left = [x for x in arr if x < pivot]
    mid = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + mid + quick_sort(right)
```

上面用列表推导实现（额外空间，但好理解）。原地分区版本（面试常考）：

```python
def quick_sort_inplace(arr, low=0, high=None):
    if high is None:
        high = len(arr) - 1
    if low >= high:
        return arr
    pivot = arr[(low + high) // 2]
    i, j = low, high
    while i <= j:
        while arr[i] < pivot:
            i += 1
        while arr[j] > pivot:
            j -= 1
        if i <= j:
            arr[i], arr[j] = arr[j], arr[i]
            i += 1
            j -= 1
    quick_sort_inplace(arr, low, j)
    quick_sort_inplace(arr, i, high)
    return arr
```

### 6. 堆排序 Heap Sort

用堆（`heapq`）每次取最小：

```python
import heapq

def heap_sort(arr):
    heapq.heapify(arr)          # 原地建小顶堆
    return [heapq.heappop(arr) for _ in range(len(arr))]
```

稳定 O(n log n)，不稳定，可原地（`_siftup` 手动实现）。

### 7. 计数排序 Counting Sort（桶思想，简介）

适用于**整数且取值范围小**的场景，O(n + k)：

```python
def counting_sort(arr):
    if not arr:
        return arr
    k = max(arr)
    count = [0] * (k + 1)
    for x in arr:
        count[x] += 1
    result = []
    for value, c in enumerate(count):
        result.extend([value] * c)
    return result
```

### 8. 排序算法对比表

| 算法 | 平均 | 最好 | 最坏 | 空间 | 稳定 |
|---|---|---|---|---|---|
| 冒泡 | O(n²) | O(n) | O(n²) | O(1) | 稳定 |
| 选择 | O(n²) | O(n²) | O(n²) | O(1) | 不稳定 |
| 插入 | O(n²) | O(n) | O(n²) | O(1) | 稳定 |
| 归并 | O(n log n) | O(n log n) | O(n log n) | O(n) | 稳定 |
| 快排 | O(n log n) | O(n log n) | O(n²) | O(log n) | 不稳定 |
| 堆排 | O(n log n) | O(n log n) | O(n log n) | O(1) | 不稳定 |
| 计数 | O(n+k) | O(n+k) | O(n+k) | O(k) | 稳定 |

**工程实践**：Python 内置 `sort` 是 TimSort（归并+插入的混合），稳定且非常快，日常直接用 `sort()` / `sorted()`，手写排序是为了理解原理和应对面试。

---

## 十一、贪心算法 Greedy

### 1. 思想

每步都做**当前看起来最优**的选择，希望最终全局最优。适合"每一步的最优能推出全局最优"的问题（称为贪心选择性质）。

**不是所有问题都能贪心**，判断方法是尝试证明或举反例。例如 0/1 背包不能贪心（见动态规划章节），但找零钱（面额整除关系时）、活动选择、霍夫曼编码可以。

### 2. 例 1：找零钱

硬币面额 1、5、10、25，用最少数量的硬币凑出金额：

```python
def coin_change_greedy(amount, coins=(25, 10, 5, 1)):
    coins = sorted(coins, reverse=True)
    result = []
    for c in coins:
        while amount >= c:
            result.append(c)
            amount -= c
    return result

print(coin_change_greedy(63))   # [25, 25, 10, 1, 1, 1]
```

只有当大面额是小面额的倍数（或面额设计合理）时贪心才是最优的；换成 1、3、4 凑 6，贪心给 4+1+1 共 3 枚，而最优是 3+3 共 2 枚 —— 此时必须用动态规划。

### 3. 例 2：活动选择（会议安排）

有一批带开始/结束时间的活动，选出**最多互不冲突**的活动：

```python
def activity_selection(activities):
    activities = sorted(activities, key=lambda x: x[1])   # 按结束时间排序
    selected = []
    last_end = 0
    for start, end in activities:
        if start >= last_end:     # 不冲突就选
            selected.append((start, end))
            last_end = end
    return selected

acts = [(1, 4), (3, 5), (0, 6), (5, 7), (3, 8), (5, 9), (6, 10), (8, 11), (8, 12)]
print(activity_selection(acts))   # [(1, 4), (5, 7), (8, 11)]
```

关键：**按结束时间最早的活动优先选**（给后面留最多空间）。

### 4. 例 3：跳跃游戏

数组每个位置表示能跳的最大步数，判断能否到达最后：每步记录"当前能到的最远位置"，贪心维护最远距离。

```python
def can_jump(nums):
    farthest = 0
    for i, step in enumerate(nums):
        if i > farthest:          # 当前索引已经追不上最远距离
            return False
        farthest = max(farthest, i + step)
    return farthest >= len(nums) - 1
```

### 5. 贪心的常见套路

1. 排序（按某个关键属性，如结束时间、单价）
2. 从头到尾逐个做局部最优选择
3. 证明贪心选择不会导致更差结果（或用常识+测试验证）

复杂度通常就是排序的 O(n log n)。

---

## 十二、动态规划 Dynamic Programming

### 1. 思想与适用条件

动态规划把大问题分解成**重叠的小问题**，保存小问题的答案避免重复计算。与分治（如归并）的区别：分治的子问题**互不重叠**，DP 的子问题**大量重叠**。

适用条件：

- **最优子结构**：全局最优包含子问题最优
- **重叠子问题**：同一子问题被反复求解

### 2. 两种实现方式

**自顶向下（记忆化搜索）**：递归 + 缓存：

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
```

**自底向上（填表）**：从小到大依次计算，用循环代替递归：

```python
def fib_dp(n):
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
```

对比：朴素递归 `fib(50)` 永远算不完（指数爆炸），DP 只要 O(n)。

自底向上可以进一步省空间（滚动数组）：

```python
def fib_opt(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
```

### 3. 例 1：爬楼梯

每次可以爬 1 或 2 阶，爬到 n 阶有多少种方法？

```python
def climb_stairs(n):
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1], dp[2] = 1, 2
    for i in range(3, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]   # 状态转移方程
    return dp[n]
```

推导：到第 i 阶 = 从 i-1 阶跨 1 步 + 从 i-2 阶跨 2 步。

**DP 四步法**：
1. 定义 `dp[i]` 的含义
2. 找状态转移方程（当前状态如何由之前状态得到）
3. 初始化边界（`dp[1]`、`dp[2]` 等）
4. 确定遍历方向（从小到大）

### 4. 例 2：最大子数组和

找出数组中和最大的连续子数组：

```python
def max_subarray(nums):
    dp = nums[:]                  # dp[i] = 以 i 结尾的最大和
    for i in range(1, len(nums)):
        dp[i] = max(nums[i], dp[i - 1] + nums[i])
    return max(dp)

print(max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]))   # 6 = 4 + (-1) + 2 + 1
```

转移思想：以 i 结尾的子数组要么只有 `nums[i]` 自己，要么接上以 i-1 结尾的最优子数组。

### 5. 例 3：0/1 背包

容量 W 的背包，每件物品只能拿一次，价值最大（**贪心无效**的例子）：

```python
def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    # dp[i][w] = 只考虑前 i 件物品、容量为 w 的最大价值
    for i in range(1, n + 1):
        wi, vi = weights[i - 1], values[i - 1]
        for w in range(1, capacity + 1):
            if wi > w:
                dp[i][w] = dp[i - 1][w]              # 装不下，只能不拿
            else:
                dp[i][w] = max(dp[i - 1][w],         # 不拿
                               dp[i - 1][w - wi] + vi)  # 拿（腾出 wi 空间）
    return dp[n][capacity]

print(knapsack([2, 3, 4, 5], [3, 4, 5, 6], 8))   # 10（拿第 2、4 件：4+6）
```

空间优化（一维滚动数组，注意 **w 必须从大到小** 遍历防止重复拿）：

```python
def knapsack_1d(weights, values, capacity):
    dp = [0] * (capacity + 1)
    for wi, vi in zip(weights, values):
        for w in range(capacity, wi - 1, -1):   # 逆序！
            dp[w] = max(dp[w], dp[w - wi] + vi)
    return dp[capacity]
```

### 6. 例 4：最长递增子序列 LIS

```python
def length_of_lis(nums):
    dp = [1] * len(nums)              # dp[i] = 以 i 结尾的 LIS 长度
    for i in range(len(nums)):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)

print(length_of_lis([10, 9, 2, 5, 3, 7, 101, 18]))   # 4 = 2, 3, 7, 101
```

O(n²)。进阶：配合二分查找可优化到 O(n log n)。

### 7. 例 5：最长公共子序列 LCS

```python
def lcs(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]

print(lcs("abcde", "ace"))   # 3，子序列 "ace"
```

双序列 DP 的通用模板：`dp[i][j]` 表示 A 前 i 个与 B 前 j 个的答案，字符相等时看 `dp[i-1][j-1]`，不等时看两个前一步的较大者。

### 8. DP 小总结

- 先想清楚 `dp[i]`（或 `dp[i][j]`）**表示什么含义**，这是全部问题的基础
- 状态转移方程就是"从旧状态算新状态的公式"
- 边界条件 = 最小子问题的答案
- 遍历方向要保证计算 `dp[i]` 时依赖的状态已经算好
- 空间往往可以优化成滚动数组（1D / 2 个变量）

常见题型：斐波那契类、爬楼梯、路径计数与路径和、背包类、买卖股票、LIS/LCS、编辑距离、区间 DP。