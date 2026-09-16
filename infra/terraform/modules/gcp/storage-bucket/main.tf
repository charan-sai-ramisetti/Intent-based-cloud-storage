resource "google_storage_bucket" "this" {
  name     = "${var.project_name}-${var.environment}-gcp-211200205"
  location = "ASIA"
  project  = var.gcp_project_id
  cors {
    origin = [
      "http://localhost:5500",
      "http://127.0.0.1:5500",
      "https://urban-chainsaw-r49qv7gvx57c955-5500.app.github.dev",
      "https://tricloudvault.charansai.me",
      "https://charansai.me"
    ]
    method          = ["PUT", "POST", "GET", "OPTIONS"]
    response_header = [
      "ETag",
      "Content-Type",
      "Content-Range",        # required for resumable upload chunks
      "X-Goog-Resumable",     # GCS sends this on the initial RESUMABLE POST
      "Location"              # GCS returns the session URI in Location header
    ]
    max_age_seconds = 3600
  }
}