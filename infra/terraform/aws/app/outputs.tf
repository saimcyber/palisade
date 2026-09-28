output "app_bucket" {
  value = aws_s3_bucket.app.bucket
}

output "app_bucket_arn" {
  value = aws_s3_bucket.app.arn
}
