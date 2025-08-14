output "api_base_url" { value = aws_apigatewayv2_api.http_api.api_endpoint }
output "dynamodb_table" { value = aws_dynamodb_table.metrics.name }
output "api_lambda_name" { value = aws_lambda_function.api_lambda.function_name }
output "ingest_lambda_name" { value = aws_lambda_function.ingest_lambda.function_name }