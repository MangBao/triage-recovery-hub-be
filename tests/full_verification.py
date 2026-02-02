
import subprocess
import time
import sys
import httpx

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def run_command(command, description):
    print(f"\n{YELLOW}▶ [RUNNING] {description}{RESET}")
    print(f"{YELLOW}  Command: {command}{RESET}")
    print("-" * 50)
    
    try:
        # Run command and stream output
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Print output in real-time
        for line in process.stdout:
            print(line, end="")
            
        process.wait()
        
        if process.returncode == 0:
            print("-" * 50)
            print(f"{GREEN}✔ [PASSED] {description}{RESET}")
            return True
        else:
            print("-" * 50)
            print(f"{RED}✘ [FAILED] {description} (Exit Code: {process.returncode}){RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}✘ [ERROR] Execution failed: {e}{RESET}")
        return False

def wait_for_rate_limit_reset(seconds=65):
    print(f"\n{YELLOW}⏳ Waiting {seconds}s for Rate Limit cooldown...{RESET}")
    for i in range(seconds, 0, -1):
        print(f"\r   Time remaining: {i}s...", end="")
        time.sleep(1)
    print("\r   Reference reset complete.       \n")

def main():
    print(f"{GREEN}🚀 STARTING FULL VERIFICATION SUITE{RESET}")
    print("=" * 60)
    
    # Safety Check
    if "--force" not in sys.argv:
        print(f"\n{YELLOW}⚠ WARNING: This suite runs Stress & Heavy Load tests.{RESET}")
        print(f"{YELLOW}   It WILL consume significant Gemini quotas.{RESET}")
        response = input(f"   Do you want to run the FULL suite? (y/N): ").strip().lower()
        if response != "y":
            print("❌ Aborted by user.")
            sys.exit(0)
    
    auto_approve_subprocess = "--force" if "--force" in sys.argv else "--force" # Always pass force to children if we approved here
    
    overall_success = True
    
    # 1. Unit & Integration Tests (Pytest)
    if not run_command("pytest tests/test_*.py -v", "Unit & Integration Tests"):
        overall_success = False
        # Continue? Yes, for heavy load etc.
        
    # 2. Functional Business Logic (Stress Test)
    if not run_command(f"python tests/stress_test.py {auto_approve_subprocess}", "Functional Scenarios (Billing, Tech, Multilingual)"):
        overall_success = False

    # 3. Security & Edge Cases
    if not run_command("python tests/security_and_edge_cases.py", "Security & Edge Cases (SQLi, XSS, Size, Encode)"):
        overall_success = False

    # 4. Rate Limit (Needs fresh quota)
    # Check if we should wait? 
    # Just wait to be safe since previous tests might have used some quota
    wait_for_rate_limit_reset(10) 
    
    if not run_command("python tests/rate_limit_test.py", "Rate API Limiting Verification (30 req/min)"):
        overall_success = False
        
    # 5. Heavy Load
    wait_for_rate_limit_reset(65) # Wait for rate limit to clear before heavy load
    if not run_command(f"python tests/heavy_load.py {auto_approve_subprocess}", "Heavy Load Test (200 Concurrent Requests)"):
        overall_success = False

    print("\n" + "=" * 60)
    if overall_success:
        print(f"{GREEN}✅ ALL TESTS PASSED! SYSTEM READY FOR PRODUCTION.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}❌ SOME TESTS FAILED. CHECK LOGS ABOVE.{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RED}⚠ ABORTED BY USER{RESET}")
        sys.exit(130)
