resource "aws_s3_bucket" "incident_evidence" {
  bucket = "nfr-incident-evidence-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"

  tags = {
    Purpose = "Network Flight Recorder incident evidence"
  }
}

resource "aws_s3_bucket_public_access_block" "incident_evidence" {
  bucket = aws_s3_bucket.incident_evidence.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "incident_evidence" {
  bucket = aws_s3_bucket.incident_evidence.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "incident_evidence" {
  bucket = aws_s3_bucket.incident_evidence.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

output "incident_evidence_bucket" {
  value = aws_s3_bucket.incident_evidence.bucket
}
