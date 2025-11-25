#!/usr/bin/env python3
"""
Pre-Deployment Dependency Test
Simulates Railway's build process locally to catch version conflicts BEFORE deploying.
"""

import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

def print_header(msg):
    print("\n" + "="*60)
    print(f"  {msg}")
    print("="*60)

def run_command(cmd, cwd=None):
    """Run command and return success status"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def test_clean_install():
    """Test fresh install in clean environment (like Railway does)"""
    
    print_header("PRE-DEPLOYMENT DEPENDENCY TEST")
    print("This simulates Railway's build process locally")
    print("Catching version conflicts BEFORE they cause production crashes!\n")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"📁 Created temporary test environment: {tmpdir}\n")
        
        # Step 1: Create virtual environment
        print_header("Step 1: Creating Clean Virtual Environment")
        success, output = run_command(f"python3 -m venv {tmpdir}/test_venv")
        if not success:
            print("❌ Failed to create virtual environment")
            print(output)
            return False
        print("✅ Virtual environment created")
        
        # Step 2: Copy requirements.txt
        print_header("Step 2: Copying requirements.txt")
        requirements_src = Path(__file__).parent.parent / "requirements.txt"
        requirements_dst = Path(tmpdir) / "requirements.txt"
        shutil.copy(requirements_src, requirements_dst)
        print(f"✅ Copied requirements.txt")
        
        # Step 3: Install dependencies (EXACTLY like Railway does)
        print_header("Step 3: Installing Dependencies (Railway Simulation)")
        print("This will take 1-2 minutes...\n")
        
        pip_cmd = f"{tmpdir}/test_venv/bin/pip install -r {tmpdir}/requirements.txt"
        success, output = run_command(pip_cmd)
        
        if not success:
            print("❌ DEPENDENCY INSTALLATION FAILED")
            print("\nThis is what would have crashed Railway!\n")
            print(output)
            print("\n" + "="*60)
            print("🔧 FIX REQUIRED:")
            print("   Update requirements.txt to resolve conflicts")
            print("   Then run this test again before deploying")
            print("="*60)
            return False
        
        print("✅ All dependencies installed successfully")
        
        # Step 4: Test critical imports
        print_header("Step 4: Testing Critical Imports")
        
        test_imports = [
            ("OpenAI", "from openai import AsyncOpenAI"),
            ("httpx", "import httpx"),
            ("exa-py", "from exa_py import Exa"),
            ("FastAPI", "from fastapi import FastAPI"),
            ("Slack SDK", "from slack_sdk import WebClient"),
            ("SQLAlchemy", "from sqlalchemy import create_engine"),
            ("Pydantic", "from pydantic import BaseModel"),
        ]
        
        python_cmd = f"{tmpdir}/test_venv/bin/python"
        failed_imports = []
        
        for name, import_stmt in test_imports:
            print(f"  Testing {name}...", end=" ")
            success, output = run_command(f'{python_cmd} -c "{import_stmt}"')
            if success:
                print("✅")
            else:
                print("❌")
                failed_imports.append((name, output))
        
        if failed_imports:
            print("\n❌ IMPORT FAILURES DETECTED")
            for name, error in failed_imports:
                print(f"\n{name} failed:")
                print(error[:200])
            return False
        
        # Step 5: Test OpenAI + httpx compatibility specifically
        print_header("Step 5: Testing OpenAI + httpx Compatibility")
        
        compat_test = '''
from openai import AsyncOpenAI
import httpx

# This is what crashed Railway - test it explicitly
try:
    client = AsyncOpenAI(api_key="test-key")
    print("✓ OpenAI client created successfully")
    print("✓ Compatible with httpx version:", httpx.__version__)
except TypeError as e:
    print("✗ COMPATIBILITY ERROR:", str(e))
    exit(1)
'''
        
        success, output = run_command(f'{python_cmd} -c \'{compat_test}\'')
        if not success:
            print("❌ OpenAI + httpx INCOMPATIBILITY DETECTED")
            print(output)
            print("\n🔧 This would have crashed Railway!")
            return False
        
        print(output)
        print("✅ OpenAI + httpx are compatible")
        
        # Step 6: Check version compatibility matrix
        print_header("Step 6: Checking Version Compatibility Matrix")
        
        # Write a test script to a file instead
        test_script = tmpdir + "/version_check.py"
        with open(test_script, 'w') as f:
            f.write("""
from importlib.metadata import version

httpx_ver = version('httpx')
openai_ver = version('openai')
exa_ver = version('exa-py')

print(f"httpx: {httpx_ver}")
print(f"openai: {openai_ver}")
print(f"exa-py: {exa_ver}")

# Check known compatibility issues
httpx_version = tuple(map(int, httpx_ver.split('.')[:2]))
openai_version = tuple(map(int, openai_ver.split('.')[:2]))

if httpx_version >= (0, 28) and openai_version < (1, 50):
    print("\\n⚠️  WARNING: OpenAI < 1.50 incompatible with httpx >= 0.28")
    exit(1)
""")
        
        success, output = run_command(f'{python_cmd} {test_script}')
        print(output)
        
        if not success:
            print("❌ Version compatibility check failed")
            return False
        
        print("✅ All versions compatible")
        
    print_header("🎉 ALL TESTS PASSED!")
    print("""
✅ Dependencies install cleanly
✅ All imports work
✅ OpenAI + httpx compatible
✅ Version matrix validated

🚀 SAFE TO DEPLOY TO RAILWAY!
    """)
    return True


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║  PRE-DEPLOYMENT DEPENDENCY TEST                           ║
║  Simulates Railway Build Process Locally                  ║
║                                                            ║
║  This test will:                                          ║
║  1. Create clean virtual environment                      ║
║  2. Install from requirements.txt (like Railway)          ║
║  3. Test all imports                                      ║
║  4. Validate version compatibility                        ║
║                                                            ║
║  ⏱️  Takes ~2 minutes                                      ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    try:
        success = test_clean_install()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

