"""Two replicas, no sticky routing, and nothing remembered between them.

Map constraint `#5`. The reason there are two rather than one is that a single
replica makes statelessness unfalsifiable: a server that remembered everything
would pass every other assertion in this repository.

**The asterisk is stated rather than buried.** ADR-0008 conceded that the
protocol package serves both eras from one endpoint with no way to disable
either, so sessions re-enter through a door this project does not control.
`stateless_http=True` closes the half that is ours: legacy callers get throwaway
per-request sessions, no session identifier is issued, and nothing is remembered
between requests. Normative register row 5 carries the reading.
"""

from collections import Counter

import httpx2

import rpc
from tokens import mint

REQUESTS = 12
"""Enough that a round robin over two upstreams cannot land on one by accident."""


def _served_by(response: httpx2.Response) -> str:
    """Which replica answered, as the gateway reports it."""
    replica = response.headers.get(rpc.SERVED_BY_HEADER)
    assert replica is not None, "the gateway did not report an upstream"
    return replica


def test_requests_round_robin_across_both_replicas() -> None:
    """One address, two backends, and no affinity between a caller and either.

    The gateway is the only way in — neither replica publishes a port — so this
    cannot accidentally be measuring one server twice.
    """
    minted = mint("priya.raman", ["erp.read"])
    replicas = Counter(
        _served_by(rpc.post("tools/list", token=minted.access_token)) for _ in range(REQUESTS)
    )

    assert len(replicas) == 2, replicas
    # Round robin rather than merely "both were used at some point": nginx's
    # default over two equal upstreams alternates, so an even count each is what
    # *no* affinity looks like.
    assert set(replicas.values()) == {REQUESTS // 2}, replicas


def test_neither_replica_issues_a_session() -> None:
    """No session identifier, and no cookie either.

    A session identifier would be the protocol's own way of asking a caller to
    come back to the same place, and a cookie would be the transport's. Both are
    what sticky routing is normally built out of, so both being absent is the
    same claim stated twice at the two layers that could break it.
    """
    minted = mint("priya.raman", ["erp.read"])

    for _ in range(REQUESTS):
        response = rpc.post("tools/list", token=minted.access_token)
        assert "mcp-session-id" not in response.headers, dict(response.headers)
        assert "set-cookie" not in response.headers, dict(response.headers)


def test_both_replicas_answer_identically() -> None:
    """Nothing is remembered, so which replica served is not observable in the answer.

    Compared as parsed documents rather than as bytes: the gateway's own
    `X-Served-By` header differs by construction, and the JSON-RPC body is the
    thing that must not.
    """
    minted = mint("priya.raman", ["erp.read"])
    answers: dict[str, list[str]] = {}

    for _ in range(REQUESTS):
        response = rpc.post("tools/list", token=minted.access_token)
        tools = sorted(tool["name"] for tool in rpc.result(response)["tools"])
        answers.setdefault(_served_by(response), []).append(",".join(tools))

    assert len(answers) == 2, answers
    assert (
        len({answer for answers_from_one in answers.values() for answer in answers_from_one}) == 1
    )


def test_the_first_request_to_a_replica_is_the_same_as_the_hundredth() -> None:
    """There is no warm-up state, which is the other direction of the same claim.

    A server that built something per caller on first contact would answer the
    first request differently from the rest — and with round-robin routing, would
    do it again on the other replica. The token is the only thing carried between
    requests, which is ADR-0008's *the token is the only seam*, executed.
    """
    minted = mint("priya.raman", ["erp.read"])

    def listing() -> tuple[list[str], str]:
        """Everything about the answer that is not a function of the clock.

        ``ttlMs`` is excluded deliberately: it is *"the remaining token
        lifetime"*, so it falls between one request and the next by design, and
        asserting on it here would be asserting that time does not pass.
        """
        result = rpc.result(rpc.post("tools/list", token=minted.access_token))
        return sorted(tool["name"] for tool in result["tools"]), result["cacheScope"]

    first = listing()
    for _ in range(REQUESTS):
        assert listing() == first
