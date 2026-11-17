# 内容许可 · Content License

本仓库的**内容**（文案、创作手记、图片、文档正文、博客文章）采用
**Creative Commons 署名—非商业性使用—相同方式共享 4.0 国际许可协议（CC BY-NC-SA 4.0）** 授权。

The **content** of this repository (copy, creator's notes, images, documentation
prose, blog posts) is licensed under
**CC BY-NC-SA 4.0 (Attribution–NonCommercial–ShareAlike)**.

- 代码部分（`src/`、`scripts/`、配置文件）为 **MIT**，见 [LICENSE](LICENSE)。
- Code (in `src/`, `scripts/`, config files) is **MIT** — see [LICENSE](LICENSE).
- 创作手记可非商业转载，须署名并以相同方式共享。
- The creator's notes may be reproduced non-commercially with attribution and
  under the same license.

完整协议文本：<https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode>

---

## 第三方字体 · Third-party fonts

本站自托管的字体均为 **SIL Open Font License 1.1**，允许自由使用、修改与再分发：

| 字体 | 用途 | 许可 |
|---|---|---|
| Cormorant Garamond | 字标 | SIL OFL 1.1 |
| Playfair Display | 大标题 | SIL OFL 1.1 |
| EB Garamond | 长文正文 | SIL OFL 1.1 |
| Noto Sans SC | 中文正文 / UI | SIL OFL 1.1 |
| Noto Serif SC | 中文标题 / 引文 | SIL OFL 1.1 |

SIL OFL 1.1 全文：<https://openfontlicense.org>

字体文件位于 `public/fonts/`（woff2）。中文字体为按站点用字生成的子集
（`scripts/build-fonts.mjs`），未修改字形，仅做子集化与 woff2 压缩。

---

## 房间场景 · The room scene

首页的房间（静帧与进门镜头的三维层）是本项目自己在 Blender 里搭的场景
（`scripts/room/build.py` → `assets/room/room.blend`），渲染结果属于上面的内容许可。

场景里的几种材质用了 [Poly Haven](https://polyhaven.com) 的贴图，均为 **CC0**（公有领域，无需署名）。
贴图本身不随仓库分发（构建场景时由 `scripts/room/fetch-textures.mjs` 下载到 `.cache/`），只以渲染后的画面出现：

| 贴图 | 用途 |
|---|---|
| Wood Table 001 | 书桌 |
| Walnut Veneer | 椅子、书架、床架 |
| Wood Floor Worn | 地板 |
| Plastered Wall 04 | 墙面 |
| Knitted Fleece | 床上的织物 |
| Rough Linen | 窗帘 |

The room on the home page is an original Blender scene. A few materials use CC0 textures from
Poly Haven; the textures are not redistributed here and appear only in rendered images.
