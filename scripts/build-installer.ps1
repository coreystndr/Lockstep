$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$compiler = "C:\Program Files\Inno Setup 7\ISCC.exe"
if (-not (Test-Path -LiteralPath $compiler)) {
    throw "Inno Setup 7 wurde nicht gefunden: $compiler"
}

Push-Location $projectRoot
try {
    $pythonCommand = Get-Command py.exe, python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $pythonCommand) {
        throw "Zum Erzeugen des vollständigen Installers wird Python 3 benötigt. Installiere Python 3 und starte das Skript erneut."
    }
    $pythonPrefix = @()
    if ($pythonCommand.Name -eq "py.exe") { $pythonPrefix = @("-3") }

    & $pythonCommand.Source @pythonPrefix -m pip install -r requirements.txt pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "Python-Abhängigkeiten konnten nicht installiert werden (Exit-Code $LASTEXITCODE)." }

    $pythonArgs = @("-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--name", "lockstep-agent", "--distpath", "build/sidecar", "--workpath", "build/pyinstaller", "--specpath", "build/pyinstaller", "--collect-all", "valclient", "main.py")
    & $pythonCommand.Source @pythonPrefix @pythonArgs
    if ($LASTEXITCODE -ne 0) { throw "Der Python-Agent konnte nicht gepackt werden (Exit-Code $LASTEXITCODE)." }

    npm.cmd run tauri -- build --no-bundle
    if ($LASTEXITCODE -ne 0) { throw "Tauri-Build fehlgeschlagen (Exit-Code $LASTEXITCODE)." }

    & $compiler "installer\Lockstep.iss"
    if ($LASTEXITCODE -ne 0) { throw "Installer-Erstellung fehlgeschlagen (Exit-Code $LASTEXITCODE)." }
} finally {
    Pop-Location
}
