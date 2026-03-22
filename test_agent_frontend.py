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


def test_frontend_hash_in_agent():
    test_project = Path(r"C:\IMPORTANT\NSU\3\shc\webai-tool\bet-app")
    if not test_project.exists():
        print(f"Project not found: {test_project}")
        return
    
    print("Frontend hash in agent workflow\n")
    
    state = {'frontend_hash': '', 'prjdir': str(test_project)}
    
    changed, new_hash = frontend_changed(state['prjdir'], state['frontend_hash'])
    print(f"Step 1: changed={changed}, hash={new_hash[:16] if new_hash else 'empty'}")
    
    state['frontend_hash'] = new_hash
    changed2, new_hash2 = frontend_changed(state['prjdir'], state['frontend_hash'])
    print(f"Step 2: changed={changed2}, hash={new_hash2[:16] if new_hash2 else 'empty'}")
    
    test_file = test_project / 'src' / 'App.vue'
    if test_file.exists():
        original = test_file.read_text(encoding='utf-8')
        test_file.write_text('<!-- test -->\n' + original, encoding='utf-8')
        
        changed3, new_hash3 = frontend_changed(state['prjdir'], state['frontend_hash'])
        print(f"Step 3 (modified): changed={changed3}, hash={new_hash3[:16] if new_hash3 else 'empty'}")
        
        test_file.write_text(original, encoding='utf-8')
    
    passed = changed and not changed2 and changed3
    print(f"\nPassed: {passed}")


if __name__ == "__main__":
    test_frontend_hash_in_agent()