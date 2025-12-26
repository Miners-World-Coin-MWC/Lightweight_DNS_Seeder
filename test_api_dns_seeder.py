import pytest
from unittest.mock import patch, MagicMock
from api_dns_seeder import PeerResolver
from dnslib import DNSRecord


# =========================
# TEST: update_peers parsing
# =========================
def test_update_peers():
    mock_response = {
        "result": [
            {"addr": "192.168.1.1"},
            {"addr": "192.168.1.1:8333"},           # IPv4 + port (dedupe)
            {"addr": "[2001:db8::ff00:42:8329]"},  # IPv6 bracketed
            {"addr": "[2001:db8::ff00:42:8329]:8333"},
            {"addr": "invalid-ip"}                  # ignored
        ]
    }

    mock_get = MagicMock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status.return_value = None

    with patch("requests.get", mock_get):
        resolver = PeerResolver(
            "https://api.minersworld.org/peers",
            start_thread=False
        )

        resolver.update_peers()

        # IPv4 parsed and deduplicated
        assert resolver.ipv4_peers == ["192.168.1.1"]

        # IPv6 parsed and deduplicated
        assert resolver.ipv6_peers == ["2001:db8::ff00:42:8329"]

        # Ensure API was called at least once
        assert mock_get.called


# =========================
# TEST: DNS resolution (A / AAAA)
# =========================
def test_resolve():
    resolver = PeerResolver(
        "https://api.minersworld.org/peers",
        start_thread=False
    )

    resolver.ipv4_peers = ["192.168.1.1"]
    resolver.ipv6_peers = ["2001:db8::ff00:42:8329"]

    # IPv4 query
    request_ipv4 = DNSRecord.question("example.com", "A")
    response_ipv4 = resolver.resolve(request_ipv4, None)

    assert len(response_ipv4.rr) == 1
    assert str(response_ipv4.rr[0].rdata) == "192.168.1.1"

    # IPv6 query
    request_ipv6 = DNSRecord.question("example.com", "AAAA")
    response_ipv6 = resolver.resolve(request_ipv6, None)

    assert len(response_ipv6.rr) == 1
    assert str(response_ipv6.rr[0].rdata) == "2001:db8::ff00:42:8329"


# =========================
# TEST: empty API response
# =========================
def test_update_peers_empty_result():
    mock_response = {"result": []}

    mock_get = MagicMock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_response
    mock_get.return_value.raise_for_status.return_value = None

    with patch("requests.get", mock_get):
        resolver = PeerResolver(
            "https://api.minersworld.org/peers",
            start_thread=False
        )

        resolver.update_peers()

        assert resolver.ipv4_peers == []
        assert resolver.ipv6_peers == []
