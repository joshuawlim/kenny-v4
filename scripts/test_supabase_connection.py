#!/usr/bin/env python3
"""
Test Supabase connection and upload functionality
This script tests the Supabase upload without requiring real credentials
"""

import os
import json
from pathlib import Path

def test_supabase_import():
    """Test that Supabase can be imported"""
    try:
        from supabase import create_client, Client
        print("✅ Supabase package imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Supabase: {e}")
        return False

def check_environment_setup():
    """Check if environment variables are set up"""
    required_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY']
    
    print("\n🔍 Checking environment variables:")
    
    # Check for .env file
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found (this is optional)")
    
    # Check environment variables
    missing_vars = []
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {missing_vars}")
        print("To use Supabase upload:")
        print("1. Copy .env.example to .env")
        print("2. Fill in your Supabase URL and service key")
        print("3. Run: source .env  (or restart terminal)")
        return False
    else:
        print("✅ All environment variables are set")
        return True

def test_data_files():
    """Check if processed email data files exist"""
    print("\n📁 Checking processed email files:")
    
    data_dir = Path("data/processed")
    if not data_dir.exists():
        print("❌ data/processed directory not found")
        return False
    
    required_files = [
        "all_emails_processed.json",
        "processing_summary.json"
    ]
    
    files_found = []
    for filename in required_files:
        filepath = data_dir / filename
        if filepath.exists():
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"✅ {filename} ({size_mb:.1f} MB)")
            files_found.append(filepath)
        else:
            print(f"❌ {filename} not found")
    
    return len(files_found) > 0

def simulate_upload_process():
    """Simulate the upload process without actually connecting"""
    print("\n🔄 Simulating upload process:")
    
    # Read processed emails file
    try:
        with open("data/processed/all_emails_processed.json", 'r') as f:
            emails = json.load(f)
        
        print(f"✅ Loaded {len(emails)} emails for upload")
        
        # Simulate batch processing
        batch_size = 100
        num_batches = (len(emails) + batch_size - 1) // batch_size
        
        print(f"📦 Would process in {num_batches} batches of {batch_size} emails each")
        
        # Check sample email structure
        if emails:
            sample_email = emails[0]
            required_fields = ['message_id', 'subject', 'from_address', 'body', 'date_sent']
            
            print("📋 Sample email structure:")
            for field in required_fields:
                if field in sample_email:
                    value = sample_email[field]
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"  ✅ {field}: {value}")
                else:
                    print(f"  ❌ {field}: missing")
        
        return True
        
    except FileNotFoundError:
        print("❌ No processed emails file found")
        print("Run: python3 scripts/mail_processor.py first")
        return False
    except json.JSONDecodeError:
        print("❌ Invalid JSON in processed emails file")
        return False

def main():
    """Run all tests"""
    print("🧪 Kenny V4 - Supabase Upload Test Suite")
    print("="*50)
    
    tests = [
        ("Supabase Import", test_supabase_import),
        ("Environment Setup", check_environment_setup),
        ("Data Files", test_data_files),
        ("Upload Simulation", simulate_upload_process)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🔬 Running: {test_name}")
        results[test_name] = test_func()
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! Ready to upload to Supabase.")
        print("\nTo upload your emails:")
        print("1. Set up .env file with Supabase credentials")
        print("2. Run: python3 scripts/upload_to_supabase.py --file data/processed/all_emails_processed.json")
    else:
        env_ready = results.get("Environment Setup", False)
        if not env_ready:
            print("\n⚠️  Environment setup needed before uploading to Supabase.")
        else:
            print("\n⚠️  Some tests failed. Check the issues above.")
    
    return all_passed

if __name__ == "__main__":
    main()