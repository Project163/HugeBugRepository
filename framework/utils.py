#!/usr/bin/env python3
# framework/utils.py

import subprocess
import os
import sys
import requests  
import requests.adapters 
from urllib.parse import urlparse, urlunparse 

# Read debug flag from environment variable
DEBUG = os.environ.get('D4J_DEBUG', '0') == '1'

_session = None

def get_http_session():
    """
    初始化并返回一个带有重试机制的 HTTP 会话。
    """
    global _session
    if _session is None:
        _session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=5)
        _session.mount('http://', adapter)
        _session.mount('https://', adapter)
        _session.headers.update({'User-Agent': 'Mozilla/5.0'})
    return _session


def download_report_data(uri, save_to):
    """
    从指定的 URI 下载报告数据并保存到本地文件。
    """
    session = get_http_session()
    headers = {}
    api_uri = uri
    
    try:
        # check and convert known issue tracker URLs to API/raw data URLs
        if 'issues.apache.org/jira/' in uri:
            issue_key = uri.split('/')[-1].split('?')[0] # 移除可能的查询参数
            api_uri = f"https://issues.apache.org/jira/si/jira.issueviews:issue-xml/{issue_key}/{issue_key}.xml"
            print(f"  -> [JIRA] Remapped to XML view", end="")

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

        elif 'bugzilla' in uri and 'show_bug.cgi?id=' in uri:
            parsed_url = urlparse(uri)
            api_uri = urlunparse(parsed_url._replace(query=f"ctype=xml&{parsed_url.query}"))
            print(f"  -> [Bugzilla] Remapped to XML view", end="")

        elif 'sourceforge.net/p/' in uri and '/bugs/' in uri:
            api_uri = uri.replace('/p/', '/rest/p/')
            if not api_uri.endswith('/'):
                api_uri += '/'
            print(f"  -> [SourceForge] Remapped to REST API", end="")
        
        elif 'storage.googleapis.com/google-code-archive' in uri and uri.endswith('.json'):
            print(f"  -> [Google Code] Using direct JSON URL", end="")
        
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
            os.remove(save_to) 
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
            # if output_file is specified, redirect stdout to that file
            try:
                stdout_handle = open(output_file, 'w', encoding='utf-8', errors='ignore')
                result = subprocess.run(
                    cmd_list,
                    shell=False,
                    stdout=stdout_handle, 
                    stderr=subprocess.PIPE, 
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
            # if no output_file, capture stdout and stderr normally
            result = subprocess.run(
                cmd_list,
                shell=False,
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            log = (result.stdout or "") + (result.stderr or "")
        
        # wrote log output
        if result.returncode != 0:
            print("FAIL", file=sys.stderr)
            print(f"Executed command: {cmd_list}", file=sys.stderr)
            print(log, file=sys.stderr)
            # if output_file was used, ensure partial file is removed
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
        
        # ensure file handle is closed
        if output_file and stdout_handle:
            stdout_handle.close()
        # ensure partial output file is removed
        if output_file and os.path.exists(output_file):
            try: os.remove(output_file)
            except OSError: pass
        return False, str(e)

def read_config_file(file_path, key_separator=','):
    """
    读取配置文件，返回键值对字典。
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