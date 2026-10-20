import os, subprocess, sys
from pathlib import Path
directory=Path(__file__).resolve().parent
subprocess.run([sys.executable,'-B',str(directory/'prepare.py'),sys.argv[1]],check=True)
raise SystemExit(subprocess.call(['C:/Users/ALEX/.local/node-v24.21.0-win-x64/node.exe',str(directory/'launch.cjs')]))
