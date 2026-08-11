# 第 15 章 内部 Flash 与芯片标识


## 本章闭环

在程序未占用的最后一个 1 KB 页保存参数，掉电后恢复；同时读取 Flash 容量和 96 位唯一设备 ID。

## 1. 存储布局

![STM32F1 Flash 组织](../assets/ppt/slide-196.png)

STM32F103C8 的程序 Flash 从 `0x08000000` 开始。中容量器件页大小为 1 KB。课程示例使用 `0x0800FC00` 作为 64 KB 空间最后一页的起点，但这个地址只有在链接产物没有占用该页时才安全。

![内部 Flash 基本结构](../assets/ppt/slide-197.png)

在 Keil map 文件中确认程序末地址，并在链接布局中预留存储页。不要只凭“程序看起来很小”猜测地址。

## 2. 解锁、擦除、编程

![Flash 解锁](../assets/ppt/slide-198.png)

标准库调用顺序：解锁 -> 等待空闲 -> 按页擦除 -> 按半字/字编程 -> 检查状态 -> 再锁定。编程只能把位从 1 改为 0；需要从 0 改回 1 时必须擦除整页。

```c
FLASH_Unlock();
FLASH_ClearFlag(FLASH_FLAG_EOP | FLASH_FLAG_PGERR | FLASH_FLAG_WRPRTERR);
FLASH_ErasePage(STORE_START_ADDRESS);
FLASH_ProgramHalfWord(STORE_START_ADDRESS, 0xA5A5);
FLASH_Lock();
```

读取不需要解锁，可通过指针访问：

```c
uint16_t value = *(__IO uint16_t *)address;
```

## 3. 参数存储模式

课程用第一个半字 `0xA5A5` 作为格式标记，其余 511 个半字存数据：上电时从 Flash 加载到 SRAM；修改 SRAM 数据后，保存函数擦除整页并重写全部数据。

![页编程流程](../assets/ppt/slide-200.png)

![页擦除流程](../assets/ppt/slide-201.png)

这种方案适合低频保存的入门实验。Flash 擦写寿命有限，不能在高速循环中每次变量变化都保存。工程中常用脏标志、延迟提交、轮换页、版本号和 CRC，以减少磨损并识别断电中断造成的半写数据。

## 4. 选项字节边界

![选项字节](../assets/ppt/slide-203.png)

选项字节可配置读保护、写保护、硬件看门狗等。误配置可能导致无法调试、全片擦除或启动行为改变。初学阶段只理解用途，不在普通参数实验中修改。

## 5. 芯片容量与 UID

![器件电子签名](../assets/ppt/slide-206.png)

STM32F103 中容量器件可从系统存储区读取 Flash 容量寄存器和 96 位 UID。课程使用：

```c
uint16_t flash_kb = *(__IO uint16_t *)0x1FFFF7E0;
uint32_t uid0 = *(__IO uint32_t *)0x1FFFF7E8;
uint32_t uid1 = *(__IO uint32_t *)0x1FFFF7EC;
uint32_t uid2 = *(__IO uint32_t *)0x1FFFF7F0;
```

地址必须以目标芯片数据手册/参考手册为准，不能把其他 STM32 系列地址照搬。UID 可用于设备识别，不应被当作保密密钥。

## 6. 验收与排错

修改参数并显式保存，断电重启后应恢复；执行清除后应回到默认值。写入失败先查地址、写保护、解锁、状态标志和供电；程序下载后数据消失，检查下载算法是否擦除了保留页；运行一段时间后程序损坏，检查存储页是否与代码区重叠。

## 本章小结

内部 Flash 的关键约束是“读可随机、写先擦除、擦除按页、寿命有限、地址必须预留”。理解这些边界后，才能把示例扩展成可靠的参数存储模块。
