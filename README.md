
python3 tiny-swarm-chat.py

════════════════════════════════════════════════════════════╗
║     🚀 TINY MODEL SWARM - DIRECT MODE                    ║
╠════════════════════════════════════════════════════════════╣
║  📊 Models:       37 installed locally               ║
║  💾 Exports:      /home/ngryroid/.tiny-swarm-data/exports ║
║  📈 Benchmarks:   /home/ngryroid/.tiny-swarm-data/benchmarks ║
║  💬 Conversations:/home/ngryroid/.tiny-swarm-data/conversations ║
╠════════════════════════════════════════════════════════════╣
║  ✨ FEATURES:                                            ║
║  • Chat with multiple models simultaneously             ║
║  • No timeout by default (set with /timeout N)          ║
║  • Benchmark models side-by-side                        ║
║  • Compare responses quality                            ║
║  • Export to JSON/CSV/Markdown                          ║
║  • Batch processing mode                                ║
║  • Custom system prompts                                ║
║  • Performance statistics                               ║
╚════════════════════════════════════════════════════════════╝

✅ Connected to Ollama
✅ 37 models available
ℹ  No timeout by default. Use /timeout N to set timeout

📚 COMMANDS:

CHAT:
  /list              - Show available models
  /select m1,m2      - Select specific models
  /select-small      - Select the 6 smallest models
  /parallel N        - Set parallel workers (default: 3)
  /timeout [N]       - Set timeout in seconds (no arg = no timeout)

EXPORT:
  /export [json|csv|md] - Export conversation
  /save              - Save conversation (JSON)

BENCHMARK:
  /benchmark [timeout] - Run benchmarks (optional timeout)
  /compare <prompt>  - Compare models
  /stats             - Show performance stats

BATCH:
  /batch <file> [json|csv] [timeout] - Process prompts file

SYSTEM:
  /system <model> <prompt> - Set system prompt
  /clear             - Clear screen
  /quit              - Exit

EXAMPLES:
  /select-small                    # Use 6 smallest models
  /timeout 30                      # Set 30s timeout
  /timeout                         # Disable timeout
  /compare "What is Python?"       # Compare with no timeout
  /compare "Hello" 60              # Compare with 60s timeout
  /batch prompts.txt csv 120       # Batch with 120s timeout


This is a comprehensive Python script called "Tiny Model Swarm - Direct Mode" that creates a multi-model chat interface for interacting with local AI models through Ollama. Here's a detailed description:
Overview

A terminal-based application that allows you to chat with multiple local AI models simultaneously, compare their responses, run benchmarks, and process batches of prompts.
Key Features
1. Multi-Model Chat

    Query multiple Ollama models at once with parallel processing

    Real-time responses with color-coded output for different models

    Configurable parallel workers (default: 3)

    No timeout by default (configurable per request)

2. Model Management

    Automatically detects available models from Ollama

    Pre-configured with 33+ models including:

        Cloud models (Nemotron, Mistral, Gemini, etc.)

        Small local models (0.5B to 8B parameters)

        Specialized models (coding, reasoning, etc.)

    Models grouped by type for easier selection

    Quick-select for smallest 6 models

3. Benchmarking & Comparison

    Run performance benchmarks across multiple models

    Compare responses side-by-side

    Track metrics:

        Response times

        Success rates

        Response lengths

        Timeout counts

4. Export & Data Management

    Export conversations to:

        JSON (full conversation data)

        CSV (tabular format)

        Markdown (readable documentation)

    Automatic saving to ~/.tiny-swarm-data/

    Organized directories for exports, benchmarks, and conversations

5. Batch Processing

    Process multiple prompts from a text file

    Choose output format (JSON/CSV)

    Configurable timeouts per request

6. System Prompts

    Set custom system prompts for individual models

    Persistent storage in config files

Interactive Commands
Chat Commands

    /list - Show available models

    /select m1,m2 - Select specific models

    /select-small - Use 6 smallest models

    /parallel N - Set concurrent workers

    /timeout [N] - Set request timeout (no arg = no timeout)

Export Commands

    /export [json|csv|md] - Export current conversation

    /save - Quick save as JSON

Benchmark Commands

    /benchmark [timeout] - Run performance tests

    /compare <prompt> [timeout] - Compare model responses

    /stats - Show performance statistics

Batch Commands

    /batch <file> [format] [timeout] - Process prompt file

System Commands

    /system <model> <prompt> - Set system prompt

    /clear - Clear screen

    /quit - Exit

