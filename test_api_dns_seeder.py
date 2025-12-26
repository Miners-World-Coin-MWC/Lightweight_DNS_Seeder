import pytest
from unittest.mock import patch
from api_dns_seeder import PeerResolver
from dnslib import DNSRecord

# Test to ensure the resolver updates peers correctly
def test_update_peers():
    # Correctly formatted mock API response (dict with "result" key)
    mock_response = {
        "result": [
            {"addr": "192.168.1.1"},
            {"addr": "2001:db8::ff00:42:8329"}
        ]
    }

    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Disable background thread for testing
        resolver = PeerResolver("https://api.minersworld.org/peers", start_thread=False)

        # Call update_peers directly
        resolver.update_peers()

        # Debug prints
        print(f"IPv4 Peers: {resolver.ipv4_peers}")
        print(f"IPv6 Peers: {resolver.ipv6_peers}")

        # Assert API call
        assert mock_get.call_count == 2  # Called once in __init__, once in update_peers

        # Assert peers were parsed correctly
        assert resolver.ipv4_peers == ["192.168.1.1"]
        assert resolver.ipv6_peers == ["2001:db8::ff00:42:8329"]

# Test DNS resolution (A and AAAA queries)
def test_resolve():
    # Create resolver with static peer lists
    resolver = PeerResolver("https://api.minersworld.org/peers", start_thread=False)
    resolver.ipv4_peers = ["192.168.1.1"]
    resolver.ipv6_peers = ["2001:db8::ff00:42:8329"]

    # Create DNS queries
    request_ipv4 = DNSRecord.question("example.com", "A")
    request_ipv6 = DNSRecord.question("example.com", "AAAA")

    # Resolve DNS queries
    response_ipv4 = resolver.resolve(request_ipv4, None)
    response_ipv6 = resolver.resolve(request_ipv6, None)

    # Verify IPv4 resolution
    assert len(response_ipv4.rr) == 1
    assert str(response_ipv4.rr[0].rdata) == "192.168.1.1"

    # Verify IPv6 resolution
    assert len(response_ipv6.rr) == 1
    assert str(response_ipv6.rr[0].rdata) == "2001:db8::ff00:42:8329"
