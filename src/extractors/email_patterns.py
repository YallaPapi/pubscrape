#!/usr/bin/env python3
"""
Email Pattern Recognition and Deobfuscation
Advanced email extraction patterns for comprehensive contact discovery
"""

import re
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass


@dataclass
class EmailPattern:
    """Email pattern definition with metadata"""
    pattern: re.Pattern
    priority: int
    description: str
    deobfuscation_type: str = "none"


class EmailPatternLibrary:
    """Comprehensive library of email patterns and deobfuscation methods"""
    
    def __init__(self):
        self.patterns = self._build_pattern_library()
        self.obfuscation_rules = self._build_deobfuscation_rules()
        
    def _build_pattern_library(self) -> List[EmailPattern]:
        """Build comprehensive email pattern library"""
        patterns = []
        
        # Standard RFC-compliant emails (highest priority)
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            priority=100,
            description="Standard RFC-compliant email format",
            deobfuscation_type="none"
        ))
        
        # Mailto href patterns
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'href=["\']mailto:([a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                re.IGNORECASE
            ),
            priority=95,
            description="Mailto link extraction",
            deobfuscation_type="none"
        ))
        
        # Common obfuscation patterns
        
        # [at] and [dot] replacements
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'\b[a-zA-Z0-9._-]+\s*\[at\]\s*[a-zA-Z0-9.-]+\s*\[dot\]\s*[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            priority=90,
            description="Square bracket obfuscation: [at] and [dot]",
            deobfuscation_type="bracket"
        ))
        
        # (at) and (dot) replacements
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'\b[a-zA-Z0-9._-]+\s*\(at\)\s*[a-zA-Z0-9.-]+\s*\(dot\)\s*[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            priority=85,
            description="Parenthesis obfuscation: (at) and (dot)",
            deobfuscation_type="parenthesis"
        ))
        
        # Uppercase AT and DOT
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'\b[a-zA-Z0-9._-]+\s*AT\s*[a-zA-Z0-9.-]+\s*DOT\s*[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            priority=80,
            description="Uppercase obfuscation: AT and DOT",
            deobfuscation_type="uppercase"
        ))
        
        # Space-separated words
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'\b[a-zA-Z0-9._-]+\s+at\s+[a-zA-Z0-9.-]+\s+dot\s+[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            priority=75,
            description="Space-separated obfuscation: word at word dot word",
            deobfuscation_type="spaces"
        ))
        
        # Unicode character replacements
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'\b[a-zA-Z0-9._-]+\s*[@＠]\s*[a-zA-Z0-9.-]+\s*[.．]\s*[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            priority=70,
            description="Unicode character obfuscation",
            deobfuscation_type="unicode"
        ))
        
        # HTML entity obfuscation
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'\b[a-zA-Z0-9._-]+\s*&#64;\s*[a-zA-Z0-9.-]+\s*&#46;\s*[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            priority=65,
            description="HTML entity obfuscation: &#64; and &#46;",
            deobfuscation_type="html_entity"
        ))
        
        # Hexadecimal entity obfuscation
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'\b[a-zA-Z0-9._-]+\s*&#x40;\s*[a-zA-Z0-9.-]+\s*&#x2E;\s*[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            priority=60,
            description="Hexadecimal entity obfuscation",
            deobfuscation_type="hex_entity"
        ))
        
        # Underscore replacement
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'\b[a-zA-Z0-9._-]+\s*_at_\s*[a-zA-Z0-9.-]+\s*_dot_\s*[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            priority=55,
            description="Underscore obfuscation: _at_ and _dot_",
            deobfuscation_type="underscore"
        ))
        
        # Dash replacement
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'\b[a-zA-Z0-9._-]+\s*-at-\s*[a-zA-Z0-9.-]+\s*-dot-\s*[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            priority=50,
            description="Dash obfuscation: -at- and -dot-",
            deobfuscation_type="dash"
        ))
        
        # Image-based obfuscation patterns (looking for alt text or data attributes)
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'alt=["\']([a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']',
                re.IGNORECASE
            ),
            priority=45,
            description="Image alt text email extraction",
            deobfuscation_type="none"
        ))
        
        # Data attribute patterns
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'data-email=["\']([a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']',
                re.IGNORECASE
            ),
            priority=40,
            description="Data attribute email extraction",
            deobfuscation_type="none"
        ))
        
        # CSS content patterns (for CSS-hidden emails)
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'content:\s*["\']([a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']',
                re.IGNORECASE
            ),
            priority=35,
            description="CSS content email extraction",
            deobfuscation_type="none"
        ))
        
        # JavaScript variable patterns
        patterns.append(EmailPattern(
            pattern=re.compile(
                r'(?:var|let|const)\s+\w*email\w*\s*=\s*["\']([a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']',
                re.IGNORECASE
            ),
            priority=30,
            description="JavaScript variable email extraction",
            deobfuscation_type="none"
        ))
        
        return sorted(patterns, key=lambda x: x.priority, reverse=True)
    
    def _build_deobfuscation_rules(self) -> Dict[str, List[Tuple[str, str]]]:
        """Build deobfuscation replacement rules"""
        return {
            "bracket": [
                (r'\s*\[at\]\s*', '@'),
                (r'\s*\[dot\]\s*', '.'),
                (r'\s*\[AT\]\s*', '@'),
                (r'\s*\[DOT\]\s*', '.')
            ],
            "parenthesis": [
                (r'\s*\(at\)\s*', '@'),
                (r'\s*\(dot\)\s*', '.'),
                (r'\s*\(AT\)\s*', '@'),
                (r'\s*\(DOT\)\s*', '.')
            ],
            "uppercase": [
                (r'\s*AT\s*', '@'),
                (r'\s*DOT\s*', '.')
            ],
            "spaces": [
                (r'\s+at\s+', '@'),
                (r'\s+dot\s+', '.'),
                (r'\s+AT\s+', '@'),
                (r'\s+DOT\s+', '.')
            ],
            "unicode": [
                (r'[@＠]', '@'),
                (r'[.．]', '.')
            ],
            "html_entity": [
                (r'&#64;', '@'),
                (r'&#46;', '.'),
                (r'&\#64;', '@'),
                (r'&\#46;', '.')
            ],
            "hex_entity": [
                (r'&#x40;', '@'),
                (r'&#x2E;', '.'),
                (r'&\#x40;', '@'),
                (r'&\#x2E;', '.')
            ],
            "underscore": [
                (r'_at_', '@'),
                (r'_dot_', '.'),
                (r'_AT_', '@'),
                (r'_DOT_', '.')
            ],
            "dash": [
                (r'-at-', '@'),
                (r'-dot-', '.'),
                (r'-AT-', '@'),
                (r'-DOT-', '.')
            ]
        }
    
    def extract_emails(self, text: str, html_content: str = "") -> List[Dict[str, Any]]:
        """Extract emails using all patterns with deobfuscation"""
        found_emails = []
        processed_emails = set()
        
        # Process both text and HTML content
        content_sources = [
            ("text", text),
            ("html", html_content)
        ] if html_content else [("text", text)]
        
        for source_type, content in content_sources:
            if not content:
                continue
                
            for pattern_info in self.patterns:
                matches = pattern_info.pattern.finditer(content)
                
                for match in matches:
                    # Extract email from match
                    if match.groups():
                        # Use first group if available
                        raw_email = match.group(1)
                    else:
                        # Use full match
                        raw_email = match.group(0)
                    
                    # Apply deobfuscation
                    email = self.deobfuscate_email(raw_email, pattern_info.deobfuscation_type)
                    
                    # Validate and normalize
                    if self.is_valid_email(email):
                        email_lower = email.lower()
                        
                        # Avoid duplicates
                        if email_lower not in processed_emails:
                            processed_emails.add(email_lower)
                            
                            # Get context around the email
                            context = self._get_email_context(content, match.start(), match.end())
                            
                            found_emails.append({
                                'email': email_lower,
                                'source': source_type,
                                'pattern': pattern_info.description,
                                'priority': pattern_info.priority,
                                'context': context,
                                'obfuscation_type': pattern_info.deobfuscation_type,
                                'position': match.start()
                            })
        
        # Sort by priority and return unique results
        return sorted(found_emails, key=lambda x: x['priority'], reverse=True)
    
    def deobfuscate_email(self, text: str, deobfuscation_type: str) -> str:
        """Apply deobfuscation rules to convert obfuscated text to valid email"""
        if deobfuscation_type == "none":
            return text.strip()
        
        result = text
        rules = self.obfuscation_rules.get(deobfuscation_type, [])
        
        for pattern, replacement in rules:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result.strip()
    
    def is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        if not email or '@' not in email:
            return False
        
        # Split into local and domain parts
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        
        # Basic validation
        if not local or not domain:
            return False
        
        # Domain must have at least one dot
        if '.' not in domain:
            return False
        
        # Must end with valid TLD (2+ characters)
        if not re.match(r'.*\.[a-zA-Z]{2,}$', domain):
            return False
        
        # Local part validation
        if len(local) > 64 or len(domain) > 253:
            return False
        
        return True
    
    def _get_email_context(self, content: str, start: int, end: int, window: int = 100) -> str:
        """Extract context around email position"""
        context_start = max(0, start - window)
        context_end = min(len(content), end + window)
        context = content[context_start:context_end]
        
        # Clean up context
        context = re.sub(r'\s+', ' ', context)
        context = context.strip()
        
        return context[:200]  # Limit context length


