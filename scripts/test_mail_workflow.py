#!/usr/bin/env python3
"""
Test workflow for Apple Mail export and processing pipeline
This script creates sample data to test the complete workflow
"""

import json
import email
import email.message
from datetime import datetime, timedelta
import mailbox
from pathlib import Path
import tempfile
import shutil

def create_test_mbox():
    """Create a test .mbox file with sample emails"""
    test_emails = [
        {
            'from': 'john@example.com',
            'from_name': 'John Doe',
            'to': 'user@test.com',
            'subject': 'Project Update Meeting',
            'body': 'Hi there,\n\nLet\'s schedule a meeting to discuss the project updates. I have some important points to cover.\n\nBest regards,\nJohn',
            'date': datetime.now() - timedelta(days=7)
        },
        {
            'from': 'sarah@company.com',
            'from_name': 'Sarah Smith',
            'to': 'user@test.com',
            'subject': 'Weekly Report',
            'body': 'Please find attached the weekly report. Key highlights:\n\n- Sales increased by 15%\n- New client acquisition: 3 companies\n- Upcoming deadlines: Project Alpha due next Friday\n\nLet me know if you have questions.',
            'date': datetime.now() - timedelta(days=3)
        },
        {
            'from': 'notifications@service.com',
            'from_name': 'Service Notifications',
            'to': 'user@test.com',
            'subject': 'Account Activity Summary',
            'body': 'Your account activity for this week:\n\n- 5 logins\n- 3 documents uploaded\n- 2 reports generated\n\nStay secure!',
            'date': datetime.now() - timedelta(days=1)
        }
    ]
    
    # Create temporary mbox file
    temp_dir = Path("data/mail_exports")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    mbox_path = temp_dir / "test_export.mbox"
    
    # Create mbox and add test emails
    test_mbox = mailbox.mbox(str(mbox_path))
    
    for email_data in test_emails:
        # Create email message
        msg = email.message.EmailMessage()
        msg.set_content(email_data['body'])
        msg['From'] = f"{email_data['from_name']} <{email_data['from']}>"
        msg['To'] = email_data['to']
        msg['Subject'] = email_data['subject']
        msg['Date'] = email_data['date'].strftime('%a, %d %b %Y %H:%M:%S +0000')
        msg['Message-ID'] = f"<{int(email_data['date'].timestamp())}@test.example.com>"
        
        test_mbox.add(msg)
    
    test_mbox.close()
    print(f"Created test .mbox file: {mbox_path}")
    return mbox_path

def test_processing():
    """Test the mail processing workflow"""
    print("="*60)
    print("TESTING APPLE MAIL PROCESSING WORKFLOW")
    print("="*60)
    
    # Step 1: Create test data
    print("\n1. Creating test .mbox file...")
    mbox_path = create_test_mbox()
    
    # Step 2: Test mail processor
    print("\n2. Testing mail processor...")
    try:
        from mail_processor import AppleMailProcessor
        
        processor = AppleMailProcessor("data/mail_exports", "data/processed")
        processor.process_all_mbox_files()
        
        print("✅ Mail processing completed successfully")
        
        # Check if output files exist
        output_dir = Path("data/processed")
        json_files = list(output_dir.glob("*.json"))
        
        print(f"   Generated {len(json_files)} output files:")
        for file in json_files:
            print(f"   - {file.name} ({file.stat().st_size} bytes)")
            
    except Exception as e:
        print(f"❌ Mail processing failed: {e}")
        return False
    
    # Step 3: Test validation
    print("\n3. Testing data validation...")
    try:
        from mail_validator import AppleMailValidator
        
        validator = AppleMailValidator("data/processed")
        validation_results = validator.validate_processed_emails()
        
        if validation_results.get('total_emails', 0) > 0:
            print(f"✅ Validation completed - {validation_results['total_emails']} emails validated")
            print(f"   Privacy check: {validation_results['privacy_check']['potentially_sensitive_emails']} sensitive emails detected")
        else:
            print("❌ Validation found no emails")
            return False
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False
    
    # Step 4: Test file integrity
    print("\n4. Testing file integrity...")
    try:
        processed_file = Path("data/processed/all_emails_processed.json")
        if processed_file.exists():
            with open(processed_file, 'r', encoding='utf-8') as f:
                emails = json.load(f)
            
            if len(emails) >= 3:  # We created 3 test emails
                print(f"✅ File integrity check passed - {len(emails)} emails loaded")
                
                # Check sample email structure
                sample_email = emails[0]
                required_fields = ['message_id', 'subject', 'from_address', 'body', 'date_sent']
                missing_fields = [field for field in required_fields if field not in sample_email]
                
                if not missing_fields:
                    print("✅ Email structure validation passed")
                else:
                    print(f"❌ Missing required fields: {missing_fields}")
                    return False
            else:
                print(f"❌ Expected 3 emails, found {len(emails)}")
                return False
        else:
            print("❌ Processed emails file not found")
            return False
            
    except Exception as e:
        print(f"❌ File integrity check failed: {e}")
        return False
    
    # Step 5: Display sample results
    print("\n5. Sample processed email:")
    try:
        with open("data/processed/all_emails_processed.json", 'r', encoding='utf-8') as f:
            emails = json.load(f)
        
        if emails:
            sample = emails[0]
            print(f"   Subject: {sample.get('subject', 'N/A')}")
            print(f"   From: {sample.get('from_name', 'N/A')} <{sample.get('from_address', 'N/A')}>")
            print(f"   Date: {sample.get('date_sent', 'N/A')}")
            print(f"   Body length: {sample.get('body_length', 0)} characters")
            print(f"   Keywords: {sample.get('keywords', [])}")
        
    except Exception as e:
        print(f"❌ Error displaying sample: {e}")
    
    # Step 6: Cleanup (optional)
    print("\n6. Workflow test completed successfully! ✅")
    print("\nGenerated files:")
    print("- data/mail_exports/test_export.mbox")
    print("- data/processed/all_emails_processed.json")
    print("- data/processed/processed_test_export.json")
    print("- data/processed/processing_summary.json")
    
    # Auto cleanup for automated testing
    try:
        shutil.rmtree("data/mail_exports")
        shutil.rmtree("data/processed")
        print("✅ Test files cleaned up")
    except Exception as e:
        print(f"❌ Error cleaning up: {e}")
    
    return True

