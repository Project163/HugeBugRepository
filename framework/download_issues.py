import argparse
import os
import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse, urlencode, quote_plus

# Required packages:
# pip install requests beautifulsoup4

SUPPORTED_TRACKERS = {
    'google': {
        'default_tracker_uri': 'https://storage.googleapis.com/google-code-archive/v2/code.google.com/',
        'default_query': 'label:type-defect',
        'default_limit': 1,
        'build_uri': lambda tracker, project, query, start, limit, org: f"{tracker}{quote_plus(project)}/issues-page-{start + 1}.json",
        'results': lambda path, project: [
            (issue['id'], f"https://storage.googleapis.com/google-code-archive/v2/code.google.com/{quote_plus(project)}/issues/issue-{issue['id']}.json")
            for issue in json.load(open(path))['issues']
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
        'results': lambda path, project: [
            (m.group(1), f"https://issues.apache.org/jira/browse/{m.group(1)}")
            for line in open(path) if (m := re.search(r'^\s*<key.*?>(.*?)</key>', line))
        ]
    },
    'github': {
        'default_tracker_uri': 'https://api.github.com/repos/',
        'default_query': '',
        'default_limit': 100,
        'build_uri': lambda tracker, project, query, start, limit, org: (
            f"{tracker}{f'{org}/' if '/' not in project and org else ''}{project}/issues?"
            f"state=all&{query}&per_page={limit}&page={start // limit + 1}"
        ),
        'results': lambda path, project: [
            (issue['number'], issue['html_url'])
            for issue in json.load(open(path))
        ]
    },
    'sourceforge': {
        'default_tracker_uri': 'http://sourceforge.net/rest/p/',
        'default_query': '/bugs/?',
        'default_limit': 100,
        'build_uri': lambda tracker, project, query, start, limit, org: (
            f"{tracker}{project}{query}&page={start // limit}&limit={limit}"
        ),
        'results': lambda path, project: [
            (ticket['ticket_num'], f"https://sourceforge.net{json.load(open(path))['tracker_config']['options']['url']}{ticket['ticket_num']}")
            for ticket in json.load(open(path))['tickets']
        ]
    },
    'bugzilla': {
        'default_tracker_uri': 'https://bz.apache.org/bugzilla/',
        'default_query': '/buglist.cgi?',
        'default_limit': 0,
        'build_uri': lambda tracker, project, query, start, limit, org: (
            f"{tracker}buglist.cgi?bug_status=RESOLVED&order=bug_id&limit=0&"
            f"product={project}&query_format=advanced&resolution=FIXED"
        ),
        'results': lambda path, project: [
            (m.group(1), f"https://bz.apache.org/bugzilla/show_bug.cgi?id={m.group(1)}")
            for line in open(path) if (m := re.search(r'^\s*<bug_id>(.*?)</bug_id>', line))
        ]
    }
}

def get_file(uri, save_to, session):
    headers = {}
    # use GH_TOKEN if available for GitHub API requests
    if 'api.github.com' in uri and os.environ.get('GH_TOKEN'):
        headers['Authorization'] = f"token {os.environ['GH_TOKEN']}"
    
    try:
        response = session.get(uri, headers=headers, timeout=20)
        response.raise_for_status() 
        
        with open(save_to, 'w', encoding='utf-8') as f:
            f.write(response.text)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {uri}: {e}", file=sys.stderr)
        return False

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
    query = args.query or tracker['default_query']
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
    
    start = 0

    # Bugzilla special handling (to be updated)
    if args.tracker_name == 'bugzilla':
        list_uri = tracker['build_uri'](tracker_uri, tracker_id, query, 0, 0, organization_id)
        if debug: print(f"Fetching Bugzilla ID list from: {list_uri}")
        id_list = get_bugzilla_id_list(list_uri, tracker_id, session)
        if not id_list:
            print("No Bugzilla IDs found.", file=sys.stderr)
            sys.exit(0)
            
        if debug: print(f"Found {len(id_list)} Bugzilla IDs.")
        
        all_results = []
        for i in range(0, len(id_list), 50):
            chunk = id_list[i:i+50]
            ids_query = "&".join([f"id={bid}" for bid in chunk])
            xml_uri = f"https://bz.apache.org/bugzilla/show_bug.cgi?ctype=xml&{ids_query}"
            out_file = os.path.join(output_dir, f"{tracker_id}-issues-xml-{i}.txt")
            
            if not os.path.exists(out_file) or os.path.getsize(out_file) == 0:
                if debug: print(f"Downloading {xml_uri} to {out_file}")
                if not get_file(xml_uri, out_file, session):
                    print(f"Could not download {xml_uri}", file=sys.stderr)
                    continue
            
            results = tracker['results'](out_file, tracker_id)
            all_results.extend(results)
            
        try:
            with open(issues_file, 'w', encoding='utf-8') as f:
                for issue_id, issue_url in all_results:
                    f.write(f"{issue_id},{issue_url}\n")
        except IOError as e:
            print(f"Error writing to {issues_file}: {e}", file=sys.stderr)
            
        print(f"Bugzilla processing complete. Wrote {len(all_results)} issues.")
        sys.exit(0)

    # other trackers's processing
    give_up = False # special logic for Google tracker
    while True:
        uri = tracker['build_uri'](tracker_uri, tracker_id, query, start, limit, organization_id)
        project_in_file = tracker_id.replace('/', '-')
        out_file = os.path.join(output_dir, f"{project_in_file}-issues-{start}.json")
        
        if not os.path.exists(out_file) or os.path.getsize(out_file) == 0:
            if debug: print(f"Downloading {uri} to {out_file}")
            if not get_file(uri, out_file, session):
                if give_up: # Google tracker special logic
                    break
                else:
                    print(f"Error: Could not download {uri}", file=sys.stderr)
                    sys.exit(1)
        else:
            if debug: print(f"Skipping download of {out_file}")
        
        try:
            results = tracker['results'](out_file, tracker_id)
        except Exception as e:
            if debug: print(f"Failed to parse {out_file}: {e}. Assuming end of results.")
            results = []

        if results:
            try:
                # use 'a' (append) mode
                with open(issues_file, 'a', encoding='utf-8') as f:
                    for issue_id, issue_url in results:
                        f.write(f"{issue_id},{issue_url}\n")
            except IOError as e:
                print(f"Cannot write to {issues_file}: {e}", file=sys.stderr)
                sys.exit(1)
            
            if args.tracker_name == 'google':
                give_up = True # special logic for Google tracker
            
            start += limit 
        else:
            if debug: print("No more results found. Stopping.")
            break 

if __name__ == "__main__":
    main()