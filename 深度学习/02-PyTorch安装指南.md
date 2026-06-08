# 02 PyTorch 安装指南

## 本章定位

本章完成 PyTorch 的安装与验证。推荐思路是：用 conda 管理 Python 环境，在该环境中按 PyTorch 官网给出的命令安装 PyTorch。这样既能保持环境隔离，又能尽量跟随官方当前支持的安装方式。

> 具体命令可能随 PyTorch 版本更新而变化。实际安装时以 PyTorch 官网 Get Started 页面生成的命令为准。

## 安装前检查

### 确认 Python 环境

先创建并激活课程环境：

```bash
conda create -n dl-pytorch python=3.12
conda activate dl-pytorch
python --version
where python
```

`where python` 输出的第一个路径应位于当前 conda 环境中，而不是系统 Python 或其他项目环境。

### 确认是否需要 GPU 版

PyTorch 可以安装 CPU 版或 GPU 版：

- **CPU 版**：不依赖 NVIDIA 显卡，安装最简单，适合入门、小模型和课程实验。
- **GPU 版**：需要 NVIDIA 显卡和兼容驱动，训练速度更快，适合较大模型和图像任务。

如果只是完成鸢尾花分类、基础 MLP、简单 CNN 学习，CPU 版已经足够。GPU 版主要用于后续更大规模的深度学习实验。

## 检查 NVIDIA GPU 与驱动

如果准备安装 GPU 版，先在终端执行：

```bash
nvidia-smi
```

若命令能显示显卡型号、驱动版本和 CUDA Version，说明 NVIDIA 驱动可用。这里显示的 CUDA Version 表示当前驱动最高兼容的 CUDA 运行时版本，不等于你必须手动安装对应版本的 CUDA Toolkit。

普通 PyTorch pip 安装包通常自带所需 CUDA 运行时组件。多数学习场景只需要安装合适版本的显卡驱动和 PyTorch，不需要单独安装完整 CUDA Toolkit 与 cuDNN。

如果 `nvidia-smi` 不存在或没有 NVIDIA 显卡，直接安装 CPU 版。

## 选择安装命令

进入 PyTorch 官网安装页面，按自己的环境选择：

- PyTorch Build：Stable。
- OS：Windows / Linux / macOS。
- Package：Pip。
- Language：Python。
- Compute Platform：CPU 或某个 CUDA 版本。

官网会生成安装命令。不要凭记忆套旧命令，尤其不要把过时 CUDA 版本写死到笔记或脚本里。

## 安装 CPU 版

在已激活的 conda 环境中执行：

```bash
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

CPU 版适合所有机器，验证代码和课程小项目最稳定。

## 安装 GPU 版

如果 `nvidia-smi` 正常，并且驱动支持官网列出的 CUDA 版本，可以选择 CUDA 版。例如选择 CUDA 12.6 时，命令通常类似：

```bash
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

如果官网当前推荐的是 CUDA 12.8 或其他版本，就使用官网生成的对应命令。

安装 GPU 版时重点检查两件事：

- 显卡必须是 NVIDIA CUDA 设备。
- 驱动版本要足够新，能支持所选 PyTorch CUDA 运行时。

## 安装常用配套库

课程后续会使用 pandas、numpy、matplotlib、scikit-learn、tqdm 和 Jupyter，可在同一环境中安装：

```bash
conda install numpy pandas matplotlib scikit-learn tqdm jupyter
```

如果 conda 解析依赖很慢，也可以改用 pip：

```bash
python -m pip install numpy pandas matplotlib scikit-learn tqdm jupyter
```

同一个环境中尽量避免反复混用多个渠道安装同一批核心库。环境乱了时，新建环境往往比修补更快。

## 验证安装

进入 Python：

```bash
python
```

执行：

```python
import torch

print(torch.__version__)
print(torch.cuda.is_available())
print(torch.version.cuda)
```

含义如下：

- `torch.__version__`：当前安装的 PyTorch 版本。
- `torch.cuda.is_available()`：当前环境是否能调用 CUDA。
- `torch.version.cuda`：当前 PyTorch 包对应的 CUDA 运行时版本；CPU 版通常为 `None`。

CPU 版返回 `False` 是正常的。GPU 版如果返回 `False`，通常需要检查驱动、安装命令、环境解释器是否选错。

也可以做一次张量计算：

```python
x = torch.randn(2, 3)
print(x)

if torch.cuda.is_available():
    x = x.to("cuda")
    print(x.device)
```

## 常见问题

### pip 安装很慢或失败

PyTorch 轮子文件体积较大，网络不稳定时容易失败。优先重试官方命令，必要时更换网络。镜像源可能滞后或缺少 CUDA 包，使用前要确认包来源和版本一致。

### 明明装了 GPU 版，CUDA 仍不可用

按顺序检查：

1. 是否有 NVIDIA 显卡。
2. `nvidia-smi` 是否能运行。
3. 是否在当前 conda 环境中安装了 PyTorch。
4. VS Code/Jupyter 是否选择了同一个解释器。
5. 驱动是否支持所选 CUDA 版本。

### 是否必须安装 CUDA Toolkit

普通 PyTorch 学习和训练通常不需要单独安装完整 CUDA Toolkit。只有在需要编译自定义 CUDA 扩展、使用特定底层库或做 CUDA 开发时，才需要额外安装。

### conda install pytorch 命令还能不能用

旧教程中常见 `conda install pytorch torchvision torchaudio ...`。如果官网仍为你的平台提供 conda 命令，可以按官网来；如果官网当前推荐 pip，就在 conda 环境中用 `python -m pip` 安装 PyTorch。

## 本章速记

- conda 负责环境隔离，PyTorch 安装命令以官网为准。
- 入门优先 CPU 版；有 NVIDIA 显卡且驱动合适再装 GPU 版。
- GPU 版通常只需要 NVIDIA 驱动和 PyTorch CUDA 包，不必手动安装完整 CUDA Toolkit。
- 安装后必须用 `import torch` 和 `torch.cuda.is_available()` 验证。
- 运行代码的解释器必须和安装 PyTorch 的环境一致。
