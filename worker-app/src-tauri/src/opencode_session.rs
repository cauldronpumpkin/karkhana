use reqwest;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::time::Duration;

#[derive(Debug, Clone)]
pub struct OpenCodeClient {
    client: reqwest::Client,
    base_url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    pub id: String,
    #[serde(default)]
    pub title: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub healthy: bool,
    pub version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileDiff {
    #[serde(flatten)]
    pub data: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionStatus {
    #[serde(flatten)]
    pub data: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageResponse {
    pub info: Value,
    pub parts: Vec<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateSessionRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SendMessageRequest {
    pub parts: Vec<MessagePart>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<ModelRef>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessagePart {
    #[serde(rename = "type")]
    pub part_type: String,
    #[serde(default)]
    pub text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelRef {
    pub provider_id: String,
    pub model_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionResponse {
    pub response: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub remember: Option<bool>,
}

#[derive(Debug)]
pub enum OpenCodeError {
    Network(String),
    Http { status: u16, body: String },
    Json(String),
}

impl std::fmt::Display for OpenCodeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OpenCodeError::Network(msg) => write!(f, "Network error: {msg}"),
            OpenCodeError::Http { status, body } => write!(f, "HTTP {status}: {body}"),
            OpenCodeError::Json(msg) => write!(f, "JSON error: {msg}"),
        }
    }
}

impl std::error::Error for OpenCodeError {}

impl OpenCodeClient {
    pub fn new(base_url: &str) -> Self {
        OpenCodeClient {
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(300))
                .build()
                .unwrap_or_default(),
            base_url: base_url.trim_end_matches('/').to_string(),
        }
    }

    pub async fn health(&self) -> Result<HealthResponse, OpenCodeError> {
        let val = self.get_json("/global/health").await?;
        serde_json::from_value(val).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    pub async fn create_session(&self, title: &str) -> Result<Session, OpenCodeError> {
        let body = CreateSessionRequest {
            title: if title.is_empty() {
                None
            } else {
                Some(title.to_string())
            },
        };
        let val = self.post_json("/session", &body).await?;
        serde_json::from_value(val).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    pub async fn get_session(&self, session_id: &str) -> Result<Session, OpenCodeError> {
        let path = format!("/session/{session_id}");
        let val = self.get_json(&path).await?;
        serde_json::from_value(val).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    pub async fn delete_session(&self, session_id: &str) -> Result<bool, OpenCodeError> {
        let path = format!("/session/{session_id}");
        let val = self.delete_json(&path).await?;
        serde_json::from_value(val).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    pub async fn abort_session(&self, session_id: &str) -> Result<bool, OpenCodeError> {
        let path = format!("/session/{session_id}/abort");
        let val = self.post_json(&path, &serde_json::json!({})).await?;
        serde_json::from_value(val).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    pub async fn send_message(
        &self,
        session_id: &str,
        req: &SendMessageRequest,
    ) -> Result<MessageResponse, OpenCodeError> {
        let path = format!("/session/{session_id}/message");
        let val = self.post_json(&path, req).await?;
        serde_json::from_value(val).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    pub async fn send_prompt_async(
        &self,
        session_id: &str,
        req: &SendMessageRequest,
    ) -> Result<(), OpenCodeError> {
        let path = format!("/session/{session_id}/prompt_async");
        self.post_json_no_response(&path, req).await
    }

    pub async fn list_messages(
        &self,
        session_id: &str,
    ) -> Result<Vec<MessageResponse>, OpenCodeError> {
        let path = format!("/session/{session_id}/message");
        let val = self.get_json(&path).await?;
        serde_json::from_value(val).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    pub async fn get_diff(&self, session_id: &str) -> Result<Vec<FileDiff>, OpenCodeError> {
        let path = format!("/session/{session_id}/diff");
        let val = self.get_json(&path).await?;
        serde_json::from_value(val).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    pub async fn get_all_session_status(
        &self,
    ) -> Result<HashMap<String, SessionStatus>, OpenCodeError> {
        let val = self.get_json("/session/status").await?;
        serde_json::from_value(val).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    pub async fn respond_permission(
        &self,
        session_id: &str,
        permission_id: &str,
        response: &str,
    ) -> Result<bool, OpenCodeError> {
        let path = format!("/session/{session_id}/permissions/{permission_id}");
        let body = PermissionResponse {
            response: response.to_string(),
            remember: None,
        };
        let val = self.post_json(&path, &body).await?;
        serde_json::from_value(val).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    async fn get_json(&self, path: &str) -> Result<Value, OpenCodeError> {
        let url = format!("{}{path}", self.base_url);
        let resp = self
            .client
            .get(&url)
            .send()
            .await
            .map_err(|e| OpenCodeError::Network(e.to_string()))?;
        let status = resp.status().as_u16();
        let body = resp
            .text()
            .await
            .map_err(|e| OpenCodeError::Network(e.to_string()))?;
        if !(200..300).contains(&status) {
            return Err(OpenCodeError::Http { status, body });
        }
        serde_json::from_str(&body).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    async fn post_json<B: Serialize>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<Value, OpenCodeError> {
        let url = format!("{}{path}", self.base_url);
        let resp = self
            .client
            .post(&url)
            .json(body)
            .send()
            .await
            .map_err(|e| OpenCodeError::Network(e.to_string()))?;
        let status = resp.status().as_u16();
        let text = resp
            .text()
            .await
            .map_err(|e| OpenCodeError::Network(e.to_string()))?;
        if !(200..300).contains(&status) {
            return Err(OpenCodeError::Http { status, body: text });
        }
        if text.is_empty() {
            return Ok(Value::Null);
        }
        serde_json::from_str(&text).map_err(|e| OpenCodeError::Json(e.to_string()))
    }

    async fn post_json_no_response<B: Serialize>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<(), OpenCodeError> {
        let url = format!("{}{path}", self.base_url);
        let resp = self
            .client
            .post(&url)
            .json(body)
            .send()
            .await
            .map_err(|e| OpenCodeError::Network(e.to_string()))?;
        let status = resp.status().as_u16();
        if !(200..300).contains(&status) {
            let text = resp
                .text()
                .await
                .map_err(|e| OpenCodeError::Network(e.to_string()))?;
            return Err(OpenCodeError::Http { status, body: text });
        }
        Ok(())
    }

    async fn delete_json(&self, path: &str) -> Result<Value, OpenCodeError> {
        let url = format!("{}{path}", self.base_url);
        let resp = self
            .client
            .delete(&url)
            .send()
            .await
            .map_err(|e| OpenCodeError::Network(e.to_string()))?;
        let status = resp.status().as_u16();
        let body = resp
            .text()
            .await
            .map_err(|e| OpenCodeError::Network(e.to_string()))?;
        if !(200..300).contains(&status) {
            return Err(OpenCodeError::Http { status, body });
        }
        if body.is_empty() {
            return Ok(Value::Null);
        }
        serde_json::from_str(&body).map_err(|e| OpenCodeError::Json(e.to_string()))
    }
}
