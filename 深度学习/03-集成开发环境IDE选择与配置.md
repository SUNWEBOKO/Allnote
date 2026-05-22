# 03 集成开发环境IDE选择与配置

## IDE 的概念与作用

IDE（Integrated Development Environment，集成开发环境）是用于编写代码的编辑平台。它将代码编辑、调试、运行等开发过程中所需的工具集成在一个图形化界面中，帮助开发者提高开发效率。通俗地说，IDE 就是程序员编写代码的工作台。

## 四款主流 IDE 介绍与对比

当下主流的 IDE 有四款：`Jupyter Notebook`、`VS Code`、`PyCharm` 和 `Vim`。它们在定位、功能和适用场景上各有侧重。

### Jupyter Notebook

`Jupyter Notebook` 是基于网页端的交互式开发环境，最大的特点是能够实时返回每一行代码的运行结果。这种"所见即所得"的方式非常适合数据分析和语言入门学习场景，例如分析 Excel 表格、处理数据，以及在初学阶段逐行验证代码行为。

不过，由于每运行一个单元格都会保留中间状态，`Jupyter Notebook` 在组织和管理大型项目时并不方便。它的代码文件结构松散，缺乏模块化管理机制，因此不推荐用于大型工程的开发。

### VS Code

`VS Code`（Visual Studio Code）是微软开发的开源轻量级编辑器。它的核心优势在于拥有一个极其庞大的插件生态系统。通过安装插件，可以扩展支持几乎所有主流编程语言（C++、Java、Python 等），甚至可以实现 Markdown 写作、PDF 编辑、PPT 制作等非编程功能。

`VS Code` 本身只提供编辑基础功能，不内置任何语言的编译或运行环境，一切功能都通过插件按需装配。这种"内核轻量、能力插件化"的设计使得 `VS Code` 既能胜任简单的脚本编辑，也能应对大型项目的开发需求。此外，`VS Code` 提供完善的代码提示（IntelliSense）功能——在输入 API 名称时自动弹出补全建议，无需完全记忆函数签名。

### PyCharm

`PyCharm` 是 JetBrains 公司专门为 Python 语言打造的专业级 IDE。它内置了强大的代码编辑、调试（Debug）、重构等高级功能，安装后可直接使用。`PyCharm` 分为社区免费版（Community Edition）和专业付费版（Professional Edition）。

专业版提供了远程连接服务器等高级功能，这些功能在 `VS Code` 中可以通过免费插件实现。`PyCharm` 的定位是面向专业 Python 开发者的全功能 IDE。

### Vim

`Vim` 是一款经典的文本编辑器，以高度可定制和强大的键盘操作能力著称。它拥有大量的快捷键和命令，可以在完全不使用鼠标的情况下完成全部编辑操作。`Vim` 尤其适用于 macOS 和 Linux 操作系统，在服务器环境中使用非常普遍——因为服务器通常没有图形化界面（桌面环境），只能通过命令行交互，而 `Vim` 纯键盘操作的特点恰好与此完美匹配。

### 对比总结

| 特性 | Jupyter Notebook | VS Code | PyCharm | Vim |
|------|-----------------|---------|---------|-----|
| 类型 | 交互式笔记本 | 轻量级编辑器 | 专业级 IDE | 文本编辑器 |
| 界面 | 网页端 | 桌面 GUI | 桌面 GUI | 命令行 |
| 代码提示 | 无 | 有（丰富） | 有 | 有限 |
| 费用 | 免费 | 免费 | 社区版免费/专业版付费 | 免费 |
| 主要场景 | 数据分析、入门学习 | 通用开发 | Python 专业开发 | 服务器端编辑 |

## 如何选择适合自己的 IDE

对于刚入门的同学，推荐的组合是 `Jupyter Notebook` + `VS Code` 配合使用。初期做数据分析、语言学习时，可以使用 `Jupyter Notebook` 逐行运行代码，实时观察输出，加深对语法的理解。入门之后转向大型项目开发时，切换到 `VS Code`，利用其丰富的插件和代码提示功能提高开发效率。这两者配合几乎可以覆盖日常 90% 的开发需求。

## 安装与基本配置

### Jupyter Notebook 的安装与启动

`Jupyter Notebook` 已被集成在 `Anaconda` 中，无需单独下载。安装 Anaconda 后即可在开始菜单中找到并启动 `Jupyter Notebook`。

启动后会自动弹出网页编辑界面。需要注意：**后台的命令行窗口是 Jupyter Notebook 的运行内核，不能关闭**，否则网页端将无法正常工作。

在网页界面中，点击 `New` → `Python 3` 即可新建一个 Python 脚本，在单元格中输入代码后点击 `Run` 运行：

```python
A = 1 + 2
print(A)
```

```python
import torch
```

如果需要在特定虚拟环境中使用 `Jupyter Notebook`，需要先激活该虚拟环境，然后通过 `conda` 安装：

```bash
conda activate pytorch_gpu
conda install jupyter notebook
```

安装完成后，在该虚拟环境中启动的 `Jupyter Notebook` 使用的就是对应虚拟环境的 Python 内核和依赖库。

### VS Code 的安装与基本配置

从官网下载对应操作系统的安装包（支持 Windows、Linux、macOS）。安装时有几点建议：

- 不建议安装在 C 盘，以免拖慢系统
- 推荐勾选"添加到资源管理器上下文菜单"和"添加到 PATH（环境变量）"选项
- 不建议勾选"注册为支持的文件类型的默认编辑器"，以保留文件的多种打开方式

安装完成后首次打开是一个空白界面，通过 `File` → `Open Folder` 选择工作目录（如 `D:\code`），目录中的文件会显示在侧边栏。

由于 `VS Code` 本身不包含编程语言支持，需要手动安装插件。以 Python 为例：

1. 点击左侧扩展图标（或按 `Ctrl+Shift+X`）
2. 搜索 `Python`，安装第一个结果（由 Microsoft 发布）
3. 新建一个 `.py` 文件即可开始编写代码

在 `VS Code` 中运行 Python 代码的结果会显示在终端（Terminal）中：

```python
A = 1 + 2
print(A)  # 输出 3
```

```python
import torch
print(torch.cuda.is_available())  # 输出 False（base 环境为 CPU 版本）
```

### VS Code 中切换 Python 解释器

`VS Code` 默认使用 Anaconda base 环境中的 Python 解释器。如果 base 环境的 PyTorch 是 CPU 版本（如 1.12），则 `torch.cuda.is_available()` 会返回 `False`。要使用 GPU 版本的 PyTorch，需要切换到对应的虚拟环境解释器：

1. 点击 VS Code 右下角的 Python 版本标识（如 `Python 3.x ('base': conda)`）
2. 选择或输入目标虚拟环境的 Python 解释器路径

如果记不住虚拟环境的路径，可以在 Anaconda Prompt 中通过以下命令查找：

```bash
conda activate pytorch_gpu
where python
```

输出的第一个路径即为该虚拟环境的 Python 解释器位置（如 `D:\anaconda\envs\pytorch2.0\python.exe`），将其配置到 VS Code 中即可正常调用 GPU 版本 PyTorch。
