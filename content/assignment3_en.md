# Assignment 3 — Collaborative Functions & Relations Project

## Overview
Work in teams of exactly three students. Your goal is to analyse a short porosity well-log dataset using precise function and relation terminology. Coordinate closely: each question depends on a shared understanding of the sets, symbols, and notation the team adopts at the start.

## Collaboration rules
- Hold three synchronous check-ins (kickoff, midway, final review). Rotate note-taking duties.
- Use a shared document or spreadsheet where all answers are drafted. Track which student led and which student reviewed each question.
- Submit one combined report plus a collaboration log signed by all three members.

## Suggested role split
- **Student A – Domain & Data Architect:** Leads Q1–Q3, maintains the glossary of symbols and ensures units are stated consistently.
- **Student B – Data Quality & Alternate Relations:** Leads Q4–Q6, documents how duplicates/noisy readings are handled, and defines any depth–depth relations.
- **Student C – Logic & Communication Lead:** Leads Q7–Q9, translates symbolic statements to plain language, and drafts the final write-up template used by the team.
- **Whole team:** Co-create and finalise Q10, then review the full submission together.

## Milestones
1. **Kickoff (Day 1, 30 min):** Agree on the dataset, list the symbol glossary, and assign question leads.
2. **Independent drafting (Days 2–3):** Leads create first versions while tagging areas that need peer review.
3. **Midway sync (Day 3, 45 min):** Challenge assumptions (e.g., codomain choice) and align notation.
4. **Peer review swap (Day 4):** Each student reviews at least three answers written by someone else.
5. **Final review & submission (Day 5, 45 min):** Finalise Q10 jointly, polish language, and compile the collaboration log.

## Deliverables
1. **Main report** (PDF or DOCX) containing:
   - Completed answers for Q1–Q10 with consistent notation.
   - Tables or diagrams (if used) labelled with units (m, porosity fractions).
2. **Collaboration log** (≤1 page) listing for each question: lead author, peer reviewer, final approver, and meeting dates.
3. **Optional:** Include a simple flowchart that explains how the team decides whether a relation is a function.

---

## Questions (answer in complete sentences, 2–4 sentences each unless noted)
1. **Domain and codomain declaration:** State the domain \(A\) (depths, in metres) and the codomain \(B\) (porosity values). Explain why these choices keep later reasoning precise.
2. **Ordered pair construction:** Convert the dataset into a set \(M\) of ordered pairs \((z, \varphi)\). Describe what each pair means physically.
3. **Function test:** Determine whether the log defines a function from \(A\) to \(B\). Cite the “one input → one output” rule and justify your conclusion with evidence from the data.
4. **Duplicate-handling policy:** If the tool reports multiple porosity readings at the same depth, document the team’s rule for resolving conflicts and demonstrate it on a sample duplicate.
5. **Range analysis:** Compute the observed range (image) of the porosity readings. Compare it to the codomain and explain any differences.
6. **Alternate relation definition:** Define a new relation on depths only—e.g., \(R_{\text{shallow}} = \{(x,y) \in A \times A : x < y\}\). List its ordered pairs for the dataset and state one practical use for the relation.
7. **Membership statements:** Translate three membership or non-membership statements (e.g., \(1198 \in A\), \(0.35 \notin B\), \((1200,0.24) \in M\)) into plain language, highlighting one common mistake to avoid.
8. **Cartesian product exploration:** Present a portion of \(A \times B\) and explain why every relation derived from the log must be a subset of this product.
9. **Quantifier practice:** Write one existential and one universal statement about porosity thresholds (e.g., \(\exists z \in A: \varphi(z) \ge 0.25\)). Evaluate whether each statement is true for the dataset and justify.
10. **Custom relation proposal (team effort):** Define a new relation \(x R y\) linked to the dataset (for example, “depth x has porosity at least as high as depth y”). Prove that \(R \subseteq A \times A\) or \(R \subseteq A \times B\), state at least three ordered pairs in \(R\), and discuss how the relation could support geoscience decision-making.

## Evaluation rubric (100 points total)
- Concept accuracy & notation (40 pts)
- Collaboration evidence (meeting notes, peer review, shared glossary) (20 pts)
- Clarity of explanations & bilingual glossary usage if needed (20 pts)
- Completeness and coherence of Q10 team synthesis (20 pts)

Good luck, and remember: precise definitions keep your geological interpretation defensible!
