"""Read-only independent review of an explicit Linux wheel download set.
Uses packaging to evaluate declared target tags/markers, never extracts, installs
or imports wheel code. Integrity is not publisher trust or runtime acceptance.
"""
from pathlib import Path,PurePosixPath
from email.parser import BytesParser
import argparse,base64,csv,hashlib,io,json,stat,struct,zipfile
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.tags import cpython_tags,compatible_tags,parse_tag
from packaging.utils import parse_wheel_filename,canonicalize_name
from packaging.version import Version
import packaging

TARGET={'implementation_name':'cpython','implementation_version':'3.12.3',
        'os_name':'posix','platform_machine':'x86_64','platform_release':'6.6.87.2-microsoft-standard-WSL2',
        'platform_system':'Linux','platform_version':'unqueried-not-used',
        'python_full_version':'3.12.3','platform_python_implementation':'CPython',
        'python_version':'3.12','sys_platform':'linux','extra':''}
PLATFORMS=['manylinux_2_17_x86_64','manylinux2014_x86_64','manylinux_2_28_x86_64',
           'manylinux_2_31_x86_64','manylinux_2_34_x86_64','manylinux_2_35_x86_64']

def need(ok,reason):
    if not ok:raise ValueError(reason)

def inspect_wheel(path,expected):
    need(path.name==expected['name'] and path.suffix=='.whl' and not path.is_symlink(),'wheel_identity')
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    need(len(raw)==expected['bytes'] and digest==expected['sha256'],'wheel_hash_or_size')
    name,version,build,tags=parse_wheel_filename(path.name)
    supported=set(cpython_tags((3,12),abis=['cp312'],platforms=PLATFORMS))
    supported.update(compatible_tags((3,12),interpreter='cp312',platforms=PLATFORMS))
    need(bool(tags & supported),'unsupported_target_tags')
    members={};elf=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos=z.infolist();need(len(infos)<=10000,'entry_count_bound')
        need(sum(i.file_size for i in infos)<=200_000_000,'expanded_byte_bound')
        seen=set()
        for info in infos:
            p=PurePosixPath(info.filename)
            need(info.filename not in seen,'duplicate_zip_member');seen.add(info.filename)
            need(all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts
                     and chr(92) not in n and ':' not in n and chr(0) not in n
                     for n in (info.filename,info.orig_filename)), 'unsafe_member_path')
            need(not stat.S_ISLNK(info.external_attr>>16),'symlink_member')
            need(not info.flag_bits&1,'encrypted_member')
            if info.is_dir():continue
            need(not info.filename.lower().endswith(('.pth','.pyd','.dll','.exe')),'startup_or_windows_binary')
            b=z.read(info);members[info.filename]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
            if p.suffix=='.so':
                need(len(b)>=20 and b[:6]==b'\x7fELF\x02\x01','not_elf64_little_endian')
                need(struct.unpack_from('<H',b,18)[0]==62,'not_x86_64_elf')
                elf.append(info.filename)
        metadata=[n for n in members if n.endswith('.dist-info/METADATA')]
        need(len(metadata)==1,'one_distribution_required');prefix=metadata[0].rsplit('/',1)[0]
        wheel=prefix+'/WHEEL';record=prefix+'/RECORD';need(wheel in members and record in members,'wheel_metadata_missing')
        m=BytesParser().parsebytes(z.read(metadata[0]));wm=BytesParser().parsebytes(z.read(wheel))
        need(canonicalize_name(m['Name'])==name and Version(m['Version'])==version,'filename_metadata_mismatch')
        need(Version('3.12.3') in SpecifierSet(m.get('Requires-Python','')),'python_requirement')
        declared=set()
        for tag in wm.get_all('Tag',[]):declared.update(parse_tag(tag))
        need(tags==declared,'wheel_filename_tag_mismatch')
        rows=list(csv.reader(io.StringIO(z.read(record).decode('utf-8'))));listed={}
        for row in rows:
            need(len(row)==3 and row[0] not in listed,'record_shape_or_duplicate');listed[row[0]]=row
        need(set(listed)==set(members),'record_membership_mismatch')
        for member,v in members.items():
            _,hashvalue,size=listed[member]
            if member==record:need(hashvalue=='' and size=='','record_self_fields');continue
            need(hashvalue.startswith('sha256=') and size.isdecimal(),'record_digest_required')
            digest=base64.urlsafe_b64decode(hashvalue.split('=',1)[1]+'===').hex()
            need(digest==v['sha256'] and int(size)==v['bytes'],'record_hash_or_size_mismatch')
        return {'name':name,'version':str(version),'filename':path.name,'sha256':expected['sha256'],
                'metadataSha256':members[metadata[0]]['sha256'],'tags':sorted(str(t) for t in tags),
                'requiresPython':m.get('Requires-Python'),'requires':m.get_all('Requires-Dist',[]),
                'memberCount':len(members),'expandedBytes':sum(v['bytes'] for v in members.values()),
                'elfMembers':elf,'allRecordHashesVerified':True}

def inspect_set(root,download):
    need(download['exitCode']==0 and download['installationPerformed'] is False,'download_not_verified')
    need(len({x['name'] for x in download['files']})==len(download['files']),'download_duplicates')
    need(set(p.name for p in root.iterdir() if p.is_file())=={x['name'] for x in download['files']},'wheel_set_changed')
    wheels=[inspect_wheel(root/x['name'],x) for x in download['files']]
    versions={w['name']:Version(w['version']) for w in wheels};need(len(versions)==len(wheels),'distribution_collision')
    need('pywin32' not in versions,'windows_package_selected')
    edges=[];inactive=[]
    for wheel in wheels:
        for text in wheel['requires']:
            r=Requirement(text);need(r.url is None,'unlocked_direct_dependency')
            # Version/release markers cannot be quietly borrowed from the host.
            need('platform_version' not in str(r.marker or ''),'unqueried_target_marker')
            if r.marker is not None and not r.marker.evaluate(TARGET):
                inactive.append({'from':wheel['name'],'requirement':text});continue
            need(not r.extras,'active_extra_resolution_unimplemented')
            name=canonicalize_name(r.name)
            need(name in versions and versions[name] in r.specifier,'unresolved_target_dependency:'+text)
            edges.append({'from':wheel['name'],'to':name,'version':str(versions[name]),'requirement':text})
    return {'result':'PASS_WHEEL_INTEGRITY_AND_DECLARED_LINUX_CLOSURE','target':TARGET,'targetPlatforms':PLATFORMS,
            'wheelCount':len(wheels),'wheels':wheels,'dependencyEdges':edges,'excludedMarkerEdges':inactive,
            'recordMemberCount':sum(w['memberCount'] for w in wheels),'elfFileCount':sum(len(w['elfMembers']) for w in wheels),
            'packagingVersion':packaging.__version__,'allHashesVerified':True,'wheelCodeExecuted':False,
            'wheelExtractionPerformed':False,'installationPerformed':False,'publisherTrustOrVulnerabilityAudited':False,
            'dynamicAbiOrRuntimeImportsTested':False,'linuxLifecycleOrConfinementAccepted':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--wheels',type=Path,required=True);p.add_argument('--download',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raw=a.download.read_bytes();r=inspect_set(a.wheels,json.loads(raw));r['downloadManifestSha256']=hashlib.sha256(raw).hexdigest()
    r['qaSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with a.output.open('x',encoding='utf-8',newline='\n') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('wheels','dependencyEdges','excludedMarkerEdges')}),flush=True)
if __name__=='__main__':main()
