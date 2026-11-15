# doodle-majo

dreaming majo の映像「Doodle of Majo」から取り出した**型**。
連番PNGの人物、背景の動画、曲を渡すと、五段の骨組みで一本の動画が組み上がる。

型は出発点で、完成形ではない。毎回の素材と、そのあとの手で変わっていく。

## 五段

| 段 | 長さの比 | 中身 |
|---|---|---|
| 1 全面 | 29 | 背景の動画と全面の図形を切り替えながら人物を乗せる |
| 2 モザイク | 12 | 画面をマスに割り、図形・背景・人物を敷き詰める |
| 3 全面 | 5 | 1に戻る |
| 4 全面＋崩し | 10 | 人物を大きく、色を崩す。物語の文を渡せば一語ずつ跳ねる |
| 5 締め | 3 | 黒地にタイトルと dreaming majo |

長さは曲の長さに合わせて比率で割る。

## 刻み

- 拍は曲から測る（測れなければ0.37秒）
- 一拍、半拍、一瞬（1コマ）、溜め（約1.4秒）がランダムに混ざる
- 人物の連番は 1秒6枚のカクカクで進む
- 小刻みリピート：ときどき連番の2コマを1〜2コマずつ行き来させる
- 背景の動画は流れる、止まる、止まった所から再開する、たまに飛ぶ

## 使い方

```
pip install -r requirements.txt

# 人物の切り抜き（連番1本ずつ）
python3 cutout.py 元の連番フォルダ materials/people/名前

# 背景の動画を連番JPGに（15fps）
ffmpeg -i 背景.mov -vf "fps=15,scale=1920:1080" -q:v 3 materials/bgv/f_%05d.jpg

# 組む
python3 doodle_majo.py \
  --people materials/people \
  --bgvideo materials/bgv \
  --bg materials/bg \
  --audio 曲.aif \
  --title "タイトル" \
  --out 出力.mp4 --seed 1
```

- `--people` の中は、切り抜き済みの連番PNGのフォルダを1つ以上（フォルダ1つ＝1本の動き）
- `--bg` は止め絵の背景（なくてもよい）
- `--text 物語.txt` を渡すと4段目に文字が出る
- `--layout tri` で元の三枚並び（左に図形・真ん中に背景・右に同心円）に戻せる
- `--seed` を変えると、同じ素材でも毎回違う並びになる

## 作品

- Doodle of Majo v3（2026-11-10）— この型の元
- 宇宙浴衣（2026-11-15）— 型を全面に変えて最初に回したもの

---

A template extracted from "Doodle of Majo" by dreaming majo.
Give it PNG-sequence cutouts, a background video and a track; it builds a video in five sections.
The template is a starting point, not a finished form.
