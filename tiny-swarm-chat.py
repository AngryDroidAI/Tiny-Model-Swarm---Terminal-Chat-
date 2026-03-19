#!/usr/bin/env python3
"""
Tiny Model Swarm - Enhanced Edition with System Control
All features: file management, app control, development, GPU utilization, and remote operation
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
import shutil
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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

try:
    import psutil
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "psutil"])
    import psutil

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "watchdog"])
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

try:
    import paramiko
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "paramiko"])
    import paramiko

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "email"])
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders

try:
    from flask import Flask, request, jsonify
    import threading
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "flask"])
    from flask import Flask, request, jsonify
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
FILES_DIR = DATA_DIR / "managed_files"
APPS_DIR = DATA_DIR / "apps"
REMOTE_DIR = DATA_DIR / "remote"

# Create directories
for dir_path in [DATA_DIR, EXPORTS_DIR, BENCHMARKS_DIR, CONVERSATIONS_DIR,
                 CONFIGS_DIR, COLLAB_DIR, FILES_DIR, APPS_DIR, REMOTE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
    dir_path.chmod(0o700)

# Cache for model details
model_cache = {
    "timestamp": None,
    "models": [],
    "by_type": {},
    "small_models": [],
    "capabilities": {}
}

# Cache timeout (5 minutes)
CACHE_TIMEOUT = 300

# ==================== FILE MANAGEMENT ====================

class FileOrganizer:
    """Organize files into categorized folders"""

    FILE_CATEGORIES = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.tiff'],
        'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
        'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
        'archives': ['.zip', '.tar', '.gz', '.rar', '.7z', '.bz2'],
        'code': ['.py', '.js', '.html', '.css', '.cpp', '.c', '.java', '.php', '.rb', '.go'],
        'config': ['.json', '.xml', '.yaml', '.yml', '.ini', '.cfg', '.conf'],
        'executables': ['.exe', '.msi', '.app', '.deb', '.rpm', '.sh', '.bat']
    }

    @staticmethod
    def get_category(filename):
        """Get category for a file based on extension"""
        ext = os.path.splitext(filename)[1].lower()
        for category, extensions in FileOrganizer.FILE_CATEGORIES.items():
            if ext in extensions:
                return category
        return 'other'

    @staticmethod
    def organize_folder(folder_path, dry_run=False):
        """Organize files in a folder by category"""
        folder = Path(folder_path).expanduser().resolve()
        if not folder.exists():
            return f"❌ Folder not found: {folder}"

        print(f"{Fore.CYAN}📁 Organizing: {folder}{Style.RESET_ALL}")

        organized = 0
        skipped = 0
        results = []

        for item in folder.iterdir():
            if item.is_file():
                category = FileOrganizer.get_category(item.name)
                category_folder = folder / category

                if not dry_run:
                    category_folder.mkdir(exist_ok=True)

                dest = category_folder / item.name

                # Handle duplicates
                if dest.exists():
                    base = dest.stem
                    ext = dest.suffix
                    counter = 1
                    while dest.exists():
                        new_name = f"{base}_{counter}{ext}"
                        dest = category_folder / new_name
                        counter += 1

                if dry_run:
                    results.append(f"  Would move: {item.name} → {category}/")
                    organized += 1
                else:
                    try:
                        shutil.move(str(item), str(dest))
                        results.append(f"  ✅ Moved: {item.name} → {category}/")
                        organized += 1
                    except Exception as e:
                        results.append(f"  ❌ Failed: {item.name} - {e}")
                        skipped += 1

        # Summary
        summary = f"\n{Fore.GREEN}📊 Organization complete:{Style.RESET_ALL}"
        summary += f"\n  • Organized: {organized} files"
        if skipped > 0:
            summary += f"\n  • Skipped: {skipped} files"

        return "\n".join(results + [summary])

    @staticmethod
    def sort_by_date(folder_path, date_format="%Y-%m"):
        """Sort files into folders by date (year-month)"""
        folder = Path(folder_path).expanduser().resolve()
        if not folder.exists():
            return f"❌ Folder not found: {folder}"

        print(f"{Fore.CYAN}📅 Sorting by date: {folder}{Style.RESET_ALL}")

        organized = 0
        results = []

        for item in folder.iterdir():
            if item.is_file():
                # Get modification time
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                date_folder = mtime.strftime(date_format)
                dest_folder = folder / date_folder
                dest_folder.mkdir(exist_ok=True)

                dest = dest_folder / item.name

                # Handle duplicates
                if dest.exists():
                    base = dest.stem
                    ext = dest.suffix
                    counter = 1
                    while dest.exists():
                        new_name = f"{base}_{counter}{ext}"
                        dest = dest_folder / new_name
                        counter += 1

                try:
                    shutil.move(str(item), str(dest))
                    results.append(f"  ✅ Moved: {item.name} → {date_folder}/")
                    organized += 1
                except Exception as e:
                    results.append(f"  ❌ Failed: {item.name} - {e}")

        return "\n".join(results + [f"\n{Fore.GREEN}✅ Sorted {organized} files by date{Style.RESET_ALL}"])

    @staticmethod
    def find_duplicates(folder_path):
        """Find duplicate files in a folder"""
        folder = Path(folder_path).expanduser().resolve()
        if not folder.exists():
            return f"❌ Folder not found: {folder}"

        print(f"{Fore.CYAN}🔍 Finding duplicates in: {folder}{Style.RESET_ALL}")

        hash_map = {}
        duplicates = []

        for item in folder.rglob('*'):
            if item.is_file():
                try:
                    # Calculate file hash
                    with open(item, 'rb') as f:
                        file_hash = hashlib.md5(f.read(1024*1024)).hexdigest()  # Read first 1MB

                    if file_hash in hash_map:
                        duplicates.append((item, hash_map[file_hash]))
                    else:
                        hash_map[file_hash] = item
                except Exception as e:
                    print(f"  ⚠️ Error reading {item}: {e}")

        if duplicates:
            result = f"\n{Fore.YELLOW}Found {len(duplicates)} duplicate pairs:{Style.RESET_ALL}"
            for dup, orig in duplicates:
                result += f"\n  • Duplicate: {dup}"
                result += f"\n    Original:  {orig}"
                result += f"\n    Size: {dup.stat().st_size / 1024:.1f} KB\n"
        else:
            result = f"\n{Fore.GREEN}No duplicates found{Style.RESET_ALL}"

        return result

    @staticmethod
    def watch_folder(folder_path, callback=None):
        """Watch a folder for changes"""
        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if not event.is_directory:
                    print(f"{Fore.YELLOW}📝 File modified: {event.src_path}{Style.RESET_ALL}")
                    if callback:
                        callback(event)

            def on_created(self, event):
                if not event.is_directory:
                    print(f"{Fore.GREEN}➕ File created: {event.src_path}{Style.RESET_ALL}")
                    if callback:
                        callback(event)

            def on_deleted(self, event):
                if not event.is_directory:
                    print(f"{Fore.RED}➖ File deleted: {event.src_path}{Style.RESET_ALL}")
                    if callback:
                        callback(event)

        folder = Path(folder_path).expanduser().resolve()
        if not folder.exists():
            return f"❌ Folder not found: {folder}"

        observer = Observer()
        observer.schedule(Handler(), str(folder), recursive=True)
        observer.start()

        print(f"{Fore.CYAN}👀 Watching folder: {folder}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Press Ctrl+C to stop watching{Style.RESET_ALL}")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

        return "✅ Folder watching stopped"

# ==================== APPLICATION CONTROL ====================

class AppController:
    """Control local applications"""

    @staticmethod
    def launch_app(app_name, args=None):
        """Launch an application"""
        try:
            if sys.platform == "darwin":  # macOS
                if not app_name.endswith('.app'):
                    app_name += '.app'
                subprocess.Popen(['open', '-a', app_name] + (args or []))
            elif sys.platform == "win32":  # Windows
                os.startfile(app_name)
            else:  # Linux
                subprocess.Popen([app_name] + (args or []))

            return f"{Fore.GREEN}✅ Launched: {app_name}{Style.RESET_ALL}"
        except Exception as e:
            return f"{Fore.RED}❌ Failed to launch {app_name}: {e}{Style.RESET_ALL}"

    @staticmethod
    def run_script(script_path, interpreter=None):
        """Run a script with appropriate interpreter"""
        script = Path(script_path).expanduser().resolve()
        if not script.exists():
            return f"❌ Script not found: {script}"

        try:
            if interpreter:
                cmd = [interpreter, str(script)]
            else:
                # Auto-detect interpreter
                ext = script.suffix.lower()
                if ext == '.py':
                    cmd = [sys.executable, str(script)]
                elif ext == '.js':
                    cmd = ['node', str(script)]
                elif ext == '.rb':
                    cmd = ['ruby', str(script)]
                elif ext == '.php':
                    cmd = ['php', str(script)]
                elif ext == '.sh':
                    cmd = ['bash', str(script)]
                elif ext == '.swift':
                    cmd = ['swift', str(script)]
                else:
                    # Make executable and run
                    os.chmod(script, 0o755)
                    cmd = [str(script)]

            print(f"{Fore.CYAN}🚀 Running: {' '.join(cmd)}{Style.RESET_ALL}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            output = f"{Fore.GREEN}✅ Script completed (exit code: {result.returncode}){Style.RESET_ALL}"
            if result.stdout:
                output += f"\n{Fore.WHITE}STDOUT:\n{result.stdout}{Style.RESET_ALL}"
            if result.stderr:
                output += f"\n{Fore.YELLOW}STDERR:\n{result.stderr}{Style.RESET_ALL}"

            return output
        except Exception as e:
            return f"{Fore.RED}❌ Error running script: {e}{Style.RESET_ALL}"

    @staticmethod
    def list_running_apps():
        """List running applications"""
        apps = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                apps.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu': proc.info['cpu_percent'],
                    'memory': proc.info['memory_percent']
                })
            except:
                pass

        # Sort by CPU usage
        apps.sort(key=lambda x: x['cpu'], reverse=True)

        result = f"\n{Fore.CYAN}📊 Running Applications:{Style.RESET_ALL}\n"
        result += f"{'PID':<8} {'CPU%':<6} {'MEM%':<6} {'Name'}\n"
        result += "-" * 40 + "\n"

        for app in apps[:20]:  # Show top 20
            result += f"{app['pid']:<8} {app['cpu']:<6.1f} {app['memory']:<6.1f} {app['name']}\n"

        return result

    @staticmethod
    def kill_app(pid_or_name):
        """Kill an application by PID or name"""
        try:
            if isinstance(pid_or_name, int) or pid_or_name.isdigit():
                # Kill by PID
                pid = int(pid_or_name)
                proc = psutil.Process(pid)
                proc.terminate()
                return f"{Fore.GREEN}✅ Terminated process {pid}: {proc.name()}{Style.RESET_ALL}"
            else:
                # Kill by name
                killed = 0
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] and pid_or_name.lower() in proc.info['name'].lower():
                        proc.terminate()
                        killed += 1

                if killed > 0:
                    return f"{Fore.GREEN}✅ Terminated {killed} process(es) matching '{pid_or_name}'{Style.RESET_ALL}"
                else:
                    return f"{Fore.YELLOW}No processes found matching '{pid_or_name}'{Style.RESET_ALL}"
        except Exception as e:
            return f"{Fore.RED}❌ Error killing process: {e}{Style.RESET_ALL}"

# ==================== DEVELOPMENT ====================

class DevEnvironment:
    """Development environment automation"""

    @staticmethod
    def create_project(project_type, name, path=None):
        """Create a new project scaffold"""
        if path:
            project_path = Path(path).expanduser().resolve() / name
        else:
            project_path = Path.cwd() / name

        project_path.mkdir(parents=True, exist_ok=True)

        templates = {
            'python': {
                'README.md': f'# {name}\n\nPython project\n',
                'requirements.txt': '# Dependencies\n',
                'main.py': '#!/usr/bin/env python3\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n',
                '.gitignore': '__pycache__/\n*.pyc\n.venv/\n',
            },
            'web': {
                'README.md': f'# {name}\n\nWeb project\n',
                'index.html': '<!DOCTYPE html>\n<html>\n<head>\n    <title>{name}</title>\n</head>\n<body>\n    <h1>Hello, World!</h1>\n</body>\n</html>'.format(name=name),
                'style.css': 'body {\n    font-family: Arial, sans-serif;\n    margin: 0;\n    padding: 20px;\n}\n',
                'script.js': 'console.log("Hello, World!");\n',
            },
            'node': {
                'README.md': f'# {name}\n\nNode.js project\n',
                'package.json': json.dumps({
                    'name': name,
                    'version': '1.0.0',
                    'description': '',
                    'main': 'index.js',
                    'scripts': {
                        'start': 'node index.js'
                    }
                }, indent=2),
                'index.js': 'console.log("Hello, World!");\n',
            },
            'swift': {
                'README.md': f'# {name}\n\nSwift project\n',
                'Package.swift': '// swift-tools-version:5.5\nimport PackageDescription\n\nlet package = Package(\n    name: "{name}",\n    products: [\n        .executable(name: "{name}", targets: ["{name}"]),\n    ],\n    targets: [\n        .executableTarget(\n            name: "{name}",\n            dependencies: []),\n    ]\n)'.format(name=name),
                'Sources/main.swift': 'print("Hello, World!")\n',
            },
            'xcode': {
                'README.md': f'# {name}\n\nXcode project\n',
                # Xcode project files would be created with xcodebuild
            }
        }

        if project_type not in templates:
            return f"❌ Unknown project type: {project_type}. Available: {', '.join(templates.keys())}"

        # Create files
        created = 0
        for filename, content in templates[project_type].items():
            file_path = project_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
            created += 1

        # Special handling for Xcode
        if project_type == 'xcode' and sys.platform == 'darwin':
            try:
                subprocess.run(['xcodebuild', '-create-xcodeproj', '-project', name],
                             cwd=str(project_path), check=True)
                created += 1
            except:
                print(f"{Fore.YELLOW}⚠️ Could not create Xcode project automatically{Style.RESET_ALL}")

        return f"""
{Fore.GREEN}✅ Created {project_type} project '{name}' at {project_path}{Style.RESET_ALL}
📁 Created {created} files
💡 Next steps:
  cd {project_path}
  {DevEnvironment.get_next_steps(project_type)}
