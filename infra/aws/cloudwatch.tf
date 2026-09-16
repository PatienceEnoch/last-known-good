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
      }
    ]
  })
}
