# Graphify Fiscal Knowledge Graph: Phase 0–1 Handoff

**Date:** 2026-09-30  
**Corpus:** 3.PSY (test run) + 100-werk (target)  
**Status:** Phase 1 complete. Phase 2 ready to execute.

---

## Summary of Accomplishments

### Phase 0: Environment Setup
- ✅ Graphify 0.9.29 installed via `uv tool` with extras: pdf, office, gemini, leiden
- ✅ Gemini API key configured globally (`GEMINI_API_KEY` set)
- ✅ Python 3.12 environment verified; graspologic available for Leiden clustering
- ✅ Corpus located: `/Users/adnanavdic/Documents/Werk aaff/100-werk` (205 files, 940,350 words)

### Phase 0b: File Preparation & Filtering
- ✅ Byte-identical duplicate detection (output/knowledge-base/sources/ excluded from 3.PSY)
- ✅ `.graphifyignore` created in 100-werk:
  ```
  *actuur*
  *vk Uittreks*
  *aaropgave*
  ~$*
  .DS_Store
  ```
- ✅ File format conversions completed:
  - RTF → DOCX (python-docx)
  - PPTX → DOCX (python-pptx)
  - Scanned PDFs → OCR'd text (pypdf with OCR fallback)
  - Final scope: 940,350 words (23k+ from OCR recovery)
- ✅ Stale semantic cache removed; fresh extraction ready

### Phase 1: Test Extraction (3.PSY)
- ✅ Monolithic extraction: 75 nodes, 65 edges, 19 communities
- ✅ Confidence distribution: 89% EXTRACTED, 11% INFERRED
- ✅ Cost: $0.15 USD (Gemini at standard rates)
- ✅ God nodes identified: "aaff International B.V.", "tax dossier structure", "audit requirements"
- ⚠️ **Critical Finding:** 63% of documents produced zero nodes (27 of 43 files)

---

## Root Cause Analysis: Document Missrate

**Problem:** Gemini's output token hardcap (16,384 tokens/request) vs. input budget (60,000 tokens) creates a 4:1 ratio. When a single chunk reaches ~60k input tokens, the LLM exhausts its output budget partway through and silently skips remaining documents in that chunk. No `finish_reason="length"` flag is triggered—adaptive retry cannot detect the failure.

**Impact:** Phase 1 missed critical cross-document relationships and entity variants (e.g., "aaff International B.V." appeared 3× with different node IDs).

**Solution:** Two-pass extraction with smaller chunks:
1. **Pass 1:** `--token-budget 25000` (reduces chunk size → more frequent completions)
2. **Pass 2:** Re-scan with `--force` to catch any missed documents from Pass 1

---

## Phase 2: Production Extraction (100-werk)

### Recommended Approach

**Question 1: Google Workspace Authentication**
- **Decision:** Defer `gws auth login -s drive`
  - Only needed if .gsheet/.gdoc shortcuts exist in corpus
  - Not blocking for Phase 2
  - Can run later: `gws auth login -s drive` (user-only OAuth action)
  - Current 100-werk has zero .gsheet/.gdoc content → skip for now

**Question 2: Graph Strategy (Monolithic vs. Per-Submap)**
- **Decision:** Monolithic extraction over entire 100-werk
  - Reason: Entity fragmentation occurs either way (same entity extracted from different files = different node IDs initially)
  - Deduplication (--dedup-llm) consolidates variants post-extraction
  - Per-submap + merge would increase LLM cost (~17 passes for 17 dossiers) without solving fragmentation
  - Monolithic is cheaper and simpler; dedup handles consolidation

### Execution Plan

**Step 1: Pass 1 – Aggressive Extraction**
```bash
cd /Users/adnanavdic/Documents/Werk\ aaff/100-werk
GRAPHIFY_MAX_OUTPUT_TOKENS=32768 graphify extract . \
  --backend gemini \
  --token-budget 25000 \
  --dedup-llm \
  --force
```

**Expected output:**
- ~400–600 nodes (vs. 75 in 3.PSY)
- High coverage (~70–80% of documents with ≥1 node)
- Cost: ~$0.80–$1.20 USD

**Step 2: Pass 2 – Catch Missrates**
```bash
cd /Users/adnanavdic/Documents/Werk\ aaff/100-werk
GRAPHIFY_MAX_OUTPUT_TOKENS=32768 graphify extract . \
  --backend gemini \
  --token-budget 25000 \
  --dedup-llm \
  --force
```
(Same command; `--force` clears cache, re-scans empty documents)

**Expected output:**
- Incremental nodes (50–150, varies by luck of chunk assignment)
- Further entity consolidation via --dedup-llm
- Cost: ~$0.40–$0.60 USD

