"""
Session Orchestration and Load Balancing System
Manages parallel browser sessions with intelligent load balancing,
resource allocation, and throughput optimization for high-volume scraping.
"""

import asyncio
import threading
import time
import queue
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import logging
import json
from concurrent.futures import ThreadPoolExecutor, Future
import random

from .memory_manager import ResourceManager, ResourcePoolConfig, get_resource_manager
from .performance_monitor import PerformanceMonitor, get_performance_monitor

logger = logging.getLogger(__name__)

class SessionState(Enum):
    """States of a scraping session"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"

@dataclass
class ScrapingTask:
    """Individual scraping task"""
    task_id: str
    platform: str  # 'bing', 'google'
    query: str
    location: str = ""
    priority: int = 1  # 1=low, 5=high
    max_results: int = 1000
    timeout_minutes: int = 30
    retry_count: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    assigned_session: Optional[str] = None
    results: List[Dict] = field(default_factory=list)
    status: str = "pending"
    error_message: Optional[str] = None

@dataclass
class SessionInfo:
    """Information about a browser session"""
    session_id: str
    state: SessionState
    created_at: datetime
    last_activity: datetime
    assigned_tasks: List[str] = field(default_factory=list)
    completed_tasks: int = 0
    failed_tasks: int = 0
    leads_extracted: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    platform_affinity: str = ""  # Preferred platform
    error_count: int = 0
    throughput_score: float = 1.0
    detection_rate: float = 0.0

class LoadBalancer:
    """Intelligent load balancer for session assignment"""
    
    def __init__(self, max_concurrent_sessions: int = 5):
        self.max_concurrent_sessions = max_concurrent_sessions
        self.session_weights: Dict[str, float] = {}
        self.platform_distribution = defaultdict(int)
        self.lock = threading.RLock()
        
    def assign_task(self, task: ScrapingTask, available_sessions: Dict[str, SessionInfo]) -> Optional[str]:
        """Assign task to best available session"""
        with self.lock:
            if not available_sessions:
                return None
            
            # Filter sessions by state and capacity
            eligible_sessions = [
                (session_id, info) for session_id, info in available_sessions.items()
                if info.state in [SessionState.IDLE, SessionState.RUNNING] and
                len(info.assigned_tasks) < 3  # Max 3 tasks per session
            ]
            
            if not eligible_sessions:
                return None
            
            # Score sessions based on multiple factors
            scored_sessions = []
            for session_id, info in eligible_sessions:
                score = self._calculate_session_score(task, info)
                scored_sessions.append((session_id, info, score))
            
            # Sort by score (higher is better)
            scored_sessions.sort(key=lambda x: x[2], reverse=True)
            
            # Select best session
            best_session_id = scored_sessions[0][0]
            
            # Update distribution tracking
            self.platform_distribution[task.platform] += 1
            
            logger.debug(f"Assigned task {task.task_id} to session {best_session_id}")
            return best_session_id
    
    def _calculate_session_score(self, task: ScrapingTask, session: SessionInfo) -> float:
        """Calculate session fitness score for a task"""
        score = 1.0
        
        # Platform affinity bonus
        if session.platform_affinity == task.platform:
            score += 0.5
        
        # Performance factors
        score *= session.throughput_score
        
        # Resource usage penalty (prefer less loaded sessions)
        memory_penalty = min(session.memory_usage_mb / 1000, 1.0)  # 0-1 based on 1GB
        cpu_penalty = session.cpu_usage_percent / 100
        score *= (1 - memory_penalty * 0.3 - cpu_penalty * 0.2)
        
        # Error rate penalty
        if session.completed_tasks > 0:
            error_rate = session.failed_tasks / session.completed_tasks
            score *= (1 - error_rate * 0.4)
        
        # Detection rate penalty
        score *= (1 - session.detection_rate * 0.6)
        
        # Load balancing - prefer less loaded sessions
        current_tasks = len(session.assigned_tasks)
        if current_tasks == 0:
            score += 0.3  # Idle session bonus
        elif current_tasks >= 2:
            score -= 0.2  # High load penalty
        
        # Priority matching
        if task.priority >= 4:  # High priority tasks
            # Prefer sessions with better track record
            if session.throughput_score > 1.2:
                score += 0.4
        
        return max(score, 0.1)  # Minimum score
    
    def update_session_performance(self, session_id: str, throughput_score: float, 
                                 detection_rate: float, memory_usage: float):
        """Update session performance metrics for scoring"""
        with self.lock:
            # Update session weight based on performance
            performance_weight = throughput_score * (1 - detection_rate)
            memory_factor = max(0.1, 1 - memory_usage / 2000)  # Penalty for high memory
            
            self.session_weights[session_id] = performance_weight * memory_factor
    
    def get_load_distribution(self) -> Dict[str, Any]:
        """Get current load distribution statistics"""
        with self.lock:
            total_tasks = sum(self.platform_distribution.values())
            
            return {
                'platform_distribution': dict(self.platform_distribution),
                'total_tasks': total_tasks,
                'distribution_percentages': {
                    platform: (count / max(total_tasks, 1)) * 100
                    for platform, count in self.platform_distribution.items()
                },
                'session_weights': dict(self.session_weights)
            }

class SessionOrchestrator:
    """Main orchestrator for managing parallel browser sessions"""
    
    def __init__(self, config: Optional[ResourcePoolConfig] = None):
        self.config = config or ResourcePoolConfig()
        self.resource_manager = get_resource_manager(self.config)
        self.performance_monitor = get_performance_monitor()
        self.load_balancer = LoadBalancer(self.config.max_sessions)
        
        # Session management
        self.sessions: Dict[str, SessionInfo] = {}
        self.task_queue = queue.PriorityQueue()
        self.completed_tasks: Dict[str, ScrapingTask] = {}
        self.failed_tasks: Dict[str, ScrapingTask] = {}
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_sessions)
        self.running = False
        self.orchestration_thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()
        
        # Metrics
        self.orchestration_metrics = {
            'total_tasks_processed': 0,
            'total_leads_extracted': 0,
            'average_session_duration': 0.0,
            'peak_concurrent_sessions': 0,
            'total_errors': 0,
            'start_time': datetime.now()
        }
        
    def start_orchestration(self):
        """Start the session orchestration system"""
        if not self.running:
            self.running = True
            
            # Start performance monitoring
            self.performance_monitor.start_monitoring()
            
            # Start orchestration thread
            self.orchestration_thread = threading.Thread(target=self._orchestration_loop, daemon=True)
            self.orchestration_thread.start()
            
            logger.info(f"Session orchestration started with {self.config.max_sessions} max sessions")
    
    def stop_orchestration(self):
        """Stop the orchestration system"""
        if self.running:
            self.running = False
            
            # Stop orchestration thread
            if self.orchestration_thread:
                self.orchestration_thread.join(timeout=10)
            
            # Cleanup all sessions
            with self.lock:
                for session_id in list(self.sessions.keys()):
                    self._cleanup_session(session_id)
            
            # Shutdown executor
            self.executor.shutdown(wait=True)
            
            # Stop performance monitoring
            self.performance_monitor.stop_monitoring()
            
            logger.info("Session orchestration stopped")
    
    def submit_task(self, platform: str, query: str, location: str = "", 
                   priority: int = 1, max_results: int = 1000) -> str:
        """Submit a new scraping task"""
        task_id = f"task_{int(time.time())}_{random.randint(1000, 9999)}"
        
        task = ScrapingTask(
            task_id=task_id,
            platform=platform.lower(),
            query=query,
            location=location,
            priority=priority,
            max_results=max_results
        )
        
        # Add to priority queue (higher priority = lower number for queue)
        queue_priority = 5 - task.priority  # Invert priority for queue
        self.task_queue.put((queue_priority, time.time(), task))
        
        logger.info(f"Submitted task {task_id}: {platform} query '{query}' in {location}")
        return task_id
    
    def submit_batch_tasks(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """Submit multiple tasks in batch"""
        task_ids = []
        
        for task_data in tasks:
            task_id = self.submit_task(
                platform=task_data.get('platform', 'bing'),
                query=task_data.get('query', ''),
                location=task_data.get('location', ''),
                priority=task_data.get('priority', 1),
                max_results=task_data.get('max_results', 1000)
            )
            task_ids.append(task_id)
        
        logger.info(f"Submitted batch of {len(tasks)} tasks")
        return task_ids
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        # Check completed tasks
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return {
                'task_id': task_id,
                'status': 'completed',
                'results_count': len(task.results),
                'assigned_session': task.assigned_session,
                'created_at': task.created_at.isoformat(),
                'platform': task.platform,
                'query': task.query,
                'location': task.location
            }
        
        # Check failed tasks
        if task_id in self.failed_tasks:
            task = self.failed_tasks[task_id]
            return {
                'task_id': task_id,
                'status': 'failed',
                'error_message': task.error_message,
                'assigned_session': task.assigned_session,
                'created_at': task.created_at.isoformat(),
                'platform': task.platform,
                'query': task.query,
                'location': task.location
            }
        
        # Check active sessions for running tasks
        with self.lock:
            for session_info in self.sessions.values():
                if task_id in session_info.assigned_tasks:
                    return {
                        'task_id': task_id,
                        'status': 'running',
                        'assigned_session': session_info.session_id,
                        'session_state': session_info.state.value
                    }
        
        return None  # Task not found
    
    def _orchestration_loop(self):
        """Main orchestration loop"""
        logger.info("Starting orchestration loop")
        
        while self.running:
            try:
                # Process pending tasks
                self._process_pending_tasks()
                
                # Monitor session health
                self._monitor_session_health()
                
                # Update load balancer metrics
                self._update_load_balancer_metrics()
                
                # Cleanup completed sessions
                self._cleanup_completed_sessions()
                
                # Sleep between iterations
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Orchestration loop error: {e}")
                time.sleep(10)
        
        logger.info("Orchestration loop ended")
    
    def _process_pending_tasks(self):
        """Process tasks from the queue"""
        processed_count = 0
        max_process_per_iteration = 10
        
        while processed_count < max_process_per_iteration and not self.task_queue.empty():
            try:
                # Get next task
                priority, timestamp, task = self.task_queue.get_nowait()
                
                # Find available session or create new one
                session_id = self._assign_task_to_session(task)
                
                if session_id:
                    # Execute task
                    self._execute_task(session_id, task)
                    processed_count += 1
                else:
                    # No available sessions, put task back
                    self.task_queue.put((priority, timestamp, task))
                    break
                    
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing task: {e}")
    
    def _assign_task_to_session(self, task: ScrapingTask) -> Optional[str]:
        """Assign task to best available session"""
        with self.lock:
            # Try to assign to existing session
            session_id = self.load_balancer.assign_task(task, self.sessions)
            
            if session_id:
                self.sessions[session_id].assigned_tasks.append(task.task_id)
                task.assigned_session = session_id
                return session_id
            
            # Create new session if under limit
            if len(self.sessions) < self.config.max_sessions:
                session_id = self._create_new_session(task.platform)
                if session_id:
                    self.sessions[session_id].assigned_tasks.append(task.task_id)
                    task.assigned_session = session_id
                    return session_id
            
            return None
    
    def _create_new_session(self, platform: str) -> Optional[str]:
        """Create a new browser session"""
        try:
            session_id = f"session_{platform}_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # Create resource manager session
            resource_session = self.resource_manager.create_session(session_id)
            
            # Create performance tracking session
            self.performance_monitor.create_session(session_id, platform)
            
            # Create session info
            session_info = SessionInfo(
                session_id=session_id,
                state=SessionState.IDLE,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                platform_affinity=platform
            )
            
            with self.lock:
                self.sessions[session_id] = session_info
                
                # Update peak concurrent sessions
                current_count = len(self.sessions)
                if current_count > self.orchestration_metrics['peak_concurrent_sessions']:
                    self.orchestration_metrics['peak_concurrent_sessions'] = current_count
            
            logger.info(f"Created new session: {session_id} for platform: {platform}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    def _execute_task(self, session_id: str, task: ScrapingTask):
        """Execute a scraping task in a session"""
        # Submit to thread pool
        future = self.executor.submit(self._run_scraping_task, session_id, task)
        
        # Update session state
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].state = SessionState.RUNNING
                self.sessions[session_id].last_activity = datetime.now()
    
    def _run_scraping_task(self, session_id: str, task: ScrapingTask):
        """Run the actual scraping task"""
        start_time = time.time()
        
        try:
            logger.info(f"Starting task {task.task_id} on session {session_id}")
            
            # Import appropriate scraper
            if task.platform == 'bing':
                from ..scrapers.infinite_scroll_handler import InfiniteScrollHandler
                from ..scrapers.scroll_strategies import ScrollConfig
                
                config = ScrollConfig(
                    max_scroll_iterations=20,
                    strategy_type='adaptive',
                    timeout_seconds=task.timeout_minutes * 60
                )
                
                handler = InfiniteScrollHandler(config)
                session_result = handler.scroll_and_extract_bing_maps(
                    driver=None,  # Will be created by handler
                    query=task.query,
                    location=task.location
                )
                
                task.results = session_result.extracted_businesses[:task.max_results]
                
            elif task.platform == 'google':
                from ..scrapers.infinite_scroll_handler import InfiniteScrollHandler
                from ..scrapers.scroll_strategies import ScrollConfig
                
                config = ScrollConfig(
                    max_scroll_iterations=20,
                    strategy_type='adaptive',
                    timeout_seconds=task.timeout_minutes * 60
                )
                
                handler = InfiniteScrollHandler(config)
                session_result = handler.scroll_and_extract_google_maps(
                    driver=None,  # Will be created by handler
                    query=task.query,
                    location=task.location
                )
                
                task.results = session_result.extracted_businesses[:task.max_results]
            
            else:
                raise ValueError(f"Unsupported platform: {task.platform}")
            
            # Update metrics
            leads_found = len(task.results)
            execution_time = time.time() - start_time
            
            # Update performance tracking
            self.performance_monitor.track_leads_extracted(session_id, leads_found)
            self.performance_monitor.track_request_result(session_id, True, execution_time)
            
            # Update session info
            with self.lock:
                if session_id in self.sessions:
                    session_info = self.sessions[session_id]
                    session_info.completed_tasks += 1
                    session_info.leads_extracted += leads_found
                    session_info.last_activity = datetime.now()
                    session_info.assigned_tasks.remove(task.task_id)
                    
                    # Update throughput score
                    if execution_time > 0:
                        leads_per_second = leads_found / execution_time
                        session_info.throughput_score = min(2.0, leads_per_second / 10)  # Normalize
            
            # Mark task as completed
            task.status = "completed"
            self.completed_tasks[task.task_id] = task
            self.orchestration_metrics['total_tasks_processed'] += 1
            self.orchestration_metrics['total_leads_extracted'] += leads_found
            
            logger.info(f"Task {task.task_id} completed: {leads_found} leads in {execution_time:.1f}s")
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            
            # Update session error count
            with self.lock:
                if session_id in self.sessions:
                    session_info = self.sessions[session_id]
                    session_info.failed_tasks += 1
                    session_info.error_count += 1
                    if task.task_id in session_info.assigned_tasks:
                        session_info.assigned_tasks.remove(task.task_id)
            
            # Track failure
            self.performance_monitor.track_request_result(session_id, False, time.time() - start_time)
            
            # Mark task as failed
            task.status = "failed"
            task.error_message = str(e)
            self.failed_tasks[task.task_id] = task
            self.orchestration_metrics['total_errors'] += 1
            
        finally:
            # Update session state
            with self.lock:
                if session_id in self.sessions:
                    if not self.sessions[session_id].assigned_tasks:
                        self.sessions[session_id].state = SessionState.IDLE
    
    def _monitor_session_health(self):
        """Monitor health of active sessions"""
        with self.lock:
            unhealthy_sessions = []
            
            for session_id, session_info in self.sessions.items():
                # Check for timeout
                inactive_time = datetime.now() - session_info.last_activity
                if inactive_time > timedelta(minutes=self.config.session_timeout_minutes):
                    logger.warning(f"Session {session_id} inactive for {inactive_time}")
                    unhealthy_sessions.append(session_id)
                
                # Check error rate
                total_tasks = session_info.completed_tasks + session_info.failed_tasks
                if total_tasks >= 5:  # Minimum sample size
                    error_rate = session_info.failed_tasks / total_tasks
                    if error_rate > 0.5:  # 50% error rate threshold
                        logger.warning(f"Session {session_id} high error rate: {error_rate:.1%}")
                        unhealthy_sessions.append(session_id)
            
            # Cleanup unhealthy sessions
            for session_id in unhealthy_sessions:
                self._cleanup_session(session_id)
    
    def _cleanup_session(self, session_id: str):
        """Clean up a browser session"""
        try:
            logger.info(f"Cleaning up session: {session_id}")
            
            # End performance tracking
            self.performance_monitor.end_session(session_id)
            
            # End resource management
            self.resource_manager.end_session(session_id)
            
            # Remove from active sessions
            with self.lock:
                if session_id in self.sessions:
                    del self.sessions[session_id]
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
    
    def _cleanup_completed_sessions(self):
        """Clean up idle sessions to free resources"""
        with self.lock:
            idle_sessions = [
                session_id for session_id, info in self.sessions.items()
                if info.state == SessionState.IDLE and not info.assigned_tasks and
                datetime.now() - info.last_activity > timedelta(minutes=10)
            ]
            
            # Keep at least 1 session for quick task processing
            if len(self.sessions) - len(idle_sessions) >= 1:
                for session_id in idle_sessions[:len(idle_sessions)//2]:  # Clean up half
                    self._cleanup_session(session_id)
    
    def _update_load_balancer_metrics(self):
        """Update load balancer with current session performance"""
        with self.lock:
            for session_id, session_info in self.sessions.items():
                # Get current memory usage from resource manager
                system_status = self.resource_manager.get_system_status()
                memory_usage = system_status['memory_metrics']['process_memory_mb']
                
                self.load_balancer.update_session_performance(
                    session_id=session_id,
                    throughput_score=session_info.throughput_score,
                    detection_rate=session_info.detection_rate,
                    memory_usage=memory_usage
                )
    
    def get_orchestration_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestration status"""
        with self.lock:
            runtime = datetime.now() - self.orchestration_metrics['start_time']
            
            # Calculate session statistics
            active_sessions = len([s for s in self.sessions.values() if s.state == SessionState.RUNNING])
            idle_sessions = len([s for s in self.sessions.values() if s.state == SessionState.IDLE])
            total_leads = sum(s.leads_extracted for s in self.sessions.values())
            
            # Calculate throughput
            runtime_hours = runtime.total_seconds() / 3600
            leads_per_hour = total_leads / max(runtime_hours, 1/60)  # At least 1 minute
            
            return {
                'orchestration_metrics': {
                    'runtime_hours': runtime_hours,
                    'total_tasks_processed': self.orchestration_metrics['total_tasks_processed'],
                    'total_leads_extracted': self.orchestration_metrics['total_leads_extracted'],
                    'total_errors': self.orchestration_metrics['total_errors'],
                    'leads_per_hour': leads_per_hour,
                    'peak_concurrent_sessions': self.orchestration_metrics['peak_concurrent_sessions']
                },
                'current_sessions': {
                    'total_sessions': len(self.sessions),
                    'active_sessions': active_sessions,
                    'idle_sessions': idle_sessions,
                    'max_sessions': self.config.max_sessions
                },
                'task_queue': {
                    'pending_tasks': self.task_queue.qsize(),
                    'completed_tasks': len(self.completed_tasks),
                    'failed_tasks': len(self.failed_tasks)
                },
                'load_balancer': self.load_balancer.get_load_distribution(),
                'system_health': self.resource_manager.get_system_status()['system_health']
            }

