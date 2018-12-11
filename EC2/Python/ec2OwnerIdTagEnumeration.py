############################################################
###                                                      ###
### ec2OwnerIdTagEnumeration.py                          ###
###                                                      ###
### 20181028 1.0 c1gx                                    ###
###                                                      ###
### Synopsis:                                            ###
###                                                      ###
### Populate DynamoDB Tables for EC2 Instance Accounting ###
### Tag Validation Auditing, and User/Group Data Col-    ###
### lection.                                             ###
###                                                      ###
### DynamoDB Tables: EC2_OWNER_INSTANCE_ACCOUNTING,      ###
###                  EC2_OWNER_TAG_VALUES,               ###
###                  EC2_USER_GROUP_DATA                 ###      
###                                                      ###
###                                                      ###
############################################################





import json
import boto3
import decimal
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr


#
# DynamoDB Tables used to store data
# ----------------------------------

TABLE_NAME = 'EC2_OWNER_INSTANCE_ACCOUNTING'
TABLE_NAME2 = 'EC2_OWNER_TAG_VALUES'
TABLE_NAME3 = 'EC2_USER_GROUP_DATA'


#
# EC2 Attribute, Tag, and USER/Group  Tuple Normalization Lists
#--------------------------------------------------------------

ATTR_TUPLE = ('InstanceId', 'InstanceType', 'LaunchTime', 'Placement', 'PrivateDnsName', 'PrivateIpAddress', 'VpcId', 'IamInstanceProfile', 'Tags', 'OwnerId', 'RRequestId')
TAG_TUPLE  = ('Role', 'Environment', 'Notify',  'CreateDate', 'createdBy', 'Org', 'Owner', 'Order', 'ProjectName', 'Name', 'AppID')
TAG_TUPLE_UPPER = [x.upper() for x in TAG_TUPLE]
USER_GROUP_DATA_TUPLE = ('Path', 'UserId', 'UserName', 'Arn' )



#
# Environment Variables
# ----------------------

#
# Get the region from session context
#------------------------------------


session = boto3.session.Session()
REGION = session.region_name

#
# DynamoDB Table Connection Object References
#--------------------------------------------
dynamodb = boto3.resource('dynamodb', REGION)
table = dynamodb.Table(TABLE_NAME)
table2 = dynamodb.Table(TABLE_NAME2)
table3 = dynamodb.Table(TABLE_NAME3)

#
# EC2 Client Object Reference
#--------------------------------------------

client = boto3.client('ec2')

#
# Config Client Object Reference
#--------------------------------------------

config = boto3.client('config')

#
# IAM Client Object Reference
#--------------------------------------------

iam = boto3.client('iam')

ec2InstanceAttrs = {}

#
# Global DEBUG Boolean Flag for debugging control flow
# ----------------------------------------------------

DEBUG = False

#
# Function to lookup  User/Group info from DynamoDB Table EC2_USER_GROUP_DATA
# ----------------------------------------------------------------------------

def getUserName(UserId):
    
    try:
          if DEBUG:
              print("Entering get user name function with User Id: {0}".format(UserId))
              
          keyStr = "{\'UserId\': \'" + UserId + "\'}"
          
          if DEBUG:
              print("Key String for  User Id: {0}".format(keyStr))
              
          response3 = table3.get_item(Key=eval(keyStr))
          
          if DEBUG:
              print("RESPONSE for User Name Lookup:{0}".format(str(response3)))
          
          if 'Item' in response3.keys():
            
            if response3['Item']['UserId'] is not None:
                
               if DEBUG: print("Found existing User ID: " + response3['Item']['UserId'])
               
               return response3['Item']['UserName']
           
          else:
               return '*UNKNOWN*'
            
          
    except KeyError as e:
          return None
    
   
    
    

#
# Function to update User/Group info to DynamoDB Table EC2_USER_GROUP_DATA
# -------------------------------------------------------------------------

