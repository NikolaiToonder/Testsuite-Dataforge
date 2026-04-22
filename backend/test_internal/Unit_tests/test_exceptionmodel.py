from app.internal.exceptionmodel import exception_to_model, ExceptionModel, FrameDetail


class TestExceptionToModel:
    def test_basic_exception_conversion(self):
        try:
            raise ValueError("test error message")
        except ValueError as e:
            result = exception_to_model(e)
        
        assert isinstance(result, ExceptionModel)
        assert result.exceptionType == "ValueError"
        assert result.message == "test error message"
        assert len(result.stackTrace) > 0

    def test_stacktrace_contains_frame_details(self):
        try:
            raise RuntimeError("runtime error")
        except RuntimeError as e:
            result = exception_to_model(e)
        
        assert all(isinstance(frame, FrameDetail) for frame in result.stackTrace)
        assert all(frame.filename for frame in result.stackTrace)
        assert all(frame.frameName for frame in result.stackTrace)


class TestExceptionPathReplacement:
    def test_replace_paths_modifies_filenames(self):
        try:
            raise Exception("test")
        except Exception as e:
            result = exception_to_model(
                e,
                replace_paths=[("/original/path", "/new/path")]
            )
        
        # All frames should have paths replaced if they matched original
        for frame in result.stackTrace:
            assert "/original/path" not in frame.filename
