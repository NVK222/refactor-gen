# About
This is the github repo for Mini Project at BVCOE, New Delhi.  
Refactor-Gen is the result of fine-tuning QWEN-1.5-7B on popular **Python** and **Javascript** github repositories.  
It outperforms the base model in both Python and JS in HumanEvalPack by ~35%.  
A VS Code extension utilizing FastAPI has been created to demonstrate this.

# Usage
## IMPORTANT: ALL SCRIPTS HAVE HARDCODED PATHS. CHANGE THEM FOR YOUR USAGE.
### Use *github_scraper.py* to find repos and generate *javascript_urls.txt* and *python_urls.txt* 
### Use *clone_repos.py* to clone the repos in *javascript_urls.txt* & *python_urls.txt*.
### Use *unshallow_repos.py* to get a deep history of all repos.
### Use *code_parser.py* & *refactor_dataset.py* to create generation and refactoring datasets from the repos.
### A .vsix file has been attached to install it in VS Code.
### Run backend/main.py to run the server.
