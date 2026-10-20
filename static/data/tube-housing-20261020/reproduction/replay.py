"""Replay a recorded baseline using an explicit executable and retained input mesh."""
from pathlib import Path
import argparse,json,subprocess,shlex
p=argparse.ArgumentParser();p.add_argument('--case',choices=['tube','tube-disc'],required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
base=Path(__file__).resolve().parents[1];cmd=json.loads((base/a.case/'COMMAND.json').read_text());cmd[0]=str(a.binary.resolve())
for k,v in [('--data',str(a.mesh.resolve())+'/'),('--out',str(a.out.resolve())+'/')]:cmd[cmd.index(k)+1]=v
if a.out.exists():raise SystemExit('Refusing to overwrite '+str(a.out))
print(shlex.join(cmd))
if a.run:
 if not a.binary.is_file() or not a.mesh.is_dir():raise SystemExit('Executable or input mesh missing')
 a.out.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run(cmd,check=True,cwd=a.out.parent)