class ContactFormAnalyzer:
    """Analyze contact forms for email discovery"""
    
    def __init__(self):
        self.form_patterns = self._build_form_patterns()
    
    def _build_form_patterns(self) -> List[re.Pattern]:
        """Build patterns to identify contact forms"""
        return [
            # Form action patterns
            re.compile(r'<form[^>]*action=["\'][^"\']*contact[^"\']*["\'][^>]*>', re.IGNORECASE),
            re.compile(r'<form[^>]*action=["\'][^"\']*email[^"\']*["\'][^>]*>', re.IGNORECASE),
            re.compile(r'<form[^>]*action=["\'][^"\']*message[^"\']*["\'][^>]*>', re.IGNORECASE),
            
            # Form class/id patterns
            re.compile(r'<form[^>]*class=["\'][^"\']*contact[^"\']*["\'][^>]*>', re.IGNORECASE),
            re.compile(r'<form[^>]*id=["\'][^"\']*contact[^"\']*["\'][^>]*>', re.IGNORECASE),
            
            # Input email patterns
            re.compile(r'<input[^>]*type=["\']email["\'][^>]*>', re.IGNORECASE),
            re.compile(r'<input[^>]*name=["\'][^"\']*email[^"\']*["\'][^>]*>', re.IGNORECASE),
        ]
    
    def analyze_forms(self, html_content: str) -> List[Dict[str, Any]]:
        """Analyze HTML content for contact forms"""
        forms_found = []
        
        # Find all forms
        form_pattern = re.compile(r'<form[^>]*>.*?</form>', re.IGNORECASE | re.DOTALL)
        forms = form_pattern.finditer(html_content)
        
        for i, form_match in enumerate(forms):
            form_html = form_match.group(0)
            
            # Check if this is a contact form
            is_contact_form = any(pattern.search(form_html) for pattern in self.form_patterns)
            
            if is_contact_form:
                # Extract form details
                action = self._extract_form_action(form_html)
                method = self._extract_form_method(form_html)
                fields = self._extract_form_fields(form_html)
                
                forms_found.append({
                    'form_index': i,
                    'action': action,
                    'method': method,
                    'fields': fields,
                    'html': form_html[:500],  # First 500 chars for reference
                    'is_contact_form': True,
                    'position': form_match.start()
                })
        
        return forms_found
    
    def _extract_form_action(self, form_html: str) -> str:
        """Extract form action URL"""
        action_match = re.search(r'action=["\']([^"\']*)["\']', form_html, re.IGNORECASE)
        return action_match.group(1) if action_match else ""
    
    def _extract_form_method(self, form_html: str) -> str:
        """Extract form method"""
        method_match = re.search(r'method=["\']([^"\']*)["\']', form_html, re.IGNORECASE)
        return method_match.group(1).upper() if method_match else "GET"
    
    def _extract_form_fields(self, form_html: str) -> List[Dict[str, str]]:
        """Extract form input fields"""
        fields = []
        
        # Input fields
        input_pattern = re.compile(r'<input[^>]*>', re.IGNORECASE)
        inputs = input_pattern.finditer(form_html)
        
        for input_match in inputs:
            input_html = input_match.group(0)
            
            field_type = self._extract_attribute(input_html, 'type')
            field_name = self._extract_attribute(input_html, 'name')
            field_placeholder = self._extract_attribute(input_html, 'placeholder')
            
            if field_name or field_type:
                fields.append({
                    'type': field_type or 'text',
                    'name': field_name or '',
                    'placeholder': field_placeholder or '',
                    'element': 'input'
                })
        
        # Textarea fields
        textarea_pattern = re.compile(r'<textarea[^>]*>.*?</textarea>', re.IGNORECASE | re.DOTALL)
        textareas = textarea_pattern.finditer(form_html)
        
        for textarea_match in textareas:
            textarea_html = textarea_match.group(0)
            field_name = self._extract_attribute(textarea_html, 'name')
            field_placeholder = self._extract_attribute(textarea_html, 'placeholder')
            
            fields.append({
                'type': 'textarea',
                'name': field_name or '',
                'placeholder': field_placeholder or '',
                'element': 'textarea'
            })
        
        return fields
    
    def _extract_attribute(self, html: str, attribute: str) -> str:
        """Extract attribute value from HTML element"""
        pattern = re.compile(f'{attribute}=["\']([^"\']*)["\']', re.IGNORECASE)
        match = pattern.search(html)
        return match.group(1) if match else ""


