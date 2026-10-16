// HYB-005D independent Windows feasibility probe. NOT a general agent launcher.
// Compiled only by the explicitly invoked local QA script; no code runs in normal CI.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;

public static class WindowsAppContainerProbe {
    const uint TOKEN_QUERY=8, CREATE_SUSPENDED=4, EXTENDED=0x80000, UNICODE_ENV=0x400, NO_WINDOW=0x8000000;
    const uint WAIT_OBJECT_0=0, WAIT_TIMEOUT=258;
    [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] struct STARTUPINFO {
        public int cb; public string reserved, desktop, title; public uint x,y,cx,cy,charsX,charsY,fill,flags;
        public ushort show,reservedBytes; public IntPtr reservedPointer,hIn,hOut,hErr;
    }
    [StructLayout(LayoutKind.Sequential)] struct STARTUPINFOEX { public STARTUPINFO info; public IntPtr attributes; }
    [StructLayout(LayoutKind.Sequential)] struct PROCESS_INFORMATION {public IntPtr process,thread;public uint pid,tid;}
    [StructLayout(LayoutKind.Sequential)] struct SECURITY_CAPABILITIES {public IntPtr sid,capabilities;public uint count,reserved;}
    [StructLayout(LayoutKind.Sequential)] struct JOB_BASIC {
        public long processTime,jobTime;public uint flags;public UIntPtr minWorkingSet,maxWorkingSet;
        public uint activeProcesses;public UIntPtr affinity;public uint priority,scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct IO_COUNTERS {public ulong readOperations,writeOperations,otherOperations,readBytes,writeBytes,otherBytes;}
    [StructLayout(LayoutKind.Sequential)] struct JOB_EXTENDED {
        public JOB_BASIC basic;public IO_COUNTERS io;public UIntPtr processMemory,jobMemory,peakProcessMemory,peakJobMemory;
    }
    [DllImport("userenv.dll",CharSet=CharSet.Unicode)] static extern int CreateAppContainerProfile(string name,string display,string description,IntPtr capabilities,uint count,out IntPtr sid);
    [DllImport("userenv.dll",CharSet=CharSet.Unicode)] static extern int DeleteAppContainerProfile(string name);
    [DllImport("advapi32.dll")] static extern IntPtr FreeSid(IntPtr sid);
    [DllImport("userenv.dll",CharSet=CharSet.Unicode)] static extern int GetAppContainerFolderPath(string sid,out IntPtr path);
    [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] static extern bool CreateProcessW(string application,StringBuilder command,IntPtr processAttributes,IntPtr threadAttributes,bool inherit,uint flags,IntPtr environment,string cwd,ref STARTUPINFOEX startup,out PROCESS_INFORMATION process);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool InitializeProcThreadAttributeList(IntPtr list,int count,int flags,ref IntPtr size);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool UpdateProcThreadAttribute(IntPtr list,uint flags,IntPtr attribute,IntPtr value,IntPtr size,IntPtr previous,IntPtr returned);
    [DllImport("kernel32.dll")] static extern void DeleteProcThreadAttributeList(IntPtr list);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint ResumeThread(IntPtr handle);
    [DllImport("kernel32.dll",SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle,uint ms);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr handle,out uint code);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateProcess(IntPtr handle,uint code);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr security,string name);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job,int kind,ref JOB_EXTENDED value,uint size);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool IsProcessInJob(IntPtr process,IntPtr job,out bool member);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool TerminateJobObject(IntPtr job,uint exitCode);
    [DllImport("kernel32.dll")] static extern uint SetErrorMode(uint mode);
    [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint access,bool inherit,uint pid);
    [DllImport("advapi32.dll",SetLastError=true)] static extern bool OpenProcessToken(IntPtr process,uint access,out IntPtr token);
    [DllImport("advapi32.dll",SetLastError=true)] static extern bool GetTokenInformation(IntPtr token,int kind,IntPtr buffer,int length,out int needed);

    static void Require(bool condition,string message) {if(!condition)throw new InvalidOperationException(message);}
    static void Win(bool condition,string operation) {if(!condition)throw new Win32Exception(Marshal.GetLastWin32Error(),operation);}
    static string Quote(string value) {Require(value.IndexOfAny(new char[]{'"','\r','\n','\0'})<0 && !value.EndsWith("\\"),"unsafe_argument");return "\""+value+"\"";}
    static JavaScriptSerializer Json() {return new JavaScriptSerializer(){MaxJsonLength=65536};}
    static Dictionary<string,object> Read(string path) {return Json().Deserialize<Dictionary<string,object>>(File.ReadAllText(path,Encoding.UTF8));}
    static void Write(string path,Dictionary<string,object> value) {using(var f=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None))using(var s=new StreamWriter(f,new UTF8Encoding(false)))s.Write(Json().Serialize(value));}

    static IntPtr TokenBuffer(IntPtr token,int kind) {
        int needed; GetTokenInformation(token,kind,IntPtr.Zero,0,out needed);
        Require(needed>0 && needed<65536,"unbounded_token");IntPtr p=Marshal.AllocHGlobal(needed);
        try {Win(GetTokenInformation(token,kind,p,needed,out needed),"GetTokenInformation");return p;}
        catch {Marshal.FreeHGlobal(p);throw;}
    }
    static Dictionary<string,object> Identity(IntPtr process) {
        IntPtr token;Win(OpenProcessToken(process,TOKEN_QUERY,out token),"OpenProcessToken");
        var result=new Dictionary<string,object>();
        try {
            foreach(int kind in new int[]{29,30,31,25}) {
                IntPtr p=TokenBuffer(token,kind);
                try {
                    if(kind==29)result["isAppContainer"]=Marshal.ReadInt32(p)!=0;
                    if(kind==30)result["capabilityCount"]=Marshal.ReadInt32(p);
                    if(kind==31) {IntPtr sid=Marshal.ReadIntPtr(p);result["appContainerSid"]=sid==IntPtr.Zero?null:new SecurityIdentifier(sid).Value;}
                    if(kind==25)result["integritySid"]=new SecurityIdentifier(Marshal.ReadIntPtr(p)).Value;
                } finally {Marshal.FreeHGlobal(p);}
            }
        } finally {CloseHandle(token);}
        return result;
    }
    static void GrantRead(string directory,SecurityIdentifier sid) {
        var acl=Directory.GetAccessControl(directory);
        acl.AddAccessRule(new FileSystemAccessRule(sid,FileSystemRights.ReadAndExecute,
            InheritanceFlags.ContainerInherit|InheritanceFlags.ObjectInherit,PropagationFlags.None,AccessControlType.Allow));
        Directory.SetAccessControl(directory,acl);
    }

    static Dictionary<string,object> Start(string exe,string root,int p4,int p6,uint parent,IntPtr sid,string mode,bool hung,string outputRoot) {
        IntPtr list=IntPtr.Zero,capPointer=IntPtr.Zero,env=IntPtr.Zero,job=IntPtr.Zero;
        bool listReady=false,started=false,exited=false;PROCESS_INFORMATION pi=new PROCESS_INFORMATION();
        var observed=new Dictionary<string,object>();
        try {
            var si=new STARTUPINFOEX();si.info.cb=Marshal.SizeOf(typeof(STARTUPINFOEX));
            uint flags=CREATE_SUSPENDED|NO_WINDOW;
            if(sid!=IntPtr.Zero) {
                IntPtr length=IntPtr.Zero;InitializeProcThreadAttributeList(IntPtr.Zero,1,0,ref length);
                Require(length.ToInt64()>0 && length.ToInt64()<65536,"attribute_size");list=Marshal.AllocHGlobal(length);
                Win(InitializeProcThreadAttributeList(list,1,0,ref length),"InitializeAttributes");listReady=true;
                var caps=new SECURITY_CAPABILITIES(){sid=sid,capabilities=IntPtr.Zero,count=0,reserved=0};
                capPointer=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(SECURITY_CAPABILITIES)));Marshal.StructureToPtr(caps,capPointer,false);
                Win(UpdateProcThreadAttribute(list,0,(IntPtr)0x20009,capPointer,(IntPtr)Marshal.SizeOf(typeof(SECURITY_CAPABILITIES)),IntPtr.Zero,IntPtr.Zero),"SetSecurityCapabilities");
                si.attributes=list;flags|=EXTENDED|UNICODE_ENV;
                var variables=new SortedDictionary<string,string>(StringComparer.OrdinalIgnoreCase) {
                    {"SystemRoot",Environment.GetEnvironmentVariable("SystemRoot")},{"WINDIR",Environment.GetEnvironmentVariable("WINDIR")},
                    {"TEMP",outputRoot},{"TMP",outputRoot},{"LOCALAPPDATA",Path.GetDirectoryName(outputRoot)}
                };
                var block=new StringBuilder();foreach(var pair in variables)block.Append(pair.Key).Append('=').Append(pair.Value).Append('\0');block.Append('\0');
                env=Marshal.StringToHGlobalUni(block.ToString());
            } else si.info.cb=Marshal.SizeOf(typeof(STARTUPINFO));
            string cmd=Quote(exe)+" --child "+Quote(root)+" "+p4+" "+p6+" "+parent+" "+mode+(hung?" hang":" run")+" "+Quote(outputRoot);
            Win(CreateProcessW(exe,new StringBuilder(cmd),IntPtr.Zero,IntPtr.Zero,false,flags,env,Path.Combine(root,"app"),ref si,out pi),"CreateProcess");started=true;
            var identity=Identity(pi.process);observed["identityBeforeResume"]=identity;observed["pid"]=pi.pid;observed["mode"]=mode;
            if(sid!=IntPtr.Zero) {
                Require((bool)identity["isAppContainer"] && (int)identity["capabilityCount"]==0 && (string)identity["appContainerSid"]==new SecurityIdentifier(sid).Value,"wrong_isolation_token");
                Require((string)identity["integritySid"]=="S-1-16-4096","not_low_integrity");
            } else Require(!(bool)identity["isAppContainer"],"invalid_positive_control");
            job=CreateJobObject(IntPtr.Zero,null);Win(job!=IntPtr.Zero,"CreateJob");
            var limits=new JOB_EXTENDED();limits.basic.flags=0x2000|0x8;limits.basic.activeProcesses=1;
            Win(SetInformationJobObject(job,9,ref limits,(uint)Marshal.SizeOf(typeof(JOB_EXTENDED))),"SetJobLimits");
            Win(AssignProcessToJobObject(job,pi.process),"AssignJob");bool member;Win(IsProcessInJob(pi.process,job,out member),"QueryJob");Require(member,"not_in_job");
            observed["jobAssignedBeforeResume"]=true;observed["handlesInherited"]=false;
            Win(ResumeThread(pi.thread)!=0xffffffff,"ResumeThread");
            uint waited=WaitForSingleObject(pi.process,hung?700U:25000U);bool timedOut=waited==WAIT_TIMEOUT;
            if(timedOut) {Win(TerminateJobObject(job,91),"TerminateJob");waited=WaitForSingleObject(pi.process,5000);}
            Require(waited==WAIT_OBJECT_0,"unconfirmed_process_exit");exited=true;
            uint exitCode;Win(GetExitCodeProcess(pi.process,out exitCode),"ExitCode");observed["exitCode"]=exitCode;observed["timedOut"]=timedOut;observed["processReaped"]=true;
            if(hung)Require(timedOut && exitCode==91,"timeout_not_enforced");
            else {Require(!timedOut && exitCode==0,"child_failed");observed["child"]=Read(Path.Combine(outputRoot,mode+".json"));
                if(outputRoot!=Path.Combine(root,"writable"))File.Copy(Path.Combine(outputRoot,mode+".json"),Path.Combine(root,"writable",mode+".json"),false);}
            return observed;
        } finally {
            if(started&&!exited) {if(job!=IntPtr.Zero)TerminateJobObject(job,92);TerminateProcess(pi.process,92);WaitForSingleObject(pi.process,5000);}
            if(pi.thread!=IntPtr.Zero)CloseHandle(pi.thread);if(pi.process!=IntPtr.Zero)CloseHandle(pi.process);
            if(job!=IntPtr.Zero)CloseHandle(job);if(env!=IntPtr.Zero)Marshal.FreeHGlobal(env);
            if(listReady)DeleteProcThreadAttributeList(list);if(list!=IntPtr.Zero)Marshal.FreeHGlobal(list);if(capPointer!=IntPtr.Zero)Marshal.FreeHGlobal(capPointer);
        }
    }
    static int Connect(IPAddress address,int port) {
        using(var socket=new Socket(address.AddressFamily,SocketType.Stream,ProtocolType.Tcp)) {
            try {
                var result=socket.BeginConnect(new IPEndPoint(address,port),null,null);
                try {if(!result.AsyncWaitHandle.WaitOne(1500))return 10060;socket.EndConnect(result);}
                finally {result.AsyncWaitHandle.Close();}
                socket.Send(new byte[]{0x41});return 0;
            } catch(SocketException e) {return e.ErrorCode;}
        }
    }
    static int FileAction(Action work) {try {work();return 0;}catch(UnauthorizedAccessException){return 5;}catch(IOException e){return e.HResult&0xffff;}}
    static int Child(string[] args) {
        string root=args[1],mode=args[5],outputRoot=args[7];if(args[6]=="hang") {Thread.Sleep(60000);return 90;}
        int p4=int.Parse(args[2]),p6=int.Parse(args[3]);uint parent=uint.Parse(args[4]);
        var r=Identity(Process.GetCurrentProcess().Handle);
        r["parentSecretInEnvironment"]=Environment.GetEnvironmentVariable("ALAZ_QA_PARENT_SECRET")!=null;
        r["privateReadError"]=FileAction(()=>File.ReadAllText(Path.Combine(root,"private","secret.txt")));
        r["privateWriteError"]=FileAction(()=>File.WriteAllText(Path.Combine(root,"private",mode+".txt"),"marker"));
        r["allowedReadError"]=FileAction(()=> {Require(File.ReadAllText(Path.Combine(root,"allowed","input.txt"))=="ALAZ_ALLOWED","bad_fixture");});
        r["allowedWriteError"]=FileAction(()=>File.WriteAllText(Path.Combine(root,"allowed",mode+".txt"),"marker"));
        r["ipv4Error"]=Connect(IPAddress.Loopback,p4);r["ipv6Error"]=Connect(IPAddress.IPv6Loopback,p6);
        // No credential or application data sent. Only an ACCESS_DENIED is a pass.
        // Timeout/unreachable on TEST-NET is NOT evidence of network isolation.
        if(mode=="isolated")r["testNetError"]=Connect(IPAddress.Parse("192.0.2.1"),9);
        IntPtr p=OpenProcess(0x10,false,parent);r["parentMemoryOpenError"]=p==IntPtr.Zero?Marshal.GetLastWin32Error():0;if(p!=IntPtr.Zero)CloseHandle(p);
        Write(Path.Combine(outputRoot,mode+".json"),r);return 0;
    }
    static int Parent(string root) {
        root=Path.GetFullPath(root);Require(Directory.Exists(root),"missing_fresh_workspace");
        string executable=Path.Combine(root,"app","probe.exe");Require(File.Exists(executable),"probe_not_staged");
        string profile="AlazHarness.QA."+Guid.NewGuid().ToString("N");IntPtr sid=IntPtr.Zero;bool created=false;
        var report=new Dictionary<string,object>();var errors=new List<string>();report["errors"]=errors;
        report["scope"]="Windows OS feasibility probe only; no Hermes process or real credential";report["profileName"]=profile;
        TcpListener v4=null,v6=null;Thread t4=null,t6=null;int count4=0,count6=0;
        try {
            foreach(string folder in new string[]{"allowed","writable","private"}) {string p=Path.Combine(root,folder);Require(!Directory.Exists(p),"workspace_not_fresh");Directory.CreateDirectory(p);}
            File.WriteAllText(Path.Combine(root,"allowed","input.txt"),"ALAZ_ALLOWED");
            string secret=Guid.NewGuid().ToString("N");Environment.SetEnvironmentVariable("ALAZ_QA_PARENT_SECRET",secret);
            File.WriteAllText(Path.Combine(root,"private","secret.txt"),secret);
            v4=new TcpListener(IPAddress.Loopback,0);v6=new TcpListener(IPAddress.IPv6Loopback,0);v4.Start();v6.Start();
            t4=new Thread(()=> {try {while(true)using(var c=v4.AcceptTcpClient()){c.ReceiveTimeout=1500;if(c.GetStream().ReadByte()==0x41)Interlocked.Increment(ref count4);}}catch(SocketException){}catch(ObjectDisposedException){}});t4.IsBackground=true;t4.Start();
            t6=new Thread(()=> {try {while(true)using(var c=v6.AcceptTcpClient()){c.ReceiveTimeout=1500;if(c.GetStream().ReadByte()==0x41)Interlocked.Increment(ref count6);}}catch(SocketException){}catch(ObjectDisposedException){}});t6.IsBackground=true;t6.Start();
            int port4=((IPEndPoint)v4.LocalEndpoint).Port,port6=((IPEndPoint)v6.LocalEndpoint).Port;uint parent=(uint)Process.GetCurrentProcess().Id;
            var baseline=Start(executable,root,port4,port6,parent,IntPtr.Zero,"baseline",false,Path.Combine(root,"writable"));report["baseline"]=baseline;
            var b=(Dictionary<string,object>)baseline["child"];
            foreach(string key in new string[]{"privateReadError","privateWriteError","allowedReadError","allowedWriteError","ipv4Error","ipv6Error","parentMemoryOpenError"})Require(Convert.ToInt32(b[key])==0,"baseline_"+key);
            Require((bool)b["parentSecretInEnvironment"],"baseline_environment");
            int hr=CreateAppContainerProfile(profile,profile,"AlazHarness isolated temporary QA",IntPtr.Zero,0,out sid);
            if(hr!=0)throw new Win32Exception(hr,"CreateAppContainerProfile");created=true;
            var identifier=new SecurityIdentifier(sid);report["appContainerSid"]=identifier.Value;
            GrantRead(Path.Combine(root,"app"),identifier);GrantRead(Path.Combine(root,"allowed"),identifier);IntPtr folderPointer;int folderHr=GetAppContainerFolderPath(identifier.Value,out folderPointer);
            if(folderHr!=0)throw new Win32Exception(folderHr,"GetAppContainerFolderPath");
            string profileFolder;try{profileFolder=Marshal.PtrToStringUni(folderPointer);}finally{Marshal.FreeCoTaskMem(folderPointer);}
            Require(profileFolder.IndexOf(profile,StringComparison.OrdinalIgnoreCase)>=0,"unexpected_profile_folder");
            string profileOutput=Path.Combine(profileFolder,"Temp");Directory.CreateDirectory(profileOutput);
            var isolated=Start(executable,root,port4,port6,parent,sid,"isolated",false,profileOutput);report["isolated"]=isolated;
            var s=(Dictionary<string,object>)isolated["child"];
            Require((bool)s["isAppContainer"]&&Convert.ToInt32(s["capabilityCount"])==0,"child_token");
            Require(!(bool)s["parentSecretInEnvironment"],"secret_environment_leak");
            foreach(string key in new string[]{"privateReadError","privateWriteError","allowedWriteError","parentMemoryOpenError"})Require(Convert.ToInt32(s[key])==5,"isolation_"+key);
            Require(Convert.ToInt32(s["allowedReadError"])==0,"allowed_read_failed");
            report["timeoutProbe"]=Start(executable,root,port4,port6,parent,sid,"timeout",true,profileOutput);
            report["fixtureSecretUnchanged"]=File.ReadAllText(Path.Combine(root,"private","secret.txt"))==secret;
            Require((bool)report["fixtureSecretUnchanged"],"private_content_changed");
            foreach(string key in new string[]{"ipv4Error","ipv6Error","testNetError"})Require(Convert.ToInt32(s[key])==10013,"isolation_"+key);
            Thread.Sleep(100);Require(count4==1&&count6==1,"unexpected_network_delivery");

        } catch(Exception e) {errors.Add(e is Win32Exception?"Win32:"+((Win32Exception)e).NativeErrorCode+":"+e.Message:e.GetType().Name+":"+e.Message);}
        finally {
            if(v4!=null)v4.Stop();if(v6!=null)v6.Stop();if(t4!=null)t4.Join(3000);if(t6!=null)t6.Join(3000);
            report["ipv4ListenerMessages"]=count4;report["ipv6ListenerMessages"]=count6;
            report["listenersStopped"]=(t4==null||!t4.IsAlive)&&(t6==null||!t6.IsAlive);
            if(created) {int hr=DeleteAppContainerProfile(profile);report["profileDeleteHresult"]=hr;if(hr!=0)errors.Add("profile_cleanup_failed");}
            else report["profileDeleteHresult"]=null;
            if(sid!=IntPtr.Zero)FreeSid(sid);Environment.SetEnvironmentVariable("ALAZ_QA_PARENT_SECRET",null);
        }
        report["result"]=errors.Count==0?"PASS":"FAIL";report["hermesIsolationAccepted"]=false;
        report["firewallModified"]=false;report["loopbackExemptionAdded"]=false;report["modelCalls"]=0;
        Write(Path.Combine(root,"observation.json"),report);Console.WriteLine(Json().Serialize(report));return errors.Count==0?0:1;
    }
    public static int Main(string[] args) {
        SetErrorMode(1|2);
        try {if(args.Length==8&&args[0]=="--child")return Child(args);if(args.Length==2&&args[0]=="--probe")return Parent(args[1]);return 2;}
        catch(Exception e) {Console.Error.WriteLine(e.GetType().Name);return 2;}
    }
}
