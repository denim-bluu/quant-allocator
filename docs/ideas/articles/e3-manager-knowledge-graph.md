## The decision

Use dated, source-linked document retrieval to prepare manager meetings and underwriting. Keep deterministic hybrid search as the active method until entity-graph expansion proves a material improvement over that simpler baseline.

The current evidence does **not** clear that graph gate. The useful product today is typed extraction tables, lexical-plus-semantic search, and a document-native meeting brief. The candidate graph remains visible as an evaluated extension, not a promoted production capability.

This distinction matters. A retrieved passage is evidence for a human conversation only when the manager identity, source sentence, document, and date remain attached. It is not a manager verdict, a skill estimate, or an invitation to build an unconstrained chatbot.

## Why the obvious answer fails

Keyword search finds literal phrases and misses paraphrase. A meeting note about “redemption gates” and “cash buffers” may answer a liquidity question without containing the word “liquidity.”

Dense semantic search solves that problem but creates another. It recognizes meaning, not necessarily entity identity, so it may rank a strong liquidity passage from the wrong firm above a relevant passage from the manager under review.

Plain retrieval-augmented generation adds fluent prose but does not by itself solve source scoping or provenance. A plausible answer without a checkable sentence and date is unsuitable for underwriting. The opposite extreme—building a graph database and broad ontology before showing that graph structure improves retrieval—buys complexity without evidence.

The method therefore separates the durable value from the optional machinery. Typed, sourced memory and hybrid search are useful now. Graph expansion must beat hybrid search on a planted evaluation set before it becomes active.

## The intuition

The system has two conceptual layers.

First, documents become typed records: manager, strategy, person, document, view, theme, and meeting. Each extracted fact retains the exact source span and as-of date. A view without its supporting sentence is inadmissible.

Second, retrieval combines a literal channel and a semantic channel. BM25 rewards exact, discriminating words. Dense embeddings recover related meanings. Reciprocal rank fusion combines their rank positions without pretending their raw scores are comparable.

The candidate graph then constrains and expands the document set around an identified manager: documents attributed to that manager, plus documents authored by people employed there. That can recover a firm-unnamed meeting note and exclude a wrong-firm semantic match. But it is only worthwhile if the measured benefit survives a larger evaluation.

## A small numerical example

Use the fictional query: “what did Corvid Lane say about liquidity in 2024?” The relevant set contains a letter, a DDQ, and a meeting note. The meeting note discusses redemption gates and cash buffers but does not use the firm name or the word “liquidity.” A Wexford Green DDQ is a wrong-firm distractor that does use the literal liquidity language.

On the current five-document authored corpus, lexical retrieval ranks the paraphrased meeting note $5$th. Plain hybrid search puts the Wexford distractor $2$nd and returns

$$
[\text{DDQ-2024},\ \text{DDQ-WEX},\ \text{L-2024Q1}]
$$

in its top three. Against the three planted relevant documents, both recall@3 and precision@3 are $0.67$.

The one-hop graph candidate removes the unrelated Wexford document and admits the firm-unnamed meeting note through the author’s employment edge. Its top three become

$$
[\text{DDQ-2024},\ \text{L-2024Q1},\ \text{MTG-2024-05}],
$$

so the illustrative recall@3 and precision@3 both rise to $1.00$.

That is useful evidence for the mechanism, but it does not pass the formal gate. The gate is recall@10, and a five-document corpus saturates it: plain hybrid and graph candidate both retrieve all three relevant documents, giving $1.00$ versus $1.00$, an uplift of $0.00$. There is also only one planted query, too few for a paired interval. The verdict is therefore **insufficient**, and active retrieval stays hybrid.

## The method

### Lexical and semantic retrieval

For query $q$, document $d$, and query term $t$, BM25 is

$$
\operatorname{BM25}(q,d)=
\sum_{t\in q}\operatorname{idf}(t)
\frac{f(t,d)(k_1+1)}
{f(t,d)+k_1\left(1-b+b\frac{|d|}{\overline{|d|}}\right)}.
$$

$f(t,d)$ is term frequency, $|d|$ is document length, $\overline{|d|}$ is average length, and $\operatorname{idf}(t)$ gives rare terms more weight. The specified constants are $k_1=1.5$ for frequency saturation and $b=0.75$ for length normalization.

Dense retrieval maps the query and document to embedding vectors $\mathbf v_q$ and $\mathbf v_d$, then scores their cosine similarity:

$$
\operatorname{dense}(q,d)=
\frac{\mathbf v_q\cdot\mathbf v_d}
{\lVert\mathbf v_q\rVert\lVert\mathbf v_d\rVert}.
$$

