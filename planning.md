# Planning: Provenance Guard (Project 4)

This document outlines the architectural specifications, algorithmic logic, and product design choices for **Provenance Guard**, a multi-signal AI content classification pipeline.

---

## 1. Detection Signals & Ensemble Strategy

To ensure robust classification, this system utilizes an **Ensemble Detection** approach combining three distinct, independent signals. This multi-layered design ensures that semantic properties and raw statistical properties are cross-verified before a final verdict is reached.

### Signal 1: Holistic Semantic & Coherence Analysis ($S_{llm}$)
* **What it measures:** Semantic consistency, logical transition predictability, and common structural tropes characteristic of large language models (e.g., over-indexing on structural hedging, or phrases like *"it is important to note"* or *"furthermore"*).
* **Mechanism:** Text is analyzed via the Groq API using the `llama-3.3-70b-versatile` model with a system prompt that enforces a continuous probability assessment.
* **Output format:** A floating-point number between 0.0 (indistinguishable from a human writer) and 1.0 (highly characteristic of AI text generation).
* **Linguistic Blind Spot:** Highly structured, professional technical documentation or formal legal writing can easily confuse this signal into returning an artificially elevated score.

### Signal 2: Sentence Length Variance Heuristic ($S_{slv}$)
* **What it measures:** Structural sentence "burstiness." Human writers naturally vary sentence lengths dramatically—mixing short, punchy statements with long, complex, multi-clause explanations. AI content tends to exhibit a highly uniform, rhythmic cadence with low sentence length variance.
* **Mechanism:** Pure Python processing splits text into sentences, counts the word tokens per sentence, and calculates the statistical variance. The raw variance is then passed through a non-linear normalization function.
* **Output format:** A normalized floating-point number between 0.0 (high sentence length variance / typical human) and 1.0 (near-zero variance / highly uniform AI cadence).
* **Linguistic Blind Spot:** Fixed-form poetry, stylized flash fiction, or minimalist copy designed with intentional uniformity will cause this signal to incorrectly register as AI.

### Signal 3: Type-Token Ratio / Lexical Diversity ($S_{ttr}$)
* **What it measures:** Vocabulary density and distribution uniformity. AI models operate on optimized probability vectors, distributing a diverse but mathematically standardized set of common vocabulary terms across a text. Humans often display hyper-focused repetition of specific idioms or casual slang.
* **Mechanism:** Pure Python logic tokenizes words, filters out standard punctuation, and calculates the unique words (types) divided by the total words (tokens). This raw ratio is normalized against expected standard lengths.
* **Output format:** A normalized floating-point number between 0.0 (highly irregular, repetitive, or uniquely dense vocabulary distribution / human) and 1.0 (perfectly distributed, standardized vocabulary range / AI).
* **Linguistic Blind Spot:** Highly focused academic introductions or highly repetitive technical descriptions that require strict, narrow jargon will score poorly on lexical diversity.

### Signal Combination & Conflict Resolution
The outputs of the three independent components are synthesized using a weighted average. Because semantic context captures holistic nuance more effectively than raw statistical heuristics, the weights are distributed as follows:

$$Score_{combined} = 0.50 \cdot S_{llm} + 0.25 \cdot S_{slv} + 0.25 \cdot S_{ttr}$$

* **Conflict Resolution Strategy:** If the statistical heuristics ($S_{slv}$, $S_{ttr}$) indicate high uniformity (e.g., 0.85) but the semantic LLM check ($S_{llm}$) indicates genuine human narrative style (e.g., 0.15), the mathematical weighting pulls the final combined score into the middle ground (0.40). This prevents a harsh binary assignment and routes anomalous content safely into the "Uncertain" category, preventing catastrophic false positives.

---

## 2. Uncertainty Representation & Threshold Calibration

A false positive (labeling a human author’s organic work as AI-generated) is profoundly demoralizing to creators and introduces severe liability for a writing platform. Consequently, our scoring thresholds are intentionally calibrated with an asymmetric bias that prioritizes protecting human authors.

