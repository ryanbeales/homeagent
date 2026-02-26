import asyncio
import os
import tempfile
from src.tools.scheduler import AgentScheduler

class DummyChat:
    def __init__(self):
        self.messages = []
    
    async def post_message(self, sender, message, room=None):
        self.messages.append(message)
        print(f"Posted: {message}")

async def main():
    with tempfile.TemporaryDirectory() as d:
        chat = DummyChat()
        scheduler = AgentScheduler("TestAgent", d, chat)
        scheduler.start()
        
        # Add a cron job that runs every second
        res = scheduler.add_job("cron", "* * * * * *", "Test message")
        print("Add job result:", res)
        
        # Add a date job
        from datetime import datetime, timedelta
        run_date = datetime.now() + timedelta(seconds=2)
        res = scheduler.add_job("date", run_date.isoformat(), "Date message")
        print("Add date job result:", res)
        
        print("Jobs in APScheduler:", scheduler.scheduler.get_jobs())
        
        # Wait a bit
        print("Waiting 5 seconds for jobs to execute...")
        await asyncio.sleep(5)
        
        print(f"Messages recorded: {chat.messages}")
        
        scheduler.stop()

if __name__ == "__main__":
    asyncio.run(main())
