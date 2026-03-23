import os
import csv
import subprocess
import shutil
import re
import argparse

# Config
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MINING_DIR = os.path.join(BASE_DIR, "bug-mining")
FRAMEWORK_DIR = os.path.join(BASE_DIR, "framework")
GENERATED_TESTS_DIR = os.path.join(MINING_DIR, "ActiveMQ", "generated_tests")
PATCHES_DIR = os.path.join(MINING_DIR, "ActiveMQ", "patches")
REPO_URL = "https://github.com/apache/activemq.git"
WORK_DIR = os.path.join(BASE_DIR, "validation_workspace") # Temp workspace for running tests

def get_bug_info(project_id="ActiveMQ"):
    csv_path = os.path.join(MINING_DIR, project_id, "active-bugs.csv")
    bugs = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bugs[row['bug.id']] = row
    return bugs

def determine_module(bug_id):
    """
    Heuristic: Read the patch file. If 'activemq-core' is modified, use that.
    Default to 'activemq-core' if uncertain.
    """
    patch_path = os.path.join(PATCHES_DIR, f"{bug_id}.src.patch")
    if not os.path.exists(patch_path):
        return "activemq-core"  # Default
    
    with open(patch_path, 'r', errors='ignore') as f:
        content = f.read()
        
    # Check for common modules in ActiveMQ
    modules = ["activemq-core", "activemq-console", "activemq-optional", "activemq-web", "activemq-jaas"]
    for mod in modules:
        if f"/{mod}/" in content or f" {mod}/" in content:
            return mod
            
    return "activemq-core"

