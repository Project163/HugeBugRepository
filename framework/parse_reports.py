import os
import json
import argparse
from bs4 import BeautifulSoup
import re

# ==========================================
# Configuration & Constants
# ==========================================

# 社交噪音/无意义短语 (Stop Phrases)
LOW_VALUE_PHRASES = [
    "thanks", "thank you", "thx", "lgtm", "+1", "bump", 
    "great work", "awesome", "sent from my", "dupe", "duplicate"
]

# 高价值关键词 (即使短也保留)
HIGH_VALUE_KEYWORDS = [
    "fix", "patch", "bisect", "regression", "workaround", 
    "repro", "crash", "panic", "segfault", "assert", 
    "exception", "error", "fail", "root cause", "caused by"
]

class TextCleaner:
    @staticmethod
    def normalize_technical_data(text):
        """
        归一化技术数据，将高熵字符串替换为通用占位符
        """
        if not text: return ""
        # 1. 归一化指针/内存地址
        text = re.sub(r'\b0x[0-9a-fA-F]{4,}\b', '<PTR>', text)
        # 2. 归一化长的 Hex 字符串
        text = re.sub(r'\b[0-9a-fA-F]{16,}\b', '<HASH>', text)
        # 3. 归一化 IPv4 地址
        text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', text)
        return text

    @staticmethod
    def simplify_links(text):
        """
        智能简化链接和图片
        """
        if not text: return ""

        # 1. 图片: ![alt](url) -> [Image: alt]
        def img_repl(match):
            alt = match.group(1).strip()
            return f"[Image: {alt}]" if alt else "[Image]"
        text = re.sub(r'!\[(.*?)\]\(.*?\)', img_repl, text)

        # 2. 链接: [text](url) -> [Link: text]
        def link_repl(match):
            anchor_text = match.group(1).strip()
            url = match.group(2).strip()
            
            # 如果 anchor text 本身就是一个长 URL，直接缩短为 [Link]
            if anchor_text.startswith('http') and len(anchor_text) > 20:
                return "[Link]"
            
            # 保留 Issue 引用 #123
            if anchor_text.startswith('#') and len(anchor_text) < 10:
                return f"[Ref: {anchor_text}]"
                
            return f"[Link: {anchor_text}]" if anchor_text else "[Link]"
            
        text = re.sub(r'\[(.*?)\]\((.*?)\)', link_repl, text)

        # 3. 裸 URL
        text = re.sub(r'(?<![\[\(])https?://\S+', '[URL]', text)

        return text

    @staticmethod
    def remove_quotes(text):
        if not text: return ""
        lines = [line for line in text.split('\n') if not line.strip().startswith('>')]
        return '\n'.join(lines)

    @staticmethod
    def truncate_code_blocks(text, max_lines=8):
        if not text: return ""
        def replacement(match):
            content = match.group(1)
            lines = content.strip().split('\n')
            if len(lines) > max_lines:
                head = '\n'.join(lines[:5]) 
                tail = '\n'.join(lines[-2:])
                return f"```\n{head}\n... [Log Snipped] ...\n{tail}\n```"
            return match.group(0)
        return re.sub(r'```(.*?)```', replacement, text, flags=re.DOTALL)

    @staticmethod
    def clean(text):
        if not text: return ""
        text = TextCleaner.truncate_code_blocks(text)
        text = TextCleaner.remove_quotes(text)
        text = TextCleaner.simplify_links(text)
        text = TextCleaner.normalize_technical_data(text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

def is_useful_comment(text):
    """
    启发式过滤器
    """
    clean_t = text.lower().strip()
    if any(kw in clean_t for kw in HIGH_VALUE_KEYWORDS):
        return True
    if len(clean_t) < 60 and any(p in clean_t for p in LOW_VALUE_PHRASES):
        return False
    return len(clean_t) > 20

# ==========================================
# Parsing Logic
# ==========================================

def parse_jira_xml(xml_content):
    try:
        soup = BeautifulSoup(xml_content, 'xml')
        title_node = soup.find('summary')
        title = TextCleaner.clean(title_node.get_text()) if title_node else "No Title"
        desc_node = soup.find('description')
        description = TextCleaner.clean(desc_node.get_text()) if desc_node else ""
        comments = []
        for comment in soup.find_all('comment'):
            raw_body = comment.get_text()
            cleaned = TextCleaner.clean(raw_body)
            if cleaned and is_useful_comment(cleaned):
                comments.append(cleaned)
        return format_for_llm(title, description, comments)
    except Exception as e:
        print(f"[Warning]: Failed to parse Jira XML: {e}")
        return None

def parse_github_json(report_json, timeline_json):
    try:
        title = TextCleaner.clean(report_json.get('title'))
        description = TextCleaner.clean(report_json.get('body'))
        comments = []
        if timeline_json:
            for event in timeline_json:
                if event.get('event') == 'commented' and event.get('body'):
                    raw_body = event['body']
                    cleaned = TextCleaner.clean(raw_body)
                    user = event.get('user', {}).get('login', '').lower()
                    if 'bot' in user and 'fail' not in cleaned.lower():
                        continue
                    if cleaned and is_useful_comment(cleaned):
                        comments.append(cleaned)
        return format_for_llm(title, description, comments)
    except Exception as e:
        print(f"[Warning]: Failed to parse GitHub JSON: {e}")
        return None

def parse_google_json(report_json):
    try:
        title = TextCleaner.clean(report_json.get('summary'))
        all_comments = report_json.get('comments', [])
        description = ""
        discussion_comments = []
        if all_comments:
            description = TextCleaner.clean(all_comments[0].get('content'))
            if len(all_comments) > 1:
                for comment in all_comments[1:]:
                    raw_body = comment.get('content')
                    cleaned = TextCleaner.clean(raw_body)
                    if cleaned and is_useful_comment(cleaned):
                        discussion_comments.append(cleaned)
        return format_for_llm(title, description, discussion_comments)
    except Exception as e:
        print(f"[Warning]: Failed to parse Google JSON: {e}")
        return None

def format_for_llm(title, description, comments):
    """
    构建 LLM 输入，应用 Head-2 + Tail-2 策略
    """
    # 限制 Description 的长度
    if len(description) > 2000:
        description = description[:2000] + "\n...[Description Truncated]..."
        
    llm_text = f"[Title]: {title}\n"
    llm_text += f"[Symptom]:\n{description}\n"
    
    if comments:
        # --- 核心修改：Head-2 + Tail-2 截断策略 ---
        if len(comments) > 4:
            # 保留前2条（症状澄清/初步尝试）
            head = comments[:2]
            # 保留后2条（最终结论/PR链接/修复确认）
            tail = comments[-2:]
            
            # 使用特定标记明确告知 LLM 中间有省略
            selected_comments = head + ["... [Middle Discussions Snipped for Brevity] ..."] + tail
        else:
            selected_comments = comments
        # ----------------------------------------

        discussion_text = "\n- ".join(selected_comments)
        
        # 安全网：如果剩下的这4条依然极其长，再做字符级截断
        if len(discussion_text) > 3000:
            head_text = discussion_text[:1500]
            tail_text = discussion_text[-1500:]
            discussion_text = f"{head_text}\n...[Text Truncated]...\n{tail_text}"
            
        llm_text += f"\n[Context/Logs]:\n- {discussion_text}"
        
    return llm_text

def main(bug_mining_root, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    processed_count = 0
    with open(output_file, 'w', encoding='utf-8') as f_out:
        project_ids = sorted([d for d in os.listdir(bug_mining_root) if os.path.isdir(os.path.join(bug_mining_root, d))])
        for project_id in project_ids:
            project_dir = os.path.join(bug_mining_root, project_id)
            reports_dir = os.path.join(project_dir, 'reports')
            if not os.path.isdir(reports_dir):
                continue
            print(f"--- Processing Project: {project_id} ---")
            files = os.listdir(reports_dir)
            report_files = {} 
            for file in files:
                match = re.match(r'(\d+)(\.timeline)?\.(json|xml)', file)
                if not match: continue
                bug_id = match.group(1)
                is_timeline = bool(match.group(2))
                ext = match.group(3)
                if bug_id not in report_files:
                    report_files[bug_id] = {'report': None, 'timeline': None, 'ext': None}
                if is_timeline:
                    report_files[bug_id]['timeline'] = os.path.join(reports_dir, file)
                else:
                    report_files[bug_id]['report'] = os.path.join(reports_dir, file)
                    report_files[bug_id]['ext'] = ext

            for bug_id in sorted(report_files.keys(), key=int):
                paths = report_files[bug_id]
                if not paths['report']: continue
                llm_input_text = None
                source_type = "unknown"
                try:
                    if paths['ext'] == 'xml':
                        source_type = "jira"
                        with open(paths['report'], 'r', encoding='utf-8') as f:
                            llm_input_text = parse_jira_xml(f.read())
                    elif paths['ext'] == 'json':
                        with open(paths['report'], 'r', encoding='utf-8') as f_rep:
                            report_data = json.load(f_rep)
                        if paths['timeline']: 
                            source_type = "github"
                            timeline_data = None
                            with open(paths['timeline'], 'r', encoding='utf-8') as f_time:
                                timeline_data = json.load(f_time)
                            llm_input_text = parse_github_json(report_data, timeline_data)
                        else:
                            source_type = "google"
                            llm_input_text = parse_google_json(report_data)
                    if llm_input_text:
                        output_record = {
                            "project_id": project_id,
                            "bug_id": bug_id,
                            "source_type": source_type,
                            "llm_input_text": llm_input_text
                        }
                        f_out.write(json.dumps(output_record) + '\n')
                        processed_count += 1
                except Exception as e:
                    print(f"[Error] Failed processing {project_id}/{bug_id} ({paths['report']}): {e}")

    print(f"\n=================================================")
    print(f"Parsing complete. Processed {processed_count} reports.")
    print(f"Output saved to: {output_file}")
    print(f"=================================================")

if __name__ == "__main__":
    DEFAULT_BUG_MINING_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug-mining'))
    DEFAULT_OUTPUT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bug_classification', 'parsed_data.jsonl'))

    parser = argparse.ArgumentParser(description="Parse bug reports into a clean JSONL format for LLM classification.")
    parser.add_argument('-i', '--input_dir', default=DEFAULT_BUG_MINING_DIR)
    parser.add_argument('-o', '--output_file', default=DEFAULT_OUTPUT_FILE)
    args = parser.parse_args()

    main(args.input_dir, args.output_file)