def updateUserInfo():
   
   tmp_user_dict = None
   
   for userlist in iam.list_users()['Users']:
   
      tmp_user_dict = {}
       
      for ukey,udata in userlist.items():
          
          if DEBUG:
             print ("User Data Key is {0} and User Data Value is {1}".format(ukey,udata))
          
          if ukey in USER_GROUP_DATA_TUPLE:
              tmp_user_dict[ ukey ] = udata
              
              if ukey in 'UserName':
                  paginator = iam.get_paginator('list_groups_for_user')
                  
                  response_iterator = paginator.paginate(UserName=udata)
                  
                  for group_list in response_iterator:
                      
                      tmp_user_dict[ 'Groups' ] = str(group_list['Groups'])
                  
          
          else:
              pass
       
          
          
      try:
          
          keyStr = "{\'UserId\': \'" + tmp_user_dict['UserId'] + "\'}"
          
          response = table3.get_item(Key=eval(keyStr))
          
          if 'Item' in response.keys():
            
            if response['Item']['UserId'] in tmp_user_dict['UserId']:
                
               if DEBUG: print("Found existing User ID: " + response['Item']['UserId'])
               
               return   
           
          else:
            
            try:
                
                table3.put_item(TableName=TABLE_NAME3, Item=tmp_user_dict)
            
            except ClientError as e:
              return
          
      except KeyError as e:
          pass
 
#
# Function to unpack/ update EC2 Instance Mandatory Tag data to DynamoDB Table EC2_OWNER_TAG_VALUES
# -------------------------------------------------------------------------------------------------
    

def updateEC2TagTable(ec2InstanceAttrs):
    
    
    
    if DEBUG: print("Entering updateEC2TagTable function with dictionary ec2InstanceAttrs")
    
    ec2InstanceTagValues = {}
    tag_list_len = 0

    if DEBUG: print("Instance ID for update: {0}".format(ec2InstanceAttrs['InstanceId']))
    if 'InstanceId' in ec2InstanceAttrs.keys():
        
        ec2InstanceTagValues['InstanceId'] = ec2InstanceAttrs['InstanceId']
  
    else:
        return "Instance Id not found!"
        
        
    if 'Tags' in ec2InstanceAttrs.keys():
        
        if DEBUG: print("WE HAVE TAGS!")
        tag_list_len = len(eval(ec2InstanceAttrs['Tags']))
    else:
        tag_list_len = -1

    
    if DEBUG: print("Tag List Length is: {0}".format(tag_list_len))
    
    if  ('Tags' in ec2InstanceAttrs.keys()) and (tag_list_len > 0) :
        
        if DEBUG:
           print ("TAGS are: {0}".format(ec2InstanceAttrs['Tags']))
        
        for ilist in eval(ec2InstanceAttrs['Tags']):
            
            if DEBUG: print("TAG LIST ITEM FOR PROCESSING\n\n")
            if DEBUG: print(" >>>>>>>>>>>>>>>>>{0}<<<<<<<<<<<<<<<".format(ilist))
            if DEBUG: print("ILIST KEY: {0} and ILIST VALUE: {1}".format(ilist['Key'],ilist['Value']))
           
            if (ilist['Key'].upper() in TAG_TUPLE_UPPER) and (ilist['Value'] is not None):
                 ec2InstanceTagValues[ilist['Key']] = ilist['Value']
            elif (ilist['Key'].upper() not in TAG_TUPLE_UPPER) and (ilist['Value'] is not None):
                 ec2InstanceTagValues[ilist['Key']] = ilist['Value']
            else:
                pass
         
        EC2_INSTANCE_TAG_UPPER = [x.upper() for x in ec2InstanceTagValues.keys()] 
        
        for mtag in TAG_TUPLE:
           if mtag.upper() in EC2_INSTANCE_TAG_UPPER:
               next
           else:
               ec2InstanceTagValues[mtag] = '*UNKNOWN*'
              
    elif 'Tags' not in ec2InstanceAttrs.keys() or tag_list_len <= 0:
        if DEBUG: print("THERE ARE NO TAGS ASSOCIATED WITH INSTANCE ID {0}".format(ec2InstanceAttrs['InstanceId']))
        
        for tag_name in TAG_TUPLE:
            ec2InstanceTagValues[ tag_name ] = '*UNKNOWN*'

    else:
       for tag_name in TAG_TUPLE:
            ec2InstanceTagValues[ tag_name ] = '*UNKNOWN*' 

    
    try:
        
        keyStr = "{\'InstanceId\': \'" + ec2InstanceAttrs['InstanceId'] + "\'}"
        
        if DEBUG: print("Key String is: " + keyStr)
        
        
        if DEBUG: print("Looking Up Instance ID: {0} in DB".format(ec2InstanceAttrs['InstanceId']))
        
        response = table2.get_item(Key=eval(keyStr))
        
        if DEBUG: print("Response Item is: {0}".format(response['Item']))
        
        if 'Item' in response.keys():
            
            if response['Item']['InstanceId'] in ec2InstanceAttrs['InstanceId']:
                
               if DEBUG: print("Found existing Instance ID: " + response['Item']['InstanceId'])
               
               return   
           
        else:
            if DEBUG: print("Adding EC2 Tag  data to DyanmoDB Table {0}  for Instance ID {1}".format(TABLE_NAME2, ec2InstanceAttrs['InstanceId']))
            
            try:
                
                
                table2.put_item(TableName=TABLE_NAME2, Item=ec2InstanceTagValues)
                
                
            except ClientError as e:
              return

         
    except KeyError as e:
        
        if DEBUG: print("Adding EC2 instance data to DyanmoDB Table {0} for Instance ID {1}".format(TABLE_NAME, ec2InstanceAttrs['InstanceId']))
        
        
        try:
         
             
             table2.put_item(TableName=TABLE_NAME2, Item=ec2InstanceTagValues)
             
        except ClientError as e:
              return
         
    except ClientError as e:
         return

