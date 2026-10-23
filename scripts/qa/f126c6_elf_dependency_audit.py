"""Read ELF metadata only; never load binaries or change projected permissions.
This static closure report is NOT dynamic-loader, hostile-code or CVE acceptance.
"""
from pathlib import Path
import hashlib,json,os,stat,struct,sys
ROOTS=(Path('/usr/lib/x86_64-linux-gnu'),Path('/usr/lib64'))
MAX_ELF=32*1024*1024

def need(ok,reason):
    if not ok:raise ValueError(reason)

def parse_elf(raw):
    need(64<=len(raw)<=MAX_ELF,'elf_size')
    h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    ident,kind,machine=h[:3]
    need(ident[:7]==b'\x7fELF\x02\x01\x01' and machine==62 and kind in (2,3),'elf_format_or_architecture')
    off,stride,count,name_index=h[6],h[11],h[12],h[13]
    need(stride==64 and 0<count<=8192 and name_index<count and 64<=off<=len(raw) and off+count*stride<=len(raw),'elf_section_table')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+n*stride) for n in range(count)]
    def content(s):
        start,size=s[4],s[5];need(start<=len(raw) and size<=len(raw)-start,'elf_section_bounds')
        return raw[start:start+size]
    def string(buf,index):
        need(0<=index<len(buf),'elf_string_index');end=buf.find(b'\0',index,min(len(buf),index+4097))
        need(end>=index,'elf_string_termination');return buf[index:end].decode('ascii')
    strings=content(sections[name_index]);by_name={}
    for s in sections:
        name=string(strings,s[0])
        if name:need(name not in by_name,'elf_duplicate_section');by_name[name]=s
    need('.dynamic' in by_name and '.dynstr' in by_name,'elf_dynamic_required')
    dynstr=content(by_name['.dynstr']);dynamic=content(by_name['.dynamic'])
    need(len(dynamic)%16==0 and len(dynamic)<=65536,'elf_dynamic_shape')
    needed,paths,soname,terminal=[],[],None,False
    for i in range(0,len(dynamic),16):
        tag,value=struct.unpack_from('<qQ',dynamic,i)
        if tag==0:terminal=True;break
        if tag in (1,14,15,29):
            text=string(dynstr,value)
            if tag==1:
                need(text and '/' not in text and chr(92) not in text and text not in ('.','..'),'elf_needed_path');needed.append(text)
            elif tag==14:need(soname is None,'elf_duplicate_soname');soname=text
            else:paths.append({'kind':'RPATH' if tag==15 else 'RUNPATH','value':text})
    need(terminal and len(needed)==len(set(needed)),'elf_dynamic_termination_or_duplicate')
    requirements={}
    if '.gnu.version_r' in by_name:
        data=content(by_name['.gnu.version_r']);cursor=0;seen=set()
        while True:
            need(cursor not in seen and len(seen)<256 and cursor+16<=len(data),'elf_verneed_bounds');seen.add(cursor)
            ver,num,filename,aux,nxt=struct.unpack_from('<HHIII',data,cursor)
            need(ver==1 and 0<num<=256 and aux>=16,'elf_verneed_header')
            library=string(dynstr,filename);names=[];pos=cursor+aux;visited=set()
            for index in range(num):
                need(pos not in visited and pos+16<=len(data),'elf_vernaux_bounds');visited.add(pos)
                _,_,_,label,jump=struct.unpack_from('<IHHII',data,pos);names.append(string(dynstr,label))
                if index+1<num:need(jump>=16,'elf_vernaux_chain');pos+=jump
            need(library not in requirements,'elf_duplicate_verneed');requirements[library]=sorted(names)
            if nxt==0:break
            need(nxt>=16,'elf_verneed_chain');cursor+=nxt
    exports=[]
    if '.gnu.version_d' in by_name:
        data=content(by_name['.gnu.version_d']);cursor=0;seen=set()
        while True:
            need(cursor not in seen and len(seen)<512 and cursor+20<=len(data),'elf_verdef_bounds');seen.add(cursor)
            ver,_,_,num,_,aux,nxt=struct.unpack_from('<HHHHIII',data,cursor)
            need(ver==1 and num>0 and aux>=20 and cursor+aux+8<=len(data),'elf_verdef_header')
            label,_=struct.unpack_from('<II',data,cursor+aux);exports.append(string(dynstr,label))
            if nxt==0:break
            need(nxt>=20,'elf_verdef_chain');cursor+=nxt
    return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'needed':needed,'soname':soname,'searchOverrides':paths,'requiredVersions':requirements,'providedVersions':sorted(set(exports)),'machine':'ELF64_LSB_x86_64'}

