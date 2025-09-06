#!/usr/bin/env python3
"""
Direct PostgreSQL database upload for Kenny emails
This bypasses Supabase client and connects directly to PostgreSQL
"""

import json
import psycopg2
from psycopg2.extras import execute_values
import os
from pathlib import Path
import logging

class DirectDBUploader:
    def __init__(self):
        # Try multiple connection methods for local PostgreSQL
        self.connection_attempts = [
            {
                'host': 'localhost',
                'port': 54322,  # Default Supabase PostgreSQL port
                'database': 'postgres',
                'user': 'postgres',
                'password': 'ed45705e7bca7b4540dd6c1e8ed76677dbadbedaccbbd97b0771fddb6749e17b'
            },
            {
                'host': 'localhost',
                'port': 5432,  # Standard PostgreSQL port
                'database': 'postgres',
                'user': 'postgres',
                'password': 'ed45705e7bca7b4540dd6c1e8ed76677dbadbedaccbbd97b0771fddb6749e17b'
            }
        ]
        self.db_config = None
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def test_connection(self):
        """Test database connection"""
        for i, config in enumerate(self.connection_attempts):
            try:
                self.logger.info(f"Attempting connection {i+1}: {config['host']}:{config['port']}")
                conn = psycopg2.connect(**config)
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()[0]
                    self.logger.info(f"✅ Connected to PostgreSQL: {version}")
                conn.close()
                self.db_config = config  # Store successful config
                return True
            except Exception as e:
                self.logger.warning(f"❌ Connection {i+1} failed: {e}")
                continue
        
        self.logger.error("❌ All connection attempts failed")
        return False
    
    def create_kenny_emails_table(self):
        """Create the kenny_emails table with proper schema"""
        create_table_sql = """
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
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_from ON kenny_emails(from_address);
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_date ON kenny_emails(date_sent);
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_thread ON kenny_emails(thread_id);
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_subject_gin ON kenny_emails USING gin(to_tsvector('english', subject));
        CREATE INDEX IF NOT EXISTS idx_kenny_emails_body_gin ON kenny_emails USING gin(to_tsvector('english', body_text));
        """
        
        try:
            conn = psycopg2.connect(**self.db_config)
            with conn.cursor() as cursor:
                cursor.execute(create_table_sql)
                conn.commit()
                self.logger.info("✅ kenny_emails table and indexes created successfully")
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"❌ Error creating table: {e}")
            return False
    
    def upload_emails_batch(self, emails, batch_size=100):
        """Upload emails in batches"""
        if not emails:
            self.logger.warning("No emails to upload")
            return {"uploaded": 0, "failed": 0}
        
        uploaded_count = 0
        failed_count = 0
        
        try:
            conn = psycopg2.connect(**self.db_config)
            
            # Insert query
            insert_sql = """
                INSERT INTO kenny_emails (
                    message_id, subject, from_address, from_name, to_addresses, 
                    cc_addresses, body_text, date_sent, thread_id, keywords, 
                    has_attachments, body_length
                ) VALUES %s
                ON CONFLICT (message_id) DO NOTHING;
            """
            
            # Process in batches
            for i in range(0, len(emails), batch_size):
                batch = emails[i:i + batch_size]
                
                # Format data for insertion
                batch_data = []
                for email in batch:
                    formatted = self._format_email_for_db(email)
                    if formatted:
                        batch_data.append((
                            formatted['message_id'],
                            formatted['subject'],
                            formatted['from_address'],
                            formatted['from_name'],
                            json.dumps(formatted['to_addresses']),
                            json.dumps(formatted['cc_addresses']),
                            formatted['body_text'],
                            formatted['date_sent'],
                            formatted['thread_id'],
                            json.dumps(formatted['keywords']),
                            formatted['has_attachments'],
                            formatted['body_length']
                        ))
                
                if batch_data:
                    try:
                        with conn.cursor() as cursor:
                            execute_values(cursor, insert_sql, batch_data, template=None, page_size=batch_size)
                            conn.commit()
                            batch_uploaded = len(batch_data)
                            uploaded_count += batch_uploaded
                            self.logger.info(f"✅ Batch {i//batch_size + 1}: Uploaded {batch_uploaded} emails")
                    except Exception as e:
                        failed_count += len(batch_data)
                        self.logger.error(f"❌ Batch {i//batch_size + 1}: Error - {e}")
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"❌ Database connection error: {e}")
            failed_count = len(emails)
        
        return {"uploaded": uploaded_count, "failed": failed_count}
    
    def _format_email_for_db(self, email):
        """Format email data for database insertion"""
        try:
            return {
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
        except Exception as e:
            self.logger.error(f"Error formatting email: {e}")
            return None
    
    def get_table_stats(self):
        """Get statistics about uploaded emails"""
        try:
            conn = psycopg2.connect(**self.db_config)
            with conn.cursor() as cursor:
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM kenny_emails;")
                total_count = cursor.fetchone()[0]
                
                # Get date range
                cursor.execute("""
                    SELECT MIN(date_sent), MAX(date_sent) 
                    FROM kenny_emails 
                    WHERE date_sent IS NOT NULL;
                """)
                date_range = cursor.fetchone()
                
                # Get top senders
                cursor.execute("""
                    SELECT from_address, COUNT(*) as email_count 
                    FROM kenny_emails 
                    GROUP BY from_address 
                    ORDER BY email_count DESC 
                    LIMIT 5;
                """)
                top_senders = cursor.fetchall()
                
                stats = {
                    'total_emails': total_count,
                    'date_range': {
                        'earliest': str(date_range[0]) if date_range[0] else None,
                        'latest': str(date_range[1]) if date_range[1] else None
                    },
                    'top_senders': [{'email': sender[0], 'count': sender[1]} for sender in top_senders]
                }
                
            conn.close()
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload emails directly to Kenny PostgreSQL database')
    parser.add_argument('--file', '-f', required=True, help='Path to processed emails JSON file')
    parser.add_argument('--batch-size', '-b', type=int, default=100, help='Batch size for uploads')
    parser.add_argument('--create-table', '-c', action='store_true', help='Create database table first')
    parser.add_argument('--stats', '-s', action='store_true', help='Show database statistics')
    
    args = parser.parse_args()
    
    uploader = DirectDBUploader()
    
    print("🔌 Testing database connection...")
    if not uploader.test_connection():
        print("❌ Could not connect to database. Is local Supabase running?")
        print("Try: cd local-ai-packaged && docker compose up -d")
        return
    
    if args.create_table:
        print("📋 Creating kenny_emails table...")
        if not uploader.create_kenny_emails_table():
            print("❌ Failed to create table")
            return
    
    if args.file:
        print(f"📂 Loading emails from {args.file}...")
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                emails = json.load(f)
            
            print(f"📊 Found {len(emails)} emails to upload")
            print("⬆️  Starting upload...")
            
            result = uploader.upload_emails_batch(emails, args.batch_size)
            
            print(f"✅ Upload completed: {result['uploaded']} uploaded, {result['failed']} failed")
            
        except Exception as e:
            print(f"❌ Error processing file: {e}")
    
    if args.stats:
        print("📊 Database statistics:")
        stats = uploader.get_table_stats()
        if 'error' in stats:
            print(f"❌ Error getting stats: {stats['error']}")
        else:
            print(f"   Total emails: {stats['total_emails']}")
            if stats['date_range']['earliest']:
                print(f"   Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
            print("   Top senders:")
            for sender in stats['top_senders']:
                print(f"     {sender['email']}: {sender['count']} emails")

if __name__ == "__main__":
    main()