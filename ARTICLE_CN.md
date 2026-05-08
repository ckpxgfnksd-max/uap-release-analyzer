# 一个 UAP 解密文件分析 skill 的从 0 到 ship：eval loop 真正能抓到什么

我手头有一个 2.5 GB 的文件夹，里面是从 war.gov 下载的 132 份解密 UAP 文件——FBI、DOW（前 DoD）、NASA、DOS、NARA 五个机构混在一起。任务是写一个 Claude skill：给它任意一个这种文件夹，输出一份十分钟能读完的结构化报告。然后跑 skill-creator 的 eval loop，迭代到指标稳定为止。下面是结果。

## skill 一句话介绍

四个幂等的 Python 脚本：`inventory.py`（按文件名前缀分配机构、统计页数）、`extract_text.py`（pdfplumber，跳过已抽取的，标记没有文字层的扫描件）、`analyze.py`（基于关键词列表 + 正则跑 location / phenomena / FOIA exemption / 涉密标识——故意不上 NER，让结果可被审计）、`build_report.py`（输出 11 个固定章节的 `REPORT.md`）。再加上三份 reference：`agency_vocab.md`、`foia_codes.md`、`war_gov_quirks.md`。整个 skill 大概 600 行 Python + 700 行 Markdown。

## eval loop 给了什么

四个 eval case，每个跑两遍——一遍带 skill，一遍裸跑（baseline）。8 个 subagent 并行。打分 + 聚合后：

| Eval | 带 skill | 裸跑 | Δ |
|---|---|---|---|
| 全套语料分析（full-tranche） | 100% | 60% | +40 |
| 单文件总结（single-file） | 100% | 100% | 0 |
| 全扫描件诚实交代（honest caveats） | 100% | 88% | +12 |
| 新一批语料 bootstrap | 88% | 50% | +38 |
| **均值** | **97%** | **74%** | **+23** |

Wall-clock：带 skill 总共约 12 分钟；裸跑约 26 分钟。Token：带 skill 23.9 万，裸跑 25.9 万。**skill 更快、更便宜、更准——除非任务小到任何称职 agent 都能搞定**。单文件 digest 就是典型例子：一份 8 页有文字层的 PDF 不需要 skill。但一份 4000 页、其中 64 份是扫描件的语料就需要。

## eval 暴露出的 bug

1. **PNG/PDF 文案 bug。** 每个文件的 digest 对 `.png` 文件输出"(scanned/image PDF — OCR required)"。但 PNG 需要的是视觉分析，不是 OCR。eval-2 的 agent 注意到 FBI 照片那一栏文案不对劲，把这个标了出来。修复：summary 函数现在按扩展名 + inventory 那边的报错分支——扫描件 PDF、图像文件、打不开的 PDF 各自有专属信息。
2. **CENTCOM mission report 里的 ICAO 机场代码不在词表。** d27 这份报告真正的运营锚点是"OMAM"（阿联酋阿德富拉空军基地），不是 UAE 这个国家名——但 skill 的 location 列表里只有国家和地区。eval-1 的 agent 报了这个 gap。补进去：OMAM、OMDB、OEDR、OBBI、OKBK、OAIX、LCRA、HEDC、HEMM。跳过了 ORBI（巴格达），因为它是 NASA mission text 里"orbit"一词的子串。
3. **bootstrap 回答漏掉了 agency_vocab 扩展工作流。** 当用户问"release_02 来了我怎么最快出报告"时，skill 答了 `run_all.py` 和 `war_gov_quirks.md`，但没提 OTHER 桶的扩展模式。SKILL.md 现在在 bootstrap 上下文显式写出这条指引。
4. **回合管理：原来 eval-0 的 agent 把 `extract_text.py` 丢到后台然后结束了自己的回合**，留下一个抽了一半的 `text/` 文件夹。SKILL.md 现在告诉 agent 要在前台跑，单次调用真要超时就用 `[start] [end]` 切片——每段都很快、脚本是幂等的、进度可见。

## 如果重做我会跳过什么

盲对比 agent。四个 eval case + 程序化打分已经给出了足够的信号——大部分失败是结构性的（少了 reference、文件类型 message 错了、agent 提前结束回合），盲对比并不会比正则更准地抓到这些。

## skill 真正赚回成本的地方

两个地方。第一，在 REPORT.md 的"What's missing"那一节——它列出了那 64 份扫描件不跑 OCR 就读不了、那 1 份 inventory 阶段报错的、还有 entity 抽取的启发式上限。这一节是让报告诚实的关键。没有它，报告就是对一半数据的自信总结，比没有总结更糟。第二，在 bootstrap 循环：release_02 落地时，`python scripts/run_all.py ~/UFO/release_02/` 输出的还是同样 11 节结构的报告，用户已经知道怎么读了。可重复性比新鲜感重要。

## 最终成绩

带 skill 96.9%，裸跑 74.4%，Δ +22.5。skill 发车。
