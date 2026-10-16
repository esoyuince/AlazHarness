"""Existing public lifecycle; periodic stack diagnostics are explicitly opt-in.

An observed Windows process fault happened while dump_traceback_later wrote a
partial stack. Causality is not established. Normal acceptance does not run this
extra watchdog thread; process ownership/deadlines are still enforced by parent.
"""
import faulthandler
import os
from pathlib import Path
import runpy
mode=os.environ.get('ALAZ_PROBE_DIAGNOSTIC_STACKS','0')
if mode not in ('0','1'):raise ValueError('Invalid diagnostic stack flag')
if mode=='1':faulthandler.dump_traceback_later(30,repeat=True)
try:
    runpy.run_path(str(Path(__file__).with_name('native_gateway_worker.py')),run_name='__main__')
finally:
    if mode=='1':faulthandler.cancel_dump_traceback_later()
