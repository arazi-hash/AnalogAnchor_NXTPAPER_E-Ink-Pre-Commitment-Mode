try {
    . (Join-Path $PSScriptRoot 'Android-Device.ps1')
    $guardAdb = Get-GuardAdb
    $guardSerial = Get-GuardDevice $guardAdb
    # Pipe a constant script over stdin; no shell interpolation of device data.
    $script = [System.IO.File]::ReadAllText((Join-Path $PSScriptRoot 'start_shizuku_usb.sh')).Replace("`r`n", "`n")
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $guardAdb
    $info.Arguments = "-s $guardSerial shell sh"
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardInput = $true
    $process = [System.Diagnostics.Process]::Start($info)
    $process.StandardInput.Write($script)
    $process.StandardInput.Close()
    if (!$process.WaitForExit(45000)) {
        $process.Kill()
        throw 'Shizuku startup timed out. Open Shizuku on the phone and check its startup status.'
    }
    if ($process.ExitCode -ne 0) { throw 'Shizuku startup failed. Read the error above.' }
    Write-Host 'Startup command completed. Check Shizuku says Running, then open NXTPAPER Guard. Wi-Fi is not needed for this USB method.'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
