import os
import re
import subprocess
import json
import sys

ENV_PATH = "C:\\Users\\Lenovo\\.env"
BACKEND_DIR = "C:\\Users\\Lenovo\\.gemini\\antigravity\\scratch\\backtestlab\\backend"
FRONTEND_DIR = "C:\\Users\\Lenovo\\.gemini\\antigravity\\scratch\\backtestlab\\frontend"

def load_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    m = re.match(r"^([^=]+)=(.*)$", line)
                    if m:
                        env[m.group(1).strip()] = m.group(2).strip()
    return env

def print_setup_instructions():
    print("=" * 80)
    print("                      BACKTESTLAB DEPLOYMENT SETUP GUIDE")
    print("=" * 80)
    print("Please configure the required deployment credentials and databases in your environment.")
    print("\n1. DATABASE_URL: Create a hosted PostgreSQL database (on Neon.tech or Supabase.com).")
    print("2. RAILWAY_TOKEN: Sign up on Railway.app, go to Account Settings -> Tokens, and generate a token.")
    print("3. VERCEL_TOKEN: Sign up on Vercel.com, go to Account Settings -> Tokens, and generate a token.")
    print("\nTo save these securely, open your PowerShell terminal and run the following commands:")
    print("-" * 80)
    print('Add-Content -Path "C:\\Users\\Lenovo\\.env" -Value "DATABASE_URL=your_postgres_connection_string"')
    print('Add-Content -Path "C:\\Users\\Lenovo\\.env" -Value "RAILWAY_TOKEN=your_railway_token"')
    print('Add-Content -Path "C:\\Users\\Lenovo\\.env" -Value "VERCEL_TOKEN=your_vercel_token"')
    print("-" * 80)
    print("\nOnce saved, run this deploy script again to execute the live deployment automatically!")
    print("=" * 80)

def run_command(args, cwd, env=None):
    print(f"Running: {' '.join(args)} (in {cwd})")
    # Merge environment
    cmd_env = os.environ.copy()
    if env:
        cmd_env.update(env)
    
    # We run via shell=True on Windows to support npx properly
    res = subprocess.run(
        args,
        cwd=cwd,
        env=cmd_env,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if res.returncode != 0:
        print(f"Command failed with exit code {res.returncode}")
        print(f"STDOUT:\n{res.stdout}")
        print(f"STDERR:\n{res.stderr}")
        raise RuntimeError(f"Command failed: {args}")
    return res.stdout

def main():
    env = load_env()
    
    db_url = env.get("DATABASE_URL")
    railway_token = env.get("RAILWAY_TOKEN")
    vercel_token = env.get("VERCEL_TOKEN")
    
    if not db_url or not railway_token or not vercel_token:
        print_setup_instructions()
        sys.exit(1)
        
    print("All deployment credentials detected. Starting deployment pipeline...\n")
    
    deployment_env = {
        "RAILWAY_TOKEN": railway_token,
        "VERCEL_TOKEN": vercel_token,
        "DATABASE_URL": db_url
    }
    
    # 1. Deploy Backend to Railway
    print("--- [1/4] Deploying Backend to Railway ---")
    run_command(["npx", "@railway/cli", "up", "--new", "-y", "--detach"], cwd=BACKEND_DIR, env=deployment_env)
    
    # 2. Configure environment variables in Railway
    print("--- [2/4] Configuring Database Variable on Railway ---")
    run_command(["npx", "@railway/cli", "variable", "set", f"DATABASE_URL={db_url}"], cwd=BACKEND_DIR, env=deployment_env)
    
    # 3. Expose backend via generated domain
    print("--- [3/4] Generating Public Domain for Railway Service ---")
    run_command(["npx", "@railway/cli", "domain"], cwd=BACKEND_DIR, env=deployment_env)
    
    # Fetch the domain list
    print("Fetching backend domain name...")
    domain_list_json = run_command(["npx", "@railway/cli", "domain", "list", "--json"], cwd=BACKEND_DIR, env=deployment_env)
    
    try:
        domains = json.loads(domain_list_json)
        # Find any active domain
        backend_url = None
        for d in domains:
            domain_name = d.get("domain")
            if domain_name:
                backend_url = f"https://{domain_name}"
                break
        
        if not backend_url:
            raise ValueError("No domain found in Railway response.")
    except Exception as e:
        print(f"Error parsing Railway domains: {e}. Raw response: {domain_list_json}")
        sys.exit(1)
        
    print(f"Backend successfully deployed at: {backend_url}")
    
    # 4. Deploy Frontend to Vercel
    print("\n--- [4/4] Deploying Frontend to Vercel ---")
    # Build env is passed at compile time so Next.js embeds the live URL
    vercel_deploy_output = run_command(
        ["npx", "vercel", "--token", vercel_token, "--yes", "--prod", "-b", f"NEXT_PUBLIC_API_URL={backend_url}"],
        cwd=FRONTEND_DIR,
        env=deployment_env
    )
    
    # Vercel prints the URL to stdout
    print("Vercel deployment finished.")
    print("=" * 80)
    print("                       DEPLOYMENT COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"Backend URL:  {backend_url}")
    print(vercel_deploy_output)
    print("=" * 80)

if __name__ == "__main__":
    main()
