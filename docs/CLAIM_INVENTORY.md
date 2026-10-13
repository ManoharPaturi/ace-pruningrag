# Plural claim and requirement inventories

The completed six-field extraction audit shows that one tuple per excerpt loses
comparison operands and mixes actors, events, dates and units. The new
`src/ace_pruningrag/claim_inventory.py` provides a plural proposal representation
and separate query/source prompts. It is implemented infrastructure, not an executed
neural extraction experiment or a semantic support verifier.

Each inventory contains at most 12 frames. Every frame has a supporting statement,
subject, relation, object, value, unit, event time, observation time, qualification
and attribution. Fields are exact source strings or null. Query-side values must
be null: requirements cannot contain a guessed answer. Several frames can retain
both sides of a comparison or separate events in one excerpt.

For example, `A bought B in 2001. C bought D in 2017.` has two separate proposed
frames. The validator rejects 2017 attached to the first statement. It also rejects
an `A` occurrence inside `CAT`, even when a separate standalone `A` occurs elsewhere
in the excerpt. It uses the corrected Unicode lexical boundaries and returns only
statement-local, boundary-valid source offsets, retaining all legitimate repetitions.

This limits an observed class of cross-statement mixing. A model can still choose
an overly broad statement, swap subject/object within it, misuse a date or omit a
claim. Structural validity therefore keeps semantic-role, source-truth, complete
requirement-coverage and answer-acceptance flags false. A proposed_complete status
is the extractor's claim; it never becomes verified completeness automatically.
Questions ending in a question mark receive an explicit assertion warning, but
this is not a general boilerplate/question classifier.

Qualification and attribution preserve text such as negation, estimates, bounds,
rumors, plans and reported statements. Event and observation dates have separate
fields; the validator does not infer temporal meaning or resolve relative dates.
Units remain proposed spans; it does not yet prove that a span is a measurement unit.

Six regression tests cover multi-event date isolation, directed role representation,
comparison operands, query answer exclusion and label blinding, qualifications,
observation dates, duplicates/caps, hallucinations, combining-mark truncation,
repeated text and question warnings. All 192 local tests pass with demo/constraints.

```sh
uv run --locked --no-editable --extra demo --extra constraints \
  pytest -q tests/test_claim_inventory.py
```

Next, version and execute an inventory decoder with counted calls and full prompt
budgets. Keep the completed six-field runs as controls. Audit the real extracted
roles and completeness before composing support sets or integrating an acceptance
gate. The inspected cohort is development data; fresh evaluation and independent
labels remain separate requirements.
