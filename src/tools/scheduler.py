import os
import json
import asyncio
import uuid
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from typing import Callable, Any, Dict
from src.tools.base import Tool
from src.core.logger import logger


class AgentScheduler:
    """Agent-specific task scheduler that manages an APScheduler and serializes jobs to a JSON file."""
    
    def __init__(self, agent_name: str, base_dir: str, chat_room):
        self.agent_name = agent_name
        self.schedule_file = os.path.join(base_dir, "schedule.json")
        self.chat_room = chat_room
        self._scheduler = None
        
        # In-memory index of jobs we've saved
        # Format: { "job_id": { "type": "date|cron", "value": "datetime_str|cron_str", "message": "msg", "target_agent": "target" } }
        self.jobs_data: Dict[str, dict] = {}
        self._has_loaded = False

    @property
    def scheduler(self):
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler()
            self._scheduler.start()
            self._load_jobs()
        return self._scheduler

    def _load_jobs(self):
        """Loads jobs from JSON and reconstructs them into APScheduler."""
        if not os.path.exists(self.schedule_file):
            return
            
        try:
            with open(self.schedule_file, "r") as f:
                data = json.load(f)
                
            now = datetime.now()
            for job_id, job_info in data.items():
                if job_info["type"] == "date":
                    run_date = datetime.fromisoformat(job_info["value"])
                    if run_date < now:
                        logger.info(f"Skipping past scheduled job {job_id} for {self.agent_name}")
                        continue
                    self._add_to_apscheduler(job_id, job_info, DateTrigger(run_date=run_date))
                elif job_info["type"] == "cron":
                    trigger = CronTrigger.from_crontab(job_info["value"])
                    self._add_to_apscheduler(job_id, job_info, trigger)
                    
                self.jobs_data[job_id] = job_info
                
            # Immediately save to prune any dropped past jobs
            self._save_jobs()
            logger.info(f"Loaded {len(self.jobs_data)} scheduled jobs for {self.agent_name}")
        except Exception as e:
            logger.error(f"Failed to load schedule for {self.agent_name}: {e}")

    def _save_jobs(self):
        """Saves current jobs to JSON."""
        try:
            with open(self.schedule_file, "w") as f:
                json.dump(self.jobs_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save schedule for {self.agent_name}: {e}")

    def _build_task_callback(self, job_id: str, message: str, target_agent: str) -> Callable:
        """Constructs the async/sync bridge for APScheduler to hit our chat room."""
        full_message = message
        if target_agent:
            full_message = f"@{target_agent} {message}"
            
        async def scheduled_post():
            try:
                if self.chat_room:
                    await self.chat_room.post_message(self.agent_name, f"[Scheduled Task] {full_message}")
                # If this was a date job, it won't run again, so we should clean it from our JSON
                if job_id in self.jobs_data and self.jobs_data[job_id]["type"] == "date":
                    del self.jobs_data[job_id]
                    self._save_jobs()
            except Exception as e:
                logger.error(f"Scheduled task error for {self.agent_name}: {e}")

        # APScheduler needs a sync wrapper for async functions by default, or run in loop
        def run_scheduled():
            loop = asyncio.get_event_loop()
            asyncio.ensure_future(scheduled_post())
            
        return run_scheduled

    def _add_to_apscheduler(self, job_id: str, job_info: dict, trigger):
        """Internal helper to add a job to the underlying scheduler machinery."""
        func = self._build_task_callback(job_id, job_info["message"], job_info["target_agent"])
        self.scheduler.add_job(func, trigger, id=job_id, replace_existing=True)

    def add_job(self, trigger_type: str, trigger_value: str, message: str, target_agent: str = "") -> str:
        """Add a new job to both the live scheduler and the save file."""
        job_id = str(uuid.uuid4())[:8]
        
        job_info = {
            "type": trigger_type,
            "value": trigger_value,
            "message": message,
            "target_agent": target_agent
        }
        
        if trigger_type == "date":
            try:
                run_date = datetime.fromisoformat(trigger_value)
                if run_date < datetime.now():
                    return "Cannot schedule a task in the past."
                trigger = DateTrigger(run_date=run_date)
            except ValueError:
                return f"Invalid datetime format: '{trigger_value}'. Use ISO format like '2026-02-16T10:00:00'."
        elif trigger_type == "cron":
            try:
                trigger = CronTrigger.from_crontab(trigger_value)
            except ValueError as e:
                return f"Invalid cron format '{trigger_value}': {e}"
        else:
            return f"Unknown trigger type: {trigger_type}"

        self._add_to_apscheduler(job_id, job_info, trigger)
        self.jobs_data[job_id] = job_info
        self._save_jobs()
        
        type_desc = f"datetime {trigger_value}" if trigger_type == "date" else f"cron pattern '{trigger_value}'"
        return f"Successfully scheduled task '{job_id}' for {type_desc}."

    def remove_job(self, job_id: str) -> str:
        """Remove a job by its short ID."""
        if job_id not in self.jobs_data:
            return f"No scheduled task found with ID '{job_id}'."
            
        self.scheduler.remove_job(job_id)
        del self.jobs_data[job_id]
        self._save_jobs()
        return f"Removed scheduled task '{job_id}'."

    def list_jobs(self) -> str:
        """Returns a formatted markdown string of all active jobs."""
        if not self.jobs_data:
            return "No tasks currently scheduled."
            
        lines = []
        for jid, info in self.jobs_data.items():
            target = f" (target: @{info['target_agent']})" if info["target_agent"] else ""
            lines.append(f"- **ID:** `{jid}` | **Type:** `{info['type']}` | **Trigger:** `{info['value']}` | **Task:** {info['message']}{target}")
            
        return "\n".join(lines)

    def stop(self):
        """Shut down the background scheduler scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()

    def start(self):
        """Explicitly start the scheduler and load jobs."""
        _ = self.scheduler


class ScheduleTaskTool(Tool):
    """Allows agents to schedule a message to be posted at a future time."""

    def __init__(self, agent_scheduler: AgentScheduler):
        super().__init__(
            "schedule_task",
            "Schedule a message to be posted to the chat at a future date/time OR on a recurring cron schedule. You MUST provide exactly one of `datetime_str` OR `cron_expr`.",
            args_schema={
                "message": "The message content or task instructions to post at the scheduled time.",
                "datetime_str": "(Optional) One-time trigger in ISO format (e.g., '2026-02-16T10:00:00'). Leave empty if using cron.",
                "cron_expr": "(Optional) Recurring trigger using standard 5-part cron syntax (e.g., '0 9 * * *' for 9 AM daily). Leave empty if using datetime.",
                "target_agent": "(Optional) @mention an agent in the scheduled message to direct it."
            }
        )
        self.scheduler = agent_scheduler

    async def run(self, message: str, datetime_str: str = "", cron_expr: str = "", target_agent: str = "") -> str:
        if datetime_str and cron_expr:
            return "Error: Provide EITHER datetime_str OR cron_expr, not both."
        if not datetime_str and not cron_expr:
            return "Error: You must provide either datetime_str or cron_expr."
            
        if datetime_str:
            return self.scheduler.add_job("date", datetime_str, message, target_agent)
        else:
            return self.scheduler.add_job("cron", cron_expr, message, target_agent)


class ListScheduledTasksTool(Tool):
    """Lists the agent's currently running scheduled jobs."""

    def __init__(self, agent_scheduler: AgentScheduler):
        super().__init__(
            "list_scheduled_tasks",
            "List all background tasks currently scheduled for your agent, including their IDs.",
            args_schema={}
        )
        self.scheduler = agent_scheduler

    async def run(self, **kwargs) -> str:
        return self.scheduler.list_jobs()


class RemoveScheduledTaskTool(Tool):
    """Deletes a scheduled job by ID."""

    def __init__(self, agent_scheduler: AgentScheduler):
        super().__init__(
            "remove_scheduled_task",
            "Remove/cancel a previously scheduled background task by its ID.",
            args_schema={
                "job_id": "The ID of the scheduled task to remove."
            }
        )
        self.scheduler = agent_scheduler

    async def run(self, job_id: str, **kwargs) -> str:
        if not job_id:
            return "Error: job_id is required."
        return self.scheduler.remove_job(job_id)
