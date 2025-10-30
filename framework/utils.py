# utils.py
import subprocess
import os
import sys

# Read debug flag from environment variable
DEBUG = os.environ.get('D4J_DEBUG', '0') == '1'

def exec_cmd(cmd_list, desc, output_file=None):
    """
    (!!) cmd_list 现在必须是一个列表 (e.g., ['git', 'log'])
    (!!) 添加了 output_file 参数用于重定向 stdout
    """
    
    print(f"{desc:.<75} ", end="", flush=True, file=sys.stderr)
    
    if not isinstance(cmd_list, list):
        print("FAIL", file=sys.stderr)
        print(f"Internal Error: exec_cmd now requires 'cmd' to be a list.", file=sys.stderr)
        return False, "exec_cmd requires list"
        
    try:
        stdout_handle = None
        
        if output_file:
            # --- (!!) 逻辑 1: output_file 已提供 ---
            # 我们将 stdout 重定向到文件, 并捕获 stderr
            try:
                stdout_handle = open(output_file, 'w', encoding='utf-8', errors='ignore')
                result = subprocess.run(
                    cmd_list,
                    shell=False,
                    stdout=stdout_handle,  # (!!) stdout 写入文件
                    stderr=subprocess.PIPE,  # (!!) stderr 正常捕获
                    text=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                log = f"(stdout written to {output_file})\n" + (result.stderr or "")
            except IOError as e:
                print(f"FAIL (Could not open output file: {e})", file=sys.stderr)
                return False, str(e)
            finally:
                if stdout_handle:
                    stdout_handle.close()
        
        else:
            # --- (!!) 逻辑 2: output_file 为 None ---
            # 我们使用 capture_output 来捕获 stdout 和 stderr
            result = subprocess.run(
                cmd_list,
                shell=False,
                capture_output=True, # (!!) 关键: 让 subprocess 自己处理捕获
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            log = (result.stdout or "") + (result.stderr or "")
        
        # --- (!!) 统一的错误处理 ---
        if result.returncode != 0:
            print("FAIL", file=sys.stderr)
            print(f"Executed command: {cmd_list}", file=sys.stderr)
            print(log, file=sys.stderr)
            # 如果失败, 删除可能不完整的输出文件
            if output_file and os.path.exists(output_file):
                try: os.remove(output_file)
                except OSError: pass
            return False, log
        else:
            print("OK", file=sys.stderr)
            if DEBUG:
                print(f"Executed command: {cmd_list}", file=sys.stderr)
                print(log, file=sys.stderr)
            return True, log
            
    except Exception as e:
        print("FAIL", file=sys.stderr)
        print(f"Exception while running command: {cmd_list}", file=sys.stderr)
        print(str(e), file=sys.stderr)
        
        # (!!) 确保句柄被关闭 (如果存在)
        if output_file and stdout_handle:
            stdout_handle.close()
        # (!!) 确保部分写入的文件被删除
        if output_file and os.path.exists(output_file):
            try: os.remove(output_file)
            except OSError: pass
        return False, str(e)

def read_config_file(file_path, key_separator=','):
    """
    Read key,value format files for vcs_log_xref.py to read issues.txt.
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