Technical Details
Dependencies

    requests - API calls to Ollama

    colorama - Colored terminal output

    concurrent.futures - Parallel processing

    Standard library: json, csv, pathlib, datetime, etc.

Data Storage
text

~/.tiny-swarm-data/
├── exports/       # Comparison exports
├── benchmarks/    # Benchmark results
├── conversations/ # Chat history
└── configs/       # Model configurations

Architecture

    ThreadPoolExecutor for parallel model queries

    Color-coded output per model for easy differentiation

    Timeout handling at individual request level

    Automatic dependency installation with fallbacks

    Persistent storage with proper permissions (0o700)

Use Cases

    Model Comparison: Compare how different models respond to the same prompt

    Performance Testing: Benchmark response times and success rates

    Batch Processing: Process multiple prompts for testing or data collection

    Development Testing: Test prompts across multiple models simultaneously

    Research: Collect response data for analysis

    Educational: Compare different AI models' capabilities

Key Design Choices

    No default timeout - Allows long-running responses

    Parallel processing - Efficient use of resources

    Color-coded output - Easy visual distinction between models

    Modular commands - Extensible command system

    Automatic setup - Creates directories and installs dependencies

    Fallback imports - Graceful handling of missing packages

The script is particularly useful for developers, researchers, and AI enthusiasts who want to test and compare multiple local language models efficiently from a single interface.

#!/usr/bin/env python3
"""
Tiny Model Swarm - Direct Mode
Works with your existing Ollama installation
All features: benchmarking, exports, comparisons, batch processing
"""

import subprocess
import sys
import os
import signal
import atexit
from pathlib import Path
import time
import csv
from datetime import datetime
import hashlib

# Try to import with fallbacks
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "requests"])
    import requests

try:
    from colorama import init, Fore, Style
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "colorama"])
    from colorama import init, Fore, Style

try:
    import readline
except ImportError:
    pass

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import threading

# Initialize colorama
init()

# Data directories
DATA_DIR = Path.home() / ".tiny-swarm-data"
EXPORTS_DIR = DATA_DIR / "exports"
BENCHMARKS_DIR = DATA_DIR / "benchmarks"
CONVERSATIONS_DIR = DATA_DIR / "conversations"
CONFIGS_DIR = DATA_DIR / "configs"

