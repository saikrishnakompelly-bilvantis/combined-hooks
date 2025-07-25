@echo off
echo Building APIGenie application...

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Install requirements if not already installed
pip install -r requirements.txt

REM Convert logo.png to logo.ico if needed
REM You can use a tool like ImageMagick or an online converter to create logo.ico
REM Place the logo.ico file in assets/

REM Build the executable
pyinstaller --clean apigenie.spec

REM Copy CLI wrapper scripts to dist folder
echo Copying CLI wrapper scripts...
copy apigenie-cli.bat dist\apigenie-cli.bat >nul 2>&1
copy apigenie-cli.ps1 dist\apigenie-cli.ps1 >nul 2>&1
echo CLI wrapper scripts copied to dist folder.

echo Build complete!
echo The executable can be found at dist\APIGenie.exe
echo CLI wrappers: dist\apigenie-cli.bat and dist\apigenie-cli.ps1
pause 