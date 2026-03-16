#!/usr/bin/env python3
"""
Tiny Model Swarm - Terminal Chat Interface
Chat with multiple small models simultaneously!
"""

import requests
import json
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style
import readline  # This gives you arrow key navigation in input

# Initialize colorama for colored output
init()

# Your tiny models
MODELS = [
    "tinyllama:1.1b",
    "qwen:0.5b", 
    "tinydolphin:1.1b",
    "driaforall/tiny-agent-a:0.5b",
    "nehcgs/Arch-Agent:1.5b",
    "deepseek-r1:1.5b"
]

OLLAMA_URL = "http://localhost:11434/api/generate"

# Color scheme for different models
MODEL_COLORS = {
    "tinyllama:1.1b": Fore.CYAN,
    "qwen:0.5b": Fore.GREEN,
    "tinydolphin:1.1b": Fore.YELLOW,
    "driaforall/tiny-agent-a:0.5b": Fore.MAGENTA,
    "nehcgs/Arch-Agent:1.5b": Fore.BLUE,
    "deepseek-r1:1.5b": Fore.RED
}

def print_banner():
    """Show a cool banner when starting"""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════╗
{Fore.CYAN}║     🐝 Tiny Model Swarm - Terminal Chat              ║
{Fore.CYAN}║     {len(MODELS)} models running simultaneously            ║
{Fore.CYAN}╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)
    print(f"{Fore.WHITE}Commands:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}/models{Style.RESET_ALL} - List all active models")
    print(f"  {Fore.GREEN}/select model1,model2{Style.RESET_ALL} - Chat with specific models only")
    print(f"  {Fore.GREEN}/parallel N{Style.RESET_ALL} - Set number of parallel requests (default: 3)")
    print(f"  {Fore.GREEN}/clear{Style.RESET_ALL} - Clear the screen")
    print(f"  {Fore.GREEN}/quit{Style.RESET_ALL} - Exit")
    print(f"{Fore.YELLOW}Just type anything and press Enter to chat with ALL models!{Style.RESET_ALL}\n")

def query_model(model, prompt):
    """Query a single model and return response"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 500
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if response.status_code == 200:
            return model, response.json().get("response", ""), None
        else:
            return model, None, f"HTTP {response.status_code}"
    except Exception as e:
        return model, None, str(e)

def chat_with_swarm(prompt, selected_models=None, max_workers=3):
    """Send prompt to multiple models and show responses in real-time"""
    models_to_use = selected_models if selected_models else MODELS
    
    print(f"\n{Fore.WHITE}📨 {prompt}{Style.RESET_ALL}\n")
    print(f"{Fore.WHITE}─" * 60)
    
    # Show which models are thinking
    thinking_msg = f"{Fore.YELLOW}🤔 Models thinking: "
    thinking_msg += ", ".join([m.split(':')[0] for m in models_to_use])
    print(thinking_msg + f"{Style.RESET_ALL}\n")
    
    # Send requests in parallel
    responses = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(query_model, model, prompt): model 
                  for model in models_to_use}
        
        for future in as_completed(futures):
            model, response, error = future.result()
            color = MODEL_COLORS.get(model, Fore.WHITE)
            
            if error:
                print(f"{color}📌 {model}:{Style.RESET_ALL}")
                print(f"  {Fore.RED}⚠️ Error: {error}{Style.RESET_ALL}\n")
            else:
                print(f"{color}📌 {model}:{Style.RESET_ALL}")
                # Pretty print the response with word wrap
                words = response.split()
                line = "  "
                for word in words:
                    if len(line) + len(word) + 1 > 80:
                        print(line)
                        line = "  " + word + " "
                    else:
                        line += word + " "
                if line:
                    print(line)
                print()
            
            print(f"{Fore.WHITE}─" * 60)
    
    print(f"{Fore.GREEN}✨ All models have responded!{Style.RESET_ALL}\n")

def main():
    """Main chat loop"""
    print_banner()
    
    selected_models = None
    max_workers = 3
    
    while True:
        try:
            # Get user input with nice prompt
            user_input = input(f"{Fore.YELLOW}You{Style.RESET_ALL} > ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input == "/quit":
                print(f"{Fore.CYAN}👋 Goodbye!{Style.RESET_ALL}")
                break
            elif user_input == "/clear":
                print("\033[2J\033[H", end="")  # Clear screen
                print_banner()
                continue
            elif user_input == "/models":
                print(f"\n{Fore.WHITE}Active Models:{Style.RESET_ALL}")
                for i, model in enumerate(MODELS, 1):
                    color = MODEL_COLORS.get(model, Fore.WHITE)
                    print(f"  {color}{i}. {model}{Style.RESET_ALL}")
                print()
                continue
            elif user_input.startswith("/select"):
                # Select specific models: /select tinyllama,qwen
                parts = user_input.split()
                if len(parts) > 1:
                    model_names = parts[1].split(',')
                    selected_models = []
                    for name in model_names:
                        matching = [m for m in MODELS if name in m]
                        selected_models.extend(matching)
                    if selected_models:
                        print(f"{Fore.GREEN}✓ Now chatting with: {', '.join(selected_models)}{Style.RESET_ALL}\n")
                    else:
                        print(f"{Fore.RED}No matching models found{Style.RESET_ALL}\n")
                continue
            elif user_input.startswith("/parallel"):
                # Set parallel requests: /parallel 4
                try:
                    max_workers = int(user_input.split()[1])
                    print(f"{Fore.GREEN}✓ Parallel requests set to {max_workers}{Style.RESET_ALL}\n")
                except:
                    print(f"{Fore.RED}Usage: /parallel N{Style.RESET_ALL}\n")
                continue
            
            # Regular chat - send to all selected models
            chat_with_swarm(user_input, selected_models, max_workers)
            
        except KeyboardInterrupt:
            print(f"\n{Fore.CYAN}👋 Goodbye!{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    # Check if Ollama is running
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
    except:
        print(f"{Fore.RED}❌ Cannot connect to Ollama. Make sure it's running!{Style.RESET_ALL}")
        print("Run: systemctl --user start ollama")
        sys.exit(1)
    
    main()
