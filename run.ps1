# run.ps1
# EuroGoal Predictor - 一键启动脚本 (FastAPI + React 整合版)

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   EuroGoal Predictor v3.0 (布莱顿量化版)   " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查前端静态编译资源是否已生成
$FrontendDist = Join-Path $PSScriptRoot "frontend\dist"
if (-not (Test-Path $FrontendDist)) {
    Write-Host "⚠️  未检测到前端编译资源 (frontend/dist)。正在执行构建..." -ForegroundColor Yellow
    Set-Location (Join-Path $PSScriptRoot "frontend")
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 前端编译失败，请检查前端依赖安装情况。" -ForegroundColor Red
        Exit
    }
    Set-Location $PSScriptRoot
    Write-Host "✅ 前端编译成功！" -ForegroundColor Green
} else {
    Write-Host "💡 检测到已有的前端静态文件，将直接由 FastAPI 后端托管。" -ForegroundColor Gray
    Write-Host "💡 如果您修改了前端代码，请在 frontend 目录下运行 'npm run build' 重新编译。" -ForegroundColor Gray
}

Write-Host ""

# 1.5. Check for .env file
$EnvFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "⚠️  未检测到 .env 文件。将使用免费 CSV 数据源加载历史数据。" -ForegroundColor Yellow
    Write-Host "💡 如需获取未来赛程，请在项目根目录创建 .env 文件并添加:" -ForegroundColor Gray
    Write-Host "   FOOTBALL_DATA_API_KEY=your_key_here" -ForegroundColor Gray
    Write-Host "💡 免费注册: https://www.football-data.org/" -ForegroundColor Gray
} else {
    Write-Host "✅ 检测到 .env 配置文件。" -ForegroundColor Green
}
Write-Host ""

Write-Host "🚀 正在启动 FastAPI 后端服务..." -ForegroundColor Cyan

# 2. 启动后台线程：等待 2 秒后端启动完成后，自动用系统默认浏览器打开网页
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Write-Host "👉 正在打开默认浏览器访问应用网页..." -ForegroundColor Green
    Start-Process "http://127.0.0.1:8000"
} | Out-Null

# 3. 在当前命令行前台运行后端服务器，方便查看实时日志，按 Ctrl+C 可停止运行
Set-Location (Join-Path $PSScriptRoot "backend")

# 检查是否安装了 python 依赖
try {
    Write-Host "📦 正在检查并安装 Python 依赖..." -ForegroundColor Cyan
    pip install -r requirements.txt -q
    # 运行 uvicorn
    uvicorn app.main:app --host 127.0.0.1 --port 8000
} catch {
    Write-Host "❌ 启动失败。请确保已安装 Python，激活了虚拟环境并运行过 'pip install -r requirements.txt'。" -ForegroundColor Red
} finally {
    Set-Location $PSScriptRoot
}
