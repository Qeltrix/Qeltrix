#!/usr/bin/env python3
"""
Qeltrix (.qltx) V4 Test Script

Tests pack, unpack, and seek functionality of qeltrix-4.py
using both 'two_pass' and 'single_pass_firstN' modes.

Copyright (c) 2025 @hejhdiss(Muhammed Shafin P)
All rights reserved.
Licensed under GPLv3.
"""
import os
import subprocess
import sys
import shutil
import hashlib

# --- Configuration ---
QELTRIX_SCRIPT = "qeltrix-4.py" # Target the new V4 script
TEST_DIR = "qeltrix_v4_test_data"
# Generate a larger test file content for robust testing
TEST_FILE_CONTENT = b"This is the official test file content for Qeltrix V4 (AES256-GCM). Verification requires passing multiple integrity checks for parallel operations and seeking. " * 500
# Total size will be 500 * 163 bytes = 81500 bytes (approx 80 KB)
TEST_HEAD_BYTES = 5 * 1024 # 5 KB head for single_pass_firstN test

# --- Helper Functions ---

def create_test_files():
    """Creates the necessary test directory and source file."""
    os.makedirs(TEST_DIR, exist_ok=True)
    source_path = os.path.join(TEST_DIR, "source.txt")
    with open(source_path, "wb") as f:
        f.write(TEST_FILE_CONTENT)
    print(f"Created source file: {source_path} ({len(TEST_FILE_CONTENT)} bytes)")
    return source_path

def cleanup_test_dir():
    """Removes the temporary test directory."""
    if os.path.exists(TEST_DIR):
        print(f"Cleaning up {TEST_DIR}...")
        shutil.rmtree(TEST_DIR)

def run_qeltrix_cmd(command: str, *args, check=True):
    """Executes the qeltrix script command."""
    full_cmd = [sys.executable, QELTRIX_SCRIPT, command] + list(args)
    print(f"\n$ {' '.join(full_cmd)}")
    result = subprocess.run(full_cmd, capture_output=True, text=True, check=check)
    print(result.stdout.strip())
    if result.stderr:
        print("--- STDERR ---")
        print(result.stderr.strip())
        print("--------------")
    return result

def verify_file_content(filepath: str, expected_content: bytes):
    """Compares the content of a file with expected bytes."""
    with open(filepath, "rb") as f:
        actual_content = f.read()
    
    if actual_content == expected_content:
        print(f"[VERIFY SUCCESS] Content of {filepath} matches expected data.")
    else:
        # For debugging, print a hash comparison
        expected_hash = hashlib.sha256(expected_content).hexdigest()
        actual_hash = hashlib.sha256(actual_content).hexdigest()
        
        raise AssertionError(
            f"[VERIFY FAILURE] Content mismatch in {filepath}.\n"
            f"  Expected size: {len(expected_content)}, Actual size: {len(actual_content)}\n"
            f"  Expected hash: {expected_hash}\n"
            f"  Actual hash:   {actual_hash}\n"
        )
        
# --- Test Cases ---

def test_v4_two_pass_cycle(source_path):
    """Tests pack/unpack cycle using two_pass mode."""
    print("\n" + "="*50)
    print("=== Test Case 1: V4 Two-Pass Pack/Unpack Cycle (LZ4) ===")
    print("="*50)
    
    qltx_file = os.path.join(TEST_DIR, "v4_two_pass.qltx")
    unpacked_file = os.path.join(TEST_DIR, "v4_two_pass_unpacked.txt")
    
    # PACK (key derived from full compressed stream)
    run_qeltrix_cmd("pack", source_path, qltx_file, "--compression", "lz4", "--block-size", "8192")
    
    # UNPACK
    run_qeltrix_cmd("unpack", qltx_file, unpacked_file)
    verify_file_content(unpacked_file, TEST_FILE_CONTENT)

