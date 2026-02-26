import pytest
import os
import tempfile
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock

from src.tools.scheduler import AgentScheduler, ScheduleTaskTool, ListScheduledTasksTool, RemoveScheduledTaskTool

@pytest.fixture
def mock_chat_room():
    room = MagicMock()
    room.post_message = AsyncMock()
    return room

@pytest.fixture
def temp_agent_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d

@pytest.fixture
def scheduler(temp_agent_dir, mock_chat_room):
    s = AgentScheduler("TestAgent", temp_agent_dir, mock_chat_room)
    # We won't start the background thread so it doesn't hang in tests,
    # or we can mock it out if needed.
    return s

def test_scheduler_init(scheduler, temp_agent_dir):
    assert scheduler.agent_name == "TestAgent"
    assert scheduler.chat_room is not None
    assert scheduler.schedule_file == os.path.join(temp_agent_dir, "schedule.json")
    assert isinstance(scheduler.jobs_data, dict)

@pytest.mark.asyncio
async def test_schedule_task_tool(scheduler):
    tool = ScheduleTaskTool(scheduler)
    res = await tool.run("Do laundry", datetime_str="2030-01-01T10:00:00")

    assert "Successfully scheduled task" in res
    assert len(scheduler.jobs_data) == 1
    job_id = list(scheduler.jobs_data.keys())[0]
    assert scheduler.jobs_data[job_id]["message"] == "Do laundry"

@pytest.mark.asyncio
async def test_list_scheduled_tasks_tool(scheduler):
    # Add a task manually
    scheduler.add_job("cron", "* * * * *", "Buy groceries")
    
    tool = ListScheduledTasksTool(scheduler)
    res = await tool.run()
    
    assert "Buy groceries" in res
    assert "ID:" in res
    
@pytest.mark.asyncio
async def test_remove_scheduled_task_tool(scheduler):
    # Add a task
    scheduler.add_job("cron", "* * * * *", "Task to remove")
    job_id = list(scheduler.jobs_data.keys())[0]
    
    tool = RemoveScheduledTaskTool(scheduler)
    res = await tool.run(job_id) 
    
    assert "Removed scheduled task" in res
    assert len(scheduler.jobs_data) == 0

@pytest.mark.asyncio
async def test_scheduler_explicit_start(temp_agent_dir, mock_chat_room):
    # Create a pre-existing schedule.json
    schedule_file = os.path.join(temp_agent_dir, "schedule.json")
    with open(schedule_file, "w") as f:
        json.dump({
            "test_job_1": {
                "type": "cron",
                "value": "0 * * * *",
                "message": "Hourly test",
                "target_agent": ""
            }
        }, f)
        
    s = AgentScheduler("TestAgent", temp_agent_dir, mock_chat_room)
    # Explicitly start the scheduler (as done in agent_loader)
    s.start()
    
    # Verify jobs were loaded from disk into memory and APScheduler
    assert "test_job_1" in s.jobs_data
    assert len(s.scheduler.get_jobs()) == 1
    
    s.stop()

@pytest.mark.asyncio
async def test_scheduler_inject_prompt(scheduler):
    # Setup mock for inject_prompt
    scheduler.chat_room.inject_prompt = AsyncMock()
    
    # Add a date task in the past (it won't run via APScheduler immediately in tests, so we call the callback manually)
    func = scheduler._build_task_callback("test_id", "Test message", "TargetAgent")
    
    # Execute the returned async function
    await func()
    
    # Verify the message was posted to the chat room
    scheduler.chat_room.post_message.assert_called_once_with("TestAgent", "[Scheduled Task] @TargetAgent Test message")
    
    # Verify the prompt was injected for the agent loop to pick up
    scheduler.chat_room.inject_prompt.assert_called_once_with("System: [Scheduled Task] @TargetAgent Test message")

