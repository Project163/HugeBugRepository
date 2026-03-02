#!/usr/bin/env bash

# 切换到 bugportal 项目目录
cd /home/younger/ExplainedRealBugs/bugportal || {
  echo "目录 /home/younger/ExplainedRealBugs/bugportal 不存在" >&2
  exit 1
}

# 激活虚拟环境
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
  echo "已进入 /home/younger/ExplainedRealBugs/bugportal，并激活虚拟环境 .venv"
  echo "如需启动服务，请手动运行：uvicorn app.main:app --reload --port 8000"
  echo "请在浏览器中打开：http://127.0.0.1:8000/bugs?lang=zh"
else
  echo "未找到虚拟环境 .venv，请先在 bugportal 目录下创建并安装依赖" >&2
  exit 1
fi




 
# 只负责激活虚拟环境，不自动启动 uvicorn

# 下面的代码已被移除以避免启动 uvicorn
