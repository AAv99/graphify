# Fiscal-law A/B Evaluation State

Captured: 2026-07-10

## Repository State

```text
$ git status --short --branch
## v8...origin/v8
```

```text
$ git rev-parse --show-toplevel
/Users/adnanavdic/Documents/GitHub/graphify
```

```text
$ git log -5 --oneline
e63321e Merge branch 'v8' of https://github.com/AAv99/graphify into v8
565026d fix(ci): add cluster-only step to generate GRAPH_REPORT.md in release-graph
ba1921f fix(ci): skip .md/.txt files in release-graph to avoid LLM API key requirement
e6d2dc4 release 0.8.37
1513e62 fix(ci): correct three bugs in release-graph workflow
```

```text
$ uv run python -m graphify --version
graphify 0.8.37
```

Note: `python -m graphify --version` failed because `python` is not available on this machine. The project runner is `uv run python`.

## Located Artifacts

Exact `Graph giw (3).json` was not found. The closest supplied graph artifact found by automatic search is:

```text
/Users/adnanavdic/Library/Mobile Documents/com~apple~CloudDocs/Graph giw .json
```

Bridge/oracle artifacts:

```text
/Users/adnanavdic/Library/Mobile Documents/com~apple~CloudDocs/Bronbstaobgraphify/giw-hir-staking-voornemen.md
/Users/adnanavdic/Library/Mobile Documents/com~apple~CloudDocs/Bronbstaobgraphify/BRIDGES-README.md
/Users/adnanavdic/Library/Mobile Documents/com~apple~CloudDocs/Bronbstaobgraphify/TEMPLATE.md
```

GIW corpus root selected from existing files:

```text
/Users/adnanavdic/Documents/Projects/Grondslagen inkomstenbelasting Winst
```

Verified required GIW files:

```text
knowledge-base/notes/herinvesteringsreserve.md: exists
knowledge-base/notes/staking-en-stakingswinst.md: exists
knowledge-base/topics/staking-en-herinvesteringsreserve.md: exists
```

VPB corpus root located for the onzakelijke-lening case:

```text
/Users/adnanavdic/Documents/Projects/Grondslagen vennootschapsbelasting lokaal/output
```

## Graph Shape

Graph measured:

```text
/Users/adnanavdic/Library/Mobile Documents/com~apple~CloudDocs/Graph giw .json
```

```json
{
  "directed": false,
  "node_count": 222,
  "edge_count": 220,
  "source_files": 121,
  "communities": 78
}
```

Additional measurements:

```text
singleton_communities: 56
nodes_without_source_file: 7
files_represented_by_more_than_one_node: 25
nodes_with_summary_rationale_content_rule_or_conditions: []
```

Search observations:

```text
herinvesteringsreserve hits in labels/source_file: 6
staking hits in labels/source_file: 33
herinvesteringsvoornemen hits in labels/source_file: 0
onzakelijke lening hits in GIW graph: 0
civielrechtelijke hits in GIW graph: 0
artikel 8b hits in GIW graph: 0
```

## Frozen Current Query Baseline

Command:

```bash
uv run python -m graphify query \
  "Hoe verhoudt de herinvesteringsreserve zich tot staking en het herinvesteringsvoornemen?" \
  --graph "/Users/adnanavdic/Library/Mobile Documents/com~apple~CloudDocs/Graph giw .json" \
  --budget 2000
```

Stdout saved verbatim to:

```text
evals/fiscal-law/current-query-baseline.txt
```

`herinvesteringsvoornemen` appears in the baseline output:

```text
false
```

Unique `source_file` paths returned:

```text
graphify-out/converted/Collegeweek V_e9893134.md
Grondslagen inkomstenbelasting Winst/knowledge-base/notes/herinvesteringsreserve.md
Grondslagen inkomstenbelasting Winst/knowledge-base/notes/staking-en-stakingswinst.md
Grondslagen inkomstenbelasting Winst/tmp/slides/week5-personenvennootschappen/preview/slide-06.png
Grondslagen inkomstenbelasting Winst/Handout GIBW 4 maart 226 Staking en HIR Thil van Kempen.pdf
Grondslagen inkomstenbelasting Winst/knowledge-base/notes/geruisloze-doorschuiving-art-363-wet-ib-2001.md
```
