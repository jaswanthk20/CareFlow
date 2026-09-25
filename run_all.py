"""Rebuild CareFlow locally. Raw sources are read, never edited."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
steps = ['EDA/run_eda.py', 'EDA/verify_eda.py', 'EDA/audit_careflow.py', 'EDA/verify_audit.py',
         'EDA/patient_flow.py', 'Forecasting/run_forecasting.py', 'Simulation/run_simulation.py',
         'Tableau/prepare_data.py', 'Tableau/render_mockups.py', 'Documentation/build_documentation.py',
         'validate_project.py']
for step in steps:
    print(f'Running {step}', flush=True)
    subprocess.run([sys.executable, str(root/step)], cwd=root, check=True)
print('CareFlow rebuild and validation completed. No data was published.')
