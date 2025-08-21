"""
DNS Validation Tool

Agency Swarm tool for DNS-based email domain validation including MX record
checking, domain reputation analysis, and bulk DNS validation capabilities.
"""

import logging
import time
import dns.resolver
import concurrent.futures
import threading
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict, Counter
from pydantic import Field
from dataclasses import dataclass, asdict

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


@dataclass
class DNSValidationResult:
    """Result of DNS validation for a domain"""
    domain: str
    has_mx_record: bool = False
    mx_records: List[str] = None
    a_records: List[str] = None
    aaaa_records: List[str] = None
    txt_records: List[str] = None
    validation_time_ms: float = 0.0
    error: Optional[str] = None
    cache_hit: bool = False
    
    def __post_init__(self):
        if self.mx_records is None:
            self.mx_records = []
        if self.a_records is None:
            self.a_records = []
        if self.aaaa_records is None:
            self.aaaa_records = []
        if self.txt_records is None:
            self.txt_records = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class DNSValidationTool(BaseTool):
    """
    Tool for validating email domains using DNS record checks.
    
    Performs MX record validation, A/AAAA record checks, and provides
    detailed DNS analysis for email domain validation.
    """
    
    domains: List[str] = Field(
        ...,
        description="List of domains to validate via DNS"
    )
    
    check_mx_records: bool = Field(
        default=True,
        description="Check for MX (Mail Exchange) records"
    )
    
    check_a_records: bool = Field(
        default=True,
        description="Check for A (IPv4) records"
    )
    
    check_aaaa_records: bool = Field(
        default=False,
        description="Check for AAAA (IPv6) records"
    )
    
    check_txt_records: bool = Field(
        default=False,
        description="Check for TXT records (SPF, DMARC analysis)"
    )
    
    dns_timeout: float = Field(
        default=5.0,
        description="DNS query timeout in seconds"
    )
    
    max_workers: int = Field(
        default=10,
        description="Maximum number of parallel DNS workers"
    )
    
    enable_caching: bool = Field(
        default=True,
        description="Enable DNS result caching to avoid redundant queries"
    )
    
    cache_ttl: int = Field(
        default=3600,
        description="Cache TTL in seconds (default: 1 hour)"
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        self._dns_cache = {}
        self._cache_lock = threading.Lock()
        self.logger = logging.getLogger(f"{__name__}.DNSValidationTool")
    
    def run(self) -> Dict[str, Any]:
        """
        Validate domains using DNS queries.
        
        Returns:
            Dictionary with DNS validation results and statistics
        """
        start_time = time.time()
        
        # Remove duplicates while preserving order
        unique_domains = []
        seen = set()
        for domain in self.domains:
            domain_clean = domain.strip().lower()
            if domain_clean and domain_clean not in seen:
                unique_domains.append(domain_clean)
                seen.add(domain_clean)
        
        # Validate domains in parallel
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_domain = {
                executor.submit(self._validate_single_domain, domain): domain
                for domain in unique_domains
            }
            
            for future in concurrent.futures.as_completed(future_to_domain):
                domain = future_to_domain[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"DNS validation error for {domain}: {e}")
                    error_result = DNSValidationResult(
                        domain=domain,
                        error=f"Validation error: {str(e)}"
                    )
                    results.append(error_result)
        
        # Sort results to maintain input order
        domain_to_result = {r.domain: r for r in results}
        ordered_results = [
            domain_to_result.get(domain, DNSValidationResult(domain=domain, error="Not processed"))
            for domain in unique_domains
        ]
        
        # Generate statistics
        stats = self._generate_statistics(ordered_results)
        
        # Analysis
        analysis = self._analyze_dns_results(ordered_results)
        
        total_time = time.time() - start_time
        
        return {
            'summary': {
                'total_domains': len(self.domains),
                'unique_domains': len(unique_domains),
                'successful_validations': stats['successful_validations'],
                'domains_with_mx_records': stats['domains_with_mx_records'],
                'domains_with_errors': stats['domains_with_errors'],
                'cache_hit_rate': stats['cache_hit_rate'],
                'processing_time_seconds': total_time,
                'domains_per_second': len(unique_domains) / max(0.001, total_time)
            },
            'validation_stats': stats,
            'dns_analysis': analysis,
            'results': [result.to_dict() for result in ordered_results],
            'valid_domains': [
                result.to_dict() for result in ordered_results 
                if result.has_mx_record and not result.error
            ],
            'invalid_domains': [
                result.to_dict() for result in ordered_results 
                if not result.has_mx_record or result.error
            ],
            'configuration': {
                'check_mx_records': self.check_mx_records,
                'check_a_records': self.check_a_records,
                'check_aaaa_records': self.check_aaaa_records,
                'check_txt_records': self.check_txt_records,
                'dns_timeout': self.dns_timeout,
                'enable_caching': self.enable_caching
            }
        }
    
    def _validate_single_domain(self, domain: str) -> DNSValidationResult:
        """Validate a single domain via DNS"""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"dns_{domain}"
        if self.enable_caching:
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                cached_result.cache_hit = True
                cached_result.validation_time_ms = (time.time() - start_time) * 1000
                return cached_result
        
        result = DNSValidationResult(domain=domain)
        
        try:
            # Configure DNS resolver
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.dns_timeout
            resolver.lifetime = self.dns_timeout
            
            # Check MX records
            if self.check_mx_records:
                try:
                    mx_answers = resolver.resolve(domain, 'MX')
                    result.mx_records = [
                        str(answer.exchange).rstrip('.') 
                        for answer in mx_answers
                    ]
                    result.has_mx_record = len(result.mx_records) > 0
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    result.has_mx_record = False
                except Exception as e:
                    self.logger.debug(f"MX lookup failed for {domain}: {e}")
                    result.error = f"MX lookup error: {str(e)}"
            
            # Check A records
            if self.check_a_records:
                try:
                    a_answers = resolver.resolve(domain, 'A')
                    result.a_records = [str(answer) for answer in a_answers]
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    pass  # No A records is not necessarily an error
                except Exception as e:
                    self.logger.debug(f"A record lookup failed for {domain}: {e}")
            
            # Check AAAA records
            if self.check_aaaa_records:
                try:
                    aaaa_answers = resolver.resolve(domain, 'AAAA')
                    result.aaaa_records = [str(answer) for answer in aaaa_answers]
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    pass  # No AAAA records is not necessarily an error
                except Exception as e:
                    self.logger.debug(f"AAAA record lookup failed for {domain}: {e}")
            
            # Check TXT records
            if self.check_txt_records:
                try:
                    txt_answers = resolver.resolve(domain, 'TXT')
                    result.txt_records = [
                        str(answer).strip('"') for answer in txt_answers
                    ]
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    pass  # No TXT records is not necessarily an error
                except Exception as e:
                    self.logger.debug(f"TXT record lookup failed for {domain}: {e}")
            
            # Cache successful result
            if self.enable_caching and not result.error:
                self._cache_result(cache_key, result)
            
        except dns.resolver.NXDOMAIN:
            result.error = "Domain does not exist"
        except dns.resolver.Timeout:
            result.error = "DNS query timeout"
        except Exception as e:
            result.error = f"DNS resolution error: {str(e)}"
            self.logger.debug(f"DNS validation failed for {domain}: {e}")
        
        result.validation_time_ms = (time.time() - start_time) * 1000
        return result
    
    def _get_cached_result(self, cache_key: str) -> Optional[DNSValidationResult]:
        """Get cached DNS result"""
        with self._cache_lock:
            if cache_key in self._dns_cache:
                result, timestamp = self._dns_cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    # Return a copy of the cached result
                    return DNSValidationResult(
                        domain=result.domain,
                        has_mx_record=result.has_mx_record,
                        mx_records=result.mx_records.copy(),
                        a_records=result.a_records.copy(),
                        aaaa_records=result.aaaa_records.copy(),
                        txt_records=result.txt_records.copy(),
                        error=result.error
                    )
                else:
                    # Remove expired entry
                    del self._dns_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: DNSValidationResult):
        """Cache DNS result"""
        with self._cache_lock:
            self._dns_cache[cache_key] = (result, time.time())
    
    def _generate_statistics(self, results: List[DNSValidationResult]) -> Dict[str, Any]:
        """Generate validation statistics"""
        stats = {
            'total_processed': len(results),
            'successful_validations': 0,
            'domains_with_mx_records': 0,
            'domains_with_a_records': 0,
            'domains_with_aaaa_records': 0,
            'domains_with_txt_records': 0,
            'domains_with_errors': 0,
            'cache_hits': 0,
            'avg_validation_time_ms': 0.0,
            'total_validation_time_ms': 0.0
        }
        
        total_time = 0.0
        error_types = Counter()
        
        for result in results:
            total_time += result.validation_time_ms
            
            if result.error:
                stats['domains_with_errors'] += 1
                error_types[result.error] += 1
            else:
                stats['successful_validations'] += 1
            
            if result.has_mx_record:
                stats['domains_with_mx_records'] += 1
            
            if result.a_records:
                stats['domains_with_a_records'] += 1
            
            if result.aaaa_records:
                stats['domains_with_aaaa_records'] += 1
            
            if result.txt_records:
                stats['domains_with_txt_records'] += 1
            
            if result.cache_hit:
                stats['cache_hits'] += 1
        
        if results:
            stats['avg_validation_time_ms'] = total_time / len(results)
            stats['cache_hit_rate'] = stats['cache_hits'] / len(results)
        
        stats['total_validation_time_ms'] = total_time
        stats['error_breakdown'] = dict(error_types.most_common())
        
        return stats
    
    def _analyze_dns_results(self, results: List[DNSValidationResult]) -> Dict[str, Any]:
        """Analyze DNS results for patterns and insights"""
        
        # MX provider analysis
        mx_providers = Counter()
        mx_provider_domains = defaultdict(list)
        
        # Domain reliability analysis
        reliable_domains = []
        unreliable_domains = []
        
        # Performance analysis
        fast_domains = []
        slow_domains = []
        
        for result in results:
            if result.error:
                unreliable_domains.append({
                    'domain': result.domain,
                    'error': result.error,
                    'validation_time_ms': result.validation_time_ms
                })
                continue
            
            # Reliability check
            if result.has_mx_record and (result.a_records or result.aaaa_records):
                reliable_domains.append(result.domain)
            else:
                unreliable_domains.append({
                    'domain': result.domain,
                    'reason': 'Missing MX or A/AAAA records',
                    'validation_time_ms': result.validation_time_ms
                })
            
            # Performance analysis
            if result.validation_time_ms < 1000:  # Less than 1 second
                fast_domains.append(result.domain)
            elif result.validation_time_ms > 3000:  # More than 3 seconds
                slow_domains.append({
                    'domain': result.domain,
                    'validation_time_ms': result.validation_time_ms
                })
            
            # MX provider analysis
            for mx_record in result.mx_records:
                # Extract provider from MX record
                provider = self._extract_mx_provider(mx_record)
                mx_providers[provider] += 1
                mx_provider_domains[provider].append(result.domain)
        
        # Security and configuration analysis
        security_analysis = self._analyze_security_features(results)
        
        return {
            'reliability': {
                'reliable_domains': len(reliable_domains),
                'unreliable_domains': len(unreliable_domains),
                'reliability_rate': len(reliable_domains) / max(1, len(results)),
                'unreliable_details': unreliable_domains[:10]  # Top 10 for brevity
            },
            'performance': {
                'fast_domains': len(fast_domains),
                'slow_domains': len(slow_domains),
                'slow_domain_details': slow_domains[:10]
            },
            'mx_providers': {
                'top_providers': dict(mx_providers.most_common(10)),
                'provider_distribution': {
                    provider: len(domains) 
                    for provider, domains in mx_provider_domains.items()
                }
            },
            'security_features': security_analysis,
            'recommendations': self._generate_dns_recommendations(results)
        }
    
    def _extract_mx_provider(self, mx_record: str) -> str:
        """Extract mail provider from MX record"""
        mx_lower = mx_record.lower()
        
        # Common providers
        if 'google' in mx_lower or 'gmail' in mx_lower:
            return 'Google Workspace'
        elif 'outlook' in mx_lower or 'office365' in mx_lower or 'microsoft' in mx_lower:
            return 'Microsoft 365'
        elif 'cloudflare' in mx_lower:
            return 'Cloudflare'
        elif 'proofpoint' in mx_lower:
            return 'Proofpoint'
        elif 'mimecast' in mx_lower:
            return 'Mimecast'
        elif 'barracuda' in mx_lower:
            return 'Barracuda'
        elif 'mailgun' in mx_lower:
            return 'Mailgun'
        elif 'sendgrid' in mx_lower:
            return 'SendGrid'
        elif 'amazon' in mx_lower or 'aws' in mx_lower:
            return 'Amazon SES'
        else:
            # Extract domain from MX record
            parts = mx_record.split('.')
            if len(parts) >= 2:
                return f"{parts[-2]}.{parts[-1]}"
            return 'Unknown'
    
    def _analyze_security_features(self, results: List[DNSValidationResult]) -> Dict[str, Any]:
        """Analyze security-related DNS features"""
        
        spf_records = 0
        dmarc_records = 0
        dkim_indicators = 0
        
        for result in results:
            if not result.txt_records:
                continue
            
            for txt_record in result.txt_records:
                txt_lower = txt_record.lower()
                
                if txt_record.startswith('v=spf1'):
                    spf_records += 1
                elif txt_record.startswith('v=dmarc1'):
                    dmarc_records += 1
                elif 'dkim' in txt_lower:
                    dkim_indicators += 1
        
        return {
            'spf_records': spf_records,
            'dmarc_records': dmarc_records,
            'dkim_indicators': dkim_indicators,
            'domains_with_spf': spf_records,
            'domains_with_dmarc': dmarc_records
        }
    
    def _generate_dns_recommendations(self, results: List[DNSValidationResult]) -> List[str]:
        """Generate actionable recommendations based on DNS analysis"""
        recommendations = []
        
        total_domains = len(results)
        domains_with_mx = sum(1 for r in results if r.has_mx_record)
        domains_with_errors = sum(1 for r in results if r.error)
        
        # MX record recommendations
        mx_rate = domains_with_mx / max(1, total_domains)
        if mx_rate < 0.8:
            recommendations.append(
                f"Low MX record rate ({mx_rate:.1%}). Consider filtering for domains "
                "with valid mail exchange records to improve deliverability."
            )
        
        # Error rate recommendations
        error_rate = domains_with_errors / max(1, total_domains)
        if error_rate > 0.2:
            recommendations.append(
                f"High DNS error rate ({error_rate:.1%}). Consider implementing "
                "retry logic and fallback mechanisms for DNS validation."
            )
        
        # Performance recommendations
        slow_domains = sum(1 for r in results if r.validation_time_ms > 3000)
        if slow_domains > total_domains * 0.1:
            recommendations.append(
                "Many domains have slow DNS response times. Consider implementing "
                "more aggressive caching and lower timeout values."
            )
        
        # Caching recommendations
        if self.enable_caching:
            cache_hits = sum(1 for r in results if r.cache_hit)
            cache_rate = cache_hits / max(1, total_domains)
            if cache_rate < 0.3:
                recommendations.append(
                    "Low cache hit rate. Consider increasing cache TTL or "
                    "processing domains in batches to improve caching efficiency."
                )
        
        return recommendations


