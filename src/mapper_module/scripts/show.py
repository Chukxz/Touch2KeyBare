from mapper_module.utils import ADB_EXE

def run():
    if ADB_EXE.exists():
        print(f"ADB Executable found at: {ADB_EXE}")
    else:
        print("ADB Executable not found.")

if __name__ == "__main__":
    run()
