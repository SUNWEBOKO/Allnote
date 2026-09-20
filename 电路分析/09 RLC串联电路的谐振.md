# 09 RLC串联电路的谐振

上一篇：[[08 非正弦周期电路]] ｜ 下一篇：[[10 非线性元器件与小信号分析]]

## 学习目标

1. 写出串联 RLC 的输入阻抗。
2. 解出谐振角频率 $\omega_0$ 与谐振频率 $f_0$。
3. 判断给定频率下电路呈容性、纯阻性还是感性。
4. 计算谐振时的电流、品质因数与元件电压 $U_L=U_C=QU_s$。
5. 由谐振曲线求半功率频率、通频带与元件电压峰值频率。

## 1. 核心主线

串联 RLC 电路的电抗随频率变化。当感抗与容抗相等时，二者在端口上相互抵消，电路发生串联谐振。本章围绕以下四个问题展开：

1. 写阻抗：
   $$
   Z(\omega)=R+j\left(\omega L-\frac1{\omega C}\right)
   $$
2. 判状态：比较 $\omega$ 与 $\omega_0$，判断容性、感性、纯阻性。
3. 用谐振结论：电源电压固定时，谐振点 $Z_{\min}=R$，$I_{\max}=U_s/R$。
4. 算品质因数：
   $$
   Q=\frac{\omega_0L}{R}
   $$
   谐振时 $U_L=U_C=QU_s$。

本节默认线性时不变电路、理想元件参数固定、正弦稳态，并沿用第 5 章的阻抗、相量与复功率概念，把第 8 章的逐频率阻抗计算推广到激励频率连续变化的情形。

![[img/电路分析-09-串联谐振.svg]]

读图：$R$、$L$、$C$ 串在同一条回路上，四个元件共用同一个电流，所以它们的电压相量可以直接相加；电源上端为电压正参考端，各元件电压取电流流入端为正。这里 $R>0$ 且已计入全部串联损耗；讨论电流峰值时保持电源有效值不随频率改变。若改用理想电流源固定回路电流，就不能再套用“扫频时电流在谐振处最大”的实验判据。

## 2. 输入阻抗与谐振条件

RLC 串联电路中：

$$
Z_R=R,
\qquad
Z_L=j\omega L,
\qquad
Z_C=\frac1{j\omega C}=-j\frac1{\omega C}
$$

三者串联，总阻抗为

$$
Z(\omega)=R+j\left(\omega L-\frac1{\omega C}\right)
$$

实部 $R$ 表示耗能，虚部表示电感与电容共同形成的电抗。随频率升高，$\omega L$ 增大、$1/(\omega C)$ 减小。

谐振的条件是总阻抗虚部为零：

$$
\omega L-\frac1{\omega C}=0
\;\Longrightarrow\;
\omega L=\frac1{\omega C}
\;\Longrightarrow\;
\omega^2LC=1
$$

所以谐振角频率与谐振频率为

$$
\omega_0=\frac1{\sqrt{LC}},
\qquad
f_0=\frac{\omega_0}{2\pi}=\frac1{2\pi\sqrt{LC}}
$$

理想串联谐振频率只由 $L,C$ 决定；$R$ 影响电流峰值、品质因数和损耗，不改变谐振频率。

## 3. 谐振状态与感容判断

一般判断谐振：端口电压与端口电流同相，或输入阻抗为纯电阻。

串联 RLC 在 $\omega=\omega_0$ 时 $Z(\omega_0)=R$，电路呈纯阻性。偏离谐振点时，用

$$
X(\omega)=\omega L-\frac1{\omega C}
$$

的符号判断电路性质：

- $\omega<\omega_0$：$X<0$，整体呈容性，电流超前电压。
- $\omega=\omega_0$：$X=0$，整体呈纯阻性，电压电流同相。
- $\omega>\omega_0$：$X>0$，整体呈感性，电流滞后电压。

## 4. 谐振时电流、电压与功率

阻抗模：

$$
|Z(\omega)|=\sqrt{R^2+\left(\omega L-\frac1{\omega C}\right)^2}
$$

谐振时虚部为零，阻抗取最小值：

$$
|Z|_{\min}=R
$$

电源电压有效值 $U_s$ 固定时，电流达到最大值：

$$
I_{\max}=\frac{U_s}{R}
$$

