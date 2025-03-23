import sys
import os
from cx_Freeze import setup, Executable

# Define the path to your project files
project_path = os.path.dirname(os.path.abspath(__file__))
inventory_path = os.path.join(project_path, 'inventoryManager')

# Make sure Python can find your local modules
sys.path.append(project_path)
sys.path.append(inventory_path)

# Determine if we're on Windows
is_windows = sys.platform.startswith('win')

# Set the appropriate target name and base based on platform
target_name = "mainCron.exe" if is_windows else "mainCron"
base = "Console" if is_windows else None

build_exe_options = {
    "packages": [
        "os", 
        "requests", 
        "json", 
        "csv", 
        "dotenv", 
        "pprint",
        "argparse",
        "socks",
        "httplib2"
    ],
    "includes": [
        "getterFunctions", 
        "queryCost", 
        "config", 
        "googleSheetsManager"
    ],
    "include_files": [
        # Include JSON credentials file
        (os.path.join(inventory_path, "nextdayaccess-452516-a51a5b7a02b8.json"), "nextdayaccess-452516-a51a5b7a02b8.json"),
        # Include the .env file
        (os.path.join(project_path, ".env"), ".env"),
        # Include CSV file
        (os.path.join(inventory_path, "inventory_download.csv"), "inventory_download.csv")
    ],
    "path": [inventory_path] + sys.path
}

setup(
    name="mainCron",
    version="1.0",
    description="NextDayAccess Inventory Manager",
    options={"build_exe": build_exe_options},
    executables=[Executable(
        os.path.join(inventory_path, "mainCron.py"), 
        target_name=target_name,
        base=base
    )]
)