@echo off
rem = """-*-Python-*- script
rem -------------------- DOS section --------------------
rem You could set PYTHONPATH or TK environment variables here
python -x "%~f0" %*
goto exit
 
"""
# -------------------- Python section --------------------
import sys
from yams.tools import schema_image
sys.exit(schema_image())

DosExitLabel = """
:exit
rem """
