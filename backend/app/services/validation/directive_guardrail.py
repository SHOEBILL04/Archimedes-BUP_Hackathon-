"""Deterministic directive guardrail and validation layer.

Performs strict, deterministic validation and normalization of upstream LLM directives
before they reach the optimization solver.

Rejects malformed, out-of-bounds, ambiguous, or unsupported directives with
structured error reporting and zero heuristic guesswork or silent reinterpretation.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.services.optimizer.models import (
    HOURS_IN_DAY,
    SUPPORTED_DIRECTIVE_TYPES,
    NormalizedDirective,
)
from app.services.validation.exceptions import GuardrailValidationError


@dataclass(frozen=True)
class DirectiveValidationErrorItem:
    """Detailed information about a single directive validation rule violation."""

    field: str
    message: str
    code: str
    value: Any = None


@dataclass(frozen=True)
class DirectiveValidationResult:
    """Result of validating and normalizing an individual directive."""

    is_valid: bool
    directive: NormalizedDirective | None = None
    errors: list[DirectiveValidationErrorItem] = field(default_factory=list)

    @property
    def error_messages(self) -> list[str]:
        """Convenience accessor for all human-readable error messages."""
        return [e.message for e in self.errors]


@dataclass(frozen=True)
class BatchDirectiveValidationResult:
    """Result of validating and normalizing a collection of directives."""

    is_valid: bool
    directives: list[NormalizedDirective] = field(default_factory=list)
    errors: list[DirectiveValidationErrorItem] = field(default_factory=list)
    item_results: list[DirectiveValidationResult] = field(default_factory=list)

    @property
    def error_messages(self) -> list[str]:
        """Convenience accessor for all human-readable error messages."""
        return [e.message for e in self.errors]


def _is_finite_number(value: Any) -> bool:
    """Return True if value is an int or float, not a bool, and is finite."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _extract_fields(raw: Any) -> tuple[int, Any, dict[str, Any], bool]:
    """Extract (note_index, directive_type, payload, applies) from raw input."""
    if isinstance(raw, dict):
        note_index = raw.get("note_index", 0)
        directive_type = raw.get("directive_type")
        applies = raw.get("applies", True)
        adj = raw.get("structured_adjustment")
        payload: dict[str, Any] = {}
        if isinstance(adj, dict):
            payload.update(adj)
        for k in (
            "hours",
            "factor",
            "minimum_energy_kwh",
            "reserve",
            "max_grid_kwh",
            "max_grid",
        ):
            if k in raw and k not in payload:
                payload[k] = raw[k]
        return note_index, directive_type, payload, applies
    elif hasattr(raw, "directive_type"):
        note_index = getattr(raw, "note_index", 0)
        directive_type = getattr(raw, "directive_type", None)
        applies = getattr(raw, "applies", True)
        payload = {}
        adj = getattr(raw, "structured_adjustment", None)
        if isinstance(adj, dict):
            payload.update(adj)
        for k in (
            "hours",
            "factor",
            "minimum_energy_kwh",
            "reserve",
            "max_grid_kwh",
            "max_grid",
        ):
            if hasattr(raw, k) and k not in payload:
                val = getattr(raw, k)
                if val is not None:
                    payload[k] = val
        return note_index, directive_type, payload, applies
    else:
        return 0, None, {}, False