# Pre-built pattern library instance
EMAIL_PATTERNS = EmailPatternLibrary()
CONTACT_FORM_ANALYZER = ContactFormAnalyzer()


def extract_emails_comprehensive(text: str, html_content: str = "") -> List[Dict[str, Any]]:
    """
    Comprehensive email extraction using all available patterns
    
    Args:
        text: Plain text content
        html_content: HTML content (optional)
    
    Returns:
        List of email dictionaries with metadata
    """
    return EMAIL_PATTERNS.extract_emails(text, html_content)


def analyze_contact_forms(html_content: str) -> List[Dict[str, Any]]:
    """
    Analyze HTML content for contact forms
    
    Args:
        html_content: HTML content to analyze
    
    Returns:
        List of contact form dictionaries
    """
    return CONTACT_FORM_ANALYZER.analyze_forms(html_content)


def test_email_patterns():
    """Test email pattern library with various obfuscation methods"""
    test_cases = [
        # Standard emails
        "Contact us at info@example.com for more information",
        "Email john.doe@company.org for details",
        
        # Obfuscated emails
        "Reach out to support [at] company [dot] com",
        "Contact admin (at) business (dot) net",
        "Write to ceo AT startup DOT io",
        "Email sales at company dot com",
        "Contact info_at_business_dot_org",
        "Reach admin-at-company-dot-net",
        
        # HTML patterns
        '<a href="mailto:contact@example.com">Email Us</a>',
        '<div data-email="hidden@company.com">Contact</div>',
        '<img alt="support@business.org" src="email.png">',
        
        # JavaScript patterns
        'var contactEmail = "info@company.com";',
        'let email = "support@business.net";',
        
        # HTML entity obfuscation
        "Contact us at info&#64;company&#46;com",
        "Email support&#x40;business&#x2E;org",
        
        # Unicode obfuscation
        "Reach info＠company．com",
        "Contact admin@business.org"
    ]
    
    print("Testing Email Pattern Library")
    print("=" * 50)
    
    total_found = 0
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_text}")
        emails = extract_emails_comprehensive(test_text, test_text)
        
        if emails:
            for email in emails:
                print(f"  Found: {email['email']} (pattern: {email['pattern']}, priority: {email['priority']})")
                total_found += 1
        else:
            print("  No emails found")
    
    print(f"\nTotal emails extracted: {total_found}")
    print(f"Test cases processed: {len(test_cases)}")
    
    return total_found > 0


if __name__ == "__main__":
    test_email_patterns()