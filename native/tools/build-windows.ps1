param(
    [string]$LlvmRoot = '',
    [string]$BuildDirectory = '',
    [string]$DependencyDirectory = '',
    [switch]$BuildOnly
)
$ErrorActionPreference = 'Stop'
$ParadoxRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (!$LlvmRoot) { $LlvmRoot = Join-Path $ParadoxRoot 'scratch/toolchains/llvm' }
if (!$BuildDirectory) { $BuildDirectory = Join-Path $ParadoxRoot 'build/windows' }
$VsWhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$VsPath = & $VsWhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (!$VsPath) { throw 'Visual Studio C++ Build Tools are required.' }
Import-Module (Join-Path $VsPath 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll')
Enter-VsDevShell -VsInstallPath $VsPath -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'
$CMakeRoot = Join-Path $VsPath 'Common7/IDE/CommonExtensions/Microsoft/CMake'
$CMake = Join-Path $CMakeRoot 'CMake/bin/cmake.exe'
$env:PATH = (Join-Path $LlvmRoot 'bin') + ';' + (Join-Path $CMakeRoot 'Ninja') + ';' + $env:PATH
$CMakeArgs = @('-S', $ParadoxRoot, '-B', $BuildDirectory, '-G', 'Ninja',
    '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_C_COMPILER=clang-cl', '-DCMAKE_CXX_COMPILER=clang-cl',
    '-DCMAKE_LINKER=lld-link', '-DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON')
if ($DependencyDirectory) { $CMakeArgs += "-DCMAKE_PREFIX_PATH=$DependencyDirectory" }
$SdkSource = Join-Path $ParadoxRoot 'scratch/references/endstone'
if (Test-Path $SdkSource) { $CMakeArgs += "-DFETCHCONTENT_SOURCE_DIR_ENDSTONE=$SdkSource" }
$ProtocolSource = Join-Path $ParadoxRoot 'scratch/windows-protocol'
if (Test-Path (Join-Path $ProtocolSource 'generated/include/bedrock/protocol.hpp')) {
    $CMakeArgs += "-DFETCHCONTENT_SOURCE_DIR_BEDROCK_PROTOCOL=$ProtocolSource"
}
if (!$BuildOnly) {
    & $CMake @CMakeArgs
    if ($LASTEXITCODE) { throw 'CMake configuration failed.' }
}
& $CMake --build $BuildDirectory --parallel 4
if ($LASTEXITCODE) { throw 'Native build failed.' }
& (Join-Path $CMakeRoot 'CMake/bin/ctest.exe') --test-dir $BuildDirectory --output-on-failure
if ($LASTEXITCODE) { throw 'Native tests failed.' }
