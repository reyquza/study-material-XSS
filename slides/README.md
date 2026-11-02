# Slides — Marp

`slides.md` is the deck; `script.md` is the speaker script.
**They're Markdown, so you can edit them freely in any text editor.**

## How to edit

- Each slide is separated by `---`.
- `<!-- ... -->` are **speaker notes** (visible only to you when presenting).
  The slide body is kept light; detailed explanations live in the notes and in `script.md`.
- Adjust the look (colors, font sizes) in the `style:` block at the top.
- `<div class="term">` is a glossary box (green); `<div class="warn">` is a warning box (red).
- Each content slide follows a **Title / Message / Body** structure: a heading, one bold "message" line
  asserting the slide's single point, then the supporting body.

## Preview

**VS Code (recommended)**
Install the **"Marp for VS Code"** extension to preview while editing.

**Command line (bun)**
```bash
# Live preview in the browser
bunx @marp-team/marp-cli slides/slides.md --preview

# Export to a single distributable HTML file
bunx @marp-team/marp-cli slides/slides.md -o slides.html

# Export to PDF
bunx @marp-team/marp-cli slides/slides.md --pdf

# Export to PowerPoint (.pptx)
bunx @marp-team/marp-cli slides/slides.md --pptx
```

## Presenting with speaker notes

- Use the HTML presenter mode, or open "Presentation" from the VS Code preview, to get the presenter view
  (next slide + notes).
- To export just the notes as text:

```bash
bunx @marp-team/marp-cli slides/slides.md --notes
```
