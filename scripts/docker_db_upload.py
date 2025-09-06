#!/usr/bin/env python3
"""
Upload emails using Docker exec to PostgreSQL container
This bypasses network connection issues by running commands directly in the container
"""

import json
import subprocess
import tempfile
import logging
from pathlib import Path

class DockerDBUploader:
    def __init__(self):
        self.container_name = "local-ai-packaged-postgres-1"
        self.db_user = "postgres"
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def test_connection(self):
        """Test PostgreSQL container connection"""
        try:
            result = subprocess.run([
                'docker', 'exec', self.container_name, 
                'psql', '-U', self.db_user, '-c', 'SELECT version();'
            ], capture_output=True, text=True, check=True)
            
            self.logger.info(f"✅ PostgreSQL container is accessible")
            return True
        except Exception as e:
            self.logger.error(f"❌ Container connection failed: {e}")
            return False
    
    def create_kenny_emails_table(self):
        """Create the kenny_emails table"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS kenny_emails (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            message_id TEXT UNIQUE NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            from_address TEXT NOT NULL DEFAULT '',
            from_name TEXT DEFAULT '',
            to_addresses JSONB DEFAULT '[]',
            cc_addresses JSONB DEFAULT '[]',
            body_text TEXT NOT NULL DEFAULT '',
            date_sent TIMESTAMP WITH TIME ZONE,
            thread_id TEXT DEFAULT '',
            keywords JSONB DEFAULT '[]',
            has_attachments BOOLEAN DEFAULT FALSE,
            body_length INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_from ON kenny_emails(from_address);
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_date ON kenny_emails(date_sent);
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_thread ON kenny_emails(thread_id);
        """
        
        try:
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'psql', '-U', self.db_user, '-c', create_sql
            ], capture_output=True, text=True, check=True)
            
            self.logger.info("✅ kenny_emails table created successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error creating table: {e}")
            if hasattr(e, 'stderr'):
                self.logger.error(f"   SQL Error: {e.stderr}")
            return False
    
    def upload_emails_from_file(self, json_file_path, batch_size=100):
        """Upload emails from JSON file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                emails = json.load(f)
        except Exception as e:
            self.logger.error(f"❌ Error reading file: {e}")
            return {"uploaded": 0, "failed": 0}
        
        self.logger.info(f"📂 Loaded {len(emails)} emails to upload")
        
        uploaded_count = 0
        failed_count = 0
        
        # Process in batches
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            self.logger.info(f"📦 Processing batch {batch_num} ({len(batch)} emails)...")
            
            # Create SQL for this batch
            insert_sql = self._create_batch_insert_sql(batch)
            
            if insert_sql:
                try:
                    # Write SQL to temporary file and execute in container
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as tmp_file:
                        tmp_file.write(insert_sql)
                        tmp_file_path = tmp_file.name
                    
                    # Copy SQL file to container
                    subprocess.run([
                        'docker', 'cp', tmp_file_path, 
                        f"{self.container_name}:/tmp/batch_{batch_num}.sql"
                    ], check=True)
                    
                    # Execute SQL in container
                    result = subprocess.run([
                        'docker', 'exec', self.container_name,
                        'psql', '-U', self.db_user, '-f', f'/tmp/batch_{batch_num}.sql'
                    ], capture_output=True, text=True, check=True)
                    
                    # Clean up
                    subprocess.run([
                        'docker', 'exec', self.container_name,
                        'rm', f'/tmp/batch_{batch_num}.sql'
                    ], capture_output=True)
                    
                    Path(tmp_file_path).unlink()
                    
                    uploaded_count += len(batch)
                    self.logger.info(f"   ✅ Batch {batch_num} uploaded successfully")
                    
                except Exception as e:
                    failed_count += len(batch)
                    self.logger.error(f"   ❌ Batch {batch_num} failed: {e}")
        
        return {"uploaded": uploaded_count, "failed": failed_count}
    
    def _create_batch_insert_sql(self, emails):
        """Create SQL INSERT statements for a batch of emails"""
        if not emails:
            return ""
        
        sql_lines = []
        
        for email in emails:
            try:
                # Format email data
                message_id = self._escape_sql_string(email.get('message_id', ''))
                subject = self._escape_sql_string(email.get('subject', ''))
                from_address = self._escape_sql_string(email.get('from_address', ''))
                from_name = self._escape_sql_string(email.get('from_name', ''))
                to_addresses = json.dumps(email.get('to_addresses', []))
                cc_addresses = json.dumps(email.get('cc_addresses', []))
                body_text = self._escape_sql_string(email.get('body', ''))
                date_sent = f"'{email.get('date_sent')}'" if email.get('date_sent') else 'NULL'
                thread_id = self._escape_sql_string(email.get('thread_id', ''))
                keywords = json.dumps(email.get('keywords', []))
                has_attachments = 'TRUE' if email.get('has_attachments', False) else 'FALSE'
                body_length = email.get('body_length', len(email.get('body', '')))
                
                insert_sql = f"""
