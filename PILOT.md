# First outside-user pilot

**Goal:** determine whether a researcher outside Hammer can install this package and understand one useful report without help. This is a software-usability pilot, not clinical validation.

## A short synthetic exercise

Allow roughly 20 minutes as a starting estimate; installation and troubleshooting may take longer. Record your actual time, including an incomplete attempt.

1. Install in a clean environment following the [README](README.md#install).
2. Run `python examples/first_run.py` unchanged. It should report no detected structural conflicts, reviewer agreement and verified run checksums for synthetic data.
3. In the same installed Python environment, run the separate exercise below (paste it into a Python interpreter or save it in a disposable Python file). It introduces cross-role patient overlap and a one-null review disagreement. Leave `examples/first_run.py` untouched: its assertions expect a clean baseline, and its reviews share one fields dictionary.

```python
import json
from copy import deepcopy
from hammer_evidence import audit_cohort, compare_reviews
from hammer_evidence.common import digest

rows = [
    dict(sample_namespace="fixture", sample_id=f"s{i}",
         patient_namespace="fixture", patient_id=f"p{i}",
         identity_source="synthetic only", cohort=role, role=role,
         endpoint="synthetic", assay="synthetic")
    for i, role in enumerate(("development", "evaluation"))
]
# Same patient namespace and ID, distinct specimens in different roles.
rows[1]["patient_id"] = rows[0]["patient_id"]
audit = audit_cohort(rows, expected_endpoint="synthetic", expected_assay="synthetic")

text = "Forty adults participated."
source = dict(text=text, sha256=digest(text.encode()), url="https://example.org/synthetic")
fields = dict(population=dict(start=0, end=len(text), quote=text),
              method=None, result=None, limitation=None)
reviews = [
    dict(reviewer=name, source_sha256=source["sha256"], status="reviewed",
         fields=deepcopy(fields))
    for name in ("Synthetic reviewer A", "Synthetic reviewer B")
]
# Each review owns its fields: only the second population becomes null.
reviews[1]["fields"]["population"] = None
compared = compare_reviews(source, reviews)
print(json.dumps({"cohort": audit, "review": compared}, indent=2))
```

The cohort report should have status `issues_found` and a `patients_across_roles` finding with count `1`. The review report should have status `requires_adjudication`, with `field_agreement.population` set to `false`. These are synthetic records, not two actual human reviewers. Neither report certifies independence or scientific truth.

4. Optionally try another small synthetic case resembling your workflow. Record what you expected and what actually happened; stopping at a confusing step is useful feedback.

## Before sharing

GitHub issues are public. Share only synthetic reproductions and sanitized output. Do not include patient data or identifiers, credentials, private correspondence, or private files and paths. Review commands and logs for sensitive content before posting. Names, employers and affiliations are not required.

## Report back

Open an issue using the [pilot-feedback template](.github/ISSUE_TEMPLATE/pilot.md). Include your relationship to the project, actual outcome (completed, partial or failed), environment, commands, output, approximate time and confusing steps. Disclose any human or agent assistance and the steps it affected, or state none. Describe what existing tool you use and where this tool would or would not fit; a negative answer is useful.

Public credit is optional and requires explicit opt-in. An omitted credit preference is not consent.

## Acceptance record

A maintainer fills in the template's disposition only after reviewing real feedback: link the feedback to a fix, documentation change or documented decision not to change, and record verification and any unresolved limitations. Leave those fields blank until evidence exists.

One outside-user attempt is not broad adoption. Report attempts, independent completions and resulting fixes separately; do not count internal tests or agent runs as outside adoption. Disclose assisted attempts separately from unassisted completions.

Status at initial publication: no outside pilot completion has been recorded.