def _validate_hours_list(hours: Any) -> list[DirectiveValidationErrorItem]:
    """Strictly validate hours according to domain rules.

    Rules:
    - Every hour must be an integer (type is int, not bool)
    - 0 <= hour <= 23
    - Hours must be unique
    - Hours must be sorted in ascending order
    """
    errors: list[DirectiveValidationErrorItem] = []

    if not isinstance(hours, (list, tuple)):
        errors.append(
            DirectiveValidationErrorItem(
                field="hours",
                message=f"Hours must be a list of integers, got {type(hours).__name__}.",
                code="INVALID_HOURS_TYPE",
                value=hours,
            )
        )
        return errors

    if len(hours) == 0:
        errors.append(
            DirectiveValidationErrorItem(
                field="hours",
                message="Hours list cannot be empty for an active directive.",
                code="EMPTY_HOURS",
                value=hours,
            )
        )
        return errors

    has_type_or_bounds_error = False
    for i, h in enumerate(hours):
        if type(h) is not int:  # excludes bool as well
            errors.append(
                DirectiveValidationErrorItem(
                    field=f"hours[{i}]",
                    message=f"Hour at index {i} must be an integer, got {h!r} of type {type(h).__name__}.",
                    code="INVALID_HOUR_TYPE",
                    value=h,
                )
            )
            has_type_or_bounds_error = True
        elif h < 0 or h >= HOURS_IN_DAY:
            errors.append(
                DirectiveValidationErrorItem(
                    field=f"hours[{i}]",
                    message=f"Hour {h} at index {i} is out of bounds [0, {HOURS_IN_DAY - 1}].",
                    code="HOUR_OUT_OF_BOUNDS",
                    value=h,
                )
            )
            has_type_or_bounds_error = True

    if has_type_or_bounds_error:
        return errors

    # Check for duplicates
    if len(hours) != len(set(hours)):
        seen = set()
        dupes = []
        for h in hours:
            if h in seen and h not in dupes:
                dupes.append(h)
            seen.add(h)
        errors.append(
            DirectiveValidationErrorItem(
                field="hours",
                message=f"Hours list contains duplicate values: {dupes}.",
                code="DUPLICATE_HOURS",
                value=list(hours),
            )
        )

    # Check ascending order
    if list(hours) != sorted(hours):
        errors.append(
            DirectiveValidationErrorItem(
                field="hours",
                message=f"Hours list must be strictly ascending, got {list(hours)}.",
                code="UNSORTED_HOURS",
                value=list(hours),
            )
        )

    return errors


