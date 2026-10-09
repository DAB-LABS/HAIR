<p align="center">
  <img src="https://raw.githubusercontent.com/DAB-LABS/HAIR/main/images/HAIR-readme-hero-v0.2.png" alt="HAIR 横幅" width="900" />
</p>

# HAIR

**HAIR 把你的红外码从厂商云端、Blaster 内存和配置文件里解救出来，搬进 Home Assistant。**

把任何遥控器对准红外接收器按一下，HAIR 就会把这个信号变成 Home Assistant 真正能用的东西：可以放进任何仪表盘的按钮、自动化的触发器，以及能从原生红外平台上任何一台发射器发出的指令。不用 YAML，不用厂商 App，也不用学习进别人的盒子。

## 安装

[![Open your Home Assistant instance and open the HAIR repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DAB-LABS&repository=HAIR&category=integration)

1. 打开 HACS 并搜索 HAIR
2. 安装 HAIR，重启 Home Assistant，然后在「设置 → 设备与服务」中添加该集成

需要 Home Assistant 2026.4 或更高版本；原生红外接收推荐 2026.6 及以上。

## 导入红外码的五种方式

- **捕获。** 按下真实遥控器上的按钮，HAIR 会实时从空中捕获信号、提取指纹，并按遥控器归类整理。
- **剪取。** 粘贴已知的红外码，或选择品牌与型号，从内置码库里取出一整套遥控器。
- **提取。** 把厂商 Blaster（例如 Tuya Local）里已学习过的红外码取出来，无需用接收器重新学一遍。
- **监听。** 经 Home Assistant 发出的每一条红外命令都会出现在 Mirror 里 —— 无论是否被听到 —— 点一下就能变成你自己的命令。
- **入库。** 把红外码文件拖进码库柜 —— 别人分享的码组、SmartIR 的 JSON、Flipper Zero 的 `.ir`、LIRC 配置文件、IrScrutinizer 导出的 Girr —— 它会被收入你的收藏，一键就能变成可用的遥控器。

## 导入红外码之后能做什么

- **创建设备。** 为电视、空调、风扇、灯具、开关、幕布建立档案，把捕获到的信号指派为命令，HAIR 会自动生成对应的原生实体：电视变成真正的媒体播放器，空调变成带模式和温度预设的真正 climate 实体，风扇则带风速调节。在仪表盘、脚本或语音助手里，它们和任何其他 Home Assistant 设备一样工作。
- **把遥控器按键变成触发器。** 实体遥控器上的任何按键都能触发自动化 —— 用旧电视遥控器上的红色按钮启动观影场景。触发器知道按键是在哪个房间按下的，所以同一个遥控器在不同房间可以有不同的作用。没有别的集成能做到这一点。
- **看住 Mirror。** 对整个家发出的红外流量做实时审计：哪条命令、从哪台发射器出去、又被哪个接收器听到。凌晨两点红外出了什么怪事，Mirror 都看着。
- **测试并打磨一切。** 信任之前先从任意发射器试发任意信号；给信号起别名；就地编辑 Pronto 码；对能识别的协议（NEC、Sony、RC-5、Samsung 等），HAIR 会解码并以更干净的方式发送。
- **实机验证。** 在真实硬件上验证一个码组：先作为设备采用，实际用过之后，在存入码库柜时逐个确认确实生效的信号。签过名的确认记录会留在码组文件里，跟着它一起流转到分享对象那里；完全验证过的码组会在码库柜里显示绿色对勾。

面板会说你的语言：英语、西班牙语、法语、日语、德语、波兰语、葡萄牙语、荷兰语、意大利语、俄语和中文，自动跟随你的 Home Assistant 个人资料语言。

> [!IMPORTANT]
> HAIR 面板的这份中文翻译由编程助手起草，正等待母语者审校。如果你愿意担起这件事：审校只需一个 pull request，你的名字会被写进文件。从这里开始：[Adding a language](CONTRIBUTING.md#adding-a-language)

## 完整文档

包含设置用 YAML、支持的硬件、功能指南和截图的完整 README 为英文：

**[阅读完整文档](README.md)**

---

*译自英文 README，截至 v0.17.2。本文件由编程助手起草，随每次发布刷新。欢迎母语者接手，详见 [Adding a language](CONTRIBUTING.md#adding-a-language)。*
