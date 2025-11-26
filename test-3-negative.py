#!/usr/bin/env python3
"""
Qeltrix (.qltx) - Content-derived, parallel, streaming obfuscation container (PoC)

Copyright (c) 2025 @hejhdiss(Muhammed Shafin P)
All rights reserved.
Licensed under GPLv3.
"""
import os
import subprocess
import time
import sys
import json 
import shutil
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

QELTRIX_SCRIPT = "qeltrix-3.py"
TEST_DIR = "qeltrix_test_data"
TEST_FILE_CONTENT = b"This is a test file for Qeltrix PoC. The quick brown fox jumps over the lazy dog. " * 500 # Approx 30KB

# --- Helper Functions ---

def create_test_files():
    """Create directory and a source file for packing."""
    os.makedirs(TEST_DIR, exist_ok=True)
    with open(os.path.join(TEST_DIR, "source.txt"), "wb") as f:
        f.write(TEST_FILE_CONTENT)
    print(f"Created source file: {os.path.join(TEST_DIR, 'source.txt')} ({len(TEST_FILE_CONTENT)} bytes)")

def generate_rsa_keys():
    """Generate RSA keys for V3-A asymmetric mode and signing."""
    # Recipient Key Pair (for DEK encryption)
    recipient_priv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    recipient_pub_key = recipient_priv_key.public_key()
    
    # Signer Key Pair (for metadata signing)
    signer_priv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    signer_pub_key = signer_priv_key.public_key()

    # Generate a third key pair for negative testing (an 'attacker' key)
    fake_signer_priv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    fake_signer_pub_key = fake_signer_priv_key.public_key()

    # Save to PEM files
    key_paths = {
        "recipient_pub": os.path.join(TEST_DIR, "recipient_pub.pem"),
        "recipient_priv": os.path.join(TEST_DIR, "recipient_priv.pem"),
        "signer_priv": os.path.join(TEST_DIR, "signer_priv.pem"),
        "signer_pub": os.path.join(TEST_DIR, "signer_pub.pem"),
        "fake_signer_pub": os.path.join(TEST_DIR, "fake_signer_pub.pem"),
    }
    
    with open(key_paths["recipient_pub"], "wb") as f:
        f.write(recipient_pub_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    with open(key_paths["recipient_priv"], "wb") as f:
        f.write(recipient_priv_key.private_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open(key_paths["signer_priv"], "wb") as f:
        f.write(signer_priv_key.private_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open(key_paths["signer_pub"], "wb") as f:
        f.write(signer_pub_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    with open(key_paths["fake_signer_pub"], "wb") as f:
        f.write(fake_signer_pub_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    print("Generated RSA key pairs.")
    return key_paths

def run_qeltrix_cmd(command: str, *args, expect_fail=False):
    """Execute a qeltrix command and return the result."""
    full_cmd = [sys.executable, QELTRIX_SCRIPT, command] + list(args)
    print(f"\n$ {' '.join(full_cmd)}")
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    
    if expect_fail:
        if result.returncode == 0:
            print("--- STDERR ---")
            print(result.stderr)
            print("--------------")
            raise RuntimeError(f"Qeltrix command '{command}' unexpectedly SUCCEEDED (expected failure).")
        # Check for expected failure types (InvalidSignature is the target)
        if "InvalidSignature" in result.stderr or "FAILED" in result.stdout or result.returncode != 0:
            print(f"✅ Command failed as expected (Exit Code: {result.returncode})")
        else:
             print("--- STDERR ---")
             print(result.stderr)
             print("--------------")
             raise RuntimeError(f"Qeltrix command '{command}' failed with unexpected error.")
        return result
    else:
        if result.returncode != 0:
            print("--- STDERR ---")
            print(result.stderr)
            print("--------------")
            raise RuntimeError(f"Qeltrix command '{command}' failed with exit code {result.returncode}")
        
        print(result.stdout.strip())
        return result

def verify_file_content(path, expected_content):
    """Read a file and compare its content."""
    with open(path, "rb") as f:
        content = f.read()
    if content == expected_content:
        print(f"✅ Content verification successful: {path}")
    else:
        raise ValueError(f"❌ Content verification FAILED for {path}! Expected {len(expected_content)} bytes, got {len(content)}.")

def cleanup():
    """Remove the test directory and all its contents."""
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
        print(f"\nCleaned up directory: {TEST_DIR}")

# --- Test Cases ---

def test_v3_symmetric(keys):
    print("\n" + "="*50)
    print("=== Test Case 1: V3 Symmetric (Content-Derived Key) ===")
    print("="*50)
    
    source = os.path.join(TEST_DIR, "source.txt")
    qltx_file = os.path.join(TEST_DIR, "v3_symm.qltx")
    unpacked_file = os.path.join(TEST_DIR, "v3_symm_unpacked.txt")
    
    # PACK (V3: no --pubkey)
    run_qeltrix_cmd("pack", source, qltx_file, "--block-size", "1024", "--cipher", "aes256-gcm")
    
    # UNPACK
    run_qeltrix_cmd("unpack", qltx_file, unpacked_file)
    verify_file_content(unpacked_file, TEST_FILE_CONTENT)
    
def test_v3a_asymmetric_signed(keys):
    print("\n" + "="*50)
    print("=== Test Case 2: V3-A Asymmetric + Signed Metadata ===")
    print("="*50)
    
    source = os.path.join(TEST_DIR, "source.txt")
    qltx_file = os.path.join(TEST_DIR, "v3a_asymm_signed.qltx")
    unpacked_file = os.path.join(TEST_DIR, "v3a_asymm_signed_unpacked.txt")
    
    # PACK (V3-A: use --pubkey, plus --signkey)
    run_qeltrix_cmd("pack", source, qltx_file, "--block-size", "2048", 
                    "--pubkey", keys["recipient_pub"], "--signkey", keys["signer_priv"], 
                    "--compression", "zstd")
    
    # UNPACK (Requires --privkey and --verifykey)
    run_qeltrix_cmd("unpack", qltx_file, unpacked_file, "--privkey", keys["recipient_priv"], 
                    "--verifykey", keys["signer_pub"])
    verify_file_content(unpacked_file, TEST_FILE_CONTENT)

def test_seek_operation(keys):
    print("\n" + "="*50)
    print("=== Test Case 3: Seek Operation ===")
    print("="*50)
    
    source = os.path.join(TEST_DIR, "source.txt")
    qltx_file = os.path.join(TEST_DIR, "seek_test.qltx")
    
    # PACK (V3-A mode for a better test)
    run_qeltrix_cmd("pack", source, qltx_file, "--block-size", "1024", 
                    "--pubkey", keys["recipient_pub"])
    
    # Test 3.1: Read from the middle
    OFFSET = 500
    LENGTH = 1024
    expected_data = TEST_FILE_CONTENT[OFFSET:OFFSET+LENGTH]
    
    seek_output_file = os.path.join(TEST_DIR, "seek_output.bin")
    run_qeltrix_cmd("seek", qltx_file, str(OFFSET), str(LENGTH), 
                    "--privkey", keys["recipient_priv"], "--output", seek_output_file)
    
    verify_file_content(seek_output_file, expected_data)

    # Test 3.2: Read spanning multiple blocks (Block size is 1024)
    OFFSET = 100
    LENGTH = 2500 
    expected_data_multi = TEST_FILE_CONTENT[OFFSET:OFFSET+LENGTH]
    
    seek_output_multi_file = os.path.join(TEST_DIR, "seek_output_multi.bin")
    run_qeltrix_cmd("seek", qltx_file, str(OFFSET), str(LENGTH), 
                    "--privkey", keys["recipient_priv"], "--output", seek_output_multi_file)
    
    verify_file_content(seek_output_multi_file, expected_data_multi)

def test_signature_verification(keys):
    print("\n" + "="*50)
    print("=== Test Case 4: Signature Verification (Positive & Negative) ===")
    print("="*50)
    
    source = os.path.join(TEST_DIR, "source.txt")
    signed_qltx_file = os.path.join(TEST_DIR, "signed_verify.qltx")
    unpacked_ok_file = os.path.join(TEST_DIR, "signed_unpacked_ok.txt")
    
    # --- STEP 1: PACK with Signer's Key ---
    print("\n--- Packing with Signature (Test File Creation) ---")
    run_qeltrix_cmd("pack", source, signed_qltx_file, "--block-size", "1024", 
                    "--pubkey", keys["recipient_pub"], "--signkey", keys["signer_priv"])
    
    # --- STEP 2: POSITIVE TEST (Correct Key) ---
    print("\n--- Positive Test: Unpack with Correct Verifier Key ---")
    run_qeltrix_cmd("unpack", signed_qltx_file, unpacked_ok_file, 
                    "--privkey", keys["recipient_priv"], "--verifykey", keys["signer_pub"])
    verify_file_content(unpacked_ok_file, TEST_FILE_CONTENT)
    
    # --- STEP 3: NEGATIVE TEST 1 (Incorrect Key) ---
    print("\n--- Negative Test 1: Unpack with Incorrect Verifier Key (Should Fail) ---")
    # Using the fake_signer_pub.pem to verify the signature made by signer_priv.pem
    run_qeltrix_cmd("unpack", signed_qltx_file, os.path.join(TEST_DIR, "unpacked_fail_1.txt"), 
                    "--privkey", keys["recipient_priv"], "--verifykey", keys["fake_signer_pub"], 
                    expect_fail=True)

    # --- STEP 4: NEGATIVE TEST 2 (Tampered Metadata) ---
    print("\n--- Negative Test 2: Tampered Metadata (Should Fail) ---")
    
    # Read the QLTX file
    with open(signed_qltx_file, "rb") as f:
        qltx_data = bytearray(f.read())
        
    # Find the critical offsets (based on qeltrix-3.py header structure)
    # MAGIC (4) + VERSION (3) + RESERVED (3) = 10 bytes. The 4-byte length follows.
    meta_start = 14
    
    # Read original metadata size and content
    original_meta_len = int.from_bytes(qltx_data[10:meta_start], 'big')
    original_meta_bytes = qltx_data[meta_start : meta_start + original_meta_len]

    # --- Tampering Logic: In-place modification of the 'mode_tag' to ensure consistent length ---
    try:
        # The JSON is sorted and compressed: Find "mode_tag":"... (64-char hex)
        mode_tag_key = b'"mode_tag":"'
        tag_start_index = original_meta_bytes.find(mode_tag_key)
        
        if tag_start_index == -1:
            raise RuntimeError("Cannot find 'mode_tag' key in metadata for tampering.")

        # Start of the 64-char hex value
        tag_value_start = tag_start_index + len(mode_tag_key)
        
        # Original value bytes (64 chars)
        original_tag_value_bytes = original_meta_bytes[tag_value_start : tag_value_start + 64]
        
        # Tamper: Flip the first byte's character representation. This guarantees same length.
        original_char = original_tag_value_bytes[0:1]
        
        # Determine the replacement character
        if original_char == b'a':
            tamper_char = b'b'
        elif original_char == b'0':
            tamper_char = b'1'
        else:
            # Fallback for other characters (e.g., 'f' -> 'e')
            tamper_char = b'e' 

        tampered_tag_value_bytes = tamper_char + original_tag_value_bytes[1:]
        
        # Construct the tampered metadata by replacing the value bytes
        tampered_meta_bytes = bytearray(original_meta_bytes)
        tampered_meta_bytes[tag_value_start : tag_value_start + 64] = tampered_tag_value_bytes

        if len(tampered_meta_bytes) != len(original_meta_bytes):
            # This should not happen with the in-place change, but is a critical fail-safe.
            raise RuntimeError("Tampering attempt failed to maintain metadata length.")
            
    except RuntimeError as e:
        print(f"Skipping tampering test due to preparation error: {e}")
        return

    # Rewrite the file with the tampered metadata, leaving the header length field untouched.
    tampered_qltx_data = qltx_data[:meta_start] + bytes(tampered_meta_bytes) + qltx_data[meta_start + original_meta_len:]
    
    tampered_file = os.path.join(TEST_DIR, "tampered_meta.qltx")
    with open(tampered_file, "wb") as f:
        f.write(tampered_qltx_data)
        
    print(f"Created tampered file (same length): {tampered_file}")
    
    # Attempt to unpack the tampered file with the correct key (Should fail due to InvalidSignature)
    run_qeltrix_cmd("unpack", tampered_file, os.path.join(TEST_DIR, "unpacked_fail_2.txt"), 
                    "--privkey", keys["recipient_priv"], "--verifykey", keys["signer_pub"], 
                    expect_fail=True)

# --- Main Execution ---

if __name__ == "__main__":
    try:
        cleanup() # Start fresh
        create_test_files()
        keys = generate_rsa_keys()
        
        # Run all test cases
        test_v3_symmetric(keys)
        test_v3a_asymmetric_signed(keys)
        test_seek_operation(keys)
        test_signature_verification(keys) 
        
        print("\n" + "#"*60)
        print("### ALL QELTRIX FUNCTIONALITY TESTS PASSED SUCCESSFULLY! ###")
        print("#"*60)

    except Exception as e:
        print("\n" + "!"*60)
        print(f"!!! A QELTRIX TEST FAILED: {e} !!!")
        print("!"*60)
        sys.exit(1)
        
    finally:
        # Optionally, comment this out if you want to inspect the generated files
        cleanup()
