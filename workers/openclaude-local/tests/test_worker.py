import json

from worker import OpenClaudeAdapter, SqsTransport


class FakeSqs:
    def __init__(self):
        self.sent = []
        self.deleted = []

    def receive_message(self, **kwargs):
        return {"Messages": [{"Body": json.dumps({"type": "job_available", "job_type": "repo_index"}), "ReceiptHandle": "r1"}]}

    def delete_message(self, **kwargs):
        self.deleted.append(kwargs)

    def send_message(self, **kwargs):
        self.sent.append(kwargs)


def test_openclaude_command_includes_control_flags():
    command = OpenClaudeAdapter(
        {
            "agent": "Explore",
            "model": "sonnet",
            "permission_mode": "acceptEdits",
            "output_format": "json",
            "max_budget_usd": "1.50",
            "system_prompt": "Stay scoped.",
            "additional_dirs": ["../shared"],
        }
    ).command("Do the task")

    assert command[:2] == ["openclaude", "-p"]
    assert "--agent" in command
    assert "--permission-mode" in command
    assert "--max-budget-usd" in command
    assert "--add-dir" in command
    assert command[-1] == "Do the task"


def test_sqs_transport_receive_delete_and_send_event():
    fake = FakeSqs()
    transport = SqsTransport(
        {
            "credentials": {
                "command_queue_url": "commands",
                "event_queue_url": "events",
                "region": "us-east-1",
            }
        },
        sqs_client=fake,
    )

    messages = transport.receive()
    transport.delete(messages[0])
    transport.send_event("worker-1", "heartbeat", {"work_item_id": "job-1"})

    assert messages[0]["ReceiptHandle"] == "r1"
    assert fake.deleted[0]["QueueUrl"] == "commands"
    assert fake.sent[0]["QueueUrl"] == "events"
    assert fake.sent[0]["MessageGroupId"] == "worker:worker-1"
