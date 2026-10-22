"""Fixed bounded worker for cold response_store.db; no native imports."""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'packages/claw-hermes'))
import gateway_response_preopen as response

def main():
    try:
        raw=sys.stdin.buffer.read(response.cold.MAX_REQUEST+1)
        response.require(0<len(raw)<=response.cold.MAX_REQUEST,'response_preopen_request_size')
        report=response.inspect_cold(response.cold._json(raw));code=0
    except response.ResponsePreopenRejected as exc:
        report={'state':'REFUSED','reason':str(exc)};code=2
    except Exception:
        report={'state':'REFUSED','reason':'response_preopen_worker_failed'};code=2
    raw=json.dumps(report,separators=(',',':')).encode()
    if len(raw)>response.cold.MAX_REPLY:
        raw=b'{"state":"REFUSED","reason":"response_preopen_worker_output"}';code=2
    sys.stdout.buffer.write(raw);sys.stdout.buffer.flush();return code
if __name__=='__main__':raise SystemExit(main())
