# path2shock_calculation.py
# This code provides shock calculation from path files to Shock
# Updates json files before running the calculations
# Requires config.json and groups.json to be set up correctly

import json
import os
import warnings
import pandas as pd

# ------------------ Paths ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# All JSON/Excel inputs live here.
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_PATH = os.path.join(BASE_DIR, "output")

CONFIG_JSON = os.path.join(INPUT_DIR, "config.json")
GROUPS_JSON = os.path.join(INPUT_DIR, "groups.json")
FORMAT_RULES_JSON = os.path.join(INPUT_DIR, "format_rules.json")


def _load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = _load_config(CONFIG_JSON)

REQUIRED_CONFIG_KEYS = {
    "mapping_excel",
    "data_excel",
    "mapping_sheet_name",
    "data_sheet_name",
    "group_rates_up_scenarios",
    "T0",
    "scen_start",
    "scen_end",
}

missing_config = REQUIRED_CONFIG_KEYS - set(CONFIG.keys())
if missing_config:
    missing_str = ", ".join(sorted(missing_config))
    raise ValueError(f"Missing required config keys: {missing_str}")

MAPPING_EXCEL = CONFIG["mapping_excel"]
DATA_EXCEL = CONFIG["data_excel"]
MAPPING_SHEET_NAME = CONFIG["mapping_sheet_name"]
DATA_SHEET_NAME = CONFIG["data_sheet_name"]
UP_SCENARIOS = set(CONFIG["group_rates_up_scenarios"])
T0 = CONFIG["T0"]
SCEN_START = CONFIG["scen_start"]
SCEN_END = CONFIG["scen_end"]


def _load_groups(groups_path):
    with open(groups_path, "r", encoding="utf-8") as f:
        groups_raw = json.load(f)
    return {k: set(v) for k, v in groups_raw.items()}


def _load_format_rules(format_rules_path):
    if not os.path.exists(format_rules_path):
        return {}
    with open(format_rules_path, "r", encoding="utf-8") as f:
        rules_raw = json.load(f)
    return rules_raw.get("format_rules", {})


def _validate_groups(groups):
    all_items = []
    for items in groups.values():
        all_items.extend(items)
    duplicates = {x for x in all_items if all_items.count(x) > 1}
    if duplicates:
        duplicates_str = ", ".join(sorted(duplicates))
        raise ValueError(f"Duplicate M names across groups: {duplicates_str}")


GROUPS = _load_groups(GROUPS_JSON)
_validate_groups(GROUPS)
GROUP_MIN_PERCENT = GROUPS.get("group_min_percent", set())
GROUP_MAX_PERCENT = GROUPS.get("group_max_percent", set())
GROUP_MAX_CHANGE = GROUPS.get("group_max_change", set())
GROUP_CPI = GROUPS.get("group_cpi", set())
GROUP_RATES = GROUPS.get("group_rates", set())
FORMAT_RULES = _load_format_rules(FORMAT_RULES_JSON) or {}


def _format_extreme_level(value, fmt):
    if fmt == "ppts_signed" and pd.notna(value) and value > 0:
        return f"+{value} ppts"
    if fmt in {"ppts", "ppts_signed"}:
        return f"{value} ppts"
    if fmt == "percent" and pd.notna(value):
        return f"{round(value * 100, 1)} %"
    if fmt == "bps_signed" and pd.notna(value):
        bps_value = value * 100
        bps_text = f"{bps_value:.0f}"
        if bps_value > 0:
            return f"+{bps_text} bps"
        return f"{bps_text} bps"
    if fmt == "bps" and pd.notna(value):
        bps_value = value * 100
        return f"{bps_value:.0f} bps"
    return value


def _apply_group_min_percent(df, range_columns):
    condition = df["M names"].isin(GROUP_MIN_PERCENT)
    shock_pct = range_columns.loc[condition].min(axis=1) / df.loc[condition, T0] - 1
    df.loc[condition, "shock"] = shock_pct


