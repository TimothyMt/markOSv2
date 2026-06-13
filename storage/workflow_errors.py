"""
Workflow error logging — best-effort Supabase insert for workflow step failures.

Never propagates exceptions — always swallows and logs.warning.
"""
import logging

logger = logging.getLogger(__name__)

TABLE = "workflow_errors"


async def log_workflow_error(
    user_id: int,
    task_type: str,
    step_index: int,
    skill_name: str,
    error_msg,
) -> None:
    """Best-effort insert workflow error to Supabase.

    Catches ALL exceptions — never propagates.
    """
    try:
        from storage.session import _client
        if _client is None:
            logger.warning(
                "[workflow_errors] Supabase client not initialized — skipping log "
                "(user=%s task=%s step=%s skill=%s)",
                user_id, task_type, step_index, skill_name,
            )
            return

        payload = {
            "user_id": user_id,
            "task_type": task_type,
            "step_index": step_index,
            "skill_name": skill_name,
            "error_msg": str(error_msg)[:1000],
        }
        await _client.table(TABLE).insert(payload).execute()
        logger.info(
            "[workflow_errors] Logged error: user=%s task=%s step=%s skill=%s",
            user_id, task_type, step_index, skill_name,
        )
    except Exception as e:
        logger.warning(
            "[workflow_errors] Failed to log error (suppressed): user=%s task=%s step=%s: %s",
            user_id, task_type, step_index, e,
        )