def validate_directive(
    raw: Any,
    battery_capacity: float | None = None,
) -> DirectiveValidationResult:
    """Validate an individual directive deterministically against domain rules.

    Args:
        raw: Untrusted input mapping or object representing a directive.
        battery_capacity: Optional battery capacity in kWh used to validate reserve upper bounds.

    Returns:
        DirectiveValidationResult with is_valid=True and NormalizedDirective if valid,
        or is_valid=False and structured error items if rejected.
    """
    note_index, directive_type, payload, applies = _extract_fields(raw)
    errors: list[DirectiveValidationErrorItem] = []

    # 1. Directive type validation
    if not isinstance(directive_type, str) or directive_type not in SUPPORTED_DIRECTIVE_TYPES:
        errors.append(
            DirectiveValidationErrorItem(
                field="directive_type",
                message=(
                    f"Unsupported or unknown directive_type '{directive_type}'. "
                    f"Must be one of {sorted(SUPPORTED_DIRECTIVE_TYPES)}."
                ),
                code="UNKNOWN_DIRECTIVE_TYPE",
                value=directive_type,
            )
        )
        return DirectiveValidationResult(is_valid=False, directive=None, errors=errors)

    # 2. no_op validation
    if directive_type == "no_op":
        raw_hours = payload.get("hours")
        if raw_hours is not None and len(raw_hours) > 0:
            hour_errs = _validate_hours_list(raw_hours)
            if hour_errs:
                return DirectiveValidationResult(is_valid=False, directive=None, errors=hour_errs)
        # A no_op must not impose physical optimization constraints
        normalized_noop = NormalizedDirective(
            note_index=note_index,
            directive_type="no_op",
            hours=[],
            factor=None,
            minimum_energy_kwh=None,
            max_grid_kwh=None,
            applies=False,
        )
        return DirectiveValidationResult(is_valid=True, directive=normalized_noop, errors=[])

    # 3. Hours validation for active directives
    raw_hours = payload.get("hours")
    if raw_hours is None:
        errors.append(
            DirectiveValidationErrorItem(
                field="hours",
                message=f"Directive '{directive_type}' requires non-empty target 'hours'.",
                code="MISSING_HOURS",
                value=None,
            )
        )
    else:
        hour_errs = _validate_hours_list(raw_hours)
        errors.extend(hour_errs)

    # 4. Directive-specific parameter validations
    factor_val: float | None = None
    reserve_val: float | None = None
    max_grid_val: float | None = None

    if directive_type == "solar_reduction":
        raw_factor = payload.get("factor")
        if raw_factor is None:
            errors.append(
                DirectiveValidationErrorItem(
                    field="factor",
                    message="solar_reduction requires 'factor'.",
                    code="MISSING_FACTOR",
                    value=None,
                )
            )
        elif not _is_finite_number(raw_factor):
            errors.append(
                DirectiveValidationErrorItem(
                    field="factor",
                    message=f"solar_reduction factor must be a numeric value, got {raw_factor!r}.",
                    code="INVALID_FACTOR_TYPE",
                    value=raw_factor,
                )
            )
        elif not (0.0 <= float(raw_factor) <= 1.0):
            errors.append(
                DirectiveValidationErrorItem(
                    field="factor",
                    message=f"solar_reduction factor must be in [0.0, 1.0], got {raw_factor}.",
                    code="FACTOR_OUT_OF_BOUNDS",
                    value=raw_factor,
                )
            )
        else:
            factor_val = float(raw_factor)

    elif directive_type == "minimum_battery_reserve":
        raw_reserve = payload.get("minimum_energy_kwh")
        if raw_reserve is None:
            raw_reserve = payload.get("reserve")

        if raw_reserve is None:
            errors.append(
                DirectiveValidationErrorItem(
                    field="minimum_energy_kwh",
                    message="minimum_battery_reserve requires 'minimum_energy_kwh' (or 'reserve').",
                    code="MISSING_RESERVE",
                    value=None,
                )
            )
        elif not _is_finite_number(raw_reserve):
            errors.append(
                DirectiveValidationErrorItem(
                    field="minimum_energy_kwh",
                    message=f"Reserve must be a numeric value, got {raw_reserve!r}.",
                    code="INVALID_RESERVE_TYPE",
                    value=raw_reserve,
                )
            )
        elif float(raw_reserve) < 0.0:
            errors.append(
                DirectiveValidationErrorItem(
                    field="minimum_energy_kwh",
                    message=f"Reserve cannot be negative, got {raw_reserve}.",
                    code="NEGATIVE_RESERVE",
                    value=raw_reserve,
                )
            )
        elif battery_capacity is not None and float(raw_reserve) > battery_capacity:
            errors.append(
                DirectiveValidationErrorItem(
                    field="minimum_energy_kwh",
                    message=(
                        f"Reserve ({raw_reserve} kWh) cannot exceed battery capacity "
                        f"({battery_capacity} kWh)."
                    ),
                    code="RESERVE_EXCEEDS_CAPACITY",
                    value=raw_reserve,
                )
            )
        else:
            reserve_val = float(raw_reserve)

    elif directive_type == "max_grid_window":
        raw_max_grid = payload.get("max_grid_kwh")
        if raw_max_grid is None:
            raw_max_grid = payload.get("max_grid")

        if raw_max_grid is None:
            errors.append(
                DirectiveValidationErrorItem(
                    field="max_grid_kwh",
                    message="max_grid_window requires 'max_grid_kwh' (or 'max_grid').",
                    code="MISSING_MAX_GRID",
                    value=None,
                )
            )
        elif not _is_finite_number(raw_max_grid):
            errors.append(
                DirectiveValidationErrorItem(
                    field="max_grid_kwh",
                    message=f"max_grid_kwh must be a numeric value, got {raw_max_grid!r}.",
                    code="INVALID_MAX_GRID_TYPE",
                    value=raw_max_grid,
                )
            )
        elif float(raw_max_grid) < 0.0:
            errors.append(
                DirectiveValidationErrorItem(
                    field="max_grid_kwh",
                    message=f"max_grid_kwh cannot be negative, got {raw_max_grid}.",
                    code="NEGATIVE_MAX_GRID",
                    value=raw_max_grid,
                )
            )
        else:
            max_grid_val = float(raw_max_grid)

    # 5. Result assembly
    if errors:
        return DirectiveValidationResult(is_valid=False, directive=None, errors=errors)

    normalized = NormalizedDirective(
        note_index=note_index,
        directive_type=directive_type,  # type: ignore[arg-type]
        hours=list(raw_hours),
        factor=factor_val,
        minimum_energy_kwh=reserve_val,
        max_grid_kwh=max_grid_val,
        applies=applies,
    )
    return DirectiveValidationResult(is_valid=True, directive=normalized, errors=[])


def validate_directive_strict(
    raw: Any,
    battery_capacity: float | None = None,
) -> NormalizedDirective:
    """Validate a directive deterministically and return NormalizedDirective, or raise GuardrailValidationError.

    Raises:
        GuardrailValidationError: If validation fails with any rule violations.
    """
    result = validate_directive(raw, battery_capacity=battery_capacity)
    if not result.is_valid:
        msg = f"Directive validation failed: {'; '.join(result.error_messages)}"
        raise GuardrailValidationError(message=msg, errors=result.errors)
    assert result.directive is not None
    return result.directive


