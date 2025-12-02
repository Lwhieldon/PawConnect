# Terraform Outputs for PawConnect AI - Production Configuration

# =============================================================================
# CLOUD RUN SERVICES
# =============================================================================

output "cloud_run_url" {
  description = "URL of the deployed Cloud Run main agent service"
  value       = google_cloud_run_service.pawconnect_main_agent.status[0].url
}

output "webhook_url" {
  description = "URL of the deployed Dialogflow webhook service"
  value       = google_cloud_run_service.pawconnect_webhook.status[0].url
}

output "cloud_run_service_name" {
  description = "Name of the Cloud Run main agent service"
  value       = google_cloud_run_service.pawconnect_main_agent.name
}

output "webhook_service_name" {
  description = "Name of the Dialogflow webhook service"
  value       = google_cloud_run_service.pawconnect_webhook.name
}

# =============================================================================
# SERVICE ACCOUNT
# =============================================================================

output "service_account_email" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.cloud_run_sa.email
}

# =============================================================================
# REDIS (MEMORYSTORE)
# =============================================================================

output "redis_host" {
  description = "Internal IP address of the Redis instance"
  value       = google_redis_instance.pawconnect_redis.host
}

output "redis_port" {
  description = "Port of the Redis instance"
  value       = google_redis_instance.pawconnect_redis.port
}

output "redis_instance_name" {
  description = "Name of the Redis instance"
  value       = google_redis_instance.pawconnect_redis.name
}

# =============================================================================
# VPC NETWORKING
# =============================================================================

output "vpc_network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.pawconnect_vpc.name
}

output "vpc_subnet_name" {
  description = "Name of the VPC subnet"
  value       = google_compute_subnetwork.pawconnect_subnet.name
}

output "vpc_connector_name" {
  description = "Name of the VPC Access Connector"
  value       = google_vpc_access_connector.pawconnect_connector.name
}

# =============================================================================
# PUB/SUB TOPICS & SUBSCRIPTIONS
# =============================================================================

output "pubsub_search_topic" {
  description = "Pub/Sub topic for search results"
  value       = google_pubsub_topic.search_results.id
}

output "pubsub_recommendations_topic" {
  description = "Pub/Sub topic for recommendations"
  value       = google_pubsub_topic.recommendations.id
}

output "pubsub_vision_topic" {
  description = "Pub/Sub topic for vision analysis"
  value       = google_pubsub_topic.vision_analysis.id
}

output "pubsub_workflow_topic" {
  description = "Pub/Sub topic for workflow events"
  value       = google_pubsub_topic.workflow_events.id
}

# =============================================================================
# CLOUD STORAGE BUCKETS
# =============================================================================

output "model_artifacts_bucket" {
  description = "Cloud Storage bucket for model artifacts"
  value       = google_storage_bucket.model_artifacts.name
}

output "build_artifacts_bucket" {
  description = "Cloud Storage bucket for build artifacts"
  value       = google_storage_bucket.build_artifacts.name
}

output "pet_images_bucket" {
  description = "Cloud Storage bucket for pet images"
  value       = google_storage_bucket.pet_images.name
}

# =============================================================================
# SECRET MANAGER
# =============================================================================

output "rescuegroups_secret_id" {
  description = "Secret Manager secret ID for RescueGroups API key"
  value       = google_secret_manager_secret.rescuegroups_api_key.secret_id
}

output "redis_password_secret_id" {
  description = "Secret Manager secret ID for Redis password"
  value       = google_secret_manager_secret.redis_password.secret_id
}

output "dialogflow_agent_secret_id" {
  description = "Secret Manager secret ID for Dialogflow agent ID"
  value       = google_secret_manager_secret.dialogflow_agent_id.secret_id
}

# =============================================================================
# PROJECT CONFIGURATION
# =============================================================================

output "project_id" {
  description = "Google Cloud Project ID"
  value       = var.project_id
}

output "region" {
  description = "Google Cloud region"
  value       = var.region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# =============================================================================
# MONITORING
# =============================================================================

output "notification_channel_id" {
  description = "Monitoring notification channel ID"
  value       = google_monitoring_notification_channel.email.id
}

output "main_agent_uptime_check_id" {
  description = "Main agent uptime check ID"
  value       = google_monitoring_uptime_check_config.health_check.id
}

output "webhook_uptime_check_id" {
  description = "Webhook uptime check ID"
  value       = google_monitoring_uptime_check_config.webhook_health_check.id
}

# =============================================================================
# DEPLOYMENT SUMMARY
# =============================================================================

output "deployment_summary" {
  description = "Summary of the deployment with key URLs and information"
  value = {
    main_agent_url     = google_cloud_run_service.pawconnect_main_agent.status[0].url
    webhook_url        = google_cloud_run_service.pawconnect_webhook.status[0].url
    health_endpoint    = "${google_cloud_run_service.pawconnect_main_agent.status[0].url}/health"
    webhook_endpoint   = "${google_cloud_run_service.pawconnect_webhook.status[0].url}/webhook"
    redis_host         = google_redis_instance.pawconnect_redis.host
    environment        = var.environment
    testing_mode       = "False"
    mock_apis          = "False"
  }
}

# =============================================================================
# NEXT STEPS
# =============================================================================

output "next_steps" {
  description = "Next steps for completing the production deployment"
  value = <<-EOT

  ========================================
  PawConnect AI - Production Deployment Complete!
  ========================================

  Main Agent URL: ${google_cloud_run_service.pawconnect_main_agent.status[0].url}
  Webhook URL: ${google_cloud_run_service.pawconnect_webhook.status[0].url}/webhook

  Next Steps:
  1. Test health endpoints:
     curl ${google_cloud_run_service.pawconnect_main_agent.status[0].url}/health
     curl ${google_cloud_run_service.pawconnect_webhook.status[0].url}/health

  2. Configure Dialogflow CX:
     - Go to: https://dialogflow.cloud.google.com/cx
     - Navigate to: Manage → Webhooks
     - Add webhook URL: ${google_cloud_run_service.pawconnect_webhook.status[0].url}/webhook

  3. Set secret values in Secret Manager:
     gcloud secrets versions add rescuegroups-api-key --data-file=-
     gcloud secrets versions add redis-password --data-file=-
     gcloud secrets versions add dialogflow-agent-id --data-file=-

  4. Monitor your deployment:
     - Logs: https://console.cloud.google.com/logs
     - Monitoring: https://console.cloud.google.com/monitoring

  5. Run integration tests:
     pytest tests/integration/ --service-url=${google_cloud_run_service.pawconnect_main_agent.status[0].url}

  For more information, see docs/DEPLOYMENT.md
  ========================================
  EOT
}
