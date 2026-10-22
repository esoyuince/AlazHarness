"""Fixed bounded stdin/stdout worker for gateway_store_preopen; no native constructors."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'packages/claw-hermes'))
import gateway_store_preopen as preopen

def main():
    try:
        raw=sys.stdin.buffer.read(preopen.MAX_REQUEST+1)
        preopen.require(0<len(raw)<=preopen.MAX_REQUEST,'preopen_request_size')
        report=preopen.inspect_cold(preopen._json(raw))
        status=0
    except preopen.PreopenRejected as exc:
        report={'state':'REFUSED','reason':str(exc)};status=2
    except Exception:
        report={'state':'REFUSED','reason':'preopen_worker_failed'};status=2
    raw=json.dumps(report,separators=(',',':')).encode()
    if len(raw)>preopen.MAX_REPLY:
        raw=b'{"state":"REFUSED","reason":"preopen_worker_output"}';status=2
    sys.stdout.buffer.write(raw);sys.stdout.buffer.flush()
    return status
if __name__=='__main__':raise SystemExit(main())
