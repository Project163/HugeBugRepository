#!/bin/bash

# 设置错误退出
set -e

# 进入脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found in .venv"
    exit 1
fi

# 运行生成脚本
echo "Running static site generator..."
python generate_site.py

echo "Static site generated successfully in 'site' directory."
echo "You can now push 'site' directory content to your GitHub Pages repository."
