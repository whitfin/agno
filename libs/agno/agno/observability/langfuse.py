
from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime
from os import getenv
try:
    from langfuse import Langfuse
except ImportError:
    raise ImportError("`langfuse` not installed. Please install using `pip install langfuse`")


@dataclass
class LangfuseObservability:
    public_key: str
    secret_key: str
    host: Optional[str] = None
    release: Optional[str] = None
    debug: Optional[bool] = False
    threads: Optional[int] = None
    max_retries: Optional[int] = None
    timeout: Optional[int] = None
    sample_rate: Optional[float] = None
    
    client: Optional[Langfuse] = None
    
    _current_trace_id: Optional[str] = None
    _current_span_id: Optional[str] = None
    _current_generation_id: Optional[str] = None

    
    def get_client(self):
        
        if self.client is not None:
            return self.client
        
        self.public_key = self.public_key or getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = self.secret_key or getenv("LANGFUSE_SECRET_KEY")
        self.host = self.host or getenv("LANGFUSE_HOST")
        self.release = self.release or getenv("LANGFUSE_RELEASE")
        self.debug = self.debug or getenv("LANGFUSE_DEBUG")
        self.threads = self.threads or getenv("LANGFUSE_THREADS")
        self.max_retries = self.max_retries or getenv("LANGFUSE_MAX_RETRIES")
        self.timeout = self.timeout or getenv("LANGFUSE_TIMEOUT")
        self.sample_rate = self.sample_rate or getenv("LANGFUSE_SAMPLE_RATE")
 
        langfuse = Langfuse(
            public_key=self.public_key,
            private_key=self.private_key,
            host=self.host,
            release=self.release,
            debug=self.debug,
            threads=self.threads,
            max_retries=self.max_retries,
            timeout=self.timeout,
            sample_rate=self.sample_rate,
        )
        self.client = langfuse
        return self.client
    
    def trace(self, name: Optional[str] = None, input_dict: Optional[Dict[str, Any]] = None, output_dict: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs):
        self._current_span = None
        trace = self.get_client().trace(id=id, name=name, input=input_dict, output=output_dict, metadata=metadata, **kwargs)
        self._current_trace_id = trace.id

    def start_span(self, name: str, input_dict: Optional[Dict[str, Any]] = None, **kwargs):
        start_time = datetime.now()
        span = self.get_client().span(trace_id=self._current_trace_id, name=name, start_time=start_time, input=input_dict, **kwargs)
        self._current_span_id = span.id
        
    def end_span(self, output_dict: Optional[Dict[str, Any]] = None, **kwargs):
        end_time = datetime.now()
        self.get_client().span(id=self._current_span_id, output=output_dict, end_time=end_time, **kwargs)
        self._current_span_id = None
        
    def start_generation(self, name: str, model: str, input_dict: Optional[Dict[str, Any]] = None, **kwargs):
        start_time = datetime.now()
        generation = self.get_client().generation(trace_id=self._current_trace_id, name=name, model=model, input=input_dict, start_time=start_time, **kwargs)
        self._current_generation_id = generation.id
        
    def end_generation(self, output_dict: Optional[Dict[str, Any]] = None, usage_details_dict: Optional[Dict[str, Any]] = None, **kwargs):
        end_time = datetime.now()   
        self.get_client().generation(id=self._current_generation_id, output=output_dict, usage_details=usage_details_dict, end_time=end_time, **kwargs)
        self._current_generation_id = None
    
    def create_event(self, name: str, input_dict: Optional[Dict[str, Any]] = None, output_dict: Optional[Dict[str, Any]] = None, **kwargs):
        start_time = datetime.now()
        self.get_client().event(trace_id=self._current_trace_id, parent_observation_id=self._current_span_id, name=self.name, start_time=start_time, input=input_dict, output=output_dict, **kwargs)
    