class BulkDNSValidationTool(BaseTool):
    """
    Tool for bulk DNS validation with advanced batching and rate limiting.
    
    Designed for processing large domain lists with configurable batch sizes,
    rate limiting, and progress tracking.
    """
    
    domains: List[str] = Field(
        ...,
        description="List of domains to validate"
    )
    
    batch_size: int = Field(
        default=50,
        description="Number of domains to process in each batch"
    )
    
    rate_limit_delay: float = Field(
        default=0.5,
        description="Delay between batches in seconds"
    )
    
    dns_timeout: float = Field(
        default=3.0,
        description="DNS query timeout in seconds"
    )
    
    max_workers_per_batch: int = Field(
        default=10,
        description="Maximum workers per batch"
    )
    
    enable_progress_logging: bool = Field(
        default=True,
        description="Enable progress logging for long-running operations"
    )
    
    def run(self) -> Dict[str, Any]:
        """
        Process domains in batches with rate limiting and progress tracking.
        
        Returns:
            Dictionary with batch processing results and summary
        """
        start_time = time.time()
        
        # Deduplicate domains
        unique_domains = list(dict.fromkeys(self.domains))
        total_domains = len(unique_domains)
        
        all_results = []
        batch_summaries = []
        
        # Process in batches
        for i in range(0, total_domains, self.batch_size):
            batch_start = time.time()
            batch_domains = unique_domains[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_domains + self.batch_size - 1) // self.batch_size
            
            # Process batch
            dns_tool = DNSValidationTool(
                domains=batch_domains,
                dns_timeout=self.dns_timeout,
                max_workers=min(self.max_workers_per_batch, len(batch_domains)),
                enable_caching=True
            )
            
            batch_result = dns_tool.run()
            
            batch_time = time.time() - batch_start
            
            # Track batch summary
            batch_summary = {
                'batch_number': batch_num,
                'total_batches': total_batches,
                'domains_processed': len(batch_domains),
                'successful_validations': batch_result['summary']['successful_validations'],
                'domains_with_mx': batch_result['summary']['domains_with_mx_records'],
                'domains_with_errors': batch_result['summary']['domains_with_errors'],
                'processing_time_seconds': batch_time,
                'domains_per_second': len(batch_domains) / max(0.001, batch_time)
            }
            
            batch_summaries.append(batch_summary)
            all_results.extend(batch_result['results'])
            
            # Progress logging
            if self.enable_progress_logging:
                success_rate = batch_summary['successful_validations'] / len(batch_domains)
                mx_rate = batch_summary['domains_with_mx'] / len(batch_domains)
                
                self.logger.info(
                    f"Batch {batch_num}/{total_batches}: {len(batch_domains)} domains, "
                    f"{success_rate:.1%} success, {mx_rate:.1%} with MX, "
                    f"{batch_time:.1f}s"
                )
            
            # Rate limiting
            if i + self.batch_size < total_domains and self.rate_limit_delay > 0:
                time.sleep(self.rate_limit_delay)
        
        # Calculate final statistics
        total_time = time.time() - start_time
        successful_validations = sum(1 for r in all_results if not r.get('error'))
        domains_with_mx = sum(1 for r in all_results if r.get('has_mx_record', False))
        
        return {
            'summary': {
                'total_domains': len(self.domains),
                'unique_domains': total_domains,
                'successful_validations': successful_validations,
                'domains_with_mx_records': domains_with_mx,
                'success_rate': successful_validations / max(1, total_domains),
                'mx_record_rate': domains_with_mx / max(1, total_domains),
                'total_processing_time_seconds': total_time,
                'average_domains_per_second': total_domains / max(0.001, total_time),
                'total_batches': len(batch_summaries)
            },
            'batch_summaries': batch_summaries,
            'all_results': all_results,
            'valid_domains': [r for r in all_results if r.get('has_mx_record', False) and not r.get('error')],
            'invalid_domains': [r for r in all_results if not r.get('has_mx_record', False) or r.get('error')],
            'performance_analysis': {
                'fastest_batch': min(batch_summaries, key=lambda x: x['processing_time_seconds']) if batch_summaries else None,
                'slowest_batch': max(batch_summaries, key=lambda x: x['processing_time_seconds']) if batch_summaries else None,
                'average_batch_time': sum(b['processing_time_seconds'] for b in batch_summaries) / max(1, len(batch_summaries))
            },
            'configuration': {
                'batch_size': self.batch_size,
                'rate_limit_delay': self.rate_limit_delay,
                'dns_timeout': self.dns_timeout,
                'max_workers_per_batch': self.max_workers_per_batch
            }
        }