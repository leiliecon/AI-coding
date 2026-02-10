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
- `config.json`: source file/sheet names, T0, scenario range, and up-scenario list
- `export_rules.json`: export fill behavior (`scenario_aliases`, `default_fill_mode`, `m_fill_modes`)
- `groups.json`: group definitions for shock logic
- `format_rules.json`: text formatting rules for `shock` and `extreme_level`
- `mapping.xlsx`, `path.xlsx`, `template_input.xlsx`

### Before You Run
- Update `input/config.json` before running.
- Update `input/export_rules.json` `scenario_aliases` before running.

## Export Fill Modes (`export_rules.json`)
- `single_shock`: fill one cell with `shock`
- `two_row_extreme_then_shock`: first row `extreme_level`, second row `shock`
- `two_row_shock_then_extreme`: first row `shock`, second row `extreme_level`
- `range_extreme_to_shock`: one cell as `"<extreme_level> to <shock>"`

## Notes
- Scenario matching in export is case-insensitive.
- Export output cells are center-aligned.
- If you add scenarios, just add their output files and template columns (plus alias if needed).
