# 09 RLC串联电路的谐振

## 1. 核心主线

串联谐振题抓四件事：

1. 写阻抗：
   $$
   Z(\omega)=R+j\left(\omega L-\frac1{\omega C}\right)
   $$
2. 判状态：比较 $\omega$ 与 $\omega_0$，判断容性、感性、纯阻性。
3. 用谐振结论：电源电压固定时，谐振点 $Z_{min}=R$，$I_{max}=U_s/R$。
4. 算品质因数：
   $$
   Q=\frac{\omega_0L}{R}
   $$
   谐振时 $U_L=U_C=QU_s$。

本节默认线性时不变电路、理想元件参数固定、正弦稳态。

**先备知识**：第 5 章的阻抗、导纳与复功率概念；第 8 章的"逐频率分析"思想（谐振就是一次谐波频率扫描的特例）。

## 2. 输入阻抗与谐振条件

RLC 串联电路中：

$$
Z_R=R,
\qquad
Z_L=j\omega L,
\qquad
Z_C=\frac1{j\omega C}=-j\frac1{\omega C}
$$

总阻抗：

$$
Z(\omega)=R+j\omega L-j\frac1{\omega C}
$$

$$
Z(\omega)=R+j\left(\omega L-\frac1{\omega C}\right)
$$

其中 $R$ 表示耗能，虚部表示电感与电容共同形成的电抗。随频率升高，$\omega L$ 增大，$1/(\omega C)$ 减小。

谐振条件是总阻抗虚部为零：

$$
\omega L-\frac1{\omega C}=0
$$

$$
\omega L=\frac1{\omega C}
$$

$$
\omega^2LC=1
$$

所以

$$
\omega_0=\frac1{\sqrt{LC}}
$$

$$
f_0=\frac{\omega_0}{2\pi}=\frac1{2\pi\sqrt{LC}}
$$

理想串联谐振频率只由 $L,C$ 决定，$R$ 影响电流峰值、品质因数和损耗，不改变谐振频率。

## 3. 谐振状态与感容判断

一般判断谐振：端口电压与端口电流同相，或输入阻抗为纯电阻。

串联 RLC 在 $\omega=\omega_0$ 时：

$$
Z(\omega_0)=R
$$

此时电路呈纯阻性。

定义

$$
X(\omega)=\omega L-\frac1{\omega C}
$$

则：

- $\omega<\omega_0$：$X<0$，整体呈容性，电流超前电压。
- $\omega=\omega_0$：$X=0$，整体呈纯阻性，电压电流同相。
- $\omega>\omega_0$：$X>0$，整体呈感性，电流滞后电压。

## 4. 谐振时电流、电压与功率

阻抗模：

$$
|Z(\omega)|=\sqrt{R^2+\left(\omega L-\frac1{\omega C}\right)^2}
$$

谐振时虚部为零，阻抗最小：

$$
|Z|_{min}=R
$$

电源电压有效值 $U_s$ 固定时：

$$
I_{max}=\frac{U_s}{R}
$$

谐振时 $L,C$ 对外串联总阻抗为零：

$$
Z_L+Z_C=j\omega_0L-j\frac1{\omega_0C}=0
$$

但这不表示 $U_L=0$ 或 $U_C=0$。以电流为参考：

$$
\dot U_L=j\omega_0L\dot I
$$

$$
\dot U_C=-j\frac1{\omega_0C}\dot I
$$

谐振时

$$
|\dot U_L|=|\dot U_C|,
\qquad
\dot U_L+\dot U_C=0
$$

因此电感、电容各自电压可能很大，只是相量相消。

电源只向整个 RLC 网络提供有功功率：

$$
P=I^2R=\frac{U_s^2}{R}
$$

电感吸收正无功：

$$
Q_L=I^2\omega_0L
$$

电容吸收负无功：

$$
Q_C=-I^2\frac1{\omega_0C}
$$

谐振时 $Q_L+Q_C=0$，电源与整个网络无净无功交换，但 $L,C$ 内部仍交换能量。

## 5. 品质因数与电压放大

谐振时

$$
I=\frac{U_s}{R}
$$

