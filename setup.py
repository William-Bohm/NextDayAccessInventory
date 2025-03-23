import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["os", "requests", "json", "csv", "dotenv", "getterFunctions", 
                 "queryCost", "config", "googleSheetsManager"],
    "include_files": [
        ("inventoryManager/nextdayaccess-452516-a51a5b7a02b8.json", "nextdayaccess-452516-a51a5b7a02b8.json"),
        (".env", ".env")
    ]
}

setup(
    name="mainCron",
    version="1.0",
    description="NextDayAccess Inventory Manager",
    options={"build_exe": build_exe_options},
    executables=[Executable("inventoryManager/mainCron.py", target_name="mainCron.exe")]
)