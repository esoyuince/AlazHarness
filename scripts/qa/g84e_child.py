"""Fixed benign root-to-Gateway projection child in the approved P71C lab."""
import json
import os
from pathlib import Path
import sys
INSTALL=Path('/opt/alazharness-broker/802fade')
QA=Path('/opt/alazharness-gateway-g84e')
sys.path[:0]=[str(QA),str(INSTALL/'packages/claw-hermes')]
import gateway_projection as gp

def main():
    if os.getuid()!=0 or os.environ.get('WSL_DISTRO_NAME')!='AlazHarness-D3B-P71C':
        raise RuntimeError('lab_root_only')
    if Path('/etc/alaz-p71c-lab-id').read_text().strip()!='AlazHarness-D3B-P71C':
        raise RuntimeError('lab_marker')
    line=sys.stdin.buffer.readline(32769)
    if len(line)>32768:raise RuntimeError('input_bound')
    data=json.loads(line)
    receipt=gp.enter(data['ipc'],data['filesystem'])
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':'/',
         'G84E_ENTRY_RECEIPT':json.dumps(receipt,separators=(',',':'))}
    os.execve('/usr/bin/python3.12',['/usr/bin/python3.12','-I','-B',str(QA/'g84e_target.py')],env)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'phase':'REFUSED','type':type(exc).__name__,'reason':str(exc)[:250]}),file=sys.stderr)
        raise SystemExit(2)