INSERT INTO kenny_emails (
    message_id, subject, from_address, from_name, to_addresses, 
    cc_addresses, body_text, date_sent, thread_id, keywords, 
    has_attachments, body_length
) VALUES (
    '{message_id}', '{subject}', '{from_address}', '{from_name}', 
    '{to_addresses}', '{cc_addresses}', '{body_text}', {date_sent}, 
    '{thread_id}', '{keywords}', {has_attachments}, {body_length}
) ON CONFLICT (message_id) DO NOTHING;
"""
                sql_lines.append(insert_sql)
                
            except Exception as e:
                self.logger.warning(f"Skipping email due to formatting error: {e}")
                continue
        
        return '\n'.join(sql_lines)
    
    def _escape_sql_string(self, s):
        """Escape SQL string to prevent injection"""
        if not s:
            return ""
        return str(s).replace("'", "''").replace('\n', '\\n').replace('\r', '\\r')
    
    def get_table_stats(self):
        """Get statistics about uploaded emails"""
        try:
            stats_sql = """
            SELECT 
                COUNT(*) as total_emails,
                MIN(date_sent) as earliest_date,
                MAX(date_sent) as latest_date
            FROM kenny_emails;
            """
            
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'psql', '-U', self.db_user, '-t', '-c', stats_sql
            ], capture_output=True, text=True, check=True)
            
            # Parse result
            output = result.stdout.strip()
            if output:
                parts = output.split('|')
                if len(parts) >= 3:
                    return {
                        'total_emails': int(parts[0].strip()),
                        'earliest_date': parts[1].strip() if parts[1].strip() else None,
                        'latest_date': parts[2].strip() if parts[2].strip() else None
                    }
            
            return {'total_emails': 0, 'earliest_date': None, 'latest_date': None}
            
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload emails using Docker exec to PostgreSQL')
    parser.add_argument('--file', '-f', required=True, help='Path to processed emails JSON file')
    parser.add_argument('--batch-size', '-b', type=int, default=50, help='Batch size for uploads')
    parser.add_argument('--create-table', '-c', action='store_true', help='Create database table first')
    parser.add_argument('--stats', '-s', action='store_true', help='Show database statistics')
    
    args = parser.parse_args()
    
    uploader = DockerDBUploader()
    
    print("🔌 Testing PostgreSQL container connection...")
    if not uploader.test_connection():
        print("❌ Could not connect to PostgreSQL container")
        print("Make sure the container 'local-ai-packaged-postgres-1' is running")
        return
    
    if args.create_table:
        print("📋 Creating kenny_emails table...")
        if not uploader.create_kenny_emails_table():
            print("❌ Failed to create table")
            return
    
    if args.file:
        print(f"📂 Starting upload from {args.file}...")
        result = uploader.upload_emails_from_file(args.file, args.batch_size)
        print(f"✅ Upload completed: {result['uploaded']} uploaded, {result['failed']} failed")
    
    if args.stats:
        print("📊 Database statistics:")
        stats = uploader.get_table_stats()
        if 'error' in stats:
            print(f"❌ Error getting stats: {stats['error']}")
        else:
            print(f"   Total emails: {stats['total_emails']}")
            if stats['earliest_date']:
                print(f"   Date range: {stats['earliest_date']} to {stats['latest_date']}")

if __name__ == "__main__":
    main()