# clone_repos.py
# This script reads a list of git repository URLs from a text file and clones them into a local directory.

import os
import subprocess

def clone_repositories_from_file(file_path, base_clone_dir):
    """
    Clones all repositories listed in a given file.

    Args:
        file_path (str): The path to the text file containing repository URLs.
        base_clone_dir (str): The directory where the repositories will be cloned.
    """
    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' was not found.")
        return

    os.makedirs(base_clone_dir, exist_ok=True)
    print(f"📂 Repositories will be cloned into: '{base_clone_dir}'")

    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"\nFound {len(urls)} repositories to clone from '{file_path}'.")
    
    for url in urls:
        try:
            repo_name = url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(base_clone_dir, repo_name)

            if os.path.exists(repo_path):
                print(f"Skipping '{repo_name}', directory already exists.")
                continue

            print(f"🚀 Cloning '{repo_name}' from {url}...")
            subprocess.run(['git', 'clone', '--depth', '1', url, repo_path], check=True, capture_output=True, text=True)
            print(f"✅ Successfully cloned '{repo_name}'.")

        except subprocess.CalledProcessError as e:
            print(f"Failed to clone {url}. Error: {e.stderr}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {url}: {e}")

    print("\nCloning process finished for this file.")

if __name__ == "__main__":
    python_urls_file = "python_urls.txt"
    javascript_urls_file = "javascript_urls.txt"

    python_clone_dir = os.path.join("cloned_repos", "python")
    javascript_clone_dir = os.path.join("cloned_repos", "javascript")

    print("Starting Python Repository Cloning")
    clone_repositories_from_file(python_urls_file, python_clone_dir)
    
    print("\nStarting JavaScript Repository Cloning")
    clone_repositories_from_file(javascript_urls_file, javascript_clone_dir)

    print("\nAll tasks complete.")
