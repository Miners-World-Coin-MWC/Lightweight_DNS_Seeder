import requests
import schedule
import time
import socket
import subprocess
from discord_webhook import DiscordWebhook, DiscordEmbed
from datetime import datetime
from dotenv import load_dotenv
import os
import re

# Load environment variables from .env file
load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# State flags
is_up = False  # Assume down at startup to force first check alert
retry_count = 0
MAX_RETRIES = 3
SEEDNODE_NAME = "MinersWorldCoin Seeder"  # Name of the seednode

def send_discord_alert(embed):
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    webhook.add_embed(embed)
    webhook.execute()

def create_embed(title, description, color):
    embed = DiscordEmbed(title=title, description=description, color=color)
    embed.set_footer(text="Health Check Monitor")
    embed.set_timestamp()
    return embed

def extract_peers_from_dig(output):
    """Extract IPs from the ANSWER SECTION of dig output."""
    peers = []
    in_answer = False

    print("DIG Output:\n", output)  # Print raw output to debug

    for line in output.splitlines():
        # Identify the start of the ANSWER SECTION
        if "ANSWER SECTION:" in line:
            in_answer = True
            continue
        
        # Stop reading once we leave the ANSWER SECTION
        if in_answer and line.strip() == "":
            in_answer = False
        
        # Extract IPs from the "IN A" records
        if in_answer:
            match = re.search(r"\sIN\sA\s([\d\.]+)", line)
            if match:
                ip = match.group(1)
                peers.append(ip)

    print(f"Extracted Peers: {peers}")  # Debug output to check extracted peers
    return peers

def health_check():
    global is_up, retry_count

    try:
        # Root NS check to ensure DNS is up (using dig, which defaults to UDP)
        root_check = subprocess.run(
            ["dig", "@localhost", "-p", "4408", ".", "NS"],
            capture_output=True,
            text=True
        )

        print("ROOT DIG OUTPUT:\n", root_check.stdout)

        if root_check.returncode != 0 or "connection timed out" in root_check.stdout or "status: SERVFAIL" in root_check.stdout:
            raise Exception("DNS server did not respond properly to root NS check.")

        # Peer check: look for A records for your seeder domain
        peer_check = subprocess.run(
            ["dig", "A", "seed.minersworld.org", "@localhost", "-p", "4408"],
            capture_output=True,
            text=True
        )

        print("SEEDER DIG OUTPUT:\n", peer_check.stdout)

        peers = extract_peers_from_dig(peer_check.stdout)
        peer_list_str = "\n".join(peers) if peers else "_No peers found._"

        print(f"Health check passed at {datetime.now()} with {len(peers)} peers.")

        if not is_up:
            embed = create_embed(
                f"✅ **{SEEDNODE_NAME} is Back Online**",
                f"{SEEDNODE_NAME} is now online and responding as of {datetime.now()}.\n\n**Seednode Response:**\n{peer_list_str}",
                0x2ECC71  # Green
            )
            send_discord_alert(embed)
            is_up = True

        retry_count = 0

    except Exception as e:
        print(f"Health check failed: {e}")
        retry_count += 1

        if retry_count <= MAX_RETRIES:
            print(f"Retrying... ({retry_count}/{MAX_RETRIES})")
        else:
            if is_up:
                embed = create_embed(
                    f"🚨 **{SEEDNODE_NAME} is Down**",
                    f"{SEEDNODE_NAME} is down or unresponsive at {datetime.now()}.\n\nError: `{e}`",
                    0xE74C3C  # Red
                )
                send_discord_alert(embed)
                is_up = False

# Schedule the health check to run every 5 minutes
schedule.every(5).minutes.do(health_check)

if __name__ == "__main__":
    print("Health check monitoring started...")

    startup_embed = create_embed(
        f"🛡️ {SEEDNODE_NAME} Monitor Started",
        f"Monitoring has **started** at {datetime.now()}.\nHealth checks run every 5 minutes.",
        0x3498DB  # Blue
    )
    send_discord_alert(startup_embed)

    # Immediate health check to send online status if DNS is working
    health_check()

    while True:
        schedule.run_pending()
        time.sleep(1)
