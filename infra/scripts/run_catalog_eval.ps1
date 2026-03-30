param(
    [string]$ServiceName = "backend",
    [int]$MaxModels = -1,
    [int]$MaxLive = -1,
    [string]$ProviderAllowlist = "",
    [switch]$IncludeVerifiedLive
)

$argsList = @("python", "-m", "packages.services.benchmark.cli", "catalog-run")

if ($MaxModels -ge 0) {
    $argsList += @("--max-models", "$MaxModels")
}

if ($MaxLive -ge 0) {
    $argsList += @("--max-live", "$MaxLive")
}

if ($ProviderAllowlist.Trim() -ne "") {
    $argsList += @("--provider-allowlist", $ProviderAllowlist)
}

if ($IncludeVerifiedLive) {
    $argsList += "--include-verified-live"
}

docker compose exec $ServiceName @argsList
