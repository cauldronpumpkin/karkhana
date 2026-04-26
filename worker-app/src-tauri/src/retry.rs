use crate::api::ApiError;
use std::time::Duration;

pub async fn with_retry<F, Fut, T>(
    mut operation: F,
    max_retries: u32,
) -> Result<T, ApiError>
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = Result<T, ApiError>>,
{
    let mut last_error = None;
    for attempt in 0..max_retries {
        match operation().await {
            Ok(result) => return Ok(result),
            Err(ApiError::Http { status, .. }) if status >= 400 && status < 500 && status != 429 => {
                return Err(last_error.unwrap_or(ApiError::Http { status, body: String::new() }));
            }
            Err(e) => {
                last_error = Some(e);
                if attempt < max_retries - 1 {
                    tokio::time::sleep(Duration::from_secs(2u64.pow(attempt))).await;
                }
            }
        }
    }
    Err(last_error.unwrap_or(ApiError::Network("Max retries exceeded".to_string())))
}