"""

    @staticmethod
    def get_next_steps(project_type):
        """Get next steps for project type"""
        steps = {
            'python': 'python main.py',
            'web': 'open index.html',
            'node': 'npm install && npm start',
            'swift': 'swift run',
            'xcode': 'open *.xcodeproj'
        }
        return steps.get(project_type, 'Start coding!')

    @staticmethod
    def build_app(project_path, build_type='release'):
        """Build an application from source"""
        project = Path(project_path).expanduser().resolve()
        if not project.exists():
            return f"❌ Project not found: {project}"

        print(f"{Fore.CYAN}🔨 Building project: {project}{Style.RESET_ALL}")

        # Detect project type
        if (project / 'Package.swift').exists():
            # Swift package
            cmd = ['swift', 'build', '-c', build_type]
        elif (project / 'main.py').exists() or list(project.glob('*.py')):
            # Python - just check syntax
            cmd = ['python', '-m', 'py_compile'] + [str(f) for f in project.glob('**/*.py')]
        elif (project / 'package.json').exists():
            # Node.js
            cmd = ['npm', 'run', 'build'] if build_type == 'release' else ['npm', 'install']
        elif any(project.glob('*.xcodeproj')):
            # Xcode
            xcodeproj = next(project.glob('*.xcodeproj'))
            configuration = 'Release' if build_type == 'release' else 'Debug'
            cmd = ['xcodebuild', '-project', str(xcodeproj), '-configuration', configuration]
        else:
            return "❌ Could not detect project type"

        try:
            result = subprocess.run(cmd, cwd=str(project), capture_output=True, text=True)

            output = f"{Fore.GREEN}✅ Build completed (exit code: {result.returncode}){Style.RESET_ALL}"
            if result.stdout:
                output += f"\n{Fore.WHITE}{result.stdout}{Style.RESET_ALL}"
            if result.stderr:
                output += f"\n{Fore.YELLOW}{result.stderr}{Style.RESET_ALL}"

            return output
        except Exception as e:
            return f"{Fore.RED}❌ Build failed: {e}{Style.RESET_ALL}"

    @staticmethod
    def run_tests(project_path):
        """Run tests for a project"""
        project = Path(project_path).expanduser().resolve()
        if not project.exists():
            return f"❌ Project not found: {project}"

        print(f"{Fore.CYAN}🧪 Running tests: {project}{Style.RESET_ALL}")

        # Detect test framework
        if (project / 'Package.swift').exists():
            # Swift
            cmd = ['swift', 'test']
        elif (project / 'pytest.ini').exists() or list(project.glob('test_*.py')):
            # Python pytest
            cmd = ['pytest', '-v']
        elif (project / 'package.json').exists():
            # Node.js
            cmd = ['npm', 'test']
        elif (project / 'Gemfile').exists():
            # Ruby
            cmd = ['bundle', 'exec', 'rspec']
        else:
            # Try python unittest
            cmd = ['python', '-m', 'unittest', 'discover']

        try:
            result = subprocess.run(cmd, cwd=str(project), capture_output=True, text=True)

            output = f"{Fore.GREEN}✅ Tests completed (exit code: {result.returncode}){Style.RESET_ALL}"
            if result.stdout:
                output += f"\n{Fore.WHITE}{result.stdout}{Style.RESET_ALL}"
            if result.stderr:
                output += f"\n{Fore.YELLOW}{result.stderr}{Style.RESET_ALL}"

            return output
        except Exception as e:
            return f"{Fore.RED}❌ Tests failed: {e}{Style.RESET_ALL}"

# ==================== HARDWARE UTILIZATION ====================

class HardwareManager:
    """Manage hardware resources including GPU"""

    @staticmethod
    def get_gpu_info():
        """Get GPU information"""
        gpu_info = []

        # Check for NVIDIA GPU
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,utilization.gpu',
                                   '--format=csv,noheader'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = [p.strip() for p in line.split(',')]
                        gpu_info.append({
                            'name': parts[0],
                            'memory_total': parts[1],
                            'memory_used': parts[2],
                            'utilization': parts[3],
                            'type': 'nvidia'
                        })
        except:
            pass

        # Check for AMD GPU
        try:
            result = subprocess.run(['rocm-smi', '--showproductname'], capture_output=True, text=True)
            if result.returncode == 0:
                gpu_info.append({
                    'name': 'AMD GPU detected',
                    'type': 'amd'
                })
        except:
            pass

        # Check for Apple Silicon
        if sys.platform == 'darwin':
            try:
                result = subprocess.run(['sysctl', '-n', 'hw.targettype'], capture_output=True, text=True)
                if 'Apple' in result.stdout:
                    gpu_info.append({
                        'name': 'Apple Silicon (Metal)',
                        'type': 'apple'
                    })
            except:
                pass

        if not gpu_info:
            return f"{Fore.YELLOW}No GPU detected or GPU tools not installed{Style.RESET_ALL}"

        result = f"{Fore.CYAN}🎮 GPU Information:{Style.RESET_ALL}\n"
        for gpu in gpu_info:
            result += f"\n  • {gpu['name']}"
            if 'memory_total' in gpu:
                result += f"\n    Memory: {gpu['memory_used']} / {gpu['memory_total']}"
            if 'utilization' in gpu:
                result += f"\n    Utilization: {gpu['utilization']}"

        return result

    @staticmethod
    def train_model(script_path, gpu=True):
        """Train a machine learning model using GPU if available"""
        script = Path(script_path).expanduser().resolve()
        if not script.exists():
            return f"❌ Script not found: {script}"

        # Set environment variables for GPU
        env = os.environ.copy()
        if gpu:
            env['CUDA_VISIBLE_DEVICES'] = '0'  # Use first GPU
        else:
            env['CUDA_VISIBLE_DEVICES'] = ''  # Disable GPU

        print(f"{Fore.CYAN}🧠 Training model: {script}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}GPU: {'Enabled' if gpu else 'Disabled'}{Style.RESET_ALL}")

        try:
            result = subprocess.run([sys.executable, str(script)], env=env,
                                   capture_output=True, text=True)

            output = f"{Fore.GREEN}✅ Training completed (exit code: {result.returncode}){Style.RESET_ALL}"
            if result.stdout:
                output += f"\n{Fore.WHITE}{result.stdout}{Style.RESET_ALL}"
            if result.stderr:
                output += f"\n{Fore.YELLOW}{result.stderr}{Style.RESET_ALL}"

            return output
        except Exception as e:
            return f"{Fore.RED}❌ Training failed: {e}{Style.RESET_ALL}"

    @staticmethod
    def run_ollama_with_gpu():
        """Check if Ollama is using GPU"""
        try:
            # Check Ollama GPU status
            result = subprocess.run(['ollama', 'show'], capture_output=True, text=True)

            # Also check nvidia-smi for Ollama processes
            gpu_processes = []
            try:
                result = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name',
                                       '--format=csv,noheader'], capture_output=True, text=True)
                for line in result.stdout.strip().split('\n'):
                    if 'ollama' in line.lower():
                        gpu_processes.append(line)
            except:
                pass

            if gpu_processes:
                return f"{Fore.GREEN}✅ Ollama is using GPU{Style.RESET_ALL}\n" + "\n".join(gpu_processes)
            else:
                return f"{Fore.YELLOW}ℹ️ Ollama may not be using GPU (check with 'ollama show'){Style.RESET_ALL}"
        except:
            return f"{Fore.YELLOW}Could not determine Ollama GPU status{Style.RESET_ALL}"

# ==================== REMOTE OPERATION ====================

class RemoteServer:
    """HTTP server for remote control"""

    def __init__(self, port=5000, auth_token=None):
        self.port = port
        self.auth_token = auth_token or hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self.app = Flask(__name__)
        self.server_thread = None
        self.setup_routes()

        # Save token
        token_file = REMOTE_DIR / 'auth_token.txt'
        with open(token_file, 'w') as f:
            f.write(self.auth_token)
        print(f"{Fore.GREEN}🔑 Remote access token: {self.auth_token} (saved to {token_file}){Style.RESET_ALL}")

    def setup_routes(self):
        @self.app.route('/execute', methods=['POST'])
        def execute():
            # Simple authentication
            data = request.json
            if not data or data.get('token') != self.auth_token:
                return jsonify({'error': 'Unauthorized'}), 401

            command = data.get('command')
            if not command:
                return jsonify({'error': 'No command provided'}), 400

            try:
                # Execute command
                if command.startswith('!'):
                    # Shell command
                    result = subprocess.run(command[1:], shell=True,
                                          capture_output=True, text=True)
                    return jsonify({
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    })
                else:
                    # Tiny Swarm command - execute in main context
                    # This would need to be handled by the main loop
                    return jsonify({'message': 'Command received', 'command': command})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/files/list', methods=['POST'])
        def list_files():
            data = request.json
            if not data or data.get('token') != self.auth_token:
                return jsonify({'error': 'Unauthorized'}), 401

            path = data.get('path', '.')
            try:
                files = []
                for item in Path(path).expanduser().iterdir():
                    files.append({
                        'name': item.name,
                        'path': str(item),
                        'is_dir': item.is_dir(),
                        'size': item.stat().st_size if item.is_file() else 0,
                        'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    })
                return jsonify({'files': files})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/files/get', methods=['POST'])
        def get_file():
            data = request.json
            if not data or data.get('token') != self.auth_token:
                return jsonify({'error': 'Unauthorized'}), 401

            filepath = data.get('file')
            if not filepath:
                return jsonify({'error': 'No file specified'}), 400

            try:
                with open(Path(filepath).expanduser(), 'r') as f:
                    content = f.read()
                return jsonify({'content': content})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/apps/launch', methods=['POST'])
        def launch_app():
            data = request.json
            if not data or data.get('token') != self.auth_token:
                return jsonify({'error': 'Unauthorized'}), 401

            app_name = data.get('app')
            if not app_name:
                return jsonify({'error': 'No app specified'}), 400

            result = AppController.launch_app(app_name)
            return jsonify({'result': result})

    def start(self):
        """Start the server in a background thread"""
        self.server_thread = threading.Thread(target=self.app.run,
                                             kwargs={'host': '0.0.0.0', 'port': self.port},
                                             daemon=True)
        self.server_thread.start()
        print(f"{Fore.GREEN}🌐 Remote server started on port {self.port}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}To connect from phone: http://YOUR_IP:{self.port}{Style.RESET_ALL}")

    def stop(self):
        """Stop the server"""
        # Flask doesn't have a clean stop method in this simple setup
        print(f"{Fore.YELLOW}Remote server stopped{Style.RESET_ALL}")

class RemoteClient:
    """Client for remote control"""

    def __init__(self, server_url, auth_token):
        self.server_url = server_url.rstrip('/')
        self.auth_token = auth_token

    def execute(self, command):
        """Execute a command on the remote server"""
        try:
            response = requests.post(f"{self.server_url}/execute", json={
                'token': self.auth_token,
                'command': command
            })
            return response.json()
        except Exception as e:
            return {'error': str(e)}

    def list_files(self, path='.'):
        """List files on remote server"""
        try:
            response = requests.post(f"{self.server_url}/files/list", json={
                'token': self.auth_token,
                'path': path
            })
            return response.json()
        except Exception as e:
            return {'error': str(e)}

    def get_file(self, filepath):
        """Get file content from remote server"""
        try:
            response = requests.post(f"{self.server_url}/files/get", json={
                'token': self.auth_token,
                'file': filepath
            })
            return response.json()
        except Exception as e:
            return {'error': str(e)}

    def launch_app(self, app_name):
        """Launch app on remote server"""
        try:
            response = requests.post(f"{self.server_url}/apps/launch", json={
                'token': self.auth_token,
                'app': app_name
            })
            return response.json()
        except Exception as e:
            return {'error': str(e)}

# ==================== EMAIL INTEGRATION ====================

class EmailHandler:
    """Handle email operations"""

    @staticmethod
    def send_email(smtp_server, port, username, password, to_address, subject, body, attachments=None):
        """Send an email with optional attachments"""
        try:
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = to_address
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            # Add attachments
            if attachments:
                for attachment in attachments:
                    with open(attachment, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment)}')
                        msg.attach(part)

            # Send email
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()

            return f"{Fore.GREEN}✅ Email sent to {to_address}{Style.RESET_ALL}"
        except Exception as e:
            return f"{Fore.RED}❌ Failed to send email: {e}{Style.RESET_ALL}"

    @staticmethod
    def find_and_email_file(search_path, filename_pattern, email_config):
        """Find a file and email it"""
        path = Path(search_path).expanduser().resolve()
        matches = list(path.rglob(filename_pattern))

        if not matches:
            return f"❌ No files matching '{filename_pattern}' found in {path}"

        # Use the first match
        file_to_send = matches[0]

        return EmailHandler.send_email(
            email_config['smtp_server'],
            email_config['port'],
            email_config['username'],
            email_config['password'],
            email_config['to_address'],
            f"File: {file_to_send.name}",
            f"File found at: {file_to_send}",
            [str(file_to_send)]
        )

# ==================== ORIGINAL TINY SWARM FUNCTIONS ====================

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

# Remote server instance
remote_server = None

def print_banner():
    """Print banner with dynamic width"""
    models = get_ollama_models()

    # Adjust banner width based on terminal
    width = min(TERM_WIDTH, 100)  # Cap at 100 to prevent excessive width
    line = "═" * (width - 4)

    banner = f"""
{Fore.RED}╔{line}╗
{Fore.RED}║  🚀 TINY MODEL SWARM - ENHANCED EDITION{' ' * (width - 45)}║
{Fore.RED}╠{line}╣
{Fore.YELLOW}║  📊 Models:       {len(models)} installed locally{' ' * (width - 38 - len(str(len(models))))}║
{Fore.YELLOW}║  💾 Exports:      {str(EXPORTS_DIR)[:width-30]}{' ' * (width - 30 - len(str(EXPORTS_DIR)[:width-30]))}║
{Fore.RED}╠{line}╣
{Fore.GREEN}║  ✨ NEW FEATURES:{' ' * (width - 22)}║
{Fore.GREEN}║  • 📁 File Management - Organize, sort, watch{' ' * (width - 47)}║
{Fore.GREEN}║  • 🚀 App Control - Launch, run scripts, kill{' ' * (width - 47)}║
{Fore.GREEN}║  • 🛠️  Development - Create, build, test projects{' ' * (width - 50)}║
{Fore.GREEN}║  • 🎮 GPU Utilization - Train models, check GPU{' ' * (width - 48)}║
{Fore.GREEN}║  • 📱 Remote Operation - Control from phone{' ' * (width - 44)}║
{Fore.GREEN}║  • 📧 Email Integration - Find and email files{' ' * (width - 45)}║
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

