import threading
from ai4se_agent.core.interrupt import InterruptChannel


def test_stop_requested_defaults_false():
    ch = InterruptChannel()
    assert not ch.stop_requested.is_set()


def test_request_stop_sets_event():
    ch = InterruptChannel()
    ch.request_stop()
    assert ch.stop_requested.is_set()


def test_send_approval_approve():
    ch = InterruptChannel()
    ch.send_approval(True)
    response = ch.approval_response.get(timeout=1)
    assert response == "approve"


def test_send_approval_reject():
    ch = InterruptChannel()
    ch.send_approval(False)
    response = ch.approval_response.get(timeout=1)
    assert response == "reject"


def test_approval_response_blocks_until_data():
    ch = InterruptChannel()
    results: list[str] = []

    def waiter():
        results.append(ch.approval_response.get(timeout=5))

    t = threading.Thread(target=waiter)
    t.start()

    ch.send_approval(True)
    t.join(timeout=2)

    assert results == ["approve"]


def test_stop_requested_is_thread_safe():
    ch = InterruptChannel()
    results: list[bool] = []

    def checker():
        results.append(ch.stop_requested.is_set())

    ch.request_stop()
    t = threading.Thread(target=checker)
    t.start()
    t.join(timeout=1)

    assert results == [True]
