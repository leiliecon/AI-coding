# Path2Shock Calculation

This project calculates scenario shocks from path data in Excel files. It merges a mapping table with scenario paths, applies group-specific shock rules, and writes per-scenario outputs to `output/`.

## What It Does
Given:
- A mapping file that links `M names` to `Slides name`
- A path file with scenarios and time series columns
- JSON config for file/sheet names and scenario ranges
- JSON group definitions that drive shock logic

The script:
1. Validates inputs and group coverage.
2. Computes shocks and extreme levels by group rules.
3. Writes one Excel file per scenario to `output/`.

## Requirements
- Python 3.9+ recommended
- `pandas`
- Excel engine for pandas (e.g., `openpyxl`)

## Folder Layout
- `path2shock_calculation.py` main logic
- `input/` input files and configs
- `output/` generated results

## Input Files
All inputs live in `input/`.

### `input/config.json`
Controls file names, sheets, and scenario range.

Example:
```json
{
  "mapping_excel": "mapping",
  "data_excel": "path",
  "mapping_sheet_name": "Sheet1",
  "data_sheet_name": "Sheet1",
  "group_rates_up_scenarios": ["Up"],
  "T0": "2025.4",
  "scen_start": "2026.1",
  "scen_end": "2029.1"
}
```

Field meanings:
- `mapping_excel`: mapping file name without `.xlsx`
- `data_excel`: path file name without `.xlsx`
- `mapping_sheet_name`: sheet name in the mapping file
- `data_sheet_name`: sheet name in the path file
- `group_rates_up_scenarios`: scenario labels treated as “up” for rate shocks
- `T0`: base column (time 0) in the path sheet
- `scen_start`: first scenario column used for range calculations
- `scen_end`: last scenario column used for range calculations

### `input/groups.json`
Defines which `M names` belong to each rule group. Every `M name` in data must appear in exactly one group.

Groups:
- `group_min_percent`: shock = min(range)/T0 - 1
- `group_max_percent`: shock = max(range)/T0 - 1
- `group_max_change`: shock = max(range) - T0
- `group_cpi`: shock = min quarterly YoY CPI change; extreme = max quarterly YoY CPI change
- `group_rates`: shock depends on scenario direction (up uses max change, others use min change)

### Excel Inputs
Mapping file (e.g., `input/mapping.xlsx`) must contain:
- `M names`
- `Slides name`

Path file (e.g., `input/path.xlsx`) must contain:
- `M names`
- `Scenario`
- `Slides name` (optional in the path file; the merge brings it from mapping if present there)
- `T0` column (from `config.json`)
- Scenario range columns from `scen_start` to `scen_end`

## How To Run
Use the module function in a short script or interactive session.

```bash
python -c "from path2shock_calculation import run_path2shock; run_path2shock()"
```

Outputs are written to `output/` as:
- `path2shock_<Scenario>.xlsx`

## Notes
- The script validates that every `M name` is assigned to exactly one group.
- If any group contains names not found in the data, a warning is emitted.
- If any data rows are missing group assignments, it raises a `ValueError`.
