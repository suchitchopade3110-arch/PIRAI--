"""Central registry for the active, attributable PIRAI policy."""

from functools import lru_cache

from config import (
    ACTIVE_POLICY_VERSION, BLOCK_THRESHOLD, CODER_MODEL, REVIEW_THRESHOLD,
    SAFETY_MODEL, TOOL_POLICY_VERSION, ZERO_TOLERANCE, ZERO_TOLERANCE_THRESHOLD,
)
from governance.models import PolicyVersion

POLICY_CREATED_AT = "2026-10-01T00:00:00+00:00"


@lru_cache(maxsize=1)
def get_active_policy() -> PolicyVersion:
    return PolicyVersion(
        policy_version=ACTIVE_POLICY_VERSION,
        review_threshold=REVIEW_THRESHOLD,
        block_threshold=BLOCK_THRESHOLD,
        zero_tolerance_threshold=ZERO_TOLERANCE_THRESHOLD,
        zero_tolerance_categories=tuple(sorted(ZERO_TOLERANCE)),
        safety_classifier=SAFETY_MODEL,
        coding_model=CODER_MODEL,
        tool_policy_version=TOOL_POLICY_VERSION,
        created_at=POLICY_CREATED_AT,
        activated_at=POLICY_CREATED_AT,
    )
