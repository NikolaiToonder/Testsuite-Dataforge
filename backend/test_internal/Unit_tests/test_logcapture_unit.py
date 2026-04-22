import io
from app.internal.logcapture import ForwardStream


class TestForwardStream:
    def test_writes_to_callback(self):
        outputs = []
        stream = ForwardStream(lambda s: outputs.append(s), None)
        
        stream.write("test message")
        
        assert outputs == ["test message"]

    def test_writes_to_original_stream_when_provided(self):
        original = io.StringIO()
        outputs = []
        stream = ForwardStream(lambda s: outputs.append(s), original)
        
        stream.write("test message")
        
        assert outputs == ["test message"]
        assert original.getvalue() == "test message"

    def test_flush_without_original_stream(self):
        outputs = []
        stream = ForwardStream(lambda s: outputs.append(s), None)
        
        # Should not raise
        stream.flush()

    def test_flush_with_original_stream(self):
        original = io.StringIO()
        stream = ForwardStream(lambda s: None, original)
        
        stream.write("data")
        stream.flush()
        
        assert original.getvalue() == "data"
