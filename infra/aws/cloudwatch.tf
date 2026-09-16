resource "aws_cloudwatch_dashboard" "nfr" {
  dashboard_name = "Network-Flight-Recorder"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          title  = "Snapshot Success"
          region = "us-east-1"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300

          metrics = [
            [
              "NetworkFlightRecorder",
              "SnapshotSuccess"
            ]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          title  = "Reachability Failures"
          region = "us-east-1"
          view   = "timeSeries"
          stat   = "Sum"
          period = 300

          metrics = [
            [
              "NetworkFlightRecorder",
              "ReachabilityFailure"
            ]
          ]
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 6
        width  = 24
        height = 6

        properties = {
          title  = "Recent Incidents"
          region = "us-east-1"
          view   = "table"

          query = <<-EOT
            SOURCE '${aws_cloudwatch_log_group.incident_summaries.name}'
            | fields @timestamp, likely_cause, confidence, finding_count, severity_counts, categories
            | sort @timestamp desc
            | limit 20
          EOT
        }
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "incident_summaries" {
  name              = "/network-flight-recorder/incidents"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_stream" "incident_summaries" {
  name           = "incident-summaries"
  log_group_name = aws_cloudwatch_log_group.incident_summaries.name
}
