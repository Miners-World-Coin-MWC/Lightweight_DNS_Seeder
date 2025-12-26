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

    def update_peers(self):
        try:
            response = requests.get(self.api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                peers = data.get("result", [])
                ipv4_list = []
                ipv6_list = []

                for entry in peers:
                    ip = entry.get("addr", "")
                    try:
                        ip_obj = ip_address(ip)
                        if ip_obj.version == 4:
                            ipv4_list.append(str(ip_obj))
                        elif ip_obj.version == 6:
                            ipv6_list.append(str(ip_obj))
                    except ValueError:
                        continue

                with self.lock:
                    self.ipv4_peers = ipv4_list
                    self.ipv6_peers = ipv6_list

        except Exception as e:
            print(f"Failed to fetch peers: {e}")

    def update_loop(self):
        while True:
            self.update_peers()
            time.sleep(300)

    def resolve(self, request, handler):
        reply = request.reply()
        qname = request.q.qname
        qtype = QTYPE[request.q.qtype]

        with self.lock:
            if qtype == 'A':
                for ip in self.ipv4_peers:
                    reply.add_answer(RR(qname, QTYPE.A, rdata=A(ip), ttl=60))
            elif qtype == 'AAAA':
                for ip in self.ipv6_peers:
                    reply.add_answer(RR(qname, QTYPE.AAAA, rdata=AAAA(ip), ttl=60))

        return reply


# Run DNS server
if __name__ == "__main__":
    resolver = PeerResolver("https://api.minersworld.org/peers")
    server = DNSServer(resolver, port=4408, address="::")  # Dual-stack (IPv4 + IPv6)
    print("MinersWorldCoin DNS Seeder running on port 4408 (IPv4 & IPv6)...")
    server.start()
