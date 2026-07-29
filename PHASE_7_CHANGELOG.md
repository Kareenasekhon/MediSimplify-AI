# Phase 7 — Intelligent Medical Assistant

## Added

- Automatic routing between report-grounded, general educational, and hybrid answers.
- Manual answer-mode override: Auto, Report Only, General Education, or Hybrid.
- Grandma Mode for gentle, short, everyday-language explanations.
- Report-type-aware suggested questions.
- Response metadata showing the mode and explanation style used.
- General medical education answers that do not require FAISS retrieval.
- Safety separation between general knowledge and patient-specific conclusions.

## API changes

`POST /api/v1/chat` accepts two new optional fields:

```json
{
  "mode": "auto",
  "explanation_style": "standard"
}
```

Allowed modes: `auto`, `report`, `educational`, `hybrid`.

Allowed styles: `standard`, `grandma`.

New endpoint:

```text
GET /api/v1/chat/{report_id}/suggested-questions
```

## Validation

```text
42 passed
```
