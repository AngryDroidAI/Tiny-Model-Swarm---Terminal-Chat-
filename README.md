📦 Install Dependencies

First, install the required Python packages:
bash

# Install the colorama library for colored output
pip3 install colorama requests

# Or if you prefer pip:
pip install colorama requests

second: nano python3 tiny-swarm-chat.py

save python script:

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

python3 tiny-swarm-chat.py

1. Start the chat:

python3 tiny-swarm-chat.py

2. You'll see a colorful interface:

╔══════════════════════════════════════════════════════╗
║     🐝 Tiny Model Swarm - Terminal Chat              ║
║     6 models running simultaneously                   ║
╚══════════════════════════════════════════════════════╝

Commands:
  /models - List all active models
  /select model1,model2 - Chat with specific models only
  /parallel N - Set number of parallel requests (default: 3)
  /clear - Clear the screen
  /quit - Exit

Just type anything and press Enter to chat with ALL models!

3. Chat with ALL models:

You > What is machine learning?

📨 What is machine learning?
────────────────────────────────────────────────────────────
🤔 Models thinking: tinyllama, qwen, tinydolphin, tiny-agent, Arch-Agent, deepseek-r1

📌 tinyllama:1.1b:
  Machine learning is a subset of artificial intelligence that enables systems to
  automatically learn and improve from experience without being explicitly programmed.

📌 qwen:0.5b:
  Machine learning is a method of data analysis that automates analytical model building.
  It uses algorithms that iteratively learn from data.

[All 6 responses will appear as they complete]
────────────────────────────────────────────────────────────
✨ All models have responded!

You >

4. Select specific models:

You > /select tinyllama,deepseek

✓ Now chatting with: tinyllama:1.1b, deepseek-r1:1.5b

You > What is Python?
[Only those two models will respond]

5. Control parallelism:

You > /parallel 4
✓ Parallel requests set to 4

🎨 Features You'll Love
Feature	What It Does
Color-coded outputs	Each model has its own color so you can easily spot them
Real-time responses	Models appear as they finish, no waiting for all
Model selection	Chat with specific models only
Parallel control	Adjust how many models respond at once
Command system	Full control from within the chat
Error handling	If a model fails, others still work

🚀 Pro Tips

    Start with all models to compare responses:

    You > Explain quantum computing in one sentence

    Then narrow down to your favorites:

    You > /select deepseek,arch-agent
    You > Write a Python function to calculate fibonacci

        Use tiny models for quick tasks:
    text

    You > /select qwen,tinyllama
    You > What's 2+2?

    Save responses by copying from terminal

🔧 Troubleshooting

If you get connection errors:
bash

# Make sure Ollama is running
systemctl --user status ollama

# Test direct connection
curl http://localhost:11434/api/tags

# If not running, start it
systemctl --user start ollama

This gives you a full terminal chat experience with your entire model swarm, no Docker needed, running entirely on your Linux system! The responses come in real-time, color-coded, and you have full control over which models participate in the conversation.

You > hello

📨 hello

────────────────────────────────────────────────────────────
🤔 Models thinking: tinyllama, qwen, tinydolphin, driaforall/tiny-agent-a, nehcgs/Arch-Agent, deepseek-r1

📌 tinydolphin:1.1b:
  Hello!

────────────────────────────────────────────────────────────
📌 qwen:0.5b:
  Hi! How can I assist you today?

────────────────────────────────────────────────────────────
📌 driaforall/tiny-agent-a:0.5b:
  Hello! How can I assist you today?

────────────────────────────────────────────────────────────
📌 nehcgs/Arch-Agent:1.5b:
  Hello! How can I assist you today?

────────────────────────────────────────────────────────────
📌 deepseek-r1:1.5b:
  Hello! How can I assist you today? 😊