# Create directories
for dir_path in [DATA_DIR, EXPORTS_DIR, BENCHMARKS_DIR, CONVERSATIONS_DIR, CONFIGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
    dir_path.chmod(0o700)

# Your models from 'ollama list'
YOUR_MODELS = [
    # Cloud models (marked with -cloud)
    {"name": "nemotron-3-super:cloud", "size": "-", "type": "nemotron", "description": "Nemotron 3 Super"},
    {"name": "qwen3.5:9b", "size": "6.6 GB", "type": "qwen", "description": "Qwen 3.5 9B"},
    {"name": "ALIENTELLIGENCE/sarahv2:latest", "size": "4.7 GB", "type": "sarah", "description": "Sarah V2"},
    {"name": "nemotron-3-nano:30b-cloud", "size": "-", "type": "nemotron", "description": "Nemotron 3 Nano 30B"},
    {"name": "gurubot/girl:3b-q4_K_M", "size": "2.2 GB", "type": "gurubot", "description": "Gurubot Girl 3B"},
    {"name": "jaahas/qwen3-abliterated:0.6b", "size": "396 MB", "type": "qwen", "description": "Qwen3 abliterated 0.6B"},
    {"name": "huihui_ai/acereason-nemotron-abliterated:7b", "size": "4.7 GB", "type": "nemotron", "description": "Acereason Nemotron abliterated 7B"},
    {"name": "cipher64/darkseek:latest", "size": "4.9 GB", "type": "darkseek", "description": "Darkseek"},
    {"name": "mistral-large-3:675b-cloud", "size": "-", "type": "mistral", "description": "Mistral Large 3"},
    {"name": "devstral-2:123b-cloud", "size": "-", "type": "devstral", "description": "Devstral 2"},
    {"name": "deepseek-v3.2:cloud", "size": "-", "type": "deepseek", "description": "DeepSeek V3.2"},
    {"name": "gemini-3-flash-preview:cloud", "size": "-", "type": "gemini", "description": "Gemini 3 Flash"},
    {"name": "kimi-k2.5:cloud", "size": "-", "type": "kimi", "description": "Kimi K2.5"},
    {"name": "minimax-m2.5:cloud", "size": "-", "type": "minimax", "description": "Minimax M2.5"},
    {"name": "glm-5:cloud", "size": "-", "type": "glm", "description": "GLM-5"},
    {"name": "qwen3-coder-next:cloud", "size": "-", "type": "qwen", "description": "Qwen3 Coder Next"},
    {"name": "qwen3.5:397b-cloud", "size": "-", "type": "qwen", "description": "Qwen3.5 397B"},
    {"name": "kimi-k2-thinking:cloud", "size": "-", "type": "kimi", "description": "Kimi K2 Thinking"},
    {"name": "qwen3-next:80b-cloud", "size": "-", "type": "qwen", "description": "Qwen3 Next 80B"},
    {"name": "deepseek-v3.1:671b-cloud", "size": "-", "type": "deepseek", "description": "DeepSeek V3.1"},
    {"name": "cogito-2.1:671b-cloud", "size": "-", "type": "cogito", "description": "Cogito 2.1"},
    {"name": "qwen3-coder:480b-cloud", "size": "-", "type": "qwen", "description": "Qwen3 Coder"},
    {"name": "gpt-oss:120b-cloud", "size": "-", "type": "gpt", "description": "GPT OSS"},
    {"name": "minimax-m2:cloud", "size": "-", "type": "minimax", "description": "Minimax M2"},
    {"name": "glm-4.6:cloud", "size": "-", "type": "glm", "description": "GLM-4.6"},
    {"name": "qwen3-vl:235b-cloud", "size": "-", "type": "qwen", "description": "Qwen3 VL"},
    {"name": "gemma3:27b-cloud", "size": "-", "type": "gemma", "description": "Gemma 3"},
    {"name": "nehcgs/Arch-Agent:1.5b", "size": "3.1 GB", "type": "arch", "description": "Arch Agent 1.5B"},
    {"name": "deepseek-r1:1.5b", "size": "1.1 GB", "type": "deepseek", "description": "DeepSeek R1 1.5B"},
    {"name": "tinyllama:1.1b", "size": "637 MB", "type": "llama", "description": "TinyLlama 1.1B"},
    {"name": "tinydolphin:1.1b", "size": "636 MB", "type": "dolphin", "description": "TinyDolphin 1.1B"},
    {"name": "qwen:0.5b", "size": "394 MB", "type": "qwen", "description": "Qwen 0.5B"},
    {"name": "hhao/qwen2.5-coder-tools:0.5b", "size": "994 MB", "type": "qwen", "description": "Qwen2.5 Coder Tools"},
    {"name": "driaforall/tiny-agent-a:0.5b", "size": "531 MB", "type": "agent", "description": "Tiny Agent A"},
    {"name": "qwen3:8b", "size": "5.2 GB", "type": "qwen", "description": "Qwen3 8B"},
    {"name": "deepseek-r1:8b", "size": "5.2 GB", "type": "deepseek", "description": "DeepSeek R1 8B"},
    {"name": "goekdenizguelmez/JOSIEFIED-Qwen3:8b", "size": "5.0 GB", "type": "qwen", "description": "JOSIEFIED Qwen3"}
]

# Group models by type for better organization
MODELS_BY_TYPE = {}
for model in YOUR_MODELS:
    model_type = model["type"]
    if model_type not in MODELS_BY_TYPE:
        MODELS_BY_TYPE[model_type] = []
    MODELS_BY_TYPE[model_type].append(model)

# Color scheme
COLORS = [Fore.CYAN, Fore.GREEN, Fore.YELLOW, Fore.MAGENTA, Fore.RED, Fore.BLUE, Fore.WHITE]
MODEL_COLORS = {}
for i, model in enumerate(YOUR_MODELS):
    MODEL_COLORS[model["name"]] = COLORS[i % len(COLORS)]

# Small models preset (your 6 smallest)
SMALL_MODELS = [
    "qwen:0.5b",
    "jaahas/qwen3-abliterated:0.6b",
    "driaforall/tiny-agent-a:0.5b",
    "tinyllama:1.1b",
    "tinydolphin:1.1b",
    "deepseek-r1:1.5b"
]

# Track response times and metrics
response_times = {}
response_quality = {}
benchmark_results = {}
current_conversation = []
conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
# Default timeout (None = no timeout)
default_timeout = None

def print_banner():
    """Print banner"""
    banner = f"""
{Fore.RED}╔════════════════════════════════════════════════════════════╗
{Fore.RED}║     🚀 TINY MODEL SWARM - DIRECT MODE                    ║
{Fore.RED}╠════════════════════════════════════════════════════════════╣
{Fore.YELLOW}║  📊 Models:       {len(YOUR_MODELS)} installed locally               ║
{Fore.YELLOW}║  💾 Exports:      {str(EXPORTS_DIR):<35} ║
{Fore.YELLOW}║  📈 Benchmarks:   {str(BENCHMARKS_DIR):<35} ║
{Fore.YELLOW}║  💬 Conversations:{str(CONVERSATIONS_DIR):<35} ║
{Fore.RED}╠════════════════════════════════════════════════════════════╣
{Fore.GREEN}║  ✨ FEATURES:                                            ║
{Fore.GREEN}║  • Chat with multiple models simultaneously             ║
{Fore.GREEN}║  • No timeout by default (set with /timeout N)          ║
{Fore.GREEN}║  • Benchmark models side-by-side                        ║
{Fore.GREEN}║  • Compare responses quality                            ║
{Fore.GREEN}║  • Export to JSON/CSV/Markdown                          ║
{Fore.GREEN}║  • Batch processing mode                                ║
{Fore.GREEN}║  • Custom system prompts                                ║
{Fore.GREEN}║  • Performance statistics                               ║
{Fore.RED}╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

def get_available_models():
    """Get list of available models from Ollama"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [model["name"] for model in models]
    except:
        pass
    return []

def query_model(model, prompt, timeout=None, system_prompt=None):
    """Query a model with optional timeout"""

    # Load system prompt if exists
    config_file = CONFIGS_DIR / f"{model.replace(':', '_').replace('/', '_')}.json"
    if not system_prompt and config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
            system_prompt = config.get("system_prompt", "")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 500,
            "num_ctx": 2048
        }
    }

    if system_prompt:
        payload["system"] = system_prompt

    start_time = time.time()
    timeout_msg = f" (timeout: {timeout}s)" if timeout else " (no timeout)"

    try:
        # Use timeout if specified, otherwise wait indefinitely
        if timeout:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=timeout
            )
        else:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload
            )

        elapsed = time.time() - start_time

        if response.status_code == 200:
            return model, response.json().get("response", ""), None, elapsed
        else:
            return model, None, f"HTTP {response.status_code}", elapsed

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        return model, None, f"Timeout after {timeout}s", elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        return model, None, str(e), elapsed

