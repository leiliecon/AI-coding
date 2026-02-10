from path2shock_calculation import run_path2shock
from path2shock_export import export_path2shock_table


def run_all():
    run_path2shock()
    return export_path2shock_table()


if __name__ == "__main__":
    output_file = run_all()
    print(f"Completed. Export file: {output_file}")
