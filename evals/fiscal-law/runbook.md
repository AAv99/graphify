# Fiscal-law A/B Runbook

Use fresh sessions and the same model/settings for every run. Do not tell either agent the expected answer, required concepts, oracle file, or scoring rules.

## Condition A - no graph

```python
no_graph_prompt = f"""You have access to {corpus_root}. Work with the user on this task:
{case['task']}
Find and read whatever files you need. Do not use graphify, graph.json,
GRAPH_REPORT.md, or any graph-derived artifact. Return the answer followed by
a machine-readable footer:
FILES_READ:
"""
```

Operational constraint for transcript verification: source files must be opened with the `Read` tool so file-read events can be verified independently of the footer.

## Condition B - graph as locator

```python
graph_locator_prompt = f"""You have access to {corpus_root} and {graph_path}.
Work with the user on this task:
{case['task']}
1. Run graphify query on the user's exact task.
2. Collect the unique source_file paths returned by the nearest subgraph.
3. Resolve those paths against the corpus root and actually open the relevant files.
4. Treat node labels and edges only as navigation. Derive every substantive fiscal statement from files you opened.
5. If the first neighborhood is insufficient, expand the graph query once or use ordinary file search after graph orientation.
6. Return the answer followed by a machine-readable footer listing only files actually opened:
FILES_READ:
"""
```

Operational constraint for transcript verification: `graphify` is provided on `PATH` via the project virtual environment. Source files must be opened with the `Read` tool so file-read events can be verified independently of the footer.

## Repair prompts

First repair:

```text
Je lijkt mogelijk te laat in de analyse in te stappen. Controleer of er een eerder liggende kwalificatie- of grondvraag is, lees de daarvoor relevante bestanden en herstel je analyse.
```

Second repair:

```text
Lees de fundamentele bronbestanden uit de gevonden omgeving opnieuw en bouw de analyse opnieuw op vanaf de eerste juridisch relevante vraag.
```

Stop as soon as the invariant passes or after the second repair. The correction count is the number of repair prompts sent before the first passing answer: `0`, `1`, `2`, or failure after two repairs.

## Corpus and graph roots

HIR/staking:

```text
corpus_root = /Users/adnanavdic/Documents/Projects
graph_path = /Users/adnanavdic/Library/Mobile Documents/com~apple~CloudDocs/Graph giw .json
```

Onzakelijke-lening:

```text
corpus_root = /Users/adnanavdic/Documents/Kennisapparaat-fiscaal
graph_path = /Users/adnanavdic/Documents/Kennisapparaat-fiscaal/graphify-out/graph.json
```

The separate real GVPB knowledge-base exists at `/Users/adnanavdic/Documents/Projects/Grondslagen vennootschapsbelasting lokaal/output/knowledge-base`, but no existing Graphify graph was found under that project. The run therefore uses the existing mixed fiscal Kennisapparaat graph/corpus for the graph-locator condition and the same corpus for the no-graph condition.