def _apply_group_max_percent(df, range_columns):
    condition = df["M names"].isin(GROUP_MAX_PERCENT)
    shock_pct = range_columns.loc[condition].max(axis=1) / df.loc[condition, T0] - 1
    df.loc[condition, "shock"] = shock_pct


def _apply_group_max_change(df, range_columns):
    condition = df["M names"].isin(GROUP_MAX_CHANGE)
    df.loc[condition, "shock"] = (
        range_columns.loc[condition].max(axis=1) - df.loc[condition, T0]
    )
    df.loc[condition, "extreme_level"] = range_columns.loc[condition].max(axis=1)


def _apply_format_rules(df):
    default_rule = FORMAT_RULES.get("default", {})
    def _apply_rule(mask, rule):
        shock_suffix = rule.get("shock_suffix", "")
        shock_format = rule.get("shock_format", "")
        extreme_format = rule.get("extreme_format", "")
        extreme_wrap = rule.get("extreme_wrap", "")
        if shock_format:
            shock_vals = df.loc[mask, "shock"]
            if shock_format == "percent":
                df.loc[mask, "shock"] = shock_vals.map(
                    lambda v: f"{round(v * 100, 1)} %" if pd.notna(v) else v
                )
            if shock_format == "percent_compact":
                df.loc[mask, "shock"] = shock_vals.map(
                    lambda v: f"{round(v * 100, 1)}%" if pd.notna(v) else v
                )
            if shock_format == "percent_compact_raw":
                df.loc[mask, "shock"] = shock_vals.map(
                    lambda v: f"{round(v, 1)}%" if pd.notna(v) else v
                )
        if shock_suffix:
            df.loc[mask, "shock"] = df.loc[mask, "shock"].astype(str) + shock_suffix
        if extreme_format or extreme_wrap:
            extreme = df.loc[mask, "extreme_level"]
            if extreme_format:
                extreme = extreme.map(
                    lambda v: _format_extreme_level(v, extreme_format)
                )
            if extreme_wrap == "parens":
                extreme = extreme.map(lambda v: f"({v})" if pd.notna(v) else v)
            df.loc[mask, "extreme_level"] = extreme

    for m_name in df["M names"].dropna().unique():
        rule = FORMAT_RULES.get(m_name, default_rule)
        m_condition = df["M names"] == m_name

        shock_format_up = rule.get("shock_format_up")
        shock_format_other = rule.get("shock_format_other")
        shock_suffix_up = rule.get("shock_suffix_up")
        shock_suffix_other = rule.get("shock_suffix_other")
        extreme_format_up = rule.get("extreme_format_up")
        extreme_format_other = rule.get("extreme_format_other")
        extreme_wrap_up = rule.get("extreme_wrap_up")
        extreme_wrap_other = rule.get("extreme_wrap_other")

        if any(
            [
                shock_format_up,
                shock_format_other,
                shock_suffix_up,
                shock_suffix_other,
                extreme_format_up,
                extreme_format_other,
                extreme_wrap_up,
                extreme_wrap_other,
            ]
        ):
            up_mask = m_condition & df["Scenario"].isin(UP_SCENARIOS)
            other_mask = m_condition & ~df["Scenario"].isin(UP_SCENARIOS)
            _apply_rule(
                up_mask,
                {
                    "shock_format": shock_format_up,
                    "shock_suffix": shock_suffix_up,
                    "extreme_format": extreme_format_up,
                    "extreme_wrap": extreme_wrap_up,
                },
            )
            _apply_rule(
                other_mask,
                {
                    "shock_format": shock_format_other,
                    "shock_suffix": shock_suffix_other,
                    "extreme_format": extreme_format_other,
                    "extreme_wrap": extreme_wrap_other,
                },
            )
            continue

        if not rule:
            continue
        _apply_rule(m_condition, rule)


