import pathlib,subprocess,sys
folder=pathlib.Path(__file__).resolve().parent
subprocess.run([sys.executable,'-B',str(folder/'prepare.py'),sys.argv[1]],check=True)
raise SystemExit(subprocess.call([r'C:\Users\ALEX\.local\node-v24.21.0-win-x64\node.exe',str(folder/'launch.cjs')]))
