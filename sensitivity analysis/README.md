# Sensitivity Analysis Script

This project runs sensitivity adjustments on quarterly scenario data using JSON-driven inputs.

## Files
- `sensitivity.py`: main script.
- `sensitivity_config.json`: runtime config (input files, sheets, dates, output paths).
- `shock_types.json`: expected `Shock Change Tested` values and adjustment mappings.
- `SFP files/`: folder for source Excel files.

## How To Run
```bash
python3 sensitivity.py
```

Or with a custom config:
```bash
python3 sensitivity.py --config your_config.json
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

## Outputs
- `output_before`: merged dataset before adjustments.
- `output_after`: dataset after adjustments.

## Notes
- Date range columns are controlled by `t0`, `start_date`, and `end_date` in `sensitivity_config.json`.
- If config keys, files, or required columns are missing, the script raises clear errors.
