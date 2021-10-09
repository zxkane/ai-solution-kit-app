# pip install -r requirements.txt
import requests 
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
from argparse import RawTextHelpFormatter
from argparse import ArgumentParser
import os
import boto3
from urllib.parse import urlparse
import base64
from PIL import Image
from io import BytesIO

endpoint = '<get endpoint from output of CloudFormation deployment>'
def detect_running_region():
    """Dynamically determine the region from a running Glue job (or anything on EC2 for
    that matter)."""
    easy_checks = [
        # check if set through ENV vars
        os.environ.get('AWS_REGION'),
        os.environ.get('AWS_DEFAULT_REGION'),
        # else check if set in config or in boto already
        boto3.DEFAULT_SESSION.region_name if boto3.DEFAULT_SESSION else None,
        boto3.Session().region_name,
    ]
    for region in easy_checks:
        if region:
            return region

    # else query an external service
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-identity-documents.html
    r = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document")
    response_json = r.json()
    return response_json.get('region')

def make_signed_request(input_img):
    o = urlparse(endpoint)
    auth = BotoAWSRequestsAuth(aws_host=o.hostname,
                           aws_region=detect_running_region(),
                           aws_service='execute-api')

    with open(input_img, 'rb') as image_file:
        payload = {
            'img': base64.b64encode(image_file.read()).decode('utf-8'),
            'scale': '2',
        }
        headers = {
           'Content-Type': 'application/json'
        }
        response = requests.request("POST", endpoint, headers=headers, json=payload, auth=auth)
        
        original_name = os.path.basename(input_img).split('.')[0]
        if response.status_code >= 200 and response.status_code < 300:
            im = Image.open(BytesIO(base64.b64decode(response.json()['result'])))
            im.save(f'{original_name}_x4.png', 'PNG')
        else:
            print(f'Response status is {response.status_code}, and message is {response.text}')

help_msg = '''
    export AWS_ACCESS_KEY_ID=[MY_ACCESS_KEY_ID]
    export AWS_SECRET_ACCESS_KEY=[MY_SECRET_ACCESS_KEY]
    export AWS_SESSION_TOKEN=[MY_AWS_SESSION_TOKEN]
    export AWS_REGION=[aws regiontime]
    python version >=3.6 is required.
    Examples: For help
    python3 program_name.py -h
    Examples: 
    python3 program_name.py -i ./input.jpg
    Environment variables must be defined as AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
    You should also set AWS_SESSION_TOKEN environment variable if you are using temporary credentials (ex. IAM Role or EC2 Instance profile).
            '''

def exit_and_print_help():
    print(help_msg)
    exit()
def image_super_resolution():
    parser = ArgumentParser(description=help_msg, formatter_class=RawTextHelpFormatter)
    input_img = parser.add_mutually_exclusive_group()
    input_img.add_argument("-i", "--input-image", type=str)
    
    args = parser.parse_args()
    # Read command line parameters
    input_img = args.input_image

    if input_img is None:
        print('!!! ERROR: Input Image is Missing')
        exit_and_print_help()

    make_signed_request(input_img)

if __name__ == "__main__":
    image_super_resolution()