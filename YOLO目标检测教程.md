本节内容讲的是：从最开始只有一批图片开始，经过数据标注、数据集划分、环境配置、模型训练，最后得到一个可以进行目标检测的程序。整个流程适合 Windows 10 / Windows 11，尤其照顾配置不高、显卡较弱甚至没有显卡的情况。

## 一、电脑配置与显卡检查

本教程演示环境是一台较老的电脑：CPU 为 E3-1230，内存 16GB，系统为 Windows 10。只要磁盘空间足够，尤其是 C 盘最好保留几十 GB 空闲空间，大多数普通电脑都可以完成本流程。

如果电脑有 NVIDIA 显卡，建议先安装或更新显卡驱动。打开命令提示符，输入：

```
nvidia-smi
```

如果能够显示显卡信息，并且驱动版本大于 580，说明显卡驱动基本可用。如果命令无法识别，或者版本过低，需要到 NVIDIA 官网下载对应显卡型号和系统版本的驱动，按默认选项安装，安装完成后重启电脑，再次运行 `nvidia-smi` 检查。

注意：没有 NVIDIA 显卡也可以继续做，只是训练速度会慢很多，程序仍然可以使用 CPU 运行。

## 二、安装基础工具

本教程需要两个主要软件：

1. Anaconda
2. Visual Studio Code

Python 不需要单独安装，因为 Anaconda 内部会集成 Python 环境。

安装 Anaconda 时，如果想安装到 D 盘，可以把路径最前面的 `C:` 改成 `D:`。安装选项中要勾选第二个选项，使系统命令行能够识别 `conda`。安装完成后，打开新的命令提示符，输入：

```
conda -V
```

如果出现版本号，说明 Anaconda 安装成功。

安装 VS Code 后，需要安装两个插件：

```
Chinese (Simplified)Python
```

其中 Chinese 插件用于中文界面，Python 插件用于运行 Python 程序。

## 三、准备资料包和英文路径

资料包所在文件夹建议改成纯英文名称，路径中尽量不要出现中文。很多深度学习工具、标注工具、训练脚本在中文路径下容易出现奇怪问题。

打开资源管理器中的“查看”，勾选“文件扩展名”，这样可以看到 `.zip`、`.py`、`.txt` 等后缀，便于后续操作。

资料包中一般包含：

```
requirements.txt预下载的安装包数据压缩包YOLO 训练代码预训练权重文件数据集划分脚本
```

如果视频作者已经提前准备好安装包，后续安装依赖时就可以从本地安装，避免网络下载失败。

## 四、创建 YOLO 运行环境

进入包含 `requirements.txt` 的项目文件夹，在命令提示符中切换路径：

```
cd /d 项目文件夹路径
```

检查当前文件夹内容：

```
dir
```

创建新的 Conda 环境：

```
conda create -n uo python=3.12
```

其中 `uo` 是环境名，可以自己改，但后续要保持一致。

创建完成后激活环境：

```
conda activate uo
```

激活成功后，命令行前面会出现类似：

```
(uo)
```

然后安装依赖包。如果资料包中已经有本地安装包，可以使用作者提供的安装命令，一般形式类似：

```
pip install -r requirements.txt --find-links 本地安装包路径
```

这样可以优先从本地文件夹安装依赖，避免因为网络连接国外服务器导致下载失败。

## 五、在 VS Code 中选择正确解释器

打开 VS Code，选择项目文件夹，新建一个测试文件，例如：

```
test.py
```

写入：

```
print("hello")
```

右下角选择 Python 解释器，选择刚才创建的 `uo` 环境。

如果运行时出现 `conda` 无法识别，通常是 VS Code 默认终端使用了 PowerShell。解决方法是把默认终端改成命令提示符：

按下：

```
Ctrl + Shift + P
```

搜索：

```
Terminal: Select Default Profile
```

选择：

```
Command Prompt
```

