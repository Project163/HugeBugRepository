import argparse
import os
import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse, urlencode, quote_plus
import time

# Optional: Try importing OpenAI for LLM support
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Required packages:
# pip install requests beautifulsoup4 openai

SUPPORTED_TRACKERS = {
    'google': {
        'default_tracker_uri': 'https://storage.googleapis.com/google-code-archive/v2/code.google.com/',
        'default_query': 'label:type-defect',
        'default_limit': 1,
        'build_uri': lambda tracker, project, query, start, limit, org: f"{tracker}{quote_plus(project)}/issues-page-{start + 1}.json",
        'results': lambda content, project: [
            (issue['id'], f"https://storage.googleapis.com/google-code-archive/v2/code.google.com/{quote_plus(project)}/issues/issue-{issue['id']}.json")
            for issue in json.loads(content)['issues']
            if any(label.startswith('Type-Defect') for label in issue['labels'])
        ]
    },
    'jira': {
        'default_tracker_uri': 'https://issues.apache.org/jira/',
        'default_query': 'issuetype = Bug ORDER BY key DESC',
        'default_limit': 200,
        'build_uri': lambda tracker, project, query, start, limit, org: (
            f"{tracker}sr/jira.issueviews:searchrequest-xml/temp/SearchRequest.xml?"
            f"jqlQuery={quote_plus(f'project = \"{project}\" AND {query}')}"
            f"&tempMax={limit}&pager/start={start}"
        ),
        'results': lambda content, project: [
            (m.group(1), f"https://issues.apache.org/jira/browse/{m.group(1)}")
            for line in content.splitlines() if (m := re.search(r'^\s*<key.*?>(.*?)</key>', line))
        ]
    },
    'github': {
        'default_tracker_uri': 'https://api.github.com/graphql', 
        'default_query': 'AUTO_DETECT_BUG_LABELS',
        'default_limit': 100,
        'build_uri': lambda tracker, project, query, start, limit, org: "",
        'results': lambda content, project: [] 
    },
    'bugzilla': {
        'default_tracker_uri': 'https://bz.apache.org/bugzilla/',
        'default_query': '/buglist.cgi?',
        'default_limit': 0,
        'build_uri': lambda tracker, project, query, start, limit, org: (
            f"{tracker}buglist.cgi?bug_status=RESOLVED&order=bug_id&limit=0&"
            f"product={project}&query_format=advanced&resolution=FIXED"
        ),
        'results': lambda content, project: [
            (m.group(1), f"https://bz.apache.org/bugzilla/show_bug.cgi?id={m.group(1)}")
            for line in content.splitlines() if (m := re.search(r'^\s*<bug_id>(.*?)</bug_id>', line))
        ]
    }
}


