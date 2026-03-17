#!/usr/bin/env python3
"""
Tiny Model Swarm - Direct Mode with Collaboration
Works with your existing Ollama installation
All features: benchmarking, exports, comparisons, batch processing, and model collaboration
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
import shutil  # Added for terminal size detection

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

# Get terminal size for dynamic formatting
def get_terminal_width():
    """Get terminal width, default to 80 if can't detect"""
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80

TERM_WIDTH = get_terminal_width()

# Data directories
DATA_DIR = Path.home() / ".tiny-swarm-data"
EXPORTS_DIR = DATA_DIR / "exports"
BENCHMARKS_DIR = DATA_DIR / "benchmarks"
CONVERSATIONS_DIR = DATA_DIR / "conversations"
CONFIGS_DIR = DATA_DIR / "configs"
COLLAB_DIR = DATA_DIR / "collaborations"

# Create directories
for dir_path in [DATA_DIR, EXPORTS_DIR, BENCHMARKS_DIR, CONVERSATIONS_DIR, CONFIGS_DIR, COLLAB_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
    dir_path.chmod(0o700)

# Cache for model details
model_cache = {
    "timestamp": None,
    "models": [],
    "by_type": {},
    "small_models": [],
    "capabilities": {}  # Track model capabilities
}

# Cache timeout (5 minutes)
CACHE_TIMEOUT = 300

def get_ollama_models(force_refresh=False):
    """Get models from Ollama with caching"""
    global model_cache
    
    # Check if cache is valid
    if not force_refresh and model_cache["timestamp"]:
        cache_age = time.time() - model_cache["timestamp"]
        if cache_age < CACHE_TIMEOUT and model_cache["models"]:
            return model_cache["models"]
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            
            # Transform to our format
            models = []
            for m in models_data:
                name = m["name"]
                # Parse size
                size_bytes = m.get("size", 0)
                if size_bytes > 0:
                    if size_bytes > 1e9:
                        size = f"{size_bytes/1e9:.1f} GB"
                    elif size_bytes > 1e6:
                        size = f"{size_bytes/1e6:.1f} MB"
                    else:
                        size = f"{size_bytes/1e3:.1f} KB"
                else:
                    size = "-"
                
                # Determine model type and capabilities from name
                name_lower = name.lower()
                capabilities = []
                
                if "nemotron" in name_lower:
                    model_type = "nemotron"
                    capabilities = ["general", "reasoning"]
                elif "qwen" in name_lower:
                    model_type = "qwen"
                    capabilities = ["general", "multilingual"]
                elif "deepseek" in name_lower:
                    model_type = "deepseek"
                    capabilities = ["coding", "reasoning"]
                elif "llama" in name_lower or "tinyllama" in name_lower:
                    model_type = "llama"
                    capabilities = ["general"]
                elif "mistral" in name_lower:
                    model_type = "mistral"
                    capabilities = ["general", "instruct"]
                elif "gemma" in name_lower:
                    model_type = "gemma"
                    capabilities = ["general", "efficient"]
                elif "phi" in name_lower:
                    model_type = "phi"
                    capabilities = ["reasoning", "coding"]
                elif "codellama" in name_lower:
                    model_type = "code"
                    capabilities = ["coding", "specialist"]
                elif "dolphin" in name_lower:
                    model_type = "dolphin"
                    capabilities = ["general", "creative"]
                elif "neural" in name_lower:
                    capabilities.append("chat")
                elif "instruct" in name_lower:
                    capabilities.append("instruction")
                else:
                    model_type = "other"
                    capabilities = ["general"]
                
                # Add based on size
                if "GB" in size:
                    try:
                        gb_value = float(size.replace(" GB", ""))
                        if gb_value < 3:
                            capabilities.append("fast")
                        if gb_value > 7:
                            capabilities.append("powerful")
                    except:
                        pass
                
                models.append({
                    "name": name,
                    "size": size,
                    "type": model_type,
                    "capabilities": capabilities,
                    "description": name.split(':')[0].capitalize()
                })
            
            # Group models by type
            by_type = {}
            capabilities_map = {}
            
            for model in models:
                model_type = model["type"]
                if model_type not in by_type:
                    by_type[model_type] = []
                by_type[model_type].append(model)
                
                # Track capabilities
                for cap in model["capabilities"]:
                    if cap not in capabilities_map:
                        capabilities_map[cap] = []
                    capabilities_map[cap].append(model["name"])
            
            # Identify small models (under 2GB)
            small_models = []
            for model in models:
                size_str = model["size"]
                if "GB" in size_str:
                    try:
                        gb_value = float(size_str.replace(" GB", ""))
                        if gb_value < 2.0:
                            small_models.append(model["name"])
                    except:
                        pass
                elif "MB" in size_str:
                    small_models.append(model["name"])
            
            # Update cache
            model_cache = {
                "timestamp": time.time(),
                "models": models,
                "by_type": by_type,
                "small_models": small_models,
                "capabilities": capabilities_map
            }
            
            return models
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not fetch models from Ollama: {e}{Style.RESET_ALL}")
    
    return []

def get_available_models():
    """Get list of available model names from Ollama"""
    models = get_ollama_models()
    return [model["name"] for model in models]

def get_models_by_capability(capability):
    """Get models with specific capability"""
    models = get_ollama_models()
    return [m["name"] for m in models if capability in m.get("capabilities", [])]

def get_small_models():
    """Get list of small models (under 2GB)"""
    models = get_ollama_models()
    small_models = []
    for model in models:
        size_str = model["size"]
        if "GB" in size_str:
            try:
                gb_value = float(size_str.replace(" GB", ""))
                if gb_value < 2.0:
                    small_models.append(model["name"])
            except:
                pass
        elif "MB" in size_str:
            small_models.append(model["name"])
    return small_models[:10]  # Return up to 10 smallest

def generate_model_colors(models):
    """Generate colors for models"""
    colors = [Fore.CYAN, Fore.GREEN, Fore.YELLOW, Fore.MAGENTA, Fore.RED, Fore.BLUE, Fore.WHITE]
    model_colors = {}
    for i, model in enumerate(models):
        model_colors[model["name"]] = colors[i % len(colors)]
    return model_colors

# Initialize model colors
initial_models = get_ollama_models()
MODEL_COLORS = generate_model_colors(initial_models)

# Track response times and metrics
response_times = {}
response_quality = {}
benchmark_results = {}
current_conversation = []
conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
collaboration_history = []
# Default timeout (None = no timeout)
default_timeout = None

def print_banner():
    """Print banner with dynamic width"""
    models = get_ollama_models()
    
    # Adjust banner width based on terminal
    width = min(TERM_WIDTH, 100)  # Cap at 100 to prevent excessive width
    line = "═" * (width - 4)
    
    banner = f"""
{Fore.RED}╔{line}╗
{Fore.RED}║  🚀 TINY MODEL SWARM - COLLABORATION MODE{' ' * (width - 44)}║
{Fore.RED}╠{line}╣
{Fore.YELLOW}║  📊 Models:       {len(models)} installed locally{' ' * (width - 38 - len(str(len(models))))}║
{Fore.YELLOW}║  💾 Exports:      {str(EXPORTS_DIR)[:width-30]}{' ' * (width - 30 - len(str(EXPORTS_DIR)[:width-30]))}║
{Fore.YELLOW}║  📈 Benchmarks:   {str(BENCHMARKS_DIR)[:width-30]}{' ' * (width - 30 - len(str(BENCHMARKS_DIR)[:width-30]))}║
{Fore.YELLOW}║  💬 Conversations:{str(CONVERSATIONS_DIR)[:width-30]}{' ' * (width - 30 - len(str(CONVERSATIONS_DIR)[:width-30]))}║
{Fore.YELLOW}║  🤝 Collaborations:{str(COLLAB_DIR)[:width-30]}{' ' * (width - 30 - len(str(COLLAB_DIR)[:width-30]))}║
{Fore.RED}╠{line}╣
{Fore.GREEN}║  ✨ FEATURES:{' ' * (width - 16)}║
{Fore.GREEN}║  • 🤝 Model collaboration (chain, debate, ensemble){' ' * (width - 52)}║
{Fore.GREEN}║  • Chat with multiple models simultaneously{' ' * (width - 43)}║
{Fore.GREEN}║  • No timeout by default (set with /timeout N){' ' * (width - 47)}║
{Fore.GREEN}║  • Benchmark models side-by-side{' ' * (width - 37)}║
{Fore.GREEN}║  • Compare responses quality{' ' * (width - 33)}║
{Fore.GREEN}║  • Export to JSON/CSV/Markdown{' ' * (width - 35)}║
{Fore.GREEN}║  • Batch processing mode{' ' * (width - 28)}║
{Fore.GREEN}║  • Custom system prompts{' ' * (width - 28)}║
{Fore.GREEN}║  • Performance statistics{' ' * (width - 29)}║
{Fore.RED}╚{line}╝{Style.RESET_ALL}
"""
    print(banner)

def refresh_model_list():
    """Force refresh the model list from Ollama"""
    global MODEL_COLORS
    models = get_ollama_models(force_refresh=True)
    MODEL_COLORS = generate_model_colors(models)
    print(f"{Fore.GREEN}✅ Model list refreshed: {len(models)} models found{Style.RESET_ALL}")
    
    # Show capabilities
    caps = model_cache.get("capabilities", {})
    print(f"{Fore.CYAN}📊 Available capabilities:{Style.RESET_ALL}")
    for cap, models_list in list(caps.items())[:5]:
        print(f"  • {cap}: {len(models_list)} models")
    
    return models

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
    print(f"{Fore.WHITE}{'─' * min(TERM_WIDTH, 80)}")
    
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
                
                # Pretty print response with dynamic wrapping
                words = response.split()
                line = "  "
                for word in words:
                    if len(line) + len(word) + 1 > min(TERM_WIDTH - 4, 78):
                        print(line)
                        line = "  " + word + " "
                    else:
                        line += word + " "
                if line:
                    print(line)
                print()
            
            print(f"{Fore.WHITE}{'─' * min(TERM_WIDTH, 80)}")
    
    print(f"{Fore.GREEN}✨ All {completed} models have responded!{Style.RESET_ALL}")
    
    # Show stats
    if times:
        fastest = min(times.items(), key=lambda x: x[1])
        slowest = max(times.items(), key=lambda x: x[1])
        print(f"{Fore.CYAN}⚡ Fastest: {fastest[0]} ({fastest[1]:.1f}s){Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}🐢 Slowest: {slowest[0]} ({slowest[1]:.1f}s){Style.RESET_ALL}")
    print()

# ==================== COLLABORATION FEATURES ====================

def collaborate_chain(prompt, model_chain, timeout=None):
    """Chain models where each model builds on previous output"""
    print(f"\n{Fore.CYAN}🤝 CHAIN COLLABORATION{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Using model chain: {' → '.join(model_chain)}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{'─' * min(TERM_WIDTH, 60)}")
    
    current_prompt = prompt
    chain_results = []
    
    for i, model in enumerate(model_chain):
        print(f"{Fore.YELLOW}Step {i+1}: {model} processing...{Style.RESET_ALL}")
        
        # Add context from previous steps
        if i > 0:
            context = f"Previous output: {chain_results[-1]['response']}\n\nBased on this, {current_prompt}"
        else:
            context = current_prompt
        
        _, response, error, elapsed = query_model(model, context, timeout=timeout)
        
        step_result = {
            "step": i+1,
            "model": model,
            "prompt": context,
            "response": response if not error else f"ERROR: {error}",
            "time": elapsed,
            "error": error
        }
        chain_results.append(step_result)
        
        color = MODEL_COLORS.get(model, Fore.WHITE)
        print(f"{color}📌 {model} responded in {elapsed:.1f}s:{Style.RESET_ALL}")
        
        if error:
            print(f"  {Fore.RED}⚠️ Error: {error}{Style.RESET_ALL}")
        else:
            # Show preview with dynamic width
            preview = response[:min(150, TERM_WIDTH-20)] + "..." if len(response) > min(150, TERM_WIDTH-20) else response
            print(f"  {preview}")
        print()
    
    # Save collaboration
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = COLLAB_DIR / f"chain_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "type": "chain",
            "prompt": prompt,
            "model_chain": model_chain,
            "results": chain_results,
            "timestamp": timestamp
        }, f, indent=2)
    
    print(f"{Fore.GREEN}✅ Chain collaboration saved to {filename}{Style.RESET_ALL}")
    
    # Return final output
    if chain_results and not chain_results[-1].get("error"):
        return chain_results[-1]["response"]
    return None