def audit_system(candidates):
    need(type(candidates) is dict and 1<=len(candidates)<=64,'candidate_count')
    resolved,missing,overrides,mismatched,edges={},[],[],[],[];queue=[]
    for origin,candidate in candidates.items():
        need(candidate['machine']=='ELF64_LSB_x86_64','candidate_architecture')
        if candidate['searchOverrides']:overrides.append({'origin':origin,'paths':candidate['searchOverrides']})
        for name in candidate['needed']:queue.append((origin,name,candidate['requiredVersions'].get(name,[])))
    while queue:
        need(len(edges)<=1024 and len(resolved)<=128,'system_graph_bound');origin,name,required=queue.pop(0)
        need(name and '/' not in name and chr(92) not in name and name not in ('.','..'),'system_needed_path')
        if name not in resolved:
            available={(root/name).resolve(strict=True) for root in ROOTS if (root/name).is_file()}
            if len(available)!=1:missing.append({'origin':origin,'name':name,'matchingPaths':sorted(map(str,available))});continue
            path=next(iter(available));need(any(path.is_relative_to(root) for root in ROOTS),'library_outside_projected_roots')
            info=path.stat();need(stat.S_ISREG(info.st_mode) and info.st_uid==0 and not stat.S_IMODE(info.st_mode)&0o022 and 64<=info.st_size<=MAX_ELF,'library_untrusted_metadata')
            with path.open('rb') as stream:first=os.fstat(stream.fileno());raw=stream.read(MAX_ELF+1);last=os.fstat(stream.fileno())
            sig=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
            need(sig(first)==sig(last)==sig(path.stat()),'library_changed_during_read')
            parsed=parse_elf(raw);resolved[name]=parsed|{'path':str(path),'device':first.st_dev,'inode':first.st_ino}
            if parsed['searchOverrides']:overrides.append({'origin':str(path),'paths':parsed['searchOverrides']})
            for dependency in parsed['needed']:queue.append((str(path),dependency,parsed['requiredVersions'].get(dependency,[])))
        absent=sorted(set(required)-set(resolved[name]['providedVersions']))
        if absent:mismatched.append({'origin':origin,'name':name,'missingVersions':absent})
        edges.append({'origin':origin,'name':name,'resolvedPath':resolved[name]['path'],'requiredVersions':required})
    return {'result':'PASS_STATIC_ELF_CLOSURE_ONLY' if not (missing or overrides or mismatched) else 'REFUSED_STATIC_ELF_CLOSURE','binaryCandidateCount':len(candidates),'systemLibraries':resolved,'dependencyEdges':edges,'missingLibraries':missing,'searchOverridesRequireReview':overrides,'missingVersions':mismatched,'allowedSystemRoots':list(map(str,ROOTS)),'binaryCodeLoadedOrExecuted':False,'projectedPolicyModified':False,'dynamicLoaderOrFullAbiVerified':False,'vulnerabilityAuditPerformed':False,'fullConfinementAccepted':False}

def main():
    need(os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C' and Path('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C','wrong_lab')
    need(os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3 and not Path('/mnt/c').exists(),'wrong_actor')
    raw=sys.stdin.buffer.read(1_000_001);need(len(raw)<=1_000_000,'input_bound');data=json.loads(raw);result=audit_system(data['candidates'])
    result.update(inputSha256=hashlib.sha256(raw).hexdigest(),qaSha256=data['qaSha256'],uid=list(os.getresuid()),gid=list(os.getresgid()),rootUsed=False,candidateDigests={n:v['sha256'] for n,v in data['candidates'].items()})
    print(json.dumps(result),flush=True);return 0 if result['result'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