电感电压：

$$
U_L=I\omega_0L=U_s\frac{\omega_0L}{R}
$$

定义品质因数：

$$
Q=\frac{\omega_0L}{R}
$$

所以

$$
U_L=QU_s
$$

同理

$$
U_C=QU_s
$$

等价形式：

$$
Q=\frac{\omega_0L}{R}=\frac1{\omega_0CR}=\frac1R\sqrt{\frac LC}
$$

$Q$ 是无量纲品质因数，不是无功功率。$R$ 越小，损耗越小，$Q$ 越大，谐振时元件电压放大越明显。高 $Q$ 可用于选频和电压放大，也可能导致过电压风险。

实验确定谐振频率和 $Q$：固定 $U_s$，扫频找电流最大点；该频率为 $\omega_0$；在谐振点测 $U_L$ 或 $U_C$，用

$$
Q=\frac{U_L}{U_s}=\frac{U_C}{U_s}
$$

## 6. 谐振曲线与通频带

固定 $U_s$，电流有效值随频率的变化关系

$$
I(\omega)=\frac{U_s}{\sqrt{R^2+\left(\omega L-\frac1{\omega C}\right)^2}}
$$

称为串联谐振曲线。把它写成相对形式，用 $Q$ 和失谐量 $\left(\frac{\omega}{\omega_0}-\frac{\omega_0}{\omega}\right)$ 表示：

$$
\frac{I}{I_{max}}=\frac1{\sqrt{1+Q^2\left(\frac{\omega}{\omega_0}-\frac{\omega_0}{\omega}\right)^2}}
$$

其中 $I_{max}=U_s/R$。$Q$ 越大，曲线在 $\omega_0$ 附近越尖锐，选频性能越好。

工程上取电流下降到 $I_{max}/\sqrt2$（即功率减半）的两个频率 $\omega_1,\omega_2$ 作为边界，定义**通频带**：

$$
BW=\omega_2-\omega_1=\frac{\omega_0}{Q}
$$

三者关系一目了然：$\omega_0$ 定中心，$Q$ 定尖锐度，$BW$ 定带宽，且 $Q$ 与 $BW$ 成反比——选频性和带宽是一对矛盾。

## 7. 谐振的应用与过电压风险

应用侧：收音机选台、滤波器、小信号调谐放大，都是利用"谐振支路对目标频率呈现极值"这一特性——串联谐振支路对该频率近乎短路（电流最大），配合第 8 章逐频率分析即可设计选频电路。

风险侧：串联谐振时 $U_L=U_C=QU_s$。若 $Q\gg1$，电感和电容上的电压可能远超电源电压，威胁元件绝缘与耐压。电力系统中要避免意外串联谐振（如断路器电容与线路电感配合），而无线电电路则刻意追求高 $Q$。同一公式，两种用途，判断依据是看 $Q$ 大小和耐压裕量。

## 8. 能量交换

电感、电容储能：

$$
w_L=\frac12Li^2,
\qquad
w_C=\frac12Cu_C^2
$$

谐振时 $L,C$ 之间不断交换能量，总储能保持不变：

$$
w=w_L+w_C=\text{常数}
$$

以电流为参考，电容电压相对电流滞后 $90^\circ$。当电流最大时，电容电压为零，储能全在电感中。

电流有效值

$$
I=\frac{U_s}{R}
$$

最大值

$$
I_m=\sqrt2I
$$

总储能：

$$
w=\frac12LI_m^2=LI^2=L\left(\frac{U_s}{R}\right)^2=\frac{LU_s^2}{R^2}
$$

又因

$$
Q^2=\frac{L}{CR^2}
$$

可写为

$$
w=CQ^2U_s^2
$$

$Q$ 越大，谐振时内部往复交换的储能越大。

## 9. 例题：求谐振频率、品质因数和元件电压

已知

$$
U_s=0.1\text{ V},
\quad
R=1\Omega,
\quad
L=2\mu\text{H},
\quad
C=200\text{ pF}
$$

测得

$$
I=0.1\text{ A}
$$

先判：

$$
\frac{U_s}{R}=0.1\text{ A}
$$

