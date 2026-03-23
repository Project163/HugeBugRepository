#!/bin/bash
set -e

# 获取脚本所在目录，确保在正确路径下运行
cd "$(dirname "$0")"

echo "========================================"
echo "Starting Deployment Process"
echo "========================================"

# 1. 重新生成静态网站
echo "[1/3] Generating static site files..."
# 确保有执行权限
chmod +x run_generate_static.sh
./run_generate_static.sh

# 2. 准备 Git 发布
echo "[2/3] Preparing git repository in site/ folder..."
cd site

# 初始化新的 Git 仓库（因为 site 目录每次生成都会被重建）
git init
git checkout -b gh-pages

# 添加所有文件
git add .
git commit -m "Auto-deploy: Update site content $(date '+%Y-%m-%d %H:%M:%S')"

# 3. 推送到 GitHub
echo "[3/3] Pushing to GitHub..."

# 设置远程仓库地址
REPO_URL="https://github.com/Project163/ExplainedRealBugs.git"

# 强制推送到远程的 gh-pages 分支
# 注意：这会覆盖远程 gh-pages 分支的历史，对于发布用途通常是可以接受的
git push -f "$REPO_URL" gh-pages

echo "========================================"
echo "Deployment Successfully Completed!"
echo "You can view your site at: https://Project163.github.io/ExplainedRealBugs/"
echo "========================================"
