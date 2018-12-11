
############################################################
###                                                      ###
### ec2OwnerInstanceReportSMTP.py                        ###
###                                                      ###
###                                                      ###
### 20181105 1.0 c1gx                                    ###
###                                                      ###
### Synopsis:                                            ###
###  SNS JSON message parser and SMTP MIME message form- ###
###  atter and transmission script to create and EC2     ###
###  Owner Instance Tagging reports.                     ###
###                                                      ###
############################################################

import boto3
import time
import datetime
import json
import smtplib
import base64
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# Build E-mail Header Information
#--------------------------------

EMAIL_DISTRO_GROUP= '2e913bd6.PGE.onmicrosoft.com@amer.teams.ms'
BCC = 'c1gx@pge.com'


# Build embedded HTML message
# -------------------------

MSG_HTML = ""

MSG_HTML_HEADER  = """
      <html>
      <head><b>EC2 Instance Assest Missing Tag Summary Report</b></head>
      <body>
      <table border="1" cellspacing="0" cellpadding="10" width=100%>
      <tr><td><b>Instance ID</b></td><td><b>Instance Type</b></td><td><b>Resource Creation Time</b></td><td><b>Region</b></td><td><b>Placement</b></td><td><b>VPC ID</b></td><td><b>Missing Tags</b></td><td><b>Reservation Id</b></td><td><b>Owner Id</b></td><td><b>User Id</b></td><td><b>User Name</b></td></tr>
      """
      
MSG_HTML_FOOTER = """
      </table><p>These assets were created without all of the required tags.
       Please review the <a href="http://wiki.comp.pge.com/display/CCE/AWS+Asset+Tagging+and+Enforcement">
       AWS Asset Tagging and Enforcement</a> Wiki for a list of the required tags
       and the values they need to contain.</p>
       <p>The required tags have been added to your assets with the value <b>*UNKNOWN*</b>. <br><br>
         *UNKNOWN* tags need to be updated as soon as possible.  Assets without valid tag
          information may be deleted or access restricted until the tags are correct.</p>
       <p>Assets that are being created using autoscaling groups, launch templates,
          or CloudFormation templates will trigger this email for each instance created 
          until the configurations are updated to create assets with the correct tags.</p>
       <p>Contact <a href="mailto:CommercialCloudSupport1@pge.com">CommercialCloudSupport1@pge.com</a> 
          if you have any questions or need assistance.</p>
       </body></html>
"""

   
# Obtain current date-time
# ------------------------
DTG = time.asctime( time.localtime(time.time()) )

# Function to generate the embedded HTML message MIME attachment
# --------------------------------------------------------------

def genEmailMsg(email_json):

      MSG_HTML_MIDDLE = ""
      
      for msgdict in eval(email_json):
          
            
            if ('InstanceId' in msgdict.keys()) and (msgdict['InstanceId'] is not None):
                
                InstanceId   = msgdict['InstanceId']
              
                if ('InstanceType' in msgdict.keys() and msgdict['InstanceType'] is not None):
                    InstanceType = msgdict['InstanceType']
                else:
                    InstanceType = "*UNKNOWN*"
                
                if ('resourceCreationTime' in msgdict.keys() and msgdict['resourceCreationTime'] is not None):
                    resourceCreationTime = msgdict['resourceCreationTime']
                else:
                    resourceCreationTime = "*UNKNOWN*"
                
                if ('Region' in msgdict.keys() and msgdict['Region'] is not None):
                    Region = msgdict['Region']
                else:
                    Region = "*UNKNOWN*"
                    
                if ('Placement' in msgdict.keys() and msgdict['Placement'] is not None):
                    Placement = str(msgdict['Placement'])
                else:
                    Placement = "*UNKNOWN*"    
              
                if ('VpcId' in msgdict.keys() and msgdict['VpcId'] is not None):
                    VpcId = msgdict['VpcId']
                else:
                    VpcId = "*UNKNOWN*"
                
                if ('MissingTags' in msgdict.keys() and msgdict['MissingTags'] is not None):
                    MissingTags = str(msgdict['MissingTags'])
                else:
                    MissingTags = "*UNKNOWN*"
                
                if ('ReservationId' in msgdict.keys() and msgdict['ReservationId'] is not None):
                   ReservationId = msgdict['ReservationId']
                else:
                    ReservationId = "*UNKNOWN*"
               
                if ('OwnerId' in msgdict.keys() and msgdict['OwnerId'] is not None):
                    OwnerId = msgdict['OwnerId']
                else:
                    OwnerId = "*UNKNOWN*"
                
                if ('UserId' in msgdict.keys() and msgdict['UserId'] is not None):
                    UserId = msgdict['UserId']
                else:
                    UserId = "*UNKNOWN*"
                    
                if ('UserName' in msgdict.keys() and msgdict['UserName'] is not None):
                    UserName = msgdict['UserName']
                else:
                    UserName = "*UNKNOWN*"
            
                MSG_HTML_MIDDLE += "<tr><td valign=\"top\">" + InstanceId  +  "</td><td>" + InstanceType + "</td><td>" + resourceCreationTime + "</td><td>"+ Region + "</td><td>" + Placement + "</td><td>" + VpcId + "</td><td>" + MissingTags + "</td><td>" + ReservationId + "</td><td>" + OwnerId + "</td><td>" + UserId + "</td><td>" + UserName + "</td></tr>"
            
            else:
               next
            
      MSG_HTML = MSG_HTML_HEADER + MSG_HTML_MIDDLE + MSG_HTML_FOOTER
      
      print(MSG_HTML)
      
      return MSG_HTML
      
      
# Function to create and send final SMTP message and attach the Text/HTML MIME Type Extensions
# --------------------------------------------------------------------------------------------      
     
    
def sendEmailMsg(msg_html):
        email_from = 'donotreply@pge.com'
        email_to = EMAIL_DISTRO_GROUP
        subject = "SUMMARY REPORT - " + DTG +  " : AWS EC2 Instance Asset Mandatory Tags Missing -- Owners Need to Be Identified"
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['To'] = email_to
        msg['From'] = email_from
        
        
        text = "Hi All, attached is a SUMMARY REPORT - " + DTG +  " : AWS EC2 Instance Asset Mandatory Tags Missing -"
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(msg_html, 'html')
        msg.attach(part1)
        msg.attach(part2)

        
        s = smtplib.SMTP('mailhost.pge.com')
        
        s.sendmail(email_from, email_to, msg.as_string())

        s.quit()
        
# Main method call
# ----------------

def lambda_handler(event, context):
    
    #print("Event Detail:" + json.dumps(event))
    
    message = ""
    
    # Extract JSON message payload for parsing and processing
    # from SNS message queue.
    #--------------------------------------------------------
    
    for r in event['Records']:
        
        if ('Sns' in r) and ('Message' in r['Sns']):
            message = json.loads(r['Sns']['Message'])
            
            
            
    
    report_html = genEmailMsg(json.dumps(message))
    sendEmailMsg(report_html)

    # TODO implement
    return {
        "statusCode": 200,
        "body": json.dumps('JSON message parsing and SMTP e-mail message transmission are both complete')
    }