然后关闭旧终端，重新运行 Python 文件即可。

测试 PyTorch 是否支持显卡：

```
import torchprint(torch.cuda.is_available())
```

如果输出：

```
True
```

说明 NVIDIA 显卡可以被 PyTorch 调用。

如果输出：

```
False
```

说明当前只能使用 CPU，仍然可以运行，只是训练更慢。

## 六、YOLO 标签格式说明

YOLO 目标检测数据通常由两部分组成：

```
images   存放图片labels   存放标签
```

文件夹名称必须严格写成：

```
imageslabels
```

每张图片对应一个 `.txt` 标签文件。例如：

```
0001.jpg0001.txt
```

YOLO 标签文件中每一行表示一个目标，格式为：

```
类别编号 中心点x 中心点y 宽 高
```

例如：

```
2 0.67 0.53 0.64 0.88
```

含义是：

```
2       表示目标类别编号0.67    表示目标框中心点的 x 坐标0.53    表示目标框中心点的 y 坐标0.64    表示目标框宽度0.88    表示目标框高度
```

这里的坐标不是像素值，而是归一化比例，范围通常是 0 到 1。图片左上角是原点，向右为 x 方向，向下为 y 方向。

如果一张图片中有多个物体，就在同一个 `.txt` 文件中写多行。例如一张图里有两只牛和一个人，就会有三行标签。

## 七、使用 LabelImg 标注数据

为了标注图片，需要安装 `labelImg`。建议单独创建一个环境：

```
conda create -n labelimg python=3.9
```

激活环境：

```
conda activate labelimg
```

安装：

```
pip install labelImg
```

如果下载很慢，可以使用清华源：

```
pip install labelImg -i https://pypi.tuna.tsinghua.edu.cn/simple
```

启动标注软件：

```
labelImg
```

打开后操作流程如下：

1. 打开图片文件夹 `images`
2. 设置标签保存文件夹 `labels`
3. 左侧格式切换为 `YOLO`
4. 按 `W` 创建标注框
5. 框选目标物体
6. 输入类别名称
7. 保存
8. 下一张继续标注

注意：LabelImg 中不要乱用鼠标滚轮，有些版本会触发显示 bug。

标注完成后，`labels` 文件夹中会生成很多 `.txt` 文件，并额外生成一个：

```
classes.txt
```

这个文件记录所有类别名称，后面编写 `data.yml` 时会用到。

## 八、整理数据集结构

训练前建议把数据放到项目中的指定目录，例如：

```
dataset_org├── images├── labels└── classes.txt
```

其中：

```
images  存放全部图片labels  存放全部标签classes.txt  存放类别名称
```

然后运行数据集划分脚本，把原始数据划分为：

```
train  训练集val    验证集test   测试集
```

划分完成后会生成类似：

```
dataset├── train│   ├── images│   └── labels├── val│   ├── images│   └── labels└── test    ├── images    └── labels
```

训练集用于让模型学习，验证集用于训练过程中评估效果，测试集用于最终测试模型表现。

## 九、编写 data.yml 文件

`data.yml` 用来告诉 YOLO：

1. 训练集图片在哪里
2. 验证集图片在哪里
3. 测试集图片在哪里
4. 一共有多少类
5. 每一类叫什么名字

格式类似：

```
train: D:/your_project/dataset/train/imagesval: D:/your_project/dataset/val/imagestest: D:/your_project/dataset/test/imagesnc: 10names:  0: cat  1: dog  2: cow  3: fox  4: horse  5: sheep  6: bird  7: person  8: rabbit  9: bear
```

其中 `nc` 表示类别数量，`names` 的顺序必须和 `classes.txt` 中的类别顺序一致，不能乱。

## 十、训练模型

训练脚本一般是 `train.py`。核心代码逻辑是：

```
from ultralytics import YOLOmodel = YOLO("预训练权重路径")model.train(    data="data.yml路径",    epochs=训练轮数,    batch=批大小,    workers=线程数)
```

