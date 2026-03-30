param(
    [string]$ContainerName = "llm-router-db",
    [string]$Database = "llm_router",
    [string]$User = "postgres"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sqlPath = Join-Path $scriptDir "monitor_catalog.sql"

if (!(Test-Path $sqlPath)) {
    throw "SQL script not found: $sqlPath"
}

Get-Content -Raw $sqlPath | docker exec -i $ContainerName psql -U $User -d $Database
