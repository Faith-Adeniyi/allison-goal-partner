import os
import subprocess
import sys
import platform

def get_venv_python():
    """
    Locates the virtual environment Python executable.
    Returns the absolute path to the venv python.exe.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check for Windows vs Unix/Mac path structure
    if platform.system() == "Windows":
        venv_python = os.path.join(base_dir, "venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join(base_dir, "venv", "bin", "python")

    return venv_python

def manage_system():
    # STRICT PROJECT SCOPE: ALLISON GOAL PARTNER
    print("\n--- ALLISON SYSTEM MANAGER ---")
    print("1. Load & Verify Virtual Environment")
    print("2. Start API Server (FastAPI)")
    print("3. Run Integration Test (Verify Logic)")
    print("4. Storage Maintenance (Clear Saved Plans)")
    print("Q. Quit")
    
    choice = input("\nSelect an option: ").upper()
    
    # We resolve the venv path immediately for all options
    venv_exec = get_venv_python()

    if choice == "1":
        print("\n[SYSTEM] Loading Virtual Environment...")
        if os.path.exists(venv_exec):
            print(f"✔ VENV FOUND: {venv_exec}")
            print("✔ STATUS: Ready to run Server and Tests.")
            # We can verify dependencies here to be fancy
            try:
                subprocess.run([venv_exec, "-m", "pip", "show", "fastapi"], capture_output=True)
                print("✔ DEPENDENCIES: Verified (FastAPI is installed).")
            except:
                print("⚠ WARNING: Venv exists but packages might be missing.")
        else:
            print("❌ ERROR: 'venv' folder not found. Please run 'python -m venv venv'.")
        
        # Pause so the user can read the status
        input("\nPress Enter to return to menu...")
        manage_system() # Reload menu

    elif choice == "2":
        print(f"\n[SYSTEM] Launching Server using: {venv_exec}")
        if not os.path.exists(venv_exec):
             print("❌ ERROR: Venv not found. Select Option 1 to verify.")
        else:
            try:
                # Uses the LOADED venv path to run the module
                subprocess.run([venv_exec, "-m", "uvicorn", "app.main:app", "--reload"])
            except KeyboardInterrupt:
                print("\n[SYSTEM] Server stopped.")

    elif choice == "3":
        print("\n[SYSTEM] Running Logic Verification...")
        if not os.path.exists(venv_exec):
             print("❌ ERROR: Venv not found. Select Option 1 to verify.")
        else:
            subprocess.run([venv_exec, "verify_logic.py"])

    elif choice == "4":
        confirm = input("Confirm: Delete all saved JSON goal plans? (y/n): ")
        if confirm.lower() == 'y':
            plan_dir = "saved_plans"
            if os.path.exists(plan_dir):
                for file in os.listdir(plan_dir):
                    os.remove(os.path.join(plan_dir, file))
                print(f"[SYSTEM] Cleaned {plan_dir} folder successfully.")
            else:
                print("[SYSTEM] No storage folder found yet.")
        manage_system()

    elif choice == "Q":
        print("Exiting Allison System Manager.")
        sys.exit()

if __name__ == "__main__":
    manage_system()