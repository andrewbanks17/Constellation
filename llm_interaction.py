import google.generativeai as genai
import os
import json
import time

# Define CONSTELLATION_ROOT_DIR at the module level
CONSTELLATION_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = 'constellation.config.json'

def load_llm_config():
    """Loads LLM configuration from the main config file."""
    config_path = os.path.join(CONSTELLATION_ROOT_DIR, CONFIG_FILE)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return config_data.get('llm') 
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in '{config_path}'. Details: {e}")
        except Exception as e:
            print(f"ERROR: Could not read or parse config file '{config_path}'. Details: {e}")
    return None

def generate_text_with_gemini(prompt_text, api_key, model_name, max_tokens=2048, temperature=0.7, retries=3, delay=5):
    """
    Generates text using the Gemini API with specified parameters.

    Args:
        prompt_text (str): The prompt to send to the LLM.
        api_key (str): The API key for authentication.
        model_name (str): The specific Gemini model to use (e.g., 'gemini-1.5-flash').
        max_tokens (int): Maximum number of tokens to generate.
        temperature (float): Controls randomness (0.0-1.0).
        retries (int): Number of times to retry on API errors.
        delay (int): Seconds to wait between retries.

    Returns:
        str: The generated text from the LLM, or None if an error occurs after retries.
    """
    genai.configure(api_key=api_key)

    generation_config = genai.GenerationConfig(
        max_output_tokens=max_tokens,
        temperature=temperature
    )
    
    # Ensure the model name is just the model identifier, not the full path
    # The SDK prepends "models/" to the model name.
    if model_name.startswith("models/"):
        model_name = model_name.split("models/", 1)[1]

    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config
        # safety_settings= Adjust as per your needs
    )

    for attempt in range(retries):
        try:
            print(f"    LLM API: Attempt {attempt + 1} to generate text for model {model_name}...")
            response = model.generate_content(prompt_text)
            
            if response.candidates:
                # Assuming the first candidate is the one we want
                if response.candidates[0].content.parts:
                    generated_text = "".join(part.text for part in response.candidates[0].content.parts)
                    print(f"    LLM API: Successfully generated text (length: {len(generated_text)}).")
                    return generated_text
                else:
                    print(f"    LLM API ERROR: No parts in candidate content for model {model_name}.")
                    # Potentially log response.candidates[0].finish_reason if available and relevant
            else:
                print(f"    LLM API ERROR: No candidates returned by model {model_name}.")
                # Potentially log response.prompt_feedback if available
            
            # If no text was returned but also no exception, it's an issue with the response structure
            # or a non-ideal finish reason (e.g., safety, recitation).
            # We'll treat this as a failure for this attempt.

        except Exception as e:
            print(f"    LLM API ERROR (Attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                print(f"    Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"    LLM API ERROR: All retries failed for model {model_name}.")
                return None # Failed after all retries
        
        # If we reach here, it means the response was not successful but didn't raise an exception
        # that the 'except Exception' block caught (e.g. empty candidates list).
        # We should retry if attempts are left.
        if attempt < retries - 1:
            print(f"    LLM API: Response not as expected. Retrying in {delay} seconds...")
            time.sleep(delay)
        else:
            print(f"    LLM API: All retries failed due to unexpected response structure or finish reason for model {model_name}.")
            return None
            
    return None # Should be unreachable if logic is correct, but as a fallback.