#
# Function to update EC2 Instance  data to DynamoDB Table EC2_OWNER_INSTANCE_ACCOUNTING
# -------------------------------------------------------------------------------------------------    
    
def updateEC2InstanceTable(ec2InstanceAttrs):
    
    
    
    if DEBUG: print("Entering updateDynamoDbTable function with dictionary ec2InstanceAttrs")
    

    
    try:
        
        keyStr = "{\'InstanceId\': \'" + ec2InstanceAttrs['InstanceId'] + "\'}"
        
        if DEBUG: print("Key String is: " + keyStr)
        
        
        if DEBUG: print("Looking Up Instance ID: {0} in DB".format(ec2InstanceAttrs['InstanceId']))
        
        response = table.get_item(Key=eval(keyStr))
        
        if DEBUG: print("Response Item is: {0}".format(response['Item']))
        
        if 'Item' in response.keys():
            
            if response['Item']['InstanceId'] in ec2InstanceAttrs['InstanceId']:
                
               if DEBUG: print("Found existing Instance ID: " + response['Item']['InstanceId'])
               
               return   
           
        else:
            
            if DEBUG: print("Adding EC2 instance data to DyanmoDB Table {0} for Instance ID {1}".format(TABLE_NAME, ec2InstanceAttrs['InstanceId']))
            
            try:
                
                table.put_item(TableName=TABLE_NAME, Item=ec2InstanceAttrs)
                
                
                
            except ClientError as e:
              return

         
    except KeyError as e:
        
        if DEBUG: print("Adding EC2 instance data to DyanmoDB Table {0} for Instance ID {1}".format(TABLE_NAME, ec2InstanceAttrs['InstanceId']))
        
        
        try:
         
             table.put_item(TableName=TABLE_NAME, Item=ec2InstanceAttrs)
             
             
        except ClientError as e:
              return
         
    except ClientError as e:
         return


#
# Main function
# -------------