常见参数含义：

```
data      数据集配置文件 data.ymlepochs    训练轮数batch     一次送入模型训练的图片数量workers   数据加载线程数
```

`batch` 越大，占用显存越多。显卡较弱或内存不足时，可以设置为：

```
batch=4
```

或：

```
batch=8
```

如果显存较大，例如 12GB 或 16GB，可以尝试：

```
batch=32
```

在 Windows 下，如果训练报错，可以把：

```
workers=0
```

有些 Windows 环境中多线程加载数据容易出问题。

## 十一、常见下载文件缺失问题

训练时有时会报错，提示某些 JSON 文件、字体文件下载失败。解决方法是找到用户目录中的 Ultralytics 配置文件夹。

一般路径类似：

```
C:/Users/你的用户名/AppData/Roaming/Ultralytics
```

如果看不到 `AppData`，需要在资源管理器中勾选“隐藏的项目”。

然后把资料包中提供的补充文件，例如 JSON 文件和字体文件，复制到对应目录下，再重新运行训练即可。

## 十二、训练指标怎么看

训练过程中主要关注：

```
mAP50mAP50-95
```

`mAP50` 可以简单理解为：当预测框和真实框重叠程度达到 50% 时，模型预测是否算正确。这个值越高，说明模型检测效果越好。

`mAP50-95` 更严格，它会统计从 50% 到 95% 不同重叠要求下的平均效果，所以通常比 `mAP50` 更低，但更能反映模型质量。

训练过程中指标可能会上下波动，不一定每一轮都上升，但总体趋势应该逐渐提高。

如果只是演示，`mAP50` 达到 50% 到 60% 左右就能看到一定效果；如果想用于实际项目，需要继续训练更久，并提高数据质量。

## 十三、判断显卡是否真的在工作

训练时可以打开新的命令提示符，输入：

```
nvidia-smi
```

查看 GPU 占用率。如果能看到 Python 进程，并且 GPU 利用率较高，说明显卡正在参与训练。

Windows 任务管理器中的 GPU 占用有时不准，尤其默认显示的可能不是 CUDA 计算占用，所以更推荐看 `nvidia-smi`。

## 十四、训练结果在哪里

训练完成或中断后，一般会在项目目录下生成：

```
runs/detect/train
```

其中最重要的是：

```
weights/best.ptweights/last.pt
```

含义如下：

```
best.pt  验证集表现最好的权重last.pt  最后一轮训练得到的权重
```

实际使用时通常优先使用：

```
best.pt
```

## 十五、使用训练好的模型进行检测

检测脚本一般会读取训练好的 `best.pt`，然后对测试集图片进行预测。

示例逻辑：

```
from ultralytics import YOLOmodel = YOLO("runs/detect/train/weights/best.pt")model.predict(    source="dataset/test/images",    save=True)
```

运行后，检测结果通常保存在：

```
runs/detect/predict
```

里面会生成带检测框的图片。

如果训练时间太短，可能会出现漏检、误检，这是正常的。解决方法包括：

```
增加训练轮数提高标注质量增加数据量使用更合适的模型大小调整 batch 和图片尺寸
```

## 十六、完整流程小结

从零开始训练 YOLO 目标检测模型，完整流程是：

```
准备图片↓用 LabelImg 标注数据↓得到 images 和 labels↓检查 YOLO 标签格式↓划分 train / val / test 数据集↓编写 data.yml↓创建 Conda 环境↓安装依赖↓选择 VS Code Python 解释器↓加载预训练权重↓训练模型↓查看 mAP 指标↓得到 best.pt↓运行预测脚本↓输出检测结果图片
```

注意：目标检测训练中最容易出问题的地方通常不是代码，而是环境、路径和数据格式。路径尽量使用英文，图片和标签文件名必须一一对应，`data.yml` 中路径和类别顺序必须正确。