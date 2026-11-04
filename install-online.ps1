# ============================================================
#  皮皮输入法 · 在线安装（一行命令版）
#
#  用法：以管理员身份打开 PowerShell，粘贴：
#    irm https://raw.githubusercontent.com/NengShuo/pipi-ime/main/install-online.ps1 | iex
#
#  仓库地址改下面两个变量即可。
# ============================================================

$Repo   = "NengShuo/pipi-ime"     # <-- 改成 用户名/仓库名
$Branch = "main"                  # <-- 分支名

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Step($t) { Write-Host "`n  >> $t" -ForegroundColor Cyan }
function OK($t)   { Write-Host "     OK  $t" -ForegroundColor Green }
function Warn($t) { Write-Host "     !   $t" -ForegroundColor Yellow }
function Bad($t)  { Write-Host "     X   $t" -ForegroundColor Red }

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkGray
Write-Host "        皮皮输入法  v0.1  在线安装" -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor DarkGray

# ---------- 管理员 ----------
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Bad "需要管理员权限。"
    Write-Host "     请右键「开始」→ 终端(管理员) / Windows PowerShell(管理员)，再粘贴这条命令。" -ForegroundColor Yellow
    return
}

# ---------- 找引擎 ----------
Step "检查 Rime 小狼毫引擎"

if ([Environment]::Is64BitOperatingSystem) {
    $arch = "amd64"
} else {
    $arch = "x86"
}
Write-Host "     系统架构：$arch" -ForegroundColor DarkGray

$server = $null
foreach ($p in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
    if (-not $p) { continue }
    $dir = Join-Path $p "Rime"
    if (-not (Test-Path $dir)) { continue }
    $hit = Get-ChildItem $dir -Filter "WeaselServer.exe" -Recurse -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($hit) { $server = $hit; break }
}
if (-not $server) {
    Bad "没有找到小狼毫。先装它：https://github.com/rime/weasel/releases"
    return
}
$weaselDir = $server.DirectoryName
OK "引擎：$weaselDir"

# ---------- 下载配置 ----------
Step "下载皮皮配置"

$rimeDir = Join-Path $env:APPDATA "Rime"
if (-not (Test-Path $rimeDir)) { New-Item -ItemType Directory -Path $rimeDir -Force | Out-Null }

$mirrors = @(
    "https://raw.githubusercontent.com/$Repo/$Branch/config",
    "https://cdn.jsdelivr.net/gh/$Repo@$Branch/config",
    "https://ghproxy.net/https://raw.githubusercontent.com/$Repo/$Branch/config"
)

$files = @("rime.lua", "luna_pinyin_simp.custom.yaml", "weasel.custom.yaml", "pipi-p.ico", "pipi-blank.ico")

$base = $null
foreach ($m in $mirrors) {
    try {
        $probe = "$m/rime.lua"
        $req = [Net.WebRequest]::Create($probe)
        $req.Timeout = 8000
        $resp = $req.GetResponse()
        $resp.Close()
        $base = $m
        break
    } catch {
        Write-Host "     源不可用：$m" -ForegroundColor DarkGray
    }
}
if (-not $base) {
    Bad "所有下载源都连不上。检查网络，或改用离线 zip 包。"
    return
}
OK "下载源：$base"

$stamp  = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $rimeDir "_pipi-backup-$stamp"
$n = 0
foreach ($f in $files) {
    $dst = Join-Path $rimeDir $f
    if (Test-Path $dst) {
        if (-not (Test-Path $backup)) { New-Item -ItemType Directory -Path $backup -Force | Out-Null }
        Copy-Item $dst $backup -Force
    }
    try {
        Invoke-WebRequest -Uri "$base/$f" -OutFile $dst -UseBasicParsing -TimeoutSec 30
        Write-Host "     ↓ $f" -ForegroundColor DarkGray
        $n++
    } catch {
        Bad "下载失败：$f"
    }
}
OK "已下载 $n 个文件"
if (Test-Path $backup) { OK "原配置备份在：$backup" }

# ---------- 改角标 ----------
Step "把「小狼毫」角标换成「皮皮输入法」"

$ico = Join-Path $rimeDir "pipi-p.ico"
$name = "皮皮输入法"
$patched = 0

