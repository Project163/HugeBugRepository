#!/usr/bin/env python3
# framework/utils.py

import subprocess
import os
import sys
import requests  # (!!) 导入
import requests.adapters # (!!) 导入
from urllib.parse import urlparse, urlunparse # (!!) 导入

# Read debug flag from environment variable
DEBUG = os.environ.get('D4J_DEBUG', '0') == '1'

# (!!) NEW: Global session for HTTP requests
_session = None

def get_http_session():
    """
    Initializes and returns a reusable requests.Session.
    """
    global _session
    if _session is None:
        _session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=5)
        _session.mount('http://', adapter)
        _session.mount('https://', adapter)
        _session.headers.update({'User-Agent': 'Mozilla/5.0'})
    return _session

# (!!) NEW: 智能下载 Bug Report 的函数
def download_report_data(uri, save_to):
    """
    Downloads a specific report file from a "browse" URI.
    It intelligently converts browse URLs to raw data API URLs.
    Returns True on success, False on failure.
    """
    session = get_http_session()
    headers = {}
    api_uri = uri # 默认 API URI 就是传入的 URI
    
    try:
        # 1. 检查 JIRA (e.g., https://issues.apache.org/jira/browse/BSF-45)
        if 'issues.apache.org/jira/' in uri:
            issue_key = uri.split('/')[-1].split('?')[0] # 移除可能的查询参数
            api_uri = f"https://issues.apache.org/jira/si/jira.issueviews:issue-xml/{issue_key}/{issue_key}.xml"
            print(f"  -> [JIRA] Remapped to XML view")

        # 2. 检查 GitHub (e.g., https://github.com/google/gson/issues/2892)
        elif 'github.com/' in uri and '/issues/' in uri and 'api.github.com' not in uri:
            parts = urlparse(uri).path.split('/')
            if len(parts) >= 5:
                org = parts[1]
                repo = parts[2]
                issue_num = parts[4]
                api_uri = f"https://api.github.com/repos/{org}/{repo}/issues/{issue_num}"
                print(f"  -> [GitHub] Remapped to API view", end="")
                if os.environ.get('GH_TOKEN'):
                    headers['Authorization'] = f"token {os.environ['GH_TOKEN']}"

        # 3. 检查 Bugzilla (e.g., https://bz.apache.org/bugzilla/show_bug.cgi?id=123)
        elif 'bugzilla' in uri and 'show_bug.cgi?id=' in uri:
            # 转换为XML视图
            parsed_url = urlparse(uri)
            api_uri = urlunparse(parsed_url._replace(query=f"ctype=xml&{parsed_url.query}"))
            print(f"  -> [Bugzilla] Remapped to XML view", end="")

        # 4. 检查 SourceForge (e.g., https://sourceforge.net/p/project/bugs/123/)
        elif 'sourceforge.net/p/' in uri and '/bugs/' in uri:
            # 转换为 REST API: http://sourceforge.net/rest/p/project/bugs/123/
            api_uri = uri.replace('/p/', '/rest/p/')
            if not api_uri.endswith('/'):
                api_uri += '/'
            print(f"  -> [SourceForge] Remapped to REST API", end="")
        
        # 5. 检查 Google Code (e.g., .../issue-123.json)
        elif 'storage.googleapis.com/google-code-archive' in uri and uri.endswith('.json'):
            print(f"  -> [Google Code] Using direct JSON URL", end="")
            # api_uri is already correct
        
        else:
            print(f"  -> [Unknown] Attempting direct download", end="")

        
        response = session.get(api_uri, headers=headers, timeout=20)
        response.raise_for_status()
        
        with open(save_to, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("OK", file=sys.stderr)
        return True
    except requests.exceptions.RequestException as e:
        print("FAIL", file=sys.stderr)
        print(f"  -> Error downloading {api_uri}: {e}", file=sys.stderr)
        if os.path.exists(save_to):
            os.remove(save_to) # 移除不完整的文件
        return False
    except Exception as e:
        print("FAIL", file=sys.stderr)
        print(f"  -> An unexpected error occurred: {e}", file=sys.stderr)
        if os.path.exists(save_to):
            os.remove(save_to)
        return False


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