def lambda_handler(event, context):
    
    if DEBUG:
        print("ENTERING LAMBDA EVENT HANDLER FUNCTION!")
    
    print(json.dumps(event))
    
    # 
    # Update User/Group information to DynamoDB
    #------------------------------------------
    
    updateUserInfo()
    
    #
    # Iterate through all of available EC2 Instance data
    #----------------------------------------------------
    
    if DEBUG: print("Enumerate EC2 Instances")
    
    response = client.describe_instances()
    
    print(response['Reservations'][1]['Instances'][0]['InstanceId'])
    
    for v in response['Reservations']:
        
        OwnerId       = v['OwnerId']
        ReservationId = v['ReservationId']
         
        if DEBUG:
            print ("Owner ID is {0} : Reservation ID is {1} ".format(v['OwnerId'], v['ReservationId']))
        
        if DEBUG: print("Instance Data: " + str(v) + "\n\n")
        
        if DEBUG: print("Enumerating Instances!")
        
        for k,w in v.items():
           
           
           
           print("\n\n")
           
           if DEBUG: print("Key is: " + k)
           
           if k in 'Instances': 
               
               if DEBUG: print("Enumerating Instances!\n")
               
               for ivalue in v['Instances']:
                   
                   if DEBUG:
                      print("ivalue is: " + str(ivalue))
                       
                   ec2InstanceAttrs = {}
                    
                    
                   for kinst, vinst in ivalue.items():
                       
                         if DEBUG:
                            print("Instance Key is: " + kinst + "\n")
                            print("Instance Value is: " + str(vinst) + "\n")
                            
                         if kinst in ATTR_TUPLE:
                             
                              if (kinst in 'InstanceId') and (vinst is not None):
                                  
                                  resourceId = vinst
                                  
                                  config_list_str = "[{\'resourceType\': \'AWS::EC2::Instance\', \'resourceId\':  \'" + resourceId + "\'}]"
                                  
                                  if DEBUG:
                                      print("CONFIG LIST STRING: {0}".format(config_list_str))
                                      
                                  resp_config = config.batch_get_resource_config(resourceKeys=eval(config_list_str))
                                  accountId = resp_config['baseConfigurationItems'][0]['accountId']
                                  resourceCreationTime = resp_config['baseConfigurationItems'][0]['resourceCreationTime']
                                  
                                  if DEBUG:
                                      print("RESPONSE CONFIG FOR: \n {0}".format(str(accountId)))
                                      
                                  if (resp_config['baseConfigurationItems'] is not None): 
                                      
                                     ec2InstanceAttrs['AccountId'] = str(accountId)
                                     
                                     ec2InstanceAttrs['resourceCreationTime'] = str(resourceCreationTime)
                                     
                                  else:
                                      
                                     ec2InstanceAttrs['accountId'] = 'UNKNOWN' 
                                     ec2InstanceAttrs['resourceCreationTime'] = 'UNKNOWN'
                                     
                              if DEBUG: print("Key in Tuple: {0} and Value in Dict: {1}".format(kinst, vinst))
                              
                              if (kinst in 'IamInstanceProfile') and (vinst is not None):
                                iamInstanceProfile = vinst
                                UserId = iamInstanceProfile['Id']
                                ec2InstanceAttrs['UserId'] = UserId
                                UserName = getUserName(UserId)
                                ec2InstanceAttrs['UserName'] = UserName
                              else:
                                ec2InstanceAttrs['UserId'] = '*UNKNOWN*'
                                ec2InstanceAttrs['UserName'] = '*UNKNOWN*'
                                
                              
                              ec2InstanceAttrs[ kinst ] = str(vinst)
                              
                         
                         else:
                             continue
                         
                    
                   #    
                   # Call functions through for loop iterations
                   # ------------------------------------------
                   ec2InstanceAttrs['ReservationId'] = ReservationId
                   ec2InstanceAttrs['OwnerId']       = OwnerId
                   updateEC2InstanceTable(ec2InstanceAttrs)
                   updateEC2TagTable(ec2InstanceAttrs)
                    
               
           else:
               pass
           
    # TODO implement
    return {
        "statusCode": 200,
        "body": json.dumps('Hello from Lambda!')
    }