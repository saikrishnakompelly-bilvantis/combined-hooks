# APIGenie CLI wrapper for PowerShell
# This script allows you to use APIGenie from PowerShell

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Path to the APIGenie executable
$APIGenieExe = Join-Path $ScriptDir "APIGenie.exe"

# Check if the executable exists
if (-not (Test-Path $APIGenieExe)) {
    Write-Error "APIGenie.exe not found in $ScriptDir"
    Write-Error "Make sure APIGenie is properly installed."
    exit 1
}

# Execute APIGenie with all provided arguments
try {
    & $APIGenieExe @Arguments
    exit $LASTEXITCODE
} catch {
    Write-Error "Failed to execute APIGenie: $_"
    exit 1
} 