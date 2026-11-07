from pathlib import Path
p = Path(r"D:/ieswork/salary-punch/build_exe.ps1")
t = p.read_text(encoding="utf-8-sig")
old = "Where-Object { $_.CommandLine -and ($_.CommandLine -match 'salary-punch|SalaryPunch') }"
new = (
    "Where-Object { $_.CommandLine -and "
    "(($_.Name -eq 'SalaryPunch.exe') -or "
    "($_.CommandLine -match 'salary-punch\\\\run\\.py|SalaryPunch\\.exe')) }"
)
if old not in t:
    print("pattern missing")
    for line in t.splitlines():
        if "CommandLine" in line or "Stop-Process" in line:
            print(line)
else:
    p.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("fixed build_exe.ps1")
