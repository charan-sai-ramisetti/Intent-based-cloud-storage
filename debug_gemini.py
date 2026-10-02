#!/usr/bin/env python3
"""
Gemini diagnostic script — run on the EC2 server to find out why
the Gemini provider is failing and falling back to heuristic.

Usage:
    source /home/ubuntu/venv/bin/activate
    cd /home/ubuntu/tricloud-vault/backend/tri_cloud_vault
    python ../../debug_gemini.py
"""

import os
import sys
import traceback

# Load .env the same way Django does
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
    if not os.path.exists(env_path):
        # Try relative to CWD (if running from backend/tri_cloud_vault)
        for candidate in [
            os.path.join(os.getcwd(), "..", ".env"),
            os.path.join(os.getcwd(), ".env"),
            "/home/ubuntu/tricloud-vault/backend/.env",
        ]:
            if os.path.exists(candidate):
                env_path = candidate
                break
    load_dotenv(dotenv_path=env_path)
    print(f"[OK] Loaded .env from: {os.path.abspath(env_path)}")
except Exception as e:
    print(f"[WARN] Could not load .env: {e}")

print("=" * 60)
print("GEMINI DIAGNOSTIC")
print("=" * 60)

# --- Step 1: Check env vars ---
print("\n--- Step 1: Environment Variables ---")
api_key = os.getenv("GEMINI_API_KEY", "")
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
provider = os.getenv("DEFAULT_LLM_PROVIDER", "gemini")

print(f"DEFAULT_LLM_PROVIDER = {provider}")
print(f"GEMINI_MODEL         = {model}")
if api_key:
    print(f"GEMINI_API_KEY       = {api_key[:8]}...{api_key[-4:]} (length={len(api_key)})")
else:
    print("GEMINI_API_KEY       = *** EMPTY / NOT SET ***")
    print("[FAIL] No API key. This is likely why Gemini fails.")
    print("       Fix: Add GEMINI_API_KEY to AWS Secrets Manager")
    print("       under tricloud/production/secrets, then re-run Ansible.")
    sys.exit(1)

# --- Step 2: SDK import ---
print("\n--- Step 2: google-genai SDK import ---")
try:
    from google import genai
    from google.genai import types
    print(f"[OK] google-genai imported (version: {getattr(genai, '__version__', 'unknown')})")
except ImportError as e:
    print(f"[FAIL] Cannot import google-genai: {e}")
    print("       Fix: pip install google-genai")
    sys.exit(1)

# --- Step 3: Client creation ---
print("\n--- Step 3: Create Gemini client ---")
try:
    client = genai.Client(api_key=api_key)
    print("[OK] Client created")
except Exception as e:
    print(f"[FAIL] Client creation error: {e}")
    traceback.print_exc()
    sys.exit(1)

# --- Step 4: List available models ---
print("\n--- Step 4: List available models ---")
try:
    models = client.models.list()
    model_names = []
    for m in models:
        name = getattr(m, 'name', str(m))
        model_names.append(name)
    print(f"[OK] Found {len(model_names)} models")

    # Check if our target model is in the list
    target = model
    matches = [n for n in model_names if target in n]
    if matches:
        print(f"[OK] Target model '{target}' found: {matches}")
    else:
        print(f"[WARN] Target model '{target}' NOT in model list")
        # Show flash models
        flash_models = [n for n in model_names if "flash" in n.lower()]
        print(f"       Available flash models: {flash_models[:10]}")
        all_gemini = [n for n in model_names if "gemini" in n.lower()]
        print(f"       All gemini models: {all_gemini[:15]}")
except Exception as e:
    print(f"[WARN] Could not list models: {e}")
    print("       (This may be a permissions issue; continuing anyway)")

# --- Step 5: Simple generate (no tools) ---
print("\n--- Step 5: Simple generate_content (no tools) ---")
try:
    response = client.models.generate_content(
        model=model,
        contents="Say hello in one word.",
    )
    text = response.candidates[0].content.parts[0].text
    print(f"[OK] Response: {text.strip()}")
except Exception as e:
    print(f"[FAIL] Simple generate failed: {e}")
    traceback.print_exc()
    print("\n       This confirms the model call itself is broken.")
    print("       Possible causes:")
    print("       - Invalid API key")
    print("       - Model name not valid for this key/project")
    print("       - Network/firewall blocking googleapis.com")
    print("       - Quota exceeded")
    sys.exit(1)

# --- Step 6: Function calling (same as intent parser) ---
print("\n--- Step 6: Function calling (mirrors parse_intent_gemini) ---")
try:
    extract_func = types.FunctionDeclaration(
        name="extract_storage_constraints",
        description="Extract structured storage requirements from user text",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "primary_goal": types.Schema(
                    type=types.Type.STRING,
                    enum=["COST_MINIMIZATION", "LATENCY_MINIMIZATION", "MAX_REDUNDANCY", "BALANCED"],
                    description="Optimization objective",
                ),
                "access_pattern": types.Schema(
                    type=types.Type.STRING,
                    enum=["hot", "warm", "cold", "archival"],
                    description="Expected access frequency",
                ),
                "redundancy_level": types.Schema(
                    type=types.Type.INTEGER,
                    description="Number of cloud replicas (1-3)",
                ),
                "max_budget_monthly_usd": types.Schema(
                    type=types.Type.NUMBER,
                    description="Maximum monthly cost in USD",
                ),
            },
            required=["primary_goal", "access_pattern"],
        ),
    )

    tool = types.Tool(function_declarations=[extract_func])

    response = client.models.generate_content(
        model=model,
        contents="Store my database backup with 2 copies under $5 per month",
        config=types.GenerateContentConfig(
            system_instruction="You are a storage requirements analyzer. Extract constraints only.",
            tools=[tool],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="ANY")
            ),
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.function_call:
            fn = part.function_call
            print(f"[OK] Function call received: {fn.name}")
            print(f"     Args: {dict(fn.args)}")
            break
    else:
        print("[FAIL] No function_call in response parts:")
        for i, part in enumerate(response.candidates[0].content.parts):
            print(f"  Part {i}: {part}")

except Exception as e:
    print(f"[FAIL] Function calling failed: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
