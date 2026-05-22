# 02 PyTorch安装指南

## 安装前提：Anaconda

安装 PyTorch 之前需要先完成 Anaconda 的安装。Anaconda 是一个 Python 发行版，自带包管理器 `conda`，用于管理 Python 环境和第三方库。安装完成后，可以通过 Anaconda 提供的命令行界面创建虚拟环境，并在其中安装 PyTorch。

## PyTorch 官网与版本选择

在 PyTorch 官网（[pytorch.org](https://pytorch.org)）的安装页面中，提供了多种版本的配置选项。用户需要根据自己的操作系统（Windows / Linux / Mac）、包管理器（pip / conda）、计算平台（CPU / GPU）以及 PyTorch 版本（Stable / Preview）进行选择。

### CPU 版本与 GPU 版本

PyTorch 的 CPU 版本和 GPU 版本针对不同的硬件设计：

- **CPU 版本**：计算依赖于中央处理器（CPU），适合模型较小、数据集不大的项目。当项目规模较小时，CPU 的训练速度是可以接受的。
- **GPU 版本**：计算依赖于图形处理器（GPU，即显卡），利用 GPU 的并行计算能力对模型训练进行加速。当训练复杂的大模型或处理大规模数据时，GPU 版本能显著提高训练速度。

### CUDA 版本选择

在 GPU 版本的配置选项中，会列出不同的 CUDA 版本号（如 CUDA 11.7、CUDA 11.8），具体安装哪一个取决于电脑中显卡驱动的版本。CUDA 是 NVIDIA 推出的并行计算平台，PyTorch 的 GPU 版本需要借助 CUDA 来调用 GPU 进行计算。

## 检查硬件环境

### 确认显卡型号

通过任务管理器可以查看电脑是否配备 NVIDIA 显卡：右键任务栏 -> 任务管理器 -> 性能选项卡，可以看到 GPU 项及其型号。**只有 NVIDIA 品牌的显卡才支持 GPU 版本的 PyTorch**，Intel、AMD 等厂商的显卡不支持。

### 确认驱动版本与 CUDA 兼容性

打开 NVIDIA 控制面板 -> 帮助 -> 系统信息，可以查看到当前显卡驱动的版本号。前往 NVIDIA 官网的驱动兼容性列表，对照驱动版本号可以确定支持哪些 CUDA 版本。驱动版本向下兼容 CUDA——即高版本驱动可以支持低版本 CUDA，但低版本驱动无法支持高版本 CUDA。

如果当前驱动版本过旧，不在兼容列表中，有两种解决方案：
1. 前往 NVIDIA 官网升级显卡驱动。
2. 放弃 GPU 版本，直接安装 CPU 版本。

## 创建 conda 虚拟环境

Anaconda 安装完成后，打开 Anaconda Prompt（命令行界面），默认处于 `base` 基础环境。建议为 PyTorch 单独创建一个虚拟环境，避免与其它项目的依赖冲突。

创建虚拟环境的命令：

```bash
conda create -n pytorch_cpu
```

其中 `-n` 参数后跟环境名称，可按需命名（如 `pytorch_cpu`、`pytorch_gpu`）。

创建完成后，可以用以下命令查看当前所有的 conda 环境：

```bash
conda info -e
```

列表中包含 `base` 环境（安装 Anaconda 时自动创建）以及新创建的虚拟环境。

激活虚拟环境：

```bash
conda activate pytorch_cpu
```

激活后，命令行提示符前的 `(base)` 会变为 `(pytorch_cpu)`，表示当前已进入该虚拟环境。

## 安装 CPU 版本

激活虚拟环境后，在 PyTorch 官网选择对应配置（PyTorch 2.0、Windows、Conda、Python、CPU），官网会生成对应的安装命令。将命令复制到命令行中执行：

```bash
conda install pytorch torchvision torchaudio cpuonly
```

执行后，conda 会自动解析并下载 PyTorch 及其依赖库，输入 `y` 确认安装即可。

### 安装失败的处理

PyTorch 的安装资源存储在海外服务器，国内访问可能存在网络延迟，导致安装失败。三个常用解决办法：

1. **切换网络环境**：如从无线切换为有线，或使用手机热点重试，通常多试几次即可成功。
2. **换源**（更换国内镜像源）：将 conda 的默认下载地址从国外服务器切换至国内镜像，可以大幅提升下载速度。但 PyTorch 官方文档不推荐换源，因为可能引入兼容性问题。
3. **科学上网**：通过代理工具提升下载稳定性。

## 安装 GPU 版本

### CUDA 与 cuDNN 准备

GPU 版本需要提前确认驱动支持的 CUDA 版本。通过 NVIDIA 控制面板获取驱动版本后，对照兼容性列表选择合适的 CUDA 版本。安装 GPU 版本 PyTorch 时，官网命令中需要指定对应的 CUDA 版本号。

### 安装步骤

新建一个虚拟环境（如 `pytorch_gpu`），激活后，在官网选择 GPU 对应配置（如 CUDA 11.8），获取命令并执行：

```bash
conda install pytorch torchvision torchaudio pytorch-cuda=11.8
```

安装过程与 CPU 版本相同，conda 会自动处理依赖。

### pip 安装方式（备选）

除 conda 外，也可以用 pip 安装 PyTorch。PyTorch 官网同样提供了 pip 安装命令，以 CPU 版本为例：

```bash
pip install torch torchvision torchaudio
```

pip 安装更轻量，但需要手动处理 CUDA 驱动和 cuDNN 等底层依赖。conda 会一并处理这些非 Python 依赖，而 pip 只负责 Python 包本身，因此 conda 通常是更省心的选择。

## 验证安装

安装完成后，在对应的虚拟环境中依次执行以下验证步骤。

### 导入 PyTorch

```python
python
>>> import torch
```

如果没有报错，说明 PyTorch 已成功安装。

### 检查 CUDA 可用性

```python
>>> torch.cuda.is_available()
```

- CPU 版本返回 `False`。
- GPU 版本如果安装正确且驱动兼容，返回 `True`，表示 CUDA 可用，PyTorch 可以调用 GPU 进行计算。

### 退出虚拟环境

```bash
conda deactivate
```

执行后命令行提示符回到 `(base)`，表示已退出当前虚拟环境。
