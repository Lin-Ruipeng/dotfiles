<#
    Microsoft.PowerShell_profile.ps1
    宿主 : PowerShell 7（pwsh），对当前用户、当前宿主生效
    部署 : 复制到 $PROFILE.CurrentUserCurrentHost（通常是 ~/Documents/PowerShell/）

    作用 : 让每个 PowerShell 7 会话默认使用 UTF-8 字符编码。

    日常用法:
        utf8            # 切回 UTF-8（默认）
        gbk             # 切回 GBK(936)，跑 ipconfig / net / systeminfo 等中文原生命令时用
        Get-EncodingInfo  # 查看当前四层编码状态

    撤销 : 删掉部署后的 $PROFILE 文件即恢复系统默认；或把下面的 $DefaultEncoding 改成 'GBK'。
#>

# ============ 默认编码档位：'UTF8' 或 'GBK' ============
$DefaultEncoding = 'UTF8'

<#
    为什么需要两个档位？
    中文版 Windows 的 ipconfig / net / systeminfo / wmic 等原生工具
    硬编码按 GBK(936) 输出字节。把控制台解码器设成 UTF-8 后，
    这些工具的中文会变成乱码。所以日常默认 UTF-8，
    遇到中文原生命令时用 gbk 临时切回去。
#>

function Set-ConsoleEncoding {
    [CmdletBinding()]
    param(
        [ValidateSet('UTF8', 'GBK')]
        [string]$Mode = 'UTF8'
    )

    switch ($Mode) {
        'UTF8' {
            # 无 BOM 的 UTF-8
            $enc = [System.Text.UTF8Encoding]::new($false)
            $cp = 65001
        }
        'GBK' {
            $enc = [System.Text.Encoding]::GetEncoding(936)
            $cp = 936
        }
    }

    # 三处一起改才一致：
    #   InputEncoding  -> 你从键盘/管道输入给 PowerShell 的字节
    #   OutputEncoding -> PowerShell 从原生程序读取输出时用的解码器
    #   $OutputEncoding-> PowerShell 把数据通过管道喂给原生程序时用的编码
    [Console]::InputEncoding = $enc
    [Console]::OutputEncoding = $enc
    $global:OutputEncoding = $enc

    # 同步 Windows 控制台的代码页（chcp.com 是外部命令，会打印一行提示，故丢弃）
    if ($IsWindows) {
        chcp $cp 2>&1 | Out-Null
    }
}

function Use-Utf8 {
    [CmdletBinding()]
    param()
    Set-ConsoleEncoding -Mode UTF8
}

function Use-Gbk {
    [CmdletBinding()]
    param()
    Set-ConsoleEncoding -Mode GBK
}

function Get-EncodingInfo {
    [CmdletBinding()]
    param()
    [pscustomobject]@{
        'chcp 代码页'          = ((chcp) -join '').Trim() -replace '.*?(\d+)\s*$', '$1'
        'Console.InputEncoding' = "$([Console]::InputEncoding.CodePage) / $([Console]::InputEncoding.EncodingName)"
        'Console.OutputEncoding' = "$([Console]::OutputEncoding.CodePage) / $([Console]::OutputEncoding.EncodingName)"
        '$OutputEncoding'       = "$($OutputEncoding.CodePage) / $($OutputEncoding.EncodingName)"
    } | Format-List
}

Set-Alias -Name utf8 -Value Use-Utf8 -Force
Set-Alias -Name gbk -Value Use-Gbk -Force

# ============ 让 PowerShell 自身的文件写入默认 UTF-8 无 BOM ============
# PowerShell 7 本来就是 utf8NoBOM，这里只是显式固定，防止被其它脚本改掉。
# 注意：PS 5.1 不认识 'utf8NoBOM' 这个值，所以不要把这行抄到 5.1 的 profile。
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8NoBOM'
$PSDefaultParameterValues['Set-Content:Encoding'] = 'utf8NoBOM'
$PSDefaultParameterValues['Add-Content:Encoding'] = 'utf8NoBOM'

# ============ 应用默认档位 ============
Set-ConsoleEncoding -Mode $DefaultEncoding