def chat_with_swarm(prompt, selected_models=None, max_workers=3, timeout=None):
    """Chat with multiple models simultaneously"""
    available_models = get_available_models()

    if not available_models:
        print(f"{Fore.RED}❌ No models available. Is Ollama running?{Style.RESET_ALL}")
        return

    # Add user message to conversation
    current_conversation.append({
        "timestamp": datetime.now().isoformat(),
        "role": "user",
        "message": prompt
    })

    if selected_models:
        models_to_use = [m for m in selected_models if m in available_models]
    else:
        # Use all available models (but limit to avoid overwhelming)
        models_to_use = available_models[:10]  # Limit to 10 models max

    if not models_to_use:
        print(f"{Fore.RED}❌ No matching models available.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.WHITE}📨 {prompt}{Style.RESET_ALL}\n")
    print(f"{Fore.WHITE}─" * 80)

    # Show which models are thinking
    model_names = [m.split(':')[0] if ':' in m else m[:15] for m in models_to_use]
    timeout_status = f" | Timeout: {timeout}s" if timeout else " | No timeout"
    print(f"{Fore.YELLOW}🤔 Getting responses from {len(models_to_use)} models: {', '.join(model_names)}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}⏱️  Parallel: {max_workers}{timeout_status}{Style.RESET_ALL}\n")

    times = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(query_model, model, prompt, timeout): model
                  for model in models_to_use}

        completed = 0
        for future in as_completed(futures):
            model, response, error, elapsed = future.result()
            color = MODEL_COLORS.get(model, Fore.WHITE)

            times[model] = elapsed
            response_times[model] = response_times.get(model, []) + [elapsed]

            completed += 1

            if error:
                print(f"{color}📌 {model}:{Style.RESET_ALL}")
                print(f"  {Fore.RED}⚠️ Error: {error}{Style.RESET_ALL}")
                print(f"  {Fore.YELLOW}⏱️  Time: {elapsed:.1f}s{Style.RESET_ALL}\n")
            else:
                print(f"{color}📌 {model}:{Style.RESET_ALL}")
                print(f"  {Fore.YELLOW}⏱️  Time: {elapsed:.1f}s{Style.RESET_ALL}")

                # Add to conversation
                current_conversation.append({
                    "timestamp": datetime.now().isoformat(),
                    "role": "assistant",
                    "model": model,
                    "message": response,
                    "response_time": elapsed
                })

                # Pretty print response
                words = response.split()
                line = "  "
                for word in words:
                    if len(line) + len(word) + 1 > 78:
                        print(line)
                        line = "  " + word + " "
                    else:
                        line += word + " "
                if line:
                    print(line)
                print()

            print(f"{Fore.WHITE}─" * 80)

    print(f"{Fore.GREEN}✨ All {completed} models have responded!{Style.RESET_ALL}")

    # Show stats
    if times:
        fastest = min(times.items(), key=lambda x: x[1])
        slowest = max(times.items(), key=lambda x: x[1])
        print(f"{Fore.CYAN}⚡ Fastest: {fastest[0]} ({fastest[1]:.1f}s){Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}🐢 Slowest: {slowest[0]} ({slowest[1]:.1f}s){Style.RESET_ALL}")
    print()