def collaborate_debate(topic, models, rounds=2, timeout=None):
    """Models debate a topic, responding to each other"""
    print(f"\n{Fore.CYAN}🎭 DEBATE COLLABORATION{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Topic: {topic}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Models: {', '.join(models)}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Rounds: {rounds}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{'─' * min(TERM_WIDTH, 60)}")
    
    debate_history = []
    current_context = f"Topic for debate: {topic}\n\n"
    
    for round_num in range(1, rounds + 1):
        print(f"\n{Fore.CYAN}Round {round_num}:{Style.RESET_ALL}")
        
        round_responses = {}
        
        for model in models:
            # Build context with previous arguments
            context = current_context
            if debate_history:
                context += "Previous arguments:\n"
                for entry in debate_history[-len(models):]:  # Last round only
                    context += f"- {entry['model']}: {entry['response'][:100]}...\n"
            
            context += f"\n{model}, present your argument for round {round_num}:"
            
            print(f"{Fore.YELLOW}  {model} thinking...{Style.RESET_ALL}")
            _, response, error, elapsed = query_model(model, context, timeout=timeout)
            
            color = MODEL_COLORS.get(model, Fore.WHITE)
            if error:
                print(f"  {color}⚠️ Error: {error}{Style.RESET_ALL}")
                round_responses[model] = f"[ERROR: {error}]"
            else:
                print(f"  {color}✓ Responded in {elapsed:.1f}s{Style.RESET_ALL}")
                # Show brief preview
                preview = response[:min(100, TERM_WIDTH-30)] + "..." if len(response) > min(100, TERM_WIDTH-30) else response
                print(f"    {preview}")
                round_responses[model] = response
                
                # Add to history
                debate_history.append({
                    "round": round_num,
                    "model": model,
                    "response": response,
                    "time": elapsed
                })
        
        # Update context for next round
        current_context += f"\nRound {round_num}:\n"
        for model, response in round_responses.items():
            current_context += f"{model}: {response}\n\n"
    
    # Save debate
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = COLLAB_DIR / f"debate_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "type": "debate",
            "topic": topic,
            "models": models,
            "rounds": rounds,
            "history": debate_history,
            "timestamp": timestamp
        }, f, indent=2)
    
    # Create readable transcript
    transcript_file = COLLAB_DIR / f"debate_{timestamp}.txt"
    with open(transcript_file, 'w') as f:
        f.write(f"DEBATE: {topic}\n")
        f.write("=" * 60 + "\n\n")
        for entry in debate_history:
            f.write(f"Round {entry['round']} - {entry['model']}:\n")
            f.write(f"{entry['response']}\n")
            f.write("-" * 40 + "\n\n")
    
    print(f"\n{Fore.GREEN}✅ Debate saved to {filename} and {transcript_file}{Style.RESET_ALL}")
    
    return debate_history

