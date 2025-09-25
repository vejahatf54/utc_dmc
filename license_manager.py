#!/usr/bin/env python3
"""
WUTC License Manager - Standalone Application
===========================================

This is a standalone license generator for the WUTC application.
It creates licenses tied to server names with expiration dates.

Usage:
    python license_manager.py

Requirements:
    - cryptography
    - tkinter (usually included with Python)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import hashlib
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import base64
import socket


class LicenseManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WUTC License Manager")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Load config and generate encryption key
        self.config = self._load_config()
        self.key = self._get_license_encryption_key()
        self.cipher = Fernet(self.key)
        
        self.setup_ui()
        
    def _load_config(self):
        """Load configuration from config.json (unencrypted version)"""
        config_file = "config.json"
        
        if not os.path.exists(config_file):
            messagebox.showerror("Error", f"Configuration file '{config_file}' not found!")
            return None
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}")
            return None
    
    def _get_license_encryption_key(self):
        """Generate encryption key from config secret for license encryption/decryption"""
        if not self.config:
            raise Exception("Configuration not loaded")
            
        try:
            # Get the secret key from config
            config_secret = self.config.get('app', {}).get('secret_key', '')
            
            if not config_secret:
                raise Exception("Secret key not found in configuration")
            
            # Create a deterministic key from the config secret
            key_material = f"WUTC_LICENSE_ENCRYPTION_{config_secret}".encode()
            key_hash = hashlib.sha256(key_material).digest()
            
            # Fernet requires a 32-byte base64-encoded key
            return base64.urlsafe_b64encode(key_hash)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate encryption key: {e}")
            raise
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="WUTC License Manager", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Server Name
        ttk.Label(main_frame, text="Server Name:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.server_name_var = tk.StringVar()
        server_entry = ttk.Entry(main_frame, textvariable=self.server_name_var, width=40)
        server_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Auto-detect button
        detect_btn = ttk.Button(main_frame, text="Auto-detect", command=self.auto_detect_server)
        detect_btn.grid(row=1, column=2, padx=(5, 0))
        
        # License Duration
        ttk.Label(main_frame, text="License Duration (days):").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.duration_var = tk.StringVar(value="365")
        duration_entry = ttk.Entry(main_frame, textvariable=self.duration_var, width=10)
        duration_entry.grid(row=2, column=1, sticky=tk.W, pady=(10, 0))
        
        # Preset duration buttons
        preset_frame = ttk.Frame(main_frame)
        preset_frame.grid(row=3, column=1, sticky=tk.W, pady=(5, 0))
        
        ttk.Button(preset_frame, text="30 days", command=lambda: self.duration_var.set("30")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(preset_frame, text="90 days", command=lambda: self.duration_var.set("90")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(preset_frame, text="1 year", command=lambda: self.duration_var.set("365")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(preset_frame, text="Unlimited", command=lambda: self.duration_var.set("36500")).pack(side=tk.LEFT)
        
        # Additional Info
        ttk.Label(main_frame, text="Additional Info (optional):").grid(row=4, column=0, sticky=(tk.W, tk.N), padx=(0, 10), pady=(15, 0))
        self.info_text = tk.Text(main_frame, height=4, width=50)
        self.info_text.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(15, 0))
        
        # License Preview
        ttk.Label(main_frame, text="License Preview:").grid(row=5, column=0, sticky=(tk.W, tk.N), padx=(0, 10), pady=(15, 0))
        
        preview_frame = ttk.Frame(main_frame)
        preview_frame.grid(row=5, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(15, 0))
        preview_frame.columnconfigure(0, weight=1)
        
        self.preview_text = tk.Text(preview_frame, height=12, width=60, wrap=tk.WORD, state=tk.DISABLED)
        preview_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scroll.set)
        
        self.preview_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        preview_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=(20, 0))
        
        ttk.Button(button_frame, text="Generate Preview", command=self.generate_preview).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Save License", command=self.save_license).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Validate License", command=self.validate_license).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 0))
        
        # Configure row weights for resizing
        main_frame.rowconfigure(5, weight=1)
        preview_frame.rowconfigure(0, weight=1)
    
    def auto_detect_server(self):
        """Auto-detect the current server name"""
        try:
            hostname = socket.gethostname()
            self.server_name_var.set(hostname)
            self.status_var.set(f"Auto-detected server: {hostname}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not auto-detect server name: {e}")
    
    def generate_license_data(self, server_name, days, additional_info=""):
        """Generate license data"""
        issue_date = datetime.now()
        expiry_date = issue_date + timedelta(days=int(days))
        
        license_data = {
            "server_name": server_name,
            "issue_date": issue_date.isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "days": int(days),
            "additional_info": additional_info,
            "version": "1.0"
        }
        
        return license_data
    
    def encrypt_license(self, license_data):
        """Encrypt license data"""
        json_data = json.dumps(license_data, indent=2)
        encrypted = self.cipher.encrypt(json_data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_license(self, encrypted_license):
        """Decrypt license data"""
        try:
            decoded = base64.b64decode(encrypted_license.encode())
            decrypted = self.cipher.decrypt(decoded)
            return json.loads(decrypted.decode())
        except Exception as e:
            raise ValueError(f"Invalid license format: {e}")
    
    def format_license_file(self, license_data, encrypted_license):
        """Format the complete license file with human-readable header"""
        header = f"""# WUTC Application License