谐振时 $L,C$ 对外串联总阻抗为零：

$$
Z_L+Z_C=j\omega_0L-j\frac1{\omega_0C}=0
$$

但这不表示 $U_L=0$ 或 $U_C=0$。以电流为参考：

$$
\dot U_L=j\omega_0L\dot I,
\qquad
\dot U_C=-j\frac1{\omega_0C}\dot I
$$

谐振时 $|\dot U_L|=|\dot U_C|$，且

$$
\dot U_L+\dot U_C=0
$$

因此电感、电容各自电压可能很大，只是相量相消。

电源只向整个 RLC 网络提供有功功率：

$$
P=I^2R=\frac{U_s^2}{R}
$$

电感吸收正无功，电容吸收负无功：

$$
Q_L=I^2\omega_0L,
\qquad
Q_C=-I^2\frac1{\omega_0C}
$$

谐振时 $Q_L+Q_C=0$，电源与整个网络无净无功交换，但 $L,C$ 内部仍交换能量。

## 5. 品质因数与电压放大

谐振时 $I=U_s/R$，于是电感电压

$$
U_L=I\omega_0L=U_s\frac{\omega_0L}{R}
$$

比例系数 $\omega_0L$ 的量纲是阻抗，称为**特性阻抗**：

$$
\rho=\omega_0L=\frac1{\omega_0C}=\sqrt{\frac LC}
$$

它只由 $L$、$C$ 决定，并在谐振时给出 $U_L=U_C=\rho I$。把特性阻抗与电阻之比定义为品质因数：

$$
Q=\frac{\rho}{R}=\frac{\omega_0L}{R}=\frac1{\omega_0CR}=\frac1R\sqrt{\frac LC}
$$

于是

$$
U_L=QU_s,
\qquad
U_C=QU_s
$$

$Q$ 是无量纲的品质因数，不是无功功率。$R$ 越小，损耗越小，$Q$ 越大，谐振时元件电压放大越明显。高 $Q$ 可用于选频和电压放大，也可能导致过电压风险。

实验确定谐振频率和 $Q$：固定 $U_s$，扫频找电流最大点，该频率即 $\omega_0$；在谐振点测 $U_L$ 或 $U_C$，用

$$
Q=\frac{U_L}{U_s}=\frac{U_C}{U_s}
$$

计算，不必先知道 $L$、$C$ 的数值。注意电压表接入后成为并联支路，内阻不够高时测到的元件电压偏低，在高 $Q$ 回路中尤其明显。

## 6. 谐振曲线与通频带

固定 $U_s$，电流有效值随频率的变化关系

$$
I(\omega)=\frac{U_s}{\sqrt{R^2+\left(\omega L-\frac1{\omega C}\right)^2}}
$$

称为串联谐振曲线。把它写成相对形式，用 $Q$ 和失谐量 $\left(\frac{\omega}{\omega_0}-\frac{\omega_0}{\omega}\right)$ 表示：

$$
\frac{I}{I_{\max}}=\frac1{\sqrt{1+Q^2\left(\frac{\omega}{\omega_0}-\frac{\omega_0}{\omega}\right)^2}}
$$

其中 $I_{\max}=U_s/R$。这个式子对理想串联 RLC 是精确的：把分母中的 $R$ 提到根号外，$|Z|=R\sqrt{1+\left[\left(\omega L-\frac1{\omega C}\right)/R\right]^2}$，再用 $\omega L/R=Q\,\omega/\omega_0$ 与 $1/(\omega CR)=Q\,\omega_0/\omega$ 即可化简成上式。$Q$ 越大，曲线在 $\omega_0$ 附近越尖锐，选频性能越好。

![[img/电路分析-09-谐振曲线.svg]]

读图：横轴为 $\omega/\omega_0$，纵轴为 $I/I_{\max}$；三条曲线对应 $Q=1,3,10$，都在归一化频率 1 处达到峰值，$Q$ 越大越窄。水平虚线 0.707 对应半功率，不是半电流。

工程上取电流下降到 $I_{\max}/\sqrt2$（即功率减半）的两个频率 $\omega_1,\omega_2$ 作为边界，定义**通频带**：

$$
\Delta\omega=\omega_2-\omega_1=\frac{\omega_0}{Q}=\frac RL
$$

