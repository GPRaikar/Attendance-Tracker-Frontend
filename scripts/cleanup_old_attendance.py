import boto3
import logging
from datetime import datetime, timedelta
import os
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get AWS region from environment variable, default to ap-south-1
aws_region = os.environ.get('AWS_REGION', 'ap-south-1')

# Initialize DynamoDB client with region
dynamodb = boto3.resource('dynamodb', region_name=aws_region)
table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'SlackAttendance')
table = dynamodb.Table(table_name)

def calculate_cutoff_date():
    """Calculate the date 90 days ago from today"""
    cutoff_date = datetime.utcnow() - timedelta(days=173)
    return cutoff_date.isoformat()

def delete_old_records():
    """
    Scan DynamoDB table and delete records older than 90 days
    Returns count of deleted records
    """
    try:
        cutoff_date = calculate_cutoff_date()
        deleted_count = 0
        
        logger.info(f"Starting cleanup of records older than 90 days (before {cutoff_date})")
        logger.info(f"Using DynamoDB table: {table_name} in region: {aws_region}")
        
        # Scan the table
        response = table.scan()
        
        while True:
            items = response.get('Items', [])
            logger.info(f"Found {len(items)} items in this scan batch")
            
            for item in items:
                timestamp = item.get('timestamp')
                user_id = item.get('user_id')
                
                # Compare timestamps (ISO format string comparison works correctly)
                if timestamp < cutoff_date:
                    try:
                        table.delete_item(
                            Key={
                                'user_id': user_id,
                                'timestamp': timestamp
                            }
                        )
                        deleted_count += 1
                        logger.debug(f"Deleted record:  user_id={user_id}, timestamp={timestamp}")
                    except Exception as e:
                        logger.error(f"Error deleting record {user_id}/{timestamp}: {str(e)}")
                        continue
            
            # Check if there are more items to scan
            if 'LastEvaluatedKey' not in response:
                break
            
            response = table. scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        
        logger.info(f"Cleanup completed. Total records deleted: {deleted_count}")
        return {
            'statusCode': 200,
            'body': json. dumps({
                'message': 'Cleanup successful',
                'deleted_records': deleted_count
            })
        }
    
    except Exception as e: 
        logger.error(f"Error during cleanup: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Cleanup failed',
                'error':  str(e)
            })
        }

if __name__ == '__main__': 
    # Run the cleanup
    result = delete_old_records()
    print(json.dumps(result, indent=2))