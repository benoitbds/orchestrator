from sqlmodel import SQLModel, Session, create_engine
from orchestrator.storage import models, services

def setup_db():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_save_blob_and_reuse_hash():
    engine = setup_db()
    with Session(engine) as session:
        blob_id = services.save_blob("txt", {"a": 1}, session=session)
        blob = session.get(models.BlobRef, blob_id)
        assert blob.sha256
        assert blob.data == {"a": 1}


def test_span_lifecycle_and_message_and_tools():
    engine = setup_db()
    with Session(engine) as session:
        run = models.Run(id="run1")
        session.add(run)
        session.commit()
        span_id = services.start_span("run1", "agent", session=session)
        services.end_span(span_id, status="done", session=session)
        span = session.get(models.AgentSpan, span_id)
        assert span.status == "done" and span.end_ts is not None
        msg_id = services.save_message(
            "run1",
            role="user",
            content="hi",
            agent_name="agent",
            tokens={"prompt": 1, "completion": 2, "total": 3},
            session=session,
        )
        msg = session.get(models.Message, msg_id)
        assert msg.prompt_tokens == 1 and msg.content_ref
        call_id = services.save_tool_call("run1", "agent", "tool", session=session)
        result_id = services.save_tool_result(call_id, "ok", session=session)
        result = session.get(models.ToolResult, result_id)
        assert result.run_id == "run1"


def test_save_message_with_content_ref():
    engine = setup_db()
    with Session(engine) as session:
        run = models.Run(id="run2")
        session.add(run)
        session.commit()
        ref = services.save_blob("txt", "hello", session=session)
        msg_id = services.save_message("run2", role="assistant", content_ref=ref, session=session)
        msg = session.get(models.Message, msg_id)
        assert msg.content_ref == ref and msg.role == "assistant"


def test_end_span_missing_raises():
    engine = setup_db()
    with Session(engine) as session:
        try:
            services.end_span("missing", session=session)
        except ValueError as e:
            assert "span not found" in str(e)
        else:
            assert False, "expected ValueError"


def test_tool_result_missing_call_raises():
    engine = setup_db()
    with Session(engine) as session:
        run = models.Run(id="run1")
        session.add(run)
        session.commit()
        try:
            services.save_tool_result("missing", "ok", session=session)
        except ValueError as e:
            assert "tool call not found" in str(e)
        else:
            assert False, "expected ValueError"
