from core.todo.ai import DedupResponseParser


def test_response_parser_converts_json_to_decisions() -> None:
    parser = DedupResponseParser()

    ai_json = (
        '{"decisions":[{"index":0,"action":"keep","target_list":null,'
        '"merged_title":null,"rationale":"Looks unique"}]}'
    )

    entries = [
        {"task": {"id": "task-1"}, "task_key": "task-1", "cluster_index": 3},
    ]

    decisions, errors = parser.parse(ai_json, entries)

    assert not errors
    assert "task-1" in decisions
    decision = decisions["task-1"]
    assert decision.raw_action == "keep"
    assert decision.cluster_index == 3


def test_response_parser_reports_errors() -> None:
    parser = DedupResponseParser()
    decisions, errors = parser.parse("{}", [])
    assert not decisions
    assert errors
