"""
Resume and Recovery Manager for VRSEN PubScrape

Provides comprehensive session management, state persistence, and intelligent
recovery capabilities for long-running scraping campaigns.
"""

import os
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import asyncio
import logging
from dataclasses import dataclass, asdict, field
from enum import Enum
import gzip
import shutil


class SessionState(Enum):
    """Session state enumeration"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SessionCheckpoint:
    """Session checkpoint data structure"""
    session_id: str
    timestamp: datetime
    state: SessionState
    progress: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    error_info: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionInfo:
    """Session information"""
    session_id: str
    created_at: datetime
    last_updated: datetime
    state: SessionState
    campaign_config: Dict[str, Any] = field(default_factory=dict)
    total_progress: float = 0.0
    current_step: str = ""
    leads_generated: int = 0
    errors_count: int = 0
    warnings_count: int = 0
    estimated_completion: Optional[datetime] = None
    checkpoints_count: int = 0


class ResumeManager:
    """
    Comprehensive resume and recovery manager for scraping sessions.
    
    Features:
    - Automatic state persistence at configurable intervals
    - Intelligent session recovery with validation
    - Progress tracking and estimation
    - Checkpoint management with compression
    - Session cleanup and archival
    - Cross-session data sharing
    """
    
    def __init__(self, state_dir: Union[str, Path] = "state", 
                 auto_save_interval: int = 300,  # 5 minutes
                 max_session_age_days: int = 7,
                 compression_enabled: bool = True,
                 logger: Optional[logging.Logger] = None):
        
        self.state_dir = Path(state_dir)
        self.auto_save_interval = auto_save_interval
        self.max_session_age_days = max_session_age_days
        self.compression_enabled = compression_enabled
        self.logger = logger or logging.getLogger(__name__)
        
        # Create state directory structure
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir = self.state_dir / "sessions"
        self.checkpoints_dir = self.state_dir / "checkpoints"
        self.archives_dir = self.state_dir / "archives"
        
        for dir_path in [self.sessions_dir, self.checkpoints_dir, self.archives_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Current session tracking
        self.current_session: Optional[SessionInfo] = None
        self.auto_save_task: Optional[asyncio.Task] = None
        self.last_checkpoint: Optional[SessionCheckpoint] = None
        
        # Initialize
        self._cleanup_old_sessions()
        
        self.logger.info(f"Resume manager initialized: {self.state_dir}")
    
    def create_session(self, session_id: str, campaign_config: Dict[str, Any]) -> SessionInfo:
        """
        Create a new session.
        
        Args:
            session_id: Unique session identifier
            campaign_config: Campaign configuration
            
        Returns:
            SessionInfo object
        """
        session = SessionInfo(
            session_id=session_id,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            state=SessionState.INITIALIZED,
            campaign_config=campaign_config
        )
        
        self.current_session = session
        self._save_session_info(session)
        
        self.logger.info(f"Created session: {session_id}")
        return session
    
    def start_session(self, session_id: str) -> bool:
        """
        Start a session and begin auto-save.
        
        Args:
            session_id: Session ID to start
            
        Returns:
            True if started successfully
        """
        try:
            if self.current_session is None:
                session = self.load_session(session_id)
                if not session:
                    self.logger.error(f"Session not found: {session_id}")
                    return False
                self.current_session = session
            
            self.current_session.state = SessionState.RUNNING
            self.current_session.last_updated = datetime.now()
            self._save_session_info(self.current_session)
            
            # Start auto-save task
            if self.auto_save_task is None or self.auto_save_task.done():
                self.auto_save_task = asyncio.create_task(self._auto_save_loop())
            
            self.logger.info(f"Started session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start session {session_id}: {e}")
            return False
    
    def pause_session(self, session_id: str) -> bool:
        """
        Pause a running session.
        
        Args:
            session_id: Session ID to pause
            
        Returns:
            True if paused successfully
        """
        try:
            if self.current_session and self.current_session.session_id == session_id:
                self.current_session.state = SessionState.PAUSED
                self.current_session.last_updated = datetime.now()
                self._save_session_info(self.current_session)
                
                # Stop auto-save
                if self.auto_save_task and not self.auto_save_task.done():
                    self.auto_save_task.cancel()
                
                self.logger.info(f"Paused session: {session_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to pause session {session_id}: {e}")
            return False
    
    def complete_session(self, session_id: str, final_results: Dict[str, Any]) -> bool:
        """
        Mark a session as completed.
        
        Args:
            session_id: Session ID to complete
            final_results: Final session results
            
        Returns:
            True if completed successfully
        """
        try:
            if self.current_session and self.current_session.session_id == session_id:
                self.current_session.state = SessionState.COMPLETED
                self.current_session.total_progress = 100.0
                self.current_session.last_updated = datetime.now()
                
                # Save final checkpoint
                self.save_checkpoint({\n                    \"final_results\": final_results,\n                    \"completion_time\": datetime.now().isoformat(),\n                    \"session_summary\": self._generate_session_summary()\n                })\n                \n                self._save_session_info(self.current_session)\n                \n                # Stop auto-save\n                if self.auto_save_task and not self.auto_save_task.done():\n                    self.auto_save_task.cancel()\n                \n                self.logger.info(f\"Completed session: {session_id}\")\n                return True\n            \n            return False\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to complete session {session_id}: {e}\")\n            return False\n    \n    def fail_session(self, session_id: str, error_info: Dict[str, Any]) -> bool:\n        \"\"\"\n        Mark a session as failed.\n        \n        Args:\n            session_id: Session ID to fail\n            error_info: Error information\n            \n        Returns:\n            True if failed successfully\n        \"\"\"\n        try:\n            if self.current_session and self.current_session.session_id == session_id:\n                self.current_session.state = SessionState.FAILED\n                self.current_session.last_updated = datetime.now()\n                \n                # Save error checkpoint\n                self.save_checkpoint({\n                    \"error_info\": error_info,\n                    \"failure_time\": datetime.now().isoformat(),\n                    \"session_summary\": self._generate_session_summary()\n                })\n                \n                self._save_session_info(self.current_session)\n                \n                # Stop auto-save\n                if self.auto_save_task and not self.auto_save_task.done():\n                    self.auto_save_task.cancel()\n                \n                self.logger.error(f\"Failed session: {session_id}\")\n                return True\n            \n            return False\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to fail session {session_id}: {e}\")\n            return False\n    \n    def save_checkpoint(self, data: Dict[str, Any], \n                       progress_info: Optional[Dict[str, Any]] = None) -> bool:\n        \"\"\"\n        Save a checkpoint with current state.\n        \n        Args:\n            data: Data to save in checkpoint\n            progress_info: Progress information\n            \n        Returns:\n            True if saved successfully\n        \"\"\"\n        try:\n            if not self.current_session:\n                self.logger.warning(\"No active session for checkpoint\")\n                return False\n            \n            checkpoint = SessionCheckpoint(\n                session_id=self.current_session.session_id,\n                timestamp=datetime.now(),\n                state=self.current_session.state,\n                data=data,\n                progress=progress_info or {},\n                metadata={\n                    \"checkpoint_count\": self.current_session.checkpoints_count + 1,\n                    \"leads_generated\": self.current_session.leads_generated,\n                    \"current_step\": self.current_session.current_step\n                }\n            )\n            \n            # Save checkpoint file\n            checkpoint_file = self._get_checkpoint_file(checkpoint.session_id, checkpoint.timestamp)\n            self._save_checkpoint_file(checkpoint, checkpoint_file)\n            \n            # Update session info\n            self.current_session.checkpoints_count += 1\n            self.current_session.last_updated = datetime.now()\n            if progress_info:\n                self.current_session.total_progress = progress_info.get(\"total_progress\", 0.0)\n                self.current_session.current_step = progress_info.get(\"current_step\", \"\")\n            \n            self._save_session_info(self.current_session)\n            self.last_checkpoint = checkpoint\n            \n            self.logger.debug(f\"Saved checkpoint for session: {checkpoint.session_id}\")\n            return True\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to save checkpoint: {e}\")\n            return False\n    \n    def load_session(self, session_id: str) -> Optional[SessionInfo]:\n        \"\"\"\n        Load session information.\n        \n        Args:\n            session_id: Session ID to load\n            \n        Returns:\n            SessionInfo object or None if not found\n        \"\"\"\n        try:\n            session_file = self.sessions_dir / f\"{session_id}.json\"\n            if not session_file.exists():\n                return None\n            \n            with open(session_file, 'r') as f:\n                data = json.load(f)\n            \n            # Convert datetime strings\n            data['created_at'] = datetime.fromisoformat(data['created_at'])\n            data['last_updated'] = datetime.fromisoformat(data['last_updated'])\n            if data.get('estimated_completion'):\n                data['estimated_completion'] = datetime.fromisoformat(data['estimated_completion'])\n            \n            # Convert state enum\n            data['state'] = SessionState(data['state'])\n            \n            session = SessionInfo(**data)\n            self.logger.info(f\"Loaded session: {session_id}\")\n            return session\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to load session {session_id}: {e}\")\n            return None\n    \n    def load_latest_checkpoint(self, session_id: str) -> Optional[SessionCheckpoint]:\n        \"\"\"\n        Load the latest checkpoint for a session.\n        \n        Args:\n            session_id: Session ID\n            \n        Returns:\n            Latest SessionCheckpoint or None\n        \"\"\"\n        try:\n            # Find all checkpoint files for session\n            checkpoint_pattern = f\"{session_id}_*.pkl\"\n            checkpoint_files = list(self.checkpoints_dir.glob(checkpoint_pattern))\n            \n            if not checkpoint_files:\n                self.logger.warning(f\"No checkpoints found for session: {session_id}\")\n                return None\n            \n            # Sort by timestamp (newest first)\n            checkpoint_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)\n            latest_file = checkpoint_files[0]\n            \n            return self._load_checkpoint_file(latest_file)\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to load latest checkpoint for {session_id}: {e}\")\n            return None\n    \n    def can_resume(self, session_id: str) -> bool:\n        \"\"\"\n        Check if a session can be resumed.\n        \n        Args:\n            session_id: Session ID to check\n            \n        Returns:\n            True if session can be resumed\n        \"\"\"\n        try:\n            session = self.load_session(session_id)\n            if not session:\n                return False\n            \n            # Check if session is in resumable state\n            resumable_states = [SessionState.PAUSED, SessionState.FAILED, SessionState.RUNNING]\n            if session.state not in resumable_states:\n                return False\n            \n            # Check if session is not too old\n            age = datetime.now() - session.last_updated\n            if age.days > self.max_session_age_days:\n                self.logger.warning(f\"Session {session_id} is too old to resume ({age.days} days)\")\n                return False\n            \n            # Check if checkpoints exist\n            checkpoint = self.load_latest_checkpoint(session_id)\n            if not checkpoint:\n                self.logger.warning(f\"No valid checkpoints for session: {session_id}\")\n                return False\n            \n            return True\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to check resume capability for {session_id}: {e}\")\n            return False\n    \n    def list_sessions(self, include_completed: bool = False) -> List[SessionInfo]:\n        \"\"\"\n        List all available sessions.\n        \n        Args:\n            include_completed: Include completed sessions\n            \n        Returns:\n            List of SessionInfo objects\n        \"\"\"\n        sessions = []\n        \n        try:\n            for session_file in self.sessions_dir.glob(\"*.json\"):\n                session_id = session_file.stem\n                session = self.load_session(session_id)\n                \n                if session:\n                    if include_completed or session.state != SessionState.COMPLETED:\n                        sessions.append(session)\n            \n            # Sort by last updated (newest first)\n            sessions.sort(key=lambda x: x.last_updated, reverse=True)\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to list sessions: {e}\")\n        \n        return sessions\n    \n    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:\n        \"\"\"\n        Get comprehensive session status.\n        \n        Args:\n            session_id: Session ID\n            \n        Returns:\n            Status dictionary or None\n        \"\"\"\n        try:\n            session = self.load_session(session_id)\n            if not session:\n                return None\n            \n            checkpoint = self.load_latest_checkpoint(session_id)\n            \n            status = {\n                \"session_id\": session.session_id,\n                \"state\": session.state.value,\n                \"created_at\": session.created_at.isoformat(),\n                \"last_updated\": session.last_updated.isoformat(),\n                \"total_progress\": session.total_progress,\n                \"current_step\": session.current_step,\n                \"leads_generated\": session.leads_generated,\n                \"errors_count\": session.errors_count,\n                \"warnings_count\": session.warnings_count,\n                \"checkpoints_count\": session.checkpoints_count,\n                \"can_resume\": self.can_resume(session_id),\n                \"runtime_hours\": (session.last_updated - session.created_at).total_seconds() / 3600\n            }\n            \n            if checkpoint:\n                status[\"last_checkpoint\"] = checkpoint.timestamp.isoformat()\n                status[\"checkpoint_data_size\"] = len(str(checkpoint.data))\n            \n            if session.estimated_completion:\n                status[\"estimated_completion\"] = session.estimated_completion.isoformat()\n                remaining = session.estimated_completion - datetime.now()\n                status[\"estimated_remaining_hours\"] = max(0, remaining.total_seconds() / 3600)\n            \n            return status\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to get session status for {session_id}: {e}\")\n            return None\n    \n    def cleanup_session(self, session_id: str, archive: bool = True) -> bool:\n        \"\"\"\n        Clean up session files.\n        \n        Args:\n            session_id: Session ID to clean up\n            archive: Whether to archive instead of delete\n            \n        Returns:\n            True if cleaned up successfully\n        \"\"\"\n        try:\n            if archive:\n                self._archive_session(session_id)\n            else:\n                # Delete session file\n                session_file = self.sessions_dir / f\"{session_id}.json\"\n                if session_file.exists():\n                    session_file.unlink()\n                \n                # Delete checkpoint files\n                checkpoint_pattern = f\"{session_id}_*.pkl\"\n                for checkpoint_file in self.checkpoints_dir.glob(checkpoint_pattern):\n                    checkpoint_file.unlink()\n            \n            self.logger.info(f\"Cleaned up session: {session_id} (archived: {archive})\")\n            return True\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to cleanup session {session_id}: {e}\")\n            return False\n    \n    def save_state(self) -> bool:\n        \"\"\"\n        Save current state (called during shutdown).\n        \n        Returns:\n            True if saved successfully\n        \"\"\"\n        try:\n            if self.current_session:\n                # Save final checkpoint if session is running\n                if self.current_session.state == SessionState.RUNNING:\n                    self.save_checkpoint({\n                        \"shutdown_save\": True,\n                        \"timestamp\": datetime.now().isoformat()\n                    })\n                \n                self._save_session_info(self.current_session)\n            \n            # Cancel auto-save task\n            if self.auto_save_task and not self.auto_save_task.done():\n                self.auto_save_task.cancel()\n            \n            self.logger.info(\"State saved successfully\")\n            return True\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to save state: {e}\")\n            return False\n    \n    def update_progress(self, progress: float, current_step: str = \"\", \n                       leads_count: int = 0, estimated_completion: Optional[datetime] = None):\n        \"\"\"\n        Update session progress information.\n        \n        Args:\n            progress: Progress percentage (0-100)\n            current_step: Current step description\n            leads_count: Number of leads generated\n            estimated_completion: Estimated completion time\n        \"\"\"\n        if self.current_session:\n            self.current_session.total_progress = progress\n            self.current_session.current_step = current_step\n            self.current_session.leads_generated = leads_count\n            if estimated_completion:\n                self.current_session.estimated_completion = estimated_completion\n            self.current_session.last_updated = datetime.now()\n    \n    # Private methods\n    \n    async def _auto_save_loop(self):\n        \"\"\"Auto-save loop for periodic checkpoints\"\"\"\n        try:\n            while True:\n                await asyncio.sleep(self.auto_save_interval)\n                \n                if self.current_session and self.current_session.state == SessionState.RUNNING:\n                    self.save_checkpoint({\n                        \"auto_save\": True,\n                        \"timestamp\": datetime.now().isoformat(),\n                        \"session_summary\": self._generate_session_summary()\n                    })\n                    \n        except asyncio.CancelledError:\n            self.logger.info(\"Auto-save loop cancelled\")\n        except Exception as e:\n            self.logger.error(f\"Auto-save loop error: {e}\")\n    \n    def _save_session_info(self, session: SessionInfo):\n        \"\"\"Save session info to file\"\"\"\n        session_file = self.sessions_dir / f\"{session.session_id}.json\"\n        \n        # Convert to serializable format\n        data = asdict(session)\n        data['created_at'] = session.created_at.isoformat()\n        data['last_updated'] = session.last_updated.isoformat()\n        if session.estimated_completion:\n            data['estimated_completion'] = session.estimated_completion.isoformat()\n        data['state'] = session.state.value\n        \n        with open(session_file, 'w') as f:\n            json.dump(data, f, indent=2)\n    \n    def _get_checkpoint_file(self, session_id: str, timestamp: datetime) -> Path:\n        \"\"\"Get checkpoint file path\"\"\"\n        timestamp_str = timestamp.strftime(\"%Y%m%d_%H%M%S_%f\")\n        filename = f\"{session_id}_{timestamp_str}.pkl\"\n        if self.compression_enabled:\n            filename += \".gz\"\n        return self.checkpoints_dir / filename\n    \n    def _save_checkpoint_file(self, checkpoint: SessionCheckpoint, file_path: Path):\n        \"\"\"Save checkpoint to file\"\"\"\n        data = asdict(checkpoint)\n        data['timestamp'] = checkpoint.timestamp.isoformat()\n        data['state'] = checkpoint.state.value\n        \n        if self.compression_enabled:\n            with gzip.open(file_path, 'wb') as f:\n                pickle.dump(data, f)\n        else:\n            with open(file_path, 'wb') as f:\n                pickle.dump(data, f)\n    \n    def _load_checkpoint_file(self, file_path: Path) -> Optional[SessionCheckpoint]:\n        \"\"\"Load checkpoint from file\"\"\"\n        try:\n            if file_path.suffix == '.gz':\n                with gzip.open(file_path, 'rb') as f:\n                    data = pickle.load(f)\n            else:\n                with open(file_path, 'rb') as f:\n                    data = pickle.load(f)\n            \n            # Convert timestamp and state\n            data['timestamp'] = datetime.fromisoformat(data['timestamp'])\n            data['state'] = SessionState(data['state'])\n            \n            return SessionCheckpoint(**data)\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to load checkpoint {file_path}: {e}\")\n            return None\n    \n    def _cleanup_old_sessions(self):\n        \"\"\"Clean up old session files\"\"\"\n        try:\n            cutoff_date = datetime.now() - timedelta(days=self.max_session_age_days)\n            \n            for session_file in self.sessions_dir.glob(\"*.json\"):\n                if datetime.fromtimestamp(session_file.stat().st_mtime) < cutoff_date:\n                    session_id = session_file.stem\n                    self.cleanup_session(session_id, archive=True)\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to cleanup old sessions: {e}\")\n    \n    def _archive_session(self, session_id: str):\n        \"\"\"Archive session files\"\"\"\n        archive_date = datetime.now().strftime(\"%Y%m%d\")\n        archive_dir = self.archives_dir / archive_date\n        archive_dir.mkdir(exist_ok=True)\n        \n        # Archive session file\n        session_file = self.sessions_dir / f\"{session_id}.json\"\n        if session_file.exists():\n            shutil.move(str(session_file), str(archive_dir / session_file.name))\n        \n        # Archive checkpoint files\n        checkpoint_pattern = f\"{session_id}_*.pkl*\"\n        for checkpoint_file in self.checkpoints_dir.glob(checkpoint_pattern):\n            shutil.move(str(checkpoint_file), str(archive_dir / checkpoint_file.name))\n    \n    def _generate_session_summary(self) -> Dict[str, Any]:\n        \"\"\"Generate session summary\"\"\"\n        if not self.current_session:\n            return {}\n        \n        runtime = datetime.now() - self.current_session.created_at\n        \n        return {\n            \"runtime_seconds\": runtime.total_seconds(),\n            \"progress_percentage\": self.current_session.total_progress,\n            \"leads_generated\": self.current_session.leads_generated,\n            \"current_step\": self.current_session.current_step,\n            \"checkpoints_count\": self.current_session.checkpoints_count,\n            \"errors_count\": self.current_session.errors_count,\n            \"warnings_count\": self.current_session.warnings_count\n        }"