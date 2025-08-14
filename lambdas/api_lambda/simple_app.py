import os
import json
import boto3
from datetime import datetime

TABLE_NAME = os.environ.get("DDB_TABLE")
API_AUTH_TOKEN = os.environ.get("API_AUTH_TOKEN", "")
PROJECT_ENV = os.environ.get("PROJECT_ENV", "dev")

ddb = boto3.resource("dynamodb")
table = ddb.Table(TABLE_NAME)

def handler(event, context):
    try:
        # Get request info
        path = event.get('rawPath', event.get('path', '/'))
        method = event.get('requestContext', {}).get('http', {}).get('method', event.get('httpMethod', 'GET'))
        headers = event.get('headers', {})
        
        # Simple auth check
        token = headers.get('x-api-key', '')
        if API_AUTH_TOKEN and token != API_AUTH_TOKEN:
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Forbidden'})
            }
        
        # Route handling
        if path == '/' and method == 'GET':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'text/html'},
                'body': f'<h1>eCFR Analytics - {PROJECT_ENV}</h1><p>API is running!</p>'
            }
        
        elif path == '/health' and method == 'GET':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'healthy',
                    'environment': PROJECT_ENV,
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        
        elif path == '/agencies' and method == 'GET':
            # Simple scan of agencies
            resp = table.scan(Limit=25)
            items = [i for i in resp.get("Items", []) if i.get("pk", "").startswith("AGENCY#")]
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'agencies': items,
                    'count': len(items)
                })
            }
        
        elif path == '/ingest' and method == 'POST':
            # Trigger ingest lambda
            lambda_client = boto3.client('lambda')
            ingest_function = os.environ.get('INGEST_LAMBDA_NAME', 'danny-ecfr-ingest-dev')
            
            try:
                response = lambda_client.invoke(
                    FunctionName=ingest_function,
                    InvocationType='Event',  # Async
                    Payload=json.dumps({})
                )
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'message': 'Ingest triggered successfully'})
                }
            except Exception as e:
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': f'Failed to trigger ingest: {str(e)}'})
                }
        
        else:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Not found'})
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }