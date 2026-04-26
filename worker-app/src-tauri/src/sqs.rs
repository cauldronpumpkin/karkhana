use crate::types::WorkerCredentials;
use aws_sdk_sqs::Client;
use aws_sdk_sqs::config::{BehaviorVersion, Credentials, Region};
use serde_json::Value;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct SqsTransport {
    credentials: WorkerCredentials,
    client: Option<Client>,
}

pub struct SqsMessage {
    pub message_id: String,
    pub receipt_handle: String,
    pub body: String,
}

impl SqsTransport {
    pub fn new(credentials: WorkerCredentials) -> Self {
        SqsTransport {
            credentials,
            client: None,
        }
    }

    pub fn configured(&self) -> bool {
        self.credentials.command_queue_url.is_some()
    }

    async fn build_client(&self) -> Result<Client, String> {
        let region = self
            .credentials
            .region
            .as_deref()
            .unwrap_or("us-east-1");

        let mut config_builder = aws_sdk_sqs::Config::builder()
            .behavior_version(BehaviorVersion::latest())
            .region(Region::new(region.to_string()));

        if let (Some(access_key), Some(secret_key)) = (
            &self.credentials.access_key_id,
            &self.credentials.secret_access_key,
        ) {
            let creds = Credentials::new(
                access_key,
                secret_key,
                self.credentials.session_token.clone(),
                None,
                "worker-credentials",
            );
            config_builder = config_builder.credentials_provider(creds);
        }

        Ok(Client::from_conf(config_builder.build()))
    }

    pub async fn get_client(&self) -> Result<Client, String> {
        if let Some(ref client) = self.client {
            return Ok(client.clone());
        }
        self.build_client().await
    }

    pub async fn receive(&self) -> Result<Vec<SqsMessage>, String> {
        let queue_url = self
            .credentials
            .command_queue_url
            .as_ref()
            .ok_or_else(|| "command_queue_url not configured".to_string())?;

        let client = self.get_client().await?;

        let response = client
            .receive_message()
            .queue_url(queue_url)
            .max_number_of_messages(1)
            .wait_time_seconds(20)
            .visibility_timeout(30)
            .send()
            .await
            .map_err(|e| format!("SQS receive failed: {}", e))?;

        let messages = response
            .messages
            .unwrap_or_default()
            .into_iter()
            .map(|m| SqsMessage {
                message_id: m.message_id.unwrap_or_default(),
                receipt_handle: m.receipt_handle.unwrap_or_default(),
                body: m.body.unwrap_or_default(),
            })
            .collect();

        Ok(messages)
    }

    pub async fn delete(&self, message: &SqsMessage) -> Result<(), String> {
        let queue_url = self
            .credentials
            .command_queue_url
            .as_ref()
            .ok_or_else(|| "command_queue_url not configured".to_string())?;

        let client = self.get_client().await?;

        client
            .delete_message()
            .queue_url(queue_url)
            .receipt_handle(&message.receipt_handle)
            .send()
            .await
            .map_err(|e| format!("SQS delete failed: {}", e))?;

        Ok(())
    }

    pub async fn send_event(
        &self,
        worker_id: &str,
        event_type: &str,
        payload: &Value,
    ) -> Result<(), String> {
        let queue_url = match self.credentials.event_queue_url.as_ref() {
            Some(url) => url,
            None => return Ok(()),
        };

        let client = self.get_client().await?;

        let body = serde_json::json!({
            "worker_id": worker_id,
            "type": event_type,
            "payload": payload,
        });

        let work_item_id = payload
            .get("work_item_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");

        let timestamp_ms = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis();

        let dedup_id = format!(
            "{}:{}:{}:{}",
            worker_id, event_type, work_item_id, timestamp_ms
        );

        let group_id = format!("worker:{}", worker_id);

        client
            .send_message()
            .queue_url(queue_url)
            .message_body(serde_json::to_string(&body).unwrap_or_default())
            .message_group_id(group_id)
            .message_deduplication_id(dedup_id)
            .send()
            .await
            .map_err(|e| format!("SQS send_event failed: {}", e))?;

        Ok(())
    }
}
