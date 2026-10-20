"""Safe branch-condition evaluator (IMPLEMENTATION.md §9.2): "a tiny safe
expression evaluator (e.g. `simpleeval`) with a whitelisted context. No
`eval`."

One deviation from §9.2's illustrative example, recorded in docs/DECISIONS.md:
conditions use Python boolean operators (`and`/`or`/`==`), not `&&`/`||` —
`&&` isn't valid Python (or JSON-Schema-describable) syntax, and §9.2's
example is clearly pseudocode rather than a literal fixture.
"""

from __future__ import annotations

from typing import Any

from simpleeval import EvalWithCompoundTypes, SimpleEval


def _evaluator(*, application_payload: dict[str, Any], stage_key: str) -> SimpleEval:
    evaluator = EvalWithCompoundTypes()
    evaluator.names = {
        "application": {"payload": application_payload},
        "stage": stage_key,
    }
    return evaluator


def evaluate_branch_condition(
    condition: str, *, application_payload: dict[str, Any], stage_key: str
) -> bool:
    """Evaluates one `BranchDef.when` expression against the running
    application's payload and the stage key currently being routed. Any
    evaluation error (bad syntax, unknown name) is treated as "condition not
    met" rather than raised — a malformed admin-authored condition should
    degrade to "don't skip", not break the whole submit flow.
    """

    try:
        result = _evaluator(application_payload=application_payload, stage_key=stage_key).eval(
            condition
        )
    except Exception:  # noqa: BLE001 - malformed condition degrades to False, see docstring
        return False
    return bool(result)
