# Slides — Marp

`slides.md` が本体（発表用スライド）、`原稿.md` が発表カンペです。
**Markdownなので、テキストエディタで自由に編集できます。**

## 編集のしかた

- 各スライドは `---`（区切り線）で区切られています。
- `<!-- ... -->` は **発表者ノート**（プレゼン時に自分だけ見えるメモ）です。
  スライド本体は文字を詰め込みすぎず、詳しい説明はここに書いています。
- 見た目（色・文字サイズ）は先頭の `style:` ブロックで調整できます。
- `<div class="term">` は用語解説（緑）、`<div class="warn">` は注意（赤）のボックスです。

## プレビュー

**VS Code（おすすめ）**
拡張機能「**Marp for VS Code**」を入れると、その場でプレビューしながら編集できます。

**コマンドライン（bun）**
```bash
# ブラウザでライブプレビュー
bunx @marp-team/marp-cli slides/slides.md --preview

# HTMLに書き出し（このファイル単体を配布できる）
bunx @marp-team/marp-cli slides/slides.md -o slides.html

# PDFに書き出し
bunx @marp-team/marp-cli slides/slides.md --pdf

# PowerPoint(.pptx)に書き出し（PowerPointで最終調整したい場合）
bunx @marp-team/marp-cli slides/slides.md --pptx
```

## 発表者ノートを見ながら発表するには

- HTML書き出し時に `--html` プレゼンモード、またはVS Codeのプレビューから「プレゼンテーション」を開くと、
  発表者ビュー（次のスライド＋ノート表示）が使えます。
- PDF/PPTXにノートを含めたい場合は `--notes` オプションでノートだけの書き出しも可能です。

```bash
bunx @marp-team/marp-cli slides/slides.md --notes   # 発表者ノートをテキスト出力
```
