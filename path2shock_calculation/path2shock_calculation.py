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


def _apply_group_min_percent(df, range_columns):
    condition = df["M names"].isin(GROUP_MIN_PERCENT)
    df.loc[condition, "shock"] = (
        range_columns.loc[condition].min(axis=1) / df.loc[condition, T0] - 1
    )


def _apply_group_max_percent(df, range_columns):
    condition = df["M names"].isin(GROUP_MAX_PERCENT)
    df.loc[condition, "shock"] = (
        range_columns.loc[condition].max(axis=1) / df.loc[condition, T0] - 1
    )


def _apply_group_max_change(df, range_columns):
    condition = df["M names"].isin(GROUP_MAX_CHANGE)
    df.loc[condition, "shock"] = (
        range_columns.loc[condition].max(axis=1) - df.loc[condition, T0]
    )
    df.loc[condition, "extreme_level"] = range_columns.loc[condition].max(axis=1)


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
    missing_groups = data_names - group_names
    if missing_groups:
        missing_groups_str = ", ".join(sorted(missing_groups))
        raise ValueError(f"Missing group assignments for: {missing_groups_str}")

    extra_groups = group_names - data_names
    if extra_groups:
        extra_groups_str = ", ".join(sorted(extra_groups))
        warnings.warn(f"Group entries not found in data: {extra_groups_str}")


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
