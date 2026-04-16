from __future__ import annotations

import logging
import os

from estimation import rad_parser

DEFAULT_ESTIMATE_MIB = 5120

def estimate_online_gpu_memory(
    *,
    spec,
    workdir: str,
    estimator_name: str,
) -> int:
    try:
        summary_path_raw = getattr(spec, "online_summary_path", None)
        model_name = getattr(spec, "online_parser_arg_1", None)
        model_arg_raw = getattr(spec, "online_parser_arg_2", None)

        if summary_path_raw is None or model_name is None or model_arg_raw is None:
            logging.warning("Online estimator '%s': missing parser fields, using fallback", estimator_name)
            return DEFAULT_ESTIMATE_MIB

        try:
            model_arg = int(model_arg_raw)
        except ValueError:
            logging.warning("Online estimator '%s': invalid model arg, using fallback", estimator_name)
            return DEFAULT_ESTIMATE_MIB

        summary_path = (
            summary_path_raw
            if os.path.isabs(summary_path_raw)
            else os.path.join(workdir, summary_path_raw)
        )

        if not os.path.exists(summary_path):
            logging.warning("Online estimator '%s': summary file missing, using fallback", estimator_name)
            return DEFAULT_ESTIMATE_MIB

        # Placeholder for now: parser is exercised, but estimate remains conservative
        rad_parser.analyze_model_summary(
            summary_path,
            model_name,
            model_arg,
        )

        logging.warning(
            "Online estimator '%s' is not connected yet, using fallback estimate",
            estimator_name,
        )
        return DEFAULT_ESTIMATE_MIB

    except Exception as e:
        logging.warning(
            "Online estimator '%s' failed (%s), using fallback",
            estimator_name,
            e,
        )
        return DEFAULT_ESTIMATE_MIB