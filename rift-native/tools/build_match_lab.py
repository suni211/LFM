"""Build without launching the simulation or modifying the global Python install."""
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
python=root/'build'/'match-python'/'Scripts'/'python.exe'
subprocess.run([str(python),'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed',
    '--name','RiftManager-Match','--paths',str(root/'engine'),'--paths',str(root/'server'),
    '--add-data',str(root/'engine'/'assets')+';engine/assets',
    '--distpath',str(root/'dist'),'--workpath',str(root/'build'/'match-lab'),
    '--specpath',str(root/'match_lab'),str(root/'match_lab'/'main.py')],check=True)
