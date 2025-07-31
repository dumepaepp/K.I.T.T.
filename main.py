import sys
import subprocess
import requests
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLineEdit, QTextEdit, QAction, QDialog, 
                             QFormLayout, QPushButton, QFileDialog)
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from pymetasploit3.msfrpc import MsfRpcClient

# --- Configuration ---
# These can be updated via the settings dialog
class AppConfig:
    def __init__(self):
        self.llm_api_url = "http://127.0.0.1:5000/v1/chat/completions"
        self.msf_user = "msf"
        self.msf_password = "msf_password" # Default password
        self.msf_host = "127.0.0.1"
        self.msf_port = 55553
        self.nmap_path = "nmap"

config = AppConfig()

# --- Settings Dialog ---
class SettingsDialog(QDialog):
    """A dialog to configure application settings."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        layout = QFormLayout(self)

        self.llm_url_edit = QLineEdit(config.llm_api_url)
        self.msf_user_edit = QLineEdit(config.msf_user)
        self.msf_pass_edit = QLineEdit(config.msf_password)
        self.msf_pass_edit.setEchoMode(QLineEdit.Password)
        
        nmap_button = QPushButton("Browse...")
        nmap_button.clicked.connect(self.browse_nmap)
        self.nmap_path_edit = QLineEdit(config.nmap_path)

        layout.addRow("LLM API URL:", self.llm_url_edit)
        layout.addRow("Metasploit User:", self.msf_user_edit)
        layout.addRow("Metasploit Password:", self.msf_pass_edit)
        layout.addRow("Nmap Path:", self.nmap_path_edit)
        layout.addRow(nmap_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

    def browse_nmap(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Nmap Executable")
        if path:
            self.nmap_path_edit.setText(path)

    def save_settings(self):
        config.llm_api_url = self.llm_url_edit.text()
        config.msf_user = self.msf_user_edit.text()
        config.msf_password = self.msf_pass_edit.text()
        config.nmap_path = self.nmap_path_edit.text()
        self.accept()

# --- Worker Thread ---
class Worker(QObject):
    """
    Worker thread for handling long-running tasks.
    """
    finished = pyqtSignal()
    output = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, command):
        super().__init__()
        self.command = command
        self.msf_client = None

    def connect_msf(self):
        """Initializes connection to Metasploit RPC server."""
        try:
            self.msf_client = MsfRpcClient(config.msf_password, user=config.msf_user, 
                                           server=config.msf_host, port=config.msf_port, ssl=False)
            self.output.emit("[INFO] Connected to Metasploit RPC server.\n")
            return True
        except Exception as e:
            self.error.emit(f"[ERROR] Failed to connect to Metasploit RPC: {e}\n"
                            f"Ensure msfrpcd is running with the correct credentials.\n"
                            f"Start it with: msfrpcd -P {config.msf_password} -U {config.msf_user} -a {config.msf_host}\n")
            return False

    @pyqtSlot()
    def run(self):
        try:
            cmd_lower = self.command.strip().lower()
            if cmd_lower.startswith("nmap "):
                self.run_nmap_command(self.command)
            elif cmd_lower.startswith("msf "):
                self.run_metasploit_command(self.command)
            else:
                self.query_llm(self.command)
        except Exception as e:
            self.error.emit(f"An unexpected error occurred in worker: {str(e)}\n")
        finally:
            self.finished.emit()

    def query_llm(self, prompt):
        self.output.emit(f"[INFO] Querying LLM with: {prompt}\n")
        try:
            payload = {
                "model": "whiterabbitneo-33b", # This should match the model loaded by text-generation-webui
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            }
            response = requests.post(config.llm_api_url, json=payload, timeout=120)
            response.raise_for_status()
            json_response = response.json()
            if 'choices' in json_response and json_response['choices']:
                llm_response = json_response['choices'][0]['message']['content']
                self.output.emit(f"[LLM RESPONSE]\n{llm_response}\n")
            else:
                self.error.emit(f"[ERROR] Unexpected LLM response format:\n{response.text}")
        except requests.exceptions.RequestException as e:
            self.error.emit(f"[ERROR] Could not connect to LLM at {config.llm_api_url}.\nDetails: {str(e)}\n")

    def run_nmap_command(self, full_command):
        self.output.emit(f"[INFO] Running command: {full_command}\n")
        try:
            command_parts = full_command.split()
            command_parts[0] = config.nmap_path
            
            process = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='ignore'
            )
            
            open_ports = []
            for line in iter(process.stdout.readline, ''):
                self.output.emit(line)
                if " open " in line and "Host is up" not in line:
                    match = re.match(r'(\d+/\w+)\s+open', line)
                    if match:
                        open_ports.append(match.group(1))
            
            process.stdout.close()
            process.wait()
            
            if open_ports:
                self.output.emit(f"\n[SUMMARY] Found open ports: {', '.join(open_ports)}\n")
            self.output.emit("\n[INFO] Nmap scan finished.\n")

        except FileNotFoundError:
            self.error.emit(f"[ERROR] Nmap not found at '{config.nmap_path}'. Check the path in Settings.\n")
        except Exception as e:
            self.error.emit(f"[ERROR] Failed to execute nmap: {str(e)}\n")

    def run_metasploit_command(self, command):
        """
        Executes a command using the Metasploit RPC.
        Example: msf use exploit/multi/handler; set LHOST 0.0.0.0; run
        """
        if not self.connect_msf():
            return

        commands_str = command.replace("msf ", "", 1).strip()
        commands = [cmd.strip() for cmd in commands_str.split(';')]

        for cmd_line in commands:
            parts = cmd_line.split()
            if not parts: continue
            
            cmd = parts[0].lower()
            self.output.emit(f"[MSF] > {cmd_line}\n")
            
            try:
                if cmd == 'use' and len(parts) > 1:
                    module_type = 'exploit' # Default
                    if 'auxiliary' in parts[1]: module_type = 'auxiliary'
                    if 'post' in parts[1]: module_type = 'post'
                    
                    self.current_module = self.msf_client.modules.use(module_type, '/'.join(parts[1:]))
                    self.output.emit(f"Using module: {self.current_module.name}\n")
                elif cmd == 'set' and len(parts) > 2:
                    if hasattr(self, 'current_module'):
                        self.current_module[parts[1].upper()] = ' '.join(parts[2:])
                        self.output.emit(f"Set {parts[1].upper()} => {' '.join(parts[2:])}\n")
                    else:
                        self.error.emit("[ERROR] No module selected. Use 'use <module>' first.\n")
                elif cmd == 'run' or cmd == 'exploit':
                    if hasattr(self, 'current_module'):
                        cid = self.msf_client.consoles.console().cid
                        self.msf_client.consoles.console(cid).write(self.current_module.fullname)
                        # This is a simplified execution, more complex interaction might be needed
                        console_output = self.msf_client.consoles.console(cid).read()
                        self.output.emit(console_output['data'])
                        self.msf_client.consoles.console(cid).destroy()
                    else:
                        self.error.emit("[ERROR] No module selected. Use 'use <module>' first.\n")
                else:
                    cid = self.msf_client.consoles.console().cid
                    self.msf_client.consoles.console(cid).write(cmd_line)
                    console_output = self.msf_client.consoles.console(cid).read()
                    self.output.emit(console_output['data'])
                    self.msf_client.consoles.console(cid).destroy()
            except Exception as e:
                self.error.emit(f"[MSF ERROR] Failed to execute '{cmd_line}': {e}\n")


# --- Main Application Window ---
class PentestApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pentest Assistant")
        self.setGeometry(100, 100, 900, 700)
        self.initUI()
        self.initMenu()

    def initMenu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')

        settings_action = QAction('&Settings', self)
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)

        exit_action = QAction('&Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.output_window = QTextEdit()
        self.output_window.setReadOnly(True)
        self.output_window.setStyleSheet("""
            QTextEdit {
                background-color: #2E3440;
                color: #D8DEE9;
                font-family: 'Courier New', monospace;
                font-size: 14px;
            }
        """)
        self.output_window.setPlaceholderText("Output will appear here. Prefix commands with 'nmap' or 'msf'.\n"
                                              "Example: nmap -sV -p- example.com\n"
                                              "Example: msf use auxiliary/scanner/http/title; set RHOSTS example.com; run\n"
                                              "Anything else will be sent to the LLM.")

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Enter command or query...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #4C566A;
                background-color: #3B4252;
                color: #ECEFF4;
            }
        """)
        self.search_bar.returnPressed.connect(self.start_task)

        layout.addWidget(self.output_window)
        layout.addWidget(self.search_bar)

    def start_task(self):
        command = self.search_bar.text()
        if not command: return

        self.output_window.append(f"<span style='color: #88C0D0;'>> {command}</span>")
        self.search_bar.setDisabled(True)

        self.thread = QThread()
        self.worker = Worker(command)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.output.connect(self.append_output)
        self.worker.error.connect(self.append_error)
        
        self.thread.finished.connect(lambda: self.search_bar.setDisabled(False))
        self.thread.finished.connect(lambda: self.search_bar.clear())
        self.thread.finished.connect(lambda: self.search_bar.setFocus())

        self.thread.start()

    def append_output(self, text):
        self.output_window.append(text.strip())

    def append_error(self, text):
        self.output_window.append(f"<span style='color: #BF616A;'>{text.strip()}</span>")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    main_win = PentestApp()
    main_win.show()
    sys.exit(app.exec_())
