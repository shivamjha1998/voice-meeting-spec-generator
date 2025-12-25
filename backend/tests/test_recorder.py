import pytest
from unittest.mock import MagicMock, patch
import os
from backend.bot.recorder import AudioRecorder

@pytest.fixture
def mock_pyaudio():
    with patch("backend.bot.recorder.pyaudio.PyAudio") as mock:
        # returns an instance
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        # Fix for wave error
        mock_instance.get_sample_size.return_value = 2
        # Fix for writeframes error (must return bytes)
        mock_instance.open.return_value.read.return_value = b'audio_chunk'
        yield mock_instance

@pytest.fixture
def mock_encryption():
    with patch("backend.bot.recorder.encrypt_data") as mock:
        mock.return_value = b"encrypted_bytes"
        yield mock

def test_recorder_initialization(mock_pyaudio):
    # Mock device finding
    mock_pyaudio.get_host_api_info_by_index.return_value = {'deviceCount': 1}
    mock_pyaudio.get_device_info_by_host_api_device_index.return_value = {
        'name': 'Built-in Microphone', 
        'maxInputChannels': 1,
        'maxOutputChannels': 0
    }
    
    recorder = AudioRecorder(filename="test.wav")
    assert recorder.is_recording is False
    assert recorder.filename == "test.wav"

def test_start_stop_recording(mock_pyaudio, mock_encryption):
    mock_pyaudio.get_host_api_info_by_index.return_value = {'deviceCount': 0}
    
    recorder = AudioRecorder(filename="test_output.wav")
    
    # Test Start
    recorder.start_recording()
    assert recorder.is_recording is True
    assert recorder.is_running is True
    # Verify stream opened
    mock_pyaudio.open.assert_called_once()
    
    # Validate stream read (loop runs in thread, so we simulate 1 chunk manually if we were testing loop)
    # But start_recording launches thread. We can check if thread started.
    assert recorder.thread.is_alive()
    
    # Test Stop
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        recorder.stop_recording()
        
    assert recorder.is_recording is False
    mock_pyaudio.open.return_value.stop_stream.assert_called()
    mock_pyaudio.open.return_value.close.assert_called()
    
    # Verify Encryption Called
    mock_encryption.assert_called()

def test_stream_generator(mock_pyaudio):
    mock_pyaudio.get_host_api_info_by_index.return_value = {'deviceCount': 0}
    recorder = AudioRecorder()
    
    # Fake queue
    recorder.audio_queue.put(b"chunk1")
    recorder.audio_queue.put(b"chunk2")
    recorder.is_running = False # Stop immediately after queue empty
    
    chunks = list(recorder.stream_audio())
    assert b"chunk1" in chunks
    assert b"chunk2" in chunks
