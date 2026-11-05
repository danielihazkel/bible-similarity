"""A fake Message Batches client for the Claude jobs' tests (series L); nothing is sent."""

from __future__ import annotations

import json
from types import SimpleNamespace as NS


def msg(text, stop="end_turn", tin=100, tout=50):
    """A message as the SDK returns it: a thinking block, then the text."""
    return NS(
        stop_reason=stop,
        content=[NS(type="thinking", thinking=""), NS(type="text", text=text)],
        usage=NS(input_tokens=tin, output_tokens=tout),
    )


class FakeBatches:
    """`answers`: custom_id → a JSON-able answer, or None for an errored request. The batch
    ends after `rounds` polls."""

    def __init__(self, answers, rounds=1):
        self.answers, self.rounds, self.created, self.retrieved = answers, rounds, [], 0

    def create(self, requests):
        self.created.append(requests)
        return NS(id="msgbatch_1")

    def retrieve(self, batch_id):
        self.retrieved += 1
        done = self.retrieved > self.rounds
        return NS(
            processing_status="ended" if done else "in_progress",
            request_counts=NS(processing=0 if done else 1, succeeded=1 if done else 0),
        )

    def results(self, batch_id):
        for cid, ans in self.answers.items():
            if ans is None:
                yield NS(custom_id=cid, result=NS(type="errored"))
            else:
                text = ans if isinstance(ans, str) else json.dumps(ans)
                yield NS(custom_id=cid, result=NS(type="succeeded", message=msg(text)))


def fake_client(answers, rounds=1):
    batches = FakeBatches(answers, rounds)
    return NS(messages=NS(batches=batches)), batches
