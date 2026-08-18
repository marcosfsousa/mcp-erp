# `tests/conformance/` — the authorization code flow, wire and outbound

The proof the map asks for: a real OAuth flow completing against a running
server. The only suite that reaches the network, and its preflight names
external causes first so an outage does not read as a regression.

Needs Compose plus network. Lands with #46.
