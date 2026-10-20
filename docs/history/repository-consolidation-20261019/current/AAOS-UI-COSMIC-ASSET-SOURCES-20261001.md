# AAOS 星空装饰资产来源（2026-10-01）

本表仅登记装饰素材。用户指定的 UI 套件产品图 `01_01_产品信息架构_Information_Architecture.png` 至 `12_12_搜索与复习_Search_Review_FSRS.png` 是页面视觉标准；品牌图 `01_01_品牌主视觉_Brand_Hero.png` 至 `11_11_品牌应用_Applications_Left.png` 是色彩、标志和图形语言参考。原图含 UI 文字，未直接铺作产品背景。

| 资产 | SHA-256 | 来源与用途 |
| --- | --- | --- |
| `apps/ArcheAxis.Desktop/Assets/home-planet-hero-20261001.png` | `EFE37347A7093AE411882C2FC611DE65258226501F4A617A3B884B71B07CEBDE` | 使用内置 imagegen 以 `UI套件/04_04_首页结构_Homepage.png` 为风格及构图参考生成；独立的深空星场、右上行星弧线，供 Aurora 首页装饰，不含业务数据。 |
| `apps/ArcheAxis.Desktop/Assets/home-planet-hero-monochrome-20261001.png` | `04140308E30E7E5F6B4F90B44636F21FF28F9A29E9B9585B8F62F59EF070D987` | 对上一张装饰图编辑成无彩色黑白版本，保留构图，供 Monochrome 首页装饰。 |

生成提示词要点：深海军蓝星空、右上蓝色行星大气弧线、左侧 70% 留出文字空间；不含控件、图标、文字、数字或标志。黑白版本保持构图并移除全部蓝青色。两图均不是原 UI 母版截图，也不应作为 Core 数据、状态或图谱证据。动效应使用原生控件/矢量和减少动态效果设置；不把光栅图当视频。