def test_privacy_filtering():
    """Test privacy filtering functionality"""
    print("\n" + "="*60)
    print("TESTING PRIVACY FILTERING")
    print("="*60)
    
    # Create test emails with sensitive content
    sensitive_emails = [
        {
            'from': 'bank@example.com',
            'subject': 'Account Statement Available',
            'body': 'Your account number 123-456-789 statement is ready. Your SSN ending in 1234 is on file.'
        },
        {
            'from': 'doctor@medical.com', 
            'subject': 'Test Results',
            'body': 'Your medical test results show normal blood pressure. Please schedule follow-up.'
        },
        {
            'from': 'legal@law.com',
            'subject': 'Confidential Legal Matter',
            'body': 'This attorney-client privileged communication discusses your case.'
        }
    ]
    
    try:
        from mail_validator import AppleMailValidator
        
        # Test privacy detection on sample emails
        validator = AppleMailValidator("data/processed")
        
        test_emails = []
        for email_data in sensitive_emails:
            test_email = {
                'message_id': f'<test{len(test_emails)}@example.com>',
                'subject': email_data['subject'],
                'from_address': email_data['from'],
                'body': email_data['body'],
                'date_sent': datetime.now().isoformat()
            }
            test_emails.append(test_email)
        
        # Run privacy check
        privacy_results = validator._check_privacy_concerns(test_emails)
        
        print(f"Sensitive emails detected: {privacy_results['potentially_sensitive_emails']}")
        print(f"Sensitive categories: {list(privacy_results['sensitive_categories'].keys())}")
        print(f"Flagged senders: {privacy_results['flagged_senders']}")
        
        if privacy_results['potentially_sensitive_emails'] > 0:
            print("✅ Privacy filtering is working correctly")
            return True
        else:
            print("⚠️  Privacy filtering may need adjustment")
            return False
    
    except Exception as e:
        print(f"❌ Privacy filtering test failed: {e}")
        return False

if __name__ == "__main__":
    print("Kenny V4 - Apple Mail Export Testing Suite")
    print("This will test the complete mail processing workflow")
    
    # Run main workflow test
    main_test_passed = test_processing()
    
    # Run privacy filtering test
    privacy_test_passed = test_privacy_filtering()
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    print(f"Mail processing workflow: {'✅ PASS' if main_test_passed else '❌ FAIL'}")
    print(f"Privacy filtering test: {'✅ PASS' if privacy_test_passed else '❌ FAIL'}")
    
    if main_test_passed and privacy_test_passed:
        print("\n🎉 All tests passed! The Apple Mail export workflow is ready for use.")
        print("\nNext steps:")
        print("1. Export real mailboxes from Mail.app")
        print("2. Run: python scripts/mail_processor.py")
        print("3. Validate with: python scripts/mail_validator.py")
        print("4. Upload to Supabase with: python scripts/upload_to_supabase.py")
    else:
        print("\n⚠️  Some tests failed. Please review the error messages above.")