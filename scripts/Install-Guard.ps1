try {
    . (Join-Path $PSScriptRoot 'Android-Device.ps1')
    $guardAdb = Get-GuardAdb
    $guardSerial = Get-GuardDevice $guardAdb
    $apk = Join-Path (Split-Path -Parent $PSScriptRoot) 'nxtpaper_guard\app\build\outputs\apk\debug\app-debug.apk'
    if (!(Test-Path -LiteralPath $apk -PathType Leaf)) {
        throw 'Build the APK first: in nxtpaper_guard run .\gradlew.bat assembleDebug --max-workers=1 --no-parallel'
    }
    Invoke-GuardAdb $guardAdb $guardSerial @('install', '-r', $apk)
    Invoke-GuardAdb $guardAdb $guardSerial @('shell', 'am', 'start', '-n', 'com.analoganchor.nxtpaperguard/.MainActivity')
    Write-Host 'APK installed. Start Shizuku, open E-Ink Pre-commitment Mode, allow its permission, then enable the guard. The APK includes its controller.'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
