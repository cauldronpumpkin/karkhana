#[derive(Debug)]
pub enum WorkerError {
    Api(crate::api::ApiError),
    Io(std::io::Error),
    Config(String),
    Git(String),
    Agent(String),
    Structured(crate::types::WorkerFailure),
    OpenCode(crate::opencode_session::OpenCodeError),
    LiteLLM(crate::litellm::LiteLLMError),
    Sqs(String),
    CircuitBreaker(String),
}

impl std::fmt::Display for WorkerError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            WorkerError::Api(e) => write!(f, "API error: {e}"),
            WorkerError::Io(e) => write!(f, "IO error: {e}"),
            WorkerError::Config(msg) => write!(f, "Config error: {msg}"),
            WorkerError::Git(msg) => write!(f, "Git error: {msg}"),
            WorkerError::Agent(msg) => write!(f, "Agent error: {msg}"),
            WorkerError::Structured(failure) => {
                match serde_json::to_string(failure) {
                    Ok(text) => f.write_str(&text),
                    Err(_) => write!(f, "Structured error: {:?}", failure),
                }
            }
            WorkerError::OpenCode(e) => write!(f, "OpenCode error: {e}"),
            WorkerError::LiteLLM(e) => write!(f, "LiteLLM error: {e}"),
            WorkerError::Sqs(msg) => write!(f, "SQS error: {msg}"),
            WorkerError::CircuitBreaker(msg) => write!(f, "Circuit breaker: {msg}"),
        }
    }
}

impl std::error::Error for WorkerError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            WorkerError::Api(e) => Some(e),
            WorkerError::Io(e) => Some(e),
            _ => None,
        }
    }
}

impl From<crate::api::ApiError> for WorkerError {
    fn from(err: crate::api::ApiError) -> Self {
        WorkerError::Api(err)
    }
}

impl From<std::io::Error> for WorkerError {
    fn from(err: std::io::Error) -> Self {
        WorkerError::Io(err)
    }
}

impl From<crate::types::WorkerFailure> for WorkerError {
    fn from(err: crate::types::WorkerFailure) -> Self {
        WorkerError::Structured(err)
    }
}

impl From<crate::opencode_session::OpenCodeError> for WorkerError {
    fn from(err: crate::opencode_session::OpenCodeError) -> Self {
        WorkerError::OpenCode(err)
    }
}

impl From<crate::litellm::LiteLLMError> for WorkerError {
    fn from(err: crate::litellm::LiteLLMError) -> Self {
        WorkerError::LiteLLM(err)
    }
}
