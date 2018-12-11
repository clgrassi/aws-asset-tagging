import json
import base64
import requests
import boto3
from botocore.exceptions import ClientError

DEBUG = True
SSL_BUNDLE = 'CA_BUNDLE'


def get_secret(secret_id):
  
    secret = None
    
    # Create a Secrets Manager client
    
    session = boto3.session.Session()
    region_name = session.region_name

    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
      
       get_secret_value_response = client.get_secret_value(
            SecretId=secret_id
        )
    
       secret = get_secret_value_response['SecretString']
        
       if DEBUG:
           print(str(get_secret_value_response))

    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])

    #if DEBUG: print("****{0}****".format(secret))
    
    return secret

def getAmpsToken(service_uri, endpoint, userId, password):

    s = None

    login_url = service_uri + endpoint 

    if DEBUG:
      print("URL is: {0}".format(login_url))


    s = requests.Session()
    s.verify = SSL_BUNDLE 

    auth = base64.b64encode((userId + ":" + password).encode("utf-8")).decode()

    if DEBUG:
      print("Authentication Header is {0}".format(str(auth)))

    basic_auth = 'Basic ' + auth

    if DEBUG:
      print("BASIC Auth Header is: {0}".format(basic_auth))

    headers = {

      'Content-Type': 'application/json',
      'Authorization': basic_auth
    }

    if DEBUG:
      print("Header Payload is: {0}".format(str(headers)))

    payload = {"email": userId, "password": password}

    if DEBUG:
      print("Message Payload is: {0}".format(str(payload)))

    r = s.post(login_url, headers=headers, data=json.dumps(payload))

    if DEBUG:
      print("\nRESPONSE FROM SERVER APP = " + r.text + '\n')

    response = json.loads(r.text)

    if DEBUG:
      print("\n\nTOKEN = " + response['token'])

    return response['token']





def getAmpsData(amps_uri,endpoint, accessToken, ampsId):

    s = None

    app_url = amps_uri + endpoint
    s = requests.Session()
    s.verify = SSL_BUNDLE

    if DEBUG:
       print("APP URL is: {0}".format(app_url))  
       print("AMPS Access Token is {0}".format(accessToken))
       print("AMPS ID is {0}".format(ampsId))
    
    auth = "Bearer " + accessToken 

    if DEBUG:
       print("Auth String is: {0}".format(auth))

    
    headers = {
         "Authorization": auth,
	 'Content-Type': 'application/json'
    }


    if DEBUG:
       print("HEADERs: {0}".format(str(headers)))


    query_payload = r'{"params":{"columnsList":["SERVICE_OR_APPLICATION_NAME","APP_ID"],"filter":[[{"key":"APP_ID","val":"' + ampsId + r'","operator":"eq"}]],"pageSize":20,"schema":"Applications","offset":0}}'
     

    if DEBUG:
       print("QUERY PAYLOAD is: {0}".format(query_payload))


    r = s.post(app_url, headers=headers, data=json.dumps(eval(query_payload)))

    if DEBUG:
       print("Response is: {0}".format(str(r.text)))
       



def lambda_handler(event, context):
  
    secret = eval(get_secret("test/ampsRestfulInterface"))
    
    if DEBUG:
       print("Secret: {0}".format(secret))
       
    userId = secret["email"]
    password = secret["password"]

    amps_token = getAmpsToken('https://itapidev01vip.comp.pge.com', '/AMPS/v1/login', userId, password)
    
    if DEBUG:
       print("AMPS Token: {0}".format(amps_token))

    getAmpsData('https://itapidev01vip.comp.pge.com', '/amps/v1/amps-enterprise-backend/application', amps_token, 'APP-9999')