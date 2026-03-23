from app.utils.client_ip import resolve_client_ip_for_lead
from app.utils.ip_extract import extract_ipv4_from_comments


def test_extract_ip_from_bitrix_comments() -> None:
    text = "Page: [b]https://x.com[/b] \nIP: [b]71.145.120.10[/b] \nBrowser: [b]Chrome[/b]"
    assert extract_ipv4_from_comments(text) == "71.145.120.10"


def test_resolve_client_ip_priority() -> None:
    comments = "IP: [b]10.0.0.1[/b]"
    assert resolve_client_ip_for_lead(comments, None, "203.0.113.5, 10.0.0.1") == "203.0.113.5"
    assert resolve_client_ip_for_lead(comments, "198.51.100.2", None) == "198.51.100.2"
    assert resolve_client_ip_for_lead(comments, None, None) == "10.0.0.1"
