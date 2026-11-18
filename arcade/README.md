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


## 2026-11-19 の版で足したもの

- `races.py` … 脇の車10種（1983ワイヤーフレーム／1983真上8bit／1986海岸線／1989ネオン街／1990真上ネオン／1991ラリー／1993雪山／1997 PS1風／1999虹の道／2000雨の夜）。キックで加速、強い音で光る
- `games16.py` … レース（真上）、落ちもの、線だけの隕石、足場登りを追加
- `render.py` … `KICKS`（低域から拾った本物のバスドラの打点）、`kickpulse(t)`（打点で1、すぐ減衰）、`offpulse(t)`（打点と打点の真ん中＝裏で山）
- `render2.py` … 動画の断片も1場面として混ぜられる（`CLIPS = {場面番号: パス}`）。裏のブラー `ura_blur` は `BLUR_SCENES` の場面だけ
- `render3.py` … 脇の番組表 `SCHED`（車×車／車×他／他×他）、見せ方（そのまま・鏡・単色・粗いドット）、場面頭の砂嵐。鏡の場面も右は別の種で別の動き
- `dance.py` … 切り抜いた人物を3つの枠をまたいで踊らせる。`WINDOWS = []` で無し（土台だけ）。`WINDOWS_CUTOUT` / `WINDOWS_GREEN` に前の配置を残してある
- `solo.py` … 二人組の切り抜きを一人ずつに分ける（別々の取り方から組むと振りが揃わない）
- `cutgreen.py` … 緑バックの動画を透明背景の連番に（人物の抜き＋緑の除去＋緑かぶり取り）

### この回で決まったこと

- 拍の格子より本物の打点。打点で動かす場面は真ん中を30コマにする（コマ落としのままやと遅れて見える）
- 裏のブラーは絵が止まってる場面だけ。入れすぎない（最終的に ベイビーの聖戦 と 無言のウィンク だけ）
- ピカッ系は打点で光らせる
- 脇が左右同じ動きやとノリが出ない。形は対称でも動きは別にする
- 車が気持ちいい。脇の3分の2は車
- 切り抜きの重ねは、最後は本人がタイムラインでやる。こっちは「切り抜きなしの土台」を高画質（場面ファイルを再圧縮せず結合）で渡す
- 素材（ポスター・曲・動画）はリポジトリに入れていない。`posters/` `clips/` `cut/` `song.aif` を作業場に置いて使う
