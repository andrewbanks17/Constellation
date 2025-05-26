print("DEBUG: directory_traversal.py script execution started.") # DEBUG LINE 1
import os
import json
import datetime
from llm_interaction import generate_diagrams_with_llm # Added

CONFIG_FILE = 'constellation.config.json'
# Define CONSTELLATION_ROOT_DIR at the module level
CONSTELLATION_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONSTELLATION_OUTPUT_ROOT_DIR_NAME = "root" # Name of the dir within Constellation for outputs

def load_config():
    print("DEBUG: load_config() called.") # DEBUG LINE
    config_path = os.path.join(CONSTELLATION_ROOT_DIR, CONFIG_FILE)
    print(f"DEBUG: Config path: {config_path}") # DEBUG LINE
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                print("DEBUG: Config file loaded successfully.") # DEBUG LINE
                return config_data
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in '{config_path}'. Details: {e}")
            return None # Return None to indicate critical error
        except Exception as e:
            print(f"ERROR: Could not read or parse config file '{config_path}'. Details: {e}")
            return None # Return None for other errors too
    else:
        print(f"Warning: Configuration file '{CONFIG_FILE}' not found at {config_path}.")
    return {} # Return empty dict if not found but no critical error

def get_project_root():
    # Assumes Constellation is cloned into a subdirectory of the project's root.
    return os.path.abspath(os.path.join(CONSTELLATION_ROOT_DIR, os.pardir))

def is_ignored(path, ignore_patterns, project_root):
    # Normalize path to be relative to project_root for consistent checking
    relative_path_to_check = ""
    try:
        # For files/dirs within the project, get their path relative to project root
        if path.startswith(project_root):
            relative_path_to_check = os.path.relpath(path, project_root)
        else:
            # If path is not under project_root (e.g. a full path to an unrelated item),
            # just use its basename for pattern matching like .git, node_modules
            relative_path_to_check = os.path.basename(path)
    except ValueError:
        # Should not happen if project_root is a valid directory
        relative_path_to_check = os.path.basename(path)

    for pattern in ignore_patterns:
        # Case 1: Exact match for basename (e.g., '.git', 'node_modules')
        if os.path.basename(path) == pattern:
            return True
        
        # Case 2: Glob-like pattern for extensions (e.g., '*.log') applied to relative path
        if pattern.startswith('*') and relative_path_to_check.endswith(pattern[1:]):
            return True

        # Case 3: Directory prefix match (e.g., 'build/', 'dist')
        # Ensure it matches a directory or a path starting with the pattern followed by a separator.
        if relative_path_to_check.startswith(pattern):
            if len(relative_path_to_check) == len(pattern) or \
               (len(relative_path_to_check) > len(pattern) and relative_path_to_check[len(pattern)] == os.sep):
                return True
    return False