def test_v4_single_pass_cycle_zstd(source_path):
    """Tests pack/unpack cycle using single_pass_firstN mode with Zstd."""
    print("\n" + "="*50)
    print("=== Test Case 2: V4 Single-Pass Pack/Unpack Cycle (ZSTD) ===")
    print("="*50)
    
    qltx_file = os.path.join(TEST_DIR, "v4_single_pass_zstd.qltx")
    unpacked_file = os.path.join(TEST_DIR, "v4_single_pass_zstd_unpacked.txt")
    
    # PACK (key derived from content head)
    run_qeltrix_cmd("pack", source_path, qltx_file, "--mode", "single_pass_firstN", 
                    "--head-bytes", str(TEST_HEAD_BYTES), "--compression", "zstd")
    
    # UNPACK 
    run_qeltrix_cmd("unpack", qltx_file, unpacked_file)
    verify_file_content(unpacked_file, TEST_FILE_CONTENT)

def test_v4_seek_operation(source_path):
    """Tests the seek operation for random access."""
    print("\n" + "="*50)
    print("=== Test Case 3: V4 Seek Operation ===")
    print("="*50)
    
    qltx_file = os.path.join(TEST_DIR, "v4_seek_test.qltx")
    
    # PACK using two_pass mode for simplicity
    run_qeltrix_cmd("pack", source_path, qltx_file, "--block-size", "10240")
    
    # Test 1: Seek a large chunk in the middle
    OFFSET_1 = 15000
    LENGTH_1 = 20000 
    expected_data_1 = TEST_FILE_CONTENT[OFFSET_1:OFFSET_1+LENGTH_1]
    
    seek_output_file_1 = os.path.join(TEST_DIR, "v4_seek_output_1.bin")
    run_qeltrix_cmd("seek", qltx_file, str(OFFSET_1), str(LENGTH_1), "--output", seek_output_file_1)
    verify_file_content(seek_output_file_1, expected_data_1)
    
    # Test 2: Seek from the end (should return a short chunk)
    OFFSET_2 = len(TEST_FILE_CONTENT) - 100
    LENGTH_2 = 500
    expected_data_2 = TEST_FILE_CONTENT[OFFSET_2:OFFSET_2+LENGTH_2] # Clamped by slicing
    
    seek_output_file_2 = os.path.join(TEST_DIR, "v4_seek_output_2.bin")
    run_qeltrix_cmd("seek", qltx_file, str(OFFSET_2), str(LENGTH_2), "--output", seek_output_file_2)
    verify_file_content(seek_output_file_2, expected_data_2)
    
    # Test 3: Seek a boundary-crossing chunk (e.g., block size is 10240)
    # Start at 9000 (near end of block 0) and read 3000 bytes (crossing into block 1)
    OFFSET_3 = 9000
    LENGTH_3 = 3000
    expected_data_3 = TEST_FILE_CONTENT[OFFSET_3:OFFSET_3+LENGTH_3]
    
    seek_output_file_3 = os.path.join(TEST_DIR, "v4_seek_output_3.bin")
    run_qeltrix_cmd("seek", qltx_file, str(OFFSET_3), str(LENGTH_3), "--output", seek_output_file_3)
    verify_file_content(seek_output_file_3, expected_data_3)


# --- Main Execution ---

if __name__ == "__main__":
    try:
        if not os.path.exists(QELTRIX_SCRIPT):
            print(f"Error: Required script '{QELTRIX_SCRIPT}' not found. Please ensure it is in the current directory.")
            sys.exit(1)
            
        source_file = create_test_files()
        
        test_v4_two_pass_cycle(source_file)
        test_v4_single_pass_cycle_zstd(source_file)
        test_v4_seek_operation(source_file)
        
        print("\n\n*** ALL QELTRIX V4 TESTS COMPLETED SUCCESSFULLY! ***")
        
    except ImportError as e:
        print(f"\n\n*** TEST FAILED DUE TO MISSING LIBRARY: {e} ***")
        print("Please ensure all required libraries (lz4 and zstandard) are installed.")
        sys.exit(1)
    except AssertionError as e:
        print(f"\n\n*** TEST FAILED: {e} ***")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n*** AN UNEXPECTED ERROR OCCURRED: {e} ***")
        sys.exit(1)
    finally:
        cleanup_test_dir()
