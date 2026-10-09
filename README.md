# EdgeAccel 文档站

面向通过 PCIe 使用 AX650 系列 M.2 算力卡的用户，按安装、首次推理、模型部署、应用接入与维护组织正文。基于 Docusaurus 3、React 19，复用 EdgeOS_Desktop-docs-site 的页面样式、响应式布局、中文搜索、Mermaid 和学习进度组件。

## 本地运行

需要 Node.js 20 或更高版本。

```powershell
npm ci
npm start
```

默认地址为 http://localhost:3000。生产构建与预览：

```powershell
npm run build
npm run serve -- --port 3000
```

中文搜索索引在生产构建时生成，请用 `npm run serve` 验证搜索功能。

内存较紧张时，可使用串行 Webpack 构建。此入口保留全部页面、压缩、搜索索引和链接检查，逐文件复制并校验静态附件；校验清单保存在 `.cache-docs/low-memory-builds/`。

```powershell
npm run build:low-memory
npm run serve -- --port 3000
```

该入口使用单独的 `docusaurus.low-memory.config.js`，不改变默认构建配置。复制插件依赖锁定版本的 Docusaurus 内部接口；升级依赖后须重新执行完整构建与页面检查。

## GitHub Actions 自动构建与发布

工作流为 `.github/workflows/build-docs.yml`。推送到 `main`、向 `main` 提交 PR 或在 Actions 页面手动运行时，会安装锁定依赖、执行首次推理脚本的本地模拟测试，并运行 `npm run build:low-memory`，自动生成文档和检查链接、模型记录及附件。

构建环境为 Ubuntu、Node.js 22。构建成功后，可在对应运行页面下载 `edgeaccel-docs-site` 产物，保留 7 天。`main` 的构建会自动将网页发布到 `gh-pages` 分支；PR 只执行检查和构建，不发布。

默认网址为 https://dshanpi.github.io/edgeaccel-docs/ 。仓库 **Settings → Pages** 中选择 **Deploy from a branch → gh-pages → / (root)**。源码始终在 `main` 维护，不要直接编辑 `gh-pages` 中的生成文件。

`scripts/prepare-pages.py` 在发布前合并重复打包的媒体文件并同步更新网页引用，保留原始附件和验证数据，检查站点未超过 GitHub Pages 的 1 GB 限制。Pages 构建通过 `PAGES_ATTACHMENT_REVISION` 指定完整提交 SHA，将 `static/examples/` 的 ZIP / tar.gz 程序包和 `static/validation/effects/` 的 JSON 结果链接到该提交的 GitHub 原始文件，避免附件重复占用网页空间。附件仍提交在源码仓库中，内容与 SHA-256 不变；图片、音频、视频继续由站点提供。本地构建不设置此变量，保留全部附件。链接转换由 `scripts/remark-pages-attachments.mjs` 完成，串行构建同时记录外部附件清单。

当前在线文档为 https://edgeaccel.100ask.net/ 。

绑定或更换自定义域名时：

1. 在仓库 **Settings → Secrets and variables → Actions → Variables** 新建 `PAGES_CUSTOM_DOMAIN`，值填写域名，不带 `https://` 或路径。
2. 在 **Settings → Pages → Custom domain** 填写同一域名，并按 GitHub 提示完成 DNS 配置。
3. 在 Actions 中手动运行工作流。构建会使用域名根路径，并在 `gh-pages` 写入对应的 `CNAME`。

未配置域名变量时，自动使用默认的 GitHub Pages 项目路径。

## 内容结构

- `docs/getting-started/`、`docs/ax650n/quick-start/`：硬件准备与三种主机安装入口。
- `docs/usage/`：设备检查、下载、编译、Python、视频、HTTP、维护与排错。
- `docs/projects/`：项目实战入口，包含六路 AI 视频推流总览与 Laya 游戏实验室。
- `docs/models/`：模型选择、目录及各类部署步骤。
- `docs/reference/`：验证计划、资料来源与原始附件目录。原始附件目录为 unlisted 页面，不显示在侧栏或站内搜索中，仅保留直接链接；此设置由生成脚本维护。
- `docs/ax650n/applications/`：已导入的六路项目正文与 Qwen3-VL 记录。六路项目归入项目实战；Qwen3-VL 历史记录隐藏侧栏、搜索及站点地图入口，保留原文件和旧 URL。
- `docs/ax650n/archive/`：早期版本快照，保留原适用环境。
- `src/pages/`：首页；`src/css/`：参考站全局样式。
- `src/components/learning/`、`src/hooks/`：参考站学习路线及浏览器进度组件。
- `src/data/`：模型元数据、文档统计与上手路线配置。
- `src/data/modelValidationResults.json`：客户样例的适用环境、结果、指标与附件索引。
- `static/validation/effects/`：实际输入输出与配套文件清单。
- `static/resources/ax650n/`：原始文档及全部配套附件，保留目录结构。
- `migration-manifest.json`：来源、文件大小、SHA-256 与历史失效链接修复记录。
- `static/templates/model-validation.md`：空白模型验证记录模板。
- `static/scripts/ax8850-first-inference.sh`：已安装 AXCL 的 Linux 主机使用的 YOLO11 首次推理脚本。
- `scripts/test-first-inference.py`：脚本的本地模拟测试，不连接算力卡或外网；运行 `python scripts/test-first-inference.py`，Windows 默认使用 Git Bash，也可用 `TEST_BASH` 指定 Bash 路径。
- `scripts/import-docs.mjs`：保留已编辑正文的资料导入脚本。

