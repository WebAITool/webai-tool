import hashlib
from pathlib import Path

FRONTEND_EXTENSIONS = {'.vue', '.jsx', '.tsx', '.css', '.scss', '.sass', '.less', '.html', '.js', '.ts'}


def compute_frontend_hash(prjdir: str) -> str:
    frontend_path = Path(prjdir) / 'frontend'
    if not frontend_path.exists():
        frontend_path = Path(prjdir) / 'src'
    if not frontend_path.exists():
        return ""
    
    hasher = hashlib.md5()
    for ext in FRONTEND_EXTENSIONS:
        for filepath in frontend_path.rglob(f'*{ext}'):
            if filepath.is_file():
                try:
                    with open(filepath, 'rb') as f:
                        hasher.update(filepath.name.encode())
                        hasher.update(f.read())
                except Exception:
                    pass
    
    return hasher.hexdigest()


def frontend_changed(prjdir: str, old_hash: str):
    new_hash = compute_frontend_hash(prjdir)
    if not new_hash:
        return False, ""
    if not old_hash:
        return True, new_hash
    return new_hash != old_hash, new_hash


def test_hash_computation():
    test_project = Path(r"C:\IMPORTANT\NSU\3\shc\webai-tool\bet-app")
    if not test_project.exists():
        print(f"Project not found: {test_project}")
        return
    
    print(f"Project: {test_project}\n")
    
    hash1 = compute_frontend_hash(str(test_project))
    hash2 = compute_frontend_hash(str(test_project))
    
    print(f"Hash 1: {hash1[:16] if hash1 else 'empty'}")
    print(f"Hash 2: {hash2[:16] if hash2 else 'empty'}")
    print(f"Identical: {hash1 == hash2}")
    
    print("\nFrontend changed test:")
    changed, new_hash = frontend_changed(str(test_project), "")
    print(f"  First call: changed={changed}")
    
    changed2, _ = frontend_changed(str(test_project), new_hash)
    print(f"  Second call: changed={changed2}")
    
    print(f"\nPassed: {changed and not changed2}")


if __name__ == "__main__":
    test_hash_computation()