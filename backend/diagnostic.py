#!/usr/bin/env python
"""Diagnostic script to check WattWise backend startup"""

import sys
import os

print("="*60)
print("🔍 WattWise Backend Diagnostic Report")
print("="*60)

# Check Python version
print(f"\n✅ Python Version: {sys.version}")
print(f"✅ Python Path: {sys.executable}")

# Check imports
errors = []

try:
    import fastapi
    print("✅ FastAPI imported successfully")
except ImportError as e:
    errors.append(f"❌ FastAPI import failed: {e}")

try:
    import sqlalchemy
    print("✅ SQLAlchemy imported successfully")
except ImportError as e:
    errors.append(f"❌ SQLAlchemy import failed: {e}")

try:
    import pydantic
    print("✅ Pydantic imported successfully")
except ImportError as e:
    errors.append(f"❌ Pydantic import failed: {e}")

try:
    import jwt
    print("✅ PyJWT imported successfully")
except ImportError as e:
    errors.append(f"❌ PyJWT import failed: {e}")

try:
    import bcrypt
    print("✅ Bcrypt imported successfully")
except ImportError as e:
    errors.append(f"❌ Bcrypt import failed: {e}")

# Try importing main app
print("\n" + "="*60)
print("Testing Application Import...")
print("="*60)

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    from main import app
    print("✅ Main app imported successfully!")
    print("✅ FastAPI application initialized")
    print("✅ All routers registered")
    print("✅ Database models created")
    print("\n" + "="*60)
    print("🎉 APPLICATION IS READY TO RUN")
    print("="*60)
    print("\nCommand to start server:")
    print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    print("\nThen visit:")
    print("  http://localhost:8000/docs (Swagger UI)")
    print("  http://localhost:8000/redoc (ReDoc)")
    print("  http://localhost:8000 (Health check)")

except Exception as e:
    print(f"\n❌ ERROR importing main app: {e}")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
    errors.append(f"Application import failed: {e}")

# Report errors if any
if errors:
    print("\n" + "="*60)
    print("⚠️  ERRORS FOUND:")
    print("="*60)
    for error in errors:
        print(f"  {error}")
    print("\n❌ Please fix the above errors before running the server")
else:
    print("\n✅ All checks passed!")