与题给电流一致，说明处于串联谐振。

$$
\omega_0=\frac1{\sqrt{LC}}
=\frac1{\sqrt{(2\times10^{-6})(200\times10^{-12})}}
=5\times10^7\text{ rad/s}
$$

$$
f_0=\frac{\omega_0}{2\pi}
\approx7.96\times10^6\text{ Hz}=7.96\text{ MHz}
$$

$$
Q=\frac{\omega_0L}{R}
=(5\times10^7)(2\times10^{-6})=100
$$

$$
U_L=U_C=QU_s=100\times0.1=10\text{ V}
$$

若以电流为参考：

$$
\dot U_L=j10\text{ V},
\qquad
\dot U_C=-j10\text{ V}
$$

结果：

$$
\boxed{\omega_0=5\times10^7\text{ rad/s}},
\quad
\boxed{f_0\approx7.96\text{ MHz}},
\quad
\boxed{Q=100},
\quad
\boxed{U_L=U_C=10\text{ V}}
$$

## 10. 高频易错点

| 错因 | 纠偏 |
|---|---|
| 把 LC 总电压为零理解成各自电压为零 | 写相量关系 $\dot U_L=-\dot U_C$，有效值可很大 |
| 混淆品质因数 $Q$ 和无功功率 $Q$ | 品质因数无量纲，无功功率单位 var |
| 误以为 $\omega_0$ 由 $R$ 决定 | 理想串联 $\omega_0=1/\sqrt{LC}$，$R$ 影响峰值与 $Q$ |
| 判感/容只看是否有 L/C | 必须看 $X(\omega)=\omega L-1/(\omega C)$ 的符号 |
| 把负荷大写成阻抗大 | 固定电压下 $P=U^2/R$，负荷大常对应阻抗小 |

## 11. 速记

$$
Z(\omega)=R+j\left(\omega L-\frac1{\omega C}\right)
$$

$$
\omega_0L=\frac1{\omega_0C},
\qquad
\omega_0=\frac1{\sqrt{LC}},
\qquad
f_0=\frac1{2\pi\sqrt{LC}}
$$

$$
\omega<\omega_0\Rightarrow\text{容性},
\quad
\omega=\omega_0\Rightarrow\text{纯阻性},
\quad
\omega>\omega_0\Rightarrow\text{感性}
$$

$$
Z_{min}=R,
\qquad
I_{max}=\frac{U_s}{R}
$$

$$
Q=\frac{\omega_0L}{R}=\frac1{\omega_0CR}=\frac1R\sqrt{\frac LC}
$$

$$
U_L=U_C=QU_s,
\qquad
\dot U_L+\dot U_C=0
$$

$$
\frac{I}{I_{max}}=\frac1{\sqrt{1+Q^2\left(\frac{\omega}{\omega_0}-\frac{\omega_0}{\omega}\right)^2}},
\qquad
BW=\omega_2-\omega_1=\frac{\omega_0}{Q}
$$

谐振时电源只向电阻提供有功功率，电感与电容之间进行内部无功和储能交换。$Q$ 大则选频好、带宽窄，但元件过电压风险也高。

## 12. 自测题

1. $L=1\mu\text{H}$、$C=100\text{ pF}$ 的串联电路，求 $\omega_0$ 和 $f_0$。
2. 谐振后把 $R$ 减小一半，$I_{max}$、$Q$、$U_L$ 各怎样变化？
3. 某调谐回路 $f_0=1\text{ MHz}$、$Q=50$，通频带多大？
4. 为什么"串联谐振是短路"这种说法只在特定意义下成立？

**答案要点**：

1. $\omega_0=1/\sqrt{LC}=10^8\text{ rad/s}$，$f_0\approx15.9\text{ MHz}$。
2. 三者都加倍：$I_{max}=U_s/R$，$Q=\omega_0L/R$，$U_L=QU_s$。
3. $BW=f_0/Q=20\text{ kHz}$。
4. 谐振时只有 $L$、$C$ 的串联组合呈零阻抗，端口总阻抗仍是 $R$；元件各自电压可达 $QU_s$，并非整个电路短路。
