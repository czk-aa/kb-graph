$ErrorActionPreference = "Continue"
$log = "C:\Users\15573\Desktop\知识库\.pg_setup.log"
$bin = "C:\Program Files\PostgreSQL\16\bin"
$data = "C:\Program Files\PostgreSQL\16\data"

function Log($msg) { Add-Content -Path $log -Value "$(Get-Date -Format HH:mm:ss) $msg" }
function WaitService($state) {
    for ($i = 0; $i -lt 30; $i++) {
        $s = (Get-Service postgresql-x64-16).Status
        if ($s -eq $state) { return $true }
        Start-Sleep 1
    }
    return $false
}

"" | Set-Content $log
Log "stopping service"
Stop-Service postgresql-x64-16 -Force
[void](WaitService "Stopped")
Log "starting service (hba has trust rules)"
Start-Service postgresql-x64-16
[void](WaitService "Running")
Start-Sleep 2

Log "resetting postgres password"
$out = & "$bin\psql.exe" -h 127.0.0.1 -U postgres -d postgres -c "ALTER USER postgres PASSWORD 'postgres';" 2>&1
Log "psql1: $out"

Log "stopping service to restore hba"
Stop-Service postgresql-x64-16 -Force
[void](WaitService "Stopped")
Copy-Item "$data\pg_hba.conf.bak" "$data\pg_hba.conf" -Force
Log "hba restored, starting service"
Start-Service postgresql-x64-16
[void](WaitService "Running")
Start-Sleep 2

Log "verifying password auth"
$env:PGPASSWORD = "postgres"
$out = & "$bin\psql.exe" -h 127.0.0.1 -U postgres -d postgres -c "SELECT 'auth_ok';" 2>&1
Log "psql2: $out"
Log "DONE"