# ========================
# 
# Server Name: {license_data['server_name']}
# Issue Date:  {datetime.fromisoformat(license_data['issue_date']).strftime('%Y-%m-%d %H:%M:%S')}
# Expiry Date: {datetime.fromisoformat(license_data['expiry_date']).strftime('%Y-%m-%d %H:%M:%S')}
# Duration:    {license_data['days']} days
# Version:     {license_data['version']}
"""
        
        if license_data.get('additional_info'):
            header += f"# Notes:      {license_data['additional_info']}\n"
        
        header += """# 
# This license is tied to the server name specified above.
# Do not modify this file or the license will become invalid.
# 
# ========================

"""
        
        return header + encrypted_license
    
    def generate_preview(self):
        """Generate and show license preview"""
        server_name = self.server_name_var.get().strip()
        duration_str = self.duration_var.get().strip()
        additional_info = self.info_text.get("1.0", tk.END).strip()
        
        if not server_name:
            messagebox.showerror("Error", "Please enter a server name")
            return
        
        try:
            duration = int(duration_str)
            if duration <= 0:
                raise ValueError("Duration must be positive")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of days")
            return
        
        try:
            license_data = self.generate_license_data(server_name, duration, additional_info)
            encrypted_license = self.encrypt_license(license_data)
            formatted_license = self.format_license_file(license_data, encrypted_license)
            
            # Show preview
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert("1.0", formatted_license)
            self.preview_text.config(state=tk.DISABLED)
            
            self.status_var.set(f"License preview generated for {server_name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error generating license: {e}")
    
    def save_license(self):
        """Save license to file"""
        server_name = self.server_name_var.get().strip()
        
        if not server_name:
            messagebox.showerror("Error", "Please enter a server name")
            return
        
        # Generate license first
        self.generate_preview()
        
        # Get license content
        license_content = self.preview_text.get("1.0", tk.END).strip()
        
        if not license_content:
            messagebox.showerror("Error", "No license content to save")
            return
        
        # Ask for save location - default to license folder
        license_dir = "license"
        if not os.path.exists(license_dir):
            os.makedirs(license_dir)
        
        default_filename = f"{server_name.replace(' ', '_')}_license.lic"
        filename = filedialog.asksaveasfilename(
            defaultextension=".lic",
            filetypes=[("License files", "*.lic"), ("All files", "*.*")],
            initialfile=default_filename,
            initialdir=license_dir
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(license_content)
                
                messagebox.showinfo("Success", f"License saved to {filename}")
                self.status_var.set(f"License saved: {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error saving license: {e}")
    
    def validate_license(self):
        """Validate an existing license file"""
        filename = filedialog.askopenfilename(
            filetypes=[("License files", "*.lic"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r') as f:
                content = f.read()
            
            # Extract encrypted part (everything after the header)
            lines = content.split('\n')
            encrypted_start = -1
            
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#') and '=' not in line[:30]:
                    encrypted_start = i
                    break
            
            if encrypted_start == -1:
                raise ValueError("Could not find encrypted license data")
            
            encrypted_license = '\n'.join(lines[encrypted_start:]).strip()
            
            # Decrypt and validate
            license_data = self.decrypt_license(encrypted_license)
            
            # Check expiry
            expiry_date = datetime.fromisoformat(license_data['expiry_date'])
            current_date = datetime.now()
            is_expired = current_date > expiry_date
            
            # Format validation result
            result = f"""License Validation Result
========================

File: {os.path.basename(filename)}
Server Name: {license_data['server_name']}
Issue Date: {datetime.fromisoformat(license_data['issue_date']).strftime('%Y-%m-%d %H:%M:%S')}
Expiry Date: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}
Duration: {license_data['days']} days
Status: {'EXPIRED' if is_expired else 'VALID'}

"""
            
            if license_data.get('additional_info'):
                result += f"Notes: {license_data['additional_info']}\n"
            
            if is_expired:
                result += f"\nThis license expired {(current_date - expiry_date).days} days ago."
            else:
                days_remaining = (expiry_date - current_date).days
                result += f"\nThis license is valid for {days_remaining} more days."
            
            # Show result
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert("1.0", result)
            self.preview_text.config(state=tk.DISABLED)
            
            status_msg = f"License {'EXPIRED' if is_expired else 'VALID'}: {license_data['server_name']}"
            self.status_var.set(status_msg)
            
            if is_expired:
                messagebox.showwarning("License Expired", f"The license for {license_data['server_name']} has expired!")
            else:
                messagebox.showinfo("License Valid", f"The license for {license_data['server_name']} is valid!")
                
        except Exception as e:
            messagebox.showerror("Validation Error", f"Error validating license: {e}")
            self.status_var.set("License validation failed")
    
    def run(self):
        """Run the license manager"""
        self.root.mainloop()


if __name__ == "__main__":
    print("WUTC License Manager")
    print("===================")
    print()
    
    # Check dependencies
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        print("Error: cryptography package is required.")
        print("Install it with: pip install cryptography")
        exit(1)
    
    # Run the application
    app = LicenseManager()
    app.run()