"""Control plane — manages sessions, proxies LLM calls, stores artifacts.

Holds all credentials. Sandboxes talk to this and nothing else.
"""

import logging
import secrets
import uuid
from dataclasses import dataclass, field

from config.settings import Settings
from models.agent import AgentSession, AgentStatus

logger = logging.getLogger(__name__)


@dataclass
class SessionRecord:
    """Internal session tracking record."""

    session: AgentSession
    token: str
    artifacts: list[str] = field(default_factory=list)


class ControlPlaneService:
    """In-memory control plane for managing agent sessions."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sessions: dict[str, SessionRecord] = {}

    def create_session(
        self,
        repo_url: str = "",
        pr_number: int = 0,
        diff: str = "",
        app_url: str = "",
    ) -> tuple[str, str]:
        """Create a new agent session. Returns (session_id, session_token)."""
        session_id = str(uuid.uuid4())[:8]
        token = secrets.token_urlsafe(32)

        session = AgentSession(
            session_id=session_id,
            repo_url=repo_url,
            pr_number=pr_number,
            diff=diff,
            app_url=app_url,
        )
        self._sessions[session_id] = SessionRecord(session=session, token=token)

        logger.info(
            "Session created",
            extra={"session_id": session_id, "repo_url": repo_url},
        )
        return session_id, token

    def validate_token(self, session_id: str, token: str) -> bool:
        """Validate a session token."""
        record = self._sessions.get(session_id)
        if not record:
            return False
        return secrets.compare_digest(record.token, token)

    def get_session(self, session_id: str) -> AgentSession | None:
        """Get session by ID."""
        record = self._sessions.get(session_id)
        return record.session if record else None

    def update_status(self, session_id: str, status: AgentStatus) -> None:
        """Update session status."""
        record = self._sessions.get(session_id)
        if record:
            record.session.status = status

    def store_artifact(self, session_id: str, path: str) -> None:
        """Record an artifact path for a session."""
        record = self._sessions.get(session_id)
        if record:
            record.artifacts.append(path)
            logger.info(
                "Artifact stored",
                extra={"session_id": session_id, "path": path},
            )

    def get_artifacts(self, session_id: str) -> list[str]:
        """Get artifact paths for a session."""
        record = self._sessions.get(session_id)
        return record.artifacts if record else []
