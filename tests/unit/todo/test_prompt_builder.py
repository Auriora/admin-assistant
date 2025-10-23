from core.todo.ai import PromptBuilder
from core.todo.config import TodoDedupConfig


def test_prompt_builder_serializes_tasks() -> None:
    config = TodoDedupConfig(user_emails={"user@example.com"})
    builder = PromptBuilder(config)

    tasks = [
        {
            "title": "Follow up with Contoso",
            "task_list": "Clients",
            "body": "Send summary email",
            "linked_message_preview": "Preview text",
        }
    ]

    prompt = builder.build_prompt(tasks, ["Clients", "Personal"])

    assert "Follow up with Contoso" in prompt
    assert '"Clients"' in prompt
    assert "user@example.com" in prompt
    assert "decisions" in prompt

