"""Exact pre-R147/R149 bytes for historical receipts only.

An expected digest must match a named immutable prior Git generation, baseline,
and saved bytes. Unknown names/digests are never redirected; current code does
not inherit old native/kernel acceptance. No product function is patched.
"""
import hashlib,json
from pathlib import Path
BASE='31e0c54c530151bd25ebc43f617a853bb1736412'
PINS={'packages/claw-hermes/credential_guard.py': '5bd669d0c5b9a3bb995cc933ab58a8a185f31e4bbec59d08683c2edb776dbe2b', 'packages/claw-hermes/gateway_retained_launch.py': 'f326c2f420eb8355b09d8bfb26ad8182be544bae71818c5a2cca1f4e40736c00', 'packages/claw-hermes/gateway_state_projection.py': 'ddcca9ca9176fd26810fd90a50de207aef7896693106efd7798cee735604065c', 'tests/historical_owner_b129d6.py': '37d8765ed3dca45ce03fd665e833963baf726dd65bd1f21040ddab0224f7b16f', 'tests/test_integrated_profile_metadata_q104e.py': '83f941027078e06fc878287d94f3509cfaa114197a77ccc501993283a011d5b1', 'tests/test_native_profile_admission_receipt.py': 'f786dfbcbbfffd45b7b45a87237b59a641f5fbc657cfa72d79c17ff02b4e860d', 'tests/test_projected_launch_l145a8.py': '6f213bcaac3d11fb7da82a804397a18ce7381b32dd2247fbcf0566b878c1b83a', 'tests/test_projected_launch_receipt_l145a8.py': '08f7b75e41f2bad59c48ce0563afb22e66996a0d16697abfc2ad849f43f775e4', 'tests/test_retained_projection_receipt_p142c6.py': '2d54296667b1370920a6af83e22f0b6e38c4b47a8bf95b75621a0983f9540429'}

def saved_generation_path(root,name,expected):
    if name not in PINS or expected!=PINS[name]:return None
    folder=root/'evidence/self-identity-r149a9'
    record=json.loads((folder/'historical-source-bindings.json').read_text(encoding='utf-8'))
    baseline=json.loads((folder/'baseline.json').read_text(encoding='utf-8'))
    assert record['base']==baseline['base']==BASE,'historical immutable base changed'
    assert set(record['sources'])==set(PINS),'historical named source set changed'
    row=record['sources'][name]
    path='evidence/self-identity-r149a9/historical-src/'+name.replace('/','__')+'.txt'
    assert row=={'sha256':expected,'path':path},'historical source mapping changed'
    assert baseline['sources'][name]==expected,'historical baseline digest changed'
    target=root/path
    assert hashlib.sha256(target.read_bytes()).hexdigest()==expected,'historical source bytes changed'
    return target

def saved_generation_hash(root,name,expected):
    path=saved_generation_path(root,name,expected)
    return None if path is None else hashlib.sha256(path.read_bytes()).hexdigest()

def historical_source_path(root,name,expected):
    path=saved_generation_path(root,name,expected)
    if path is None:
        relative=Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts,'invalid source name'
        path=root/relative
        assert path.resolve().is_relative_to(root.resolve()),'source path escapes root'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,'unknown source generation'
    return path