The dense channel can recognize that redemption gates relate to liquidity even when the words differ.

### Fuse ranks, then test graph expansion

Reciprocal rank fusion assigns

$$
\operatorname{RRF}(d)=
\sum_{r\in\{\mathrm{BM25},\mathrm{dense}\}}
\frac{1}{60+\operatorname{rank}_r(d)}.
$$

The constant $60$ dampens differences among top ranks. It lets either channel contribute without tuning a weight between unrelated score scales.

For manager $M$, the candidate graph uses one-hop expansion:

$$
C(M)=
\{d:\operatorname{attributed\_to}(d)=M\}
\cup
\{d:\operatorname{authored\_by}(d)=p,\ \operatorname{employed\_by}(p,M)\}.
$$

The graph candidate reranks only $C(M)$. Two-hop theme expansion is outside the current method because its precision cost has not been measured.

### Gate both extraction and retrieval

Real-document extraction requires precision and recall of at least $0.8$ for every core slot: direction, theme mapping, person, document type, date, and quote span. A slot missing the gate after two prompt or model iterations remains demo-only.

Graph activation requires at least $+0.10$ absolute recall@10 over plain hybrid search, with the paired-difference interval excluding zero. If that gate fails, the method deliberately remains extraction tables plus hybrid search.

## What the evidence changes

The current evidence supports sourced institutional memory and a document-native meeting brief. It shows, in one small example, how entity structure could remove a wrong-firm distractor and recover a paraphrased note.

It does not support the broader claim that graph expansion improves recall@10. The formal metric is saturated, the observed uplift is zero, and the query set is too small for the required paired interval. The negative finding is load-bearing: the candidate graph has not earned active status.

Nothing retrieved here establishes manager skill, confirms an operational fact without source review, or authorizes mechanical action. A passage is preparation material with provenance, not a judgement.

## What the allocator does next

Use the hybrid system for decision-hook queries and meeting preparation. For every returned item, inspect the manager scope, exact source span, document date, and as-of date before carrying it into an underwriting claim.

Keep the meeting brief narrow: prior stated views, document-native open questions, and only those cross-card panels whose manager identity has a valid crosswalk. When a tear sheet or say–do payload belongs to a different fictional manager, mark it unavailable rather than relabelling it.

To revisit graph activation, build a larger planted query-to-relevant-document set, rerun hybrid and graph retrieval on identical queries, and report recall@10 uplift with its paired interval. Promote the graph only if the $+0.10$ gate clears.

## Limits and go-live

- The current synthetic exhibit uses authored fictional documents and relationships, not claims extracted from live manager material.
- Real-document facts require per-slot extraction precision and recall of at least $0.8$.
- Graph expansion requires $+0.10$ absolute recall@10 over plain hybrid search and a paired-difference interval excluding zero. The current evidence fails that gate.
- The data ask at the returns/document tier is dated manager letters, DDQs, and meeting notes, with public documents only in the publication corpus. Exposure summaries enrich say–do sections; positions permit supported name-level sections.
- Every fact needs manager identity, receipt context, source document, exact source span, and as-of date. Incomplete corpus provenance or entity resolution causes refusal.
- No chatbot, manager ranking, skill inference, or automatic decision is produced.
- A light typed-table implementation is sufficient. A graph database is not a go-live prerequisite.

## Key takeaways

- Hybrid retrieval combines exact words with paraphrase recovery.
- Provenance and entity scoping are requirements, not interface decoration.
- The small top-three example favors graph expansion, but the formal recall@10 gate does not.
- The current active method is typed extraction plus hybrid search.
- Graph complexity must earn itself through $+0.10$ recall@10 uplift with interval support.
- Retrieved evidence prepares a human decision; it never becomes a manager verdict.

## References

- Robertson, Stephen, and Hugo Zaragoza. “The Probabilistic Relevance Framework: BM25 and Beyond.” *Foundations and Trends in Information Retrieval*, 2009.
- Karpukhin and coauthors. “Dense Passage Retrieval for Open-Domain Question Answering.” *EMNLP*, 2020.
- Cormack, Gordon, Charles Clarke, and Stefan Büttcher. “Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods.” *SIGIR*, 2009.
- Lewis and coauthors. “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.” *NeurIPS*, 2020.
- Hogan and coauthors. “Knowledge Graphs.” *ACM Computing Surveys*, 2021.
- Edge and coauthors. “From Local to Global: A Graph RAG Approach to Query-Focused Summarization,” 2024.
- Manning, Christopher, Prabhakar Raghavan, and Hinrich Schütze. *Introduction to Information Retrieval*.
