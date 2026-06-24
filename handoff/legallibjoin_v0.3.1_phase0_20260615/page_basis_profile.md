# Phase 0 page_basis profile (book TOC nodes, report-only)

- 対象: content_type=book の全 TOC ノード **623891**
- pdf_page あり: 623891 (100.0%)
- print_page あり: 592614 (95.0%)
- **両持ち (pdf+print)**: 592614 (95.0%)
- pdf のみ: 31277 (5.0%) (章見出し等・本文頁未付与の構造ノード)
- print のみ: 0 / どちらも無し: 0

## offset = pdf_page - print_page 分布 (両持ちノード)

| offset | nodes |
|---:|---:|
| 1 | 41942 |
| 22 | 31197 |
| 20 | 25030 |
| 26 | 24569 |
| 18 | 23986 |
| 14 | 23907 |
| 16 | 23832 |
| 24 | 19585 |

- 異なる offset 値の種類 (全本横断): 133

## offset の本単位一貫性 (両持ちノード3以上の book)

- 対象 book: 2670
- 最頻 offset が **100% 単一**の本: 2533 (94.9%)
- 最頻 offset が **90%以上**を占める本: 2549 (95.5%)
- 本ごとの最頻 offset 占有率 平均: 0.979

> **所見**: legallib の各ノードは pdf_page と print_page を併記し、両持ち率 95%。実測のとおり offset(=前付け頁数) は **本ごとにほぼ単一** (95% の本で最頻 offset が 90%以上を占める) なので、pdf↔print 変換は本単位の単一 offset で機械化できる。横断で offset が 133 種に散るのは『本ごとに前付け頁数が違う』ためで、**同一本内の基準ブレではない**。残り 5% の pdf-only は章見出し等の構造ノード (本文頁未付与)。→ **page tolerance は本単位 offset 補正後に評価すべき** (生の pdf_page 差で別版判定すると前付け差を誤検知する)。
- 参考: book の total_pages 分布 n=2760 min=2 max=2096

