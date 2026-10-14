"""Local, explicitly invoked Pi experiment preparation; no application imports."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def pi_record() -> dict:
    lock=json.loads((ROOT/'config/research-sources.lock.json').read_text(encoding='utf-8'))
    return next(x for x in lock['sources'] if x['name']=='pi')


def git(source: Path, *args: str) -> str:
    return subprocess.check_output(['git','-C',str(source),*args],text=True,encoding='utf-8',timeout=25).strip()


def check_source(source: Path) -> str:
    pin=pi_record()['commit']
    if git(source,'rev-parse','HEAD')!=pin:raise ValueError('Pi source is not the reviewed commit')
    if git(source,'status','--porcelain','--untracked-files=all'):raise ValueError('Pi tracked source is modified')
    if (source/'.env').exists():raise ValueError('Refusing source dotenv')
    return pin


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fresh_runtime_path(workspace: Path, output: Path) -> Path:
    out=output.absolute()
    if not out.resolve().is_relative_to((workspace.resolve()/'runtime').resolve()):
        raise ValueError('Output must be inside the selected workspace runtime directory')
    if out.exists():raise FileExistsError('Choose a fresh experiment directory')
    return out


def isolated_env(work: Path) -> dict[str,str]:
    keep={'SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','PATH','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE'}
    env={k:v for k,v in os.environ.items() if k.upper() in keep}
    for name in ('home','home/local','home/roaming','temp','cache'):(work/name).mkdir(parents=True,exist_ok=True)
    config=work/'empty-npmrc'
    if not config.exists():config.write_text('',encoding='utf-8')
    env.update(HOME=str(work/'home'),USERPROFILE=str(work/'home'),
               LOCALAPPDATA=str(work/'home/local'),APPDATA=str(work/'home/roaming'),
               TEMP=str(work/'temp'),TMP=str(work/'temp'),
               NPM_CONFIG_USERCONFIG=str(config),NPM_CONFIG_CACHE=str(work/'cache'),
               NPM_CONFIG_IGNORE_SCRIPTS='true',NPM_CONFIG_AUDIT='false',NPM_CONFIG_FUND='false',
               PI_CODING_AGENT_DIR=str(work/'home/pi'),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
    return env
