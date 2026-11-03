# KCC 中文版

> **本仓库已于 2026-11-03 停止维护并归档。**
>
> 上游 [ciromattia/kcc](https://github.com/ciromattia/kcc) 从 12.1.x 起自带简体中文
> （`translations/kcc_zh_CN.ts`，界面右上角「文 A」菜单可切换语言），不再需要这个中文 fork。
> 请直接下载上游 Release：<https://github.com/ciromattia/kcc/releases>
>
> 这里的旧产物 `v12.1.5-zh` 仍可下载，但不会再更新。以下内容仅作历史记录保留。

本仓库是 [ciromattia/kcc](https://github.com/ciromattia/kcc) 的 fork，产出**开箱即简体中文**的
Windows / Linux 可执行文件，全部在 GitHub Actions 云端构建 —— 本机不需要装 Python / PySide6 / PyInstaller。

界面译文参考并吸收了 [pretenderlu/kcc-chinese](https://github.com/pretenderlu/kcc-chinese)
（基于 KCC v11.3.2）的措辞，特此致谢。

## 拿可执行文件

`Actions` → `构建中文版 KCC` → `Run workflow`（或直接下载已有 run 的 Artifacts）：

| Artifact | 内容 |
|---|---|
| `kcc-zh-windows` | `KCC_zh_win64_<版本>.exe`（图形界面）+ `kcc-c2e_zh_win64_<版本>.exe`（命令行） |
| `kcc-zh-linux` | `kcc_zh_linux_<版本>`（图形界面）+ `kcc-c2e_zh_linux_<版本>`（命令行） |
| `zh-translations` | 翻译表 `translations/kcc_zh_CN.ts` 与编译产物 `kcc_zh_CN.qm` |

长期版本走 Release，tag 形如 `v12.1.5-zh`。

## 注意

- **Windows exe 未签名**。上游走 SignPath 签名，fork 上没有密钥，首次运行会弹 SmartScreen 警告，
  需要「更多信息」→「仍要运行」。
- **Linux 单文件程序**需要系统有 Qt 运行库：`libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3`。
- **macOS 未构建**：上游 macOS 流程依赖 Apple 签名证书与描述文件，fork 上无法使用。
- **命令行程序（kcc-c2e）的输出提示仍是英文**，汉化只覆盖图形界面。

## 中文化是怎么做的

**跟上上游，不另起炉灶。** 上游从 12.1.x 起自带多语言：源码里所有界面文案都走 Qt 的
`translate()` / `self.tr()`，翻译表在 `translations/*.ts`，构建时 `pyside6-lrelease`
编译成 `.qm`，再由 `pyside6-rcc` 编进 Qt 资源系统，运行时从 `:/i18n/kcc_zh_CN.qm` 装载。
界面右上角「文 A」菜单可切换语言，选择记在 `QSettings` 里。

本 fork 因此**不再改任何源码**，只在三处动手：

1. **`.github/zh_overrides.json` —— 中文措辞**
   `{context: {英文原文: 中文}}`，共 82 条：80 条是本 fork 与上游译法不同的措辞，
   2 条是上游 `.ts` 漏收（lupdate 落后于源码）而运行时只会在界面上出现英文的串。
2. **`.github/scripts/apply_zh_overrides.py` —— 把措辞盖上上游 `.ts`**
   以上游 `.ts` 为底（保住上游新增的串），同一 `(context, source)` 用本 fork 译法覆盖；
   上游漏收的串直接补进去。合并上游后由 `merge_upstream.sh` 调用，幂等。
3. **`.github/scripts/set_zh_default.py` —— 默认语言钉成中文**
   构建期把 `kindlecomicconverter/i18n.py` 的 `DEFAULT_LANGUAGE` 改成 `zh_CN`。
   只在 CI 工作树里改、不提交，所以合并上游永远不会为这几行冲突。

### 为什么不再自己包一层运行时翻译

老做法是在 `KCC_gui.py` 的消息 funnel 处包 `tr_runtime()`，配一份 349 行运行时替换表。
上游 12.1.x（commit `a053b3e`）自己做了同样的活，而且覆盖更全（280 条，含任务列表、
对话框、托盘通知、进度条），于是两套机制正面相撞、每天合并都冲突。现在只在「怎么翻」
这一层有 fork 的东西，代码层完全跟上游。

### 设备名与格式名必须保留英文

设备下拉框与格式下拉框的**显示文字本身就是程序逻辑键**：

```python
options.profile = GUI.profiles[str(GUI.deviceBox.currentText())]['Label']
current_format = GUI.formats[str(GUI.formatBox.currentText())]['format']
```

`Kindle Scribe 3`、`Kobo Nia`、`MOBI/AZW3`、`KFX (Send to Kindle EPUB)` 这类共 55 个字符串
**绝不能被翻译**，否则功能直接失效。自检里有一道守卫：AST 从 `KCC_gui.py` 的
`self.profiles` / `self.formats` 字典精确提取这些键，一旦出现在 `.ts` 里即判定失败。

## 自检

`.github/scripts/verify_zh.py` 八层校验，任一不过则构建失败：

1. 翻译表存在、条数 ≥ 250、无未翻译条目
2. `.qm` 能否装载（资源形态 / 文件系统形态各跑一次）
3. 控件层：`translate()` 的采样串确实变成了中文
4. 运行时消息：`translate('KCCGUI', ...)` 的采样串确实变成了中文
5. 用真实生成的 `Ui_mainWindow` 建窗口，断言按钮文字与窗口标题是中文
6. `gui/KCC.qrc` 确实把 `translations/kcc_zh_CN.qm` 绑到了 `:/i18n/`
7. 打包前额外断言 `DEFAULT_LANGUAGE == 'zh_CN'`（`--require-default-zh`）
8. **守卫**：55 个设备名 / 格式名不得出现在 `.ts` 里

断言以**语义**为主：「已中文化」= 译文与英文原文不同且含汉字，不锁具体用词，
这样调译文不会误报，适配跟随上游自动重建。

构建流程分两段跑：`lrelease` 之后跑一次（验文件系统路径），`rcc` 之后再跑一次并加
`--require-resource`（验打包后真正走的资源路径）。另有一道冒烟测试：offscreen 真跑
打包出的 Linux 程序，退出码 124（被 timeout 终止）即说明冻结包内依赖与资源完整。

## 改翻译

1. 编辑 `.github/zh_overrides.json`（只写要覆盖的条目，键为英文原文）
2. 推到 master，`build-zh.yml` 会自动重新构建
3. 想验证：本地跑 `python3 .github/scripts/apply_zh_overrides.py` 看命中情况

上游新增的串会自动进 `.ts`（英文兜底），需要中文时在 `.github/zh_overrides.json` 里补一条即可。

## 跟随上游自动中文化

`.github/workflows/sync-upstream.yml` —— 上游更新后自动合并、编译、出包，全在 GitHub 云端跑。

- **触发**：每天 UTC 19:00（北京时间 03:00）定时检查；也可手动 `Run workflow`
- **判断上游是否有更新**：用 git 祖先关系，不需要额外存状态文件
- **流程**：检出 fork → 拉上游 → `merge_upstream.sh` 按白名单消解冲突 → 编译翻译 →
  `verify_zh.py` 自检 → 通过才推送 → 触发 `build-zh.yml` 出包并发 Release
- **Release tag 规则**：`v<上游版本号>-zh`；版本号未变时刷新同一个 Release（`--clobber`）
- **手动强制重建**：手动触发时打开 `force`，即使上游无更新也会重建
- **补历史漏跟的工作流**：`sync_workflows=true` 会把上游存在的 `.github/workflows/**`
  强制拉成上游版本（fork 自己的三个工作流上游没有，不受影响）

### 合并白名单

`merge_upstream.sh` 只自动消解这些文件的冲突，其余一律 `merge --abort` 硬失败：

| 文件 | 归属 |
|---|---|
| `README.md` | 上游（`README_POLICY=ours` 可反转） |
| `.github/workflows/**` | 上游（需带 workflow 权限的推送令牌） |
| `gui/KCC.qrc`、`KCC_gui.py`、`kindlecomicconverter/i18n.py` | 上游（源码层不再由 fork 改造） |
| `translations/kcc_zh_CN.ts` | 上游为底 + 重新盖 `.github/zh_overrides.json` |

### 注意

- GitHub 对 fork 的定时工作流有默认限制。若次日 03:00 没跑，到 `Actions` 页把
  「跟随上游自动中文化」/「构建中文版 KCC」启用一次即可。
- 上游若改了 `i18n.py` 的结构（例如 `DEFAULT_LANGUAGE` 改名），`set_zh_default.py`
  会直接报错失败 —— 这是故意的，宁可停下来，也不要静默出一个默认英文的「中文版」。
- **GitHub 会因为 fork 的 Actions 用量把整套工作流自动停掉**（表现为推送不触发、dispatch 报
  `422 Actions has been disabled for this repository`，而 API 里 `actions/permissions` 仍显示
  `enabled: true`、workflow 仍是 `active` —— 别被这两个探针误导）。2026-10-14 本仓库就中过一次，
  之后 20 天没有任何运行。恢复：打开 <https://github.com/Emopeny/kcc/actions> 点横幅上的
  「Enable workflows」。所以构建策略刻意收敛：**上游版本号没变就不重建**（`sync-upstream.yml` 会跳过），
  `build-zh.yml` 也不挂 push 触发。
