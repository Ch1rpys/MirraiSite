# Mirrai 官网 · 执行书

> 版本 v1.3 · 配合《项目计划书》使用（修订记录见文末）
> 原则：每个任务有明确的完成定义（DoD）；每个资产有明确的负责人；没有"以后再说"的悬空项

---

## 0. 工作分工总表

| 类别 | 负责人 | 说明 |
|---|---|---|
| 工程搭建、页面开发、动效实现 | AI（MiMoCode） | Astro 工程、组件、i18n、构建 |
| 抽象视觉素材（纹理/图形/动效） | AI | SVG/CSS 代码生成 |
| 文案起草 | AI 起草 → 用户定稿 | 中文先写，英文由 AI 译、用户审 |
| logo / 规范 | AI 出稿 → 用户拍板 | ✅ 已定稿 V3 空与在 |
| 产品截图摆拍 | **用户** | 按 §4 摆拍清单在本地产品截 |
| 录屏 | **用户** | 按 AI 提供的脚本录制 |
| 域名注册 / 备案 | **用户** | ✅ 域名已购 `mirrai.ink`；备案主体（个人/企业）待定；ICP 通过后 30 日内须公安备案 |
| 联系邮箱 / 用户群信息 | **用户** | ✅ 已提供：`ch1rpy@163.com` / 微信群 + QQ 群（入群二维码或链接待给） |
| 文档内容重写 | AI 起草 → 用户审 | 以产品仓库 docs/README 为源 |
| 产品仓库 CI 改动（`SHA256SUMS`） | AI 出 patch → 用户合并 | 跨仓依赖，M2 下载页需要 |
| 官网仓库 license | 已定 | 代码 MIT + 内容 CC BY-NC-SA 4.0；第三方字体（Cormorant/Playfair/EB Garamond/思源黑·Noto Sans SC）为 SIL OFL |

---

## 1. 仓库与目录结构

新建独立仓库（建议名 `MirraiSite`），结构：

```
MirraiSite/
├── docs/
│   ├── PROJECT-PLAN.md          # 计划书（已就绪）
│   └── EXECUTION.md             # 本执行书（已就绪）
├── public/
│   ├── favicon.svg / favicon-32.png / favicon-16.png
│   ├── og-default.png           # 1200×630
│   └── fonts/                   # Cormorant / Playfair / EB Garamond（自托管）
├── src/
│   ├── components/
│   │   ├── logo/                # Logo.tsx（V3 符号）、Wordmark.tsx
│   │   ├── home/                # Hero, Unfinished, HowItWorks, WhenAbsent,
│   │   │                        # Graduation, Fidelity, Trust, Download, Coda
│   │   ├── demo/                # PrerecordedDemo.tsx（预录对话回放）
│   │   ├── motion/              # M1–M4 动效组件（含 reduced-motion 降级）
│   │   └── layout/              # Header, Footer, ThemeToggle, LangSwitch
│   ├── content/                 # MDX 内容（Git-based CMS 管理）
│   │   ├── blog/                # 版本博客
│   │   ├── docs/                # 文档站（zh）
│   │   └── docs-en/             # 文档站（en）
│   ├── i18n/                    # zh.json / en.json（界面文案）
│   ├── pages/
│   │   ├── index.astro          # 首页（zh）
│   │   ├── download.astro
│   │   ├── ethics.astro
│   │   ├── privacy.astro
│   │   ├── about.astro
│   │   ├── go/[slug].astro      # 下载跳转链（CDN 302 优先，退化 meta-refresh；零脚本转化统计）
│   │   ├── blog/[...slug].astro
│   │   ├── docs/[...slug].astro
│   │   └── en/                  # 以上全部的英文镜像
│   └── styles/
│       ├── tokens.css           # 双主题色板 / 字体 / 间距
│       └── base.css
├── scripts/
│   └── fetch-releases.mjs       # 拉取 GitHub Releases（下载页数据）
├── LICENSE                      # MIT（代码）
├── LICENSE-CONTENT.md           # CC BY-NC-SA 4.0（内容：文案/手记/图片）
├── astro.config.mjs
└── package.json
```

**技术栈锁定**：Astro + MDX + **Keystatic（Cloud mode：GitHub App + 登录；生产站保留 `/keystatic`，账号仅协作者）** + **Tailwind** + React 岛（demo/交互）+ **零统计脚本**（转化走 `/go/*` 跳转链访问日志——只量安装包与 Docker，`/en/` 合并；可用性用免费拨测）。License：代码 MIT + 内容 CC BY-NC-SA 4.0。