def generate_directory_summary_prompt(directory_path, concatenated_content, children_summaries):
    """
    Creates a prompt for the LLM to generate a summary.md for a directory.
    """
    prompt = f"""
You are an expert software engineering assistant. Your task is to analyze the provided content of a directory and its sub-directory summaries to generate a concise, markdown-formatted summary.

Directory under analysis: '{directory_path}'

The content of the files directly within '{directory_path}' is as follows:
---
{concatenated_content}
---

This directory has the following child sub-directories that have already been processed.
Their summaries are (if any):
"""
    if children_summaries:
        for child in children_summaries:
            prompt += f"""
- Child Directory: '{child['path']}'
  - Files Aggregated: {child['files_aggregated_count']}
  - Summary (if available, might be path to summary file): {child.get('summary_content', 'Not available')} 
""" # Assuming child summaries might be paths or actual content
    else:
        prompt += "No child sub-directories were processed or their summaries are not available.\\n"

    prompt += f"""
Based on the file contents of '{directory_path}' and the information about its children:
1.  Write a brief overview of the primary purpose and responsibility of the '{directory_path}' directory.
2.  Identify and list the key files or components within '{directory_path}' and briefly describe their role.
3.  If there are notable interactions or dependencies revealed by the file contents (e.g., one file uses another, a module exports key functions), mention them.
4.  Conclude with a high-level statement about how this directory fits into the larger project structure, considering its children if applicable.

Format the entire output as a single Markdown block. Do not include any preamble or explanation outside the markdown.
Start with a heading like: # Summary for {directory_path}
"""
    return prompt

def generate_directory_mermaid_prompt(directory_path, concatenated_content, children_summaries):
    """
    Creates a prompt for the LLM to generate a mermaid.md for a directory.
    """
    prompt = f"""
You are an expert software engineering assistant specializing in creating Mermaid.js diagrams.
Your task is to generate a Mermaid.js 'flowchart TD' (Top-Down) diagram based on the content of a specific directory and information about its child directories.

Directory under analysis: '{directory_path}'

The content of the files directly within '{directory_path}' is as follows:
---
{concatenated_content}
---

This directory has the following child sub-directories that have already been processed:
"""
    if children_summaries:
        for i, child in enumerate(children_summaries):
            # Sanitize child path for use as a Mermaid node ID and for display
            safe_child_path_id = child['path'].replace(os.sep, '_').replace('.', '_').replace('-', '_')
            display_child_path = child['path'].replace(os.sep, '/')
            prompt += f"""
- Child Directory {i+1}:
  - Path: '{display_child_path}'
  - Node ID suggestion: '{safe_child_path_id}_node' 
  - Link to its diagram: './{display_child_path}/mermaid.md' 
"""
    else:
        prompt += "No child sub-directories were processed.\\n"

    prompt += f"""
Instructions for the Mermaid Diagram:
1.  The diagram MUST be a 'flowchart TD'.
2.  Create a title for the diagram using '--- title: Flowchart for {directory_path} ---'.
3.  Represent the main components, files, or logical blocks within '{directory_path}' as nodes in the flowchart.
4.  Show the primary interactions or data flow between these components/files within '{directory_path}'.
5.  If '{directory_path}' has child sub-directories (listed above), represent each child directory as a distinct node.
    - The text for each child node should be its relative path (e.g., 'src/utils').
    - Make these child directory nodes clickable to link to their respective 'mermaid.md' files.
      Example: click YOUR_CHILD_NODE_ID_HERE "./child_relative_path/mermaid.md" "Go to child_relative_path diagram" _self
6.  Connect the representation of '{directory_path}'s internal logic to these child directory nodes where appropriate (e.g., if the code in '{directory_path}' seems to delegate tasks to or depend on a child). If the relationship is not clear, you can connect them from a general node representing '{directory_path}' itself.
7.  Keep the diagram relatively high-level. Focus on the most important aspects and relationships. Do not try to represent every single detail.
8.  Ensure the output is ONLY the Mermaid code block, starting with \\`\\`\\`mermaid and ending with \\`\\`\\`. No other text or explanation.

Example of a clickable child node:
    ParentDirectoryNode --> ChildDirNode[sub_dir_path]
    click ChildDirNode "./sub_dir_path/mermaid.md" "Go to sub_dir_path diagram" _self

Generate the Mermaid.js 'flowchart TD' code block now.
"""
    return prompt

