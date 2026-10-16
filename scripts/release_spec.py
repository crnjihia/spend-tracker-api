"""Script to package OpenAPI specification files and metadata for GitHub Releases."""

import argparse
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

import yaml

# Disable C-extensions in restricted envs
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
os.environ["JWT_SECRET_KEY"] = "release-packager-secret-key-32-chars-sample"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.main import app  # noqa: E402


def get_app_version() -> str:
    """Retrieve version from app or pyproject."""
    return app.version or "0.1.0"


def generate_specs(output_dir: Path, version_tag: str) -> tuple[Path, Path]:
    """Generate versioned openapi.json and openapi.yaml."""
    output_dir.mkdir(parents=True, exist_ok=True)

    openapi_data = app.openapi()
    # Update version in spec
    clean_version = version_tag.lstrip("v")
    openapi_data["info"]["version"] = clean_version
    openapi_data["info"]["title"] = "Spend Tracker API"
    openapi_data["info"]["description"] = (
        "Personal finance tracking REST API built for Kenyan spending habits. "
        "Handles M-Pesa transactions, SACCO contributions, utility bills, and budgets."
    )

    if not openapi_data.get("servers"):
        openapi_data["servers"] = [
            {"url": "http://127.0.0.1:8000", "description": "Local Development Server"},
            {"url": "https://api.spendtracker.ke", "description": "Production Server"},
        ]

    json_path = output_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_data, f, indent=2)

    yaml_path = output_dir / "openapi.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_data, f, sort_keys=False, allow_unicode=True)

    print(f"Generated spec JSON: {json_path}")
    print(f"Generated spec YAML: {yaml_path}")
    return json_path, yaml_path


def compute_sha256(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def package_release_bundle(version_tag: str, dist_dir: Path) -> Path:
    """Create a zip archive containing OpenAPI specs, documentation, and checksums."""
    dist_dir.mkdir(parents=True, exist_ok=True)
    clean_version = version_tag.lstrip("v")

    json_path, yaml_path = generate_specs(dist_dir, version_tag)

    zip_filename = f"spend-tracker-api-openapi-v{clean_version}.zip"
    zip_path = dist_dir / zip_filename

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(json_path, arcname="openapi.json")
        archive.write(yaml_path, arcname="openapi.yaml")
        readme_file = REPO_ROOT / "README.md"
        if readme_file.exists():
            archive.write(readme_file, arcname="README.md")
        changelog_file = REPO_ROOT / "CHANGELOG.md"
        if changelog_file.exists():
            archive.write(changelog_file, arcname="CHANGELOG.md")
        license_file = REPO_ROOT / "LICENSE"
        if license_file.exists():
            archive.write(license_file, arcname="LICENSE")

    # Generate SHA-256 checksums file
    checksums_path = dist_dir / f"checksums-v{clean_version}.txt"
    with open(checksums_path, "w", encoding="utf-8") as f:
        for p in [json_path, yaml_path, zip_path]:
            f.write(f"{compute_sha256(p)}  {p.name}\n")

    print(f"Release bundle created: {zip_path}")
    print(f"Checksums created: {checksums_path}")
    return zip_path


def main():
    parser = argparse.ArgumentParser(description="Package OpenAPI specifications for release.")
    parser.add_argument(
        "--version",
        default=f"v{get_app_version()}",
        help="Version tag for the release (e.g. v0.1.0)",
    )
    parser.add_argument(
        "--outdir",
        default="dist",
        help="Directory to place release artifacts (default: dist)",
    )
    args = parser.parse_args()

    out_path = REPO_ROOT / args.outdir
    print(f"Packaging OpenAPI release assets for {args.version} into {out_path}...")
    package_release_bundle(args.version, out_path)
    print("Done!")


if __name__ == "__main__":
    main()
