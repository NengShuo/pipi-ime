# ============================================================
#  皮皮输入法 · 一键安装
#  基于 Rime/Weasel (GPL-3.0) 的配置层
#  需要管理员权限（要写 HKLM 注册表）
# ============================================================

$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot

function Write-Step($text) {
    Write-Host ""
    Write-Host "  >> $text" -ForegroundColor Cyan
}
function Write-OK($text)   { Write-Host "     OK  $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "     !   $text" -ForegroundColor Yellow }
function Write-Err($text)  { Write-Host "     X   $text" -ForegroundColor Red }

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkGray
Write-Host "        皮皮输入法  v0.1  安装程序" -ForegroundColor White
Write-Host "        能自动认中英的拼音输入法" -ForegroundColor DarkGray
Write-Host "  ============================================" -ForegroundColor DarkGray

# ---------- 0. 管理员权限检查 ----------
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Err "需要管理员权限，请右键 install.bat 选「以管理员身份运行」。"
    Read-Host "按回车退出"
    exit 1
}

# ---------- 1. 找小狼毫 ----------
Write-Step "检查 Rime 小狼毫引擎"

$searchRoots = @()
if ($env:ProgramFiles)      { $searchRoots += (Join-Path $env:ProgramFiles "Rime") }
if (${env:ProgramFiles(x86)}) { $searchRoots += (Join-Path ${env:ProgramFiles(x86)} "Rime") }

$server = $null
foreach ($r in $searchRoots) {
    if (-not (Test-Path $r)) { continue }
    $hit = Get-ChildItem -Path $r -Filter "WeaselServer.exe" -Recurse -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($hit) { $server = $hit; break }
}

if (-not $server) {
    Write-Err "没有找到小狼毫（Weasel）。"
    Write-Host ""
    Write-Host "  皮皮输入法依赖小狼毫的引擎（Rime），需要先装它：" -ForegroundColor White
    Write-Host "    https://github.com/rime/weasel/releases" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  装完小狼毫后，再双击一次 install.bat 即可。" -ForegroundColor White
    Read-Host "按回车打开下载页"
    Start-Process "https://github.com/rime/weasel/releases"
    exit 1
}

$weaselDir = $server.DirectoryName
Write-OK "引擎位置：$weaselDir"

$ver = (Get-Item $server.FullName).VersionInfo.FileVersion
if ($ver) { Write-OK "版本：$ver" }

# ---------- 2. 复制配置 ----------
Write-Step "安装皮皮配置到 $env:APPDATA\Rime"

$rimeDir = Join-Path $env:APPDATA "Rime"
if (-not (Test-Path $rimeDir)) {
    New-Item -ItemType Directory -Path $rimeDir -Force | Out-Null
}

$srcDir = Join-Path $Root "files"
if (-not (Test-Path $srcDir)) {
    Write-Err "安装包不完整：缺少 files 目录。"
    Read-Host "按回车退出"
    exit 1
}

$stamp  = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $rimeDir "_pipi-backup-$stamp"
$copied = 0
foreach ($f in Get-ChildItem $srcDir -File) {
    $dst = Join-Path $rimeDir $f.Name
    if (Test-Path $dst) {
        if (-not (Test-Path $backup)) { New-Item -ItemType Directory -Path $backup -Force | Out-Null }
        Copy-Item $dst $backup -Force
    }
    Copy-Item $f.FullName $dst -Force
    $copied++
}
Write-OK "已复制 $copied 个文件"
if (Test-Path $backup) { Write-OK "原配置已备份到：$backup" }

# ---------- 3. 把系统输入指示器改成皮皮 ----------
Write-Step "把「小狼毫」角标换成「皮皮输入法」"

$icoPath    = Join-Path $rimeDir "pipi-p.ico"
$displayName = "皮皮输入法"

if (-not (Test-Path $icoPath)) {
    Write-Warn "图标文件缺失，跳过改名（不影响输入功能）"
} else {
    $patched = 0
    $roots = @("HKLM:\SOFTWARE\Microsoft\CTF\TIP",
               "HKLM:\SOFTWARE\WOW6432Node\Microsoft\CTF\TIP")
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        foreach ($tip in (Get-ChildItem $root -ErrorAction SilentlyContinue)) {
            # TIP 根节点本身
            $tp = Get-ItemProperty $tip.PSPath -ErrorAction SilentlyContinue
            if ($tp -and $tp.IconFile -and $tp.IconFile -like "*weasel.dll*") {
                Set-ItemProperty -Path $tip.PSPath -Name "Description" -Value $displayName -Force
                Set-ItemProperty -Path $tip.PSPath -Name "IconFile"    -Value $icoPath     -Force
                Set-ItemProperty -Path $tip.PSPath -Name "IconIndex"   -Value 0            -Force
                $patched++
            }
            # LanguageProfile 下的子项
            $lpRoot = Join-Path $tip.PSPath "LanguageProfile"
            if (-not (Test-Path $lpRoot)) { continue }
            foreach ($lp in (Get-ChildItem $lpRoot -Recurse -ErrorAction SilentlyContinue)) {
                $props = Get-ItemProperty $lp.PSPath -ErrorAction SilentlyContinue
                if (-not $props) { continue }
                if ($props.IconFile -and $props.IconFile -like "*weasel.dll*") {
                    Set-ItemProperty -Path $lp.PSPath -Name "Description" -Value $displayName -Force
                    Set-ItemProperty -Path $lp.PSPath -Name "IconFile"    -Value $icoPath     -Force
                    Set-ItemProperty -Path $lp.PSPath -Name "IconIndex"   -Value 0            -Force
                    $patched++
                }
            }
        }
    }
    if ($patched -gt 0) {
        Write-OK "已改名 $patched 处注册项"
    } else {
        Write-Warn "没找到小狼毫的注册项，角标可能仍是「小狼毫」（输入功能不受影响）"
    }
    # 清掉旧版本可能留下的无效用户级覆盖
    Get-ChildItem "HKCU:\Software\Microsoft\CTF\TIP" -ErrorAction SilentlyContinue |
        Where-Object { (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).IconFile -like "*weasel.dll*" } |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

# ---------- 4. 部署配置 ----------
Write-Step "编译输入方案（第一次约 10-30 秒）"

$buildYaml = Join-Path $rimeDir "build\weasel.yaml"
$before = $null
if (Test-Path $buildYaml) { $before = (Get-Item $buildYaml).LastWriteTime }

$deployer = Join-Path $weaselDir "WeaselDeployer.exe"
$deployOK = $false
if (Test-Path $deployer) {
    try {
        $p = Start-Process -FilePath $deployer -ArgumentList "/deploy" -WorkingDirectory $weaselDir -Wait -PassThru -ErrorAction Stop
        Write-OK "部署进程结束（退出码 $($p.ExitCode)）"
    } catch {
        Write-Warn "自动部署没跑起来"
    }
    Start-Sleep -Seconds 1
    $after = $null
    if (Test-Path $buildYaml) { $after = (Get-Item $buildYaml).LastWriteTime }
    if ($after -and ($null -eq $before -or $after -gt $before)) {
        Write-OK "配置已重新编译"
        $deployOK = $true
    } elseif ($after) {
        Write-Warn "配置可能没重新编译过"
    }
} else {
    Write-Warn "找不到 WeaselDeployer.exe"
}

# ---------- 5. 收掉小狼毫自己的托盘图标 ----------
Write-Step "隐藏小狼毫自带的托盘图标"

