# 03 集成开发环境 IDE 选择与配置

## 本章定位

IDE 是写代码、运行代码和调试代码的工作界面。深度学习入门阶段不需要追求复杂工具链，重点是保证编辑器、Python 解释器、Jupyter 内核和 conda 环境指向同一个项目环境。

推荐组合：

- 学习、实验、逐步观察中间结果：Jupyter Notebook / JupyterLab。
- 写 `.py` 脚本和完整项目：VS Code。
- 大型纯 Python 工程：PyCharm。
- 服务器临时编辑：Vim / Nano。

## 常见工具对比

| 工具 | 类型 | 优势 | 适合场景 | 注意点 |
|---|---|---|---|---|
| Jupyter Notebook | 交互式笔记本 | 分块运行、即时显示结果 | 数据探索、教学演示、快速实验 | 状态容易混乱，不适合大型工程 |
| VS Code | 轻量编辑器 | 插件丰富、解释器切换方便 | 课程项目、脚本开发、Markdown 笔记 | 需要正确安装 Python/Jupyter 插件 |
| PyCharm | 专业 IDE | Python 工程能力强、调试体验完整 | 较大的 Python 项目 | 资源占用较高 |
| Vim | 命令行编辑器 | 轻量、服务器常见 | 远程服务器快速修改文件 | 学习曲线较陡 |

入门阶段建议先掌握 Jupyter + VS Code。前者帮助理解代码执行过程，后者帮助建立真实项目结构。

## Jupyter Notebook 配置

如果使用 Anaconda，Jupyter 通常已经安装。建议在课程环境中显式安装一次，确保当前环境可用：

```bash
conda activate dl-pytorch
conda install jupyter ipykernel
```

启动：

```bash
jupyter notebook
```

浏览器打开后，新建 Notebook，执行：

```python
import sys
import torch

print(sys.executable)
print(torch.__version__)
print(torch.cuda.is_available())
```

`sys.executable` 应指向 `dl-pytorch` 环境中的 Python。如果不是，说明 Jupyter 当前内核选错了。

## 注册 Jupyter 内核

为了在 Jupyter 中清楚选择课程环境，可以注册一个专用内核：

```bash
conda activate dl-pytorch
python -m ipykernel install --user --name dl-pytorch --display-name "Python (dl-pytorch)"
```

之后在 Notebook 的 Kernel 菜单里选择 `Python (dl-pytorch)`。这一步能避免“终端装了 PyTorch，但 Notebook 里 import torch 失败”的常见问题。

## VS Code 安装与插件

安装 VS Code 后，建议安装以下扩展：

- Python（Microsoft）。
- Jupyter（Microsoft）。
- Pylance（Microsoft）。

打开项目时，使用 `File -> Open Folder` 打开课程文件夹，而不是只打开单个 `.py` 文件。这样 VS Code 才能正确识别项目路径、相对导入和工作目录。

## VS Code 选择 Python 解释器

在 VS Code 中按 `Ctrl+Shift+P`，输入并选择：

```text
Python: Select Interpreter
```

选择 `dl-pytorch` 对应的 Python 解释器。如果列表中没有，可以在 Anaconda Prompt 中查询路径：

```bash
conda activate dl-pytorch
where python
```

复制输出的第一个路径，在 VS Code 中手动选择。

验证脚本：

```python
import sys
import torch

print(sys.executable)
print(torch.__version__)
print(torch.cuda.is_available())
```

只要 `sys.executable` 指向当前 conda 环境，VS Code 就使用了正确解释器。

## VS Code 运行 `.py` 文件

新建 `check_env.py`：

```python
import torch

print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
```

在 VS Code 终端中运行：

```bash
python check_env.py
```

如果直接点击右上角运行按钮，也要确认终端环境和右下角解释器一致。调试环境问题时，命令行运行通常更透明。

## VS Code 使用 Notebook

VS Code 可以直接打开 `.ipynb` 文件。打开后注意右上角的 Kernel 选择，确保它是 `Python (dl-pytorch)` 或对应的 conda 环境。

Notebook 适合：

- 分步验证数据处理。
- 画图观察数据分布。
- 演示张量形状变化。

`.py` 脚本适合：

- 保存完整训练流程。
- 复现实验。
- 组织模型、数据集、训练函数等模块。

一个实用习惯是：先在 Notebook 中探索，再把稳定代码整理进 `.py` 文件。

## PyCharm 简要配置

如果使用 PyCharm，创建或打开项目后，在解释器设置中选择已有 conda 环境：

```text
Settings -> Project -> Python Interpreter -> Add Interpreter -> Conda Environment -> Existing
```

选择 `dl-pytorch` 环境下的 `python.exe`。配置完成后，同样用 `import torch` 验证。

## 常见问题

### 终端能导入 torch，VS Code 不能

几乎一定是解释器选错。检查 VS Code 右下角解释器、`Python: Select Interpreter` 和 `sys.executable`。

### Notebook 能运行旧变量，脚本却报错

Notebook 会保留内存状态。调试时使用 `Restart Kernel and Run All`，确认代码从空状态开始也能运行。

### 相对路径找不到数据文件

检查当前工作目录：

```python
import os
print(os.getcwd())
```

脚本读取 `./data/iris.csv` 时，`./` 指的是当前工作目录，不一定是脚本所在目录。项目中更稳妥的做法是用 `pathlib.Path(__file__).parent` 构造路径。

## 本章速记

- 工具选择不复杂：Jupyter 做探索，VS Code 写项目。
- 环境问题优先看 `sys.executable`。
- Notebook 要选择正确 Kernel。
- VS Code 要选择正确 Interpreter。
- 代码、环境、数据路径三者一致，后续训练才稳定。