if (Test-Path $ico) {
    foreach ($root in @("HKLM:\SOFTWARE\Microsoft\CTF\TIP",
                        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\CTF\TIP")) {
        if (-not (Test-Path $root)) { continue }
        foreach ($tip in (Get-ChildItem $root -ErrorAction SilentlyContinue)) {
            $tp = Get-ItemProperty $tip.PSPath -ErrorAction SilentlyContinue
            if ($tp -and $tp.IconFile -and $tp.IconFile -like "*weasel.dll*") {
                Set-ItemProperty $tip.PSPath -Name "Description" -Value $name  -Force
                Set-ItemProperty $tip.PSPath -Name "IconFile"    -Value $ico   -Force
                Set-ItemProperty $tip.PSPath -Name "IconIndex"   -Value 0      -Force
                $patched++
            }
            $lpRoot = Join-Path $tip.PSPath "LanguageProfile"
            if (-not (Test-Path $lpRoot)) { continue }
            foreach ($lp in (Get-ChildItem $lpRoot -Recurse -ErrorAction SilentlyContinue)) {
                $props = Get-ItemProperty $lp.PSPath -ErrorAction SilentlyContinue
                if ($props -and $props.IconFile -and $props.IconFile -like "*weasel.dll*") {
                    Set-ItemProperty $lp.PSPath -Name "Description" -Value $name -Force
                    Set-ItemProperty $lp.PSPath -Name "IconFile"    -Value $ico  -Force
                    Set-ItemProperty $lp.PSPath -Name "IconIndex"   -Value 0     -Force
                    $patched++
                }
            }
        }
    }
}
if ($patched -gt 0) { OK "已改名 $patched 处注册项" } else { Warn "没找到小狼毫注册项" }

# ---------- 部署 ----------
Step "编译输入方案（约 10-30 秒）"

$buildYaml = Join-Path $rimeDir "build\weasel.yaml"
$before = $null
if (Test-Path $buildYaml) { $before = (Get-Item $buildYaml).LastWriteTime }

$deployer = Join-Path $weaselDir "WeaselDeployer.exe"
$deployOK = $false
if (Test-Path $deployer) {
    try {
        $p = Start-Process $deployer -ArgumentList "/deploy" -WorkingDirectory $weaselDir -Wait -PassThru
        Write-Host "     退出码 $($p.ExitCode)" -ForegroundColor DarkGray
    } catch {
        Warn "部署进程没跑起来"
    }
    Start-Sleep -Seconds 1
    $after = $null
    if (Test-Path $buildYaml) { $after = (Get-Item $buildYaml).LastWriteTime }
    if ($after -and ($null -eq $before -or $after -gt $before)) { OK "配置已重新编译"; $deployOK = $true }
}

# ---------- 角标 ----------
Step "处理右下角角标"

if (Test-Path $buildYaml) {
    try {
        $txt = Get-Content $buildYaml -Raw -Encoding UTF8
        if ($txt -match "(?m)^(\s*)display_tray_icon:\s*true") {
            $txt = [regex]::Replace($txt, "(?m)^(\s*)display_tray_icon:\s*true", '$1display_tray_icon: false')
            # 无 BOM 写回，Rime 不认 BOM
            [System.IO.File]::WriteAllText($buildYaml, $txt, (New-Object System.Text.UTF8Encoding($false)))
            OK "已关闭小狼毫自带托盘图标"
        } else {
            OK "托盘图标已是关闭状态"
        }
    } catch { Warn "改配置失败" }
}

# 说明托盘最终长什么样（取决于本机装了几个输入法）
try {
    $ims = (Get-WinUserLanguageList)[0].InputMethodTips
    if ($ims.Count -gt 1) {
        Warn "本机装了 $($ims.Count) 个中文输入法"
        Write-Host "     右下角会是：蓝牙 [空格] P 时钟" -ForegroundColor Gray
        Write-Host "     那格空格是 Windows 给「输入法模式」固定预留的，改配置删不掉。" -ForegroundColor Gray
        Write-Host "     想变成「只有一个皮皮 P、没有空格」：" -ForegroundColor Gray
        Write-Host "       设置 -> 时间和语言 -> 语言 -> 中文(简体) -> 选项 -> 删掉微软拼音" -ForegroundColor Gray
        Write-Host "       （想加回来：同一页面点「添加键盘」。删掉前请确认皮皮能正常打字）" -ForegroundColor Gray
    } else {
        OK "只有皮皮一个输入法，右下角不会有空格"
    }
} catch { }

# ---------- 重启 ----------
Step "重启输入法服务"
Stop-Process -Name WeaselServer -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800
# 用 explorer 代启：若本脚本由 AI 助手/终端代理执行，直接 Start-Process 起的进程
# 会挂在调用方的作业对象下，脚本一结束就被连带杀掉（表现为「打了字没反应」）。
$serverArg = '"' + $server.FullName + '"'
& explorer.exe $serverArg
Start-Sleep -Seconds 3
if (Get-Process -Name WeaselServer -ErrorAction SilentlyContinue) { OK "服务已启动" } else { Warn "服务没起来" }

Step "刷新任务栏（会闪一下）"
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
if (-not (Get-Process -Name explorer -ErrorAction SilentlyContinue)) { Start-Process "explorer.exe" }
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkGray
Write-Host "   装好了。打个字试试：" -ForegroundColor White
Write-Host ""
Write-Host "     woyaochifan  →  1 我要吃饭   2 woyaochifan" -ForegroundColor Gray
Write-Host "     meeting      →  1 meeting    2 么额听" -ForegroundColor Gray
Write-Host ""
if (-not $deployOK) {
    Write-Host "   配置编译没确认成功。如果打了字母没候选窗，" -ForegroundColor Yellow
    Write-Host "   去小狼毫目录双击 WeaselDeployer.exe 重新部署。" -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "  ============================================" -ForegroundColor DarkGray
Write-Host ""