其中 $\omega_0$ 表示谐振频率，$Q$ 描述曲线在谐振点附近的尖锐程度，$\Delta\omega$ 表示角频率带宽。谐振频率固定时，$Q$ 越大，带宽越窄，电路对邻近频率的区分能力越强。

### 半功率频率的精确求法

令 $I=I_{\max}/\sqrt2$，即 $|Z|=\sqrt2R$。由 $|Z|^2=R^2+X^2$ 得 $|X|=R$：低频边界电抗为 $-R$，高频边界为 $+R$。把

$$
\omega L-\frac1{\omega C}=\pm R
$$

两边乘以 $\omega C$，得到两个二次方程 $\omega^2LC\mp\omega RC-1=0$，各取正根：

$$
\omega_1=\frac{\sqrt{R^2+4L/C}-R}{2L},
\qquad
\omega_2=\frac{\sqrt{R^2+4L/C}+R}{2L}
$$

把根号改写成 $\sqrt{(R/2L)^2+\omega_0^2}$，同一对结果也常写成

$$
\omega_{1,2}=\mp\frac{R}{2L}+\sqrt{\left(\frac{R}{2L}\right)^2+\omega_0^2}
$$

两式相乘时分母为 $4L^2$、分子为 $\left(\sqrt{R^2+4L/C}\right)^2-R^2=4L/C$，故 $\omega_1\omega_2=1/(LC)=\omega_0^2$；两式相减得 $\omega_2-\omega_1=R/L$。对理想参数固定的串联 RLC，这两个都是精确关系：谐振频率是两个边界的**几何平均值**，一般不是算术中点；只有高 $Q$（即 $R/2L\ll\omega_0$）时才可近似

$$
\omega_{1,2}\approx\omega_0\mp\frac{\Delta\omega}{2}
$$

以 Hz 表示时应写

$$
\Delta f=f_2-f_1=\frac{\Delta\omega}{2\pi}=\frac{f_0}{Q}
$$

例：$R=2\,\Omega$、$L=1\,\mathrm{H}$、$C=0.25\,\mathrm{F}$，则 $\omega_0=2\,\mathrm{rad/s}$、$Q=1$。两个边界为 $\sqrt5-1\approx1.236$ 与 $\sqrt5+1\approx3.236\,\mathrm{rad/s}$，差为 2，但算术平均约为 2.236，并不等于 2。低 $Q$ 时谐振曲线在频率轴上左右并不对称，不能把它当成关于 $\omega_0$ 线性对称。

### 电流谐振频率不等于元件电压最大频率

![[img/电路分析-09-电压峰值.svg]]

读图：横轴为 $\omega/\omega_0$，纵轴为元件电压与电源电压的幅值比。$Q=1$ 时电容电压峰在虚线左侧、电感电压峰在右侧，虚线只表示电流谐振点。

令 $x=\omega/\omega_0>0$。同一串联电路的电容、电感电压传递幅值分别为

$$
\frac{U_C}{U_s}=\frac1{\sqrt{(1-x^2)^2+x^2/Q^2}},
\qquad
\frac{U_L}{U_s}=\frac{x^2}{\sqrt{(1-x^2)^2+x^2/Q^2}}
$$

电容式可直接由 $|Z_C/Z|$ 得到。记分母的平方为 $D=(1-x^2)^2+x^2/Q^2$，则 $D'=2x\left(2x^2-2+1/Q^2\right)$，令 $D'=0$ 得唯一正驻点 $x^2=1-1/(2Q^2)$；又 $D''=12x^2-4+2/Q^2$ 在该点等于 $8-4/Q^2>0$，故它是 $D$ 的极小点，也就是电容电压的极大点。因此当 $Q>1/\sqrt2$ 时，电容电压的峰值频率为

$$
\omega_{C,\max}=\omega_0\sqrt{1-\frac1{2Q^2}}
$$

电感幅值满足 $|H_L(x)|=|H_C(1/x)|$，所以同一条件下

$$
\omega_{L,\max}=\frac{\omega_0}{\sqrt{1-1/(2Q^2)}}
$$

电容峰在 $\omega_0$ 以下，电感峰在其以上，高 $Q$ 时两者才接近 $\omega_0$。例如 $Q=1$ 时，两个峰分别在 $0.707\omega_0$ 和 $1.414\omega_0$，峰值约为 $1.155U_s$；在电流谐振点二者均只有 $QU_s=U_s$。若 $Q\le1/\sqrt2$，没有有限的正频率电压峰：电容电压从低频的 $U_s$ 单调下降，电感电压向高频渐近 $U_s$。所以题问“哪个量最大”，必须先确定问的是电流、电容电压还是电感电压。

