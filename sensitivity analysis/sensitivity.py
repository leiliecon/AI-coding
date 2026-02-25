import argparse
import json
from pathlib import Path

import pandas as pd


def load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    required_keys = [
        "sfp_data_file",
        "shock_file",
        "shock_types_file",
        "data_sheet",
        "shock_sheet",
        "t0",
        "start_date",
        "end_date",
        "output_before",
        "output_after",
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(f"Missing keys in config: {missing}")

    return config


def load_shock_types(shock_types_path: Path) -> dict:
    with shock_types_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if "shock_change_tested" not in payload:
        raise KeyError("Missing key 'shock_change_tested' in shock types file.")
    shock_types = payload["shock_change_tested"]
    if not isinstance(shock_types, list) or not all(
        isinstance(item, str) for item in shock_types
    ):
        raise TypeError("'shock_change_tested' must be a list of strings.")

    if "adjustments" not in payload:
        raise KeyError("Missing key 'adjustments' in shock types file.")
    adjustments = payload["adjustments"]
    if not isinstance(adjustments, dict):
        raise TypeError("'adjustments' must be an object.")

    for key in ["points_add", "bps_add", "decline_pct_of_t0"]:
        if key not in adjustments:
            raise KeyError(f"Missing key 'adjustments.{key}' in shock types file.")
        if not isinstance(adjustments[key], dict):
            raise TypeError(f"'adjustments.{key}' must be an object.")
        if not all(
            isinstance(k, str) and isinstance(v, (int, float))
            for k, v in adjustments[key].items()
        ):
            raise TypeError(
                f"'adjustments.{key}' must map string labels to numeric values."
            )

    fx_pct_rules = adjustments.get("pct_of_t0_add_by_mnemonic", [])
    if not isinstance(fx_pct_rules, list):
        raise TypeError("'adjustments.pct_of_t0_add_by_mnemonic' must be a list.")
    for idx, rule in enumerate(fx_pct_rules):
        if not isinstance(rule, dict):
            raise TypeError(
                f"'adjustments.pct_of_t0_add_by_mnemonic[{idx}]' must be an object."
            )
        required_rule_keys = {"shock_label", "mnemonics", "pct_of_t0_add"}
        missing = required_rule_keys - set(rule.keys())
        if missing:
            raise KeyError(
                "Missing keys in "
                f"'adjustments.pct_of_t0_add_by_mnemonic[{idx}]': {sorted(missing)}"
            )
        if not isinstance(rule["shock_label"], str):
            raise TypeError(
                f"'adjustments.pct_of_t0_add_by_mnemonic[{idx}].shock_label' must be a string."
            )
        mnemonics = rule["mnemonics"]
        if not isinstance(mnemonics, list) or not all(
            isinstance(m, str) for m in mnemonics
        ):
            raise TypeError(
                f"'adjustments.pct_of_t0_add_by_mnemonic[{idx}].mnemonics' must be a list of strings."
            )
        if not isinstance(rule["pct_of_t0_add"], (int, float)):
            raise TypeError(
                f"'adjustments.pct_of_t0_add_by_mnemonic[{idx}].pct_of_t0_add' must be numeric."
            )

    return payload


def get_period_columns(df: pd.DataFrame, t0: str, end_date: str) -> list[str]:
    columns = list(df.columns)
    if t0 not in columns:
        raise KeyError(f"t0 column '{t0}' not found in merged data.")
    if end_date not in columns:
        raise KeyError(f"end_date column '{end_date}' not found in merged data.")

    start_idx = columns.index(t0)
    end_idx = columns.index(end_date)
    if end_idx < start_idx:
        raise ValueError(f"end_date '{end_date}' appears before t0 '{t0}'.")

    return columns[start_idx : end_idx + 1]


def get_adjustment_columns(df: pd.DataFrame, start_date: str, end_date: str) -> list[str]:
    columns = list(df.columns)
    if start_date not in columns:
        raise KeyError(f"start_date column '{start_date}' not found in result data.")
    if end_date not in columns:
        raise KeyError(f"end_date column '{end_date}' not found in result data.")

    start_idx = columns.index(start_date)
    end_idx = columns.index(end_date)
    if end_idx < start_idx:
        raise ValueError(f"end_date '{end_date}' appears before start_date '{start_date}'.")

    return columns[start_idx : end_idx + 1]


def apply_shock_adjustments(
    res: pd.DataFrame, adjustment_cols: list[str], t0: str, adjustment_rules: dict
) -> pd.DataFrame:
    pts_adjustments = adjustment_rules["points_add"]
    for shock_label, delta in pts_adjustments.items():
        mask = res["Shock Change Tested"] == shock_label
        res.loc[mask, adjustment_cols] += delta

    bps_adjustments = adjustment_rules["bps_add"]
    for shock_label, delta in bps_adjustments.items():
        mask = res["Shock Change Tested"] == shock_label
        res.loc[mask, adjustment_cols] += delta

    decline_adjustments = adjustment_rules["decline_pct_of_t0"]
    for shock_label, pct in decline_adjustments.items():
        mask = res["Shock Change Tested"] == shock_label
        if mask.any():
            base = res.loc[mask, t0].to_numpy(dtype=float)
            adjusted = (
                res.loc[mask, adjustment_cols].to_numpy(dtype=float)
                - base[:, None] * pct
            )
            res.loc[mask, adjustment_cols] = adjusted

    fx_pct_rules = adjustment_rules.get("pct_of_t0_add_by_mnemonic", [])
    for rule in fx_pct_rules:
        mask = (
            (res["Shock Change Tested"] == rule["shock_label"])
            & (res["Mnemonic"].isin(rule["mnemonics"]))
        )
        if mask.any():
            base = res.loc[mask, t0].to_numpy(dtype=float)
            adjusted = (
                res.loc[mask, adjustment_cols].to_numpy(dtype=float)
                + base[:, None] * float(rule["pct_of_t0_add"])
            )
            res.loc[mask, adjustment_cols] = adjusted

    mask_ag = res["Mnemonic"] == "US.RFRRT.AQ.1M"
    mask_eq = res["Mnemonic"] == "US.RFRRT.EQ.1M"
    mask_aqr = res["Mnemonic"] == "US.SOVRT.AQ.1M"
    mask_eqr = res["Mnemonic"] == "US.SOVRT.EQ.1M"
    mask_sp = res["Mnemonic"] == "US.RFRSP.AQ.1M1M"

    res.loc[mask_ag, adjustment_cols] = (
        res.loc[mask_aqr, adjustment_cols].values
        + res.loc[mask_sp, adjustment_cols].values
    )

    res.loc[mask_eq, adjustment_cols] = (
        res.loc[mask_eqr, adjustment_cols].values
        + res.loc[mask_sp, adjustment_cols].values
    )

    return res


def run(config_path: Path) -> None:
    base_path = Path(__file__).resolve().parent
    config = load_config(config_path)

    sfp_data_path = base_path / config["sfp_data_file"]
    shock_path = base_path / config["shock_file"]
    shock_types_path = base_path / config["shock_types_file"]
    output_before_path = base_path / config["output_before"]
    output_after_path = base_path / config["output_after"]

    if not sfp_data_path.exists():
        raise FileNotFoundError(f"SFP data file not found: {sfp_data_path}")
    if not shock_path.exists():
        raise FileNotFoundError(f"Shock file not found: {shock_path}")
    if not shock_types_path.exists():
        raise FileNotFoundError(f"Shock types file not found: {shock_types_path}")

    data = pd.read_excel(sfp_data_path, sheet_name=config["data_sheet"])
    shock = pd.read_excel(shock_path, sheet_name=config["shock_sheet"])
    shock_types_payload = load_shock_types(shock_types_path)
    expected_shock_types = shock_types_payload["shock_change_tested"]

    required_data_cols = {"Mnemonic"}
    required_shock_cols = {"Mnemonic", "Shock Change Tested"}
    if not required_data_cols.issubset(data.columns):
        raise KeyError(f"Data file is missing required columns: {required_data_cols}")
    if not required_shock_cols.issubset(shock.columns):
        raise KeyError(f"Shock file is missing required columns: {required_shock_cols}")

    shock_needed = shock.loc[:, ["Mnemonic", "Shock Change Tested"]]
    merged_df = pd.merge(shock_needed, data, on="Mnemonic", how="inner")

    period_cols = get_period_columns(merged_df, config["t0"], config["end_date"])
    res = merged_df.loc[:, ["Mnemonic", "Shock Change Tested"] + period_cols].copy()

    res["extra shock"] = pd.to_numeric(
        res["Shock Change Tested"].str.extract(r"(\d+(?:\.\d+)?)", expand=False),
        errors="coerce",
    )

    cols = list(res.columns)
    res = res.loc[:, cols[:2] + [cols[-1]] + cols[2:-1]]
    res.to_excel(output_before_path, index=False)

    grouped = res.groupby("Shock Change Tested").size()
    print(grouped)
    observed_types = set(res["Shock Change Tested"].dropna().unique())
    expected_types = set(expected_shock_types)
    missing_types = sorted(expected_types - observed_types)
    unexpected_types = sorted(observed_types - expected_types)
    print(f"Expected shock type count: {len(expected_shock_types)}")
    print(f"Observed shock type count: {len(observed_types)}")
    if missing_types:
        print(f"Missing expected shock types: {missing_types}")
    if unexpected_types:
        print(f"Unexpected shock types: {unexpected_types}")

    adjustment_cols = get_adjustment_columns(
        res, config["start_date"], config["end_date"]
    )
    res = apply_shock_adjustments(
        res, adjustment_cols, config["t0"], shock_types_payload["adjustments"]
    )
    res.to_excel(output_after_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run sensitivity analysis adjustments.")
    parser.add_argument(
        "--config",
        default="sensitivity_config.json",
        help="Path to JSON config file (relative to this script directory if not absolute).",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent / config_path

    run(config_path)


if __name__ == "__main__":
    main()
