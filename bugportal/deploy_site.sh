#!/bin/bash
set -e

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 获取当前主仓库的 remote url
# 假设 bugportal 在仓库根目录下的子目录，或者 ExplainedRealBugs 本身就是仓库根目录
# 我们可以尝试在当前目录或上级目录找 git
REMOTE_URL=$(git config --get remote.origin.url || git -C .. config --get remote.origin.url)

if [ -z "$REMOTE_URL" ]; then
    echo "Error: Could not find git remote URL. Please run this script from within the git repository."
    exit 1
fi

echo "Target Remote Repository: $REMOTE_URL"

# 1. 生成静态文件 (这会清空 site 目录)
echo "Generating static site..."
./run_generate_static.sh

# 2. 进入 site 目录
cd site

# 3. 初始化 git 并推送
echo "Initializing git and pushing to gh-pages..."
git init
git checkout -b gh-pages
git add .
git commit -m "Update site data: $(date '+%Y-%m-%d %H:%M:%S')"
git remote add origin "$REMOTE_URL"

# 注意：这里使用 force push，因为每次都是重建仓库历史
git push -f origin gh-pages

echo "----------------------------------------"
echo "Success! The static site has been updated."
echo "Visit your page at the GitHub Pages URL."
echo "----------------------------------------"