**Step 3: Verify Deduplication**
```bash
graphify query "aaff International B.V."
```
Should return **single consolidated node** (not 3 fragmented versions).

**Step 4: Cross-Dossier Relationship Test**
Run three queries to confirm multi-file extraction:
```bash
graphify query "tax audit requirements"
graphify path "3.PSY tax dossier" "100-werk audit finding"
graphify explain "invoice flow across dossiers"
```

**Step 5: Cluster Analysis (Optional, No LLM Cost)**
```bash
graphify cluster . --resolution 1.4 --force
```
(Leiden clustering with adjusted resolution for finer granularity)

**Step 6: Merge Graphs (3.PSY + 100-werk)**
```bash
graphify global add graphify-out/graph.json
```
Creates `/Users/adnanavdic/Documents/Werk\ aaff/3.PSY/graphify-out/global_merged.json`  
Enables queries across both corpora.

---

## Technical Reference

### Key Parameters
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `--token-budget` | 25000 | Reduce chunk size; more frequent LLM completions |
| `GRAPHIFY_MAX_OUTPUT_TOKENS` | 32768 | Max output per request (if API accepts) |
| `--dedup-llm` | enabled | Semantic deduplication for "aaff International B.V." variants |
| `--force` | (Pass 2 only) | Clear cache and re-scan previously empty documents |
| Clustering resolution | 1.4 | Finer communities (default ~1.0) |

### File Structure
```
100-werk/
├── graphify-out/
│   ├── graph.json              (main knowledge graph)
│   ├── clusters.json           (Leiden community assignments)
│   ├── cache/                  (SHA256-keyed semantic cache)
│   └── GRAPH_REPORT.md         (architecture summary)
├── .graphifyignore             (exclusion patterns)
└── [17 client dossiers + misc files]

3.PSY/
└── graphify-out/
    ├── graph.json
    └── [Phase 1 results]
```

---

## Success Criteria for Phase 2

- [ ] Pass 1 completes without errors; logs show ≥70% document coverage
- [ ] Pass 2 catches ≥50 missed documents from Pass 1
- [ ] `graphify query "aaff International B.V."` returns single consolidated node
- [ ] Cross-dossier test queries return ≥3 edges linking 3.PSY ↔ 100-werk
- [ ] Final graph: ≥400 nodes, ≥350 edges, ≥20 communities
- [ ] Total cost: ≤$2.00 USD

---

## Next Steps (In Order)

1. **Run Phase 2 Pass 1** (automated extraction on 100-werk with smaller chunks)
2. **Run Phase 2 Pass 2** (catch-up pass for missed documents)
3. **Verify deduplication** (check if "aaff International B.V." is consolidated)
4. **Run test queries** (confirm cross-dossier relationships)
5. **Cluster & merge** (optional: refine communities, create global graph)
6. **Document findings** (export analysis, share with stakeholders)

---

## Known Limitations & Notes

- **Entity fragmentation (expected):** Same entity extracted from different files initially gets different node IDs. `--dedup-llm` consolidates via semantic similarity (Jaro-Winkler + context). Manual review of merged nodes may be needed for 10–15% edge cases.
- **Scanned PDFs (recovered):** 23k+ words recovered via OCR; quality varies. Numerical data may be misread; validate critical figures manually.
- **Google Workspace (deferred):** `.gsheet`/`.gdoc` shortcuts in corpus will remain as stubs until `gws auth login -s drive` is run. Not blocking for Phase 2.
- **Cache behavior:** Semantic cache keyed by file content SHA256. If extraction method changes (e.g., LLM backend switch), cache is stale and should be cleared (moved to scratchpad for archival).

---

## Questions Before Phase 2 Execution

**Ready to proceed?** Confirm:
- [ ] Phase 2 Pass 1 & 2 should run as specified above
- [ ] Monolithic extraction (not per-submap) is approved
- [ ] `gws auth login -s drive` can be deferred
- [ ] Accept $2.00 USD budget for Phase 2

**When confirmed, run:**
```bash
cd /Users/adnanavdic/Documents/Werk\ aaff/100-werk
# Pass 1
GRAPHIFY_MAX_OUTPUT_TOKENS=32768 graphify extract . --backend gemini --token-budget 25000 --dedup-llm --force
# [Wait for completion, ~5–10 min]
# Pass 2
GRAPHIFY_MAX_OUTPUT_TOKENS=32768 graphify extract . --backend gemini --token-budget 25000 --dedup-llm --force
```

Then report results and proceed with verification steps.

---

**Document version:** 1.0 (Phase 0–1 complete)  
**Last updated:** 2026-09-30  
**Next review:** After Phase 2 Pass 2 completion
