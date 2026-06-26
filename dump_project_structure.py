import os
import sys
import argparse

def count_lines(filepath, max_size_bytes=1024*1024):
    try:
        size = os.path.getsize(filepath)
        if size > max_size_bytes:
            return -2 # Marker untuk file terlalu besar
            
        # Periksa apakah binary dengan membaca 1024 byte pertama
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return -1 # Marker binary
        
        # Hitung jumlah baris dengan cepat
        count = 0
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for _ in f:
                count += 1
        return count
    except Exception:
        return 0

def print_tree(dir_path, prefix="", ignore_dirs=None, ignore_exts=None, include_data=False, max_size_bytes=1024*1024):
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__', 'venv', '.venv', '.gemini', 'node_modules', '.idea', '.vscode'}
    if not include_data:
        ignore_dirs.add('data')
        
    if ignore_exts is None:
        ignore_exts = {
            '.db', '.db-journal', '.db-wal', '.mitm', '.png', '.jpg', '.jpeg', 
            '.gif', '.ico', '.pdf', '.zip', '.gz', '.tar', '.exe', '.dll', 
            '.bin', '.asar', '.log', '.jsonl', '.json', '.pyc', '.pyo'
        }
        
    try:
        raw_entries = sorted(os.listdir(dir_path))
    except Exception as e:
        print(f"{prefix}\\-- [Error membaca folder: {e}]")
        return []
        
    # Saring folder dan file yang tidak relevan dengan refactoring
    entries = []
    for entry in raw_entries:
        path = os.path.join(dir_path, entry)
        if os.path.isdir(path):
            if entry not in ignore_dirs:
                entries.append(entry)
        else:
            ext = os.path.splitext(entry)[1].lower()
            if ext not in ignore_exts:
                # Lewati file log dan file data lainnya
                entries.append(entry)
    
    all_files = []
    
    for i, entry in enumerate(entries):
        path = os.path.join(dir_path, entry)
        is_last = (i == len(entries) - 1)
        connector = "\\-- " if is_last else "|-- "
        
        if os.path.isdir(path):
            print(f"{prefix}{connector}{entry}/")
            sub_files = print_tree(
                path, 
                prefix + ("    " if is_last else "|   "), 
                ignore_dirs, 
                ignore_exts, 
                include_data, 
                max_size_bytes
            )
            all_files.extend(sub_files)
        else:
            line_count = count_lines(path, max_size_bytes)
            if line_count == -1:
                # Do not show binary files at all if we want code refactoring only
                continue
            elif line_count == -2:
                line_str = f"(file >{max_size_bytes//1024}KB, lewati)"
            else:
                line_str = f"({line_count} baris)"
                all_files.append((path, line_count))
                
            print(f"{prefix}{connector}{entry} {line_str}")
            
    return all_files

def main():
    parser = argparse.ArgumentParser(description="Dump project folder tree structure with file line counts.")
    parser.add_argument("--include-data", action="store_true", help="Sertakan folder 'data' (dilewati secara default karena banyak data mentah jsonl)")
    parser.add_argument("--max-size", type=int, default=1000, help="Batas ukuran file maksimal dalam KB untuk dihitung barisnya (default: 1000 KB)")
    args = parser.parse_args()
    
    root_dir = "."
    abs_root = os.path.abspath(root_dir)
    print("=" * 80)
    print(f" DUMP STRUKTUR FOLDER & JUMLAH BARIS FILE")
    print(f" Root Folder: {abs_root}")
    print("=" * 80)
    
    print(os.path.basename(abs_root) + "/")
    
    max_bytes = args.max_size * 1024
    
    # Jalankan penelusuran pohon folder
    all_files = print_tree(
        root_dir, 
        prefix="", 
        include_data=args.include_data, 
        max_size_bytes=max_bytes
    )
    
    # Saring file non-binary dan urutkan berdasarkan jumlah baris menurun
    text_files = [(path, count) for path, count in all_files if count >= 0]
    text_files.sort(key=lambda x: x[1], reverse=True)
    
    print("\n" + "=" * 80)
    print(f" 5 FILE TERBESAR DENGAN BARIS TERBANYAK")
    print("=" * 80)
    for i, (path, count) in enumerate(text_files[:5]):
        rel_path = os.path.relpath(path, root_dir)
        print(f" [{i+1}] {rel_path} : {count:,} baris")
    print("=" * 80)

if __name__ == "__main__":
    main()
