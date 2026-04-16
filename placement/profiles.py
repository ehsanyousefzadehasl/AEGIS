from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyProfile:
    name: str
    estimate_source: str
    exclusive_first: bool
    uses_dispatcher: bool


POLICY_PROFILES = {
    "exclusive": PolicyProfile(
        name="exclusive",
        estimate_source="none",
        exclusive_first=True,
        uses_dispatcher=False,
    ),
    "oracle-FF": PolicyProfile(
        name="oracle-FF",
        estimate_source="oracle",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
    "oracle-BF": PolicyProfile(
        name="oracle-BF",
        estimate_source="oracle",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
    "oracle-MAGM": PolicyProfile(
        name="oracle-MAGM",
        estimate_source="oracle",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
    "oracle-LUG": PolicyProfile(
        name="oracle-LUG",
        estimate_source="oracle",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
    "OR-RR": PolicyProfile(
        name="OR-RR",
        estimate_source="none",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
    "OR-MAGM": PolicyProfile(
        name="OR-MAGM",
        estimate_source="none",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
    "OR-LUG": PolicyProfile(
        name="OR-LUG",
        estimate_source="none",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
    "EST-MAGM": PolicyProfile(
        name="EST-MAGM",
        estimate_source="task_file_estimate",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
    "EST-LUG": PolicyProfile(
        name="EST-LUG",
        estimate_source="task_file_estimate",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
    "ONLINE-EST-MAGM": PolicyProfile(
        name="ONLINE-EST-MAGM",
        estimate_source="online_estimate",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
    "ONLINE-EST-LUG": PolicyProfile(
        name="ONLINE-EST-LUG",
        estimate_source="online_estimate",
        exclusive_first=True,
        uses_dispatcher=True,
    ),
}


def get_policy_profile(policy: str) -> PolicyProfile:
    return POLICY_PROFILES[policy]