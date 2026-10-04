$ErrorActionPreference = 'Stop'

function Get-GuardAdb {
    if ($env:NXTPAPER_ADB -and (Test-Path -LiteralPath $env:NXTPAPER_ADB -PathType Leaf)) {
        return $env:NXTPAPER_ADB
    }
    $command = Get-Command adb.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $candidate = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    throw 'ADB not found. Install Android Platform Tools or set NXTPAPER_ADB to adb.exe.'
}

function Get-GuardDevice([string]$Adb) {
    $list = & $Adb devices
    if ($LASTEXITCODE -ne 0) { throw 'ADB could not list devices.' }
    $available = @($list | Where-Object { $_ -match '^\S+\s+device$' })
    if ($available.Count -ne 1) {
        throw 'Connect exactly one phone by USB, enable USB debugging, and accept its computer authorization prompt.'
    }
    $deviceSerial = ($available[0] -split '\s+')[0]
    if ($deviceSerial -notmatch '^[A-Za-z0-9._:-]+$') { throw 'The connected device returned an unsupported identifier.' }
    return $deviceSerial
}

function Invoke-GuardAdb([string]$Adb, [string]$Serial, [string[]]$Arguments) {
    & $Adb -s $Serial @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'ADB command failed. Check the phone connection and the error above.' }
}