def show_enhanced_help():
    """Show help with new commands"""
    help_text = f"""
{Fore.CYAN}📚 TINY SWARM COMMANDS:{Style.RESET_ALL}

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

{Fore.MAGENTA}✨ NEW ENHANCED FEATURES:{Style.RESET_ALL}

{Fore.CYAN}📁 FILE MANAGEMENT:{Style.RESET_ALL}
  /organize <folder>           - Organize files by category
  /sort-by-date <folder>       - Sort files into date folders
  /find-dupes <folder>         - Find duplicate files
  /watch <folder>              - Watch folder for changes

{Fore.CYAN}🚀 APPLICATION CONTROL:{Style.RESET_ALL}
  /launch <app> [args]         - Launch an application
  /run <script> [interpreter]  - Run a script
  /ps                          - List running processes
  /kill <pid|name>             - Kill a process

{Fore.CYAN}🛠️  DEVELOPMENT:{Style.RESET_ALL}
  /create-project <type> <name> [path] - Create project (python/web/node/swift/xcode)
  /build <path> [release|debug] - Build project
  /test <path>                 - Run project tests

{Fore.CYAN}🎮 HARDWARE:{Style.RESET_ALL}
  /gpu-info                    - Show GPU information
  /train <script> [gpu]        - Train ML model (use GPU)
  /ollama-gpu                  - Check if Ollama uses GPU

{Fore.CYAN}📱 REMOTE CONTROL:{Style.RESET_ALL}
  /remote-start [port]         - Start remote server
  /remote-stop                 - Stop remote server
  /remote-token                - Show access token
  /email-file <pattern> <to>   - Find and email a file

{Fore.YELLOW}EXAMPLES:{Style.RESET_ALL}
  /organize ~/Downloads                    # Organize downloads folder
  /launch Chrome                            # Launch Chrome
  /create-project python myapp              # Create Python app
  /gpu-info                                 # Check GPU status
  /remote-start 8080                        # Start remote server
  /email-file "*.pdf" user@example.com      # Email PDF files
"""
    print(help_text)