def collaborate_ensemble(prompt, models, consensus_method="majority", timeout=None):
    """Multiple models work on same task, then combine results"""
    print(f"\n{Fore.CYAN}👥 ENSEMBLE COLLABORATION{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Task: {prompt}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Models: {', '.join(models)}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Consensus method: {consensus_method}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{'─' * min(TERM_WIDTH, 60)}")
    
    # Get individual responses
    responses = {}
    with ThreadPoolExecutor(max_workers=len(models)) as executor:
        futures = {executor.submit(query_model, model, prompt, timeout): model 
                  for model in models}
        
        for future in as_completed(futures):
            model, response, error, elapsed = future.result()
            color = MODEL_COLORS.get(model, Fore.WHITE)
            
            if error:
                print(f"{color}⚠️ {model} error: {error}{Style.RESET_ALL}")
                responses[model] = {"error": error, "time": elapsed}
            else:
                print(f"{color}✓ {model} responded in {elapsed:.1f}s{Style.RESET_ALL}")
                responses[model] = {
                    "response": response,
                    "time": elapsed,
                    "length": len(response.split())
                }
    
    # Combine responses based on method
    valid_responses = {m: data for m, data in responses.items() if "response" in data}
    
    if not valid_responses:
        print(f"{Fore.RED}No valid responses received{Style.RESET_ALL}")
        return None
    
    if consensus_method == "majority":
        # Simple majority vote not really applicable for text, so we'll summarize
        consensus_prompt = f"Multiple models responded to: '{prompt}'\n\nTheir responses:\n"
        for model, data in valid_responses.items():
            consensus_prompt += f"\n{model}: {data['response']}\n"
        consensus_prompt += "\nSynthesize these responses into a single coherent answer:"
        
        # Use first model to synthesize
        synthesizer = list(valid_responses.keys())[0]
        print(f"{Fore.YELLOW}🤔 Synthesizing with {synthesizer}...{Style.RESET_ALL}")
        _, consensus, error, elapsed = query_model(synthesizer, consensus_prompt, timeout=timeout)
        
        if error:
            print(f"{Fore.RED}Synthesis error: {error}{Style.RESET_ALL}")
            consensus = "Could not synthesize"
        else:
            print(f"{Fore.GREEN}✓ Synthesized in {elapsed:.1f}s{Style.RESET_ALL}")
    
    elif consensus_method == "summary":
        # Just create a summary
        summary = f"ENSEMBLE RESULTS ({len(valid_responses)} models):\n\n"
        for model, data in valid_responses.items():
            summary += f"--- {model} ---\n{data['response']}\n\n"
        consensus = summary
    
    else:  # raw
        consensus = {model: data["response"] for model, data in valid_responses.items()}
    
    # Save ensemble results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = COLLAB_DIR / f"ensemble_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "type": "ensemble",
            "prompt": prompt,
            "models": models,
            "consensus_method": consensus_method,
            "responses": responses,
            "consensus": consensus,
            "timestamp": timestamp
        }, f, indent=2)
    
    print(f"\n{Fore.GREEN}✅ Ensemble results saved to {filename}{Style.RESET_ALL}")
    
    # Display consensus with dynamic width
    print(f"\n{Fore.CYAN}📊 CONSENSUS:{Style.RESET_ALL}")
    if isinstance(consensus, dict):
        for model, resp in consensus.items():
            preview = resp[:min(100, TERM_WIDTH-30)] + "..." if len(resp) > min(100, TERM_WIDTH-30) else resp
            print(f"{Fore.WHITE}{model}:{Style.RESET_ALL} {preview}")
    else:
        print(consensus[:min(500, TERM_WIDTH-10)] + "..." if len(consensus) > min(500, TERM_WIDTH-10) else consensus)
    
    return consensus

