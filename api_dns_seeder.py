import requests
import time
import threading
from dnslib.server import DNSServer, BaseResolver
from dnslib.dns import RR, QTYPE, A, AAAA
from ipaddress import ip_address


class PeerResolver(BaseResolver):
    def __init__(self, api_url, start_thread=True):
        self.api_url = api_url
        self.ipv4_peers = []
        self.ipv6_peers = []
        self.lock = threading.Lock()

        self.update_peers()

        if start_thread:
            threading.Thread(target=self.update_loop, daemon=True).start()

    @staticmethod
    def _extract_ip(addr):
        """
        Extract a valid IPv4/IPv6 address from:
        - 1.2.3.4:port
        - [2001:db8::1]:port
        - raw IPv4 / IPv6
        """
        if not addr:
            return None

        ip = addr.strip()

        # IPv6 in brackets: [addr]:port
        if ip.startswith("["):
            end = ip.find("]")
            if end != -1:
                ip = ip[1:end]

        # IPv4 with port OR non-bracketed IPv6 with port
        elif ":" in ip:
            parts = ip.rsplit(":", 1)
            if len(parts) == 2 and parts[1].isdigit():
                ip = parts[0]

        try:
            return ip_address(ip)
        except ValueError:
            return None

    def update_peers(self):
        try:
            response = requests.get(self.api_url, timeout=5)
            response.raise_for_status()

            data = response.json()
            peers = data.get("result", [])

            ipv4_set = set()
            ipv6_set = set()

            for entry in peers:
                raw_addr = entry.get("addr", "")
                ip_obj = self._extract_ip(raw_addr)

                if not ip_obj:
                    continue

                if ip_obj.version == 4:
                    ipv4_set.add(str(ip_obj))
                elif ip_obj.version == 6:
                    ipv6_set.add(str(ip_obj))

            with self.lock:
                self.ipv4_peers = sorted(ipv4_set)
                self.ipv6_peers = sorted(ipv6_set)

            print(
                f"[Seeder] Loaded {len(self.ipv4_peers)} IPv4 peers "
                f"and {len(self.ipv6_peers)} IPv6 peers"
            )

        except Exception as e:
            print(f"[Seeder] Failed to fetch peers: {e}")

    def update_loop(self):
        while True:
            self.update_peers()
            time.sleep(300)

    def resolve(self, request, handler):
        reply = request.reply()
        qname = request.q.qname
        qtype = QTYPE[request.q.qtype]

        with self.lock:
            if qtype == "A":
                for ip in self.ipv4_peers:
                    reply.add_answer(
                        RR(qname, QTYPE.A, rdata=A(ip), ttl=60)
                    )

            elif qtype == "AAAA":
                for ip in self.ipv6_peers:
                    reply.add_answer(
                        RR(qname, QTYPE.AAAA, rdata=AAAA(ip), ttl=60)
                    )

        return reply


# Run DNS server
if __name__ == "__main__":
    resolver = PeerResolver("https://api.minersworld.org/peers")
    server = DNSServer(
        resolver,
        port=4408,
        address="::",   # Dual-stack IPv4 + IPv6
        tcp=False
    )

    print("MinersWorldCoin DNS Seeder running on port 4408 (IPv4 & IPv6)...")
    server.start()
