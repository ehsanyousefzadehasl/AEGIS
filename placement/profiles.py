from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyProfile:
    name: str
    estimate_source: str
    exclusive_first: bool
    uses_dispatcher: bool
    placement_strategy: str | None
    required_profile_metrics: tuple[str, ...] = ()


POLICY_PROFILES = {
    "exclusive": PolicyProfile(
        name="exclusive",
        estimate_source="none",
        exclusive_first=True,
        uses_dispatcher=False,
        placement_strategy=None,
    ),
    "oracle-FF": PolicyProfile(
        name="oracle-FF",
        estimate_source="oracle",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="oracle_ff",
    ),
    "oracle-BF": PolicyProfile(
        name="oracle-BF",
        estimate_source="oracle",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="oracle_bf",
    ),
    "oracle-MAGM": PolicyProfile(
        name="oracle-MAGM",
        estimate_source="oracle",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="oracle_magm",
    ),
    "oracle-LUG": PolicyProfile(
        name="oracle-LUG",
        estimate_source="oracle",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="oracle_lug",
    ),
    "OR-RR": PolicyProfile(
        name="OR-RR",
        estimate_source="none",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="or_rr",
    ),
    "OR-MAGM": PolicyProfile(
        name="OR-MAGM",
        estimate_source="none",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="or_magm",
    ),
    "OR-LUG": PolicyProfile(
        name="OR-LUG",
        estimate_source="none",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="or_lug",
    ),
    "EST-MAGM": PolicyProfile(
        name="EST-MAGM",
        estimate_source="task_file_estimate",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="est_magm",
    ),
    "EST-LUG": PolicyProfile(
        name="EST-LUG",
        estimate_source="task_file_estimate",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="est_lug",
    ),
    "ONLINE-EST-MAGM": PolicyProfile(
        name="ONLINE-EST-MAGM",
        estimate_source="online_estimate",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="est_magm",
    ),
    "ONLINE-EST-LUG": PolicyProfile(
        name="ONLINE-EST-LUG",
        estimate_source="online_estimate",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="est_lug"
    ),
    "PROFILED-MAGM": PolicyProfile(
        name="PROFILED-MAGM",
        estimate_source="profiled_metadata",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="est_magm",
        required_profile_metrics=("peak_memory_mib",)
    ),
    "PROFILED-LUG": PolicyProfile(
        name="PROFILED-LUG",
        estimate_source="profiled_metadata",
        exclusive_first=True,
        uses_dispatcher=True,
        placement_strategy="est_lug",
        required_profile_metrics=("peak_memory_mib",)
    ),
}


def get_policy_profile(policy: str) -> PolicyProfile:
    return POLICY_PROFILES[policy]

def policy_required_profile_metrics(policy: str) -> tuple[str, ...]:
    return get_policy_profile(policy).required_profile_metrics

def policy_requires_estimator(policy: str) -> bool:
    return get_policy_profile(policy).estimate_source in {
        "task_file_estimate",
        "online_estimate",
    }

def policy_required_profile_metrics(policy: str) -> tuple[str, ...]:
    return get_policy_profile(policy).required_profile_metrics

def policy_estimate_source(policy: str) -> str:
    return get_policy_profile(policy).estimate_source

def policy_placement_strategy(policy: str) -> str | None:
    return get_policy_profile(policy).placement_strategy

def policy_uses_dispatcher(policy: str) -> bool:
    return get_policy_profile(policy).uses_dispatcher