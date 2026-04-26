use crate::types::{
    ClaimRequest, ClaimResponse, JobCompleteRequest, JobFailRequest, JobUpdateRequest,
    PairingResponse, RegisterRequest, RegisterResponse,
};
use reqwest;
use serde_json::Value;

#[derive(Debug, Clone)]
pub struct ApiClient {
    client: reqwest::Client,
    api_base: String,
    token: String,
    worker_auth_token: Option<String>,
}

#[derive(Debug)]
pub enum ApiError {
    Network(String),
    Http { status: u16, body: String },
    Json(String),
    Auth(String),
}

impl std::fmt::Display for ApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ApiError::Network(msg) => write!(f, "Network error: {msg}"),
            ApiError::Http { status, body } => write!(f, "HTTP {status}: {body}"),
            ApiError::Json(msg) => write!(f, "JSON error: {msg}"),
            ApiError::Auth(msg) => write!(f, "Auth error: {msg}"),
        }
    }
}

impl std::error::Error for ApiError {}

impl ApiClient {
    pub fn new(api_base: String, token: String) -> Self {
        ApiClient {
            client: reqwest::Client::new(),
            api_base: api_base.trim_end_matches('/').to_string(),
            token,
            worker_auth_token: None,
        }
    }

    pub fn with_worker_auth_token(mut self, token: String) -> Self {
        self.worker_auth_token = Some(token);
        self
    }

    fn headers(&self) -> reqwest::header::HeaderMap {
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert(
            reqwest::header::CONTENT_TYPE,
            reqwest::header::HeaderValue::from_static("application/json"),
        );
        if !self.token.is_empty() {
            if let Ok(value) = reqwest::header::HeaderValue::from_str(&format!("Bearer {}", self.token)) {
                headers.insert(reqwest::header::AUTHORIZATION, value);
            }
        }
        if let Some(ref wat) = self.worker_auth_token {
            if let Ok(value) = reqwest::header::HeaderValue::from_str(wat) {
                headers.insert("X-IdeaRefinery-Worker-Token", value);
            }
        }
        headers
    }

    pub async fn get(&self, path: &str) -> Result<Value, ApiError> {
        let url = format!("{}{}", self.api_base, path);
        let response = self
            .client
            .get(&url)
            .headers(self.headers())
            .timeout(std::time::Duration::from_secs(60))
            .send()
            .await
            .map_err(|e| ApiError::Network(e.to_string()))?;
        let status = response.status();
        let body_text = response.text().await.map_err(|e| ApiError::Network(e.to_string()))?;
        if !status.is_success() {
            return Err(ApiError::Http {
                status: status.as_u16(),
                body: body_text,
            });
        }
        serde_json::from_str(&body_text).map_err(|e| ApiError::Json(e.to_string()))
    }

    pub async fn post<B: serde::Serialize>(&self, path: &str, body: &B) -> Result<Value, ApiError> {
        let url = format!("{}{}", self.api_base, path);
        let response = self
            .client
            .post(&url)
            .headers(self.headers())
            .json(body)
            .timeout(std::time::Duration::from_secs(60))
            .send()
            .await
            .map_err(|e| ApiError::Network(e.to_string()))?;
        let status = response.status();
        let body_text = response.text().await.map_err(|e| ApiError::Network(e.to_string()))?;
        if !status.is_success() {
            return Err(ApiError::Http {
                status: status.as_u16(),
                body: body_text,
            });
        }
        serde_json::from_str(&body_text).map_err(|e| ApiError::Json(e.to_string()))
    }

    pub async fn register(&self, req: &RegisterRequest) -> Result<RegisterResponse, ApiError> {
        let value = self.post("/api/local-workers/register", req).await?;
        serde_json::from_value(value).map_err(|e| ApiError::Json(e.to_string()))
    }

    pub async fn get_registration(
        &self,
        request_id: &str,
        pairing_token: &str,
    ) -> Result<PairingResponse, ApiError> {
        let value = self
            .get(&format!(
                "/api/local-workers/registrations/{}?pairing_token={}",
                request_id, pairing_token
            ))
            .await?;
        serde_json::from_value(value).map_err(|e| ApiError::Json(e.to_string()))
    }

    pub async fn claim_job(&self, worker_id: &str, capabilities: &[String]) -> Result<Option<ClaimResponse>, ApiError> {
        let value = self
            .post("/api/worker/claim", &ClaimRequest {
                worker_id: worker_id.to_string(),
                capabilities: capabilities.to_vec(),
            })
            .await?;
        let resp: ClaimResponse = serde_json::from_value(value).map_err(|e| ApiError::Json(e.to_string()))?;
        Ok(resp.claim.map(|c| ClaimResponse { claim: Some(c) }))
    }

    pub async fn heartbeat_job(&self, job_id: &str, req: &JobUpdateRequest) -> Result<(), ApiError> {
        self.post(&format!("/api/worker/jobs/{}/heartbeat", job_id), req)
            .await?;
        Ok(())
    }

    pub async fn complete_job(&self, job_id: &str, req: &JobCompleteRequest) -> Result<(), ApiError> {
        self.post(&format!("/api/worker/jobs/{}/complete", job_id), req)
            .await?;
        Ok(())
    }

    pub async fn fail_job(&self, job_id: &str, req: &JobFailRequest) -> Result<(), ApiError> {
        self.post(&format!("/api/worker/jobs/{}/fail", job_id), req)
            .await?;
        Ok(())
    }
}
