param(
    [ValidateSet("docker", "local")]
    [string]$ExecutionMode = "docker",
    [string]$ServiceName = "backend",
    [int]$MaxModels = -1,
    [int]$MaxLive = -1,
    [string]$ProviderAllowlist = "",
    [switch]$IncludeVerifiedLive,
    [switch]$EnableImageTextV2,
    [switch]$StrictImageTextChecks,
    [switch]$EnableFileTextV3,
    [switch]$StrictFileTextChecks
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
if ($EnableImageTextV2) {
    $argsList += "--enable-image-text-v2"
}
if ($StrictImageTextChecks) {
    $argsList += "--strict-image-text-checks"
}
if ($EnableFileTextV3) {
    $argsList += "--enable-file-text-v3"
}
if ($StrictFileTextChecks) {
    $argsList += "--strict-file-text-checks"
}

if ($ExecutionMode -eq "local") {
    & $argsList[0] $argsList[1..($argsList.Length - 1)]
}
else {
    docker compose exec $ServiceName @argsList
}
