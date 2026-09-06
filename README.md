# Podcast 英语听力站

把播客音频转写、**标注句级时间戳**，点任意句子就跳到那一刻播放；
整集音频常驻底部播放条，页面跳转（Hotwire Turbo）不打断，用来精听和跟读。

技术栈：Hugo + Hotwire Turbo 8（SPA 式页间跳转）+ AppWrite（生词本）。

## 目录结构

```
english-site/          # Hugo 站点
  content/episodes/    # 每集一个 .md（frontmatter 存每句文字+起止时间戳）
  data/transcripts/    # 每集 <slug>.small.json（词级时间戳）
  static/audio/<slug>/ # 每集整段 episode.mp3（句子按时间戳定位，不切片）
  static/css/          # main.css
  assets/js/           # turbo.umd.js（Hotwire Turbo 8，内嵌依赖）、
                       # player.js（底部播放条）、episode.js（单集页绑定）、
                       # appwrite.js（生词本）
  layouts/             # 模板
tools/make_episode.py  # MP3 → 整段音频 + Hugo 内容（含句级时间戳）的流水线
bin/                   # hugo、ffmpeg 静态二进制、uv
venv/                  # Python 环境（faster-whisper）
```

## 从 MP3 生成一集

```bash
cd ~/dcgrid
HF_HOME=$PWD/.hf-cache ./venv/bin/python tools/make_episode.py \
  ~/Downloads/BBC\ Global\ News\ Podcast/2026-09-03\ xxx.mp3 \
  --show "Global News Podcast" \
  --title "Episode title" --date 2026-09-03
```

流程：faster-whisper（word 级时间戳）→ 按标点/停顿分组句子 →
ffmpeg 转码整段 → 写 `content/episodes/<slug>.md`（每句起止时间）
和 `static/audio/<slug>/episode.mp3`（转写缓存落在 `data/transcripts/`）。
第一次运行会下载 Whisper 模型（缓存到 `.hf-cache/`，约 460MB，small 档）。

- `--model tiny|base|small|medium|large-v3`：越大越准越慢（默认 small）
- `--slug`、`--force` 见 `--help`

## 本地预览 / 构建

```bash
cd ~/dcgrid/english-site
../bin/hugo server -n 127.0.0.1 -p 1313      # 开发预览（自动刷新）
../bin/hugo --minify                            # 构建到 public/
```

## 发布到 GitHub Pages

站点发布在 <https://mapengfei-glasgow.github.io/>（用户主页站点），
仓库为 `mapengfei-glasgow/mapengfei-glasgow.github.io`。

`.github/workflows/deploy.yml` 在每次 push 到 `main` 时自动：
下载 Hugo extended 0.165.0 → `hugo --minify --baseURL <Pages URL>` →
`actions/deploy-pages` 发布 `public/`。Pages 的构建模式已设为 **workflow**，
所以 `git push` 即自动上线，本地 `public/` 不入库。

> 注意：仓库名为 `mapengfei-glasgow.github.io`，是用户主页站点，
> 直接发布在根路径；本地构建同样用 `baseURL = "/"`，两者一致。

发布一集：

```bash
cd ~/dcgrid/english-site
git add -A && git commit -m "add episode ..."
git push origin main   # 远端为 SSH；仓库已配 core.sshCommand 指向本机 ssh config
```

## 页面上怎么用

- 点任意句子 → 跳到该句开始播放（句级 seek）；再点同一句 = 暂停
- 「▶ 播放全部」→ 从头按句连播，句子高亮随播放推进
- 底部播放条（全站常驻）：⏮/⏭ 逐句、▶/⏸、拖进度条跳转、「自动连播」开关
- 页面跳转（Hotwire Turbo，SPA 式）播放不中断，播放条始终在底部
- 每集独立记忆播放位置：换集再回来，从上次停下的位置续播
- 全局键盘：↑/↓ 逐句，空格 播放/暂停（任何页面都有效）

## 加新节目/新集

1. 用 `bbc_podcast.py` 或手动下载 MP3
2. 跑 `make_episode.py`
3. 刷新站点即可（hugo server 会自动重建）