The system maps the final continuous `$Score_{combined}$` into three distinct platform tiers:

* **0.00 to 0.35 $
ightarrow$ High-Confidence Human Category**
  * The system detects clear structural irregularity, natural sentence length variation, and organic semantic flows. False-positive mitigation is strongest here; borderline cases are given the benefit of the doubt.
* **0.36 to 0.70 $
ightarrow$ Uncertain / Ambiguous Category**
  * The system registers conflicting signals (e.g., highly uniform sentence pacing combined with deeply emotional or highly irregular idiomatic expressions). The pipeline explicitly communicates lack of certainty rather than guessing.
* **0.71 to 1.00 $
ightarrow$ High-Confidence AI Category**
  * The text exhibits high uniformity across sentence length variance, perfectly distributed lexical frequency, and noticeable AI transitional tropes.

---

## 3. Transparency Label Design

Transparency labels must protect user trust by speaking in plain, clear language. They completely omit technical jargon like "logit distributions," "classification algorithms," or "confidence thresholds," translating data into actionable context for non-technical readers.

### Variant 1: High-Confidence Human (Score Range: 0.00 - 0.35)
> **Verified Authentic**
> This text displays the natural variations in rhythm, pacing, and vocabulary choices characteristic of direct human writing.

### Variant 2: Uncertain / Ambiguous (Score Range: 0.36 - 0.70)
> **Stylistically Mixed**
> This text includes a blend of patterns. It features highly organized structures common in automated assistants alongside natural variations typical of personal expression.

### Variant 3: High-Confidence AI (Score Range: 0.71 - 1.00)
> **Automated Patterns Detected**
> This text closely matches the uniform structure, repeating phrase links, and predictable sentence spacing typically generated by AI language models.

---

## 4. Appeals Workflow

When a writer believes their content has been misclassified, they can immediately contest the decision.

### The Lifecycle of an Appeal
1. **Submission:** The creator initiates the request via a `POST /appeal` endpoint, providing the unique `content_id` along with a mandatory explanation string (`creator_reasoning`).
2. **State Mutability:** The system queries the persistent data layer (SQLite database) to locate the classification record. It transitions the record's `status` field from `"classified"` to `"under_review"`.
3. **Immutable Auditing:** The appeal event, timestamp, and creator reasoning are appended to the immutable audit log table, linking them directly to the original scores.
4. **Human Reviewer Interface Queue:** Platform moderators view a dedicated dashboard populated by a database query selecting entries where `status = 'under_review'`, ordered by oldest submission date.

### Moderator Interface Structure
A human reviewer opens the queue and is presented with a clean, row-by-row layout displaying these exact fields:

| Field | Description | Source |
|---|---|---|
| **Content ID** | Unique system tracking UUID | Generated at submission |
| **Submission Details** | Timestamp and Creator Account Identifier | Metadata payload |
| **System Diagnostics** | Combined Confidence Score alongside individual signal outputs | Audit log columns |
| **Creator Reasoning** | The explicit textual justification written by the author | Appeal payload |
| **Action Console** | Binary administrative controls: `[Approve Appeal - Force Human Status]` or `[Deny Appeal - Maintain Classification]` | Operational buttons |

---

## 5. Anticipated Edge Cases

### Edge Case 1: Non-Native English Speakers (Formal Academic Pacing)
Writers who have learned English through formal academic training often use highly standardized, uniform sentence lengths and rigid transition formulas (e.g., *"Furthermore, it must be considered,"* *"In summary, the data indicates"*). 
* **Pipeline Impact:** The Groq LLM semantic parser may identify these structures as typical AI hedging, and the pure Python stylometric module will register very low sentence length variance, triggering a high-confidence AI classification on genuine human effort.