def run_validation(bug_id, bug_data, test_file_path):
    print(f"\n[Bug {bug_id}] Validating...")
    
    # 1. Prepare Workspace (Clone if needed, Clean)
    if not os.path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)
        print("Cloning repo to validation workspace (this measures once)...")
        subprocess.run(["git", "clone", REPO_URL, "activemq"], cwd=WORK_DIR, check=True)
    
    repo_dir = os.path.join(WORK_DIR, "activemq")
    
    # 2. Checkout Buggy Version
    buggy_commit = bug_data['revision.id.buggy']
    print(f"Checking out {buggy_commit}...")
    subprocess.run(["git", "checkout", "-f", buggy_commit], cwd=repo_dir, capture_output=True)
    
    # Clean untracked files (e.g. old ReproductionTest.java from previous runs)
    print("Cleaning untracked files...")
    subprocess.run(["git", "clean", "-fd"], cwd=repo_dir, capture_output=True)

    # 3. Determine Module and Place Test
    target_module = determine_module(bug_id)
    test_dest_dir = os.path.join(repo_dir, target_module, "src", "test", "java")
    if not os.path.exists(test_dest_dir):
        # Fallback for older versions or different layouts
        test_dest_dir = os.path.join(repo_dir, "src", "test", "java")
        if not os.path.exists(test_dest_dir):
            os.makedirs(test_dest_dir)
            
    # Copy test file
    # Rename to ReproductionTest.java to match the class name inside
    dest_file = os.path.join(test_dest_dir, "ReproductionTest.java")
    shutil.copy(test_file_path, dest_file)
    print(f"Injected test into: {target_module}")
    
    # --- AUTO FIX POM ---
    main_pom = os.path.join(repo_dir, "pom.xml")
    core_pom = os.path.join(repo_dir, "activemq-core", "pom.xml")
    
    if os.path.exists(main_pom):
        with open(main_pom, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Fix Root Element
        # content = re.sub(r'<model>.*?</model>', '', content, flags=re.DOTALL) # Remove incorrect model tag if wrapped weirdly
        content = content.replace("<model>", '<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/maven-v4_0_0.xsd">')
        content = content.replace("</model>", "</project>")
        
        # Fix Legacy Layout (Maven 3 doesn't support 'legacy')
        content = content.replace("<layout>legacy</layout>", "<layout>default</layout>")

        # Fix Duplicate Repo ID in same file if any
        if 'id>codehaus</id>' in content and content.count('id>codehaus</id>') > 1:
             content = content.replace('id>codehaus</id>', 'id>codehaus-legacy</id>', 1)
             
        # Fix XMLBeans version (2.0.0-beta1 depends on missing artifacts)
        content = content.replace("<version>2.0.0-beta1</version>", "<version>2.2.0</version>")
        
        # Upgrade xbean-spring to avoid missing transitive deps
        content = re.sub(r'<artifactId>xbean-spring</artifactId>\s*<version>2.0</version>', '<artifactId>xbean-spring</artifactId>\n            <version>3.4</version>', content)
        content = re.sub(r'<artifactId>xbean-spring</artifactId>\s*</dependency>', '<artifactId>xbean-spring</artifactId>\n        <version>3.4</version>\n    </dependency>', content)

        # Remove dead modules
        content = re.sub(r'<module>activeio</module>', '<!-- <module>activeio</module> -->', content)
        content = re.sub(r'<module>activecluster</module>', '<!-- <module>activecluster</module> -->', content)
        content = re.sub(r'<module>activemq-ra</module>', '<!-- <module>activemq-ra</module> -->', content)
        content = re.sub(r'<module>activemq-jaas</module>', '<!-- <module>activemq-jaas</module> -->', content)
        content = re.sub(r'<module>activemq-optional</module>', '<!-- <module>activemq-optional</module> -->', content)
        content = re.sub(r'<module>activemq-console</module>', '<!-- <module>activemq-console</module> -->', content)
        content = re.sub(r'<module>activemq-web</module>', '<!-- <module>activemq-web</module> -->', content)
        content = re.sub(r'<module>activemq-systest</module>', '<!-- <module>activemq-systest</module> -->', content)
        content = re.sub(r'<module>assembly</module>', '<!-- <module>assembly</module> -->', content)
        content = re.sub(r'<module>openwire-c</module>', '<!-- <module>openwire-c</module> -->', content)
        content = re.sub(r'<module>openwire-dotnet</module>', '<!-- <module>openwire-dotnet</module> -->', content)
        
        with open(main_pom, 'w', encoding='utf-8') as f:
            f.write(content)
            print("Auto-fixed main pom.xml")
            
    if os.path.exists(core_pom):
        with open(core_pom, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        content = content.replace("<model>", '<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/maven-v4_0_0.xsd">')
        content = content.replace("</model>", "</project>")
        
        # Fix Surefire (Handle various snapshot versions)
        content = re.sub(r'<artifactId>maven-surefire-plugin</artifactId>\s*<version>.*?</version>', '<artifactId>maven-surefire-plugin</artifactId>\n        <version>2.4</version>', content, flags=re.DOTALL)
        
        # Fix JavaCC (Handle missing snapshot)
        content = re.sub(r'<artifactId>javacc-maven-plugin</artifactId>\s*<version>.*?</version>', '<artifactId>javacc-maven-plugin</artifactId>\n        <version>2.6</version>', content, flags=re.DOTALL)
        
        # Remove broken dependencies matching commented out modules
        content = re.sub(r'<dependency>\s*<groupId>activemq</groupId>\s*<artifactId>activemq-activecluster</artifactId>.*?</dependency>', '', content, flags=re.DOTALL)
        content = re.sub(r'<dependency>\s*<groupId>org.apache.activemq</groupId>\s*<artifactId>activemq-activecluster</artifactId>.*?</dependency>', '', content, flags=re.DOTALL)
        content = re.sub(r'<dependency>\s*<groupId>activecluster</groupId>\s*<artifactId>activecluster</artifactId>.*?</dependency>', '', content, flags=re.DOTALL)
        
        content = re.sub(r'<dependency>\s*<groupId>activemq</groupId>\s*<artifactId>activemq-jaas</artifactId>.*?</dependency>', '', content, flags=re.DOTALL)
        content = re.sub(r'<dependency>\s*<groupId>org.apache.activemq</groupId>\s*<artifactId>activemq-jaas</artifactId>.*?</dependency>', '', content, flags=re.DOTALL)
        
        # Exclude bad artifact from xbean and related
        for art in ['xbean', 'xmlpublic', 'xbean_xpath', 'xbean-spring']:
            if f"<artifactId>{art}</artifactId>" in content:
                content = content.replace(f"<artifactId>{art}</artifactId>", f"<artifactId>{art}</artifactId><exclusions><exclusion><groupId>xmlbeans</groupId><artifactId>xmlbeans-jsr173-api</artifactId></exclusion></exclusions>")
        
        with open(core_pom, 'w', encoding='utf-8') as f:
            f.write(content)
            print("Auto-fixed activemq-core/pom.xml")

    # --- REMOVE BROKEN TESTS ---
    problematic_tests = [
        os.path.join(repo_dir, "activemq-core", "src", "test", "java", "org", "apache", "activemq", "security", "SimpleSecurityBrokerSystemTest.java")
    ]
    
    for p_test in problematic_tests:
        if os.path.exists(p_test):
            os.remove(p_test)
            print(f"Removed broken test file: {p_test}")
    # ---------------------------

    # 4. Run Maven Test
    # -DfailIfNoTests=false to avoid error if we picked wrong module (but we specified test class)
    cmd = [
        "mvn", "test", 
        f"-pl", target_module, 
        "-am", 
        "-Dtest=ReproductionTest", 
        "-DfailIfNoTests=false",
        "-Dcheckstyle.skip", # Speed up
        "-Drat.skip"         # Speed up
    ]
    
    print("Running Maven validation (this may take time)...")
    try:
        # Timeout after 5 minutes to avoid hangs
        result = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return "TIMEOUT"

    stdout = result.stdout
    
    if "BUILD SUCCESS" in stdout:
        if "Tests run: 1, Failures: 0, Errors: 0, Skipped: 0" in stdout:
            return "PASS (Did not reproduce bug)"
        elif "No tests were executed" in stdout:
            return "ERROR (Test not found/executed)"
        else:
            return "PASS (Unclear)"
            
    elif "BUILD FAILURE" in stdout:
        if "Compilation failure" in stdout:
            return "COMPILE_ERROR"
        elif "Tests run: 1" in stdout and ("Failures: 1" in stdout or "Errors: 1" in stdout):
            return "REPRODUCED (Success!)"
        else:
            return "BUILD_FAILURE (Other)"
            
    # Debug output for UNKNOWN
    print("DEBUG: Maven Output (Tail 20 lines):")
    print("\n".join(stdout.splitlines()[-20:]))
    return "UNKNOWN"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bug", type=str, help="Specific bug ID to validate")
    args = parser.parse_args()
    
    bugs = get_bug_info()
    test_files = os.listdir(GENERATED_TESTS_DIR)
    
    results = []
    
    for filename in sorted(test_files):
        if not filename.endswith("_test.java"):
            continue
            
        bug_id = filename.split("_")[0]
        
        if args.bug and args.bug != bug_id:
            continue
            
        if bug_id not in bugs:
            continue
            
        test_path = os.path.join(GENERATED_TESTS_DIR, filename)
        status = run_validation(bug_id, bugs[bug_id], test_path)
        
        print(f"Result for Bug {bug_id}: {status}")
        results.append((bug_id, status))
        
    print("\n\n=== Validation Summary ===")
    for bid, res in results:
        print(f"Bug {bid}: {res}")

if __name__ == "__main__":
    main()