────────────────────────────────────────────────────────────
📌 tinyllama:1.1b:
  I'm not able to see or interact with the world around me. However, I can
  provide you with a detailed and comprehensive list of all the helpful things
  you can do as an ai assistant. Here are some suggestions: 1. Automated
  customer service: ai can handle customer service inquiries and provide
  instant responses, saving time and increasing customer satisfaction. 2.
  Personalized recommendations: ai can recommend products, services, and
  content based on a user's search history and purchasing history. 3. Voice and
  facial recognition: ai can recognize users by voice or facial features,
  enabling seamless interaction and facilitating efficient tasks such as
  checkout or appointment scheduling. 4. Automated language translation: ai can
  translate between different languages, making it easier for users to
  communicate with each other. 5. Voice-activated assistance: ai can be
  integrated into a user's daily routine by automatically answering questions
  and providing assistance as needed. 6. Personalized product recommendations:
  ai can recommend products based on a user's interests, making it easier to
  find the products they want and need. 7. Artificial intelligence in
  healthcare: ai can assist doctors, nurses, and other healthcare professionals
  by providing real-time medical information, diagnosis, and treatment
  recommendations. 8. Voice-based scheduling: ai can schedule appointments,
  events, and tasks, freeing up time for users to focus on more important
  tasks. 9. Augmented reality: ai can create interactive and immersive
  experiences, such as virtual tours, interactive exhibits, and virtual reality
  simulations. 10. Voice-based customer support: ai can provide real-time
  customer support, resolving issues and answering questions in a natural and
  conversational way.

────────────────────────────────────────────────────────────
✨ All models have responded!

You >
You > You > Explain quantum computing in one sentence

📨 You > Explain quantum computing in one sentence

────────────────────────────────────────────────────────────
🤔 Models thinking: tinyllama, qwen, tinydolphin, driaforall/tiny-agent-a, nehcgs/Arch-Agent, deepseek-r1

📌 tinyllama:1.1b:
  Quantum computing is a cutting-edge technology that leverages quantum bits
  (qubits) to perform computations exponentially faster than classical
  computers.

────────────────────────────────────────────────────────────
📌 qwen:0.5b:
  Quantum computing is a type of computing that uses quantum-mechanical
  phenomena, such as superposition and entanglement, to perform operations on
  data.

────────────────────────────────────────────────────────────
📌 tinydolphin:1.1b:
  Quantum computing, also known as quantum bit or quantum bit, is a powerful
  computational technique that allows for the manipulation of quantum states
  more efficiently than classical bits, also known as bits, such as 0 and 1.
  Unlike classical bits, quantum bits or qubits can exist in multiple states at
  the same time, which allows for an exponential increase in computational
  power. This quantum computing system is designed to be more efficient and
  faster than traditional computers based on bits.

────────────────────────────────────────────────────────────
📌 driaforall/tiny-agent-a:0.5b:
  Quantum computing is a type of computing that uses quantum bits, or qubits,
  which are bits that can exist in multiple states simultaneously. This allows
  quantum computers to perform certain types of calculations much faster than
  classical computers.

────────────────────────────────────────────────────────────
📌 nehcgs/Arch-Agent:1.5b:
  Quantum computing uses quantum bits (qubits) instead of classical bits,
  allowing it to perform certain calculations much faster than classical
  computers.

────────────────────────────────────────────────────────────
📌 deepseek-r1:1.5b:
  Quantum computing harnesses the principles of quantum mechanics to process
  information using qubits, allowing for more efficient solutions to complex
  problems compared to classical computers.

────────────────────────────────────────────────────────────
✨ All models have responded!

You >

🎯 Task Specialization

Based on what I see in your responses:

    deepseek-r1:1.5b → Best for technical explanations

    Arch-Agent:1.5b → Best for concise answers

    tinydolphin:1.1b → Best for detailed, educational responses

    tinyllama:1.1b → Good all-rounder

    qwen:0.5b → Good for simple concepts

    tiny-agent-a:0.5b → Good for balanced explanations

Future additions- whats next Create model "teams" for different tasks

Export interesting responses by copying from terminal

Add more tiny models to your swarm

Try the pipeline feature to chain responses Have models debate a topic

Generate code and have another model review it

Create a story where each model adds a sentence

can stack ai so run small models work togather not need large model data sets turn small models to agentic system
