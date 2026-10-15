"""Validate a Windows venv redirector's child using OS ancestry and a held handle."""
from __future__ import annotations
import os

def ancestry(target: int, launcher: int, parents: dict[int,int]) -> list[int]:
    if type(target) is not int or type(launcher) is not int or min(target,launcher)<=0:
        raise ValueError('Invalid process identity')
    chain=[];current=target
    for _ in range(8):
        if current in chain:break
        chain.append(current)
        if current==launcher:return chain
        current=parents.get(current,0)
        if not current:break
    raise ValueError('Gateway process is not an owned launcher descendant')

class OwnedGatewayProcess:
    def __init__(self,child,pid: int):
        self.child,self.pid,self.handle=child,pid,None
        if child.poll() is not None:raise RuntimeError('Launcher already exited')
        if os.name!='nt':
            self.chain=ancestry(pid,child.pid,{})
            return
        import ctypes
        from ctypes import wintypes as w
        k=ctypes.WinDLL('kernel32',use_last_error=True);self.k=k
        class Entry(ctypes.Structure):
            _fields_=[('size',w.DWORD),('usage',w.DWORD),('pid',w.DWORD),('heap',ctypes.c_size_t),
                      ('module',w.DWORD),('threads',w.DWORD),('parent',w.DWORD),('priority',w.LONG),
                      ('flags',w.DWORD),('exe',w.WCHAR*260)]
        k.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];k.CreateToolhelp32Snapshot.restype=w.HANDLE
        k.Process32FirstW.argtypes=[w.HANDLE,ctypes.POINTER(Entry)];k.Process32FirstW.restype=w.BOOL
        k.Process32NextW.argtypes=[w.HANDLE,ctypes.POINTER(Entry)];k.Process32NextW.restype=w.BOOL
        k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
        k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
        k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.WaitForSingleObject.restype=w.DWORD
        k.TerminateProcess.argtypes=[w.HANDLE,w.UINT];k.TerminateProcess.restype=w.BOOL
        handle=k.OpenProcess(0x100000|0x1000|0x1,False,pid)
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        try:
            snap=k.CreateToolhelp32Snapshot(2,0)
            if snap==w.HANDLE(-1).value:raise ctypes.WinError(ctypes.get_last_error())
            parents={};e=Entry();e.size=ctypes.sizeof(e)
            try:
                ok=k.Process32FirstW(snap,ctypes.byref(e))
                while ok:
                    parents[int(e.pid)]=int(e.parent)
                    ok=k.Process32NextW(snap,ctypes.byref(e))
            finally:k.CloseHandle(snap)
            self.chain=ancestry(pid,child.pid,parents)
            if child.poll() is not None or k.WaitForSingleObject(handle,0)!=258:
                raise RuntimeError('Process exited during ownership check')
            self.handle=handle
        except BaseException:
            k.CloseHandle(handle);raise
    def wait(self,seconds=0) -> bool:
        if self.handle is None:return self.child.poll() is not None
        result=self.k.WaitForSingleObject(self.handle,int(seconds*1000))
        if result not in (0,258):raise OSError('Process wait failed')
        return result==0
    def kill(self):
        if self.handle is not None and not self.wait():
            if not self.k.TerminateProcess(self.handle,2):raise OSError('Owned Gateway termination failed')
        elif self.handle is None and self.child.poll() is None:self.child.kill()
    def close(self):
        if self.handle is not None:self.k.CloseHandle(self.handle);self.handle=None
