import os
import shutil
import subprocess
import pathlib
import zipfile
import socket

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SUBMISSION_DIR = SCRIPT_DIR / 'self_check_submission'
EXERCISE_DIR = SUBMISSION_DIR / 'ex1'

INPUT_DIR = SCRIPT_DIR / 'tests'
EXPECTED_OUTPUT_DIR = SCRIPT_DIR / 'expected_output'
SELF_CHECK_OUTPUT_DIR = SCRIPT_DIR / 'self_check_output'
MAKEFILE_PATH = EXERCISE_DIR / 'Makefile'
IDS_FILE_PATH = SUBMISSION_DIR / 'ids.txt'
EXECUTABLE_NAME = "LEXER"

HOST_NAME = "nova"

def remove_if_exists(path_obj):
    if path_obj.is_symlink() or path_obj.is_file():
        os.remove(str(path_obj))
    elif path_obj.exists():
        shutil.rmtree(str(path_obj))


def ensure_exists(path_obj, is_file=True):
    valid = path_obj.is_file() if is_file else path_obj.is_dir()
    if not valid:
        kind = "file" if is_file else "directory"
        raise RuntimeError(f"Required {kind} missing or invalid: {path_obj}")


def unzip_single_archive():
    zip_files = [f for f in SCRIPT_DIR.glob("*.zip") if f.stem.isdigit()]
    if len(zip_files) == 0:
        raise RuntimeError("No zip archive found in the directory.")
    elif len(zip_files) > 1:
        raise RuntimeError("More than one zip archive found. Ensure only one archive is present.")
    zip_file = zip_files[0]
    ensure_exists(zip_file)
    print(f"Unzipping archive: {zip_file.name}")
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        names = zip_ref.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("The archive contains duplicate entries.")
        for name in names:
            path = pathlib.PurePosixPath(name)
            if (path.is_absolute() or ".." in path.parts or "\\" in name
                    or not path.parts
                    or (name != 'ids.txt' and path.parts[0] != EXERCISE_DIR.name)):
                raise RuntimeError(f"Invalid archive entry: {name}")
        remove_if_exists(SUBMISSION_DIR)
        zip_ref.extractall(SUBMISSION_DIR)
        print("Unzip complete.")

 
def setup_self_check():
    print("--- 1. Validating project structure ---")
    ensure_exists(MAKEFILE_PATH)
    ensure_exists(IDS_FILE_PATH)
    ensure_exists(INPUT_DIR, is_file=False)
    ensure_exists(EXPECTED_OUTPUT_DIR, is_file=False)
    print("Project structure OK.")
    print("--- 2. Running 'make' ---")
    executable_file = EXERCISE_DIR / EXECUTABLE_NAME
    remove_if_exists(executable_file)
    process = subprocess.Popen(
        ["make"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=str(EXERCISE_DIR),
        start_new_session=True
    ) 
    try:
        stdout, stderr = process.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, 9)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        print(stdout)
        print(stderr)
        raise RuntimeError("Make command timed out after 120 seconds.")
    if process.returncode != 0:
        print("--- MAKE FAILED! ---")
        print("--- STDOUT: ---")
        print(stdout)
        print("--- STDERR: ---")
        print(stderr)
        print("--------------------")
        raise RuntimeError("Make command failed. See output above.")
    
    print("--- 'make' successful ---")
    
    ensure_exists(executable_file)
    
    remove_if_exists(SELF_CHECK_OUTPUT_DIR)
    os.makedirs(str(SELF_CHECK_OUTPUT_DIR), exist_ok=True)
    
    return SELF_CHECK_OUTPUT_DIR, executable_file


def run_test(test_path, output_dir, executable_file):
    output_path = output_dir / test_path.name
    ensure_exists(test_path)
    remove_if_exists(output_path)
    
    try:
        process = subprocess.run(
            ["java", "-jar", str(executable_file.resolve()), str(test_path.resolve()), str(output_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
            cwd=str(EXERCISE_DIR)
        )
    
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timed out after 10 seconds.")

    if process.returncode != 0:
        print(process.stderr.decode(errors='replace'))
        raise RuntimeError(f"Java failed with exit status {process.returncode}.")
    ensure_exists(output_path)

    expected_output_path = EXPECTED_OUTPUT_DIR / f"{test_path.stem}_Expected_Output.txt"
    ensure_exists(expected_output_path)
        
    with open(str(output_path), 'r') as f1, open(str(expected_output_path), 'r') as f2:
        content1 = f1.read()
        content2 = f2.read()
        if content1 == content2:
            print("OK")
        else:
            raise RuntimeError(f"Output mismatch: compare {output_path} with {expected_output_path}")


def run_all_tests(output_dir, executable_file):
    print("--- 3. Running all tests ---")
    failed = []

    tests = sorted(INPUT_DIR.glob("*.txt"))
    if not tests:
        raise RuntimeError("No test files found; an empty test suite cannot pass.")
    expected_names = {f"{p.stem}_Expected_Output.txt" for p in tests}
    actual_names = {p.name for p in EXPECTED_OUTPUT_DIR.glob("*.txt")}
    if expected_names != actual_names:
        raise RuntimeError(f"Missing expected outputs: {sorted(expected_names - actual_names)}; "
                           f"expected outputs without tests: {sorted(actual_names - expected_names)}")

    for test_path in tests:
        print(f"Running {test_path.stem} ... ", end="")
        try:
            run_test(test_path, output_dir, executable_file)
        except (RuntimeError, OSError, UnicodeError) as e:
            print(f"FAILED ({e})")
            failed.append((test_path.stem, str(e)))

    print("--- 4. Test summary ---")
    total = len(tests)
    passed = total - len(failed)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failed test details:")
        for name, reason in failed:
            print(f"  {name}: {reason}")
        raise RuntimeError(f"{len(failed)} test(s) failed.")

    print("All tests passed")


def main():
    print("--- Starting Student Self-Check ---")
    
    try:
        hostname = socket.gethostname()
        if hostname not in (HOST_NAME, 'nova.cs.tau.ac.il'):
            print(f"FATAL ERROR: This script must be run on 'nova'.")
            raise RuntimeError("Invalid host machine.")
    
        unzip_single_archive()
        output_dir, executable_file = setup_self_check()
        run_all_tests(output_dir, executable_file)

    except Exception as e:
        print("--- SELF-CHECK FAILED ---")
        print(f"ERROR: {e}")
        return 1
    
    print("--- Self-Check Finished ---")
    print("All provided checks passed.")
    return 0
    
if __name__ == "__main__":
    raise SystemExit(main())