---

## 2. 里程碑任务分解（WBS）

### M1 · 工程骨架 + 首页（可公开）

**M1.1 工程初始化**
- [x] Astro 项目初始化（TS strict、MDX、i18n 路由 `/` + `/en/`）
- [x] `tokens.css`：双主题色板（夜/纸）、字体栈、间距、圆角、hairline
- [x] 主题系统：默认暗色、切换器、localStorage 持久化、`prefers-color-scheme` 尊重
- [x] 自托管字体（Cormorant / Playfair / EB Garamond，woff2，font-display: swap）
- [x] 中文字体方案确定（Noto Sans SC 子集化，控制体积）

**M1.2 品牌组件**
- [x] `Logo.tsx`：V3「空与在」符号（SVG，双主题适配）
- [x] `Wordmark.tsx`：Cormorant 字标 .22em
- [x] lockup 四形态（横排/竖排/纯符号/纯字标）
- [x] favicon 全套（16/32/48 SVG + PNG）+ app icon
- [x] OG 默认卡（1200×630，**中文版**；英文版 `og-default-en.png` 随 M1.5 出）

**M1.3 首页九屏**
- [x] S1 Hero（主标语 + 副标语 + 双 CTA + 信任角标 + 纯抽象背景；**M1 期主 CTA 直指 GitHub Releases**）
- [x] S2 未竟之言（场景叙事 + 创作手记引文；引文不带链接，M2 起链 `/about`）
- [x] S3 怎么做到（三步式 + 截图占位）
- [x] S4 TA 不在的时候（四态卡片）
- [x] S5 毕业机制（大字宣言 + 预录 demo 占位 + M4 消隐）
- [x] S6 像不像（判别规则图 + 保真之尺）
- [x] S7 信任（四要点 + CTA 旁边界句；**M1 期隐藏「伦理与边界」入口**）
- [x] S8 下载（三平台 + Docker 入口，**M1 期按钮指 GitHub Releases**）
- [x] S9 尾声（尾句 + **M1 期只留 GitHub** 社区链接）
- [x] Header（logo + **锚点导航 + GitHub 外链** + 主题切换 + 语言切换）/ Footer（占位版：邮箱 + GitHub，子页链接 M2 补）

**M1.4 动效**
- [x] M1 入场对望（Hero 加载）
- [x] M2 呼吸「灯」（S5 demo 加载态 / "TA 在打字"）
- [x] M3 消息浮现（S4/S5）
- [x] M4 毕业消隐（S5 尾）
- [x] 全部组件 `prefers-reduced-motion: reduce` 降级

**M1.5 英文镜像**
- [x] `/en/` 首页九屏英文文案（A 主标语线）
- [x] `og-default-en.png`（英文版 OG 卡）
- [x] hreflang 互标

**M1 DoD**：移动端 375px 九屏完整可读；双主题切换无破版；Lighthouse 性能 ≥ 90（终验 ≥95）；**内链 404 扫描零死链**（导航仅锚点与外链；屏内链接已按降级策略处理；M1 期 404 用框架默认页，定制 404 随 M2.6）；首页能让人在 30 秒内说清"这是什么"（验收方式：请 2–3 位没接触过产品的人看 30 秒后复述）。

---

### M2 · 内容站

**M2.1 `/download`**
- [x] 三平台 + Docker 四入口卡片（系统需求、版本；**SHA 仅安装包**，Docker 显示镜像 digest 或不显示）
- [x] Docker 按钮走 `/go/docker` → Docker Hub 镜像页（计数）
- [x] `scripts/fetch-releases.mjs`：构建时拉 GitHub Releases API
- [x] Release notes 渲染（可读化）
- [x] 版本历史列表

**M2.2 `/ethics`**
- [x] 五个"不是什么"完整章节
- [x] 同意权 / AI 透明 / 数据本地 / 记忆锚点 / 情感安全层 / 毕业"只提一次"
- [x] 本地求助资源
- [x] 隐私内容不在本页展开，只留一句链接到 `/privacy`

