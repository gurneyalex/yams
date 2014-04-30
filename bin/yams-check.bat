@echo off
rem = """-*-Python-*- script
rem -------------------- DOS section --------------------
rem You could set PYTHONPATH or TK environment variables here
python -x "%~f0" %*
goto exit
 
"""
# -------------------- Python section --------------------
import sys
from yams.tools import check_schema
sys.exit(check_schema())

DosExitLabel = """
:exit
rem """
