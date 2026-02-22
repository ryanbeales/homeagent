import socket
import os
import sys
import threading
import time
import subprocess
import json
import logging

def setup_logging(agent_name):
    log_dir = "/app/data/agent"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "agent.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr)
        ]
    )
    return logging.getLogger(f"{agent_name}-bridge")

def read_from_agent(process, irc_sock, channel, logger):
    """Read lines from agent's stdout and send to IRC."""
    while True:
        line = process.stdout.readline()
        if not line:
            break
        line = line.strip()
        if not line: continue
        
        if line == "--- WAIT_FOR_INPUT ---":
            # Just a synchronization marker, we don't send this to IRC
            continue
            
        # Send line to IRC
        send_irc(irc_sock, f"PRIVMSG {channel} :{line}")
        logger.info(f"[Agent -> IRC] {line}")

def send_irc(sock, msg):
    try:
        sock.send((msg + "\r\n").encode("utf-8"))
    except Exception as e:
        logging.error(f"IRC send error: {e}")

def main():
    agent_name = os.environ.get("AGENT_NAME")
    
    if not agent_name:
        sys.stderr.write("AGENT_NAME not set\n")
        sys.exit(1)

    from src.core.config import settings
    server = settings.irc_server
    port = settings.irc_port
    channel = settings.irc_channel

    logger = setup_logging(agent_name)
    logger.info(f"Starting IRC bridge for {agent_name}")

    # Load claim keywords
    keywords = [agent_name.lower()]
    meta_path = "/app/data/agent/metadata.json"
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            keywords.extend([k.lower() for k in meta.get("claim_keywords", [])])

    logger.info(f"Keywords: {keywords}")

    # Spawn Agent Subprocess
    agent_cmd = [sys.executable, "-m", "src.core.agent_loop"]
    logger.info(f"Spawning: {' '.join(agent_cmd)}")
    process = subprocess.Popen(
        agent_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr, # Map stderr directly transparently
        text=True,
        bufsize=1 # Line buffered
    )

    # Start IRC Socket
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        irc.connect((server, port))
    except Exception as e:
        logger.error(f"Failed to connect to IRC: {e}")
        sys.exit(1)
        
    send_irc(irc, f"NICK {agent_name}")
    send_irc(irc, f"USER {agent_name} 0 * :{agent_name} Agent")
    # Quick sleep to let MOTD pass before join (proper IRC clients wait for 376 or 422, but a sleep is fine for local)
    time.sleep(2)
    send_irc(irc, f"JOIN {channel}")

    # Start thread to read from agent stdout and pass to IRC
    t = threading.Thread(target=read_from_agent, args=(process, irc, channel, logger), daemon=True)
    t.start()

    # Coordinator Latency State
    pending_fallback_lock = threading.Lock()
    pending_fallback = None # Stores (sender, message, timestamp)

    def fallback_dispatch():
        nonlocal pending_fallback
        while True:
            time.sleep(0.5)
            with pending_fallback_lock:
                if pending_fallback:
                    sender, msg, ts = pending_fallback
                    if time.time() - ts >= 3.0:
                        logger.info(f"[Fallback] 3s elapsed. Delivering to Coordinator: {msg[:30]}...")
                        process.stdin.write(f"{sender}: {msg}\n")
                        process.stdin.flush()
                        pending_fallback = None

    if agent_name.lower() == "coordinator":
        threading.Thread(target=fallback_dispatch, daemon=True).start()

    # Read from IRC
    buffer = ""
    while True:
        try:
            data = irc.recv(4096)
            if not data:
                break
            buffer += data.decode("utf-8", errors="ignore")
            while "\r\n" in buffer:
                line, buffer = buffer.split("\r\n", 1)
                
                # Respond to PING
                if line.startswith("PING"):
                    send_irc(irc, line.replace("PING", "PONG", 1))
                    continue

                    
                # Handle PRIVMSG
                if " PRIVMSG " in line:
                    parts = line.split(" PRIVMSG ", 1)
                    prefix = parts[0]
                    # prefix usually looks like :nick!user@host
                    sender = prefix.split("!")[0].lstrip(":") if "!" in prefix else "Unknown"
                    sender_lower = sender.lower()
                    
                    target_msg = parts[1].split(" :", 1)
                    if len(target_msg) > 1:
                        target = target_msg[0]
                        message = target_msg[1]
                        msg_lower = message.lower()
                        
                        # Don't process our own messages
                        if sender == agent_name:
                            continue
                            
                        # Discovery: Who are the other agents?
                        known_agents = []
                        if os.path.exists("/app/data/agents"):
                            known_agents = [d.lower() for d in os.listdir("/app/data/agents") if os.path.isdir(os.path.join("/app/data/agents", d))]
                        
                        is_agent_sender = sender_lower in known_agents
                        
                        # If ANY agent speaks, cancel pending Coordinator fallback
                        if is_agent_sender and agent_name.lower() == "coordinator":
                            with pending_fallback_lock:
                                if pending_fallback:
                                    logger.info(f"Agent {sender} spoke. Cancelling pending fallback.")
                                    pending_fallback = None

                        # Check for mentions
                        mentioned_direct = f"@{agent_name.lower()}" in msg_lower
                        
                        # Check if ANY other agent is mentioned (Strict Ignore)
                        any_other_mentioned = False
                        msg_words = msg_lower.split()
                        other_agent_keywords = []

                        for agent in known_agents:
                            if agent != agent_name.lower():
                                # Check for @mention or plain word mention
                                if f"@{agent}" in msg_lower or agent in msg_words:
                                    any_other_mentioned = True
                                
                                # Gather keywords for coordinator check
                                if agent_name.lower() == "coordinator":
                                    meta_path = os.path.join("/app/data/agents", agent, "metadata.json")
                                    if os.path.exists(meta_path):
                                        try:
                                            with open(meta_path, "r", encoding="utf-8") as f:
                                                meta = json.load(f)
                                                other_agent_keywords.extend([k.lower() for k in meta.get("claim_keywords", [])])
                                        except Exception:
                                            pass

                        # Routing Logic:
                        should_process_now = False
                        should_queue_fallback = False
                        
                        if is_agent_sender:
                            # STRICT: Only respond to other agents if specifically mentioned with @Name
                            if mentioned_direct:
                                should_process_now = True
                        else:
                            # Messages from humans:
                            if mentioned_direct:
                                should_process_now = True
                            elif any_other_mentioned:
                                # Explicitly ignore if someone else was tagged
                                pass
                            elif any(kw in msg_lower for kw in keywords):
                                # Keyword match (e.g. "create agent" for Creator)
                                should_process_now = True
                            elif agent_name.lower() == "coordinator":
                                if any(kw in msg_lower for kw in other_agent_keywords):
                                    logger.info("Message matches another agent's keywords. Coordinator ignoring fallback.")
                                    pass
                                else:
                                    # Untagged human message -> Coordinator Fallback with Latency
                                    should_queue_fallback = True

                        if should_process_now:
                            logger.info(f"[IRC -> Agent] {sender}: {message}")
                            process.stdin.write(f"{sender}: {message}\n")
                            process.stdin.flush()
                            # Cancel any pending fallback as we are responding now
                            if agent_name.lower() == "coordinator":
                                with pending_fallback_lock:
                                    pending_fallback = None
                        elif should_queue_fallback:
                            with pending_fallback_lock:
                                logger.info(f"Queuing fallback for Coordinator (3s delay): {message[:30]}...")
                                pending_fallback = (sender, message, time.time())
                        else:
                            # Send as passive history so the agent maintains context
                            process.stdin.write(f"[HISTORY] {sender}: {message}\n")
                            process.stdin.flush()

        except Exception as e:
            logger.error(f"IRC loop error: {e}")
            break


    process.terminate()

if __name__ == "__main__":
    main()