**M2.3 `/about`**
- [x] 品牌词源（mirari → mirror / mirage）
- [x] 创作手记全文（MDX 迁入，排版为长文阅读体验）
- [x] 团队 / 致谢 / 许可（代码 MIT + 内容 CC BY-NC-SA 4.0）

**M2.4 `/privacy`**
- [x] 独立隐私页：无统计脚本 / 无 Cookie / `/go/*` 跳转链日志计数说明 / 外部拨测说明 / 主题偏好仅存 localStorage 的说明
- [x] 英文镜像

**M2.5 预录 demo 真版 + 录屏 + 截图上页**
- [x] demo 对话脚本（8–12 条，演到情感状态/记忆召回行/第三态/告别信，标注「演示数据」）
- [x] 录屏脚本（AI 出稿，见 §4.2）
- [x] `PrerecordedDemo` 组件实现（点击/自动播放、可暂停、reduced-motion 降级），替换 S5 占位
- [ ] 录屏成品（用户按脚本录）嵌入首页 S3「怎么做到」
- [ ] 截图 P1–P8 按槽位映射表上页面
- [x] 英文站 demo 呈现方式落实（英文台词或中字）

**M2.6 全局**
- [x] 链接切换五处：Hero 主 CTA 切回 `/download`；S2 引文补 `/about`；S7 显示「伦理与边界」入口链 `/ethics`；S8 按钮切 `/download`；S9 补创作手记（`/about`）与博客（`/blog`）入口
- [x] Footer 完整版（GitHub / 邮箱 / 用户群 / 伦理 / 隐私 / 备案号；英文版用户群位改 GitHub Discussions）
- [x] `/ethics` 英文版附国际求助资源（Befrienders Worldwide 等），不直译大陆热线
- [x] 404 页（符合调性："这句话没有发出去"）
- [x] 四个子页英文镜像

**M2 DoD**：子页（download/ethics/about/privacy）中英齐备；下载信息与 GitHub Releases 一致、校验和可对照；伦理五条一条不少；demo 真版可完整走通一遍；`/go/*` 跳转可达（计数口径：只量安装包与 Docker 按钮，`/en/` 合并）。

---

### M3 · 文档 + 博客 + SEO

**M3.1 文档站**
- [x] 文档框架（侧边栏、目录、上一页/下一页、移动端抽屉）
- [x] 用户文档重写：
  - [x] 快速开始（Docker 一条命令）
  - [x] 安装：Docker / 源码 / macOS DMG / Windows Setup
  - [x] 配置 LLM（12 提供商表 + Ollama 离线）
  - [x] 上传素材 → 蒸馏模式（快速/标准/深度/同事/名人研究）
  - [x] 对话与情感状态、记忆、信与第三态
  - [x] 毕业机制使用说明
  - [x] 渠道：微信 ClawBot / 飞书
  - [x] FAQ
- [x] 开发者文档：架构概览 / API / 贡献指南 / 开发环境
- [x] 英文文档（`/en/docs/`）

**M3.2 版本博客**
- [x] 博客框架（列表页 + 详情页 + RSS）
- [ ] 发版模板（可读 changelog 结构）
- [x] 迁移/撰写最近 1–2 篇发版文
- [x] 运营流程固化：产品发版 → AI 起草 → 用户审 → 发布

**M3.3 SEO 与监控**
- [x] 每页 title/description/OG（中英）
- [x] sitemap.xml、robots.txt（`robots.txt` 屏蔽 `/go/*`）
- [x] 结构化数据（SoftwareApplication / FAQPage）
- [ ] 免费拨测接入（UptimeRobot 类，监控 `/` 与 `/download`；告警发 `ch1rpy@163.com`）
- [x] `/go/*` 跳转链验证（跳转可达——302 或 meta-refresh；访问日志可计数；口径：安装包+Docker）
- [ ] Lighthouse 全站终验 ≥ 95 / SEO ≥ 95（各里程碑 ≥ 90）

**M3 DoD**：文档站可完成"从零装好并聊上第一句"；博客可发布；搜索收录路径完整；转化链路验收过（计划书 §10 第 6 条）。

---

## 3. 上线清单（Launch Checklist）

