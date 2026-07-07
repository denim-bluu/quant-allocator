# E3 · Manager Knowledge Graph & Retrieval — Method Spec

**Date:** 2026-07-07
**Status: Reviewed — method gate passed 2026-07-07 (rulings in §8)**
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § E3
**Demo:** gallery page `e3.html` (graph exhibit + one-command meeting-prep brief; authored synthetic corpus, §5)

---

## 1. What this is

E3 is an **information-architecture** card, not an estimator. The team's collective
memory of a manager lives in prose — quarterly letters, due-diligence questionnaires
(DDQs), and meeting notes — and today it is unqueryable: to answer *"what did this
manager say about liquidity in 2024, and did the book back it up?"* someone reads back
through a folder by hand. E3 turns that document trail into two things. First, a **typed
entity graph**: every document is parsed into records for the entities it mentions —
**manager, strategy, person, view, theme, meeting, document** — each carrying **dates and
provenance** (which sentence, which file, which date it came from). Second, a **hybrid
retrieval layer** over that graph — lexical search plus semantic (embedding) search,
fused and then expanded along the graph's edges — so a question about a manager can
follow the entities (this person, who moved from that firm; this theme, across these
letters) rather than matching keywords alone.

The **product is not a chatbot**. It is a small set of **decision-anchored artifacts**:
a **meeting-prep brief** produced by one command (last quarter's stated views, open
questions carried over from prior notes, the say–do flags from M5, and the S2 tear
sheet, assembled in seconds), and a handful of **decision-hook queries** ("what did they
say about X in year Y?"). The card's stated non-goal is binding: *no chatbot without a
decision hook — the hooks are the product.* Two honesty commitments travel with
everything E3 emits. Extraction is LLM-assisted, so **no claim about a real document
renders until an eval harness has cleared the extraction** (the M5 precedent, §6.3). And
the graph layer must **earn its complexity**: if graph expansion does not beat a plain
retrieval baseline on the eval set (§3.5), E3 **simplifies to extraction tables plus
search and says so** — the kill criterion, in writing.

The consumers are the **investment team** (daily, at meeting prep and underwriting) and
the team's future members, who inherit the institutional memory. The decisions it feeds
are **engage** (walk into a manager call already knowing what was said and what is still
open) and **select** (institutional memory available at the moment of underwriting). It
is the verbatim "institutionalizing and expanding the team's collective domain knowledge"
mandate, made into a tool.

## 2. Why we use it

The decision problem is **recall of what the team already knows** at the moment a
decision is made. A manager relationship accretes a paper trail over years; the value in
it is locked up because nobody can query it, so meeting prep re-derives from scratch and
underwriting forgets what a prior analyst learned. The naive alternatives each fail in a
specific, nameable way.

- **Keyword search (grep the folder).** Finds documents that contain the exact word and
  nothing else. It cannot answer an entity question — *"what did the portfolio manager who
  now runs Corvid Lane say at her prior shop?"* requires knowing that a **person** moved
  between two **managers**, which no keyword carries — and it misses paraphrase: a note
  that discusses "redemption gates and cash buffers" is squarely about **liquidity** but
  shares no token with the word "liquidity." Keyword search is precise on the literal and
  blind to everything else.
- **Dump everything into a chatbot / plain retrieval-augmented generation (RAG).** This is
  the commonplace 2026 answer, and on its own it is the trap. Plain RAG retrieves passages
  by semantic similarity and lets a model narrate them, which produces a *plausible-sounding*
  answer with **no provenance the reader can check**, **no entity scoping** (it cannot
  reliably tell a liquidity passage about *this* manager from one about a different firm
  that used the same words), and **no way to follow a person or a theme across documents**.
  Worse, it offers no measurable notion of whether it retrieved the right thing. A RAG demo
  is easy to build and hard to trust.
- **Stand up a graph database and an ontology up front.** The over-engineered answer:
  months of schema and infrastructure for a corpus of a few hundred documents, before there
  is any evidence the graph structure improves an answer over plain search. That is
  complexity bought on spec.

What E3 wins over all three is **decision-anchored retrieval with provenance, entity
scoping, and a measured warrant that the graph pays for itself.** Every retrieved passage
carries the sentence and date it came from (a reader can verify it). The graph scopes a
query to a manager and follows its people and themes, so it catches the paraphrased note
the keyword search misses *and* drops the wrong-firm passage the semantic search pulls in
(§3.2). And the card refuses to assert the graph's value — it **measures** it against a
plain-RAG baseline on a planted eval set (§3.5), and if the graph loses, it ships the
simpler thing. The differentiator is never "we built RAG"; it is **the schema, the
decision hooks, and the honesty that the technology is not the point.**

- **Decisions improved:** **engage** — a meeting-prep brief that turns 30 minutes of
  folder-reading into 30 seconds; **select** — institutional memory (prior views, prior
  concerns, who said what) available at underwriting.
- **Customer:** the investment team (daily); the team's future members (inherited memory).

## 3. How it works

### 3.1 The mental model, before any math

Picture the system as **two layers stacked on the document trail**.

**Layer one — extraction into a typed graph.** Each incoming document is read once by a
language model whose only job is to turn prose into **structured records** with
provenance: this letter, dated April 2024, is by **person** *Elena Voss*, is a
**document** of type *letter* attributed to **manager** *Corvid Lane Capital*, and
expresses these **views** on these **themes**, each pinned to the exact sentence it came
from. This is a *reading* task — extracting who-said-what — and it is **the same station
one as M5** (the say–do monitor): E3 reuses M5's extraction call and schema and adds the
graph-entity slots (person, meeting, document type, employment edges). The model never
renders a judgement; it records facts and where they came from.

**Layer two — hybrid retrieval, then graph expansion.** A question is answered in three
moves. (i) **Lexical retrieval** (BM25) ranks documents by exact-term overlap — precise,
literal, and blind to paraphrase. (ii) **Dense retrieval** ranks documents by *semantic*
similarity of embeddings — it catches "redemption gates" as being about liquidity, but it
has no notion of which manager a passage belongs to, so it will happily surface a
liquidity passage from the wrong firm. (iii) The two rankings are **fused** (reciprocal
rank fusion), and then the fused list is **scoped and expanded along the graph's edges**:
the query is entity-linked to a **manager** node, and the candidate set becomes the
documents *about that manager* **union** the documents *authored by the people who work or
worked there*. That last union is the whole point — it pulls in a meeting note that never
names the firm but was written by the manager's PM, which neither retriever could have
tied to the manager on text alone.

**The graph is deliberately light.** It is a set of **typed tables in DuckDB/SQLite** with
foreign-key edges — not a graph database. A graph DB is introduced only if and when the
graph earns it (right-level engineering; the card's kill criterion). At a corpus of
hundreds to low-thousands of documents, joins over indexed tables answer every
one-to-two-hop question E3 needs, and the schema stays legible to a new team member.

**E3 makes no statistical estimate.** It does not infer skill, rank managers, or fit any
model of returns. The only numbers it produces are **retrieval-quality metrics** (§3.5) —
information-retrieval measurements, not inference. Where the rest of the campaign leans on
hierarchical shrinkage at small N, E3 has nothing to shrink: it is a search-and-structure
card, and its honesty lives in the eval, not in a posterior.

### 3.2 A worked toy example — where the graph earns its keep

Take a six-document corpus for one manager relationship and the query **"corvid lane
liquidity 2024."** Three documents are genuinely on-topic (the **planted relevant set**):
a Q1 2024 **letter** that says the book is "comfortable with portfolio liquidity," a 2024
**DDQ** stating "liquidity terms … quarterly redemption with ninety day notice," and a
May-2024 **meeting note** in which the PM "walked through how redemption gates would apply
under stress and how she sizes cash buffers." The corpus also contains a **distractor**: a
DDQ from a *different* firm (Wexford Green Capital) that also says "liquidity … notice
terms."

Watch each retriever in isolation, over all six documents:

- **Lexical (BM25)** ranks the meeting note **dead last (6th of 6)**. The note is exactly
  on-topic but shares *no token* with the query — it says "redemption gates" and "cash
  buffers," never "liquidity," never "corvid lane." A pure keyword system misses it.
- **Dense (embeddings)** pulls the **wrong-firm distractor to rank 2**. It correctly reads
  the distractor as being about liquidity — but it has no idea the passage belongs to a
  different manager, so it surfaces it above genuinely relevant Corvid Lane material.

Now fuse and add the graph. **Plain RAG** (lexical + dense fused, *no graph*) returns, at
$k=3$: `[DDQ-2024, DDQ-WEX, L-2024Q1]` — **recall@3 = 0.67, precision@3 = 0.67**. It
grabbed the wrong-firm distractor and still missed the paraphrased note. **Graph-augmented
retrieval** first entity-links "corvid lane" to the manager node and builds the candidate
set = {documents about Corvid Lane} ∪ {documents by people employed at Corvid Lane}. That
union **includes** the meeting note (its author, Elena Voss, is a Corvid Lane PM) and
**excludes** the Wexford distractor (wrong firm, unrelated author). Ranking the fused
scores within that set returns, at $k=3$: `[DDQ-2024, L-2024Q1, MTG-2024-05]` — **recall@3
= 1.00, precision@3 = 1.00**.

The fusion arithmetic is worth seeing once, because it is the whole of the ranking math.
Reciprocal rank fusion assigns each document the sum, over the retrievers, of
$1/(k_{\text{rrf}} + \text{rank})$ with $k_{\text{rrf}} = 60$. Within the graph candidate
set the meeting note ranks **5th on BM25** (still a near-lexical-miss) but **2nd on dense**
(a clean concept match), so its fused score is
$$\frac{1}{60 + 5} + \frac{1}{60 + 2} = 0.01538 + 0.01613 = 0.03151,$$
which lands it **3rd overall** — inside the top-3. The Q1 letter (BM25 rank 2, dense rank
3) scores $\tfrac{1}{62} + \tfrac{1}{63} = 0.03200$, and the DDQ (rank 1 on both) tops the
list at $\tfrac{2}{61} = 0.03279$. Same fusion rule, three documents, and the note the
keyword search buried is now surfaced — **because the graph put it in the room, and the
dense retriever recognized it once it was there.** That is the card's entire value
proposition in one query: recall **0.67 → 1.00** and precision **0.67 → 1.00**, and it is
reproduced from first principles by the code in §4.

### 3.3 The entity–relation schema (the information architecture)

The graph is a fixed, small set of **typed node tables** and **edge tables**. Every row
carries **provenance** — the `source_doc`, `source_span` (the verbatim sentence), and
`as_of` date — so any fact the graph asserts can be traced to the sentence that produced
it. The node types are exactly those the card names:

| Node type | Key fields | Provenance carried |
| --- | --- | --- |
| **manager** | firm id, name, **current tier (R/E/P)**, strategy id | first-seen doc, tier-grant date |
| **strategy** | strategy id, label (e.g. equity long/short) | — (controlled vocabulary) |
| **person** | person id, name, role | source_doc, source_span |
| **document** | doc id, type ∈ {letter, DDQ, meeting-note}, date, manager id, author id | file path, ingest date |
| **view** | direction, theme id, horizon, conviction (the **M5 view schema**) | source_doc, **source_span (the quote)** |
| **theme** | theme id, label (controlled vocabulary: liquidity, duration, momentum, …) | — |
| **meeting** | meeting id, date, attendees, linked doc id | meeting-note doc |

The **edge tables** are the joins that make it a graph:

- `authored_by` (document → person), `attributed_to` (document → manager),
- `employed_by` (person → manager, with `from`/`to` dates — this is the edge that lets a
  query follow a PM across firms),
- `expresses` (document → view), `about_theme` (view → theme),
- `discussed_at` (view → meeting).

Two design choices are load-bearing and worth stating. **Provenance is mandatory, not
optional** — a `view` with no `source_span` is a lint error, exactly as a bare point
estimate is a lint error elsewhere in the design system; a fact you cannot trace to a
sentence is not admitted. And the **manager node records its own tier and what was promised
when** — the graph is *orthogonal* to the R/E/P ladder (documents exist for every manager
regardless of tier), but it is the natural home for the record of *which* tier a manager is
at and *what transparency they committed to at which date* (the E1 ladder's state), because
that record is itself a dated, sourced fact about the relationship.

### 3.4 The retrieval math, with every symbol

Retrieval is **deterministic scoring** — given the corpus and the query, the ranking is
fixed. There is no probability model and no distributional assumption in the ranking
itself; the only statistics in the whole card are the eval metrics of §3.5, computed over a
query set. Three scoring rules and one set operation.

**(a) Lexical relevance — BM25.** For a query $q$ with terms $\{t\}$ and a document $d$,
$$\text{BM25}(q, d) = \sum_{t \in q} \text{idf}(t)\,
\frac{f(t, d)\,(k_1 + 1)}{f(t, d) + k_1\big(1 - b + b\,\frac{|d|}{\overline{|d|}}\big)},
\qquad
\text{idf}(t) = \ln\!\Big(1 + \frac{N - n(t) + 0.5}{n(t) + 0.5}\Big).$$

where:

- $f(t, d)$ — the **term frequency**: how many times term $t$ appears in document $d$.
- $|d|$ — the length of document $d$ in tokens; $\overline{|d|}$ — the average document
  length in the corpus. The ratio $|d| / \overline{|d|}$ **length-normalizes**, so a long
  document does not score highly just for being long.
- $N$ — the number of documents in the corpus; $n(t)$ — the number of documents containing
  $t$. The **inverse document frequency** $\text{idf}(t)$ up-weights rare, discriminating
  terms and down-weights common ones.
- $k_1$ — the **term-frequency saturation** constant (**`BM25_K1` = 1.5, provisional —
  NUMERICS-GATE**): larger $k_1$ lets repeated terms keep adding score; the saturating form
  means the 5th occurrence adds less than the 1st.
- $b$ — the **length-normalization** constant (**`BM25_B` = 0.75, provisional —
  NUMERICS-GATE**): $b = 1$ fully normalizes by length, $b = 0$ not at all.

*In words:* a document scores highly when it contains the query's **rare** terms **often**,
adjusted so length and repetition do not run away. BM25 is precise on the literal word and,
by construction, blind to synonyms — which is exactly the gap the dense retriever fills.

**(b) Semantic relevance — dense (embedding) cosine.** Each document and the query are
mapped to vectors $\mathbf{v}_d, \mathbf{v}_q \in \mathbb{R}^{m}$ by an embedding model, and
scored by cosine similarity:
$$\text{dense}(q, d) = \cos(\mathbf{v}_q, \mathbf{v}_d)
= \frac{\mathbf{v}_q \cdot \mathbf{v}_d}{\lVert \mathbf{v}_q \rVert\,\lVert \mathbf{v}_d \rVert}.$$

where:

- $\mathbf{v}_q, \mathbf{v}_d$ — the embedding vectors of the query and document: a learned
  numeric summary in which passages with **similar meaning** sit close together, so "redemption
  gates" lands near "liquidity" even with no shared word.
- $m$ — the embedding dimension, fixed by the model (**`EMBEDDING_MODEL`, provisional —
  NUMERICS-GATE**: the live choice of sentence-embedding model is a gate question; the demo
  uses a small authored concept table as a self-contained stand-in, §4).
- $\cos(\cdot,\cdot) \in [-1, 1]$ — the angle between the two vectors; 1 is identical
  direction (maximally similar), 0 is unrelated.

*In words:* dense retrieval scores **meaning overlap**, catching paraphrase the lexical
score cannot — at the cost of having no idea which *entity* a passage belongs to, which is
why it needs the graph.

**(c) Fusing the two — reciprocal rank fusion (RRF).** Rather than reconcile BM25's and
cosine's incommensurable score scales, RRF fuses their **rank positions**:
$$\text{RRF}(d) = \sum_{r \in \{\text{bm25},\,\text{dense}\}} \frac{1}{k_{\text{rrf}} + \text{rank}_r(d)}.$$

where:

- $\text{rank}_r(d)$ — the 1-based position of document $d$ in retriever $r$'s ranking (rank
  1 = top).
- $k_{\text{rrf}}$ — the **fusion constant** (**`RRF_K` = 60, provisional — NUMERICS-GATE**;
  the Cormack–Clarke–Büttcher default): it damps the contribution of top ranks so no single
  retriever dominates, and makes the fusion robust to score-scale differences.

*In words:* a document ranked highly by **either** retriever gets credit, and a document
ranked highly by **both** gets the most — the §3.2 arithmetic ($\tfrac{2}{61}$ for a
rank-1/rank-1 document) is this formula.

**(d) Graph expansion.** Let the query entity-link to a manager node $M$. The candidate set
is
$$C(M) = \{d : \text{attributed\_to}(d) = M\} \;\cup\;
\{d : \text{authored\_by}(d) = p,\; \text{employed\_by}(p, M)\},$$
computed within **`GRAPH_EXPANSION_HOPS` = 1 (provisional — NUMERICS-GATE)** hop of $M$
(manager → its people → their documents). Retrieval then ranks $C(M)$ by $\text{RRF}(d)$.

where:

- $C(M)$ — the **candidate set**: documents *about* the manager, unioned with documents *by
  the people who work or worked there*. The union is the mechanism that recovers the
  firm-unnamed meeting note (§3.2).
- `GRAPH_EXPANSION_HOPS` — how far to walk from the anchor entity; **1 hop** (manager ↔
  person ↔ document) is the v1 default. Two hops (e.g. manager → theme → other managers'
  views on the same theme) is a flagged extension, off by default, because it trades
  precision for reach.

*In words:* the graph **scopes** retrieval to the right entity and **expands** it along the
edges text alone cannot see, then hands the scoped set to the same hybrid ranker.

### 3.5 The eval — the load-bearing gate (retrieval must beat plain RAG)

E3 has **no statistical power axis**; its gate is an **information-retrieval eval on a
planted-truth corpus**, run twice — once for extraction, once for retrieval — and it is the
whole warrant for the card.

**Retrieval eval (does the graph earn its keep?).** Build a query set where each query's
**relevant documents are known by construction** (planted at corpus-generation time, §6.4).
For each query, retrieve two ways — **plain RAG** (hybrid, no graph) as the **baseline**,
and **graph-augmented** — and score both with standard IR metrics:

- **recall@$k$** — fraction of the relevant documents that appear in the top $k$.
- **precision@$k$** — fraction of the top $k$ that are relevant.
- **MRR** (mean reciprocal rank) — $1/\text{rank}$ of the first relevant document, averaged
  over queries.
- **nDCG@$k$** — a rank-discounted gain, reported where graded relevance matters.

The **gate**: graph-augmented retrieval must **beat the plain-RAG baseline** on the primary
metric (recall@`RETRIEVAL_TOPK`, with **`RETRIEVAL_TOPK` = 10, provisional —
NUMERICS-GATE**) by a stated margin — **`RETRIEVAL_GATE_UPLIFT`, provisional —
NUMERICS-GATE** — with the margin judged **significant** under the seeded-replication +
Wilson-interval discipline borrowed from the X1 atlas (§6.3), not by a single point. **If
the graph does not clear the baseline, E3 ships as extraction tables + hybrid search with
no graph layer, and the page says so.** This is the card's central kill criterion turned
into a measurement.

**Extraction eval (is the reading trustworthy?).** This **reuses M5's harness directly**
(shared corpus, shared station one): per-slot **precision and recall** on the schema slots
(direction, theme-mapping, person, document-type, date, quote-span), with the go/no-go gate
**`EXTRACTION_GATE`: precision ≥ 0.8 AND recall ≥ 0.8** per core slot (M5 §6.2). No claim
about a **real** document renders until this passes; miss it after two prompt/model
iterations and the affected slot **stays demo-only**, in writing.

### 3.6 What the canonical work contributes

- **Robertson & Zaragoza (2009), "The Probabilistic Relevance Framework: BM25 and Beyond."**
  The definitive treatment of BM25 (§3.4a): why the saturating term-frequency form and
  length normalization make it the durable lexical baseline that dense methods must
  *complement*, not replace. E3's lexical channel is BM25 for exactly this reason.
- **Karpukhin et al. (2020), "Dense Passage Retrieval for Open-Domain Question Answering."**
  Showed that learned dense embeddings retrieve passages by *meaning*, materially beating
  lexical retrieval on paraphrase — and, crucially, that dense and lexical retrieve
  *different* relevant documents, which is the empirical case for fusing them rather than
  choosing one. E3's dense channel and the §3.2 paraphrase recovery are this result.
- **Cormack, Clarke & Büttcher (2009), "Reciprocal Rank Fusion Outperforms Condorcet and
  Individual Rank Learning Methods."** Established RRF (§3.4c) as a simple, robust,
  training-free way to combine rankings from incommensurable scorers — the reason E3 fuses
  on rank position with a single constant rather than tuning score weights.
- **Lewis et al. (2020), "Retrieval-Augmented Generation for Knowledge-Intensive NLP
  Tasks."** Defined the RAG pattern that is E3's **baseline** — the thing the graph layer
  must beat on the eval (§3.5). E3 takes RAG's retrieve-then-read structure and adds the two
  things plain RAG lacks: entity structure and a measured warrant.
- **Hogan et al. (2021), "Knowledge Graphs" (ACM Computing Surveys), and Edge et al. (2024),
  "From Local to Global: A Graph RAG Approach."** The former is the reference for the typed
  entity–relation data model (§3.3); the latter is the modern statement that graph structure
  over a corpus can improve retrieval — while E3 holds the honest line that this must be
  *demonstrated on the eval*, not assumed, and that a light typed-table graph is the
  right-level realization until scale forces more.
- **Manning, Raghavan & Schütze, *Introduction to Information Retrieval*.** The standard
  basis for the eval metrics (§3.5) — precision/recall@$k$, MRR, nDCG — shared with M5's
  extraction eval.

## 4. How to implement

The reference implementation below is **self-contained teaching code** — paste it into a
fresh file, it runs on the Python standard library alone (no third-party packages, no
project imports, no repo paths). It implements the retrieval layer of §3: BM25 (§3.4a), a
dense stand-in via an authored concept table (§3.4b — the live build swaps in a real
sentence-embedding model), reciprocal rank fusion (§3.4c), graph expansion (§3.4d), and the
retrieval eval (§3.5). Running it reproduces the §3.2 numbers exactly: **plain RAG recall@3
= 0.67, graph-augmented recall@3 = 1.00.**

```python
"""E3 mock: hybrid retrieval (BM25 + dense stand-in) with graph expansion,
plus a retrieval eval that scores graph-augmented vs plain-RAG on planted truth.
Standard library only. No hash()-derived seeds. Authored constants throughout.
"""

from __future__ import annotations

import math
from collections import Counter

# --- Typed entities + provenance. Authored constants (fictional names). ---
# Each document is a node; person/manager tags are edges into the light graph.
DOCS: dict[str, dict] = {
    "L-2024Q1": {
        "text": "first quarter letter corvid lane capital we remain constructive on "
                "us front end duration and comfortable with portfolio liquidity",
        "author": "elena voss", "manager": "corvid lane capital", "year": 2024,
    },
    "DDQ-2024": {
        "text": "due diligence questionnaire corvid lane capital investor liquidity "
                "terms quarterly redemption with ninety day notice and no side pockets",
        "author": "elena voss", "manager": "corvid lane capital", "year": 2024,
    },
    "MTG-2024-05": {
        # A meeting note that never names the firm and never says "liquidity".
        "text": "meeting note elena voss walked through how redemption gates would "
                "apply under stress and how she sizes cash buffers against them",
        "author": "elena voss", "manager": None, "year": 2024,
    },
    "L-2023Q3": {
        "text": "third quarter letter selby point advisors momentum has become crowded "
                "and we have trimmed the factor",
        "author": "elena voss", "manager": "selby point advisors", "year": 2023,
    },
    "L-2024Q3": {
        "text": "third quarter letter corvid lane capital we added to energy equities "
                "and kept net exposure disciplined",
        "author": "elena voss", "manager": "corvid lane capital", "year": 2024,
    },
    "DDQ-WEX": {
        # Wrong-firm liquidity distractor: matches "liquidity" but not the manager.
        "text": "due diligence questionnaire wexford green capital monthly liquidity "
                "with thirty day notice terms",
        "author": "priya anand", "manager": "wexford green capital", "year": 2024,
    },
}

# Employment edges (person -> firms). Elena Voss moved Selby Point -> Corvid Lane.
EMPLOYED_BY = {
    "elena voss": {"corvid lane capital", "selby point advisors"},
    "priya anand": {"wexford green capital"},
}

# --- Dense stand-in: an authored concept table, NOT a trained model. ---
# Live build swaps in a sentence-embedding model; this fixed map keeps the demo
# self-contained and shows dense retrieval catching a paraphrase ("redemption
# gates", "cash buffers") that shares no tokens with the query word "liquidity".
CONCEPT_OF_TERM = {
    "duration": "duration", "liquidity": "liquidity", "redemption": "liquidity",
    "gates": "liquidity", "cash": "liquidity", "buffers": "liquidity",
    "notice": "liquidity", "momentum": "momentum", "energy": "energy",
    "net": "net_exposure",
}
CONCEPTS = ["duration", "liquidity", "momentum", "energy", "net_exposure"]


def concept_vector(text: str) -> list[float]:
    counts = Counter(CONCEPT_OF_TERM[w] for w in text.split() if w in CONCEPT_OF_TERM)
    return [float(counts.get(c, 0)) for c in CONCEPTS]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


# --- BM25 (Robertson-Zaragoza), the lexical/sparse retriever. ---
BM25_K1 = 1.5   # provisional (NUMERICS-GATE)
BM25_B = 0.75   # provisional (NUMERICS-GATE)


def bm25_scores(query: str, doc_ids: list[str]) -> dict[str, float]:
    q_terms = query.split()
    docs = {d: DOCS[d]["text"].split() for d in doc_ids}
    n_docs = len(docs)
    avg_len = sum(len(t) for t in docs.values()) / n_docs
    df = Counter()
    for tokens in docs.values():
        for term in set(tokens):
            df[term] += 1
    scores: dict[str, float] = {}
    for d, tokens in docs.items():
        tf = Counter(tokens)
        dl = len(tokens)
        s = 0.0
        for term in q_terms:
            if term not in df:
                continue
            idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
            freq = tf[term]
            denom = freq + BM25_K1 * (1 - BM25_B + BM25_B * dl / avg_len)
            s += idf * (freq * (BM25_K1 + 1)) / denom if denom > 0 else 0.0
        scores[d] = s
    return scores


def dense_scores(query: str, doc_ids: list[str]) -> dict[str, float]:
    qv = concept_vector(query)
    return {d: cosine(qv, concept_vector(DOCS[d]["text"])) for d in doc_ids}


def rank(scores: dict[str, float]) -> list[str]:
    return [d for d, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


# --- Reciprocal Rank Fusion (Cormack-Clarke-Buttcher). ---
RRF_K = 60  # provisional (NUMERICS-GATE); the paper's default constant.


def rrf(rankings: list[list[str]], doc_ids: list[str]) -> dict[str, float]:
    fused = {d: 0.0 for d in doc_ids}
    for ranking in rankings:
        for pos, d in enumerate(ranking):
            fused[d] += 1.0 / (RRF_K + pos + 1)
    return fused


def hybrid_rank(doc_ids: list[str], query: str) -> list[str]:
    bm = rank(bm25_scores(query, doc_ids))
    dn = rank(dense_scores(query, doc_ids))
    return rank(rrf([bm, dn], doc_ids))


# --- Graph expansion: entity-link the query to a manager node, then gather the
#     candidate set = docs about that manager UNION docs by its people. ---
GRAPH_EXPANSION_HOPS = 1  # provisional (NUMERICS-GATE)


def graph_candidates(manager: str) -> list[str]:
    people = {p for p, firms in EMPLOYED_BY.items() if manager in firms}
    cand = set()
    for d, meta in DOCS.items():
        if meta["manager"] == manager or meta["author"] in people:
            cand.add(d)
    return sorted(cand)


# --- Retrieval eval on planted ground truth. ---
def recall_at_k(ranking: list[str], relevant: set[str], k: int) -> float:
    hits = sum(1 for d in ranking[:k] if d in relevant)
    return hits / len(relevant)


def precision_at_k(ranking: list[str], relevant: set[str], k: int) -> float:
    hits = sum(1 for d in ranking[:k] if d in relevant)
    return hits / k


def mrr(ranking: list[str], relevant: set[str]) -> float:
    for pos, d in enumerate(ranking):
        if d in relevant:
            return 1.0 / (pos + 1)
    return 0.0


if __name__ == "__main__":
    query = "corvid lane liquidity 2024"
    relevant = {"L-2024Q1", "DDQ-2024", "MTG-2024-05"}   # planted truth
    all_docs = list(DOCS.keys())
    K = 3

    plain = hybrid_rank(all_docs, query)              # plain RAG: no graph
    cand = graph_candidates("corvid lane capital")
    graph = hybrid_rank(cand, query)                  # graph-augmented

    print("plain RAG top-3 :", plain[:K])
    print("graph      top-3:", graph[:K])
    print(f"plain  recall@{K}={recall_at_k(plain, relevant, K):.2f} "
          f"prec@{K}={precision_at_k(plain, relevant, K):.2f} "
          f"MRR={mrr(plain, relevant):.2f}")
    print(f"graph  recall@{K}={recall_at_k(graph, relevant, K):.2f} "
          f"prec@{K}={precision_at_k(graph, relevant, K):.2f} "
          f"MRR={mrr(graph, relevant):.2f}")

    # Where each plain retriever fails, in isolation, on the paraphrased note:
    bm = rank(bm25_scores(query, all_docs))
    dn = rank(dense_scores(query, all_docs))
    print("BM25 rank of MTG note (lexical miss):", bm.index("MTG-2024-05") + 1)
    print("dense pulls wrong-firm distractor DDQ-WEX at:", dn.index("DDQ-WEX") + 1)
    print("graph drops DDQ-WEX from candidate set   :", "DDQ-WEX" not in cand)
```

Running it prints, verbatim:

```
plain RAG top-3 : ['DDQ-2024', 'DDQ-WEX', 'L-2024Q1']
graph      top-3: ['DDQ-2024', 'L-2024Q1', 'MTG-2024-05']
plain  recall@3=0.67 prec@3=0.67 MRR=1.00
graph  recall@3=1.00 prec@3=1.00 MRR=1.00
BM25 rank of MTG note (lexical miss): 6
dense pulls wrong-firm distractor DDQ-WEX at: 2
graph drops DDQ-WEX from candidate set   : True
```

The plain baseline surfaces the wrong-firm distractor and misses the paraphrased note;
graph expansion drops the distractor (it is not in the candidate set) and recovers the note
(via the PM's `authored_by`/`employed_by` edges), taking both recall and precision at 3 from
**0.67 to 1.00** — the §3.2 story, reproduced from first principles. The dense stand-in
(`CONCEPT_OF_TERM`) is a deliberately transparent placeholder for a real embedding model;
swapping it for one does not change the retrieval or graph logic, only the vectors fed to
`cosine`.

## 5. Reading the demo

The gallery page `e3.html` runs on an **authored synthetic corpus** — hand-written letters,
a DDQ, and meeting notes for a fictional manager relationship — because the graph and the
extraction are the exhibit, not a simulator draw (the M5 precedent, §6.4). It has four
parts, and the SYNTHETIC badge and "what this needs to go live" box are always present.

**The graph exhibit — the centerpiece.** A rendered entity–relation graph for one manager,
**Corvid Lane Capital**, showing the typed nodes of §3.3: the **manager**, its **strategy**,
its lead **person** *Elena Voss* (with an `employed_by` edge back to her prior firm **Selby
Point Advisors**, the edge that lets a query follow her across shops), the **documents**
(two letters, a DDQ, two meeting notes), the **views** they express, and the **themes**
those views touch (liquidity, duration, momentum, energy). How each element maps to the
method:

- **Every node and edge is clickable to its provenance** — the source document, the exact
  sentence (`source_span`), and the date (§3.3). A fact with no sentence behind it is not on
  the graph; provenance is the design-system contract, the way an interval band is elsewhere.
- **The `employed_by` edge to Selby Point** is the graph's signature move made visible: it is
  why a question about Corvid Lane can reach a note written by Elena Voss before the firm's
  name ever appears.
- **The manager node's TierBadge** shows the recorded R/E/P tier and the date it was granted —
  the graph as the home of the E1 ladder's state (§3.3).

**The meeting-prep brief — the wow-demo.** One command
(`python -m quant_allocator.knowledge brief --manager "Corvid Lane Capital"`) composes a
print-clean brief via the **E2 pack layer**: last quarter's **stated views** (from the M5
extraction schema), **open questions carried over** from prior meeting notes, the **say–do
flags** (M5's aligned/partial/contradicted verdicts), and the **S2 tear sheet**. This is the
"30-minute prep in 30 seconds" claim, rendered — and it is explicitly a *composition* of
existing cards' outputs over the graph, not a new estimator.

**The retrieval panel.** The §3.2 query, "what did Corvid Lane say about liquidity in 2024?",
run three ways side by side: **lexical only** (misses the paraphrased meeting note — it ranks
6th), **plain hybrid RAG** (surfaces the wrong-firm Wexford distractor at rank 2), and
**graph-augmented** (drops the distractor, recovers the note; top-3 = DDQ, Q1 letter, meeting
note). Each returned passage shows its **provenance chip** (document + sentence + date). The
reader sees *why* the graph answer is the right one, not just that it is.

**The eval gate — the honest refusal made visible.** A working PowerGate-style panel showing
the retrieval eval of §3.5: **graph-augmented recall@10 vs the plain-RAG baseline**, with its
seeded-replication interval. The panel states the rule in plain sight: *if the graph does not
clear the baseline by the stated margin, E3 ships as extraction tables + search, no graph.*
On the demo corpus the graph clears it (recall 0.67 → 1.00 on the worked query); the panel
shows the gate **passing**, and states that on real documents the same gate governs whether
the graph layer renders at all.

What an allocator should conclude: the value is not "we built RAG" — RAG is the baseline the
page shows being beaten. The value is the **schema** (entities, provenance, the person-across-
firms edge), the **decision hooks** (the brief, the sourced query), and the **measured
warrant** that the graph earns its complexity, with an honest switch to the simpler system if
it ever does not.

## 6. Honest limits & go-live

### 6.1 What E3 does not do (non-goals and do-not-build adjacency)

- **No chatbot without a decision hook.** The product is the meeting-prep brief and the
  sourced decision-hook queries (§1, §5). A free-form conversational agent with no decision
  anchor is the card's stated non-goal and the standing-non-goal "no chatbots without a
  decision hook" (convergence §4).
- **No LLM-extraction claim without the eval harness.** No fact about a **real** document
  renders until the extraction gate passes (§3.5, M5 precedent). Authored constants in the
  demo; the harness required for live.
- **No graph database, and no graph layer at all, until it is earned.** The graph is light
  typed tables (§3.1); a graph DB waits on scale. The **graph layer itself renders only if it
  beats plain RAG on the eval** (§3.5) — otherwise E3 is extraction tables + hybrid search,
  said out loud.
- **No statistical inference — so the Sweep-C do-not-build list is orthogonal, not
  violated.** E3 estimates no skill, ranks no managers, fits no return model; it therefore
  runs none of the prohibited small-N machinery (persistence rankings, FDR luck-screens,
  regime-split or conditional-beta alphas — convergence §4). It is a search-and-structure
  card, and it says so.
- **Never a mechanical judgement.** A retrieved passage or a carried-over open question is
  material for a human's preparation, never an automatic verdict about a manager.

### 6.2 Data contract per tier

E3 is **orthogonal to the R/E/P ladder**: documents exist for every manager regardless of
transparency tier, and the graph is the *record-keeper* of the tier rather than a consumer of
it. What the tiers change is not whether E3 runs, but how much the brief can **fuse** from
the other cards.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **R** (universal) | The manager's documents — letters, DDQs, meeting notes (dated text/PDF); **public fund letters only in the repo**. | The **whole graph and retrieval layer**: typed entities with provenance, hybrid + graph-expanded search, and a meeting-prep brief carrying the **view inventory, internal-consistency-over-time, and open-questions** (everything document-native). |
| **E** | R + the manager's **exposure summaries** (factor/sector/duration/net), so M5's say–do alignment can run. | The brief additionally carries **say–do flags** (M5's aligned/partial/contradicted) against exposures — a richer prep, same graph. |
| **P** | E + **holdings/positions**. | The brief carries **name-level** say–do alignment where M5 supports it. No new graph machinery; a richer fused brief. |

**Frequency & provenance.** Documents at their native cadence (letters quarterly, DDQs
annually, meeting notes ad hoc); every extracted fact is stamped with its `source_doc`,
`source_span`, and `as_of` date. **Compliance (standing):** any document committed to the
public repo is a **public fund letter/DDQ from an unaffiliated manager**; no employer-internal
documents, processes, or real roster names in code, docs, prompts, or the committed demo
corpus. The demo's manager, prior firm, and person names (**Corvid Lane Capital, Selby Point
Advisors, Wexford Green Capital, Elena Voss, Priya Anand**) are **authored fictional
constants**, chosen to be non-confusable with the existing roster.

### 6.3 The two eval gates (the load-bearing honesty)

E3 has no statistical power axis and **does not contribute cells to the X1 atlas** — it is
orthogonal to the tier-degradation the atlas maps. It does, however, **borrow the atlas's
reporting discipline** ([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md) §3.3): the eval is
run over **seeded replications** (per-module RNG stream tags — no `hash()`-derived seeds) with
**Wilson 95% intervals** on every rate, so the "graph beats plain RAG" claim is an interval,
never a bare point.

1. **Retrieval gate (does the graph earn its keep?).** On the planted-truth query set,
   graph-augmented recall@`RETRIEVAL_TOPK` must beat the plain-RAG baseline by
   **`RETRIEVAL_GATE_UPLIFT`** (both **provisional — NUMERICS-GATE**), significant under the
   Wilson interval / paired bootstrap. **Fail ⇒ ship extraction tables + hybrid search, no
   graph layer** (§6.5 kill criterion).
2. **Extraction gate (is the reading trustworthy?).** Reuses **M5's harness** verbatim
   (shared corpus, shared station one): per-slot precision ≥ 0.8 **and** recall ≥ 0.8
   (**`EXTRACTION_GATE`, provisional — NUMERICS-GATE**) before any real-document fact renders;
   miss after two iterations ⇒ that slot stays demo-only, in writing.

**Provisional constants, gathered for the numerics gate:** `BM25_K1` = 1.5, `BM25_B` = 0.75,
`RRF_K` = 60, `GRAPH_EXPANSION_HOPS` = 1, `RETRIEVAL_TOPK` = 10, `RETRIEVAL_GATE_UPLIFT`
(unset), `EXTRACTION_GATE` = (0.8, 0.8), and `EMBEDDING_MODEL` (live model choice, unset).
Each is a **named constant flagged in-text**; none is a tuned magic number in the code body.

### 6.4 New substrate this card needs (named prerequisites, byte-identical-default discipline)

E3 consumes existing substrate and requires two **new, small, shared** pieces — named here as
gate questions, not hidden.

- **Reused, not rebuilt:** M5's extraction station one and view schema
  (`flagships/saydo/extraction.py`), M5's extraction eval harness (`flagships/saydo/harness.py`),
  the E2 pack-composition layer (`flagships/packs/`) for the brief, the S2 tear-sheet output,
  and the roster names (`demo_data/roster.py`). E3 **imports** these; it does not reimplement
  them.
- **NEW — synthetic-corpus generator, extended to DDQs and meeting notes.** M5's corpus
  generator emits **letters** only; E3's demo and eval need **DDQs and meeting notes** as well
  (the meeting note is the §3.2 hero). This is a small extension of the *shared* corpus
  generator. **Byte-identical-default discipline:** the DDQ/meeting-note emitters are added
  **behind a flag defaulting off**, so M5's existing letter corpus and eval outputs are
  **byte-for-byte unchanged**; E3's demo turns the flag on.
- **NEW — planted retrieval-relevance eval set.** M5 plants *view/alignment* truth; E3
  additionally needs **query → relevant-document** ground truth planted at generation time (a
  query touches a theme and an entity; the documents that genuinely answer it are marked). This
  is what makes the §3.5 retrieval gate measurable without human annotation. Small, and shared
  with any future retrieval card.
- **The graph schema + light table layer** (DuckDB/SQLite typed tables of §3.3) is E3's own
  build, not borrowed substrate — but it introduces **no new heavy dependency** (DuckDB/SQLite
  are file-backed and standard). A graph database is explicitly *not* a prerequisite.

### 6.5 Kill criteria

- **The graph does not beat plain RAG (§3.5, §6.3 gate 1).** If graph-augmented retrieval fails
  to clear the plain-RAG baseline by the stated margin on the eval set, E3 **ships as
  extraction tables + hybrid search, with the graph layer removed**, recorded in writing per
  converge-or-cut. The schema and decision hooks remain valuable; the graph expansion is
  dropped as unearned complexity. *A graph that does not improve the answer is over-engineering,
  and the card is honest enough to delete it.*
- **Extraction below gate (§6.3 gate 2).** Below `EXTRACTION_GATE` after two prompt/model
  iterations ⇒ the affected slot stays **demo-only**; no real-document claim renders.
- **Political / framing.** The brief is preparation material, never an accusation or a
  mechanical trigger. A meeting-prep tool read as a dossier corrodes the transparency the E/P
  rungs depend on (Falk–Kosfeld, via M5 §7); it ships as help-not-audit, provenance always
  attached.

### 6.6 Implementation architecture

Module home: **`src/quant_allocator/flagships/knowledge/`**

- `extraction.py` — **imports M5's station one**; adds the graph-entity slots (person, meeting,
  document-type, `employed_by`) to the shared view schema. One LLM call per document,
  schema-validated on return; provenance (`source_span`, `as_of`) mandatory.
- `graph.py` — the typed-table layer of §3.3 over DuckDB/SQLite: node and edge tables, the
  entity-linking of a query to a manager node, and the `graph_candidates` expansion (§3.4d). No
  graph database.
- `retrieval.py` — the hybrid ranker: BM25, dense (via `EMBEDDING_MODEL`), RRF fusion, and the
  graph-scoped rank (§3.4). Pure functions over the corpus and graph; no I/O.
- `brief.py` — composes the meeting-prep brief via the **E2 pack layer**, fusing the M5 view
  inventory + say–do flags and the S2 tear sheet over the graph. Rendering only; no estimator.
- `eval.py` — the retrieval eval of §3.5 (recall/precision@$k$, MRR, nDCG, graph-vs-baseline with
  Wilson intervals); **reuses M5's `harness.py`** for the extraction gate.
- Demo: **`src/quant_allocator/demo_data/e3_knowledge.py`** — imports the same pipeline; only the
  input corpus is the authored synthetic set. Emits committed JSON to `site/data/e3_knowledge.json`
  via `_emit.write_json`; **CI renders the page from that JSON only — CI never computes**
  (demo-layer doctrine). The demo retrieval mock is **standard-library only** (§4); the live
  build adds the embedding model and DuckDB/SQLite.
- **Effort:** **M–L** (card estimate) — the extraction is reused, the retrieval and graph layers
  are modest, and the two new substrate pieces (corpus extension, retrieval eval set) are small
  but real. The hardened build waits on the shared corpus generator (wave-3 stretch).

### 6.7 Adoption & packaging

- **The brief is delivered in-workflow, not as a standing dashboard.** E3 surfaces at the two
  moments that already have the reader's attention — **meeting prep** and **underwriting** —
  via the E2 pack, not a separate always-on search tab that goes stale (Sweep E: the standing
  dashboard dies at ~25% adoption).
- **Provenance is the product's trust.** Every fact, view, and retrieved passage carries its
  source sentence and date; the reader verifies rather than believes. This is what a plain
  chatbot cannot offer and is the differentiator the card rests on.
- **Help-not-audit framing.** The brief is preparation, framed as the shared question ("here is
  what was said and what is still open"), never a gotcha — the manager-facing posture lives only
  inside the E1 transparency-ladder relationship.

**Who sees what, when:** the investment team gets the full graph and brief at meeting-prep and
underwriting cadence; any manager-facing view ships only inside the E1 ladder, framed as help.

### 6.8 Go-live requirements (demo-page box, expanded)

- **Data ask:** the manager's **documents** (tier R — letters, DDQs, meeting notes; **public
  documents only in the repo**). Tier E adds exposure summaries (enables say–do flags in the
  brief); tier P adds holdings (name-level flags). The graph runs at R.
- **Sample required:** **not a sample-size gate** — E3 is a per-document analytic, not a
  small-N estimator. The gates are the **evals**: extraction precision/recall ≥ 0.8 per slot,
  **and** graph-augmented retrieval beating the plain-RAG baseline by the stated margin
  (§3.5) — **before any real-document claim renders, and before the graph layer ships at all**.
- **Build effort:** **M–L**, including the shared corpus extension (DDQ + meeting notes) and the
  planted retrieval eval set.
- **Go-live box (demo page):** data ask = manager documents (R); gate = extraction eval ≥ 0.8
  and graph-beats-RAG on the retrieval eval; effort = M–L.

## 7. Deeper reading

**Canonical references (read in this order):**

1. **Robertson & Zaragoza (2009), "The Probabilistic Relevance Framework: BM25 and Beyond,"
   *Foundations and Trends in Information Retrieval*.** The BM25 scoring function (§3.4a) and why
   its saturating, length-normalized form remains the lexical baseline dense methods complement
   rather than replace.
2. **Karpukhin et al. (2020), "Dense Passage Retrieval for Open-Domain Question Answering,"
   *EMNLP*.** Learned dense embeddings retrieve by meaning and recover paraphrase lexical search
   misses — and retrieve *different* documents than BM25, the empirical case for fusing the two.
3. **Cormack, Clarke & Büttcher (2009), "Reciprocal Rank Fusion Outperforms Condorcet and
   Individual Rank Learning Methods," *SIGIR*.** RRF (§3.4c): a training-free, robust fusion of
   incommensurable rankings with a single constant — the reason E3 fuses on rank, not score.
4. **Lewis et al. (2020), "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,"
   *NeurIPS*.** The RAG pattern that is E3's **baseline** — the thing the graph layer must beat
   on the eval, and the retrieve-then-read structure E3 augments with entity structure.
5. **Hogan et al. (2021), "Knowledge Graphs," *ACM Computing Surveys*; Edge et al. (2024),
   "From Local to Global: A Graph RAG Approach to Query-Focused Summarization."** The typed
   entity–relation data model (§3.3) and the modern claim that graph structure can improve
   retrieval — held to E3's honest line: *demonstrate it on the eval, keep the graph light until
   scale forces more.*
6. **Manning, Raghavan & Schütze, *Introduction to Information Retrieval*.** The eval metrics of
   §3.5 — precision/recall@$k$, MRR, nDCG — shared with M5's extraction eval.

**Questions you should be able to answer after reading this page:**

- **Why hybrid, not one retriever?** Explain what BM25 catches that dense misses (rare literal
  terms) and what dense catches that BM25 misses (paraphrase — "redemption gates" ≈ liquidity),
  and why fusing their *ranks* with RRF (not their scores) is the robust way to keep both.
- **Where the graph earns its keep — work the §3.2 case by hand.** Why does plain hybrid RAG
  return the wrong-firm distractor and miss the paraphrased note, and how does entity-linking to
  the manager node plus a one-hop `employed_by`/`authored_by` expansion fix *both* — taking
  recall@3 and precision@3 from 0.67 to 1.00? Re-derive the RRF score
  $\tfrac{1}{65} + \tfrac{1}{62} = 0.03151$ for the note.
- **Why is the graph's value measured, not asserted?** State the retrieval gate (graph must beat
  plain RAG on the planted eval by a stated margin) and the kill criterion (if it does not, ship
  extraction tables + search, no graph). Explain why this is right-level engineering rather than
  a hedge.
- **Why authored constants and a planted eval, not a simulator draw?** E3 is not a statistical
  estimator, so there is no ground-truth *return* to draw; the ground truth is which document
  answers which query, which is planted at corpus-generation time — the same move M5 makes for
  view/alignment truth, extended to retrieval relevance.
- **Why provenance on every fact, and why no chatbot?** Explain why a retrieved passage without
  its source sentence and date is inadmissible (the trust the card rests on), and why the product
  is the decision-hook brief rather than a free-form agent (the hooks, not the chat, are the
  value).
- **How does E3 relate to the do-not-build list?** Explain why E3 runs none of the prohibited
  small-N statistical machinery — because it makes no skill inference at all — and why that makes
  the list *orthogonal* to this card rather than a constraint it must dodge.

## 8. Method-review gate rulings (2026-07-07)

1. **`RETRIEVAL_GATE_UPLIFT` set:** graph-augmented retrieval must beat the
   plain-RAG baseline by **+0.10 absolute recall@10**, with the paired-difference
   interval excluding zero under the §6.3 seeded-replication discipline.
   Provisional; re-examined once the planted eval set exists at scale.
2. **`GRAPH_EXPANSION_HOPS` = 1 confirmed.** Two-hop theme expansion is out of
   v1 — a v2 question, admissible only with its precision cost measured on the
   same eval.
3. **No new runtime dependency for the demo.** The demo graph layer uses stdlib
   `sqlite3` (or plain in-memory tables); DuckDB is a live-build choice, and
   `EMBEDDING_MODEL` is deferred to live — the authored concept-table stand-in
   is approved for the demo with its nature disclosed on the page.
4. **Extraction discipline confirmed:** demo facts are authored constants (the
   M5 precedent); `EXTRACTION_GATE` = (0.8, 0.8) reusing M5's harness verbatim.
   The shared corpus-generator extension (DDQs + meeting notes behind a
   default-off flag, M5's letter corpus byte-identical) and the planted
   query→relevant-document eval set are approved as batch-3 substrate.
5. **Constants confirmed:** `BM25_K1` = 1.5, `BM25_B` = 0.75, `RRF_K` = 60,
   `RETRIEVAL_TOPK` = 10.
6. **Names approved** (Corvid Lane Capital, Selby Point Advisors, Wexford Green
   Capital, Elena Voss, Priya Anand). P2 renames its confusable "Wexford
   Capital" (P2 §8 ruling 6).
