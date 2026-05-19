import os
import subprocess
import time

def get_all_repo_paths(root_dir):
    """Finds all Git repository paths in the python and javascript subdirs."""
    repo_paths = []
    if not os.path.exists(root_dir):
        print(f"Error: Root directory '{root_dir}' not found.")
        return []
        
    for lang_dir in os.listdir(root_dir):
        lang_path = os.path.join(root_dir, lang_dir)
        if os.path.isdir(lang_path):
            for repo_name in os.listdir(lang_path):
                repo_path = os.path.join(lang_path, repo_name)
                if os.path.isdir(os.path.join(repo_path, '.git')):
                    repo_paths.append(repo_path)
    return repo_paths

def unshallow_repo(repo_path):
    """Runs 'git fetch --depth=500' in the specified repository directory."""
    repo_name = os.path.basename(repo_path)
    print(f"Deepening {repo_name} to 500 commits (in {repo_path})")
    
    try:
        is_shallow_output = subprocess.run(
            ['git', 'rev-parse', '--is-shallow-repository'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        is_shallow = is_shallow_output.stdout.strip() == 'true'
        
        if not is_shallow:
            print(f"Already a full clone (has all commits). Skipping.")
            return True

        print("Starting 'git fetch --depth=500'...")
        start_time = time.time()
        subprocess.run(
            ['git', 'fetch', '--depth=500'],
            cwd=repo_path,
            check=True,
            capture_output=True
        )
        end_time = time.time()
        print(f"Successfully fetched history (depth 500) in {end_time - start_time:.2f} seconds.")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR fetching history for {repo_name}.")
        print(f"Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"ERROR: 'git' command not found. Is Git installed and in your PATH?")
        return False

if __name__ == "__main__":
    CLONED_REPOS_ROOT_PATH = "D:\\cloned_repos"
    print("Starting process to fetch 500 commits for all shallow clones...")
    print(f"Target directory: {os.path.abspath(CLONED_REPOS_ROOT_PATH)}")
    
    repo_paths = get_all_repo_paths(CLONED_REPOS_ROOT_PATH)
    
    if not repo_paths:
        print(f"No repositories found in '{CLONED_REPOS_ROOT_PATH}'. Exiting.")
    else:
        print(f"Found {len(repo_paths)} repositories to check.")
        success_count = 0
        fail_count = 0
        for repo_path in repo_paths:
            if unshallow_repo(repo_path):
                success_count += 1
            else:
                fail_count += 1
            print("-" * 30)
            
        print(f"Successfully processed: {success_count}")
        print(f"Failed:                 {fail_count}")
        if fail_count > 0:
            print("Please review any errors above before re-running the mining script.")
        else:
            print("All repositories now have at least 500 commits of history (if available).")