**域名与备案**
- [ ] ⚠️ 向云厂商确认 `.ink` 可否 ICP 备案（域名已购 `mirrai.ink`，此项**仍必须做**；不可备案则启用备选 `mirrai.cn`/`mirrai.app` 做大陆入口）
- [x] ~~注册域名~~ ✅ 已购 `mirrai.ink`
- [ ] 备案主体确定（个人/企业）→ 备案材料准备（主体证件、幕布照、核验单）
- [ ] 备案期间 `mirrai.ink` 解析到境外过渡托管（已定：直接用主域名）；⚠️ 与接入商确认期间可否解析、是否要求关站/挂引导页；若被要求，回退平台临时域名（`*.github.io` / `*.pages.dev`）
- [ ] ICP 备案通过后**把解析从境外过渡托管切到大陆托管**
- [ ] **公安备案**（ICP 通过后 30 日内，全国互联网安全管理服务平台）

**部署**
- [ ] 境外过渡托管部署（**GitHub Pages**）+ `mirrai.ink` 解析指过去——M1 公开即在此
- [ ] 大陆云静态托管（OSS/COS + CDN 或静态站点服务，备案后切换）
- [ ] HTTPS 证书
- [ ] `www` 与裸域跳转策略
- [ ] `/en/` 与 `/` 均可访问
- [ ] 301 / canonical 正确

**统计与监控**
- [x] ~~统计脚本~~ 不接任何第三方统计（品牌与隐私一致性，已定案）
- [ ] 免费拨测接入（UptimeRobot 类，`/` 与 `/download`；告警发 `ch1rpy@163.com`）
- [ ] `/go/*` 跳转链上线并验证（跳转可达 + 访问日志可计数；口径：仅安装包与 Docker，`/en/` 合并）；确认托管方**访问日志已开通**（选型条件，OSS/CDN 日志常需手动开通）

**内容终检**
- [ ] 伦理五条在位
- [ ] CTA 旁边界句在位
- [ ] 入群二维码/链接替换占位（邮箱 `ch1rpy@163.com` 已定）
- [ ] 创作手记全文排版检查
- [ ] 所有外链（GitHub / Releases / Discussions）可达

**提交**
- [ ] Google / Bing 站长工具提交 sitemap
- [ ] GitHub 仓库 README 加官网链接
- [ ] 产品内 Landing.tsx 加官网链接

---

## 4. 资产生产清单

### 4.1 产品截图摆拍清单（用户执行）

> 全部使用**演示数据**（虚构人名/头像/对话），不得包含真实聊天记录。暗色主题为主，亮色补 1–2 张。
> 文件规范：2x 分辨率 PNG，命名 `shot-p01-lobby@2x.png` 格式；导出前确认无真实隐私。
> 注意：截图编号用 **P**（P1–P8），与首页屏编号（S1–S9）区分。

| # | 场景 | 构图要求 | 用在哪 |
|---|---|---|---|
| P1 | 大厅（多分身） | 2–3 个分身卡，含亲密度、上次联系天数、状态标签 | 首页 S3 / `/about` |
| P2 | 对话界面 | 一段有情绪起伏的对话；底部可见情感状态标签；一条"记忆召回"可见行 | 首页 S3 / S5 |
| P3 | 上传素材页 | 拖拽区 + 蒸馏模式选择（快速/标准/深度/同事/名人研究） | 首页 S3 三步之 1 |
| P4 | 蒸馏进度 | pipeline 阶段推进中的界面 | 首页 S3 三步之 2 |
| P5 | 毕业/告别信 | 告别信生成态（TA 的口吻的信笺排版） | 首页 S5 毕业机制 |
| P6 | 信（写下来 / 交出去） | 信件列表或写信界面 | 首页 S4 TA 不在的时候 |
| P7 | 人格档案页 | 7 层人设的可视化 | 首页 S6 像不像 |
| P8 | 设置-隐私/毕业模式 | 三种毕业模式选项 | `/ethics` / 文档 |

### 4.2 录屏脚本（AI 出脚本 → 用户录）

60–120 秒旅程：**启动 → 大厅 → 上传 → 蒸馏进度 → 第一次对话（流式逐字）→ 记忆召回可见 → 告别信 → 休眠**。1080p，鼠标移动平缓，无个人信息。成品嵌首页 S3，优先 WebM/压缩 GIF，控制体积。

### 4.3 抽象素材（AI 生成，代码内实现）

- 纸张肌理（CSS/SVG noise）
- 暖光晕（radial-gradient + blur）
- 消息痕迹抽象图形（M3 动效组件）
- 时间痕迹元素（日期、天数、时区的排版组件）

