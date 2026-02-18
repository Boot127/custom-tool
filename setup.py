#thylis, 251684J, group 4
# setup.py
import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

required_packages = [
    'Flask==2.3.3',
    'Flask-WTF==1.1.1',
    'Flask-SQLAlchemy==3.0.5',
    'Werkzeug==2.3.7',
    'Pillow==10.0.0',
    'WTForms==3.0.1',
    'python-dotenv==1.0.0'
]

print("Installing required packages...")
for package in required_packages:
    print(f"Installing {package}...")
    install(package)

print("\n✅ All packages installed successfully!")