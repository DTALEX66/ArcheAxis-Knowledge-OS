---
fixture: f01-quality
---
# 星环知识平台 Roundtrip
Controlled synthetic line with CJK 中文 and astral emoji 😀.
## 结构 anchors
Wiki link [[Roundtrip]] and a markdown link [docs](https://example.invalid/docs).
Embed ![[figure.png]] is counted apart from the wiki link.
~~~json
{"roundtrip": true}
~~~
- first list item
- second list item
Line endings stay LF so coverage is the only measured loss.
Original bytes remain the source of record.
Transform hash binds this text to its source.
Explicit unsupported state is reported, never guessed.
