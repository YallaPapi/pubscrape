"""
Crawl Scheduler Tool

Tool for managing crawl queues, prioritization, and scheduling
with robots.txt compliance and polite delays.
"""

import logging
import time
import heapq
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

try:
    from agency_swarm.tools import BaseTool
    AGENCY_SWARM_AVAILABLE = True
except ImportError:
    AGENCY_SWARM_AVAILABLE = False
    class BaseTool:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

from pydantic import Field

# Import crawl policy components
import sys
import os
sys.path.append(os.path.dirname(__file__))

try:
    from robots_compliance_tool import CrawlPolicyManager, CrawlPolicy
except ImportError:
    CrawlPolicyManager = None
    CrawlPolicy = None


class SchedulePriority(Enum):
    """Priority levels for scheduled crawl tasks"""
    CRITICAL = 1    # Contact, about pages
    HIGH = 2        # Team, services pages
    MEDIUM = 3      # General content pages
    LOW = 4         # Footer, legal pages
    BACKGROUND = 5  # Discovery/exploration


@dataclass
class ScheduledCrawlTask:
    """Represents a scheduled crawl task with priority"""
    url: str
    domain: str
    priority: SchedulePriority
    page_type: str = "unknown"
    confidence_score: float = 0.0
    scheduled_time: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    discovered_from: Optional[str] = None
    
    def __lt__(self, other):
        """Enable priority queue ordering"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # Secondary sort by confidence score (higher is better)
        return self.confidence_score > other.confidence_score
    
    @property
    def is_high_priority(self) -> bool:
        """Check if this is a high priority task"""
        return self.priority in [SchedulePriority.CRITICAL, SchedulePriority.HIGH]
    
    @property
    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return self.retry_count < self.max_retries


@dataclass
class CrawlScheduleMetrics:
    """Metrics for crawl scheduling"""
    total_tasks_scheduled: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_skipped: int = 0
    high_priority_completed: int = 0
    avg_task_duration_seconds: float = 0.0
    domains_scheduled: Set[str] = field(default_factory=set)
    page_types_discovered: Dict[str, int] = field(default_factory=dict)


class CrawlScheduler:
    """
    Scheduler for managing crawl tasks with priority queues and policy compliance.
    
    This class handles the ordering and scheduling of crawl tasks, ensuring
    compliance with robots.txt policies and implementing polite delays.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = self._setup_logging()
        
        # Priority queues for different domains
        self.task_queues: Dict[str, List[ScheduledCrawlTask]] = {}
        self.completed_tasks: List[ScheduledCrawlTask] = []
        self.failed_tasks: List[ScheduledCrawlTask] = []
        
        # Policy manager for robots.txt compliance
        if CrawlPolicyManager:
            self.policy_manager = CrawlPolicyManager(self.config.get("policy_manager", {}))
        else:
            self.policy_manager = None
            self.logger.warning("CrawlPolicyManager not available")
        
        # Scheduling configuration
        self.max_concurrent_domains = self.config.get("max_concurrent_domains", 5)
        self.default_priority = SchedulePriority.MEDIUM
        self.respect_domain_limits = self.config.get("respect_domain_limits", True)
        
        # Metrics
        self.metrics = CrawlScheduleMetrics()
        
        self.logger.info("CrawlScheduler initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the scheduler"""
        logger = logging.getLogger(f"{__name__}.CrawlScheduler")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(self.config.get("log_level", logging.INFO))
        
        return logger
    
    def schedule_task(self, url: str, page_type: str = "unknown",
                     confidence_score: float = 0.0, 
                     priority: Optional[SchedulePriority] = None,
                     discovered_from: Optional[str] = None) -> bool:
        """
        Schedule a new crawl task.
        
        Args:
            url: URL to crawl
            page_type: Type of page (contact, about, etc.)
            confidence_score: Confidence in page type classification
            priority: Optional explicit priority
            discovered_from: URL where this link was discovered
            
        Returns:
            True if task was scheduled, False if rejected
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Determine priority
            if priority is None:
                priority = self._determine_priority(page_type, confidence_score)
            
            # Check if we should schedule this task
            if not self._should_schedule_task(url, domain, priority):
                return False
            
            # Create scheduled task
            task = ScheduledCrawlTask(
                url=url,
                domain=domain,
                priority=priority,
                page_type=page_type,
                confidence_score=confidence_score,
                discovered_from=discovered_from
            )
            
            # Add to appropriate queue
            if domain not in self.task_queues:
                self.task_queues[domain] = []
            
            heapq.heappush(self.task_queues[domain], task)
            
            # Update metrics
            self.metrics.total_tasks_scheduled += 1
            self.metrics.domains_scheduled.add(domain)
            self.metrics.page_types_discovered[page_type] = (
                self.metrics.page_types_discovered.get(page_type, 0) + 1
            )
            
            self.logger.debug(f"Scheduled task: {url} (priority: {priority.name}, "
                             f"type: {page_type}, confidence: {confidence_score:.2f})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error scheduling task for {url}: {e}")
            return False
    
    def _determine_priority(self, page_type: str, confidence_score: float) -> SchedulePriority:
        """Determine priority based on page type and confidence"""
        page_type_lower = page_type.lower()
        
        # Critical priority pages
        if page_type_lower in ['contact', 'contact-us']:
            return SchedulePriority.CRITICAL
        
        # High priority pages
        if page_type_lower in ['about', 'team', 'staff', 'services']:
            return SchedulePriority.HIGH
        
        # Medium priority pages
        if page_type_lower in ['home', 'sitemap', 'careers', 'news']:
            return SchedulePriority.MEDIUM
        
        # Low priority pages
        if page_type_lower in ['privacy', 'legal', 'terms', 'footer']:
            return SchedulePriority.LOW
        
        # Unknown pages - priority based on confidence
        if confidence_score >= 0.7:
            return SchedulePriority.MEDIUM
        elif confidence_score >= 0.4:
            return SchedulePriority.LOW
        else:
            return SchedulePriority.BACKGROUND
    
    def _should_schedule_task(self, url: str, domain: str, priority: SchedulePriority) -> bool:
        """Check if a task should be scheduled"""
        # Check for duplicates
        if domain in self.task_queues:
            existing_urls = {task.url for task in self.task_queues[domain]}
            if url in existing_urls:
                self.logger.debug(f"Duplicate URL skipped: {url}")
                return False
        
        # Check completed tasks
        completed_urls = {task.url for task in self.completed_tasks}
        if url in completed_urls:
            self.logger.debug(f"Already completed URL skipped: {url}")
            return False
        
        # Check domain limits if policy manager is available
        if self.policy_manager and self.respect_domain_limits:
            try:
                policy = self.policy_manager.get_or_create_policy(domain)
                if policy.request_count >= policy.max_pages:
                    self.logger.debug(f"Domain limit reached for {domain}")
                    return False
            except Exception as e:
                self.logger.warning(f"Error checking domain limits for {domain}: {e}")
        
        # Check maximum concurrent domains
        if len(self.task_queues) >= self.max_concurrent_domains and domain not in self.task_queues:
            # Only allow if this is a high priority task
            if priority not in [SchedulePriority.CRITICAL, SchedulePriority.HIGH]:
                self.logger.debug(f"Max concurrent domains reached, rejecting {url}")
                return False
        
        return True
    
    def get_next_task(self) -> Optional[ScheduledCrawlTask]:
        """
        Get the next task to execute based on priority and policies.
        
        Returns:
            Next ScheduledCrawlTask or None if no tasks available
        """
        if not self.task_queues:
            return None
        
        # Find the highest priority task across all domains
        best_task = None
        best_domain = None
        
        for domain, queue in self.task_queues.items():
            if not queue:
                continue
            
            # Check if we can crawl from this domain now
            if self.policy_manager:
                try:
                    policy = self.policy_manager.get_or_create_policy(domain)
                    is_allowed, reason = self.policy_manager.is_crawl_allowed(queue[0].url, policy)
                    if not is_allowed:
                        self.logger.debug(f"Task not allowed for {domain}: {reason}")
                        continue
                except Exception as e:
                    self.logger.warning(f"Error checking crawl permission for {domain}: {e}")
                    continue
            
            # Compare with current best task
            if best_task is None or queue[0] < best_task:
                best_task = queue[0]
                best_domain = domain
        
        if best_task and best_domain:
            # Remove task from queue
            heapq.heappop(self.task_queues[best_domain])
            
            # Clean up empty queues
            if not self.task_queues[best_domain]:
                del self.task_queues[best_domain]
            
            self.logger.debug(f"Next task selected: {best_task.url} "
                             f"(priority: {best_task.priority.name})")
            
            return best_task
        
        return None
    
    def mark_task_completed(self, task: ScheduledCrawlTask, success: bool = True,
                           processing_time: Optional[float] = None):
        """
        Mark a task as completed and update metrics.
        
        Args:
            task: Completed task
            success: Whether the task completed successfully
            processing_time: Time taken to complete the task
        """
        if success:
            self.completed_tasks.append(task)
            self.metrics.tasks_completed += 1
            
            if task.is_high_priority:
                self.metrics.high_priority_completed += 1
        else:
            task.retry_count += 1
            
            if task.can_retry:
                # Reschedule with lower priority
                if task.priority != SchedulePriority.BACKGROUND:
                    task.priority = SchedulePriority(min(task.priority.value + 1, 5))
                
                # Add back to queue
                if task.domain not in self.task_queues:
                    self.task_queues[task.domain] = []
                heapq.heappush(self.task_queues[task.domain], task)
                
                self.logger.debug(f"Rescheduled failed task: {task.url} "
                                 f"(retry {task.retry_count}/{task.max_retries})")
            else:
                self.failed_tasks.append(task)
                self.metrics.tasks_failed += 1
                self.logger.warning(f"Task failed permanently: {task.url}")
        
        # Update processing time metrics
        if processing_time is not None:
            total_time = self.metrics.avg_task_duration_seconds * self.metrics.tasks_completed
            self.metrics.avg_task_duration_seconds = (
                (total_time + processing_time) / (self.metrics.tasks_completed + 1)
            )
        
        # Record request with policy manager
        if self.policy_manager:
            try:
                policy = self.policy_manager.get_or_create_policy(task.domain)
                self.policy_manager.record_request(policy, success)
            except Exception as e:
                self.logger.warning(f"Error recording request for {task.domain}: {e}")
    
    def enforce_crawl_delay(self, domain: str) -> float:
        """
        Enforce crawl delay for a domain.
        
        Args:
            domain: Domain to enforce delay for
            
        Returns:
            Actual delay time applied in seconds
        """
        if not self.policy_manager:
            return 0.0
        
        try:
            policy = self.policy_manager.get_or_create_policy(domain)
            return self.policy_manager.enforce_delay(policy)
        except Exception as e:
            self.logger.warning(f"Error enforcing delay for {domain}: {e}")
            return 1.0  # Default delay
    
    def schedule_multiple_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Schedule multiple tasks in batch.
        
        Args:
            tasks: List of task dictionaries with url, page_type, etc.
            
        Returns:
            Summary of scheduling results
        """
        scheduled_count = 0
        rejected_count = 0
        
        for task_data in tasks:
            url = task_data.get("url")
            if not url:
                rejected_count += 1
                continue
            
            success = self.schedule_task(
                url=url,
                page_type=task_data.get("page_type", "unknown"),
                confidence_score=task_data.get("confidence_score", 0.0),
                priority=task_data.get("priority"),
                discovered_from=task_data.get("discovered_from")
            )
            
            if success:
                scheduled_count += 1
            else:
                rejected_count += 1
        
        self.logger.info(f"Batch scheduling completed: {scheduled_count} scheduled, "
                        f"{rejected_count} rejected")
        
        return {
            "total_tasks": len(tasks),
            "scheduled": scheduled_count,
            "rejected": rejected_count,
            "success_rate": (scheduled_count / len(tasks)) * 100 if tasks else 0
        }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current status of all task queues"""
        total_pending = sum(len(queue) for queue in self.task_queues.values())
        
        domain_status = {}
        for domain, queue in self.task_queues.items():
            if queue:
                priority_counts = {}
                for task in queue:
                    priority_name = task.priority.name
                    priority_counts[priority_name] = priority_counts.get(priority_name, 0) + 1
                
                domain_status[domain] = {
                    "pending_tasks": len(queue),
                    "next_priority": queue[0].priority.name,
                    "next_url": queue[0].url,
                    "priority_distribution": priority_counts
                }
        
        return {
            "total_pending_tasks": total_pending,
            "active_domains": len(self.task_queues),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "domain_queues": domain_status,
            "metrics": {
                "total_scheduled": self.metrics.total_tasks_scheduled,
                "completion_rate": (
                    (self.metrics.tasks_completed / self.metrics.total_tasks_scheduled) * 100
                    if self.metrics.total_tasks_scheduled > 0 else 0
                ),
                "high_priority_completed": self.metrics.high_priority_completed,
                "avg_task_duration": self.metrics.avg_task_duration_seconds,
                "unique_domains": len(self.metrics.domains_scheduled),
                "page_types_found": dict(self.metrics.page_types_discovered)
            }
        }
    
    def clear_completed_tasks(self, keep_count: int = 100):
        """Clear old completed tasks to manage memory"""
        if len(self.completed_tasks) > keep_count:
            self.completed_tasks = self.completed_tasks[-keep_count:]
        
        if len(self.failed_tasks) > keep_count:
            self.failed_tasks = self.failed_tasks[-keep_count:]


class CrawlSchedulerTool(BaseTool):
    """
    Tool for managing crawl scheduling and task prioritization.
    
    This tool provides an interface to the CrawlScheduler for
    scheduling tasks, getting next tasks, and managing queues.
    """
    
    operation: str = Field(
        ...,
        description="Operation to perform: 'schedule_task', 'get_next_task', 'get_status', 'schedule_batch'"
    )
    
    url: Optional[str] = Field(
        None,
        description="URL to schedule (for schedule_task operation)"
    )
    
    page_type: str = Field(
        "unknown",
        description="Type of page for the URL"
    )
    
    confidence_score: float = Field(
        0.0,
        description="Confidence score for page type classification"
    )
    
    priority: Optional[str] = Field(
        None,
        description="Explicit priority: CRITICAL, HIGH, MEDIUM, LOW, BACKGROUND"
    )
    
    discovered_from: Optional[str] = Field(
        None,
        description="URL where this link was discovered"
    )
    
    tasks_batch: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Batch of tasks to schedule (for schedule_batch operation)"
    )
    
    max_concurrent_domains: int = Field(
        5,
        description="Maximum number of concurrent domains to manage"
    )
    
    respect_robots: bool = Field(
        True,
        description="Whether to respect robots.txt policies"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scheduler = None
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the tool"""
        logger = logging.getLogger(f"{__name__}.CrawlSchedulerTool")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _initialize_scheduler(self) -> bool:
        """Initialize the crawl scheduler"""
        if self.scheduler is None:
            try:
                config = {
                    "max_concurrent_domains": self.max_concurrent_domains,
                    "respect_domain_limits": self.respect_robots,
                    "policy_manager": {
                        "respect_robots": self.respect_robots
                    }
                }
                self.scheduler = CrawlScheduler(config)
                return True
            except Exception as e:
                self.logger.error(f"Failed to initialize scheduler: {e}")
                return False
        
        return True
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the crawl scheduling operation.
        
        Returns:
            Dictionary containing operation results
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting crawl scheduler operation: {self.operation}")
            
            # Initialize scheduler
            if not self._initialize_scheduler():
                return {
                    "success": False,
                    "error": "Failed to initialize scheduler",
                    "operation": self.operation
                }
            
            if self.operation == "schedule_task":
                return self._schedule_task_operation(start_time)
            
            elif self.operation == "get_next_task":
                return self._get_next_task_operation(start_time)
            
            elif self.operation == "get_status":
                return self._get_status_operation(start_time)
            
            elif self.operation == "schedule_batch":
                return self._schedule_batch_operation(start_time)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {self.operation}",
                    "operation": self.operation,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
        except Exception as e:
            self.logger.error(f"Error during crawl scheduler operation: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": self.operation,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _schedule_task_operation(self, start_time: float) -> Dict[str, Any]:
        """Schedule a single task"""
        if not self.url:
            return {
                "success": False,
                "error": "No URL provided for scheduling",
                "operation": "schedule_task",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            # Convert priority string to enum
            priority_enum = None
            if self.priority:
                try:
                    priority_enum = SchedulePriority[self.priority.upper()]
                except KeyError:
                    self.logger.warning(f"Invalid priority: {self.priority}")
            
            success = self.scheduler.schedule_task(
                url=self.url,
                page_type=self.page_type,
                confidence_score=self.confidence_score,
                priority=priority_enum,
                discovered_from=self.discovered_from
            )
            
            queue_status = self.scheduler.get_queue_status()
            
            return {
                "success": success,
                "operation": "schedule_task",
                "url": self.url,
                "page_type": self.page_type,
                "priority": self.priority or "auto-determined",
                "scheduled": success,
                "queue_status": queue_status,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "schedule_task",
                "url": self.url,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _get_next_task_operation(self, start_time: float) -> Dict[str, Any]:
        """Get the next task to execute"""
        try:
            next_task = self.scheduler.get_next_task()
            
            if next_task:
                # Enforce crawl delay
                delay_applied = self.scheduler.enforce_crawl_delay(next_task.domain)
                
                return {
                    "success": True,
                    "operation": "get_next_task",
                    "has_task": True,
                    "task": {
                        "url": next_task.url,
                        "domain": next_task.domain,
                        "priority": next_task.priority.name,
                        "page_type": next_task.page_type,
                        "confidence_score": next_task.confidence_score,
                        "retry_count": next_task.retry_count,
                        "discovered_from": next_task.discovered_from
                    },
                    "delay_applied_seconds": delay_applied,
                    "queue_status": self.scheduler.get_queue_status(),
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
            else:
                return {
                    "success": True,
                    "operation": "get_next_task",
                    "has_task": False,
                    "message": "No tasks available in queue",
                    "queue_status": self.scheduler.get_queue_status(),
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "get_next_task",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _get_status_operation(self, start_time: float) -> Dict[str, Any]:
        """Get scheduler status"""
        try:
            queue_status = self.scheduler.get_queue_status()
            
            return {
                "success": True,
                "operation": "get_status",
                "scheduler_status": queue_status,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "get_status",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _schedule_batch_operation(self, start_time: float) -> Dict[str, Any]:
        """Schedule a batch of tasks"""
        if not self.tasks_batch:
            return {
                "success": False,
                "error": "No tasks provided for batch scheduling",
                "operation": "schedule_batch",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            batch_result = self.scheduler.schedule_multiple_tasks(self.tasks_batch)
            queue_status = self.scheduler.get_queue_status()
            
            return {
                "success": True,
                "operation": "schedule_batch",
                "batch_result": batch_result,
                "queue_status": queue_status,
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": "schedule_batch",
                "processing_time_ms": (time.time() - start_time) * 1000
            }


if __name__ == "__main__":
    # Test the crawl scheduler tool
    print("Testing CrawlSchedulerTool...")
    
    # Test task scheduling
    tool = CrawlSchedulerTool(
        operation="schedule_task",
        url="https://example.com/contact",
        page_type="contact",
        confidence_score=0.9,
        priority="CRITICAL"
    )
    
    result = tool.run()
    print(f"Task scheduling result: {result.get('success', False)}")
    
    # Test getting next task
    tool = CrawlSchedulerTool(operation="get_next_task")
    result = tool.run()
    print(f"Next task available: {result.get('has_task', False)}")