def export_conversation(format="json"):
    """Export current conversation"""
    if not current_conversation:
        print(f"{Fore.YELLOW}No conversation to export{Style.RESET_ALL}")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "json":
        filename = CONVERSATIONS_DIR / f"conversation_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump({
                "conversation_id": conversation_id,
                "timestamp": timestamp,
                "messages": current_conversation
            }, f, indent=2)
        print(f"{Fore.GREEN}✅ Exported to {filename}{Style.RESET_ALL}")

    elif format == "csv":
        filename = CONVERSATIONS_DIR / f"conversation_{timestamp}.csv"
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "role", "model", "message", "response_time"])
            for msg in current_conversation:
                writer.writerow([
                    msg.get("timestamp", ""),
                    msg.get("role", ""),
                    msg.get("model", ""),
                    msg.get("message", ""),
                    msg.get("response_time", 0)
                ])
        print(f"{Fore.GREEN}✅ Exported to {filename}{Style.RESET_ALL}")

    elif format == "md":
        filename = CONVERSATIONS_DIR / f"conversation_{timestamp}.md"
        with open(filename, 'w') as f:
            f.write(f"# Conversation - {timestamp}\n\n")
            for msg in current_conversation:
                if msg["role"] == "user":
                    f.write(f"## 👤 User\n{msg['message']}\n\n")
                else:
                    f.write(f"### 🤖 {msg['model']}\n")
                    f.write(f"*Response time: {msg.get('response_time', 0):.1f}s*\n\n")
                    f.write(f"{msg['message']}\n\n")
        print(f"{Fore.GREEN}✅ Exported to {filename}{Style.RESET_ALL}")

def benchmark_models(test_prompts=None, timeout=120):
    """Run benchmarks on models with optional timeout"""
    if not test_prompts:
        test_prompts = [
            "What is 2+2?",
            "Explain Python in one sentence.",
            "What is the capital of France?",
            "Write a haiku about programming.",
            "What is machine learning?"
        ]

    available_models = get_available_models()
    if not available_models:
        print(f"{Fore.RED}No models available{Style.RESET_ALL}")
        return

    # Use first 10 models max for benchmarking
    models_to_test = available_models[:10]

    print(f"\n{Fore.CYAN}📊 Benchmarking {len(models_to_test)} models...{Style.RESET_ALL}")
    print(f"Testing with {len(test_prompts)} prompts")
    print(f"Timeout per request: {timeout if timeout else 'None'}s\n")

    results = {}

    for model in models_to_test:
        print(f"{Fore.YELLOW}Testing {model}...{Style.RESET_ALL}")
        model_results = {
            "response_times": [],
            "response_lengths": [],
            "success_count": 0,
            "fail_count": 0,
            "timeouts": 0
        }

        for prompt in test_prompts:
            try:
                _, response, error, elapsed = query_model(model, prompt, timeout=timeout)

                if not error:
                    model_results["response_times"].append(elapsed)
                    model_results["response_lengths"].append(len(response.split()))
                    model_results["success_count"] += 1
                elif "Timeout" in str(error):
                    model_results["timeouts"] += 1
                    model_results["fail_count"] += 1
                else:
                    model_results["fail_count"] += 1
            except:
                model_results["fail_count"] += 1

        # Calculate statistics
        if model_results["response_times"]:
            model_results["avg_response_time"] = sum(model_results["response_times"]) / len(model_results["response_times"])
            model_results["min_response_time"] = min(model_results["response_times"])
            model_results["max_response_time"] = max(model_results["response_times"])
            model_results["avg_response_length"] = sum(model_results["response_lengths"]) / len(model_results["response_lengths"])
        else:
            model_results["avg_response_time"] = 0
            model_results["avg_response_length"] = 0

        model_results["success_rate"] = (model_results["success_count"] / len(test_prompts)) * 100
        results[model] = model_results

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = BENCHMARKS_DIR / f"benchmark_{timestamp}.json"

    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "test_prompts": test_prompts,
            "timeout": timeout,
            "results": results
        }, f, indent=2)

    # Display results
    print(f"\n{Fore.CYAN}📊 BENCHMARK RESULTS{Style.RESET_ALL}")
    print("=" * 80)

    for model, model_results in results.items():
        color = MODEL_COLORS.get(model, Fore.WHITE)
        print(f"\n{color}{model}:{Style.RESET_ALL}")
        print(f"  ✅ Success rate: {model_results['success_rate']:.1f}%")
        print(f"  ⚡ Avg time: {model_results['avg_response_time']:.2f}s")
        print(f"  📏 Avg length: {model_results['avg_response_length']:.0f} words")
        if model_results.get('timeouts', 0) > 0:
            print(f"  ⏰ Timeouts: {model_results['timeouts']}")

    print(f"\n{Fore.GREEN}✅ Benchmark saved to {filename}{Style.RESET_ALL}")
    return results

