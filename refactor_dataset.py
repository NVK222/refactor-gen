import os
import json
import git
from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_language
from tqdm import tqdm
import concurrent.futures
import multiprocessing

REFACTOR_KEYWORDS = [
    'refactor', 'cleanup', 'simplify', 'optimize', 'performance', 
    'pep8', 'style', 'restructure', 'speed up'
]

MAX_COMMITS_PER_REPO = 1000

PYTHON_PATH = os.path.join("D:", "cloned_repos", "python")
JS_PATH = os.path.join("D:", "cloned_repos", "js")

LANGUAGES = {
    'python': {
        'root_dir': PYTHON_PATH,
        'file_extension': '.py',
        'query_string': "(function_definition) @function",
    },
    'javascript': {
        'root_dir': JS_PATH,
        'file_extension': '.js',
        'query_string': "[(function_declaration) @function (arrow_function) @function (method_definition) @function]",
    }
}

def parse_code_to_functions(source_bytes, language_obj, query_string):
    """
    Parses source code and returns a dictionary of {function_name: function_code}.
    This function is run by each worker process.
    """
    parser = Parser()
    parser.language = language_obj
    query = language_obj.query(query_string)
    
    tree = parser.parse(source_bytes)
    captures = query.captures(tree.root_node)
    
    functions = {}
    node_list = captures.get("function") # Use "function", not "@function"
    
    if not node_list:
        return functions

    for node in node_list:
        try:
            name_node = node.child_by_field_name('name')
            if not name_node:
                if node.parent and node.parent.type == 'variable_declarator':
                     name_node = node.parent.child_by_field_name('name')
                elif node.parent and node.parent.type == 'pair':
                     name_node = node.parent.child_by_field_name('key')
            
            if name_node:
                func_name = name_node.text.decode('utf-8', errors='ignore')
                func_code = node.text.decode('utf-8', errors='ignore')
                functions[func_name] = func_code
        except Exception:
            continue
            
    return functions

def mine_repository(repo_path, lang_name, lang_config):
    """
    Mines a single Git repository for refactoring commits.
    This function is designed to be run in a separate process.
    """
    dataset = []
    stats = {
        "commits_scanned": 0,
        "refactor_commits_found": 0,
        "pairs_found": 0
    }
    try:
        repo = git.Repo(repo_path)
        language_obj = get_language(lang_name)
        query_string = lang_config['query_string']
    except git.InvalidGitRepositoryError:
        return lang_name, dataset, stats
    except Exception as e:
        print(f"  -> Worker init error for {repo_path}: {e}")
        return lang_name, dataset, stats

    try:
        commits = list(repo.iter_commits('HEAD', max_count=MAX_COMMITS_PER_REPO))
        
        for commit in commits:
            stats["commits_scanned"] += 1
            try:
                commit_message = commit.message.lower()
                if not any(keyword in commit_message for keyword in REFACTOR_KEYWORDS):
                    continue
                
                stats["refactor_commits_found"] += 1
                
                if not commit.parents:
                    continue
                parent_commit = commit.parents[0]

                diff = commit.diff(parent_commit, create_patch=False, R=True)
                modified_files = diff.iter_change_type('M')
                
                for diff_item in modified_files:
                    file_path = diff_item.a_path
                    if not file_path or not file_path.endswith(lang_config['file_extension']):
                        continue
                    
                    try:
                        content_before = parent_commit.tree[file_path].data_stream.read()
                        content_after = commit.tree[file_path].data_stream.read()
                    except (KeyError, ValueError, AttributeError, OSError):
                        continue
                        
                    functions_before = parse_code_to_functions(content_before, language_obj, query_string)
                    functions_after = parse_code_to_functions(content_after, language_obj, query_string)

                    for func_name, func_code_before in functions_before.items():
                        if func_name in functions_after:
                            func_code_after = functions_after[func_name]
                            if func_code_before != func_code_after:
                                dataset.append({
                                    "code_before": func_code_before,
                                    "code_after": func_code_after
                                })
                                stats["pairs_found"] += 1
            except Exception:
                continue
    except Exception as e:
        print(f"  -> Critical Error scanning repo {repo_path}: {e}")
        return lang_name, [], stats

    return lang_name, dataset, stats

if __name__ == "__main__":
    print("Starting PARALLEL Refactoring Data Mining (with Diagnostics)")
    
    num_workers = multiprocessing.cpu_count()
    print(f"Spawning {num_workers} worker processes...")

    task_list = []
    for lang_name, config in LANGUAGES.items():
        lang_root_dir = config['root_dir']
        if not os.path.exists(lang_root_dir):
            print(f"  -> Warning: Directory not found, skipping: {lang_root_dir}")
            continue
            
        repo_dirs = [os.path.join(lang_root_dir, d) for d in os.listdir(lang_root_dir) 
                     if os.path.isdir(os.path.join(lang_root_dir, d))]
        
        for repo_dir in repo_dirs:
            task_list.append((repo_dir, lang_name, config))

    print(f"Found {len(task_list)} total repositories to scan.")

    all_language_data = {'python': [], 'javascript': []}
    
    total_stats = {
        "commits_scanned": 0,
        "refactor_commits_found": 0,
        "pairs_found": 0
    }
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(mine_repository, task[0], task[1], task[2]): task for task in task_list}
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processing Repos"):
            repo_path = futures[future][0]
            try:
                lang_name, repo_data, repo_stats = future.result()
                
                if repo_data:
                    all_language_data[lang_name].extend(repo_data)
                
                total_stats["commits_scanned"] += repo_stats["commits_scanned"]
                total_stats["refactor_commits_found"] += repo_stats["refactor_commits_found"]
                total_stats["pairs_found"] += repo_stats["pairs_found"]
                
            except Exception as e:
                print(f"  -> Task for repo {repo_path} failed: {e}")

    for lang_name, dataset in all_language_data.items():
        output_filename = f"{lang_name}_refactoring_dataset.jsonl"
        with open(output_filename, 'w', encoding='utf-8') as f:
            for entry in dataset:
                f.write(json.dumps(entry) + '\n')
                
        print(f"\nSuccess! Saved {len(dataset)} refactoring examples for {lang_name} to '{output_filename}'.")

    print(f"Total Repositories Scanned: {len(task_list)}")
    print(f"Total Commits Scanned:     {total_stats['commits_scanned']}")
    print(f"Refactor Commits Found:  {total_stats['refactor_commits_found']}")
    print(f"Refactor Pairs Extracted:  {total_stats['pairs_found']}")