## 7. 谐振的应用与过电压风险

收音机选台、滤波器和小信号调谐放大，都利用电路对不同频率具有不同响应的特点。串联 RLC 在谐振频率处阻抗最小；保持电源电压不变时，该频率对应的电流最大，因此可用于选频。

串联谐振也会提高元件电压：由 $U_L=U_C=QU_s$ 可知，若 $Q\gg1$，电感和电容的电压可能远高于电源电压。电力系统需要避免这类意外过电压；调谐电路利用高品质因数时，也必须同时满足元件耐压和带宽要求。

![[img/电路分析-09-加载回路.svg]]

读图：图中把线圈电阻 $r$、信号源内阻 $R_s$ 与串联负载 $R_L$ 合并画成一个电阻，表示决定 $Q$ 和带宽的是这三者之和；若实际负载改为并联在电容两端，这个串联模型就不再适用。

**加载后的 Q 要计入全部串联电阻。** 若线圈电阻为 $r$、信号源内阻为 $R_s$、串联负载为 $R_L$，则取 $R=r+R_s+R_L$，加载品质因数 $Q=\omega_0L/R$，带宽为 $R/L$。例如 $\omega_0L=100\,\Omega$、$r=1\,\Omega$，单看线圈有 $Q=100$；接入 $R_s=4\,\Omega$、$R_L=5\,\Omega$ 后，回路 $Q$ 只有 10。讲电压放大倍数时必须以完整回路的源电压 $U_s$ 为分母，不能混用发生器内部电动势与负载端电压。若负载跨接在 $C$ 两端，电路已不是上述纯串联形式，须重新求输入阻抗或传递函数。

## 8. 能量交换

电感、电容储能：

$$
w_L=\frac12Li^2,
\qquad
w_C=\frac12Cu_C^2
$$

在本节的理想串联模型中，已建立的正弦谐振稳态里 $L,C$ 之间不断交换能量，两者总储能保持不变：

$$
w=w_L+w_C=\text{常数}
$$

以电流为参考，电容电压相对电流滞后 $90^\circ$。当电流最大时，电容电压为零，储能全在电感中。电流有效值为

$$
I=\frac{U_s}{R}
$$

电流幅值 $I_m=\sqrt2I$，故总储能：

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

令 $i=\sqrt2I\cos\omega_0t$，则 $u_C=\frac{\sqrt2I}{\omega_0C}\sin\omega_0t$。由 $\omega_0^2LC=1$，

$$
w_L=LI^2\cos^2\omega_0t,
\qquad
w_C=LI^2\sin^2\omega_0t
$$

相加即得 $LI^2$，与时间无关。虽然串联电阻仍耗能，但电源电压此时瞬时等于电阻电压，所以电源即时补足电阻损耗。这不意味着任意初值、暂态阶段或有损 LC 自由振荡的总储能都保持不变。

每周期电阻损耗能量为 $W_{\text{loss}}=I^2R\left(2\pi/\omega_0\right)$，于是

$$
2\pi\frac{w}{W_{\text{loss}}}=\frac{\omega_0L}{R}=Q
$$

这说明品质因数衡量的是储能相对于每周期损耗的大小。第 4 章欠阻尼自由响应的振荡频率是 $\omega_d=\sqrt{\omega_0^2-(R/2L)^2}$，而本章受迫稳态电流谐振在 $\omega_0$；有电阻时两者一般不同。

### 例题 9-1：求谐振频率、品质因数和元件电压

![[img/电路分析-09-数值谐振.svg]]

读图：三个元件值直接标在串联回路上，电源 $0.1$ V 与图题中的电流 $0.1$ A 都指有效值；元件电压均取电流流入端为正。

**题目**

串联回路中 $U_s=0.1\text{ V}$、$R=1\,\Omega$、$L=2\,\mu\text{H}$、$C=200\text{ pF}$，在某一激励频率下测得回路电流有效值

$$
I=0.1\text{ A}
$$

求 $\omega_0$、$f_0$、$Q$、$U_L=U_C$，以及该电路的 $\Delta f$。

