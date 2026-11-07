# 安装/卸载「薪资打卡器」开机自启（当前用户）
param([switch]$Uninstall)
$Name = 'SalaryPunch'
$Start = 'D:\ieswork\salary-punch\start.bat'
$Run = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
if ($Uninstall) {
  Remove-ItemProperty -Path $Run -Name $Name -ErrorAction SilentlyContinue
  Write-Host '已取消开机自启'
} else {
  Set-ItemProperty -Path $Run -Name $Name -Value "`"$Start`""
  Write-Host "已写入开机自启: $Start"
}
