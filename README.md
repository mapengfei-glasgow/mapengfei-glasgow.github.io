# Podcast 英语听力站

把播客音频转写、**按句切成独立音频**，每句点一下就读一遍，用来精听和跟读。

## 目录结构

```
english-site/          # Hugo 站点
  content/episodes/    # 每集一个 .md（frontmatter 里存全部句子+时间戳）
  static/audio/<slug>/ # 每集的 0001.mp3, 0002.mp3, ...
  static/css/js/       # 样式与播放器脚本
  layouts/             # 模板
tools/make_episode.py  # MP3 → 句子音频 + Hugo 内容的流水线
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
ffmpeg 逐句切片 → 写 `content/episodes/<slug>.md`。
第一次运行会下载 Whisper 模型（缓存到 `.hf-cache/`，约 460MB，small 档）。

- `--model tiny|base|small|medium|large-v3`：越大越准越慢（默认 small）
- `--slug`、`--force` 见 `--help`

## 本地预览 / 构建

```bash
cd ~/dcgrid/english-site
../bin/hugo server -n 127.0.0.1 -p 1313      # 开发预览（自动刷新）
../bin/hugo --minify                            # 构建到 public/
```

## 页面上怎么用

- 点任意句子 → 只读那一句；再点一下停止
- 「▶ 播放全部」→ 从头按句连播，等价于听完整集
- 「自动连播」勾选 → 播完一句自动下一句
- 键盘：↑/↓ 选句，空格 播放/停止
- 句子下的细条是当前播放进度

## 加新节目/新集

1. 用 `bbc_podcast.py` 或手动下载 MP3
2. 跑 `make_episode.py`
3. 刷新站点即可（hugo server 会自动重建）