### 4.4 交互式 demo 脚本（预录对话回放）

- 编排 8–12 条消息的假对话（用户与"TA"各半）
- 需演到的机制点：情感状态切换、**记忆召回可见行**、第三态（信/暂停）、**告别信**
- 交互：点击"下一条"或自动播放，可暂停；零后端
- 语气必须与产品真实输出风格一致（克制、有不完美感）
- 界面标注「演示数据」；**交付在 M2**（M1 仅占位）；英文站呈现方式（英文台词或中字）随 M2 定

---

## 5. 文档重写原则（M3 执行标准）

1. **任务导向**：标题是"我想在 Windows 上装好"，不是"Windows 安装"
2. **每篇文档只有一个任务**，开头一句话说明适用场景
3. 命令可复制、步骤可验证（写明"预期看到什么"）
4. README 源材料里的内部验收细节（roadmap/eval）**不搬**
5. 中文先行，英文版保持同步（同结构翻译）

---

## 6. 内容与代码约定

- **文案仓库化**：界面文案进 `src/i18n/zh.json|en.json`；长文进 MDX
- **禁用词清单**（文案 review 时检查）：赋能、闭环（SaaS 义；「情感闭环」为产品正典词，豁免）、抓手、颠覆、重新定义、AI 女友、复活 TA
- **必须出现的词**：毕业、告别、同意、本地、开源
- **Git-based CMS**：正文用 Keystatic 编辑，frontmatter 字段固定（title/description/order）；**语言由目录决定**（`docs/` vs `docs-en/`），frontmatter 不设 `lang`。**Cloud mode**：GitHub App + 登录，生产站保留 `/keystatic`，账号仅协作者
- **预览部署**：PR 自动部署预览 URL 供审阅（Vercel / Cloudflare Pages 任一）；大陆打不开时附构建产物截图包
- **版本博客运营**：产品发版 → AI 起草 changelog 文 → 用户审 → 发布（进 `content/blog/`）
- **组件命名**：语义化（`GraduationSection` 而非 `Section5`）
- **每个动效组件**都必须带 `prefers-reduced-motion` 降级

---

## 7. 验收与回归

每个里程碑结束跑一次：

```
□ 375px / 768px / 1440px 三档目测
□ 暗 / 亮双主题切换
□ / 与 /en/ 双语抽查
□ Lighthouse（performance：里程碑 ≥90 / 终验 ≥95；SEO / accessibility / best practices）
□ 内链 404 扫描
□ `/go/*` 跳转与日志抽查（口径：安装包+Docker）
□ 伦理五条 + 边界句存在性检查（人工）
```

---

## 8. 时间与节奏（建议）

| 周 | 目标 |
|---|---|
| W1 | M1.1 + M1.2（工程 + 品牌组件）|
| W2 | M1.3 + M1.4 + M1.5（九屏 + 动效 + 英文镜像）→ **M1 公开** |
| W3–W4 | M2 全部（下载/伦理/隐私/关于/demo 真版/页脚/404）|
| W5–W7 | M3 全部（文档站 + 博客 + SEO + 拨测）|
| W8 | 上线清单执行、**备案流程收尾**、提交收录 |

> 备案周期（约 2–4 周）应与 M2/M3 并行启动。

---

## 修订记录

| 版本 | 变更 |
|---|---|
| v1.0 | 14 轮设计讨论定稿 |
| v1.1 | 三轮自审修正：动效 M2 入 WBS、预览部署流程、`/privacy` 与零统计脚本、截图 P1–P8 与槽位映射、demo 归 M2、双许可文件、Keystatic Cloud mode、录屏脚本入 WBS、下载计数口径（安装包+Docker）、告警邮箱、localStorage 隐私声明、回归补 `/go/*` 抽查等 |
| v1.2 | 四轮自审修正：M1 零死链（锚点导航 + CTA 临时指 GitHub Releases，M2.6 加切换任务）、Docker 计数落地（`/go/docker`）、SHA 仅安装包、域名解析两阶段表述、字体 OFL 声明、M1 引文孤引说明 |
| v1.3 | 五轮自审修正：M1 零死链补全屏内链接（S7/S8/S9 降级策略），M2.6 切换清单扩为五处；境外过渡托管定 GitHub Pages 并进上线清单；OFL 补中文字体；OG 分中英两版（og-default-en 随 M1.5） |