def compare_models(prompt, timeout=None):
    """Compare responses from multiple models"""
    available_models = get_available_models()
    if len(available_models) < 2:
        print(f"{Fore.YELLOW}Need at least 2 models{Style.RESET_ALL}")
        return

    # Use first 5 models
    models_to_compare = available_models[:5]

    print(f"\n{Fore.CYAN}🔍 Comparing {len(models_to_compare)} models for: '{prompt}'{Style.RESET_ALL}")
    timeout_msg = f" (timeout: {timeout}s)" if timeout else " (no timeout)"
    print(f"{Fore.YELLOW}This may take a while{timeout_msg}{Style.RESET_ALL}")

    responses = {}
    for model in models_to_compare:
        print(f"{Fore.YELLOW}Getting response from {model}...{Style.RESET_ALL}")
        _, response, error, elapsed = query_model(model, prompt, timeout=timeout)

        if not error:
            responses[model] = {
                "text": response,
                "time": elapsed,
                "length": len(response.split())
            }
        else:
            print(f"{Fore.RED}  Error: {error}{Style.RESET_ALL}")

    # Save comparison
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = EXPORTS_DIR / f"comparison_{timestamp}.md"

    with open(filename, 'w') as f:
        f.write(f"# Model Comparison\n\n**Prompt:** {prompt}\n\n")
        for model, data in responses.items():
            f.write(f"## {model}\n")
            f.write(f"- Time: {data['time']:.2f}s\n")
            f.write(f"- Length: {data['length']} words\n\n")
            f.write(f"{data['text']}\n\n---\n\n")

    print(f"\n{Fore.GREEN}✅ Comparison saved to {filename}{Style.RESET_ALL}")

    # Display
    for model, data in responses.items():
        color = MODEL_COLORS.get(model, Fore.WHITE)
        print(f"\n{color}📌 {model} ({data['time']:.1f}s):{Style.RESET_ALL}")
        print("-" * 40)
        print(data['text'][:200] + "..." if len(data['text']) > 200 else data['text'])

def set_system_prompt(model_name, system_prompt):
    """Set system prompt for a model"""
    config_file = CONFIGS_DIR / f"{model_name.replace(':', '_').replace('/', '_')}.json"

    config = {}
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)

    config["system_prompt"] = system_prompt

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"{Fore.GREEN}✅ System prompt saved for {model_name}{Style.RESET_ALL}")

def batch_process(file_path, output_format="json", timeout=None):
    """Process multiple prompts from a file"""
    if not os.path.exists(file_path):
        print(f"{Fore.RED}File not found: {file_path}{Style.RESET_ALL}")
        return

    with open(file_path, 'r') as f:
        prompts = [line.strip() for line in f if line.strip()]

    available_models = get_available_models()
    if not available_models:
        print(f"{Fore.RED}No models available{Style.RESET_ALL}")
        return

    # Use first 3 models for batch processing
    models_to_use = available_models[:3]

    print(f"{Fore.CYAN}📦 Batch processing {len(prompts)} prompts with {len(models_to_use)} models...{Style.RESET_ALL}")
    timeout_msg = f" (timeout: {timeout}s per request)" if timeout else " (no timeout)"
    print(f"{Fore.YELLOW}{timeout_msg}{Style.RESET_ALL}")

    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"\n{Fore.YELLOW}Prompt {i}/{len(prompts)}: {prompt[:50]}...{Style.RESET_ALL}")

        prompt_results = {"prompt": prompt, "responses": {}}

        for model in models_to_use:
            _, response, error, elapsed = query_model(model, prompt, timeout=timeout)

            if not error:
                prompt_results["responses"][model] = {
                    "response": response,
                    "time": elapsed,
                    "length": len(response.split())
                }
            else:
                prompt_results["responses"][model] = {
                    "error": error,
                    "time": elapsed
                }

        results.append(prompt_results)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = EXPORTS_DIR / f"batch_{timestamp}.{output_format}"

    if output_format == "json":
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
    elif output_format == "csv":
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["prompt", "model", "response", "time", "words", "error"])
            for result in results:
                for model, data in result["responses"].items():
                    writer.writerow([
                        result["prompt"],
                        model,
                        data.get("response", "ERROR"),
                        data.get("time", 0),
                        data.get("length", 0),
                        data.get("error", "")
                    ])

    print(f"\n{Fore.GREEN}✅ Batch complete! Results saved to {filename}{Style.RESET_ALL}")

