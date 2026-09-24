# KCC 云端转换使用说明

在 GitHub 的机器上跑 Kindle Comic Converter，本机不装 KCC、不落中间文件。

## 怎么用

1. 打开 `Actions` → 左侧 `KCC 云端转换` → `Run workflow`
2. 填参数：

| 参数 | 说明 |
|---|---|
| `source` | 漫画包直链，多个用空格或换行分隔。**留空=跑自检样例** |
| `format` | `EPUB` / `AZW3` / `MOBI` / `CBZ` / `PDF` / `KFX` |
| `profile` | 目标设备，默认 `KV`（Kindle Voyage）。见下表 |
| `manga_style` | 日漫右翻页，默认开 |
| `hq` | 高质量，尽量不压缩图片 |
| `title` / `author` | 书名、作者，留空用 KCC 默认值 |
| `extra_args` | 直接透传给 `kcc-c2e` 的额外参数 |
| `release_tag` | 填了就建 Release 并把成品挂上去，例如 `v1` |

3. 跑完在 run 页面底部 `Artifacts` 下载产物（保留 30 天）。
   填了 `release_tag` 的话，产物在仓库 `Releases` 里长期可下载。

## 支持的输入

`CBZ` `CBR` `ZIP` `RAR` `CB7` `7Z` `PDF`，以及图片文件夹打包成的 zip。

`source` 必须是**直链**（能 `curl -fL` 直接下到文件）。网盘分享页链接不行，要用直链。

## 设备 profile

- Kindle：`K1` `K2` `KDX` `K34` `K57` `KPW` `KV` `KPW34` `K810` `KO` `K11` `KPW5` `KPW6` `KS1860` `KS1920` `KS1240` `KS1324` `KS` `KCS` `KS3` `KSCS`
- Kobo：`KoMT` `KoG` `KoGHD` `KoA` `KoAHD` `KoAH2O` `KoAO` `KoN` `KoC` `KoCC` `KoL` `KoLC` `KoF` `KoS` `KoE`
- reMarkable：`Rmk1` `Rmk2` `RmkPP` `RmkPPMove`
- 其他：`OTHER`

工作流下拉框只放了常用项，其他值走 `extra_args` 传 `-p <profile>`（会覆盖下拉框的选择，因为它排在后面）。

## 格式说明

| 格式 | 怎么来的 |
|---|---|
| EPUB / CBZ / PDF / KFX | KCC 原生直接产出 |
| AZW3 / MOBI | 先由 KCC 产 EPUB，再用 calibre `ebook-convert` 转（Amazon 的 `kindlegen` 是私有二进制，GitHub 机器上没有） |

## 为什么不用本机跑

- 依赖（Pillow / PyMuPDF / numpy / mozjpeg）和中间文件全在运行器上
- 转换过程占 CPU 和内存，云端跑不挤占主机
- 产物走 Artifact / Release，主机只需下载最终那一份

## 自检

`source` 留空即触发自检：当场生成 6 页测试漫画 → 打包 CBZ → 走完整转换链路。
用来确认仓库的工作流本身没坏。