def generate_diagrams_with_llm(config, relative_dir_path, concatenated_content, children_summaries):
    """
    Replaces generate_mock_llm_outputs.
    Uses the actual LLM to generate summary and mermaid diagram.
    """
    llm_config = config.get('llm')
    if not llm_config:
        print("    ERROR: LLM configuration not found in main config.")
        return {"summary_md": "Error: LLM config missing.", "mermaid_md": "```mermaid\\nflowchart TD\\n  A[Error: LLM config missing];\\n```"}

    api_key = llm_config.get('apiKey')
    # Use a default model if not specified, but prefer the one from config
    model_name = llm_config.get('model', 'gemini-1.5-flash-latest') # Default to a known Gemini model
    llm_settings = llm_config.get('settings', {})
    max_tokens = llm_settings.get('maxTokens', 2048) # Default from your example
    temperature = llm_settings.get('temperature', 0.7) # Default from your example

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print(f"    ERROR: LLM API key not configured in {CONFIG_FILE}.")
        return {"summary_md": "Error: LLM API key missing.", "mermaid_md": "```mermaid\\nflowchart TD\\n  A[Error: LLM API key missing];\\n```"}

    # 1. Generate Summary
    print(f"    LLM: Generating summary for '{relative_dir_path}' using model '{model_name}'...")
    summary_prompt = generate_directory_summary_prompt(relative_dir_path, concatenated_content, children_summaries)
    
    # Truncate concatenated_content if it's too large for the prompt (very basic strategy)
    # A more sophisticated approach would be to summarize chunks or be selective.
    # This is a rough estimate; actual token limits depend on the model and include the whole prompt.
    # Gemini 1.5 Flash has a large context window, but let's be cautious for now.
    # Max prompt size could be around 30k tokens, but output also counts.
    # For now, let's assume a very conservative limit for the content part of the prompt.
    # This needs refinement based on typical content sizes and LLM limits.
    MAX_CONTENT_CHARS_FOR_PROMPT = 50000 # Arbitrary limit for now
    if len(concatenated_content) > MAX_CONTENT_CHARS_FOR_PROMPT:
        print(f"    WARNING: Concatenated content for '{relative_dir_path}' is very long ({len(concatenated_content)} chars). Truncating to {MAX_CONTENT_CHARS_FOR_PROMPT} chars for summary prompt.")
        truncated_content_summary = concatenated_content[:MAX_CONTENT_CHARS_FOR_PROMPT] + "\\n... (content truncated)"
    else:
        truncated_content_summary = concatenated_content
    
    summary_prompt_final = generate_directory_summary_prompt(relative_dir_path, truncated_content_summary, children_summaries)
    summary_md = generate_text_with_gemini(summary_prompt_final, api_key, model_name, max_tokens, temperature)
    if summary_md is None:
        summary_md = f"# Summary for {relative_dir_path}\\n\\nError: Failed to generate summary from LLM after multiple retries."

    # 2. Generate Mermaid Diagram
    print(f"    LLM: Generating Mermaid diagram for '{relative_dir_path}' using model '{model_name}'...")
    
    # Similar truncation for mermaid prompt, could be different if needed
    if len(concatenated_content) > MAX_CONTENT_CHARS_FOR_PROMPT:
        print(f"    WARNING: Concatenated content for '{relative_dir_path}' is very long ({len(concatenated_content)} chars). Truncating to {MAX_CONTENT_CHARS_FOR_PROMPT} chars for mermaid prompt.")
        truncated_content_mermaid = concatenated_content[:MAX_CONTENT_CHARS_FOR_PROMPT] + "\\n... (content truncated)"
    else:
        truncated_content_mermaid = concatenated_content

    mermaid_prompt_final = generate_directory_mermaid_prompt(relative_dir_path, truncated_content_mermaid, children_summaries)
    mermaid_md = generate_text_with_gemini(mermaid_prompt_final, api_key, model_name, max_tokens, temperature)
    if mermaid_md is None:
        mermaid_md = f"""\`\`\`mermaid
---
title: Error Generating Diagram for {relative_dir_path}
---
flowchart TD
    A[Error] --> B[Failed to generate Mermaid diagram from LLM after multiple retries];
\`\`\`"""
    else:
        # Ensure the LLM output is wrapped in ```mermaid ... ``` if it isn't already
        if not mermaid_md.strip().startswith("```mermaid"):
            mermaid_md = "```mermaid\\n" + mermaid_md
        if not mermaid_md.strip().endswith("```"):
            mermaid_md = mermaid_md + "\\n```"
            
    return {
        "summary_md": summary_md,
        "mermaid_md": mermaid_md
    }