# Global orchestrator instance
_session_orchestrator: Optional[SessionOrchestrator] = None

def get_session_orchestrator(config: Optional[ResourcePoolConfig] = None) -> SessionOrchestrator:
    """Get global session orchestrator instance"""
    global _session_orchestrator
    if _session_orchestrator is None:
        _session_orchestrator = SessionOrchestrator(config)
    return _session_orchestrator

def shutdown_session_orchestrator():
    """Shutdown global session orchestrator"""
    global _session_orchestrator
    if _session_orchestrator:
        _session_orchestrator.stop_orchestration()
        _session_orchestrator = None

if __name__ == "__main__":
    # Test session orchestration system
    print("Session Orchestration System Test")
    print("=" * 50)
    
    # Test configuration
    config = ResourcePoolConfig(
        max_sessions=3,
        memory_threshold_mb=1500,
        session_timeout_minutes=15
    )
    
    # Create orchestrator
    orchestrator = SessionOrchestrator(config)
    orchestrator.start_orchestration()
    
    try:
        # Submit test tasks
        task_ids = []
        
        # Submit single tasks
        task1 = orchestrator.submit_task("bing", "restaurants", "Miami, FL", priority=3)
        task2 = orchestrator.submit_task("google", "doctors", "New York, NY", priority=2)
        task_ids.extend([task1, task2])
        
        # Submit batch tasks
        batch_tasks = [
            {"platform": "bing", "query": "hotels", "location": "Orlando, FL", "priority": 1},
            {"platform": "google", "query": "gyms", "location": "Los Angeles, CA", "priority": 4}
        ]
        batch_ids = orchestrator.submit_batch_tasks(batch_tasks)
        task_ids.extend(batch_ids)
        
        print(f"Submitted {len(task_ids)} tasks: {task_ids}")
        
        # Monitor progress
        for _ in range(12):  # Monitor for 1 minute
            status = orchestrator.get_orchestration_status()
            print(f"\nStatus Update:")
            print(f"  Active Sessions: {status['current_sessions']['active_sessions']}")
            print(f"  Pending Tasks: {status['task_queue']['pending_tasks']}")
            print(f"  Completed Tasks: {status['task_queue']['completed_tasks']}")
            print(f"  Total Leads: {status['orchestration_metrics']['total_leads_extracted']}")
            print(f"  System Health: {status['system_health']}")
            
            # Check individual task status
            for task_id in task_ids:
                task_status = orchestrator.get_task_status(task_id)
                if task_status:
                    print(f"  Task {task_id}: {task_status['status']}")
            
            time.sleep(5)
        
        print("\nTest completed successfully")
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        orchestrator.stop_orchestration()