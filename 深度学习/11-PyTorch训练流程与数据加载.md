# 11 PyTorch 训练流程与数据加载

## 本章定位

PyTorch 把深度学习训练中的重复工作封装成几个核心组件：`Dataset`、`DataLoader`、`nn.Module`、损失函数、优化器和 Autograd。本章把这些组件串成一条完整训练链路，为后续鸢尾花实战做准备。

## PyTorch 训练的五个组件

一个标准训练脚本通常包含：

- **数据集 `Dataset`**：定义如何读取单个样本。
- **数据加载器 `DataLoader`**：把样本组成 batch，并负责打乱、多进程加载等。
- **模型 `nn.Module`**：定义网络结构和前向传播。
- **损失函数 `loss_fn`**：衡量预测与标签之间的差距。
- **优化器 `optimizer`**：根据梯度更新模型参数。

训练循环负责把这些组件连接起来。

## Dataset：定义单个样本如何读取

自定义数据集通常继承 `torch.utils.data.Dataset`，并实现两个方法：

```python
from torch.utils.data import Dataset


class CustomDataset(Dataset):
    def __len__(self):
        return len(self.labels)

    def __getitem__(self, index):
        return self.features[index], self.labels[index]
```

`__len__` 返回样本数量；`__getitem__` 根据索引返回一个样本和对应标签。

数据集内部可以完成：

- 文件读取。
- 标签映射。
- 数值类型转换。
- 特征标准化。
- 图像预处理。

## DataLoader：批量封装样本

`DataLoader` 接收一个 `Dataset`，按 batch 输出数据：

```python
from torch.utils.data import DataLoader

train_loader = DataLoader(
    train_dataset,
    batch_size=16,
    shuffle=True,
)
```

关键参数：

- `batch_size`：每个 batch 的样本数。
- `shuffle`：是否在每个 epoch 打乱样本顺序。
- `num_workers`：使用多少子进程加载数据，Windows 入门阶段可以先设为 0。
- `drop_last`：是否丢弃最后一个不足 batch_size 的 batch。

训练集通常 `shuffle=True`，验证集和测试集通常 `shuffle=False`。

## 模型：继承 nn.Module

模型负责把输入张量转换为输出张量：

```python
import torch.nn as nn


class IrisNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(4, 12),
            nn.ReLU(),
            nn.Linear(12, 6),
            nn.ReLU(),
            nn.Linear(6, 3),
        )

    def forward(self, x):
        return self.net(x)
```

层结构写在 `__init__` 中，计算逻辑写在 `forward` 中。调用 `model(inputs)` 时会自动执行 `forward`。

## 损失函数

分类任务常用：

```python
loss_fn = nn.CrossEntropyLoss()
```

使用要求：

- 模型输出形状为 `(batch_size, num_classes)`。
- 标签形状为 `(batch_size,)`。
- 标签类型为 `torch.long` / `torch.int64`。
- 模型输出是 logits，不需要先 softmax。

回归任务常用：

```python
loss_fn = nn.MSELoss()
```

具体选择取决于任务目标。

## 优化器

优化器负责参数更新：

```python
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
```

常用优化器：

- `SGD`：基础梯度下降，可配合 momentum。
- `Adam`：自适应学习率，入门项目常用。
- `AdamW`：Adam 的改进版本，常用于现代深度学习模型。

优化器只会更新传入的参数。如果某些参数 `requires_grad=False`，即使传入优化器也不会产生梯度更新。

## 设备管理

训练时模型和数据必须在同一个设备：

```python
import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)
```

训练循环中：

```python
inputs = inputs.to(device)
labels = labels.to(device)
```

如果模型在 GPU、数据在 CPU，会报设备不一致错误。

## 标准训练循环

完整结构如下：

```python
for epoch in range(num_epochs):
    model.train()

    for inputs, labels in train_loader:
        inputs = inputs.to(device)
        labels = labels.to(device)

        optimizer.zero_grad(set_to_none=True)
        outputs = model(inputs)
        loss = loss_fn(outputs, labels)
        loss.backward()
        optimizer.step()
```

顺序不能随意打乱：

```text
清梯度 -> 前向传播 -> 算损失 -> 反向传播 -> 更新参数
```

## 验证循环

验证不更新参数：

```python
model.eval()
correct = 0
total = 0

with torch.inference_mode():
    for inputs, labels in val_loader:
        inputs = inputs.to(device)
        labels = labels.to(device)

        outputs = model(inputs)
        preds = outputs.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

acc = correct / total
```

验证时使用 `model.eval()` 和 `torch.inference_mode()`，可以避免 Dropout/BatchNorm 状态错误，也能减少内存占用。

## Autograd：自动求导

PyTorch 的 Autograd 会在前向传播时记录计算图。只要张量参与了可求导运算，且相关参数 `requires_grad=True`，调用：

```python
loss.backward()
```

就会自动计算损失对参数的梯度。

查看梯度：

```python
for name, param in model.named_parameters():
    print(name, param.grad)
```

通常不需要手动修改梯度，除非在做梯度裁剪、梯度累积等高级训练技巧。

## 常见错误

### 标签形状错误

`CrossEntropyLoss` 要求标签形状是 `(batch_size,)`，不是 `(batch_size, 1)`，也不是 one-hot。

### 忘记清空梯度

每个 batch 前需要：

```python
optimizer.zero_grad(set_to_none=True)
```

否则梯度会累加。

### 模型和数据不在同一设备

确保模型、输入、标签都 `.to(device)`。

### 训练和验证模式混用

训练前 `model.train()`，验证/测试前 `model.eval()`。

## 本章速记

- `Dataset` 管单个样本，`DataLoader` 管 batch。
- `nn.Module` 管模型结构，`forward` 管前向传播。
- `loss.backward()` 算梯度，`optimizer.step()` 更新参数。
- 分类任务用 `CrossEntropyLoss` 时，输出 logits，标签是一维 `int64`。
- 训练、验证、测试要分别写清楚，避免数据泄漏。