def fetch_github_labels(owner, repo, token):
    """Fetch all labels from a GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/labels"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    all_labels = []
    page = 1
    while True:
        try:
            resp = requests.get(f"{url}?per_page=100&page={page}", headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"[Warning] Failed to fetch labels: {resp.status_code} {resp.text}", file=sys.stderr)
                break
            
            data = resp.json()
            if not data:
                break
            
            for item in data:
                if isinstance(item, dict) and 'name' in item:
                    all_labels.append(item['name'])
            
            if len(data) < 100:
                break
            page += 1
        except Exception as e:
            print(f"[Warning] Error fetching labels: {e}", file=sys.stderr)
            break
            
    # [DEBUG] Output fetched labels
    print(f"[DEBUG] Fetched Labels for {owner}/{repo}: {json.dumps(all_labels, ensure_ascii=False)}", file=sys.stderr)
    return all_labels

def get_llm_suggested_bug_labels(all_labels):
    """Use LLM to identify which labels in the list represent bugs."""
    api_key = os.getenv("SILICONCLOUD_API_KEY")
    if not api_key:
        print("[Info] SILICONCLOUD_API_KEY not set. Skipping LLM label analysis.", file=sys.stderr)
        return []
    
    if not OpenAI:
        print("[Info] 'openai' package not installed. Skipping LLM label analysis.", file=sys.stderr)
        return []

    client = OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")

    system_prompt = """
    You are a Software Repository Mining Expert.
    Your task is to identify labels that specifically represent "software defects", "bugs", "errors", or "crashes".
    
    Strict Rules:
    1. Input: A JSON list of label names from a GitHub repository.
    2. Output: A JSON OBJECT with a single key "labels" containing the list of bug-related labels.
       Example format: {"labels": ["bug", "defect"]}
    3. NEGATIVE CONSTRAINTS (Crucial):
       - DO NOT include "enhancement", "feature", "documentation", "question", "wontfix", "duplicate", "good first issue", "help wanted".
       - DO NOT include status labels like "stale", "invalid", "incomplete", "cant-reproduce". 
       - DO NOT include ambiguous labels like "triage", "investigation" unless they explicitly say "bug".
       - DO NOT include "test" (unless it is "failing test") or "refactor".
    4. POSITIVE PATTERNS:
       - Look for: "bug", "defect", "kind/bug", "type: bug", "category: error", "C-bug", "A-crash", "T-Defect".
    """

    user_prompt = f"""
    Here are the labels found in the repository:
    {json.dumps(all_labels)}
    
    Return the JSON list of bug-related labels:
    """

    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        content = response.choices[0].message.content

        # [DEBUG] Output LLM raw response
        print(f"[DEBUG] LLM Response Content:\n{content}", file=sys.stderr)

        result = json.loads(content)
        
        # Priority 1: Check for the 'labels' key (Best Practice)
        if isinstance(result, dict) and "labels" in result:
             if isinstance(result["labels"], list):
                 return result["labels"]
        
        # Priority 2: Fallback - Check if values are lists (in case LLM uses a different key)
        if isinstance(result, dict):
            for val in result.values():
                if isinstance(val, list):
                    return val
        
        # Priority 3: Direct list (unlikely with json_object mode but possible in some API variants)
        if isinstance(result, list):
            return result
        
        return []
    except Exception as e:
        print(f"[Warning] LLM Label Analysis failed: {e}", file=sys.stderr)
        return []


def get_bugzilla_id_list(uri, project_name, session):
    try:
        response = session.get(uri, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        body = soup.find('div', id='bugzilla-body')
        if not body:
            return []
        
        buttons_div = body.find('span', class_='bz_query_buttons')
        if not buttons_div:
            return []
            
        hidden_input = buttons_div.find('input', {'type': 'hidden'})
        if not hidden_input or 'value' not in hidden_input.attrs:
            return []
            
        return hidden_input['value'].split(',')
    except requests.exceptions.RequestException as e:
        print(f"Error parsing Bugzilla list {uri}: {e}", file=sys.stderr)
        return []

def main():
    parser = argparse.ArgumentParser(description="Download issues from an issue tracker.")
    parser.add_argument('-g', dest='tracker_name', required=True, help="Tracker name (jira, github, etc.)")
    parser.add_argument('-t', dest='tracker_project_id', required=True, help="Project ID used on the tracker (e.g., LANG)")
    parser.add_argument('-o', dest='output_dir', required=True, help="Output directory for fetched issues (cache)")
    parser.add_argument('-f', dest='issues_file', required=True, help="Output file for issue id,url list (e.g., issues.txt)")
    parser.add_argument('-z', dest='organization_id', help="Organization ID (for GitHub)")
    parser.add_argument('-q', dest='query', help="Custom query")
    parser.add_argument('-u', dest='tracker_uri', help="Custom tracker URI")
    parser.add_argument('-l', dest='limit', type=int, help="Fetching limit per page")
    parser.add_argument('-D', dest='debug', action='store_true', help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.tracker_name not in SUPPORTED_TRACKERS:
        print(f"Error: Invalid tracker-name! Expected one of: {', '.join(SUPPORTED_TRACKERS.keys())}", file=sys.stderr)
        sys.exit(1)
        
    tracker = SUPPORTED_TRACKERS[args.tracker_name]
    
    tracker_id = args.tracker_project_id
    output_dir = args.output_dir
    issues_file = args.issues_file
    organization_id = args.organization_id
    query = args.query
    tracker_uri = args.tracker_uri or tracker['default_tracker_uri']
    limit = args.limit or tracker['default_limit']
    debug = args.debug

    os.makedirs(output_dir, exist_ok=True)

    # Set up a session with retries
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=5)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    print("----------------------------------------------")

    if args.tracker_name == 'github':
        print(f"Using GitHub GraphQL strategy (Issues API) for {tracker_id}.")
        sys.stdout.flush()
        

        print("  -> Preparing GraphQL API access...")
        # 1. Get GH_TOKEN
        gh_token = os.environ.get('GH_TOKEN')
        if not gh_token:
            print("[Error]: GH_TOKEN environment variable must be set for GraphQL API.", file=sys.stderr)
            sys.stderr.flush()
            sys.exit(1)
        
        headers = {
            'Authorization': f'token {gh_token}',
            'User-Agent': 'Mozilla/5.0'
        }
        
        graphql_endpoint = "https://api.github.com/graphql"

        # 2. Extract owner and repo name
        try:
            if '/' in tracker_id:
                owner, name = tracker_id.split('/', 1)
            elif organization_id:
                owner = organization_id
                name = tracker_id
            else:
                raise ValueError(f"[Error]: GitHub project ID '{tracker_id}' must be 'owner/repo' or require -z <org>.")
        except ValueError as e:
            print(f"[Error]: Error parsing GitHub project ID: {e}", file=sys.stderr)
            sys.stderr.flush()
            sys.exit(1)

        # 3. Determine Labels to Search (LLM Magic Here)
        labels_to_search = []
        
        # Use default logic if query is None or explicitly set to AUTO_DETECT
        should_auto_detect = (query is None) or (query == 'AUTO_DETECT_BUG_LABELS')
        
        if should_auto_detect:
            print(f"  -> Attempting to auto-detect bug labels for {owner}/{name}...")
            
            # A. Fetch all labels
            repo_labels = fetch_github_labels(owner, name, gh_token)
            
            if repo_labels:
                if debug: print(f"  -> Found {len(repo_labels)} labels in repo.")
                
                # B. Analyze with LLM
                suggested_labels = get_llm_suggested_bug_labels(repo_labels)
                
                if suggested_labels:
                    labels_to_search = suggested_labels
                    print(f"  -> [LLM] Identified bug labels: {labels_to_search}")
                else:
                    print("  -> [LLM] Could not identify specific bug labels (or LLM unavailable). Fallback to defaults.")
                    labels_to_search = ['bug', 'defect']
            else:
                print("  -> Could not fetch labels from repo. Fallback to defaults.")
                labels_to_search = ['bug', 'defect']
                
        else:
            # Manual query provided (e.g., via command line)
            if query.startswith('label='):
                labels_to_search = query.split('=', 1)[1].split(',')
            else:
                labels_to_search = query.split(',')

        if not labels_to_search:
            print(f"[Error]: No labels to search. Query: {query}", file=sys.stderr)
            sys.exit(1)

        if debug: print(f"GraphQL will run enumerations for labels: {labels_to_search}")

        # 4. Define GraphQL Repository.Issues API query template
        graphql_query_template = """
        query($owner: String!, $name: String!, $labels: [String!], $cursor: String) {
          repository(owner: $owner, name: $name) {
            issues(first: 100, after: $cursor, labels: $labels, states: [OPEN, CLOSED]) {
              totalCount
              pageInfo {
                endCursor
                hasNextPage
              }
              nodes {
                number
                url
              }
            }
          }
        }
        """

        # 5. Run GraphQL queries per label
        all_results_set = set() # set to avoid duplicates
        
        # Make sure issues_file is empty
        try:
            open(issues_file, 'w').close() 
        except IOError as e:
            print(f"[Error]: Cannot clear issues file {issues_file}: {e}", file=sys.stderr)
            sys.exit(1)

        for label in labels_to_search:
            label_name = label.strip()
            if not label_name: continue
            
            if debug: print(f"--- Starting GraphQL Enumeration (Label: {label_name}) ---")
            sys.stdout.flush()
            
            cursor = None
            hasNextPage = True
            page_count = 1

            while hasNextPage:
                variables = {
                    "owner": owner,
                    "name": name,
                    "labels": [label_name], # Query labels as list
                    "cursor": cursor
                }
                payload = {
                    "query": graphql_query_template,
                    "variables": variables
                }
                
                try:
                    # Use session.post with a longer timeout
                    response = session.post(graphql_endpoint, headers=headers, json=payload, timeout=45)
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'errors' in data:
                        print(f"GraphQL Error: {data['errors']}", file=sys.stderr)
                        sys.stderr.flush()
                        break
                        
                    issues_data = data.get('data', {}).get('repository', {}).get('issues', {})
                    pageInfo = issues_data.get('pageInfo', {})
                    
                    hasNextPage = pageInfo.get('hasNextPage', False)
                    cursor = pageInfo.get('endCursor', None)
                    nodes = issues_data.get('nodes', [])
                    
                    # New results from this page
                    page_results = []
                    for node in nodes:
                        if node:
                            issue_tuple = (node['number'], node['url'])
                            if issue_tuple not in all_results_set:
                                all_results_set.add(issue_tuple)
                                page_results.append(issue_tuple)

                    # Append new results from this page to file
                    if page_results:
                        try:
                            with open(issues_file, 'a', encoding='utf-8') as f:
                                for issue_id, issue_url in page_results:
                                    f.write(f"{issue_id},{issue_url}\n")
                        except IOError as e:
                            print(f"[Error]: Cannot write to {issues_file}: {e}", file=sys.stderr)
                            sys.exit(1) 

                    page_count += 1
                    time.sleep(0.5) # Slight delay to be nice

                except requests.exceptions.RequestException as e:
                    print(f"[Error]: During GraphQL request: {e}. Retrying...", file=sys.stderr)
                    time.sleep(5) 
                except KeyboardInterrupt:
                    print("[Error]: GraphQL download interrupted.")
                    sys.exit(1)

        print(f"[Info]: GitHub GraphQL processing complete. Wrote {len(all_results_set)} total unique issues to {issues_file}.")
        sys.exit(0)
    
    start = 0

    # Bugzilla and other logic remains same...
    if args.tracker_name == 'bugzilla':
        # ... (Original Bugzilla logic preserved) ...
        list_uri = tracker['build_uri'](tracker_uri, tracker_id, query or tracker['default_query'], 0, 0, organization_id)
        if debug: print(f"Fetching Bugzilla ID list from: {list_uri}")
        id_list = get_bugzilla_id_list(list_uri, tracker_id, session)
        if not id_list:
            print("[Warning]: No Bugzilla IDs found.", file=sys.stderr)
            sys.exit(0)
            
        if debug: print(f"Found {len(id_list)} Bugzilla IDs.")
        
        all_results = []
        for i in range(0, len(id_list), 50):
            chunk = id_list[i:i+50]
            ids_query = "&".join([f"id={bid}" for bid in chunk])
            xml_uri = f"https://bz.apache.org/bugzilla/show_bug.cgi?ctype=xml&{ids_query}"
            
            if debug: print(f"Downloading {xml_uri}")

            xml_content = None
            max_retries = 5
            retry_delay = 10

            for attempt in range(max_retries):
                try:
                    response = session.get(xml_uri, headers={}, timeout=90) 
                    response.raise_for_status() 
                    xml_content = response.text 
                    break 
                except requests.exceptions.RequestException as e:
                    time.sleep(retry_delay)
                    retry_delay *= 2

            if not xml_content:
                continue
            
            try:
                results = tracker['results'](xml_content, tracker_id)
                all_results.extend(results)
            except Exception as e:
                 if debug: print(f"Failed to parse content from {xml_uri}: {e}.")
            
        try:
            with open(issues_file, 'w', encoding='utf-8') as f:
                for issue_id, issue_url in all_results:
                    f.write(f"{issue_id},{issue_url}\n")
        except IOError as e:
            print(f"Error writing to {issues_file}: {e}", file=sys.stderr)
            
        print(f"Bugzilla processing complete. Wrote {len(all_results)} issues.")
        sys.exit(0)

    # Generic loop for others (Google Code, Jira)
    current_query = query or tracker['default_query']
    give_up = False 
    while True:
        uri = tracker['build_uri'](tracker_uri, tracker_id, current_query, start, limit, organization_id)
        if debug: print(f"Downloading (in-memory) {uri}")
        
        content = None
        max_retries = 5
        retry_delay = 10 
        
        for attempt in range(max_retries):
            try:
                response = session.get(uri, headers={}, timeout=90) 
                response.raise_for_status() 
                content = response.text
                break 
            except requests.exceptions.RequestException as e:
                if attempt + 1 == max_retries:
                    if give_up: break
                    else: sys.exit(1)
                time.sleep(retry_delay)
                retry_delay *= 2

        if content is None:
             if give_up: break
             else: sys.exit(1)

        if not content: break
        
        try:
            results = tracker['results'](content, tracker_id)
        except Exception:
            results = []

        if results:
            with open(issues_file, 'a', encoding='utf-8') as f:
                for issue_id, issue_url in results:
                    f.write(f"{issue_id},{issue_url}\n")
            
            if args.tracker_name == 'google': give_up = True
            start += limit 
        else:
            break 

if __name__ == "__main__":
    main()