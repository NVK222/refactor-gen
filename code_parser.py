# parse_code.py
# This script walks through directories of cloned code, parses source files using tree-sitter,
# and extracts (description, code) pairs to create a dataset for training a generative AI model.

import os
import json
from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_language
from tqdm import tqdm

def get_function_docstring_and_body(node, source_code_bytes):
    """
    For a given function definition node, extracts the docstring and the full function body.
    This version is robust and handles cases where the docstring isn't the first child.
    """
    body_node = node.child_by_field_name('body')
    if not body_node:
        return None, None

    docstring_node = None
    docstring_raw_text = None
    
    if body_node.named_child_count > 0:
        first_named_child = body_node.named_children[0]
        if first_named_child.type == 'expression_statement' and first_named_child.named_child_count > 0:
            string_node = first_named_child.named_children[0]
            if string_node.type == 'string':
                docstring_node = string_node
                docstring_raw_text = first_named_child.text.decode('utf-8')

    if docstring_node and docstring_raw_text:
        docstring_text = docstring_node.text.decode('utf-8').strip()
        if docstring_text.startswith(('"""', "'''")):
            docstring_text = docstring_text[3:-3].strip()
        elif docstring_text.startswith(('"', "'")):
            docstring_text = docstring_text[1:-1].strip()
        
        full_function_text = node.text.decode('utf-8')
        
        function_code_only = full_function_text.replace(docstring_raw_text, "", 1).strip()
        return docstring_text, function_code_only
        
    return None, None


def get_js_function_comment_and_body(node, source_code_bytes):
    """
    For a JS function, extracts the leading JSDoc-style comment block and function body.
    """
    comment_node = node.prev_sibling
    comment_text_buffer = []
    
    while comment_node and comment_node.type in ['comment', '\n', '\r', ' ']:
        if comment_node.type == 'comment':
            comment_text = comment_node.text.decode('utf-8').strip()
            comment_text_buffer.insert(0, comment_text)
            if comment_text.startswith('/**'):
                break
        comment_node = comment_node.prev_sibling

    if comment_text_buffer:
        full_comment = "\n".join(comment_text_buffer).strip()
        if full_comment.startswith('/**'):
            lines = full_comment.split('\n')
            cleaned_lines = [line.strip().lstrip('*').strip() for line in lines]
            cleaned_comment = "\n".join(cleaned_lines[1:-1]).strip() # Remove /** and */
            
            function_body = node.text.decode('utf-8')
            return cleaned_comment, function_body
            
    return None, None


def parse_repositories(root_dir, language_name, file_extension, query_string, extractor_func):
    """
    Parses all repositories in a directory for a specific language.
    """
    print(f"\nParsing {language_name.capitalize()} Repositories")
    
    language = get_language(language_name)
    parser = Parser()
    parser.language = (language)
    
    query = language.query(query_string)
    dataset = []

    filepaths = []
    exclude_dirs = {'node_modules', '.git', 'dist', 'build', 'docs', '__pycache__', 'test', 'tests', 'examples', 'e2e'}
    
    print("Finding files to parse...")
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        
        for filename in filenames:
            if filename.endswith(file_extension):
                filepaths.append(os.path.join(dirpath, filename))

    print(f"Found {len(filepaths)} files.")
    
    for filepath in tqdm(filepaths, desc=f"Parsing {language_name} files"):
        try:
            with open(filepath, 'rb') as f:
                source_code_bytes = f.read()

            tree = parser.parse(source_code_bytes)
            captures = query.captures(tree.root_node)
            node_list = captures.get("function") 

            if node_list:
                for node in node_list:
                    description, code = extractor_func(node, source_code_bytes)
                    if description and code and len(description.split()) > 5 and len(code.split()) > 10:
                        dataset.append({"description": description, "code": code})
        except Exception:
            continue
    
    output_filename = f"{language_name}_generation_dataset.jsonl"
    with open(output_filename, 'w', encoding='utf-8') as f:
        for entry in dataset:
            f.write(json.dumps(entry) + '\n')

    print(f"\nSuccess! Saved {len(dataset)} examples to '{output_filename}'.")


if __name__ == "__main__":
    PYTHON_ROOT = os.path.join("D:","cloned_repos", "python")
    PYTHON_QUERY = "(function_definition) @function"

    JS_ROOT = os.path.join("D:","cloned_repos", "javascript")
    JS_QUERY = "[(function_declaration) @function (arrow_function) @function (method_definition) @function]"

    parse_repositories(PYTHON_ROOT, "python", ".py", PYTHON_QUERY, get_function_docstring_and_body)
    parse_repositories(JS_ROOT, "javascript", ".js", JS_QUERY, get_js_function_comment_and_body)
    
    print("\nAll parsing tasks complete.")

