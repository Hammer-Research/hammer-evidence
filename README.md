# hammer-evidence

Small, composable research checks using Python's standard library. Three modules, no databases, network calls, model downloads or runtime dependencies.

- `audit_cohort`: flag declared sample/patient overlap, repeated specimens, missing metadata and endpoint/assay differences.
- `compare_reviews`: verify exact source spans and compare two attributed annotations without treating agreement as truth.
- `run_experiment` / `verify_run`: snapshot declared inputs, code, configuration and splits; run a Python callback once; checksum results and preserve failure receipts.

These are accounting tools, not scientific approval or clinical validation. A clean audit cannot prove independence; reviewer names cannot prove independent human review; a runner cannot detect undeclared data access.

## Install

From this package's directory:

```sh
python -m pip install '.[test]'
python -m pytest tests -q
python examples/first_run.py
```

The example uses synthetic data and a temporary directory. No paid service, account or biomedical expertise is required. This package is not published on PyPI.

## Cohort records

```python
from hammer_evidence import audit_cohort

report = audit_cohort(samples, expected_endpoint='EAC_vs_Barrett_tissue', expected_assay='defined-assay-v1')
```

`samples` is a nonempty list of objects with string fields `sample_namespace`, `sample_id`, `cohort`, `role` (`development` or `evaluation`), `patient_namespace`, `patient_id`, `identity_source`, `endpoint` and `assay`. Unknown values remain missing; shared sample-title prefixes are not patient identities. Match aliases through a reviewed crosswalk before calling this function. Multiple unresolved namespaces are flagged. Repeated specimens are counted separately from distinct reported patient groups. Output contains aggregate counts and issue codes, not raw identities. Assay mismatch flags a review requirement, not proof that transfer is impossible.

## Evidence review

`compare_reviews(source, reviews)` requires a source object `{text, sha256, url}` and exactly two reviews. Each review has `reviewer`, `source_sha256`, `status` (`reviewed` or `uncertain`), and `fields`. Fields must be exactly `population`, `method`, `result`, `limitation`; each is null or `{start, end, quote}` matching the source exactly. Offsets count Python Unicode characters, not encoded bytes. SHA-256 covers UTF-8 source text. Null explicitly means no evidence was selected. Any uncertainty or span disagreement remains for adjudication. Store original reviews separately; the comparison does not replace them.

## Experiment runner

```python
from pathlib import Path
from hammer_evidence import run_experiment, verify_run

# Define compute in a source file included in code_files.
# It receives snapshot paths and a JSON-copy of config and returns a JSON object.
run_experiment(
    Path('new-run'), inputs={'matrix':Path('matrix.json')},
    code_files={'analysis':Path('analysis.py')},
    config={'seed':42, 'threshold':0.3, 'preprocessing':'declared-method'},
    splits=[{'train':['group-a'], 'test':['group-b']}], compute=compute,
    dependencies=['numpy'],
)
verify_run('new-run')
```

Include every input and code file used, all seeds/preprocessing/threshold rules in config, and third-party package names in dependencies. The runner records their installed versions. Split lists describe grouping units within each fold; cross-fold reuse is allowed. It does not generate splits or certify identity linkage. Input snapshots are copied before computation and rechecked afterward. The callback's source file must be included. No command strings are executed by the library.

For metadata-only accounting, specify `kind='metadata', splits=[]`. This records that no train/test split applies. The default `kind='model'` requires nonempty splits; never invent patient splits to run a metadata check.

Run directories can contain private data and identities. Keep them private. They contain `inputs/`, `code/`, `config.json`, `splits.json`, `manifest.json`, `result.json` on success, and `receipt.json`. A crash may leave a reserved receipt; never relabel it successful without investigation. Use a new directory after a failed attempt. The callback is trusted local Python, not sandboxed: it can access undeclared resources. Checksums detect accidental changes; they are not digital signatures or proof against a malicious author. No experiment is automatically approved as independent evaluation.

## CLI composition

```sh
hammer-evidence cohort cohort-input.json
hammer-evidence reviews review-input.json
hammer-evidence verify-run new-run
```

Input JSON keys match the Python function arguments. Reports print to stdout; malformed inputs exit nonzero. A valid report containing issues still exits zero—automation must inspect `status` and `findings`, not just the exit code. Contracts carry versioned schema strings. Version 0.2 is an initial API; preserve dependency versions in reproducible runs.

## Help improve this

Try [the pilot](PILOT.md), then open an issue with a small synthetic reproduction. The most useful feedback is a real workflow these functions cannot express, a missed conflict, or a confusing report. See [CONTRIBUTING.md](CONTRIBUTING.md). MIT applies to this package; no third-party data or model weights are included.

## Record adjudication

`adjudicate_reviews(source, reviews, decision)` verifies a third reviewer's explicit
resolution against the exact source and original review records. The original
reviews are never overwritten. The decision must contain:

- `adjudicator`: a name distinct from both original reviewer names.
- `reviewed_at`: a timezone-aware ISO timestamp.
- `source_sha256`: the source text hash.
- `reviews_sha256`: `digest(encode(reviews))`, using `hammer_evidence.common`.
- `decisions`: all four field names, each with `status` (`resolved` or `unresolved`),
  `span` (source span or null), and a nonempty `reason`.

An unresolved field must have null span and makes the overall `reference_fields`
output null. A resolved null means the adjudicator explicitly decided no evidence
was present. This distinction prevents unresolved work from becoming a negative
reference label. A completed record still does not prove human identity, reviewer
independence or scientific accuracy. Automatic promotion remains disabled.

The CLI equivalent is `hammer-evidence adjudicate decision-input.json`; input keys
are `source`, `reviews` and `decision`. See `examples/adjudication.py` for a synthetic
worked example. Preserve original review JSON alongside the resulting record.

Run verification rejects file paths and symlinks that resolve outside the run
folder, including the receipt, manifest and result. It is still not a security
sandbox: do not execute untrusted callbacks.
