import sys
import os

# Get the path of the Python executable currently being used
executable_path = sys.executable

# Get the Python version
python_version = sys.version

print(f"✅ Python Executable Path:\n   {executable_path}\n")
print(f"🐍 Python Version:\n   {python_version}\n")

# A clear check for a conda environment
if 'conda' in executable_path:
    print("🚀 It looks like you ARE using a Conda environment.")
else:
    print("⚠️ It looks like you are NOT using a Conda environment.")