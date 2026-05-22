# 01 Anaconda环境配置

## 1.1 Anaconda 简介

Anaconda 是一个开源的数据科学平台，专门用于简化机器学习、深度学习等场景下的环境配置与包管理工作。对于刚接触 PyTorch 等深度学习框架的新手来说，Anaconda 是搭建开发环境的首选工具。

在 Python 生态中，数据科学和机器学习项目往往依赖大量的第三方库，如 `numpy`、`pandas`、`scikit-learn` 等。如果手动逐个安装这些库，不仅过程繁琐，而且容易遇到版本冲突问题。Anaconda 的核心定位就是解决这些问题。

## 1.2 Anaconda 的主要特点

### 一站式安装

Anaconda 本身包含了众多常用的科学计算与机器学习库。用户在安装 Anaconda 后，无需再单独下载安装 `numpy`、`pandas`、`scikit-learn` 等库，这些库已经预装在 Anaconda 中，安装完成后可直接导入使用。这避免了入门阶段逐个安装依赖库的重复操作。

### 环境管理

环境管理是 Anaconda 最重要的特性，也是选择它的核心原因。在实际的深度学习学习中，通常不会只做一个项目。不同项目对环境的需求可能存在冲突，例如：

- 项目 A 需要 PyTorch CPU 版本 + Python 3.8
- 项目 B 需要 PyTorch GPU 版本 + Python 3.9

在同一台电脑的同一个 Python 环境中，无法同时存在 PyTorch 的 CPU 和 GPU 版本。如果没有环境管理工具，就只能做完一个项目后清空环境，再配置下一个项目，效率极低。

Anaconda 通过虚拟环境机制解决了这个问题。它能够在计算机的基础环境（base 环境）之上，虚拟出多个相互隔离的独立环境，就像把一个大房间隔成多个独立的小隔间。每个虚拟环境都可以拥有自己独立的 Python 版本和库组合：

```bash
# 创建一个名为 project_a 的新环境，指定 Python 版本
conda create --name project_a python=3.8

# 切换到 project_a 环境
conda activate project_a

# 在该环境中安装 PyTorch CPU 版本
conda install pytorch-cpu

# 创建另一个名为 project_b 的环境
conda create --name project_b python=3.9

# 切换到 project_b 环境
conda activate project_b

# 在该环境中安装 PyTorch GPU 版本
conda install pytorch-gpu
```

这样，一台电脑就可以同时容纳多个项目所需的运行环境，彼此互不干扰。

### 包管理

Anaconda 内置了 `conda` 包管理器，它可以用来安装、更新、删除和管理各种科学计算库。`conda` 类似于 Python 的 `pip`，但功能更强大，尤其擅长处理非 Python 依赖（如 C/C++ 库）的安装。例如，如果需要安装一个在终端显示进度条的 `tqdm` 库，只需在 Anaconda Prompt 中输入：

```bash
conda install tqdm
```

`conda` 会自动将 `tqdm` 及其依赖下载并安装到当前激活的环境中。

### 自带 Jupyter Notebook

Anaconda 还自带了 Jupyter Notebook，这是一个基于 Web 的交互式集成开发环境（IDE）。它的最大优点是能够实时显示当前代码单元格的运行结果，非常适合数据探索、代码调试和学习阶段的实验性编程。用户可以在浏览器中边写代码边看到输出，学习体验直观。

## 1.3 Anaconda 的下载与安装

### 下载

访问 Anaconda 官方网站（anaconda.com），在 Download 页面可以看到支持的操作系统：Windows、macOS 和 Linux。根据自己电脑的操作系统选择对应的版本下载即可。本教程以 Windows 系统为例。

### 安装步骤

下载完成后，双击安装程序运行，按照以下步骤操作：

1. 点击 **Next** 进入下一步
2. 点击 **I Agree** 接受许可协议
3. 选择 **Just Me** 安装模式（为当前用户安装）
4. **切换安装目录**：不建议安装在 C 盘，因为 Anaconda 占用的空间较大，长期使用会影响系统盘性能。建议安装到其他盘符（如 D 盘）。注意：安装目录必须是一个**空目录**，需要提前新建好
5. 后续选项保持默认即可，点击 **Install** 开始安装

整个安装过程大约需要 5 分钟左右，具体时间取决于电脑性能。

## 1.4 安装后的验证

安装完成后，在 Windows 的开始菜单中可以搜索到新安装的 Anaconda 相关程序。常见的组件包括：

- **Anaconda Navigator**：图形化界面的 Anaconda 管理器，初学者可以不使用它
- **Anaconda Prompt**：Anaconda 的命令行交互界面，是后续最常用的工具，可以在其中执行 `conda` 命令
- **Jupyter Notebook**：Web 端编辑器，用于编写和运行 Python 代码

当在开始菜单中看到这些程序时，说明 Anaconda 已经成功安装。

打开 Anaconda Prompt，可以通过以下命令验证安装：

```bash
# 查看 conda 版本
conda --version

# 查看当前环境列表
conda info --envs
```

如果正常输出版本号和环境列表，说明安装和配置已经完成。

## 1.5 常见问题与注意事项

- **安装路径避免中文和空格**：安装 Anaconda 的路径中不要包含中文字符或空格，以免后续某些库出现兼容性问题。
- **安装目录必须是空目录**：Anaconda 安装程序要求目标文件夹为空，否则无法继续。
- **不要安装在 C 盘**：Anaconda 及其创建的环境会占用较大磁盘空间，安装在 C 盘容易导致系统盘空间不足。
- **conda 命令找不到**：如果在普通命令行中无法识别 `conda` 命令，请使用 Anaconda Prompt，它已自动配置好环境变量。
- **不要同时安装 Miniconda 和 Anaconda**：两者功能重复，选择一个即可。Miniconda 是 Anaconda 的轻量版，仅包含 conda 和 Python，需要用户自行安装其他库。
