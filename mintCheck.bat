echo off
if exist mintCheck.py (
  set PYTHONPATH=..\github\mintapi
)
set /A live=0

if %live%==1 (
  python mintCheck.py --config home.ini --live
) else (
  python mintCheck.py --config home.ini 
)
exit