def validate_directive_batch(
    raw_list: Sequence[Any],
    battery_capacity: float | None = None,
) -> BatchDirectiveValidationResult:
    """Validate a sequence of raw directives deterministically.

    Args:
        raw_list: Sequence of raw directive dictionaries or objects.
        battery_capacity: Optional battery capacity in kWh for reserve checks.

    Returns:
        BatchDirectiveValidationResult with list of NormalizedDirectives and error details.
    """
    item_results: list[DirectiveValidationResult] = []
    all_errors: list[DirectiveValidationErrorItem] = []
    normalized_list: list[NormalizedDirective] = []

    for i, raw in enumerate(raw_list):
        if isinstance(raw, dict) and "note_index" not in raw:
            raw = {**raw, "note_index": i}
        res = validate_directive(raw, battery_capacity=battery_capacity)
        item_results.append(res)
        if not res.is_valid:
            all_errors.extend(res.errors)
        else:
            assert res.directive is not None
            normalized_list.append(res.directive)

    is_valid = len(all_errors) == 0
    return BatchDirectiveValidationResult(
        is_valid=is_valid,
        directives=normalized_list if is_valid else [],
        errors=all_errors,
        item_results=item_results,
    )


def validate_directive_batch_strict(
    raw_list: Sequence[Any],
    battery_capacity: float | None = None,
) -> list[NormalizedDirective]:
    """Validate a sequence of raw directives strictly, raising if any error occurs.

    Raises:
        GuardrailValidationError: If any directive violates validation rules.
    """
    batch_res = validate_directive_batch(raw_list, battery_capacity=battery_capacity)
    if not batch_res.is_valid:
        msg = (
            f"Batch directive validation failed with {len(batch_res.errors)} violation(s): "
            f"{'; '.join(batch_res.error_messages)}"
        )
        raise GuardrailValidationError(message=msg, errors=batch_res.errors)
    return batch_res.directives


class DeterministicDirectiveGuardrail:
    """Concrete implementation of IDirectiveGuardrail protocol.

    Provides both strict validation and safe fallback sanitization.
    """

    def validate(
        self,
        raw: Any,
        battery_capacity: float | None = None,
    ) -> DirectiveValidationResult:
        """Validate a single raw directive deterministically."""
        return validate_directive(raw, battery_capacity=battery_capacity)

    def validate_strict(
        self,
        raw: Any,
        battery_capacity: float | None = None,
    ) -> NormalizedDirective:
        """Validate a single directive strictly, raising on failure."""
        return validate_directive_strict(raw, battery_capacity=battery_capacity)

    def validate_batch(
        self,
        raw_list: Sequence[Any],
        battery_capacity: float | None = None,
    ) -> BatchDirectiveValidationResult:
        """Validate a batch of raw directives deterministically."""
        return validate_directive_batch(raw_list, battery_capacity=battery_capacity)

    def sanitize(
        self,
        raw_directives: list[dict],
        note_count: int,
        battery_capacity: float,
    ) -> list[NormalizedDirective]:
        """Validate and sanitize raw directive interpretations, falling back safely to no_op.

        If the item count or note index ordering is mismatched, degrades all items to no_op.
        Any individual invalid directive safely degrades to a no_op.
        """
        if len(raw_directives) != note_count:
            return [
                NormalizedDirective(note_index=i, directive_type="no_op", hours=[], applies=False)
                for i in range(note_count)
            ]

        results: list[NormalizedDirective] = []
        for i, raw in enumerate(raw_directives):
            idx = raw.get("note_index", i) if isinstance(raw, dict) else i
            if idx != i:
                return [
                    NormalizedDirective(
                        note_index=j, directive_type="no_op", hours=[], applies=False
                    )
                    for j in range(note_count)
                ]

            outcome = validate_directive(raw, battery_capacity=battery_capacity)
            if outcome.is_valid and outcome.directive is not None:
                results.append(outcome.directive)
            else:
                results.append(
                    NormalizedDirective(
                        note_index=i, directive_type="no_op", hours=[], applies=False
                    )
                )

        return results