def get_small_models():
    """Return list of smallest models"""
    return SMALL_MODELS

def show_help():
    """Show help"""
    help_text = f"""
{Fore.CYAN}📚 COMMANDS:{Style.RESET_ALL}

{Fore.GREEN}CHAT:{Style.RESET_ALL}
  /list              - Show available models
  /select m1,m2      - Select specific models
  /select-small      - Select the 6 smallest models
  /parallel N        - Set parallel workers (default: 3)
  /timeout [N]       - Set timeout in seconds (no arg = no timeout)

{Fore.GREEN}EXPORT:{Style.RESET_ALL}
  /export [json|csv|md] - Export conversation
  /save              - Save conversation (JSON)

{Fore.GREEN}BENCHMARK:{Style.RESET_ALL}
  /benchmark [timeout] - Run benchmarks (optional timeout)
  /compare <prompt>  - Compare models
  /stats             - Show performance stats

{Fore.GREEN}BATCH:{Style.RESET_ALL}
  /batch <file> [json|csv] [timeout] - Process prompts file

{Fore.GREEN}SYSTEM:{Style.RESET_ALL}
  /system <model> <prompt> - Set system prompt
  /clear             - Clear screen
  /quit              - Exit

{Fore.YELLOW}EXAMPLES:{Style.RESET_ALL}
  /select-small                    # Use 6 smallest models
  /timeout 30                      # Set 30s timeout
  /timeout                         # Disable timeout
  /compare "What is Python?"       # Compare with no timeout
  /compare "Hello" 60              # Compare with 60s timeout
  /batch prompts.txt csv 120       # Batch with 120s timeout
"""
    print(help_text)

def show_models_by_type():
    """Show models grouped by type"""
    print(f"\n{Fore.CYAN}📋 Models by type:{Style.RESET_ALL}")
    for model_type, models in MODELS_BY_TYPE.items():
        print(f"\n{Fore.GREEN}{model_type.upper()}:{Style.RESET_ALL}")
        for model in models[:5]:  # Show first 5 of each type
            print(f"  • {model['name']} ({model['size']})")

