import json
import os
from typing import List, Dict, Optional
from pathlib import Path
import logging
from supabase import create_client, Client

class KennyEmailUploader:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def create_tables_if_not_exist(self):
        """Create the kenny_emails table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS kenny_emails (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            message_id TEXT UNIQUE NOT NULL,
            subject TEXT NOT NULL,
            from_address TEXT NOT NULL,
            from_name TEXT,
            to_addresses JSONB,
            cc_addresses JSONB,
            body_text TEXT NOT NULL,
            date_sent TIMESTAMP WITH TIME ZONE,
            thread_id TEXT,
            keywords JSONB,
            has_attachments BOOLEAN DEFAULT FALSE,
            body_length INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_from ON kenny_emails(from_address);
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_date ON kenny_emails(date_sent);
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_thread ON kenny_emails(thread_id);
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_subject ON kenny_emails USING gin(to_tsvector('english', subject));
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_body ON kenny_emails USING gin(to_tsvector('english', body_text));
        """
        
        try:
            self.supabase.postgrest.rpc('exec', {'sql': create_table_sql}).execute()
            self.logger.info("Email tables and indexes created successfully")
        except Exception as e:
            self.logger.error(f"Error creating tables: {e}")
            raise
    
    def upload_processed_emails(self, json_file_path: str, batch_size: int = 100):
        """Upload processed emails to Supabase"""
        file_path = Path(json_file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {json_file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            emails = json.load(f)
        
        if not emails:
            self.logger.warning("No emails to upload")
            return
        
        self.logger.info(f"Starting upload of {len(emails)} emails in batches of {batch_size}")
        
        # Process in batches
        uploaded_count = 0
        failed_count = 0
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            formatted_batch = []
            
            for email in batch:
                formatted_email = self._format_for_supabase(email)
                if formatted_email:
                    formatted_batch.append(formatted_email)
            
            if formatted_batch:
                try:
                    result = self.supabase.table('kenny_emails').insert(formatted_batch).execute()
                    
                    if result.data:
                        batch_uploaded = len(result.data)
                        uploaded_count += batch_uploaded
                        self.logger.info(f"Batch {i//batch_size + 1}: Uploaded {batch_uploaded} emails")
                    else:
                        failed_count += len(formatted_batch)
                        self.logger.error(f"Batch {i//batch_size + 1}: Upload failed")
                        
                except Exception as e:
                    failed_count += len(formatted_batch)
                    self.logger.error(f"Batch {i//batch_size + 1}: Error uploading - {e}")
        
        self.logger.info(f"Upload completed: {uploaded_count} successful, {failed_count} failed")
        return {"uploaded": uploaded_count, "failed": failed_count}
    
    def _format_for_supabase(self, email: Dict) -> Optional[Dict]:
        """Format email data for Supabase insertion"""
        try:
            # Basic validation
            if not email.get('message_id') or not email.get('body'):
                return None
            
            formatted = {
                'message_id': email.get('message_id', ''),
                'subject': email.get('subject', ''),
                'from_address': email.get('from_address', ''),
                'from_name': email.get('from_name', ''),
                'to_addresses': email.get('to_addresses', []),
                'cc_addresses': email.get('cc_addresses', []),
                'body_text': email.get('body', ''),
                'date_sent': email.get('date_sent'),
                'thread_id': email.get('thread_id', ''),
                'keywords': email.get('keywords', []),
                'has_attachments': email.get('has_attachments', False),
                'body_length': email.get('body_length', len(email.get('body', '')))
            }
            
            return formatted
            
        except Exception as e:
            self.logger.error(f"Error formatting email: {e}")
            return None
    
    def check_existing_emails(self, message_ids: List[str]) -> List[str]:
        """Check which message IDs already exist in the database"""
        if not message_ids:
            return []
        
        try:
            result = self.supabase.table('kenny_emails')\
                .select('message_id')\
                .in_('message_id', message_ids)\
                .execute()
            
            existing_ids = [row['message_id'] for row in result.data]
            return existing_ids
            
        except Exception as e:
            self.logger.error(f"Error checking existing emails: {e}")
            return []
    
    def upload_new_emails_only(self, json_file_path: str, batch_size: int = 100):
        """Upload only emails that don't already exist in the database"""
        with open(json_file_path, 'r', encoding='utf-8') as f:
            emails = json.load(f)
        
        # Get all message IDs
        message_ids = [email.get('message_id') for email in emails if email.get('message_id')]
        
        # Check which ones already exist
        existing_ids = self.check_existing_emails(message_ids)
        existing_set = set(existing_ids)
        
        # Filter out existing emails
        new_emails = [email for email in emails 
                     if email.get('message_id') not in existing_set]
        
        self.logger.info(f"Found {len(existing_ids)} existing emails, {len(new_emails)} new emails to upload")
        
        if new_emails:
            # Create temporary file with new emails only
            temp_file = Path(json_file_path).parent / "temp_new_emails.json"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(new_emails, f, indent=2)
            
            # Upload new emails
            result = self.upload_processed_emails(str(temp_file), batch_size)
            
            # Clean up temp file
            temp_file.unlink()
            
            return result
        else:
            self.logger.info("No new emails to upload")
            return {"uploaded": 0, "failed": 0}
    
    def get_database_stats(self) -> Dict:
        """Get statistics about emails in the database"""
        try:
            # Get total count
            count_result = self.supabase.table('kenny_emails')\
                .select('id', count='exact')\
                .execute()
            total_emails = count_result.count
            
            # Get date range
            date_result = self.supabase.table('kenny_emails')\
                .select('date_sent')\
                .order('date_sent')\
                .limit(1)\
                .execute()
            
            latest_result = self.supabase.table('kenny_emails')\
                .select('date_sent')\
                .order('date_sent', desc=True)\
                .limit(1)\
                .execute()
            
            earliest_date = date_result.data[0]['date_sent'] if date_result.data else None
            latest_date = latest_result.data[0]['date_sent'] if latest_result.data else None
            
            # Get top senders
            # Note: This would need to be implemented with proper SQL aggregation
            
            stats = {
                'total_emails': total_emails,
                'earliest_email': earliest_date,
                'latest_email': latest_date,
                'database_ready': total_emails > 0
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {'error': str(e)}

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload processed emails to Kenny\'s Supabase database')
    parser.add_argument('--file', '-f', required=True, help='Path to processed emails JSON file')
    parser.add_argument('--batch-size', '-b', type=int, default=100, help='Batch size for uploads')
    parser.add_argument('--new-only', '-n', action='store_true', help='Upload only new emails (skip duplicates)')
    parser.add_argument('--stats', '-s', action='store_true', help='Show database statistics')
    parser.add_argument('--create-tables', '-c', action='store_true', help='Create database tables if they don\'t exist')
    
    args = parser.parse_args()
    
    try:
        uploader = KennyEmailUploader()
        
        if args.create_tables:
            uploader.create_tables_if_not_exist()
        
        if args.stats:
            stats = uploader.get_database_stats()
            print(f"Database Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        if args.file:
            if args.new_only:
                result = uploader.upload_new_emails_only(args.file, args.batch_size)
            else:
                result = uploader.upload_processed_emails(args.file, args.batch_size)
            
            print(f"Upload Results: {result['uploaded']} uploaded, {result['failed']} failed")
    
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()