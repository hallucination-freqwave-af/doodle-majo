# arcade — ポスター×曲×脇ゲームの動画道具（狂った周波数）

- render.py   … 共通ヘルパー（曲解析の読み込み、切片・明滅・猫・朝日など）。`song.aif` を mono.f32 に落として rms/flux/low/hi を .npy に保存してから使う
- render2.py  … 1080×1350。posters/pNN.png を順に、1枚1芸（36種）。字幕は切ってある（数字と credit だけ残す）
- render3.py  … 1920×1080。真ん中に render2、両脇に games16（1990風縦シュー／回るテトリス／たまに8bit）。真ん中のコマ数は場面ごとに 4〜15
- games.py    … 8bit（インベーダー・テトリス・ポン・スネーク・ブロック崩し・縦シュー）
- games16.py  … 16bit（3面の縦シュー＋中ボス、回転テトリス）

手順: 曲解析 → `python3 render3.py N`（N=場面）を全部 → concat → 音を乗せる。詳細は SKILL.md。

## 手順（あまのじゃく 2026-11-18 の作り方）

```
python3 analyze.py song.aif            # 曲の解析（BPMと長さが出る。render.py の BEAT を合わせる）
mkdir posters && cp ... posters/p01.png # 1080x1350 を順番に
python3 render3.py 0 ... N-1           # 場面ごと（偶数と奇数で2本並列）
for i in $(seq -w 0 N-1); do echo "file v3_scene$i.mp4"; done > list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy silent.mp4
ffmpeg -i silent.mp4 -i song.aif -map 0:v -map 1:a -c:v libx264 -crf 22 -c:a aac -b:a 256k -shortest out.mp4
```

決まりごと：字幕なし／伸び縮み・斜め・波は使わない（大きさ・色・位置・明るさ）／1枚1芸、絵の話に合わせる／真ん中のコマ数は場面ごとに4〜15、脇は30。
必要なもの：numpy, opencv-python, pillow, scipy, ffmpeg, Noto Sans CJK（数字用）。
