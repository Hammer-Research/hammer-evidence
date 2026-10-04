# First outside-user pilot

**Goal:** determine whether a researcher outside Hammer can install this package and understand one useful report without help. This is a software-usability pilot, not clinical validation.

## A 20-minute exercise

1. Install from a clean environment using the README.
2. Run `examples/first_run.py`. It should report no detected structural conflicts, reviewer agreement and verified run checksums for synthetic data.
3. Change the second synthetic patient's ID to match the first. Does the cohort report expose cross-role overlap?
4. Change one review's population span to null. Does the review comparison require adjudication?
5. Try a synthetic case resembling your own workflow. Do not share real patient identifiers or data in an issue.

## Report back

Open a pilot-feedback issue with your environment, commands, actual output, confusing steps, approximate time, and whether you would use this for a real task. A negative answer is useful. Describe what existing tool you use and where this tool would or would not fit. Choose whether you want public credit; do not include your institution or name unless you wish to.

## Acceptance record

A maintainer links the feedback to a fix, documentation change or documented decision not to change. One outside-user attempt is not broad adoption. Report attempts, independent completions and resulting fixes separately; do not count internal tests or agent runs as outside adoption.

Status at initial publication: no outside pilot completion has been recorded.
