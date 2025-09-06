import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
import logging

class AppleMailValidator:
    def __init__(self, processed_data_dir: str):
        self.data_dir = Path(processed_data_dir)
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
    
    def validate_processed_emails(self, filename: str = "all_emails_processed.json") -> Dict:
        """Validate processed email data"""
        file_path = self.data_dir / filename
        
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return {"valid": False, "error": "File not found"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                emails = json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON: {e}")
            return {"valid": False, "error": f"Invalid JSON: {e}"}
        
        if not isinstance(emails, list):
            return {"valid": False, "error": "Data should be a list of emails"}
        
        # Run validation checks
        validation_results = {
            "total_emails": len(emails),
            "file_size_mb": file_path.stat().st_size / (1024 * 1024),
            "structure_valid": True,
            "data_quality": self._check_data_quality(emails),
            "privacy_check": self._check_privacy_concerns(emails),
            "content_analysis": self._analyze_content(emails),
            "recommendations": []
        }
        
        # Generate recommendations
        validation_results["recommendations"] = self._generate_recommendations(validation_results)
        
        return validation_results
    
    def _check_data_quality(self, emails: List[Dict]) -> Dict:
        """Check data quality metrics"""
        quality_metrics = {
            "emails_with_subject": 0,
            "emails_with_body": 0,
            "emails_with_valid_date": 0,
            "emails_with_sender": 0,
            "average_body_length": 0,
            "empty_or_short_emails": 0,
            "duplicate_message_ids": 0
        }
        
        message_ids = set()
        total_body_length = 0
        
        for email in emails:
            # Check for required fields
            if email.get('subject', '').strip():
                quality_metrics["emails_with_subject"] += 1
            
            body = email.get('body', '')
            if body.strip():
                quality_metrics["emails_with_body"] += 1
                total_body_length += len(body)
            
            if len(body.strip()) < 10:  # Very short emails
                quality_metrics["empty_or_short_emails"] += 1
            
            if email.get('date_sent'):
                quality_metrics["emails_with_valid_date"] += 1
            
            if email.get('from_address', '').strip():
                quality_metrics["emails_with_sender"] += 1
            
            # Check for duplicates
            msg_id = email.get('message_id', '')
            if msg_id:
                if msg_id in message_ids:
                    quality_metrics["duplicate_message_ids"] += 1
                else:
                    message_ids.add(msg_id)
        
        # Calculate averages
        if quality_metrics["emails_with_body"] > 0:
            quality_metrics["average_body_length"] = total_body_length // quality_metrics["emails_with_body"]
        
        return quality_metrics
    
    def _check_privacy_concerns(self, emails: List[Dict]) -> Dict:
        """Check for potential privacy issues"""
        privacy_patterns = {
            'password_related': re.compile(r'\b(password|pwd|passcode|pin)\b', re.IGNORECASE),
            'financial': re.compile(r'\b(account\s+number|routing\s+number|ssn|social\s+security|credit\s+card)\b', re.IGNORECASE),
            'sensitive_personal': re.compile(r'\b(medical|health|diagnosis|prescription|therapy)\b', re.IGNORECASE),
            'legal': re.compile(r'\b(confidential|attorney|lawyer|legal\s+matter|lawsuit)\b', re.IGNORECASE)
        }
        
        privacy_results = {
            'potentially_sensitive_emails': 0,
            'sensitive_categories': {},
            'flagged_senders': set(),
            'sample_subjects': []
        }
        
        for email in emails:
            email_text = f"{email.get('subject', '')} {email.get('body', '')}"
            is_sensitive = False
            
            for category, pattern in privacy_patterns.items():
                if pattern.search(email_text):
                    if category not in privacy_results['sensitive_categories']:
                        privacy_results['sensitive_categories'][category] = 0
                    privacy_results['sensitive_categories'][category] += 1
                    is_sensitive = True
            
            if is_sensitive:
                privacy_results['potentially_sensitive_emails'] += 1
                privacy_results['flagged_senders'].add(email.get('from_address', 'unknown'))
                
                # Keep sample subjects for review
                if len(privacy_results['sample_subjects']) < 5:
                    privacy_results['sample_subjects'].append(email.get('subject', ''))
        
        # Convert set to list for JSON serialization
        privacy_results['flagged_senders'] = list(privacy_results['flagged_senders'])
        
        return privacy_results
    
    def _analyze_content(self, emails: List[Dict]) -> Dict:
        """Analyze email content patterns"""
        content_analysis = {
            'date_range': self._get_date_range(emails),
            'top_senders': self._get_top_senders(emails, 10),
            'subject_patterns': self._analyze_subjects(emails),
            'language_distribution': self._estimate_language_distribution(emails),
            'thread_analysis': self._analyze_threads(emails)
        }
        
        return content_analysis
    
    def _get_date_range(self, emails: List[Dict]) -> Dict:
        """Get date range of emails"""
        dates = []
        for email in emails:
            date_sent = email.get('date_sent')
            if date_sent:
                dates.append(date_sent)
        
        if not dates:
            return {'earliest': None, 'latest': None, 'span_years': 0}
        
        dates.sort()
        earliest = dates[0]
        latest = dates[-1]
        
        # Calculate span in years (rough estimate)
        try:
            from datetime import datetime
            early_dt = datetime.fromisoformat(earliest.replace('Z', '+00:00'))
            late_dt = datetime.fromisoformat(latest.replace('Z', '+00:00'))
            span_years = (late_dt - early_dt).days / 365.25
        except:
            span_years = 0
        
        return {
            'earliest': earliest,
            'latest': latest,
            'span_years': round(span_years, 1)
        }
    
    def _get_top_senders(self, emails: List[Dict], limit: int) -> List[Dict]:
        """Get most frequent senders"""
        sender_counts = {}
        
        for email in emails:
            sender = email.get('from_address', '')
            if sender:
                sender_counts[sender] = sender_counts.get(sender, 0) + 1
        
        top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{'email': sender, 'count': count} for sender, count in top_senders]
    
    def _analyze_subjects(self, emails: List[Dict]) -> Dict:
        """Analyze email subject patterns"""
        subjects = [email.get('subject', '') for email in emails if email.get('subject', '').strip()]
        
        # Find common words in subjects
        word_counts = {}
        for subject in subjects:
            words = re.findall(r'\b\w+\b', subject.lower())
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        common_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        
        return {
            'total_subjects': len(subjects),
            'empty_subjects': len([s for s in subjects if not s.strip()]),
            'common_words': [{'word': word, 'count': count} for word, count in common_words],
            'avg_subject_length': sum(len(s) for s in subjects) // len(subjects) if subjects else 0
        }
    
    def _estimate_language_distribution(self, emails: List[Dict]) -> Dict:
        """Rough estimation of language distribution based on common words"""
        # Very basic language detection based on common words
        english_indicators = {'the', 'and', 'you', 'that', 'was', 'for', 'are', 'with', 'his', 'they', 'have', 'this'}
        
        text_samples = []
        for email in emails[:100]:  # Sample first 100 emails
            text = f"{email.get('subject', '')} {email.get('body', '')[:200]}"  # First 200 chars of body
            text_samples.append(text.lower())
        
        english_score = 0
        for text in text_samples:
            words = set(re.findall(r'\b\w+\b', text))
            english_matches = len(words & english_indicators)
            if english_matches >= 2:  # At least 2 English indicators
                english_score += 1
        
        english_percentage = (english_score / len(text_samples)) * 100 if text_samples else 0
        
        return {
            'estimated_english_percentage': round(english_percentage, 1),
            'sample_size': len(text_samples),
            'note': 'Basic estimation based on common English words'
        }
    
    def _analyze_threads(self, emails: List[Dict]) -> Dict:
        """Analyze email thread patterns"""
        thread_ids = [email.get('thread_id', '') for email in emails if email.get('thread_id', '')]
        unique_threads = set(thread_ids)
        
        thread_counts = {}
        for thread_id in thread_ids:
            thread_counts[thread_id] = thread_counts.get(thread_id, 0) + 1
        
        # Find threads with multiple emails
        conversation_threads = {k: v for k, v in thread_counts.items() if v > 1}
        
        return {
            'total_emails_with_threads': len(thread_ids),
            'unique_threads': len(unique_threads),
            'conversation_threads': len(conversation_threads),
            'avg_thread_length': sum(conversation_threads.values()) // len(conversation_threads) if conversation_threads else 0,
            'longest_thread_length': max(conversation_threads.values()) if conversation_threads else 0
        }
    
    def _generate_recommendations(self, validation_results: Dict) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Data quality recommendations
        quality = validation_results['data_quality']
        total_emails = validation_results['total_emails']
        
        if quality['empty_or_short_emails'] > total_emails * 0.1:
            recommendations.append(f"Consider filtering out {quality['empty_or_short_emails']} very short/empty emails")
        
        if quality['duplicate_message_ids'] > 0:
            recommendations.append(f"Found {quality['duplicate_message_ids']} duplicate emails - consider deduplication")
        
        if quality['emails_with_valid_date'] < total_emails * 0.9:
            recommendations.append("Some emails missing valid dates - may affect chronological search")
        
        # Privacy recommendations
        privacy = validation_results['privacy_check']
        if privacy['potentially_sensitive_emails'] > 0:
            recommendations.append(f"Found {privacy['potentially_sensitive_emails']} potentially sensitive emails - review privacy filtering")
        
        # Content recommendations
        content = validation_results['content_analysis']
        if content['date_range']['span_years'] > 10:
            recommendations.append("Large date range - consider archiving very old emails separately")
        
        if len(content['top_senders']) < 5:
            recommendations.append("Limited sender diversity - may indicate incomplete export")
        
        # File size recommendations
        file_size = validation_results['file_size_mb']
        if file_size > 100:
            recommendations.append(f"Large file size ({file_size:.1f}MB) - consider processing in chunks for better performance")
        
        if not recommendations:
            recommendations.append("Data looks good - ready for Kenny integration!")
        
        return recommendations
    
    def generate_validation_report(self, output_filename: str = "validation_report.json"):
        """Generate and save comprehensive validation report"""
        validation_results = self.validate_processed_emails()
        
        report_path = self.data_dir / output_filename
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Validation report saved to {report_path}")
        
        # Print summary to console
        print("\n" + "="*50)
        print("EMAIL DATA VALIDATION SUMMARY")
        print("="*50)
        print(f"Total emails processed: {validation_results['total_emails']}")
        print(f"File size: {validation_results['file_size_mb']:.1f} MB")
        print(f"Date range: {validation_results['content_analysis']['date_range']['span_years']} years")
        print(f"Potentially sensitive emails: {validation_results['privacy_check']['potentially_sensitive_emails']}")
        
        print("\nRecommendations:")
        for i, rec in enumerate(validation_results['recommendations'], 1):
            print(f"{i}. {rec}")
        
        return validation_results

if __name__ == "__main__":
    validator = AppleMailValidator("data/processed")
    validator.generate_validation_report()