def main():
    """Main loop"""
    global default_timeout, MODEL_COLORS, TERM_WIDTH, remote_server
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
    print(f"{Fore.MAGENTA}🚀 Enhanced edition with file management, app control, development, GPU, and remote features!{Style.RESET_ALL}")

    selected_models = None
    max_workers = 3
    timeout = None  # No timeout by default

    show_enhanced_help()

    while True:
        try:
            user_input = input(f"{Fore.YELLOW}You{Style.RESET_ALL} > ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input == "/quit":
                # Stop remote server if running
                if remote_server:
                    remote_server.stop()
                break
            elif user_input == "/clear":
                print("\033[2J\033[H", end="")
                print_banner()
                continue
            elif user_input == "/help":
                show_enhanced_help()
                continue
            elif user_input == "/refresh":
                models = refresh_model_list()
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
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 3:
                    model_chain = [m.strip() for m in parts[1].split(',')]
                    prompt = parts[2]
                    collaborate_chain(prompt, model_chain, timeout)
                else:
                    print(f"{Fore.RED}Usage: /chain model1,model2,model3 <prompt>{Style.RESET_ALL}")
                continue

            elif user_input.startswith("/debate"):
                parts = user_input.split(maxsplit=3)
                if len(parts) >= 2:
                    topic = parts[1]

                    available = get_available_models()
                    debate_models = available[:3]
                    rounds = 2

                    if len(parts) >= 3:
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
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 2:
                    prompt = parts[1]
                    method = "majority"

                    if len(parts) >= 3:
                        method = parts[2]

                    available = get_available_models()
                    ensemble_models = available[:3]
                    collaborate_ensemble(prompt, ensemble_models, method, timeout)
                else:
                    print(f"{Fore.RED}Usage: /ensemble <prompt> [majority|summary|raw]{Style.RESET_ALL}")
                continue

            elif user_input.startswith("/specialist"):
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

            # BENCHMARK COMMANDS
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

            # SYSTEM COMMANDS
            elif user_input.startswith("/system"):
                parts = user_input.split(maxsplit=2)
                if len(parts) == 3:
                    set_system_prompt(parts[1], parts[2])
                else:
                    print(f"{Fore.RED}Usage: /system <model> <prompt>{Style.RESET_ALL}")
                continue
            elif user_input.startswith("/batch"):
                parts = user_input.split()
                if len(parts) >= 2:
                    file_path = parts[1]
                    format = "json"
                    batch_timeout = timeout

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

            # ==================== NEW ENHANCED COMMANDS ====================

            # FILE MANAGEMENT
            elif user_input.startswith("/organize"):
                parts = user_input.split(maxsplit=1)
                if len(parts) >= 2:
                    folder = parts[1]
                    result = FileOrganizer.organize_folder(folder)
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /organize <folder>{Style.RESET_ALL}")
                continue

            elif user_input.startswith("/sort-by-date"):
                parts = user_input.split(maxsplit=1)
                if len(parts) >= 2:
                    folder = parts[1]
                    result = FileOrganizer.sort_by_date(folder)
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /sort-by-date <folder>{Style.RESET_ALL}")
                continue

            elif user_input.startswith("/find-dupes"):
                parts = user_input.split(maxsplit=1)
                if len(parts) >= 2:
                    folder = parts[1]
                    result = FileOrganizer.find_duplicates(folder)
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /find-dupes <folder>{Style.RESET_ALL}")
                continue

            elif user_input.startswith("/watch"):
                parts = user_input.split(maxsplit=1)
                if len(parts) >= 2:
                    folder = parts[1]
                    FileOrganizer.watch_folder(folder)
                else:
                    print(f"{Fore.RED}Usage: /watch <folder>{Style.RESET_ALL}")
                continue

            # APPLICATION CONTROL
            elif user_input.startswith("/launch"):
                parts = user_input.split(maxsplit=1)
                if len(parts) >= 2:
                    result = AppController.launch_app(parts[1])
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /launch <app> [args]{Style.RESET_ALL}")
                continue

            elif user_input.startswith("/run"):
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 2:
                    script = parts[1]
                    interpreter = parts[2] if len(parts) >= 3 else None
                    result = AppController.run_script(script, interpreter)
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /run <script> [interpreter]{Style.RESET_ALL}")
                continue

            elif user_input == "/ps":
                result = AppController.list_running_apps()
                print(result)
                continue

            elif user_input.startswith("/kill"):
                parts = user_input.split(maxsplit=1)
                if len(parts) >= 2:
                    result = AppController.kill_app(parts[1])
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /kill <pid|name>{Style.RESET_ALL}")
                continue

            # DEVELOPMENT
            elif user_input.startswith("/create-project"):
                parts = user_input.split(maxsplit=3)
                if len(parts) >= 3:
                    project_type = parts[1]
                    name = parts[2]
                    path = parts[3] if len(parts) >= 4 else None
                    result = DevEnvironment.create_project(project_type, name, path)
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /create-project <type> <name> [path]{Style.RESET_ALL}")
                    print(f"Types: python, web, node, swift, xcode")
                continue

            elif user_input.startswith("/build"):
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 2:
                    project_path = parts[1]
                    build_type = parts[2] if len(parts) >= 3 else 'release'
                    result = DevEnvironment.build_app(project_path, build_type)
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /build <path> [release|debug]{Style.RESET_ALL}")
                continue

            elif user_input.startswith("/test"):
                parts = user_input.split(maxsplit=1)
                if len(parts) >= 2:
                    project_path = parts[1]
                    result = DevEnvironment.run_tests(project_path)
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /test <path>{Style.RESET_ALL}")
                continue

            # HARDWARE
            elif user_input == "/gpu-info":
                result = HardwareManager.get_gpu_info()
                print(result)
                continue

            elif user_input.startswith("/train"):
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 2:
                    script = parts[1]
                    use_gpu = parts[2].lower() != 'cpu' if len(parts) >= 3 else True
                    result = HardwareManager.train_model(script, use_gpu)
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /train <script> [gpu|cpu]{Style.RESET_ALL}")
                continue

            elif user_input == "/ollama-gpu":
                result = HardwareManager.run_ollama_with_gpu()
                print(result)
                continue

            # REMOTE CONTROL
            elif user_input.startswith("/remote-start"):
                parts = user_input.split()
                port = 5000
                if len(parts) > 1:
                    try:
                        port = int(parts[1])
                    except:
                        pass

                if remote_server:
                    print(f"{Fore.YELLOW}Remote server already running{Style.RESET_ALL}")
                else:
                    remote_server = RemoteServer(port=port)
                    remote_server.start()
                continue

            elif user_input == "/remote-stop":
                if remote_server:
                    remote_server.stop()
                    remote_server = None
                    print(f"{Fore.GREEN}✅ Remote server stopped{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}No remote server running{Style.RESET_ALL}")
                continue

            elif user_input == "/remote-token":
                token_file = REMOTE_DIR / 'auth_token.txt'
                if token_file.exists():
                    with open(token_file, 'r') as f:
                        token = f.read().strip()
                    print(f"{Fore.GREEN}🔑 Remote access token: {token}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}No remote server running or token not found{Style.RESET_ALL}")
                continue

            # EMAIL
            elif user_input.startswith("/email-file"):
                parts = user_input.split(maxsplit=2)
                if len(parts) >= 3:
                    pattern = parts[1]
                    to_address = parts[2]

                    # Simple email config - in practice, you'd want to store this securely
                    print(f"{Fore.YELLOW}This will search for files matching '{pattern}' and email to {to_address}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}You need to provide email credentials:{Style.RESET_ALL}")

                    smtp_server = input("SMTP server (e.g., smtp.gmail.com): ").strip()
                    port = input("Port (e.g., 587): ").strip()
                    username = input("Email username: ").strip()
                    password = input("Email password: ").strip()

                    email_config = {
                        'smtp_server': smtp_server,
                        'port': int(port) if port else 587,
                        'username': username,
                        'password': password,
                        'to_address': to_address
                    }

                    result = EmailHandler.find_and_email_file('.', pattern, email_config)
                    print(result)
                else:
                    print(f"{Fore.RED}Usage: /email-file <pattern> <to_address>{Style.RESET_ALL}")
                continue

            # Regular chat - use current timeout setting
            else:
                chat_with_swarm(user_input, selected_models, max_workers, timeout)

        except KeyboardInterrupt:
            print(f"\n{Fore.Yellow}Use /quit to exit{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
