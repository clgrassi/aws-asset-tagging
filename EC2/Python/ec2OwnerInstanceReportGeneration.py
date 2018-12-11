
############################################################
###                                                      ###
### ec2OwnerInstanceReportGeneration.py                  ###
###                                                      ###
###                                                      ###
### 20181105 1.0 c1gx                                    ###
###                                                      ###
### Synopsis:                                            ###
###  Generate EC2 Instance data and tagging report info  ###
###  for report generation and e-mail distribution.      ###
###                                                      ###
############################################################

import json
import boto3
import decimal
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

sns = boto3.client('sns')
session = boto3.session.Session()
REGION = session.region_name

dynamodb = boto3.resource('dynamodb', REGION)



DEBUG = False

TAG_TUPLE  = ('UserName', 'UserId','Role', 'Environment', 'Notify',  'CreateDate', 'createdBy', 'Org', 'Owner', 'Order', 'ProjectName', 'Name', 'AppID')

#
# DynamoDB Tables used to store data
# ----------------------------------

TABLE_NAME = 'EC2_OWNER_TAG_VALUES'
TABLE_NAME2 = 'EC2_OWNER_INSTANCE_ACCOUNTING'
TABLE_NAME3 = 'EC2_USER_GROUP_DATA'

# Marshall JSON message payload for publishing to SNS message queue
#------------------------------------------------------------------

def snsEmailMsgGen(sns_topic_arn, sns_msg_payload):
    
     msgpub = sns.publish(
      TopicArn = sns_topic_arn,
      Message = json.dumps(sns_msg_payload)
    )
   
 # Scan EC2 Instance and Tagging Data for SNS JSON message payload construction
 #-----------------------------------------------------------------------------

def scanEC2InstanceData(table_name, table_name2):
    
    report_list = []
    
    table = dynamodb.Table(table_name)
    table2 = dynamodb.Table(table_name2)
    
    try:
        
        response = table.scan()
        
        if DEBUG: print("LENGTH OF RESPONSE ITEMS" + str(len(response['Items'])))
        
        data = response['Items']
    
        while 'LastEvaluatedKey' in response:
           response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
           data.extend(response['Items'])
           
        for item_dict in data:
            
            tmp_dict = {}
            missing_tags = []
            
            if DEBUG: print("Instance ID is: {}".format(item_dict['InstanceId']))
            
            if ('InstanceId' in item_dict.keys()) and (item_dict['InstanceId'] is not None):
                
                tmp_dict['InstanceId'] = item_dict['InstanceId']
                tmp_dict['Region'] = REGION
                
                response2 = table2.query(KeyConditionExpression=Key('InstanceId').eq(item_dict['InstanceId']))
                
                for i in response2['Items']:
                    tmp_dict['VpcId'] = i['VpcId']
                    tmp_dict['Placement'] = str(i['Placement'])
                    tmp_dict['InstanceType'] = str(i['InstanceType'])
                    tmp_dict['OwnerId'] = i['OwnerId']
                    tmp_dict['ReservationId'] = i['ReservationId']
                    
                    if ('UserId' in i.keys()) and (i['UserId'] is not None):
                      tmp_dict['UserId'] = i['UserId']
                    else:
                      tmp_dict['UserId'] = '*UKNOWN*'
                      
                    if ('UserName' in i.keys()) and (i['UserName'] is not None):   
                      tmp_dict['UserName'] = i['UserName']
                    else:
                      tmp_dict['UserName'] = '*UNKNOWN*'
                    
                    if ('resourceCreationTime' in i.keys()) and (i['resourceCreationTime'] is not None):  
                      tmp_dict['resourceCreationTime'] = i['resourceCreationTime']
                    else:
                      tmp_dict['resourceCreationTime'] = '*UNKNOWN*' 
                    
                    
            else:
                next
            
            
            for key, value in item_dict.items():
                
                if (key in TAG_TUPLE) and ((value in '*UNKNOWN*') or (value is None)):
                        missing_tags.append(key)
                else:
                    pass
                
        
            if len(missing_tags) > 0:
                tmp_dict['MissingTags'] = missing_tags
                report_list.append(tmp_dict)
        
            
                
    except ClientError as e:
        pass
    
    if DEBUG: print("REPORT LIST INSTANCE COUNT: {0}".format(str(len(report_list))))
    if DEBUG: print(str(report_list))
    
    if len(report_list) > 0:
        return report_list
    else:
        return None
        
# Main Method
# -----------

def lambda_handler(event, context):
    
    
    rl = scanEC2InstanceData(TABLE_NAME, TABLE_NAME2)
    
    if rl is not None:
        snsEmailMsgGen('arn:aws:sns:us-west-2:686137062481:ec2OwnerInstanceReport', rl)
        
    
    # TODO implement
    return {
        "statusCode": 200,
        "body": json.dumps('ec2OwnerInstanceReportGeneration successfully executed!')
    }