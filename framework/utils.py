# utils.py
# (精简自 Utils.pm)

import subprocess
import os
import sys

# 从环境变量读取调试模式
DEBUG = os.environ.get('D4J_DEBUG', '0') == '1'

def exec_cmd(cmd, desc):
    """
    运行一个系统命令, 类似 Perl 脚本中的 exec_cmd。
    :param cmd: 要执行的命令字符串
    :param desc: 命令的描述
    :return: (True, stdout+stderr) or (False, stdout+stderr)
    """
    print(f"{desc:.<75} ", end="", flush=True, file=sys.stderr)
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='ignore'
        )
        
        log = result.stdout + result.stderr
            
        if result.returncode != 0:
            print("FAIL", file=sys.stderr)
            print(f"Executed command: {cmd}", file=sys.stderr)
            print(log, file=sys.stderr)
            return False, log
        else:
            print("OK", file=sys.stderr)
            if DEBUG:
                print(f"Executed command: {cmd}", file=sys.stderr)
                print(log, file=sys.stderr)
            return True, log
            
    except Exception as e:
        print("FAIL", file=sys.stderr)
        print(f"Exception while running command: {cmd}", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return False, str(e)

def read_config_file(file_path, key_separator=','):
    """
    读取 key,value 格式的文件, 用于 vcs_log_xref.py 读取 issues.txt。
    """
    config_data = {}
    if not os.path.exists(file_path):
        print(f"Cannot open config file ({file_path}): File not found!", file=sys.stderr)
        return None
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                
                if key_separator in line:
                    try:
                        key, val = line.split(key_separator, 1)
                        config_data[key.strip()] = val.strip()
                    except ValueError:
                        print(f"Skipping malformed line: {line}", file=sys.stderr)
    except IOError as e:
        print(f"Cannot open config file ({file_path}): {e}", file=sys.stderr)
        return None
        
    return config_data