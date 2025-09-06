import mailbox
import email.utils
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import logging

class AppleMailProcessor:
    def __init__(self, export_dir: str, output_dir: str):
        self.export_dir = Path(export_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def process_mbox_file(self, mbox_path: Path) -> List[Dict]:
        """Process a single .mbox file and extract email data"""
        self.logger.info(f"Processing {mbox_path.name}")
        
        emails = []
        
        # Handle Mail.app directory structure
        if mbox_path.is_dir():
            # Mail.app creates a directory with an 'mbox' file inside
            actual_mbox_file = mbox_path / "mbox"
            if actual_mbox_file.exists():
                self.logger.info(f"Found Mail.app directory structure, using {actual_mbox_file}")
                mbox = mailbox.mbox(str(actual_mbox_file))
            else:
                self.logger.error(f"No 'mbox' file found in directory {mbox_path}")
                return []
        else:
            mbox = mailbox.mbox(str(mbox_path))
        
        for i, message in enumerate(mbox):
            try:
                email_data = self._extract_email_data(message)
                if email_data:
                    emails.append(email_data)
                    
                if (i + 1) % 100 == 0:
                    self.logger.info(f"Processed {i + 1} emails from {mbox_path.name}")
                    
            except Exception as e:
                self.logger.error(f"Error processing email {i}: {e}")
                continue
        
        self.logger.info(f"Successfully processed {len(emails)} emails from {mbox_path.name}")
        return emails
    
    def _extract_email_data(self, message) -> Optional[Dict]:
        """Extract relevant data from a single email message"""
        try:
            # Basic email metadata
            email_data = {
                'message_id': message.get('Message-ID', ''),
                'subject': self._clean_subject(message.get('Subject', '')),
                'from_address': self._extract_email_address(message.get('From', '')),
                'from_name': self._extract_name(message.get('From', '')),
                'to_addresses': self._extract_email_addresses(message.get('To', '')),
                'cc_addresses': self._extract_email_addresses(message.get('Cc', '')),
                'date_sent': self._parse_date(message.get('Date', '')),
                'thread_id': self._extract_thread_id(message),
            }
            
            # Extract email body
            body_text = self._extract_body_text(message)
            if body_text:
                email_data['body'] = body_text
                email_data['body_length'] = len(body_text)
                email_data['has_attachments'] = self._has_attachments(message)
                
                # Generate search keywords
                email_data['keywords'] = self._extract_keywords(email_data['subject'], body_text)
                
                return email_data
            
        except Exception as e:
            self.logger.error(f"Error extracting email data: {e}")
            return None
    
    def _clean_subject(self, subject: str) -> str:
        """Clean and normalize email subject"""
        if not subject:
            return ""
        
        # Remove Re: and Fwd: prefixes
        subject = re.sub(r'^(Re|RE|re|Fwd|FWD|fwd):\s*', '', subject)
        
        # Remove extra whitespace
        subject = ' '.join(subject.split())
        
        return subject.strip()
    
    def _extract_email_address(self, field: str) -> str:
        """Extract email address from email field"""
        if not field:
            return ""
        
        # Use email.utils to parse properly
        parsed = email.utils.parseaddr(field)
        return parsed[1] if parsed[1] else ""
    
    def _extract_name(self, field: str) -> str:
        """Extract display name from email field"""
        if not field:
            return ""
        
        parsed = email.utils.parseaddr(field)
        return parsed[0] if parsed[0] else ""
    
    def _extract_email_addresses(self, field: str) -> List[str]:
        """Extract multiple email addresses from field"""
        if not field:
            return []
        
        addresses = email.utils.getaddresses([field])
        return [addr[1] for addr in addresses if addr[1]]
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse email date into ISO format"""
        if not date_str:
            return None
        
        try:
            # Parse email date
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            return parsed_date.isoformat()
        except Exception:
            return None
    
    def _extract_thread_id(self, message) -> str:
        """Extract or generate thread ID for conversation grouping"""
        # Look for In-Reply-To or References headers
        in_reply_to = message.get('In-Reply-To', '')
        references = message.get('References', '')
        
        if in_reply_to:
            return in_reply_to.strip('<>')
        elif references:
            # Use first reference as thread ID
            refs = references.split()
            if refs:
                return refs[0].strip('<>')
        
        # Fall back to message ID for new threads
        msg_id = message.get('Message-ID', '')
        return msg_id.strip('<>')
    
    def _extract_body_text(self, message) -> str:
        """Extract plain text body from email"""
        body = ""
        
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body = part.get_payload(decode=True).decode(charset)
                        break
                    except (UnicodeDecodeError, AttributeError):
                        continue
        else:
            content_type = message.get_content_type()
            if content_type == "text/plain":
                charset = message.get_content_charset() or 'utf-8'
                try:
                    body = message.get_payload(decode=True).decode(charset)
                except (UnicodeDecodeError, AttributeError):
                    body = ""
        
        # Clean up body text
        if body:
            # Remove excessive whitespace
            body = re.sub(r'\n\s*\n\s*\n', '\n\n', body)
            body = body.strip()
        
        return body
    
    def _has_attachments(self, message) -> bool:
        """Check if email has attachments"""
        if not message.is_multipart():
            return False
        
        for part in message.walk():
            disposition = part.get('Content-Disposition', '')
            if 'attachment' in disposition:
                return True
        
        return False
    
    def _extract_keywords(self, subject: str, body: str) -> List[str]:
        """Extract important keywords from email content"""
        text = f"{subject} {body}".lower()
        
        # Remove common email artifacts
        text = re.sub(r'(on .* wrote:|-----original message----|\n>.*)', '', text)
        
        # Extract potential keywords (simple approach)
        # This could be enhanced with NLP libraries
        words = re.findall(r'\b\w{4,}\b', text)
        
        # Filter out common words
        stop_words = {'that', 'this', 'with', 'have', 'will', 'been', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were'}
        
        keywords = [w for w in set(words) if w not in stop_words and len(w) > 3]
        
        # Return top 10 most relevant keywords
        return keywords[:10]
    
    def save_processed_emails(self, emails: List[Dict], output_filename: str):
        """Save processed emails to JSON file"""
        output_path = self.output_dir / output_filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(emails, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved {len(emails)} emails to {output_path}")
    
    def process_all_mbox_files(self):
        """Process all .mbox files and directories in the export directory"""
        # Find both .mbox files and .mbox directories
        mbox_files = []
        
        for item in self.export_dir.iterdir():
            if item.name.endswith('.mbox'):
                mbox_files.append(item)
        
        if not mbox_files:
            self.logger.error(f"No .mbox files or directories found in {self.export_dir}")
            return
        
        all_emails = []
        
        for mbox_file in mbox_files:
            emails = self.process_mbox_file(mbox_file)
            
            # Save individual mailbox data
            # Clean filename by removing .mbox extension and spaces
            clean_name = mbox_file.name.replace('.mbox', '').replace(' ', '_')
            output_filename = f"processed_{clean_name}.json"
            self.save_processed_emails(emails, output_filename)
            
            all_emails.extend(emails)
        
        # Save combined data
        if all_emails:
            self.save_processed_emails(all_emails, "all_emails_processed.json")
            
            # Generate summary
            self._generate_processing_summary(all_emails)
    
    def _generate_processing_summary(self, emails: List[Dict]):
        """Generate a summary of processed emails"""
        summary = {
            'total_emails': len(emails),
            'date_range': self._get_date_range(emails),
            'top_senders': self._get_top_senders(emails, 10),
            'emails_by_year': self._get_emails_by_year(emails),
            'avg_body_length': sum(e.get('body_length', 0) for e in emails) // len(emails) if emails else 0,
            'emails_with_attachments': sum(1 for e in emails if e.get('has_attachments', False)),
        }
        
        summary_path = self.output_dir / "processing_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Processing summary saved to {summary_path}")
        self.logger.info(f"Total emails processed: {summary['total_emails']}")
    
    def _get_date_range(self, emails: List[Dict]) -> Dict[str, str]:
        """Get date range of processed emails"""
        dates = [e['date_sent'] for e in emails if e.get('date_sent')]
        if not dates:
            return {'earliest': None, 'latest': None}
        
        dates.sort()
        return {
            'earliest': dates[0],
            'latest': dates[-1]
        }
    
    def _get_top_senders(self, emails: List[Dict], limit: int) -> List[Dict]:
        """Get most frequent email senders"""
        sender_counts = {}
        
        for email in emails:
            sender = email.get('from_address', '')
            if sender:
                sender_counts[sender] = sender_counts.get(sender, 0) + 1
        
        # Sort by count and return top senders
        top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [{'email': sender, 'count': count} for sender, count in top_senders]
    
    def _get_emails_by_year(self, emails: List[Dict]) -> Dict[str, int]:
        """Count emails by year"""
        year_counts = {}
        
        for email in emails:
            date_sent = email.get('date_sent')
            if date_sent:
                try:
                    year = datetime.fromisoformat(date_sent.replace('Z', '+00:00')).year
                    year_counts[str(year)] = year_counts.get(str(year), 0) + 1
                except Exception:
                    continue
        
        return dict(sorted(year_counts.items()))

if __name__ == "__main__":
    # Configuration
    EXPORT_DIR = "data/mail_exports"
    OUTPUT_DIR = "data/processed"
    
    # Initialize processor
    processor = AppleMailProcessor(EXPORT_DIR, OUTPUT_DIR)
    
    # Process all .mbox files
    processor.process_all_mbox_files()
    
    print("Mail processing completed. Check the 'data/processed' directory for results.")