/// <reference types="node" />

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { mergeSessionSummaryAndMessage } from "./sessionMessagePagination.js";
import type { SessionMessage, SessionPayload, SessionSummary } from "../shared/types.js";

function createSummary(): SessionSummary {
  return {
    key: "role:mira",
    created_at: "2026-09-07T11:00:00+08:00",
    updated_at: "2026-09-07T11:00:00+08:00",
    last_consolidated: 0,
    metadata: { role_id: "mira" },
  };
}

function createSession(messages: SessionMessage[]): SessionPayload {
  return {
    ...createSummary(),
    messages,
  };
}

describe("mergeSessionSummaryAndMessage", () => {
  it("keeps the user turn when the assistant reply carries the same client message id", () => {
    const currentSession = createSession([
      {
        id: "role:mira:5",
        seq: 5,
        role: "user",
        content: "刚发出去的消息",
        metadata: { client_message_id: "client-message-1" },
      },
      {
        role: "assistant",
        content: "流式回复",
        streaming: true,
      },
    ]);
    const committedReply: SessionMessage = {
      id: "role:mira:6",
      seq: 6,
      role: "assistant",
      content: "流式回复全文",
      metadata: { client_message_id: "client-message-1", turn_id: "turn-1" },
    };

    const merged = mergeSessionSummaryAndMessage(currentSession, createSummary(), committedReply);

    assert.deepEqual(
      merged.messages.map((message) => [message.role, message.id ?? ""]),
      [
        ["user", "role:mira:5"],
        ["assistant", "role:mira:6"],
      ],
    );
    assert.equal(merged.messages[0]?.content, "刚发出去的消息");
  });

  it("replaces the optimistic user turn with its persisted copy by client message id", () => {
    const currentSession = createSession([
      {
        id: "role:mira:4",
        seq: 4,
        role: "assistant",
        content: "上一条回复",
      },
      {
        role: "user",
        content: "刚发出去的消息",
        metadata: { client_message_id: "client-message-1" },
      },
    ]);
    const persistedUserMessage: SessionMessage = {
      id: "role:mira:5",
      seq: 5,
      role: "user",
      content: "刚发出去的消息",
      metadata: { client_message_id: "client-message-1" },
    };

    const merged = mergeSessionSummaryAndMessage(
      currentSession,
      createSummary(),
      persistedUserMessage,
    );

    assert.deepEqual(
      merged.messages.map((message) => [message.role, message.id ?? ""]),
      [
        ["assistant", "role:mira:4"],
        ["user", "role:mira:5"],
      ],
    );
  });
});
