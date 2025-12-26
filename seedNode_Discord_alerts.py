import os
import re
import time
import subprocess
from datetime import datetime

import requests
import schedule
from discord_webhook import DiscordWebhook, DiscordEmbed
from dotenv import load_dotenv


# =========================
# CONFIG
# =========================
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SEEDNODE_NAME = "MinersWorldCoin Seeder"

DNS_PORT = "4408"
SEED_DOMAIN = "seed.minersworld.org"
CHECK_INTERVAL_MINUTES = 5
MAX_RETRIES = 3


# =========================
# STATE
# =========================
is_up = False  # Assume down at startup to force first alert
retry_count = 0


# =========================
# DISCORD HELPERS
# =========================
def send_discord_alert(embed):
    if not DISCORD_WEBHOOK_URL:
        print("[WARN] DISCORD_WEBHOOK_URL not set")
        return

    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    webhook.add_embed(embed)
    webhook.execute()


def create_embed(title, description, color):
    embed = DiscordEmbed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="Seednode Health Monitor")
    embed.set_timestamp()
    return embed


# =========================
# DIG PARSING
# =========================
def extract_peers_from_dig(output):
    """
    Extract IPv4 peers from the ANSWER SECTION of dig output.
    Safe for all Python versions.
    """
    peers = []
    in_answer = False

    for line in output.splitlines():
        if "ANSWER SECTION:" in line:
            in_answer = True
            continue

        if in_answer and not line.strip():
            break

        if in_answer:
            match = re.search(r"\sIN\sA\s([\d\.]+)", line)
            if match:
                peers.append(match.group(1))

    return peers


# =========================
# HEALTH CHECK
# =========================
def run_dig(args):
    """Run dig safely across Python versions"""
    return subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


def health_check():
    global is_up, retry_count

    try:
        # Root NS check
        root_check = run_dig([
            "dig", "@localhost", "-p", DNS_PORT, ".", "NS"
        ])

        if root_check.returncode != 0:
            raise RuntimeError("dig failed on root NS check")

        stdout = root_check.stdout.lower()
        if "timed out" in stdout or "servfail" in stdout:
            raise RuntimeError("DNS root NS check failed")

        # Seeder peer check
        peer_check = run_dig([
            "dig", "A", SEED_DOMAIN, "@localhost", "-p", DNS_PORT
        ])

        peers = extract_peers_from_dig(peer_check.stdout)
        peer_list_str = "\n".join(peers) if peers else "_No peers returned_"

        print(
            f"[OK] {datetime.now()} | "
            f"Peers: {len(peers)}"
        )

        if not is_up:
            embed = create_embed(
                f"✅ **{SEEDNODE_NAME} Online**",
                (
                    f"{SEEDNODE_NAME} is now responding.\n\n"
                    f"**Returned Peers:**\n{peer_list_str}"
                ),
                0x2ECC71
            )
            send_discord_alert(embed)
            is_up = True

        retry_count = 0

    except Exception as e:
        retry_count += 1
        print(f"[FAIL] {datetime.now()} | {e}")

        if retry_count > MAX_RETRIES and is_up:
            embed = create_embed(
                f"🚨 **{SEEDNODE_NAME} Down**",
                (
                    f"{SEEDNODE_NAME} is unresponsive.\n\n"
                    f"Error:\n`{e}`"
                ),
                0xE74C3C
            )
            send_discord_alert(embed)
            is_up = False


# =========================
# SCHEDULER
# =========================
schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(health_check)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    print("Seednode health monitor started")

    startup_embed = create_embed(
        f"🛡️ {SEEDNODE_NAME} Monitor Started",
        (
            f"Monitoring started at {datetime.now()}.\n"
            f"Checks every {CHECK_INTERVAL_MINUTES} minutes."
        ),
        0x3498DB
    )
    send_discord_alert(startup_embed)

    # Immediate check on startup
    health_check()

    while True:
        schedule.run_pending()
        time.sleep(1)