def collaborate_specialist(task, specialists=None, timeout=None):
    """Assign specialist roles to different models based on capabilities"""
    models = get_ollama_models()
    
    if not specialists:
        # Auto-assign based on capabilities
        specialists = {
            "coder": get_models_by_capability("coding")[:1],
            "reasoner": get_models_by_capability("reasoning")[:1],
            "general": get_models_by_capability("general")[:1]
        }
        # Flatten and remove duplicates
        specialist_models = []
        for role, model_list in specialists.items():
            if model_list:
                specialist_models.append(model_list[0])
        specialists = specialist_models[:3]  # Use up to 3
    
    print(f"\n{Fore.CYAN}🔧 SPECIALIST COLLABORATION{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Task: {task}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Specialists: {', '.join(specialists)}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{'─' * min(TERM_WIDTH, 60)}")
    
    # Break down task for specialists
    breakdown_prompt = f"Break down this task into subtasks: {task}"
    _, breakdown, error, _ = query_model(specialists[0], breakdown_prompt, timeout=timeout)
    
    if error:
        print(f"{Fore.RED}Could not break down task: {error}{Style.RESET_ALL}")
        subtasks = [task]  # Fallback to original task
    else:
        # Extract subtasks (simple heuristic - split by newlines or numbers)
        subtasks = [line for line in breakdown.split('\n') 
                   if line.strip() and (line[0].isdigit() or line.startswith('-'))]
        if not subtasks:
            subtasks = [task]
    
    print(f"{Fore.YELLOW}Identified {len(subtasks)} subtasks{Style.RESET_ALL}")
    
    # Assign subtasks to specialists
    results = {}
    with ThreadPoolExecutor(max_workers=len(specialists)) as executor:
        futures = {}
        for i, (specialist, subtask) in enumerate(zip(specialists * (len(subtasks) // len(specialists) + 1), subtasks)):
            if i < len(subtasks):
                futures[executor.submit(query_model, specialist, subtask, timeout)] = (specialist, subtask)
        
        for future in as_completed(futures):
            specialist, subtask = futures[future]
            model, response, error, elapsed = future.result()
            
            if error:
                preview = subtask[:min(30, TERM_WIDTH-40)]
                print(f"{Fore.RED}⚠️ {specialist} error on '{preview}...': {error}{Style.RESET_ALL}")
                results[specialist] = results.get(specialist, []) + [{"subtask": subtask, "error": error}]
            else:
                preview = subtask[:min(30, TERM_WIDTH-40)]
                print(f"{Fore.GREEN}✓ {specialist} completed '{preview}...' in {elapsed:.1f}s{Style.RESET_ALL}")
                results[specialist] = results.get(specialist, []) + [{
                    "subtask": subtask,
                    "response": response,
                    "time": elapsed
                }]
    
    # Synthesize results
    synthesis_prompt = f"Task: {task}\n\nSpecialist results:\n"
    for specialist, subtask_results in results.items():
        for result in subtask_results:
            if "response" in result:
                synthesis_prompt += f"\n{specialist} on '{result['subtask']}':\n{result['response']}\n"
    
    synthesis_prompt += "\nSynthesize these specialist contributions into a complete answer:"
    
    print(f"{Fore.YELLOW}🤔 Synthesizing results...{Style.RESET_ALL}")
    _, final_response, error, elapsed = query_model(specialists[0], synthesis_prompt, timeout=timeout)
    
    if error:
        print(f"{Fore.RED}Synthesis error: {error}{Style.RESET_ALL}")
        final_response = "Could not synthesize"
    
    # Save collaboration
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = COLLAB_DIR / f"specialist_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "type": "specialist",
            "task": task,
            "specialists": specialists,
            "subtasks": subtasks,
            "results": results,
            "final_response": final_response,
            "timestamp": timestamp
        }, f, indent=2)
    
    print(f"\n{Fore.GREEN}✅ Specialist collaboration saved to {filename}{Style.RESET_ALL}")
    
    # Display final response with dynamic width
    print(f"\n{Fore.CYAN}📊 FINAL RESULT:{Style.RESET_ALL}")
    print(final_response[:min(500, TERM_WIDTH-10)] + "..." if len(final_response) > min(500, TERM_WIDTH-10) else final_response)
    
    return final_response

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
    print("=" * min(TERM_WIDTH, 80))
    
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
    
    # Display with dynamic width
    for model, data in responses.items():
        color = MODEL_COLORS.get(model, Fore.WHITE)
        print(f"\n{color}📌 {model} ({data['time']:.1f}s):{Style.RESET_ALL}")
        print("-" * min(TERM_WIDTH, 40))
        preview = data['text'][:min(200, TERM_WIDTH-20)] + "..." if len(data['text']) > min(200, TERM_WIDTH-20) else data['text']
        print(preview)

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
        preview = prompt[:min(50, TERM_WIDTH-30)] + "..." if len(prompt) > min(50, TERM_WIDTH-30) else prompt
        print(f"\n{Fore.YELLOW}Prompt {i}/{len(prompts)}: {preview}{Style.RESET_ALL}")
        
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

def show_help():
    """Show help"""
    help_text = f"""
{Fore.CYAN}📚 COMMANDS:{Style.RESET_ALL}

{Fore.GREEN}CHAT:{Style.RESET_ALL}
  /list              - Show available models
  /refresh           - Refresh model list from Ollama
  /select m1,m2      - Select specific models
  /select-small      - Select small models (<2GB)
  /parallel N        - Set parallel workers (default: 3)
  /timeout [N]       - Set timeout in seconds (no arg = no timeout)

{Fore.GREEN}COLLABORATION:{Style.RESET_ALL}
  /chain <m1,m2,m3> <prompt>    - Chain collaboration
  /debate <topic> [models] [rounds] - Model debate
  /ensemble <prompt> [method]   - Ensemble (majority/summary/raw)
  /specialist <task>            - Specialist collaboration
  /collab-list                  - List saved collaborations

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
  /select-small                    # Use small models
  /timeout 30                      # Set 30s timeout
  /chain tinyllama,mistral "Write a story"  # Chain collaboration
  /debate "AI safety" 3            # 3-round debate
  /ensemble "Solve math problem" majority  # Ensemble
  /specialist "Build a web app"    # Specialist collaboration
  /compare "What is Python?"       # Compare with no timeout
"""
    print(help_text)

def list_collaborations():
    """List saved collaborations"""
    collab_files = list(COLLAB_DIR.glob("*.json"))
    if not collab_files:
        print(f"{Fore.YELLOW}No collaborations found{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}📋 Saved Collaborations:{Style.RESET_ALL}")
    for file in sorted(collab_files, key=os.path.getmtime, reverse=True)[:10]:
        mtime = datetime.fromtimestamp(os.path.getmtime(file)).strftime("%Y-%m-%d %H:%M")
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                collab_type = data.get("type", "unknown")
                print(f"  • {file.name} ({collab_type}) - {mtime}")
        except:
            print(f"  • {file.name} - {mtime}")
    print()

def show_models_by_type():
    """Show models grouped by type"""
    by_type = model_cache.get("by_type", {})
    print(f"\n{Fore.CYAN}📋 Models by type:{Style.RESET_ALL}")
    for model_type, models in by_type.items():
        print(f"\n{Fore.GREEN}{model_type.upper()}:{Style.RESET_ALL}")
        for model in models[:5]:  # Show first 5 of each type
            caps = ", ".join(model.get("capabilities", [])[:3])
            print(f"  • {model['name']} ({model['size']}) [{caps}]")

def main():
    """Main loop"""
    global default_timeout, MODEL_COLORS, TERM_WIDTH
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
    print(f"{Fore.CYAN}ℹ️  Use /refresh to update model list{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}🤝 New: Model collaboration features! Try /chain, /debate, /ensemble{Style.RESET_ALL}")
    
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
            elif user_input == "/refresh":
                models = refresh_model_list()
                # Update terminal width in case it changed
                TERM_WIDTH = get_terminal_width()
                print(f"{Fore.GREEN}✓ Found {len(models)} models:{Style.RESET_ALL}")
                for model in models[:10]:
                    caps = ", ".join(model.get("capabilities", [])[:3])
                    print(f"  • {model['name']} ({model['size']}) [{caps}]")
                if len(models) > 10:
                    print(f"  ... and {len(models)-10} more")
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
                
            # COLLABORATION COMMANDS
            elif user_input.startswith("/chain"):
                # Format: /chain model1,model2,model3 prompt
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 3:
                    model_chain = [m.strip() for m in parts[1].split(',')]
                    prompt = parts[2]
                    collaborate_chain(prompt, model_chain, timeout)
                else:
                    print(f"{Fore.RED}Usage: /chain model1,model2,model3 <prompt>{Style.RESET_ALL}")
                continue
                
            elif user_input.startswith("/debate"):
                # Format: /debate topic [models] [rounds]
                parts = user_input.split(maxsplit=3)
                if len(parts) >= 2:
                    topic = parts[1]
                    
                    # Default models
                    available = get_available_models()
                    debate_models = available[:3]  # First 3 models
                    rounds = 2
                    
                    if len(parts) >= 3:
                        # Try to parse as models or rounds
                        if parts[2].isdigit():
                            rounds = int(parts[2])
                        else:
                            debate_models = [m.strip() for m in parts[2].split(',')]
                    
                    if len(parts) >= 4:
                        if parts[3].isdigit():
                            rounds = int(parts[3])
                    
                    collaborate_debate(topic, debate_models, rounds, timeout)
                else:
                    print(f"{Fore.RED}Usage: /debate <topic> [models] [rounds]{Style.RESET_ALL}")
                continue
                
            elif user_input.startswith("/ensemble"):
                # Format: /ensemble prompt [method]
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 2:
                    prompt = parts[1]
                    method = "majority"
                    
                    if len(parts) >= 3:
                        method = parts[2]
                    
                    available = get_available_models()
                    ensemble_models = available[:3]  # First 3 models
                    collaborate_ensemble(prompt, ensemble_models, method, timeout)
                else:
                    print(f"{Fore.RED}Usage: /ensemble <prompt> [majority|summary|raw]{Style.RESET_ALL}")
                continue
                
            elif user_input.startswith("/specialist"):
                # Format: /specialist task
                parts = user_input.split(maxsplit=1)
                if len(parts) >= 2:
                    task = parts[1]
                    collaborate_specialist(task, timeout=timeout)
                else:
                    print(f"{Fore.RED}Usage: /specialist <task>{Style.RESET_ALL}")
                continue
                
            elif user_input == "/collab-list":
                list_collaborations()
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
