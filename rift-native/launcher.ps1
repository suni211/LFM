param([switch]$SkipUpdate)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$base = 'https://berrple.com/rift/updates/windows/'
$versionRoot = Join-Path $root 'versions'
$pointer = Join-Path $root 'installed-version.txt'
$bundled = Join-Path $root 'RiftManagerNative.exe'
$current = if (Test-Path -LiteralPath $pointer) { (Get-Content -Raw -LiteralPath $pointer).Trim() } else { '' }
$launch = $bundled
if ($current -match '^\d{1,8}\.\d{1,8}\.\d{1,8}$') {
    $installed = Join-Path $versionRoot "$current/RiftManagerNative.exe"
    if (Test-Path -LiteralPath $installed -PathType Leaf) { $launch = $installed }
    else { $current = '' }
} else { $current = '' }
if (!$SkipUpdate) {
    $staging = $null
    try {
        $release = Invoke-RestMethod ($base + 'latest.json') -TimeoutSec 8 -MaximumRedirection 0
        if ($release.version -notmatch '^\d{1,8}\.\d{1,8}\.\d{1,8}$' -or
            $release.sha256 -notmatch '^[a-fA-F0-9]{64}$') { throw 'Invalid release manifest.' }
        $version = [version]$release.version
        if (!$current -or $version -gt [version]$current) {
            New-Item -ItemType Directory -Path $versionRoot -Force | Out-Null
            $staging = Join-Path $versionRoot ('.staging-' + [guid]::NewGuid().ToString('N'))
            New-Item -ItemType Directory -Path $staging | Out-Null
            $archive = Join-Path $staging 'package.zip'
            Invoke-WebRequest ($base + "$version.zip") -OutFile $archive -UseBasicParsing -TimeoutSec 60 -MaximumRedirection 0
            if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $release.sha256) {
                throw 'Release archive checksum mismatch.'
            }
            $unpacked = Join-Path $staging 'app'
            Expand-Archive -LiteralPath $archive -DestinationPath $unpacked
            foreach ($required in @('RiftManagerNative.exe','assets/main.rml','assets/people.json')) {
                if (!(Test-Path -LiteralPath (Join-Path $unpacked $required) -PathType Leaf)) {
                    throw "Missing release file: $required"
                }
            }
            $canonical = Join-Path $versionRoot $version
            [IO.Directory]::Move($unpacked,$canonical)
            $tempPointer = Join-Path $staging 'installed-version.txt'
            [IO.File]::WriteAllText($tempPointer,$version.ToString())
            if ([IO.File]::Exists($pointer)) { [IO.File]::Replace($tempPointer,$pointer,$null) }
            else { [IO.File]::Move($tempPointer,$pointer) }
            $launch = Join-Path $canonical 'RiftManagerNative.exe'
        }
    } catch {
        Write-Warning ('Update skipped: ' + $_.Exception.Message)
    } finally {
        if ($staging -and (Test-Path -LiteralPath $staging)) {
            $actual = (Resolve-Path -LiteralPath $staging).Path
            $parent = (Resolve-Path -LiteralPath $versionRoot).Path
            if ([IO.Path]::GetDirectoryName($actual) -eq $parent -and
                [IO.Path]::GetFileName($actual) -match '^\.staging-[a-f0-9]{32}$') {
                Remove-Item -LiteralPath $actual -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    }
}
if (!(Test-Path -LiteralPath $launch -PathType Leaf)) { throw 'RiftManagerNative.exe is missing.' }
& $launch
exit $LASTEXITCODE