def aggregate_content_for_directory(directory_path, config, project_root):
    """
    Aggregates content of relevant files directly within the given directory.
    Returns a dictionary with a list of individual file details and a single
    concatenated string of their content, formatted for LLM consumption.
    """
    # print(f"Aggregating content for: {os.path.relpath(directory_path, project_root)}")
    individual_files_details = []
    concatenated_content_parts = []
    source_file_extensions = config.get('sourceFileExtensions', [])
    ignore_patterns = config.get('ignore', [])

    try:
        for entry_name in os.listdir(directory_path):
            entry_path = os.path.join(directory_path, entry_name)

            if os.path.isfile(entry_path):
                if is_ignored(entry_path, ignore_patterns, project_root):
                    continue

                relevant_by_extension = False
                if not source_file_extensions:
                    relevant_by_extension = True
                else:
                    _, ext = os.path.splitext(entry_name)
                    if ext.lower() in [e.lower() for e in source_file_extensions]:
                        relevant_by_extension = True
                
                if not relevant_by_extension:
                    continue
                
                try:
                    with open(entry_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    relative_file_path = os.path.relpath(entry_path, project_root)
                    
                    individual_files_details.append({
                        "file_name": entry_name,
                        "path": relative_file_path,
                        "content_length": len(content) # Store length instead of full content here
                    })

                    concatenated_content_parts.append(f"--- START FILE: {relative_file_path} ---\\n")
                    concatenated_content_parts.append(content)
                    concatenated_content_parts.append(f"\\n--- END FILE: {relative_file_path} ---\\n\\n")
                    
                except Exception as e:
                    print(f"    Error reading file {entry_name}: {e}")
            
    except OSError as e:
        print(f"Error listing directory for aggregation {os.path.relpath(directory_path, project_root)}: {e}")
        return {"individual_files": [], "concatenated_content": ""}

    final_concatenated_content = "".join(concatenated_content_parts)
    return {
        "individual_files": individual_files_details,
        "concatenated_content": final_concatenated_content
    }

def generate_mock_llm_outputs(relative_dir_path, concatenated_content, children_summaries):
    """
    Generates mock summary and Mermaid diagram content for a directory.
    """
    print(f"    Mock LLM: Generating outputs for '{relative_dir_path}'")
    # print(f"      LLM Input (concatenated content - first 100 chars): {concatenated_content[:100]}...")
    # print(f"      LLM Input (children summaries): {children_summaries}")

    current_date = datetime.date.today().isoformat()
    summary_md = f"# Summary for {relative_dir_path}\n\n"
    summary_md += f"This is a mock summary generated on {current_date}.\n"
    summary_md += f"It processes content of length: {len(concatenated_content)} characters.\n"
    if children_summaries:
        summary_md += "\nIt has the following child directories processed:\n"
        for child in children_summaries:
            summary_md += f"- {child['path']} (Files: {child['files_aggregated_count']})\n"
    else:
        summary_md += "No child directories were processed or passed to this mock LLM call.\n"

    mermaid_md = f"```mermaid\n---\ntitle: Mock Flowchart for {relative_dir_path}\n---\nflowchart TD\n    A[Start {relative_dir_path}] --> B{{Contains {len(concatenated_content)} chars of content}};\n"
    if children_summaries:
        for i, child in enumerate(children_summaries):
            # Sanitize child path for use as a Mermaid node ID
            safe_child_path_id = child['path'].replace(os.sep, '_').replace('.', '_').replace('-','_')
            child_node_id = f"Child{i}_{safe_child_path_id}"
            mermaid_md += f"    B --> {child_node_id}[{child['path']}]\n"
            # Mock clickable link to child's mermaid diagram (actual linking handled by UI)
            # Ensure forward slashes for web-like paths in mermaid diagram links
            link_path = f"./{child['path'].replace(os.sep, '/')}/mermaid.md"
            mermaid_md += f"    click {child_node_id} \"{link_path}\" \"Go to {child['path']} diagram\" _self\n"
    else:
        mermaid_md += f"    B --> C[No sub-directories]\n"
    mermaid_md += "```\n"

    return {
        "summary_md": summary_md,
        "mermaid_md": mermaid_md
    }

def save_outputs(relative_dir_path, summary_md, mermaid_md, project_root):
    """
    Saves the generated summary.md and mermaid.md to the mirrored output directory.
    """
    base_output_dir = os.path.join(CONSTELLATION_ROOT_DIR, CONSTELLATION_OUTPUT_ROOT_DIR_NAME)

    # Construct the specific output directory path for the current item
    # If relative_dir_path is the project name (i.e., it's the root of the project being analyzed),
    # files go into root/<project_name>/. 
    # Otherwise, for subdirectories, they go into root/<project_name>/<relative_subdir_path>.
    
    # The root of the mirrored structure should be the project's name.
    project_name = os.path.basename(project_root)
    
    if relative_dir_path == project_name: # Current item is the project root itself
        target_output_dir = os.path.join(base_output_dir, project_name)
    else: # Current item is a subdirectory within the project
        # We need to ensure that relative_dir_path here is truly relative to the project_name directory
        # For example, if project_name is 'MyProject' and relative_dir_path is 'MyProject/src',
        # we want the output in 'root/MyProject/src'.
        # The relative_dir_path passed here should already be like 'ProjectName/subdir'
        target_output_dir = os.path.join(base_output_dir, relative_dir_path)

    try:
        os.makedirs(target_output_dir, exist_ok=True)
        summary_file_path = os.path.join(target_output_dir, "summary.md")
        mermaid_file_path = os.path.join(target_output_dir, "mermaid.md")

        with open(summary_file_path, 'w', encoding='utf-8') as f:
            f.write(summary_md)
        # print(f"    Saved summary to: {summary_file_path}")

        with open(mermaid_file_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_md)
        # print(f"    Saved mermaid to: {mermaid_file_path}")
        
        # Return paths relative to the CONSTELLATION_OUTPUT_ROOT_DIR_NAME for consistency in links
        output_root_for_relative_paths = os.path.join(CONSTELLATION_ROOT_DIR, CONSTELLATION_OUTPUT_ROOT_DIR_NAME)
        return {
            "summary_path": os.path.relpath(summary_file_path, output_root_for_relative_paths),
            "mermaid_path": os.path.relpath(mermaid_file_path, output_root_for_relative_paths)
        }
    except Exception as e:
        print(f"    Error saving outputs for {relative_dir_path}: {e}")
        return {"summary_path": None, "mermaid_path": None}

def traverse_directory_post_order(current_dir_path, config, project_root):
    children_aggregation_results = [] 
    ignore_patterns = config.get('ignore', [])

    if current_dir_path != project_root and is_ignored(current_dir_path, ignore_patterns, project_root):
        return [] 

    entries = []
    try:
        entries = os.listdir(current_dir_path)
    except OSError as e:
        # Ensure project_root is not None or empty before relpath
        err_rel_path = current_dir_path
        if project_root and project_root != current_dir_path:
            try: err_rel_path = os.path.relpath(current_dir_path, project_root)
            except ValueError: pass # Keep absolute if error
        print(f"Error listing directory {err_rel_path}: {e}")
        return []

    processed_children_outputs = [] # Store the full summary objects from children
    for entry_name in entries:
        entry_path = os.path.join(current_dir_path, entry_name)
        if os.path.isdir(entry_path):
            # No need to check is_ignored here again if the top-level check in recursive call handles it
            processed_children_outputs.extend(
                traverse_directory_post_order(entry_path, config, project_root)
            )
            
    # Determine the relative path for the current directory
    # This path will be used for naming in the output structure and for LLM context
    if current_dir_path == project_root:
        relative_current_dir_for_output = os.path.basename(project_root)
    else:
        relative_current_dir_for_output = os.path.join(os.path.basename(project_root), os.path.relpath(current_dir_path, project_root))
    
    # Normalize to use forward slashes for display and internal consistency if desired, os.sep for os operations
    display_relative_dir = relative_current_dir_for_output.replace(os.sep, '/')

    print(f"--- Processing directory: {display_relative_dir} ---")
    aggregation_result = aggregate_content_for_directory(current_dir_path, config, project_root)
    current_dir_files_details = aggregation_result["individual_files"]
    concatenated_content_for_llm = aggregation_result["concatenated_content"]
    
    if current_dir_files_details:
        print(f"  Files in '{display_relative_dir}': {[item['file_name'] for item in current_dir_files_details]}")
        print(f"  Concatenated content length for LLM: {len(concatenated_content_for_llm)} chars")
    else:
        print(f"  No relevant files found in '{display_relative_dir}'.")

    llm_input_children_summaries = [
        {"path": child["path"], "files_aggregated_count": child["files_aggregated_count"]}
        for child in processed_children_outputs
    ]
    # Pass the display_relative_dir to LLM mock, as this is what we want in titles/content
    # mock_llm_result = generate_mock_llm_outputs(display_relative_dir, concatenated_content_for_llm, llm_input_children_summaries)
    # Replace mock call with actual LLM call
    llm_result = generate_diagrams_with_llm(config, display_relative_dir, concatenated_content_for_llm, llm_input_children_summaries)

    # Save the mock outputs using relative_current_dir_for_output for path construction
    # saved_paths = save_outputs(relative_current_dir_for_output, mock_llm_result["summary_md"], mock_llm_result["mermaid_md"], project_root)
    saved_paths = save_outputs(relative_current_dir_for_output, llm_result["summary_md"], llm_result["mermaid_md"], project_root)
    
    if saved_paths["summary_path"]:
        print(f"    Outputs saved for '{display_relative_dir}':")
        print(f"      Summary: {os.path.join(CONSTELLATION_OUTPUT_ROOT_DIR_NAME, saved_paths['summary_path'])}")
        print(f"      Mermaid: {os.path.join(CONSTELLATION_OUTPUT_ROOT_DIR_NAME, saved_paths['mermaid_path'])}")
    else:
        print(f"    Failed to save outputs for '{display_relative_dir}'")

    current_dir_summary_for_parent = {
        "path": display_relative_dir, # Use the display path for parent context
        "type": "directory",
        "files_aggregated_count": len(current_dir_files_details),
        "children_processed_count": len(llm_input_children_summaries),
        "summary_file": saved_paths['summary_path'], # Store relative path from output root
        "mermaid_file": saved_paths['mermaid_path']  # Store relative path from output root
    }
    
    return [current_dir_summary_for_parent] + processed_children_outputs

if __name__ == "__main__":
    print("DEBUG: Entered __main__ block.") # DEBUG LINE
    config = load_config()
    
    # if load_config returned None (due to critical error like unparsable JSON), exit.
    if config is None:
        print("Exiting: Critical error loading configuration.")
        exit(1)
        
    # if config is an empty dictionary (e.g. file not found, or file was empty {}), print warning and exit.
    if not config: 
        print("Exiting: Configuration is empty (e.g., file not found or JSON is empty). Check constellation.config.json.")
        exit(1)

    project_root = get_project_root()
    print(f"DEBUG: Detected project root: {project_root}")

    # Start the traversal and processing from the project root directory
    traverse_directory_post_order(project_root, config, project_root)
