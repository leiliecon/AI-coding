# Path2Shock

Calculates shocks from path data and exports a presentation-ready table.

## Run
```bash
python run_all.py
```

This runs:
1. `path2shock_calculation.py` -> creates per-scenario files in `output/` (`path2shock_<Scenario>.xlsx`)
2. `path2shock_export.py` -> fills `input/template_input.xlsx` and writes `output/path2shock_finalV.xlsx`

## Main Files
- `run_all.py`: runs full pipeline
- `path2shock_calculation.py`: shock/extreme calculation + formatting
- `path2shock_export.py`: template filling/export logic

## Input Folder (`input/`)
- `config.json`: source file/sheet names, T0, scenario range, rates up-scenarios, and baseline scenarios
- `export_rules.json`: export fill behavior (`scenario_aliases`, `default_fill_mode`, `m_fill_modes`)
- `groups.json`: group definitions for shock logic
- `format_rules.json`: text formatting rules for `shock` and `extreme_level`
- `mapping.xlsx`, `path.xlsx`, `template_input.xlsx`

### Before You Run
- Update `input/config.json` before running.
- Update `input/export_rules.json` `scenario_aliases` before running.

## Shock Logic
- `group_min_eqt`: in `group_baseline_scenarios`, shock = `first_forecast_year_Q4 / last_history_year_Q4 - 1`
- `group_min_hpi_cre`: in `group_baseline_scenarios`, shock = `max(scen_start:scen_end) / T0 - 1`
- `group_min_gdp-fx`: in `group_baseline_scenarios`, shock = average of:
  `first_forecast_year_Q4 / last_history_year_Q4 - 1`
  and
  `second_forecast_year_Q4 / first_forecast_year_Q4 - 1`
- For scenarios not in `group_baseline_scenarios`, all three groups above fall back to the standard min-percent logic:
  `min(scen_start:scen_end) / T0 - 1`
- `group_max_percent`: `max(scen_start:scen_end) / T0 - 1`
- `group_max_change`: `max(scen_start:scen_end) - T0`
- `group_cpi`: annualized quarterly change over `T0:scen_end`, then min shock / max extreme
- `group_rates`: uses `group_rates_up_scenarios` for up-vs-other direction

## Config Keys (`config.json`)
- `group_rates_up_scenarios`: scenarios where `group_rates` uses `max(range) - T0`
- `group_baseline_scenarios`: scenarios where the baseline formulas are used for `group_min_eqt`, `group_min_hpi_cre`, and `group_min_gdp-fx`
- `scen_start`: also defines `first_forecast_year`
- `scen_end`: end of the scenario range used for min/max calculations
- `T0`: starting comparison column

## Format Rules
- `percent` renders like `17.4 %`
- `percent_compact` renders like `17.4%`
- Baseline-only formatting is supported with keys like:
  `shock_format_baseline`, `shock_suffix_baseline`, `shock_wrap_baseline`
- Current baseline-only display suffixes are:
  `group_min_eqt` -> `x%+`
  `group_min_hpi_cre` -> `x%#`
  `group_min_gdp-fx` -> `x%*`

## Export Fill Modes (`export_rules.json`)
- `single_shock`: fill one cell with `shock`
- `two_row_extreme_then_shock`: first row `extreme_level`, second row `shock`
- `two_row_shock_then_extreme`: first row `shock`, second row `extreme_level`
- `range_extreme_to_shock`: one cell as `"<extreme_level> to <shock>"`

## Notes
- Scenario matching in export is case-insensitive.
- Export output cells are center-aligned.
- If you add scenarios, just add their output files and template columns (plus alias if needed).
- Baseline formulas require the relevant Q4 columns to exist in the input data, such as `2025.4`, `2026.4`, `2027.4`.
