# Sensitivity Analysis Script

This project runs sensitivity adjustments on quarterly scenario data using JSON-driven inputs.

## Files
- `sensitivity.py`: main script.
- `export_to_template.py`: writes adjusted outputs into template sheets and generates comparison output.
- `input/sensitivity_config.json`: runtime config (input files, sheets, dates, output paths).
- `input/shock_types.json`: expected `Shock Change Tested` values and adjustment mappings.
- `input/`: folder for source input files.
- `output/`: folder for generated output files.

## How To Run
```bash
python3 sensitivity.py
```

Or with a custom config:
```bash
python3 sensitivity.py --config your_config.json
```

Export to template and generate comparison:
```bash
python3 export_to_template.py
```

## Inputs
1. Scenario data Excel (`sfp_data_file`) with `Mnemonic` and period columns (for example `2025.4`, `2026.1`).
2. Shock mapping Excel (`shock_file`) with columns:
- `Mnemonic`
- `Shock Change Tested`
3. Shock type JSON (`shock_types_file`) with:
- `shock_change_tested` (list of expected types)
- `adjustments`:
  - `points_add`
  - `bps_add`
  - `decline_pct_of_t0`
  - `pct_of_t0_add_by_mnemonic` (optional rule list for mnemonic-specific percentage adjustments off `t0`)
  - `sum_by_shock_label_and_mnemonic` (optional rule list for computed series under a specific `Shock Change Tested` type)

## Outputs
- `output_before`: merged dataset before adjustments (now written under `output/`).
- `output_after`: dataset after adjustments (now written under `output/`).
- `output/<shock_file_stem>_distribution.xlsx`: filled template workbook.
- `output/comparison.xlsx`: comparison workbook where `t0:end_date` columns are `template_after_sheet - shock_sheet`.

## Notes
- Date range columns are controlled by `t0`, `start_date`, and `end_date` in `input/sensitivity_config.json`.
- Relative paths in config are resolved from the config file location (`input/` by default).
- `export_to_template.py` matches rows by `Mnemonic` + `Shock Change Tested` (fallback: `Mnemonic` only).
- `comparison.xlsx` appends `before_shock`, `after_shock`, `diff`.
- Extreme selection for these extra columns is rule-driven from `input/shock_types.json`:
  - For `decline_pct_of_t0`: use `min(start_date:end_date)/t0 - 1`.
  - For `pct_of_t0_add_by_mnemonic`: if `pct_of_t0_add < 0` use `min`, else use `max`.
- If config keys, files, or required columns are missing, the script raises clear errors.
