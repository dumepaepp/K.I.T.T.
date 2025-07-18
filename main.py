# main.py
#
# A fully functional AI agent with Nmap and Aircrack-ng integration.
# WARNING: For authorized and ethical use only. Read the setup guide.
#
# SETUP:
# 1. Install Ollama: https://ollama.com/
# 2. Install System Tools: `sudo apt-get install -y nmap aircrack-ng` (or equivalent)
# 3. Pull the model: `ollama pull whiterabbitneo/whiterabbitneo-33b`
# 4. Install Python libs: `pip install langchain langchain-community duckduckgo-search`

import os
import subprocess
import time
import platform
import shlex
from langchain_community.llms import Ollama
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain import hub
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# --- Tool Implementations ---

def run_command(command: str) -> str:
    """
    A helper function to securely run shell commands and return their output.
    Uses shlex.split to prevent shell injection vulnerabilities.
    """
    try:
        print(f"\n--- Running Command: '{command}' ---")
        # Use shlex.split to handle command-line arguments safely.
        args = shlex.split(command)
        # Check if the command requires sudo.
        if "sudo" not in args[0] and os.geteuid() != 0:
             # Certain commands like airodump-ng need root privileges.
             # We can check for specific commands if needed.
             if any(cmd in args for cmd in ["airodump-ng", "aireplay-ng"]):
                 print("INFO: This command may require root privileges. Prepending 'sudo'.")
                 args.insert(0, "sudo")

        process = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False, # Set to False to handle non-zero exit codes manually.
            timeout=300  # 5-minute timeout for long scans.
        )
        if process.returncode != 0:
            # Return both stdout and stderr for better debugging by the agent.
            return f"Error executing command. Return Code: {process.returncode}\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
        return process.stdout
    except FileNotFoundError:
        return f"Error: The command '{shlex.split(command)[0]}' was not found. Is it installed and in your PATH?"
    except subprocess.TimeoutExpired:
        return "Error: The command took too long to execute and was timed out."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def nmap_scan(target_and_args: str) -> str:
    """
    Runs an Nmap scan with the given arguments against a target.
    Example: 'nmap -sV -p 1-1000 192.168.1.1'
    For security, only allows commands that start with 'nmap'.
    """
    if not target_and_args.strip().startswith("nmap "):
        return "Invalid input. The command must start with 'nmap '."
    return run_command(target_and_args)

def aircrack_scan(args: str) -> str:
    """
    Runs an Aircrack-ng suite command (e.g., airodump-ng, aireplay-ng).
    Example: 'airodump-ng wlan0mon'
    For security, only allows commands starting with 'airodump-ng', 'aireplay-ng', or 'aircrack-ng'.
    """
    command_parts = args.strip().split()
    if not command_parts or command_parts[0] not in ["airodump-ng", "aireplay-ng", "aircrack-ng"]:
        return "Invalid input. Command must start with 'airodump-ng', 'aireplay-ng', or 'aircrack-ng'."
    return run_command(args)

def internet_search(query: str) -> str:
    """Performs an internet search using DuckDuckGo."""
    print(f"\n--- Performing Internet Search for: '{query}' ---")
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=5)]
            return "\n".join([f"Title: {res['title']}\nSnippet: {res['body']}\nURL: {res['href']}\n"]) if results else "No results found."
    except Exception as e:
        return f"An error occurred during web search: {e}"

def self_enhancement_tool_func(llm: Ollama) -> callable:
    """Creates the self-enhancement tool."""
    enhancement_prompt = PromptTemplate(
        input_variables=["user_objective"],
        template="You are a meta-cognitive AI. Improve the following objective: '{user_objective}'"
    )
    enhancement_chain = LLMChain(llm=llm, prompt=enhancement_prompt)
    def run_enhancement(user_objective: str) -> str:
        print(f"\n--- Engaging Self-Enhancement for: '{user_objective}' ---")
        try:
            return enhancement_chain.invoke({"user_objective": user_objective}).get('text', 'Failed to get enhancement response.')
        except Exception as e:
            return f"An error occurred during self-enhancement: {e}"
    return run_enhancement

# --- Main Agent Class ---

class EnhancedAIAgent:
    """The main class for our AI agent."""
    def __init__(self, model_name="whiterabbitneo/whiterabbitneo-33b"):
        print("Initializing the Enhanced AI Agent...")
        self.agent_executor = None
        if os.geteuid() != 0:
            print("\nWARNING: You are not running this script as root.")
            print("Nmap and Aircrack-ng tools may require sudo privileges to function correctly.\n")

        try:
            self.llm = Ollama(model=model_name, temperature=0.1)
            self.llm.invoke("Hello?", stop=["?"])
            print("Successfully connected to Ollama model.")
        except Exception:
            print("Could not connect to Ollama. Attempting to start the server...")
            try:
                # Simplified server start logic for brevity
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(5)
                self.llm = Ollama(model=model_name, temperature=0.1)
                self.llm.invoke("Hello?", stop=["?"])
                print("Successfully started and connected to Ollama model.")
            except Exception as e:
                print(f"\nFATAL ERROR: Failed to start or connect to Ollama. Please start it manually. Details: {e}")
                return

        self.tools = [
            Tool(name="InternetSearch", func=internet_search, description="Searches the internet for information. Input is a search query."),
            Tool(name="SelfEnhancement", func=self_enhancement_tool_func(self.llm), description="Analyzes and improves a complex plan or prompt. Input is the objective to enhance."),
            Tool(name="NmapScan", func=nmap_scan, description="Executes an Nmap scan to discover hosts, ports, and services on a network. Input must be a valid Nmap command string (e.g., 'nmap -sV 192.168.1.1')."),
            Tool(name="AircrackScan", func=aircrack_scan, description="Executes a command from the Aircrack-ng suite for WiFi security analysis. Input must be a valid command string (e.g., 'airodump-ng wlan0mon').")
        ]
        prompt = hub.pull("hwchase17/react")
        agent = create_react_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, handle_parsing_errors=True)
        print("Agent initialized successfully.")

    def run(self, prompt: str):
        if not self.agent_executor:
            print("Cannot run because the agent failed to initialize.")
            return
        print(f"\n--- Starting Agent Run with Prompt ---\n'{prompt}'\n---------------------------------------\n")
        try:
            response = self.agent_executor.invoke({"input": prompt})
            print(f"\n--- Agent Run Finished ---\nFinal Answer: {response['output']}")
        except Exception as e:
            print(f"An error occurred while running the agent: {e}")

if __name__ == "__main__":
    agent = EnhancedAIAgent()
    if agent.agent_executor:
        print("\nWelcome to the Interactive AI Agent with Networking Tools.")
        print("WARNING: Use these tools responsibly and only on authorized networks.")
        print("Enter your prompt below. Type 'exit' or 'quit' to end.")
        while True:
            try:
                user_prompt = input("\nYour Prompt: ")
                if user_prompt.lower() in ["exit", "quit"]:
                    print("Exiting agent session. Goodbye!")
                    break
                if user_prompt:
                    agent.run(user_prompt)
            except KeyboardInterrupt:
                print("\nExiting agent session. Goodbye!")
                break
