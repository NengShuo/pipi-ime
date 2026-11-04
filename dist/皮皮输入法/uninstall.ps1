# ============================================================
#  皮皮输入法 · 卸载（只卸皮皮，保留小狼毫引擎）
# ============================================================

$ErrorActionPreference = "Continue"

function Write-Step($t) { Write-Host ""; Write-Host "  >> $t" -ForegroundColor Cyan }
function Write-OK($t)   { Write-Host "     OK  $t" -ForegroundColor Green }
function Write-Warn($t) { Write-Host "     !   $t" -ForegroundColor Yellow }

$identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "  需要管理员权限，请右键 uninstall.bat 选「以管理员身份运行」。" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

Write-Host ""
Write-Host "  皮皮输入法 卸载程序" -ForegroundColor White
Write-Host "  会移除皮皮的键盘方案和取名，小狼毫本身保留。" -ForegroundColor DarkGray

$rimeDir = Join-Path $env:APPDATA "Rime"

# ---------- 1. 恢复系统输入指示器 ----------
Write-Step "恢复系统角标的名称与图标"

$patched = 0
$roots = @("HKLM:\SOFTWARE\Microsoft\CTF\TIP",
           "HKLM:\SOFTWARE\WOW6432Node\Microsoft\CTF\TIP")
foreach ($root in $roots) {
    if (-not (Test-Path $root)) { continue }
    foreach ($tip in (Get-ChildItem $root -ErrorAction SilentlyContinue)) {
        $targets = @($tip)
        $lpRoot = Join-Path $tip.PSPath "LanguageProfile"
        if (Test-Path $lpRoot) {
            $targets += (Get-ChildItem $lpRoot -Recurse -ErrorAction SilentlyContinue)
        }
        foreach ($t in $targets) {
            $props = Get-ItemProperty $t.PSPath -ErrorAction SilentlyContinue
            if (-not $props) { continue }
            if ($props.IconFile -and $props.IconFile -like "*pipi*") {
                Set-ItemProperty -Path $t.PSPath -Name "Description" -Value "小狼毫"                        -Force
                Set-ItemProperty -Path $t.PSPath -Name "IconFile"    -Value "C:\Windows\system32\weasel.dll" -Force
                Set-ItemProperty -Path $t.PSPath -Name "IconIndex"   -Value 0                                -Force
                $patched++
            }
        }
    }
}
if ($patched -gt 0) { Write-OK "已恢复 $patched 处" } else { Write-Warn "没有找到需要恢复的项" }

# ---------- 2. 删掉皮皮的配置 ----------
Write-Step "移除皮皮的配置文件"

$targets = @(
    "rime.lua",
    "luna_pinyin_simp.custom.yaml",
    "weasel.custom.yaml",
    "pipi-p.ico",
    "pipi-hat.ico",
    "pipi-state.json",
    "pipi-cmd.json"
)
$removed = 0
foreach ($name in $targets) {
    $f = Join-Path $rimeDir $name
    if (Test-Path $f) {
        Remove-Item $f -Force -ErrorAction SilentlyContinue
        $removed++
    }
}
Write-OK "已删除 $removed 个文件"

# 恢复小狼毫自带托盘图标
$buildYaml = Join-Path $rimeDir "build\weasel.yaml"
if (Test-Path $buildYaml) {
    $txt = Get-Content $buildYaml -Raw -Encoding UTF8
    if ($txt -match "(?m)^(\s*)display_tray_icon:\s*false") {
        $txt = [regex]::Replace($txt, "(?m)^(\s*)display_tray_icon:\s*false", '$1display_tray_icon: true')
        # 无 BOM 写回
        [System.IO.File]::WriteAllText($buildYaml, $txt, (New-Object System.Text.UTF8Encoding($false)))
        Write-OK "已恢复小狼毫托盘图标"
    }
}

# ---------- 3. 重启 ----------
Write-Step "重启输入法服务"
Stop-Process -Name WeaselServer -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800

$server = Get-ChildItem -Path "$env:ProgramFiles\Rime","${env:ProgramFiles(x86)}\Rime" `
          -Filter "WeaselServer.exe" -Recurse -ErrorAction SilentlyContinue |
          Select-Object -First 1
if ($server) {
    Start-Process -FilePath $server.FullName -WorkingDirectory $server.DirectoryName
    Start-Sleep -Seconds 2
    Write-OK "服务已重启"
}

Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
if (-not (Get-Process -Name explorer -ErrorAction SilentlyContinue)) { Start-Process "explorer.exe" }
Start-Sleep -Seconds 1
Write-OK "任务栏已刷新"

Write-Host ""
Write-Host "  卸载完成。小狼毫还在，但会退回自带的原样配置。" -ForegroundColor White
Write-Host "  想彻底删掉小狼毫，去「设置 → 应用」里卸载 Rime Weasel。" -ForegroundColor DarkGray
Write-Host ""
Read-Host "按回车关闭"
