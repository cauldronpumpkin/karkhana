use crate::api::ApiError;
use std::time::Duration;

/// Compute exponential backoff delay for a given attempt number (0-based).
/// Sequence: 1s, 2s, 4s, 8s, 16s, 30s max.
pub fn backoff_delay(attempt: u32) -> Duration {
    let seconds = 2u64.pow(attempt).min(30);
    Duration::from_secs(seconds)
}

/// Generic async retry wrapper with exponential backoff.
/// Calls `f` up to `max_attempts` times, returning the first Ok result.
/// Delays between attempts using [`backoff_delay`].
pub async fn with_backoff<F, Fut, T, E>(
    max_attempts: u32,
    mut f: F,
) -> Result<T, E>
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = Result<T, E>>,
{
    let mut last_err: Option<E> = None;
    for attempt in 1..=max_attempts {
        match f().await {
            Ok(val) => return Ok(val),
            Err(e) => {
                last_err = Some(e);
                if attempt < max_attempts {
                    tokio::time::sleep(backoff_delay(attempt - 1)).await;
                }
            }
        }
    }
    // SAFETY: loop always sets last_err at least once before reaching here
    Err(last_err.unwrap())
}

/// Existing retry helper for API calls (keeps original behaviour but uses
/// the new backoff_delay for consistency).
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
                    tokio::time::sleep(backoff_delay(attempt)).await;
                }
            }
        }
    }
    Err(last_error.unwrap_or(ApiError::Network("Max retries exceeded".to_string())))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn backoff_sequence() {
        assert_eq!(backoff_delay(0), Duration::from_secs(1));
        assert_eq!(backoff_delay(1), Duration::from_secs(2));
        assert_eq!(backoff_delay(2), Duration::from_secs(4));
        assert_eq!(backoff_delay(3), Duration::from_secs(8));
        assert_eq!(backoff_delay(4), Duration::from_secs(16));
        assert_eq!(backoff_delay(5), Duration::from_secs(30));
        assert_eq!(backoff_delay(6), Duration::from_secs(30));
        assert_eq!(backoff_delay(10), Duration::from_secs(30));
    }

    #[tokio::test]
    async fn with_backoff_returns_ok_on_first_attempt() {
        let result: Result<&str, &str> =
            with_backoff(3, || async { Ok("done") }).await;
        assert_eq!(result, Ok("done"));
    }

    #[tokio::test]
    async fn with_backoff_retries_on_err() {
        let mut calls = 0;
        let result: Result<&str, &str> = with_backoff(3, || {
            calls += 1;
            async move {
                if calls < 3 {
                    Err("fail")
                } else {
                    Ok("ok")
                }
            }
        })
        .await;
        assert_eq!(result, Ok("ok"));
        assert_eq!(calls, 3);
    }

    #[tokio::test]
    async fn with_backoff_exhausts_attempts() {
        let result: Result<&str, &str> =
            with_backoff(2, || async { Err("always fail") }).await;
        assert_eq!(result, Err("always fail"));
    }
}