### Edge Case 2: Minimalism and Stylized Copywriting
Professional sales copy, landing page statements, or modern minimalist poetry utilize highly repetitive vocabulary, uniform phrase patterns, and short, evenly spaced sentences for structural emphasis.
* **Pipeline Impact:** The low Type-Token Ratio (due to intentional repetition) combined with zero sentence length variance will trick the statistical heuristics completely, causing a mid-to-high AI score on highly curated human writing.

---

## 6. Architecture & System Flow

The system coordinates the submission and appeal routines through independent, clean data flows.

```
[SUBMISSION FLOW]
User Content -> POST /submit -> [Rate Limiter] -> [Pipeline Controller]
                                         |
                                         +--> [Signal 1: Groq LLM]
                                         +--> [Signal 2: Sentence Var]
                                         +--> [Signal 3: Lexical TTR]
                                               |
                                               v
                                         [Ensemble Scoring]
                                               |
                                               v
                                      [Threshold Classifier]
                                               |
                                               v
                               [SQLite Log: classified] -> Response

[APPEAL FLOW]
Creator Payload -> POST /appeal -> [Locate Content ID]
                                      |
                                      v
                        [Update status: under_review]
                                      |
                                      v
                           [Append appeal evidence]
                                      |
                                      v
                                 [Confirmation]
```

### Architecture Narrative
* **Submission Path:** Content hits the `POST /submit` endpoint where it is checked by `Flask-Limiter`. If safe, the pipeline broadcasts the text to all three detection functions simultaneously. The individual float outputs are synthesized via the weighted formula, a transparency text block is matched based on the threshold tier, an audit row is safely written to the SQLite database with a `"classified"` flag, and the payload returns to the sender.
* **Appeal Path:** If a user files a dispute, the `POST /appeal` endpoint parses the targeted `content_id`. The application performs an atomic update query on the SQLite logging table, altering the tracking state to `"under_review"` while binding the author's statement directly to that row.

---

## 7. AI Tool Plan

### Milestone 3: Core API Blueprint & Groq Integration
* **Inputs Provided to AI:** The Architecture Narrative, ASCII workflow diagram, and the *Signal 1* specification criteria.
* **Generation Task Request:** A Flask application blueprint establishing the initialization boilerplate, a functional `POST /submit` stub validating JSON request payloads (`text`, `creator_id`), and an asynchronous function wrapping the Groq client library to parse text structures and return a standardized float score.
* **Verification Routine:** Execute manual integration calls locally using mock payloads. Validate that invalid input types generate explicit HTTP 400 structures, and assert that the Groq parser reliably outputs isolated numeric floating points.

### Milestone 4: Statistical Heuristics & Ensemble Synthesis
* **Inputs Provided to AI:** Section 1 (*Detection Signals & Ensemble Strategy*) detailing the mathematical weight parameters and the ASCII system flow diagram.
* **Generation Task Request:** Pure Python functions computing sentence length variance and Type-Token distribution ratios along with an encapsulation method combining the 3 distinct tracking values into a unified float.
* **Verification Routine:** Inject the 4 standard benchmark strings provided in the milestone spec. Print out individual sub-signal components alongside the total score to verify that formal human writing and short, conversational text shift the scores precisely along the anticipated numerical paths.

### Milestone 5: Production Infrastructure Layer
* **Inputs Provided to AI:** Section 2 and 3 (*Threshold Calibration / Label Design*), Section 4 (*Appeals Workflow*), and the explicit memory storage syntax configuration rules for `Flask-Limiter`.
* **Generation Task Request:** Logic trees routing calculated floats to their respective plain-language label variants, a structured SQLite schema executing schema creations for entries and appeals, the complete `POST /appeal` endpoint processing state adjustments, and the `GET /log` endpoint for audit visibility.
* **Verification Routine:** Trigger 12 consecutive bash-driven curl submission requests to confirm the application terminates rapid traffic with an HTTP 429 status. Issue an appeal query for a generated record ID, then verify via the `/log` response that the target record matches the `"under_review"` tracking string.
