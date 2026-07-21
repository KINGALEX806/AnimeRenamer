@echo off
cd /d "%~dp0"

echo Running diagnostics... > diagnose.log 2>&1

echo ====== Python Info ====== >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1
echo [1] Which python in PATH: >> diagnose.log 2>&1
where python >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1

echo [2] Python version: >> diagnose.log 2>&1
python --version >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1

echo [3] PySide6 check: >> diagnose.log 2>&1
python -c "import PySide6; print('PySide6 version:', PySide6.__version__)" >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1

echo [4] requests check: >> diagnose.log 2>&1
python -c "import requests; print('requests version:', requests.__version__)" >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1

echo ====== .venv Python ====== >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1
echo [5] .venv python path: >> diagnose.log 2>&1
echo "%~dp0.venv\Scripts\python.exe" >> diagnose.log 2>&1
if exist "%~dp0.venv\Scripts\python.exe" (
    echo EXISTS >> diagnose.log 2>&1
    "%~dp0.venv\Scripts\python.exe" --version >> diagnose.log 2>&1
) else (
    echo NOT FOUND >> diagnose.log 2>&1
)
echo.  >> diagnose.log 2>&1

echo ====== Config File ====== >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1
echo [6] Config path: >> diagnose.log 2>&1
echo %USERPROFILE%\.anime_renamer\config.json >> diagnose.log 2>&1
if exist "%USERPROFILE%\.anime_renamer\config.json" (
    echo EXISTS >> diagnose.log 2>&1
    type "%USERPROFILE%\.anime_renamer\config.json" >> diagnose.log 2>&1
) else (
    echo NOT FOUND >> diagnose.log 2>&1
)
echo.  >> diagnose.log 2>&1

echo ====== sys.path ====== >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1
echo [7] sys.path and sys.executable: >> diagnose.log 2>&1
"%~dp0.venv\Scripts\python.exe" -c "import sys,os; print('executable:', sys.executable); print('path:'); [print(' ', p) for p in sys.path]" >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1

echo ====== Core Test ====== >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1
echo [8] Full test with .venv Python: >> diagnose.log 2>&1
"%~dp0.venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, r'E:\AnimeRenamer'); from core.parser import parse_filename; from core.recognizer import AnimeRecognizer; from utils.config import load_config; import os; print('config theme:', load_config().get('theme')); print('python executable:', sys.executable); print('cwd:', os.getcwd())" >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1

echo [9] Clear cache and test: >> diagnose.log 2>&1
"%~dp0.venv\Scripts\python.exe" -c "import os,glob; [os.remove(f) for f in glob.glob(os.path.expanduser('~/.anime_cache/*.json'))]" >> diagnose.log 2>&1
"%~dp0.venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, r'E:\AnimeRenamer'); from core.parser import parse_filename; from core.recognizer import AnimeRecognizer; import os; os.environ['HOME'] = os.path.expanduser('~'); info = parse_filename('[VCB-Studio] Fate Strange 01.mkv'); r = AnimeRecognizer(log_callback=print); ai = r.recognize(info); print('ID:', ai.bangumi_id); print('Title:', ai.title); print('Ep1:', ai.get_episode_title(1, 'cn'))" >> diagnose.log 2>&1
echo.  >> diagnose.log 2>&1

echo DONE. Please check diagnose.log >> diagnose.log 2>&1
echo Done! Check diagnose.log for results.
pause