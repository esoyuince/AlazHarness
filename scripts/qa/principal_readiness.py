"""Read-only Linux host-principal readiness check. Never provision identities."""
import json
import os
from pathlib import Path
import shutil
import sys

def inspect():
    if sys.platform != 'linux':
        return {'status':'UNSUPPORTED','reason':'linux_required'}
    uid=os.getuid()
    userns=os.readlink('/proc/self/ns/user')
    groups=os.getgroups()
    tools={name:bool(shutil.which(name)) for name in ('unshare','setpriv','runuser')}
    return {'status':'NOT_READY','uid':uid,'euid':os.geteuid(),
            'gid':os.getgid(),'egid':os.getegid(),
            'supplementalGroupsPresent':bool(groups),
            'userNamespace':userns,'tools':tools,
            'separateBrokerUidVerified':False,
            'brokerStorageIsolated':False,
            'reason':'two_distinct_trusted_host_principals_not_provisioned_or_tested'}

if __name__ == '__main__':
    print(json.dumps(inspect(),sort_keys=True))