**判断是否谐振**

$U_s$ 固定时回路电流 $I=U_s/|Z|$，所以 $|Z|=U_s/I=0.1/0.1=1\,\Omega$，恰等于 $R$。由 $|Z|^2=R^2+X^2$ 得 $X=0$，说明该激励频率正是谐振频率；若测得的电流小于 $0.1$ A，就只能说明工作频率偏离了谐振点。

**解答**

$$
\omega_0=\frac1{\sqrt{LC}}
=\frac1{\sqrt{(2\times10^{-6})(200\times10^{-12})}}
=5\times10^7\text{ rad/s}
$$

$$
f_0=\frac{\omega_0}{2\pi}
\approx7.96\times10^6\text{ Hz}=7.96\text{ MHz}
$$

再用特性阻抗校核 $Q$：

$$
\rho=\sqrt{\frac LC}=\sqrt{\frac{2\times10^{-6}}{200\times10^{-12}}}=100\,\Omega,
\qquad
Q=\frac{\rho}{R}=\frac{\omega_0L}{R}=100
$$

谐振时元件电压

$$
U_L=U_C=QU_s=100\times0.1=10\text{ V}
$$

以电流为参考：

$$
\dot U_L=j10\text{ V},
\qquad
\dot U_C=-j10\text{ V}
$$

**结果**

$$
\boxed{\omega_0=5\times10^7\text{ rad/s}},
\quad
\boxed{f_0\approx7.96\text{ MHz}},
\quad
\boxed{Q=100},
\quad
\boxed{U_L=U_C=10\text{ V}}
$$

**讨论**

通频带用精确式 $\Delta\omega=R/L$ 计算：$\Delta\omega=5\times10^5\,\mathrm{rad/s}$，$\Delta f=\Delta\omega/(2\pi)\approx79.6\,\mathrm{kHz}$，与 $f_0/Q$ 一致。若把激励频率改为 $0.5\omega_0$，则

$$
\frac{I}{I_{\max}}=\frac1{\sqrt{1+100^2(0.5-2)^2}}\approx0.00667
$$

电流只有约 $0.667\,\mathrm{mA}$，且 $\omega<\omega_0$ 时电路呈容性。可见单凭电路含有 $L$、$C$ 不能断定“谐振”，必须核对当前激励频率与参数。

## 9. 高频易错点

| 错因 | 纠偏 |
|---|---|
| 把 LC 总电压为零理解成各自电压为零 | 写相量关系 $\dot U_L=-\dot U_C$，有效值可以很大 |
| 混淆品质因数 $Q$ 和无功功率 $Q$ | 品质因数无量纲，无功功率单位 var |
| 误以为 $\omega_0$ 由 $R$ 决定 | 理想串联 $\omega_0=1/\sqrt{LC}$，$R$ 只影响峰值与 $Q$ |
| 判感/容只看是否有 L、C | 必须看 $X(\omega)=\omega L-1/(\omega C)$ 的符号 |
| 把负荷大写成阻抗大 | 固定电压下 $P=U^2/R$，负荷大常对应阻抗小 |

## 本篇小结

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
|Z|_{\min}=R,
\qquad
I_{\max}=\frac{U_s}{R}
$$

$$
\rho=\sqrt{\frac LC}=\omega_0L=\frac1{\omega_0C},
\qquad
Q=\frac{\rho}{R}=\frac{\omega_0L}{R}=\frac1{\omega_0CR}=\frac1R\sqrt{\frac LC}
$$

$$
U_L=U_C=QU_s,
\qquad
\dot U_L+\dot U_C=0
$$

$$
\frac{I}{I_{\max}}=\frac1{\sqrt{1+Q^2\left(\frac{\omega}{\omega_0}-\frac{\omega_0}{\omega}\right)^2}},
\qquad
\Delta\omega=\omega_2-\omega_1=\frac{\omega_0}{Q}=\frac RL
$$

谐振时电源只向电阻提供有功功率，电感与电容之间进行内部无功和储能交换。$Q$ 大则选频好、带宽窄，但元件过电压风险也高。电流谐振在 $\omega_0$，而电容电压峰在 $\omega_0\sqrt{1-1/(2Q^2)}$、电感电压峰在其倒数倍处，只在高 $Q$ 时才都接近 $\omega_0$。
