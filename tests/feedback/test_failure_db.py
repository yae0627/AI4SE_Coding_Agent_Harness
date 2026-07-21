from ai4se_agent.feedback.failure_db import FailureDB

def test_failure_db_save_and_query(tmp_path):
    db = FailureDB(db_path=str(tmp_path / "test_failure.db"))
    db.record_failure("logic_error", "Missing null check on order_id", "Add guard clause before query")
    results = db.query_similar("logic_error")
    assert len(results) >= 1
    assert results[0]["failure_type"] == "logic_error"
