# Query requirements with unknown answers

The frozen plural-inventory control forced every query value to null. That excluded
guessed answers but also lost explicit conditions such as “14 awards.” The separately
versioned `query_requirements.py` represents known conditions and unknown answers
independently. Existing GPU protocols, raw outputs and submitted modules are preserved.

Each proposal has status, composition, cardinality, variables, clauses and operation.
Up to eight sequential variables and twelve clauses are allowed. Answer variables
and latent intermediate variables have null constants. Context variables copy exact
question spans. The first variable is an answer variable; empty ambiguous proposals
remain possible and receive missing-structure warnings.

For “Who won 14 awards and was born in 1990?”, an unknown subject variable can bind
both clauses, while 14 and 1990 remain explicit copied conditions. Comparisons can
link two context entities to distinct unknown measurements and an unknown result.
Calculation proposals can link copied numeric operands to an unknown output; this
module neither calculates a result nor supplies an answer.

Subject, object, value and period fields contain a copied span, a declared variable
reference or null. Relations, units and qualifications are copied clause-local spans.
The validator checks Unicode lexical boundaries, clause-local occurrence offsets,
variable roles, constant restrictions, operation arity and self-dependencies. Query
time remains an authoritative input anchor. Relative dates are not resolved.

The canonical character grammar enforces field order, bounds, sequential IDs, declared
references, copied query spans and null answer/intermediate constants. It permits
global spans and declared references without proving local role coherence. Every
decoded output must subsequently pass the validator. Even a bound proposal leaves
semantic requirements, complete coverage and answer acceptance explicitly false.
Repeated operands, relation meaning, cardinality meaning, negation scope and temporal
meaning still require semantic review; syntax cannot establish these.

Nine tests cover explicit numeric conditions, shared unknowns, comparisons,
calculation references, label blinding, combining marks, limits and decoder rejection
of invented or undeclared values. A real token-enforcer test with a synthetic
character tokenizer checks that termination is permitted only after a full proposal. Tests also demonstrate that grammar-admitted
cross-clause spans, wrong-role references and wrong arity fail validation.

```sh
uv run --locked --no-editable --extra constraints \
  pytest -q tests/test_query_requirements.py
```

This checkpoint implements representation, prompting, decoding grammar and validation.
It has no submitted GPU run or measured neural quality. Next, freeze a separate
query-only protocol on the fifty existing development questions, count full extraction
budgets and reconstruct outputs before reviewing roles and omissions. Retain the
negative inventory control and keep answer-generation settings fixed. The source
statement/context protocol and web/API support composition remain subsequent work.
Fresh independently reviewed evaluation remains a separate scientific gate.
