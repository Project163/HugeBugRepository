#!/usr/bin/env bash

# 切换到 ExplainedRealBugs 项目根目录
cd /home/younger/ExplainedRealBugs || {
  echo "目录 /home/younger/ExplainedRealBugs 不存在" >&2
  exit 1
}

# 激活虚拟环境
if [ -f .venv/bin/activate ]; then
  # 注意：在脚本内部 source 只对当前脚本进程有效
  # 要让当前终端生效，请使用：source activate_explainedrealbugs.sh
  source .venv/bin/activate
  echo "已进入 /home/younger/ExplainedRealBugs 并激活虚拟环境 .venv"
  # 保留一个交互式 shell（如果你是直接 ./activate_explainedrealbugs.sh 运行，可选）
  $SHELL
else
  echo "未找到虚拟环境 .venv，请先在项目根目录创建：python3 -m venv .venv" >&2
  exit 1
fi