if (Test-Path $buildYaml) {
    try {
        $txt = Get-Content $buildYaml -Raw -Encoding UTF8
        if ($txt -match "(?m)^(\s*)display_tray_icon:\s*true") {
            $txt = [regex]::Replace($txt, "(?m)^(\s*)display_tray_icon:\s*true", '$1display_tray_icon: false')
            # 必须无 BOM 写回，Rime 的 YAML 解析器不认 BOM
            [System.IO.File]::WriteAllText($buildYaml, $txt, (New-Object System.Text.UTF8Encoding($false)))
            Write-OK "已写入 display_tray_icon: false"
        } else {
            Write-OK "display_tray_icon 已是关闭状态"
        }
    } catch {
        Write-Warn "改配置失败：$($_.Exception.Message)"
    }
} else {
    Write-Warn "还没生成 build\weasel.yaml，跳过"
}

# 说明托盘最终长什么样（取决于本机装了几个输入法）
try {
    $ims = (Get-WinUserLanguageList)[0].InputMethodTips
    if ($ims.Count -gt 1) {
        Write-Warn "本机装了 $($ims.Count) 个中文输入法"
        Write-Host "     右下角会是：蓝牙 [空格] P 时钟" -ForegroundColor Gray
        Write-Host "     那格空格是 Windows 给「输入法模式」固定预留的，改配置删不掉。" -ForegroundColor Gray
        Write-Host "     想变成「只有一个皮皮 P、没有空格」：" -ForegroundColor Gray
        Write-Host "       设置 -> 时间和语言 -> 语言 -> 中文(简体) -> 选项 -> 删掉微软拼音" -ForegroundColor Gray
        Write-Host "       （想加回来：同一页面点「添加键盘」。删掉前请确认皮皮能正常打字）" -ForegroundColor Gray
    } else {
        Write-OK "只有皮皮一个输入法，右下角不会有空格"
    }
} catch { }

# ---------- 6. 重启服务 ----------
Write-Step "重启输入法服务"

Stop-Process -Name WeaselServer -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800
try {
    # 用 explorer 代启：若本脚本由 AI 助手/终端代理执行，直接 Start-Process 起的进程
    # 会挂在调用方的作业对象下，脚本一结束就被连带杀掉（表现为「打了字没反应」）。
    $serverArg = '"' + $server.FullName + '"'
    & explorer.exe $serverArg
    Start-Sleep -Seconds 3
    if (Get-Process -Name WeaselServer -ErrorAction SilentlyContinue) {
        Write-OK "服务已启动"
    } else {
        Write-Warn "服务没起来，请手动运行 $($server.FullName)"
    }
} catch {
    Write-Warn "启动失败：$($_.Exception.Message)"
}

# ---------- 7. 刷新任务栏 ----------
Write-Step "刷新任务栏（会短暂黑一下，正常）"
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
if (-not (Get-Process -Name explorer -ErrorAction SilentlyContinue)) {
    Start-Process "explorer.exe"
}
Start-Sleep -Seconds 2
Write-OK "完成"

# ---------- 完 ----------
Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkGray
Write-Host "   装好了。现在可以这样用：" -ForegroundColor White
Write-Host ""
Write-Host "   打 woyaochifan    → 1 我要吃饭   2 woyaochifan" -ForegroundColor Gray
Write-Host "   打 meeting        → 1 meeting    2 么额听" -ForegroundColor Gray
Write-Host ""
Write-Host "   空格上屏第 1 位，数字键选其他候选。" -ForegroundColor Gray
Write-Host "   如果新窗口里还不是皮皮，按 Ctrl+空格 切一下。" -ForegroundColor Gray
Write-Host "  ============================================" -ForegroundColor DarkGray
Write-Host ""

if (-not $deployOK) {
    Write-Host "  注意：配置编译这一步没确认成功。" -ForegroundColor Yellow
    Write-Host "  如果打字时字母直接进输入框、没有候选窗，" -ForegroundColor Yellow
    Write-Host "  请双击「皮皮维护.bat」→ 选 1 重新部署。" -ForegroundColor Yellow
    Write-Host ""
}

Read-Host "按回车关闭"
