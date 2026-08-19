"""Two replicas, no sticky routing, and nothing remembered between them.

Map constraint `#5`. The reason there are two rather than one is that a single
replica makes statelessness unfalsifiable: a server that remembered everything
would pass every other assertion in this repository.

**The asterisk is stated rather than buried.** ADR-0008 conceded that the
protocol package serves both eras from one endpoint with no way to disable
either, so sessions re-enter through a door this project does not control.
`stateless_http=True` closes the half that is ours: legacy callers get throwaway
per-request sessions, no session identifier is issued, and nothing is remembered
between requests. The normative register's *Statelessness across both legs*
interpretation carries the reading.
"""

from collections import Counter
from pathlib import Path

import httpx2

import rpc
from tokens import mint

REQUESTS = 12
"""Enough that a round robin over two upstreams cannot land on one by accident."""

REPOSITORY = Path(__file__).resolve().parents[2]
"""The checkout, for the two committed files the precondition below is read from."""

GATEWAY_CONFIGURATION = REPOSITORY / "gateway" / "nginx.conf"
COMPOSE = REPOSITORY / "compose.yaml"

MOUNT = "./gateway/nginx.conf:/etc/nginx/nginx.conf:ro"
"""Where Compose puts that configuration, and the link the second half asserts.

The whole file rather than a fragment in `conf.d/`, because the directive this
is about is a main-context one.
"""


def _served_by(response: httpx2.Response) -> str:
    """Which replica answered, as the gateway reports it."""
    replica = response.headers.get(rpc.SERVED_BY_HEADER)
    assert replica is not None, "the gateway did not report an upstream"
    return replica


def test_the_gateway_runs_a_single_worker() -> None:
    """The precondition every assertion below depends on, held by a test rather than a note.

    **Round-robin state is per worker.** Several workers is several independent
    rotations, and twelve requests measured 10/2 before `worker_processes 1` was
    set. The affinity assertion below would still pass under that — two replicas
    would still both appear — while having stopped measuring what it is named
    for. **The failure mode is not a red test; it is a green one that has quietly
    stopped asserting**, which is the reason this is a test and not a sentence in
    `gateway/README.md`.

    **Two assertions, because the chain has two links.** The directive is in the
    committed configuration, and the committed configuration is only the running
    gateway's because `compose.yaml` mounts it there. Asserting the first alone
    would leave a mount change breaking the link in silence.

    Read from the checkout rather than from the running container, deliberately.
    `docker compose exec gateway nginx -T` would assert the process instead, and
    it would put a docker invocation inside a suite that otherwise speaks only
    HTTP. The committed file is what Compose mounts, and that is the level the
    rest of this repository checks at — the same move as the seed's rendering
    checks, which read committed artifacts rather than a running database.
    """
    configuration = GATEWAY_CONFIGURATION.read_text(encoding="utf-8")
    assert "\nworker_processes 1;" in configuration, (
        "the gateway's rotation is only observable with one worker; "
        f"{GATEWAY_CONFIGURATION} no longer sets worker_processes 1"
    )

    compose = COMPOSE.read_text(encoding="utf-8")
    assert MOUNT in compose, (
        f"{COMPOSE} no longer mounts {GATEWAY_CONFIGURATION.name} at /etc/nginx/nginx.conf, "
        "so the directive asserted above is not the running gateway's"
    )


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
    # Both, and neither dominant. **Not an exact split**, deliberately: an even
    # count is the *gateway's* arithmetic, and one upstream retry or a moment of
    # mark-down would make it uneven while every claim this row is about still
    # held. What falsifies "no sticky routing" is a caller reaching one replica
    # and staying there, and a third of the requests is far below anything
    # affinity could produce.
    assert min(replicas.values()) >= REQUESTS // 3, replicas


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


def test_the_first_request_is_the_same_as_the_last() -> None:
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
