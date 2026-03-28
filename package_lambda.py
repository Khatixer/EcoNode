import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.join(ROOT, "lambda_package")
ZIP_PATH = os.path.join(ROOT, "econode_lambda.zip")

print("Step 1 — Cleaning...")
if os.path.exists(PACKAGE_DIR):
    shutil.rmtree(PACKAGE_DIR)
if os.path.exists(ZIP_PATH):
    os.remove(ZIP_PATH)
os.makedirs(PACKAGE_DIR)

print("Step 2 — Installing minimal dependencies for Linux...")
subprocess.check_call([
    sys.executable, "-m", "pip", "install",
    "boto3==1.35.0",
    "python-dotenv==1.0.1",
    "reportlab==4.2.2",
    "slack-sdk>=3.38.0",
    "requests",
    "pydantic",
    "pydantic-core",
    "langchain-core",
    "langchain-anthropic",
    "langgraph>=1.0.2,<1.1.0",
    "--platform", "manylinux2014_x86_64",
    "--implementation", "cp",
    "--python-version", "3.13",
    "--only-binary=:all:",
    "-t", PACKAGE_DIR,
    "--quiet",
    "--upgrade",
])

print("Step 3 — Copying code...")
for folder in ["agents", "core", "integrations", "output"]:
    src = os.path.join(ROOT, folder)
    dst = os.path.join(PACKAGE_DIR, folder)
    if os.path.exists(src):
        shutil.copytree(src, dst)
        print(f"  Copied {folder}/")

shutil.copy(
    os.path.join(ROOT, "lambda_handler.py"),
    os.path.join(PACKAGE_DIR, "lambda_handler.py"),
)
print("  Copied lambda_handler.py")

print("Step 4 — Removing unnecessary files to reduce size...")
# Remove test files, __pycache__, .pyc files
for root, dirs, files in os.walk(PACKAGE_DIR):
    for f in files:
        if f.endswith((".pyc", ".pyo")):
            os.remove(os.path.join(root, f))
    for d in dirs:
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))

# Remove heavy unused packages
for pkg in ["boto3", "botocore", "s3transfer", "urllib3"]:
    pkg_path = os.path.join(PACKAGE_DIR, pkg)
    if os.path.exists(pkg_path):
        shutil.rmtree(pkg_path)
        print(f"  Removed {pkg}/ (already in Lambda runtime)")

print("Step 5 — Creating zip...")
shutil.make_archive(
    base_name=os.path.join(ROOT, "econode_lambda"),
    format="zip",
    root_dir=PACKAGE_DIR,
    base_dir=".",
)

size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
print(f"\nDone. Zip size: {size_mb:.1f} MB")
print(f"Location: {ZIP_PATH}")

if size_mb > 250:
    print("WARNING: Still too large. Check what's big inside lambda_package/")
else:
    print("Size OK — ready to upload to S3.")