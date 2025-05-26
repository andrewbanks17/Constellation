# Project Constellation

Project Constellation is a system designed to automatically generate, update, and visualize architectural and logical diagrams of a codebase. These diagrams are represented as "Diagrams as Code" using the Mermaid.js syntax.

## Setup

1.  **Clone Project Constellation:**
    Clone this repository into the root directory of the project you want to analyze.
    ```bash
    git clone <constellation_repo_url> Constellation
    cd Constellation
    ```

2.  **Create and Activate a Python Virtual Environment:**
    It's highly recommended to use a Python virtual environment to manage dependencies and ensure a consistent environment. Make sure you have Python 3.6+ installed.

    *   Navigate to the `Constellation` directory if you aren't already there.
    *   Create the virtual environment (typically named `.venv`):
        ```powershell
        # For Windows (PowerShell or CMD)
        python -m venv .venv
        ```
        ```bash
        # For macOS/Linux
        python3 -m venv .venv
        ```
    *   Activate the virtual environment:
        *   **Windows (PowerShell):**
            ```powershell
            .venv\Scripts\Activate.ps1
            ```
            (If you encounter an error about script execution being disabled, you might need to run the following command in your PowerShell session and then try activating again: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`)
        *   **Windows (CMD.exe):**
            ```cmd
            .venv\Scripts\activate.bat
            ```
        *   **macOS/Linux (bash/zsh):**
            ```bash
            source .venv/bin/activate
            ```
        Your terminal prompt should now indicate that the virtual environment is active (e.g., `(.venv) PS E:\YourProject\Constellation>`).

3.  **Install Dependencies:**
    (Currently, Project Constellation uses only built-in Python modules. This step is for future dependencies.)
    Once the virtual environment is activated, install the required packages from `requirements.txt` (a blank `requirements.txt` has been created for future use):
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure LLM Settings:**
    Open `constellation.config.json` and update the `llm` section with your API key and preferred model settings.
    ```json
    {
      // ... other configurations ...
      "llm": {
        "apiKey": "YOUR_ACTUAL_API_KEY_HERE",
        "model": "your-preferred-model", // e.g., "gpt-4", "claude-3-opus-20240229"
        "settings": {
          "temperature": 0.7,
          "maxTokens": 2048
        }
      }
    }
    ```

## Usage

(Instructions on how to run Project Constellation will be added here as the project develops.)

For now, to test the directory traversal (which is the first step of analysis):

1.  Ensure your virtual environment is activated.
2.  Run the `directory_traversal.py` script from within the `Constellation` directory:
    ```powershell
    python directory_traversal.py
    ```
    This will scan the parent directory (your project) and print the directories it processes in a post-order traversal, respecting the ignore patterns in `constellation.config.json`.

## How it Works (Overview)

At its heart, Project Constellation works through a multi-stage process, primarily driven by Large Language Models (LLMs) and Git integration:

1.  **Code Analysis:** It first analyzes the codebase to understand its structure, identify key components, and their relationships.
2.  **Diagram Scoping & Initial Generation:** Based on the analysis, it determines what types of diagrams are needed and generates the initial Mermaid.js code.
3.  **Git-Driven Updates:** When new code changes are committed, Constellation detects these changes and instructs an LLM to update the relevant diagrams.
4.  **Visualization & Interaction:** The generated diagrams can be viewed through an interface, allowing users to explore the project's architecture.

(More details from the project overview can be added here.)
