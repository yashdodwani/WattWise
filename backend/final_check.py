#!/usr/bin/env python
"""Final verification script to confirm everything works"""

import time
import subprocess
import sys

print("=" * 70)
print("🔍 WattWise Final Verification - All Fixes Applied")
print("=" * 70)
print()

# 1. Check database migration
print("1️⃣  Checking Database Migration...")
print("-" * 70)
from db.session import engine
from sqlalchemy import text, inspect

inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('users')]

required_cols = ['username', 'password_hash', 'phone_number', 'consumer_number', 'is_active', 'created_at']
missing = [col for col in required_cols if col not in columns]

if missing:
    print(f"❌ Missing columns: {missing}")
    sys.exit(1)
else:
    print(f"✅ All authentication columns exist")
    print(f"   Columns: {columns}")

# 2. Check OTP table
print()
print("2️⃣  Checking OTP Records Table...")
print("-" * 70)
tables = inspector.get_table_names()
if 'otp_records' in tables:
    print(f"✅ OTP records table exists")
    otp_cols = [col['name'] for col in inspector.get_columns('otp_records')]
    print(f"   Columns: {otp_cols}")
else:
    print(f"❌ OTP records table not found")
    sys.exit(1)

# 3. Check app loads
print()
print("3️⃣  Checking Application Loads...")
print("-" * 70)
try:
    import main as main_mod
    app = main_mod.app
    print(f"✅ Main app loads successfully")
    print(f"   FastAPI app: {app.title}")

    # Check routers
    routes = [route.path for route in app.routes]
    auth_routes = [r for r in routes if '/auth' in r]
    print(f"   Auth routes: {len(auth_routes)} endpoints")

except Exception as e:
    print(f"❌ App loading failed: {e}")
    sys.exit(1)

# 4. Check dependencies
print()
print("4️⃣  Checking Dependencies...")
print("-" * 70)
deps = ['fastapi', 'sqlalchemy', 'pydantic', 'jwt', 'bcrypt', 'tzdata']
for dep in deps:
    try:
        __import__(dep if dep != 'jwt' else 'jwt' if dep != 'bcrypt' else 'bcrypt')
        print(f"✅ {dep}")
    except ImportError:
        print(f"❌ {dep} - NOT INSTALLED")
        sys.exit(1)

print()
print("=" * 70)
print("✅ ALL CHECKS PASSED!")
print("=" * 70)
print()
print("🚀 Your server is ready to run:")
print()
print("   cd backend")
print("   uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("📍 Then access:")
print("   http://localhost:8000/docs      (Swagger UI)")
print("   http://localhost:8000/redoc     (ReDoc)")
print("   http://localhost:8000           (Health check)")
print()
print("=" * 70)