def _apply_group_cpi(df):
    condition = df["M names"].isin(GROUP_CPI)
    cpi = df.loc[condition, T0:SCEN_END].astype(float)
    cpi_change = (1 + cpi.pct_change(periods=1, axis=1)) ** 4 - 1
    cpi_change = cpi_change.apply(pd.to_numeric, errors="coerce")
    df.loc[condition, "shock"] = cpi_change.min(axis=1, skipna=True)
    df.loc[condition, "extreme_level"] = cpi_change.max(axis=1, skipna=True)


def _apply_group_rates(df, range_columns):
    base_condition = df["M names"].isin(GROUP_RATES)
    UP_condition = base_condition & df["Scenario"].isin(UP_SCENARIOS)
    other_condition = base_condition & ~df["Scenario"].isin(UP_SCENARIOS)

    df.loc[UP_condition, "shock"] = (
        range_columns.loc[UP_condition].max(axis=1) - df.loc[UP_condition, T0]
    )
    df.loc[UP_condition, "extreme_level"] = range_columns.loc[UP_condition].max(axis=1)

    df.loc[other_condition, "shock"] = (
        range_columns.loc[other_condition].min(axis=1) - df.loc[other_condition, T0]
    )
    df.loc[other_condition, "extreme_level"] = range_columns.loc[
        other_condition
    ].min(axis=1)


def calculate_shocks(df, range_columns):
    _apply_group_min_percent(df, range_columns)
    _apply_group_max_percent(df, range_columns)
    _apply_group_max_change(df, range_columns)
    _apply_group_cpi(df)
    _apply_group_rates(df, range_columns)
    _apply_format_rules(df)


def save_scenario_outputs(df, output_path):
    for scen in df["Scenario"].unique():
        res1 = df[df["Scenario"] == scen].copy()
        res1 = res1[["M names", "Slides name", "shock", "extreme_level"]]
        res1 = res1[res1["shock"].notna()]
        file_name = f"path2shock_{scen}.xlsx"
        res1.to_excel(output_path + os.sep + file_name, index=False)


def _validate_data(df, range_columns):
    required_cols = {"M names", "Scenario", "Slides name", T0}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        missing_str = ", ".join(sorted(missing_cols))
        raise ValueError(f"Missing required columns: {missing_str}")

    if range_columns.empty:
        raise ValueError(
            f"Scenario range columns not found: {SCEN_START} to {SCEN_END}"
        )

    data_names = set(df["M names"].dropna().unique())
    group_names = set().union(
        GROUP_MIN_PERCENT,
        GROUP_MAX_PERCENT,
        GROUP_MAX_CHANGE,
        GROUP_CPI,
        GROUP_RATES,
    )
    # Note: missing/extra group assignments are allowed without warnings.


def run_path2shock(
    mapping_excel=MAPPING_EXCEL,
    data_excel=DATA_EXCEL,
    output_path=OUTPUT_PATH,
    t0=T0,
    scen_start=SCEN_START,
    scen_end=SCEN_END,
):
    mapping = pd.read_excel(
        os.path.join(INPUT_DIR, f"{mapping_excel}.xlsx"),
        sheet_name=MAPPING_SHEET_NAME,
    )
    path_df = pd.read_excel(
        os.path.join(INPUT_DIR, f"{data_excel}.xlsx"),
        sheet_name=DATA_SHEET_NAME,
    )
    res = mapping.merge(path_df, on="M names", how="left")
    res.columns = [col.replace("Q", ".") for col in res.columns]
    res["shock"] = None
    res["extreme_level"] = None
    range_columns = res.loc[:, scen_start:scen_end]
    _validate_data(res, range_columns)
    os.makedirs(output_path, exist_ok=True)
    calculate_shocks(res, range_columns)
    save_scenario_outputs(res, output_path)
    return res


if __name__ == "__main__":
    run_path2shock()
