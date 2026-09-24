# KCC 中文版

本仓库是 [ciromattia/kcc](https://github.com/ciromattia/kcc) 的 fork，在其基础上做了**简体中文界面**，
并用 GitHub Actions 在云端产出可执行文件 —— 本机不需要装 Python / PySide6 / PyInstaller。

界面翻译参考并吸收了 [pretenderlu/kcc-chinese](https://github.com/pretenderlu/kcc-chinese)
（同样基于 KCC v11.3.2）的译文，并在此基础上补齐了它未覆盖的部分。特此致谢。

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

分两层，只加翻译钩子，不改逻辑与布局。

### 1. 控件层（138 条：按钮 / 标签 / 菜单 / 提示）

上游 `kindlecomicconverter/KCC_ui.py` 与 `KCC_ui_editor.py` 是 Qt Designer 生成的，
本来就已经把文字包在 `QCoreApplication.translate("mainWindow"/"editorDialog", ...)` 里了，
所以这一层**不需要改任何源码**，只要提供翻译文件：

- `i18n/kcc_zh_CN.ts` —— 翻译源文件，138 条，0 缺译
- 构建时 `pyside6-lrelease` 编译成 `kcc_zh_CN.qm`
- `gui/KCC.qrc` 里加了资源条目，构建时 `pyside6-rcc` 把它编进 `KCC_rc.py`，
  于是 .qm 随 Qt 资源系统一起进 exe
- 运行时从 `:/i18n/kcc_zh_CN.qm` 装载（直接跑源码时回退到文件系统路径）

抽取用 AST 而非正则：跨行隐式拼接的字符串会被 Python 合并成一个字面量，
而 `translate()` 收到的正是合并后的整串，必须按整串建键。

### 2. 运行时消息（262 条：任务列表 / 对话框 / 托盘通知 / 进度条 / 原生对话框）

这些是硬编码在源码里的，没有走 Qt 翻译机制。处理方式是**在消息 funnel 处统一查表**：

- 新增 `kindlecomicconverter/i18n.py`：提供 `install_translator()` 与 `tr_runtime()`
- `KCC_gui.py` 的 4 个 funnel 加钩子：
  `addMessage` / `showDialog` / `addTrayMessage` / `updateProgressbar`
- 查表规则：先整串精确匹配，未命中再按**长串优先**做片段替换。
  这样引擎侧 `f'{job_progress}Processing images'` 这类「前缀 + 句子」的拼接也能翻译，
  所以 `comic2ebook.py` 一行都不用改。
- 不走 funnel 的地方另有 11 处 `tr_runtime(...)` 包裹：
  按钮与状态栏、窗口标题、`QFileDialog` 的标题与过滤器、`QMessageBox` 的标题。
  卷号校验等元数据编辑器消息统一在 `statusLabel` 展示处包一处即全覆盖。

### 3. Qt 自带目录（标准按钮）

`QMessageBox` 的 OK / Yes / No 等按钮文字来自 Qt 自己的翻译目录，不在 KCC 源码里。
`.github/scripts/fetch_qtbase.sh` 依次尝试取得 `qtbase_zh_CN.qm`：

1. PySide6 自带目录（实测多数版本**不带**这个文件）
2. 官方 [qt/qttranslations](https://github.com/qt/qttranslations) 仓库下载 `.ts`，用 `pyside6-lrelease` 编译
3. 都拿不到则生成空占位文件 —— rcc 不会中断，运行时 `QTranslator.load` 返回 False
   优雅降级为英文，不会崩

### 4. 接线

`startup.py` 在构建主窗口**之前**装载翻译器 —— 必须在此之前，
因为 `setupUi()` 里的 `translate()` 是在窗口构造时执行的。

### 5. 设备名与格式名必须保留英文

设备下拉框与格式下拉框的**显示文字本身就是程序逻辑键**：

```python
options.profile = GUI.profiles[str(GUI.deviceBox.currentText())]['Label']
current_format = GUI.formats[str(GUI.formatBox.currentText())]['format']
```

所以 `Kindle Scribe 3`、`Kobo Nia`、`MOBI/AZW3`、`KFX (Send to Kindle EPUB)` 这类
共 55 个字符串**绝不能被翻译**，否则功能直接失效。
工具链用 AST 从 `KCC_gui.py` 的 `self.profiles` / `self.formats` 字典精确提取这些键，
加入黑名单；自检里还有一道守卫，一旦发现它们出现在 `.ts` 里就判定构建失败。

### 6. 跨层一致性

同一句文本可能在控件层与运行时层各有一份译文（例如标签初值与动态更新），
会出现同一个标签显示两种文字。合并时按归一化文本（忽略大小写、空白、冒号）对齐，
统一采用控件层译文；窗口标题这类需要保留尾空格的再单独定稿。

## 自检

`.github/scripts/verify_zh.py` 做七层校验，任一不过则构建失败：

1. 翻译文件能否装载
2. 控件层：`translate()` 是否已中文化
3. 运行时层：整串 / 片段替换 / 拼接消息是否正确，且控制指令（`tick`、数字）必须原样透传
4. 用真实生成的 `Ui_mainWindow` 构建窗口，断言控件文字确实是中文
5. 原生对话框：`QFileDialog` 标题与过滤器、`QMessageBox` 标题
6. `QMessageBox` 标准按钮（qtbase 取不到时只提示不判失败）
7. **守卫**：55 个设备名 / 格式名是程序逻辑键，一旦出现在 `.ts` 里即判定失败

断言方式以**语义**为主：「已中文化」= 译文与英文原文不同且含汉字。
不硬编码具体用词，这样调整译文不会导致自检误报，适配跟随上游自动重建。

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

- 新增 7 个文件：`i18n/kcc_zh_CN.ts`、`kindlecomicconverter/i18n.py`、
  两个工作流（构建 / 跟随上游）、两个自检脚本、qtbase 获取脚本
- 改动 3 个文件：
  `gui/KCC.qrc`（+4 行资源）、`startup.py`（+3 行）、
  `KCC_gui.py`（+37 处 `tr_runtime` 调用，均为插入钩子，不动原逻辑）

## 跟随上游自动中文化

`.github/workflows/sync-upstream.yml` —— 上游更新后自动重新中文化编译，全在 GitHub 云端跑。

- **触发**：每天 UTC 19:00（北京时间 03:00）定时检查；也可手动 `Run workflow`
- **判断上游是否有更新**：用 git 祖先关系，不需要额外存状态文件
  （`upstream/master` 是 `HEAD` 的祖先 → 已合过；否则就是有新提交）
- **流程**：
  1. 检出 fork，拉取上游 `ciromattia/kcc`
  2. 有新提交则 `git merge upstream/master` —— 冲突会直接失败，不会带着坏结果往下走
  3. 装依赖、`lrelease` 编译翻译、跑 `verify_zh.py` 中文化自检
  4. **自检通过才推送**；然后触发 `build-zh.yml` 重建并发布 Release
  5. 无更新则跳过，不空跑构建

- **Release tag 规则**：`v<上游版本号>-zh`。上游升版本号 → 出新 Release；
  版本号未变但只有零散提交 → 刷新同一个 Release（`upload --clobber`）。
- **手动强制重建**：手动触发时把 `force` 打开，即使上游无更新也会重建并刷新 Release。

### 注意

- 上游若改动了被中文化补丁锚定的代码行（`KCC_gui.py` 的 4 个 funnel 与 11 处 site 钩子、
  `startup.py`、`gui/KCC.qrc`），`git merge` 会冲突并让工作流失败 —— 这是**故意**的，
  宁可停下来让人处理，也不要静默产出半中文化的版本。
- GitHub 对 fork 的定时工作流有默认限制。若次日 03:00 没有自动跑，
  到仓库 `Actions` 页把 `跟随上游自动中文化` 启用一次即可。
