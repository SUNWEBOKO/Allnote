# 01 Anaconda 环境配置

## 本章定位

深度学习项目最容易卡住的地方不是模型代码，而是环境。Python 版本、PyTorch 版本、CUDA 版本和第三方库版本只要有一处不匹配，就可能导致代码无法运行。本章的目标是用 Anaconda/conda 建立一个可隔离、可复现、可验证的 Python 环境。

## Anaconda 与 conda 的关系

Anaconda 是一个面向数据科学的 Python 发行版，包含 Python、conda 包管理器以及一批常用科学计算库。conda 是它最重要的工具，负责创建虚拟环境、安装包、解决依赖冲突。

需要区分三个概念：

- **Anaconda Distribution**：体积较大的完整发行版，预装许多数据科学库，适合入门。
- **Miniconda**：轻量版本，只包含 Python 和 conda，需要什么库再自己安装。
- **conda 环境**：由 conda 创建的隔离 Python 环境，每个环境可以有独立的 Python 版本和依赖库。

入门阶段用 Anaconda 更省心；熟悉后也可以换成 Miniconda，原理完全一致。

## 为什么必须使用虚拟环境

不同项目经常需要不同版本的依赖。例如一个旧项目可能要求 Python 3.9，新的 PyTorch 项目可能要求 Python 3.12；一个项目只需要 CPU 版 PyTorch，另一个项目需要 CUDA 版 PyTorch。把所有库都装进 `base` 环境，很快会造成版本冲突。

正确做法是：`base` 只作为管理入口，不直接做项目开发。每个项目单独创建环境。

示例：

```bash
conda create -n dl-pytorch python=3.12
conda activate dl-pytorch
```

上面命令创建了一个名为 `dl-pytorch` 的环境，并指定 Python 版本为 3.12。后续安装 PyTorch、Jupyter、pandas、scikit-learn 等库，都应在激活该环境后执行。

## 下载与安装 Anaconda

进入 Anaconda 官方下载页面，根据操作系统选择对应安装包。本课程以 Windows 为例。

安装时建议遵守以下规则：

- 安装路径尽量不要包含中文、空格或特殊符号。
- 可以安装在非系统盘，但不要选择过深、过复杂的目录。
- 目标目录应为空目录。
- Windows 上不建议手动把 Anaconda 添加到全局 PATH；优先使用 Anaconda Prompt 或 Anaconda PowerShell Prompt。
- 安装模式通常选择 **Just Me**，除非确实需要给所有系统用户安装。

安装完成后，在开始菜单中应能看到：

- Anaconda Prompt。
- Anaconda PowerShell Prompt。
- Anaconda Navigator。
- Jupyter Notebook。

日常学习主要使用 Anaconda Prompt 或 Anaconda PowerShell Prompt，Navigator 可以暂时不用。

## 验证安装

打开 Anaconda Prompt，依次执行：

```bash
conda --version
conda info --envs
```

如果能看到 conda 版本号和环境列表，说明安装成功。环境列表中默认会有一个 `base` 环境。

也可以检查 Python 位置：

```bash
where python
python --version
```

在激活不同 conda 环境后，`where python` 输出的第一个路径应随环境变化。这一点对后续 VS Code 解释器选择非常重要。

## 常用 conda 命令

### 创建环境

```bash
conda create -n dl-pytorch python=3.12
```

### 激活环境

```bash
conda activate dl-pytorch
```

激活成功后，命令行前缀会从 `(base)` 变成 `(dl-pytorch)`。

### 查看环境列表

```bash
conda info --envs
```

带星号 `*` 的环境是当前激活环境。

### 安装常用包

```bash
conda install numpy pandas scikit-learn matplotlib jupyter
```

也可以在 conda 环境中使用 `pip`，例如安装 PyTorch 官方 pip 包：

```bash
python -m pip install torch torchvision torchaudio
```

推荐写成 `python -m pip`，这样可以确保 `pip` 对应的是当前激活环境中的 Python。

### 退出环境

```bash
conda deactivate
```

### 删除环境

```bash
conda remove -n dl-pytorch --all
```

删除前确认没有重要代码或数据放在环境目录中。项目文件应放在独立工作目录，而不是放进 conda 环境内部。

## 推荐的学习环境结构

建议把“项目代码”和“Python 环境”分开：

```text
D:\code\deep-learning-course\     # 项目代码、笔记、数据
D:\anaconda\envs\dl-pytorch\      # conda 环境，由 conda 管理
```

不要把代码写进 `envs` 目录，也不要手动修改环境目录下的库文件。

## 常见问题

### 找不到 conda 命令

优先使用开始菜单里的 Anaconda Prompt。如果一定要在普通 PowerShell 中使用 conda，需要先执行 conda 初始化，但入门阶段没必要折腾。

### base 环境是否可以直接开发

不建议。`base` 环境越干净，后续维护越轻松。课程项目建议使用独立环境，例如 `dl-pytorch`。

### conda 和 pip 能不能混用

可以，但要有顺序：先用 conda 安装通用科学计算库，再用 pip 安装官方只推荐 pip 的包。混用后如果环境冲突严重，通常新建环境比原地修复更快。

### 是否必须安装 Anaconda

不是。Miniconda、Miniforge、uv、普通 Python + venv 都可以管理环境。本课程选择 Anaconda，是因为它对初学者更直观，也方便配合 Jupyter 使用。

## 本章速记

- 不要在 `base` 环境中堆项目依赖。
- 每个项目单独创建 conda 环境。
- 安装包前先确认已经 `conda activate` 到目标环境。
- 用 `where python` 检查当前解释器路径。
- 项目文件和环境目录分开放置。
