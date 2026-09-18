# Gurbani Search vs ChatGPT upload: product pilot

Status: preparation complete; no comparative results collected. The owner has agreed to be the first participant. An owner pilot diagnoses problems; it does not establish independent demand or superiority.

## Start here

1. Before using either product, write three genuine tasks in your normal wording: a half-remembered line, a conceptual question, and a passage/context question. Save them in `owner_tasks.jsonl` with IDs and `provenance: participant_authored`. Do not edit after seeing results. The 12 tasks in `pilot_tasks.jsonl` are synthetic practice examples only.
2. Use `sggs_multilingual.txt` for the primary ChatGPT comparison. It contains the same 60,555 source lines, translation, transliteration, source IDs and passage boundaries as the app. Use `sggs_english.txt` for a separate secondary comparison against the user's original English-file idea. Do not combine results across these conditions.
3. Record ChatGPT's visible model/mode/date and the app version, search mode and generation model. Do not infer ChatGPT's model from API configuration. Record upload errors as setup failures, not answer-quality failures. If the full file is rejected, pause and define a new condition with documented full-corpus splitting; never silently supply selected excerpts.
4. Record one-time setup separately. For repeated-use testing, upload once to a dedicated project if available, then start fresh chats within it. Otherwise reattach the file in fresh chats, logging upload overhead separately. ChatGPT supports projects containing chats and source files: https://learn.chatgpt.com/docs/projects . Do not penalize every repeat lookup with a one-time acquisition/upload cost.
5. For the three owner tasks, use ChatGPT first on tasks 1 and 3, app first on task 2. Allow both products up to 5 minutes and the same maximum of two reformulations per task. Preserve the initial query and every follow-up. Second attempts benefit from learning; report order and do not interpret this tiny pilot's timing as a general speed gain.
6. In ChatGPT, use the instruction below followed by the exact task. In the app, use the same query, and allow normal search/Ask/filter/reader controls. Preserve complete answers, selected source IDs and screenshots or notes. Do not tune the app midway through the comparison.
7. Stop timing when you can point to a relevant source AND have checked its full context, or at 300 seconds. Record failures and timeouts, not only successes. For an unsupported request, a clear admission with no invented evidence is a valid outcome.

## Shared ChatGPT instruction

Using only the attached source file, find up to three passages addressing my request. You may search the file or use available data-analysis tools. Do not use the web. Give the Shabad ID and Ang for each passage, quote the relevant English wording, and briefly explain its relevance. Provide the full context of the best match when requested. If the source does not support an answer, say so; do not invent references.

## What to record for each task and product

Copy `observation_template.json` into a separate JSON record. Keep unobserved fields null. Do not enter guessed timing or grades. Save raw output separately and reference its filename. Keep personal questions local; choose what to share later.

- Success: found an appropriate source and inspected context within the budget; yes/no. Participant judgment is provisional until independent review.
- Relevance: 0 unrelated, 1 tangential, 2 directly relevant but incomplete, 3 directly relevant with appropriate context.
- Citation exactness: referenced passage exists, quoted wording matches, and Ang is correct. This is distinct from whether the passage supports the interpretation.
- Unsupported interpretation: yes/no/uncertain, with explanation. A knowledgeable reader should check this independently before any accuracy claim.
- Elapsed seconds, reformulations, context-navigation effort, and why you preferred one workflow.

## Decisions fixed before results

For this three-task owner pilot, publish no percentage improvement. Report each task's outcome and friction. A useful next step requires a concrete reason to return to the app: a verified successful task that was easier, more reliable or more convenient, not merely a nicer answer. If both work equally well, record that. If ChatGPT wins, record that.

Next, recruit 3–5 independent readers for usability discovery, each contributing fresh tasks before trying the tools. Alternate product order, use matched task pairs where possible to reduce recall effects, and have a knowledgeable reviewer judge de-identified outputs. This small sample still supports only narrowly qualified pilot observations. Broad superiority requires a larger independently judged held-out evaluation with uncertainty and participant-level analysis, not treating repeated tasks as independent people.

The previously measured 114/120 keyword retrieval hits and 89/120 hybrid hits are not ChatGPT comparison results. Existing conceptual rankings have no human relevance grades.

## Reproduce preparation

Run `.venv/bin/python scripts/prepare_product_validation.py` from the repo root. `manifest.json` records complete-corpus counts and export hashes. Preparation regenerates exports and synthetic tasks, not participant files or observations.