if __name__ == '__main__':
    # Example usage (for testing this module directly)
    print("DEBUG: llm_interaction.py script execution started in __main__.")
    
    # Create a dummy config for testing
    mock_config_data = {
        "llm": {
            "apiKey": "YOUR_API_KEY_HERE", # Replace with a real key for actual testing
            "model": "gemini-1.5-flash-latest", # Or your preferred model
            "settings": {
                "temperature": 0.5,
                "maxTokens": 1000 
            }
        }
    }
    
    # Create a dummy constellation.config.json for the test
    dummy_config_path = os.path.join(CONSTELLATION_ROOT_DIR, "constellation.config.json")
    is_dummy_created = False
    if not os.path.exists(dummy_config_path):
        try:
            with open(dummy_config_path, 'w') as f:
                json.dump(mock_config_data, f, indent=2)
            print(f"DEBUG: Created dummy {CONFIG_FILE} for testing.")
            is_dummy_created = True
        except Exception as e:
            print(f"DEBUG: Could not create dummy config: {e}")

    loaded_llm_config = load_llm_config()

    if not loaded_llm_config or loaded_llm_config.get("apiKey") == "YOUR_API_KEY_HERE":
        print("PST! API Key is 'YOUR_API_KEY_HERE'. Update it in constellation.config.json to run a real test.")
    
    if loaded_llm_config and loaded_llm_config.get("apiKey") != "YOUR_API_KEY_HERE":
        print(f"DEBUG: Loaded LLM Config: {loaded_llm_config}")
        
        # Test generate_text_with_gemini
        print("\\n--- Testing generate_text_with_gemini ---")
        test_prompt = "Explain what a 'flowchart TD' in Mermaid.js is in one sentence."
        generated_text = generate_text_with_gemini(
            prompt_text=test_prompt,
            api_key=loaded_llm_config['apiKey'],
            model_name=loaded_llm_config['model'],
            max_tokens=loaded_llm_config['settings'].get('maxTokens', 100),
            temperature=loaded_llm_config['settings'].get('temperature', 0.7)
        )
        if generated_text:
            print(f"LLM Response for '{test_prompt}':\\n{generated_text}")
        else:
            print(f"Failed to get response for '{test_prompt}'.")

        # Test generate_diagrams_with_llm
        print("\\n--- Testing generate_diagrams_with_llm ---")
        mock_dir_path = "src/components"
        mock_content = """
--- START FILE: src/components/button.js ---
function Button() { return <button>Click me</button>; }
export default Button;
--- END FILE: src/components/button.js ---

--- START FILE: src/components/card.js ---
import Button from './button.js';
function Card({{title, children}}) {{ return <div><h2>{{title}}</h2>{{children}}<Button /></div>; }}
export default Card;
--- END FILE: src/components/card.js ---"""
        mock_children = [
            {"path": "src/components/utils", "files_aggregated_count": 2, "summary_content": "Utility functions."}
        ]
        
        # Need the full config structure for generate_diagrams_with_llm
        full_mock_config_for_test = {"llm": loaded_llm_config}

        llm_outputs = generate_diagrams_with_llm(full_mock_config_for_test, mock_dir_path, mock_content, mock_children)
        print(f"Generated Summary for '{mock_dir_path}':\\n{llm_outputs['summary_md']}")
        print(f"Generated Mermaid for '{mock_dir_path}':\\n{llm_outputs['mermaid_md']}")
    else:
        print("Skipping direct LLM call tests as API key is not set or config not loaded.")

    if is_dummy_created:
        try:
            # Clean up the dummy config file
            # os.remove(dummy_config_path)
            # print(f"DEBUG: Removed dummy {CONFIG_FILE}.")
            print(f"DEBUG: Keeping dummy {CONFIG_FILE} for manual inspection. Please delete it if not needed.")
        except Exception as e:
            print(f"DEBUG: Could not remove dummy config: {e}")
            
    print("DEBUG: llm_interaction.py script execution finished in __main__.")
