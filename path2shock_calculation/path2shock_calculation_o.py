# -*- coding: utf-8 -*-
# This code provides shock calculation from path files to Shock
# Updates scenario names in group 5

import os
import pandas as pd

# ------------------ Paths ------------------
path = os.path.dirname(os.path.abspath(__file__))
output_path = path + "/path2shock/"

mapping_excel = "mapping"
data_excel = "path"

mapping = pd.read_excel(path + os.sep + mapping_excel + ".xlsx", sheet_name="Sheet1")
path = pd.read_excel(path + os.sep + data_excel + ".xlsx", sheet_name="Sheet1")

res = mapping.merge(path, on="M names", how="left")
res.columns = [col.replace("Q", ".") for col in res.columns]

# ------------------ Scenario Range ------------------
T0 = "2025.4"
scen_start = "2026.1"
scen_end = "2029.1"

res["shock"] = None
res["extreme_level"] = None

range_columns = res.loc[:, scen_start:scen_end]

# ================== LOOP BY SCENARIO ==================
for scen in res["Scenario"].unique():

    # ---------- Group 1 : min change percent ----------
    condition = (
        res["M names"].isin([
            "M1", "M2", "M3", "M4",
            "M5", "M6", "M7", "M8", "M9"
        ])
    ) & (res["Scenario"] == scen)

    res.loc[condition, "shock"] = (
        range_columns.loc[condition].min(axis=1) / res.loc[condition, T0] - 1
    )

    # ---------- Group 2 : max change percent ----------
    condition = (
        res["M names"].isin(["M10"])
    ) & (res["Scenario"] == scen)

    res.loc[condition, "shock"] = (
        range_columns.loc[condition].max(axis=1) / res.loc[condition, T0] - 1
    )

    # ---------- Group 3 : max change level ----------
    condition = (
        res["M names"].isin([
            "M11", "M12", "M13", "M14",
            "M15", "M16", "M17", "M18", "M19"
        ])
    ) & (res["Scenario"] == scen)

    res.loc[condition, "shock"] = (
        range_columns.loc[condition].max(axis=1) - res.loc[condition, T0]
    )
    res.loc[condition, "extreme_level"] = range_columns.loc[condition].max(axis=1)

    # ---------- Group 4 : CPI ----------
    condition = (
        (res["M names"] == "M20") &
        (res["Scenario"] == scen)
    )

    cpi = res.loc[condition, T0:scen_end].astype(float).dropna()
    cpi_change = (1 + cpi.pct_change(periods=1, axis=1))**4 - 1
    cpi_change = cpi_change.apply(pd.to_numeric, errors="coerce")

    res.loc[condition, "shock"] = cpi_change.min(axis=1, skipna=True).values[0]
    res.loc[condition, "extreme_level"] = cpi_change.max(axis=1, skipna=True).values[0]

    # ---------- Group 5 : Rates ----------
    name_rates = {
        "M21",
        "M22",
        "M23",
        "M24"
    }

    condition = (
        res["M names"].isin(name_rates)
    ) & (res["Scenario"] == scen)

    if scen in ["S1"]:
        res.loc[condition, "shock"] = (
            range_columns.loc[condition].max(axis=1) - res.loc[condition, T0]
        )
        res.loc[condition, "extreme_level"] = range_columns.loc[condition].max(axis=1)
    else:
        res.loc[condition, "shock"] = (
            range_columns.loc[condition].min(axis=1) - res.loc[condition, T0]
        )
        res.loc[condition, "extreme_level"] = range_columns.loc[condition].min(axis=1)

    # ---------- Save Results ----------
    res1 = res[res["Scenario"] == scen].copy()
    res1 = res1[["M names", "Slides name", "shock", "extreme_level"]]
    res1 = res1[res1["shock"].notna()]

    file_name = f"path2shock_{scen}.xlsx"
    res1.to_excel(output_path + os.sep + file_name, index=False)