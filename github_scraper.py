# github_repo_scraper.py
# This script searches for popular and recently updated repositories on GitHub for a given language.
# It saves the URLs of the found repositories to a file for later use.

from github import Github
import os

def find_popular_repos(token, language, min_stars=5000, pushed_after="2025-01-01"):
    """
    Searches GitHub for popular repositories and saves their URLs to a file.

    Args:
        token (str): Your GitHub personal access token.
        language (str): The programming language to search for (e.g., "python", "javascript").
        min_stars (int): The minimum number of stars for a repo to be considered popular.
        pushed_after (str): The date after which a repo must have been pushed to (YYYY-MM-DD).

    Returns:
        None. The output is saved to a file.
    """
    try:
        g = Github(token)
        query = f"language:{language} stars:>{min_stars} pushed:>{pushed_after}"
        print(f"\nSearching GitHub with query: '{query}'")

        repositories = g.search_repositories(query=query, sort='stars', order='desc')
        output_filename = f"{language}_urls.txt"
        print(f"\nFound repositories. Saving URLs to '{output_filename}'...")
        print("-" * 30)

        with open(output_filename, 'w') as f:
            repo_count = 0
            for i, repo in enumerate(repositories):
                if i >= 50:
                    break
                print(f"Name: {repo.full_name} | Stars: {repo.stargazers_count}")
                f.write(repo.clone_url + '\n')
                repo_count += 1
        
        print("-" * 30)
        print(f"Success! Saved {repo_count} repository URLs to '{output_filename}'.")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please check if your GitHub token is correct and has the necessary permissions.")

if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        github_token = input("Please enter your GitHub Personal Access Token: ")

    if github_token:
        while True:
            lang_choice = input("Enter the language to search for (python/javascript): ").lower()
            if lang_choice in ["python", "javascript"]:
                break
            else:
                print("Invalid choice. Please enter 'python' or 'javascript'.")
        
        find_popular_repos(github_token, lang_choice)
    else:
        print("GitHub token not provided. Exiting.")