源目录实际为 `F:\AX\AX650N_card\doc`。首次迁移包含 26 篇 Markdown 与全部 293 个原始文件，静态副本保留目录结构。历史文档缺失的共享附件链接已指向现存文件，页面有历史提示，具体映射见清单。

重新导入会刷新原始附件、迁移清单、导入索引及 `docs/reference/original-files.md`，仅为尚不存在的导入页面创建正文。**不会覆盖已编辑的正文、侧栏或下载入口页。** 新增文件的导航需手动确认：

```powershell
npm run import:docs -- "F:\AX\AX650N_card\doc"
```

通用指南可直接编辑 `docs/`。新增通用文档后在 `sidebars.js` 添加入口；逐模型页面按下节生成，不能直接编辑生成文件。首页与上手路线分别在 `src/pages/index.js`、`src/data/learningRoadmaps.js` 中维护。

六路项目总览位于 `docs/projects/six-streams.md`，分步部署正文保留在 `docs/ax650n/applications/six-streams/`，服务管理说明保留在 `docs/usage/services.md`。这些文档均已归入“项目实战”，重新导入不会覆盖整理后的正文。“既有项目与历史记录”侧栏已移除，11 篇早期快照保留原链接及附件索引。若另需删除快照源文件，还需同步处理导入映射和原始附件目录中的链接。

## 维护模型与验证状态

当前覆盖 2026-09-23 官方 Hugging Face API 返回的全部 264 个公开仓库：252 个模型、模型变体或组合应用，以及 12 个工具与配套资源。每个仓库均有独立页面，不同量化、上下文与芯片版本分别保留。目录支持型号搜索、任务、资料状态和最近一次本机实测状态筛选。这些数量表示文档覆盖范围，实际验证数量由测试记录生成；各容量的结果分别记录，16GB 结果不作为 8GB 卡的验证证据。

客户页面展示最近一次模型样例的输入、输出、适用环境和必要限制。最新数量见生成的模型目录与 `src/data/siteStats.json`；基本运行不等于回答正确，也不代表长期稳定性。16GB 卡的实测页面明确标注环境，不混用为 8GB 卡的容量验证。目录统计由数据文件生成。

逐模型事实、文件表、固定 revision、运行配方和注意事项保存在 `src/data/modelDeployments.json`；`src/data/models.json` 是目录使用的精简索引。修改事实时保持两者的型号、状态和页面路径一致。来源覆盖清单为 `src/data/modelSourceSnapshot.json`。更新后执行：

```powershell
npm run docs:models
npm run docs:stats
npm run docs:check
npm run build
```

`docs/models/catalog.mdx`、`docs/models/deploy/*.md` 、10 个任务选型页和 `src/data/modelSidebar.json` 为生成文件，应修改数据或 `scripts/generate-model-guides.mjs` 后重新生成。生产构建自动更新文档、目录、侧栏分组和首页统计。生成过程不联网、不下载模型权重。`docs:check` 检查仓库覆盖、固定提交、配套文件、编译目标、页面对应关系和实测证据。

`src/data/modelValidationResults.json` 只保存用于客户效果展示的数据：模型、固定 revision、环境、日期、结果、指标、限制与样例附件。`static/validation/effects/` 仅保存输入输出媒体、API 回复与下载文件清单。`basic` 表示基本运行，`correctness` 表示固定样例已核对；未取得有效结果的配置仍标为待验证。

完整测试历史、诊断脚本、主机日志、设备标识及资源采样只保存在 `.cache-docs/` 的内部记录中，不放入 `docs/`、`static/` 或站点数据。清理板端模型前先备份内部记录。原有完整数据备份位于 `.cache-docs/customer-content-before-cleanup/`。

模型页先展示部署操作，再展示实际图片、问答、音频或向量结果。数据与媒体的校验由 `docs:check` 完成；没有记录的模型仍标为待验证。通用输出检查方法见 `docs/reference/validation.md`。

资料来源及固定源码版本见 `docs/reference/sources.md`。写作遵循 `F:\Skills\写作风格Skill\SKILL.md`，按准备、操作、检查组织内容，保留版本与失败边界。外部模型权重未下载进网站，研究缓存 `.cache-docs/` 不进入站点或版本库。

## 部署路径

默认根路径用于本地预览。部署到 GitHub Pages 项目路径时，在构建前设置：

```powershell
$env:SITE_URL = 'https://dshanpi.github.io'
$env:BASE_URL = '/edgeaccel-docs/'
npm run build
```

构建产物位于 `build/`，可以交给静态服务器。GitHub Actions 自动编译并发布到 `gh-pages`，域名配置见上文。

## 基础源码来源

`F:\AI 辅助嵌入式 Linux 多平台桌面系统 UI 移植实战\Doc\tmp\EdgeOS_Desktop-docs-site`

保留原项目 LICENSE；依赖使用原始 package-lock.json 的锁定版本。未复制旧站课程正文、node_modules 或构建缓存。

模型页的效果排版由 `scripts/model-effects.mjs` 生成；图片、音频和 API 回复读取原始记录，未实测模型明确标注待补充。任务分类页只保留选型和部署入口，不重复具体模型命令。

任务选型页由 `scripts/generate-task-guides.mjs` 维护模型入口、实测状态和设备环境；选型矩阵、输入准备、验收要点和后续入口保存在 `scripts/task-guide-content.mjs`。修改这两个源文件后重新生成，避免手改分类页被构建覆盖。

选型、分类与公共指南共用 `src/components/ModelGuideLayout/` 的页首摘要和后续入口。保留 `.md` 路径的交互页面使用 `mdx: {format: mdx}`，现有内部链接无需改名。目录汇总按每个模型最近一条记录统计，与表格筛选采用相同口径；历史记录仍在独立模型页保留。
