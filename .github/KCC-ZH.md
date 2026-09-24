# KCC 中文版

本仓库是 [ciromattia/kcc](https://github.com/ciromattia/kcc) 的 fork，在其基础上做了**简体中文界面**，
并用 GitHub Actions 在云端产出可执行文件 —— 本机不需要装 Python / PySide6 / PyInstaller。

## 拿可执行文件

`Actions` → `构建中文版 KCC` → 选 `Run workflow`（或直接下载已有 run 的 Artifacts）：

| Artifact | 内容 |
|---|---|
| `kcc-zh-windows` | `KCC_zh_win64_<版本>.exe`（图形界面）+ `kcc-c2e_zh_win64_<版本>.exe`（命令行） |
| `kcc-zh-linux` | `kcc_zh_linux_<版本>`（图形界面）+ `kcc-c2e_zh_linux_<版本>`（命令行） |
| `zh-translations` | 翻译源文件 `kcc_zh_CN.ts` 与编译产物 `kcc_zh_CN.qm` |

产物默认保留 90 天。需要长期链接就建一个 Release 挂上去。

## 注意

- **Windows exe 未签名**。上游走 SignPath 签名，fork 上没有密钥，所以首次运行会弹 SmartScreen 警告，
  需要「更多信息」→「仍要运行」。
- **Linux 单文件程序**需要系统有 Qt 运行库：`libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3`。
- **macOS 未构建**：上游 macOS 流程依赖 Apple 签名证书与描述文件，fork 上无法使用。
- **命令行程序（kcc-c2e）的输出提示仍是英文**，本次只做了图形界面中文化。

## 中文化是怎么做的

分三层，只加翻译钩子，不改逻辑与布局。

### 1. 控件层（128 条：按钮 / 标签 / 菜单 / 提示）

上游 `kindlecomicconverter/KCC_ui.py` 与 `KCC_ui_editor.py` 是 Qt Designer 生成的，
本来就已经把文字包在 `QCoreApplication.translate("mainWindow"/"editorDialog", ...)` 里了，
所以这一层**不需要改任何源码**，只要提供翻译文件：

- `i18n/kcc_zh_CN.ts` —— 翻译源文件，128 条
- 构建时 `pyside6-lrelease` 编译成 `kcc_zh_CN.qm`
- `gui/KCC.qrc` 里加了一条 `<file alias="kcc_zh_CN.qm">../i18n/kcc_zh_CN.qm</file>`，
  构建时 `pyside6-rcc` 把它编进 `KCC_rc.py`，于是 .qm 随 Qt 资源系统一起进 exe
- 运行时从 `:/i18n/kcc_zh_CN.qm` 装载（直接跑源码时回退到文件系统路径）

### 2. 运行时消息（60 条：任务列表 / 对话框 / 托盘通知 / 进度条）

这些是硬编码在源码里的，没有走 Qt 翻译机制。处理方式是**在消息 funnel 处统一查表**：

- 新增 `kindlecomicconverter/i18n.py`：提供 `install_translator()` 与 `tr_runtime()`
- `KCC_gui.py` 只在 4 个 funnel 加钩子：
  `addMessage` / `showDialog` / `addTrayMessage` / `updateProgressbar`
- 查表规则：先整串精确匹配，未命中再按**长串优先**做片段替换。
  这样引擎侧 `f'{job_progress}Processing images'` 这类「前缀 + 句子」的拼接也能翻译，
  所以 `comic2ebook.py` 一行都不用改。
- 非 funnel 的控件（按钮、状态栏、窗口标题等）另有 18 处调用 `tr_runtime(...)`

### 3. 接线

`startup.py` 在构建主窗口**之前**装载翻译器 —— 必须在此之前，
因为 `setupUi()` 里的 `translate()` 是在窗口构造时执行的。

## 自检

`.github/scripts/verify_zh.py` 做四层校验，任一不过则构建失败：

1. 翻译文件能否装载
2. 控件层：`translate()` 是否返回中文
3. 运行时层：整串 / 片段替换 / 拼接消息是否正确，且控制指令（`tick`、数字）必须原样透传
4. 用真实生成的 `Ui_mainWindow` 构建窗口，断言控件文字确实是中文

构建流程分两段跑：`lrelease` 之后跑一次（验证文件系统回退路径），
`rcc` 之后再跑一次并加 `--require-resource`（验证打包后真正走的资源路径）。

另有一道冒烟测试：offscreen 模式真跑打包出来的 Linux 程序，
退出码为 124（被 timeout 终止）即说明冻结包内依赖与资源完整。

## 改翻译

1. 编辑 `i18n/kcc_zh_CN.ts`（控件层）
2. 编辑 `kindlecomicconverter/i18n.py` 里的 `RUNTIME_ZH`（运行时层）
3. 推到 master，`build-zh.yml` 会自动重新构建

## 与上游同步

中文化改动刻意保持最小，便于跟随上游更新：

- 新增 4 个文件（`i18n/kcc_zh_CN.ts`、`kindlecomicconverter/i18n.py`、构建工作流、自检脚本）
- 改动 3 个文件，共约 20 行：
  `gui/KCC.qrc`（+1 行资源）、`startup.py`（+3 行）、`KCC_gui.py`（+24 处 `tr_runtime` 调用）
