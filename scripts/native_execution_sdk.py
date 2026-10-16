"""Native auxiliary factory + real SDK through actual native budget HTTP route."""
import json,sys
from pathlib import Path
source,params,result=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source))
from agent.auxiliary_client import _create_openai_client
c=json.loads(params.read_text());client=_create_openai_client(api_key=c['providerToken'],base_url=c['providerUrl'],max_retries=1,timeout=10)
try:
    try:
        response=client.chat.completions.create(model='alaz-scripted',messages=[{'role':'user','content':'SDK retry fixture'}],max_tokens=20)
        d={'success':True,'exception':None}
    except Exception as exc:
        body=getattr(exc,'body',None)
        if isinstance(body,dict) and isinstance(body.get('error'),dict):body=body['error']
        code=body.get('code') if isinstance(body,dict) else None
        d={'success':False,'exception':type(exc).__name__,'error_code':code if code=='provider_attempt_limit' else None}
finally:client.close()
d['nonce']=c['nonce'];d['sdk_invocations']=1
result.write_text(json.dumps(d),encoding='utf-8')
