import asyncio
import os
import sys

# Ensure src is in pythonpath
sys.path.insert(0, os.path.abspath("."))

from src.core.agent_loader import create_agent_instance
from src.core.agent_loop import StdoutChatBridge

async def main():
    agent_name = "PrometheusAnomalyBot"
    agent_path = os.path.join("data", "agents", agent_name)
    
    if not os.path.exists(agent_path):
        print(f"Agent path {agent_path} does not exist.")
        return
        
    chat_bridge = StdoutChatBridge()
    agent = create_agent_instance(agent_name, "Bot", agent_path, [], chat_bridge)
    
    print("Agent created.")
    print("Does agent have scheduler?", hasattr(agent, "scheduler_daemon"))
    
    if hasattr(agent, "scheduler_daemon"):
        print("Starting scheduler daemon...")
        agent.scheduler_daemon.start()
        
        # Add a quick test job to see if it fires
        print("Adding a 2-second test job...")
        from datetime import datetime, timedelta
        run_date = datetime.now() + timedelta(seconds=2)
        res = agent.scheduler_daemon.add_job("date", run_date.isoformat(), "Test fire from script")
        print("Add job result:", res)
        
        print("Currently scheduled jobs:", agent.scheduler_daemon.list_jobs())
        print("APScheduler jobs:", agent.scheduler_daemon.scheduler.get_jobs())
        
        print("Waiting 5 seconds for jobs to fire...")
        await asyncio.sleep(5)
        
        print("Stopping scheduler...")
        agent.scheduler_daemon.stop()

if __name__ == "__main__":
    asyncio.run(main())