def main():
    """Main loop"""
    global default_timeout
    print_banner()

    # Check if Ollama is running
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        print(f"{Fore.GREEN}✅ Connected to Ollama{Style.RESET_ALL}")
    except:
        print(f"{Fore.RED}❌ Cannot connect to Ollama. Is it running?{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Start it with: ollama serve{Style.RESET_ALL}")
        sys.exit(1)

    available = get_available_models()
    print(f"{Fore.GREEN}✅ {len(available)} models available{Style.RESET_ALL}")
    print(f"{Fore.CYAN}ℹ️  No timeout by default. Use /timeout N to set timeout{Style.RESET_ALL}")

    selected_models = None
    max_workers = 3
    timeout = None  # No timeout by default

    show_help()

    while True:
        try:
            user_input = input(f"{Fore.YELLOW}You{Style.RESET_ALL} > ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input == "/quit":
                break
            elif user_input == "/clear":
                print("\033[2J\033[H", end="")
                print_banner()
                continue
            elif user_input == "/help":
                show_help()
                continue
            elif user_input == "/list":
                available = get_available_models()
                print(f"\n{Fore.WHITE}Available models:{Style.RESET_ALL}")
                for i, model in enumerate(available, 1):
                    color = MODEL_COLORS.get(model, Fore.WHITE)
                    print(f"  {color}{i}. {model}{Style.RESET_ALL}")
                print()
                continue
            elif user_input == "/types":
                show_models_by_type()
                continue
            elif user_input == "/select-small":
                selected_models = get_small_models()
                print(f"{Fore.GREEN}✓ Selected {len(selected_models)} small models:{Style.RESET_ALL}")
                for model in selected_models:
                    print(f"  • {model}")
                continue
            elif user_input.startswith("/select"):
                parts = user_input.split()
                if len(parts) > 1:
                    model_names = parts[1].split(',')
                    available = get_available_models()
                    selected_models = []
                    for name in model_names:
                        matches = [m for m in available if name.strip().lower() in m.lower()]
                        selected_models.extend(matches)
                    if selected_models:
                        print(f"{Fore.GREEN}✓ Selected: {', '.join(selected_models)}{Style.RESET_ALL}")
                continue
            elif user_input.startswith("/parallel"):
                try:
                    max_workers = int(user_input.split()[1])
                    print(f"{Fore.GREEN}✓ Parallel workers: {max_workers}{Style.RESET_ALL}")
                except:
                    print(f"{Fore.RED}Usage: /parallel N{Style.RESET_ALL}")
                continue
            elif user_input.startswith("/timeout"):
                parts = user_input.split()
                if len(parts) > 1:
                    try:
                        timeout = int(parts[1])
                        print(f"{Fore.GREEN}✓ Timeout set to: {timeout}s{Style.RESET_ALL}")
                    except:
                        print(f"{Fore.RED}Usage: /timeout N (seconds){Style.RESET_ALL}")
                else:
                    timeout = None
                    print(f"{Fore.GREEN}✓ Timeout disabled (no timeout){Style.RESET_ALL}")
                continue
            elif user_input.startswith("/benchmark"):
                parts = user_input.split()
                bench_timeout = None
                if len(parts) > 1:
                    try:
                        bench_timeout = int(parts[1])
                    except:
                        pass
                benchmark_models(timeout=bench_timeout)
                continue
            elif user_input.startswith("/compare"):
                # Parse: /compare <prompt> [timeout]
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 2:
                    prompt = parts[1]
                    compare_timeout = None
                    if len(parts) == 3:
                        try:
                            compare_timeout = int(parts[2])
                        except:
                            pass
                    compare_models(prompt, timeout=compare_timeout)
                else:
                    print(f"{Fore.RED}Usage: /compare <prompt> [timeout]{Style.RESET_ALL}")
                continue
            elif user_input.startswith("/system"):
                parts = user_input.split(maxsplit=2)
                if len(parts) == 3:
                    set_system_prompt(parts[1], parts[2])
                else:
                    print(f"{Fore.RED}Usage: /system <model> <prompt>{Style.RESET_ALL}")
                continue
            elif user_input.startswith("/batch"):
                # Parse: /batch <file> [format] [timeout]
                parts = user_input.split()
                if len(parts) >= 2:
                    file_path = parts[1]
                    format = "json"
                    batch_timeout = timeout  # Use current timeout as default

                    if len(parts) >= 3:
                        if parts[2] in ["json", "csv"]:
                            format = parts[2]
                            if len(parts) >= 4:
                                try:
                                    batch_timeout = int(parts[3])
                                except:
                                    pass
                        else:
                            try:
                                batch_timeout = int(parts[2])
                            except:
                                pass

                    batch_process(file_path, format, batch_timeout)
                else:
                    print(f"{Fore.RED}Usage: /batch <file> [json|csv] [timeout]{Style.RESET_ALL}")
                continue
            elif user_input.startswith("/export"):
                format = user_input.split()[1] if len(user_input.split()) > 1 else "json"
                if format in ["json", "csv", "md"]:
                    export_conversation(format)
                else:
                    print(f"{Fore.RED}Usage: /export [json|csv|md]{Style.RESET_ALL}")
                continue
            elif user_input == "/save":
                export_conversation("json")
                continue
            elif user_input == "/stats":
                if response_times:
                    print(f"\n{Fore.CYAN}📊 STATISTICS{Style.RESET_ALL}")
                    for model, times in response_times.items():
                        if times:
                            avg = sum(times) / len(times)
                            color = MODEL_COLORS.get(model, Fore.WHITE)
                            print(f"{color}{model}:{Style.RESET_ALL}")
                            print(f"  Avg: {avg:.2f}s | Count: {len(times)}")
                else:
                    print(f"{Fore.YELLOW}No stats yet{Style.RESET_ALL}")
                continue

            # Regular chat - use current timeout setting
            chat_with_swarm(user_input, selected_models, max_workers, timeout)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Use /quit to exit{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
