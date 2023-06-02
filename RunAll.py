import subprocess
import os

scriptfolders = ["Webscrapers - Wellington"]

for folder_path in scriptfolders:
    file_list = os.listdir(folder_path)
    python_files = [file for file in file_list if file.endswith(".py")]
    for file in python_files:
        file_path = os.path.join(folder_path, file)
        subprocess.run(["python", file_path])