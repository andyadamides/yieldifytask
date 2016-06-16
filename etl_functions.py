import csv
import gzip as gz
import json
import tempfile
import os
import shutil
import datetime,time,re,validators
import requests
import constants
from urlparse import urlparse

# Ported by Matt Sullivan http://sullerton.com/2011/03/django-mobile-browser-detection-middleware/
reg_b = re.compile(r"(android|bb\\d+|meego).+mobile|avantgo|bada\\/|blackberry|blazer|compal|ipad|iphone|iphone os|ipod|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\\.(browser|link)|vodafone|wap|windows ce|xda|xiino", re.I|re.M)
reg_v = re.compile(r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\\-|your|zeto|zte\\-", re.I|re.M)


def if_null(var, val):
  if var is None:
    return val
  return var


# validation of 1st column = date
def validate_date(date_column):
    result = False
    try:
        datetime.datetime.strptime(date_column, '%Y-%m-%d')
        result = True
    except ValueError:
        return result
    return result


# validation of 2nd column = time
def validate_time(time_column):
    result = False
    try:
        time.strptime(time_column, '%H:%M:%S')
        result = True
    except ValueError:
        return result
    return result


# validation of 3rd column = url
def validate_url(url_column):

    # using module parse the hashed url
    parsed_url  = urlparse(url_column)

    # construct regex for each of the three pieces of the url -  http://hashed_domain/hashed_path
    regex_scheme = re.compile(r"(http|https)")
    regex_domain = re.compile(r"^[a-zA-Z0-9]+$")
    regex_path = re.compile(r"^(/)[a-zA-Z0-9]+$")

    # verify each piece
    match_scheme = regex_scheme.match(parsed_url.scheme)
    match_domain = regex_domain.match(parsed_url.netloc)
    match_path = regex_path.match(parsed_url.path)

    if match_domain and match_path and match_scheme:
        return True
    else:
        return False


# validation and processing of 4th column = ip
def validate_ip(ip_column):
    if validators.ip_address.ipv4(ip_column):
        return True
    else:
        return False


# offline database would be the ideal part here for boosting performance
def process_geolocation_data(ip_column):
    location={}
    request_url = constants.GEOLOCATIONURL + constants.APIKEY + '&ip=' + ip_column + '&format=json'
    response_content = requests.get(request_url)._content
    response_content_json = json.loads(response_content)
    location['latitude'] = if_null(response_content_json['latitude'],0.0)
    location['longitude'] = if_null(response_content_json['longitude'],0.0)
    location['country'] = if_null(response_content_json['countryName'],0.0)
    location['city'] = if_null(response_content_json['cityName'],0.0)
    return location


# processing of 5th column = ua
def process_user_agent(ua_column):

    result = {}
    try:
        # construct GET request and load to JSON
        request_url = 'http://useragentstring.com/?uas=' + ua_column.replace(' ','%20') + '&getJSON=all'
        response_content = requests.get(request_url)._content
        response_content_json = json.loads(response_content)

        # get is_mobile
        b = reg_b.search(ua_column)
        v = reg_v.search(ua_column[0:4])
        if b or v:
            result['mobile'] = True
        else:
            result['mobile'] = False

        # get OS_family
        result['os_family'] = if_null(response_content_json['os_type'],'')
        # get full string
        result['string'] = ua_column
        # get browser_family
        result['browser_family'] = if_null(response_content_json['agent_name'],'')

    except ValueError:
        return result
    return result


def parse_and_transform_file(input_file):
    tranformed_data = {}
    tranformed_record = {}
    counter=1
    # decompress the file and process according to wanted output
    with gz.open(input_file, 'rb') as tsvfile:
        records = csv.reader(tsvfile, delimiter='\t')

        # go through each record and
        # 1. store relevant information in a json(Done)
        # log invalid records
        # 2. insert data in DynamoDB for later querying through API service(Not yet started)
        for record in records:
            if len(record) == constants.TOTAL_LENGTH:
                if validate_date(record[constants.DATE_LOCATION]) \
                        and validate_time(record[constants.TIME_LOCATION]):
                    tranformed_record['timestamp'] = record[constants.DATE_LOCATION]\
                                                     + ' ' + record[constants.TIME_LOCATION]
                else:
                    tranformed_record['timestamp'] = 'Invalid'
                if record[constants.USER_ID_LOCATION] != '':
                    tranformed_record['user_id'] = record[constants.USER_ID_LOCATION]
                else:
                    tranformed_record['user_id'] = 'Invalid'
                if validate_url(record[constants.URL_LOCATION]):
                    tranformed_record['url'] = record[constants.URL_LOCATION]
                else:
                    tranformed_record['url'] = 'Invalid'
                if validate_ip(record[constants.IP_LOCATION]):
                    tranformed_record['location'] = process_geolocation_data(record[constants.IP_LOCATION])
                else:
                    tranformed_record['location'] = 'Invalid'
                if record[constants.UA_LOCATION] != '':
                    tranformed_record['user_agent'] = process_user_agent(record[constants.UA_LOCATION])
                else:
                    tranformed_record['user_agent'] = 'Invalid'
                tranformed_data[counter] = tranformed_record
                counter+=1
                print(counter)

    # convert directly dict to json and return
    return json.dumps(tranformed_data)


def upload_to_s3(output_json,source_file_name,s3,s3_bucket,s3_key_prefix):
    # creating temporary directory for our file
    tempdir = tempfile.mkdtemp(prefix='yieldify')
    file_name = os.path.basename('tranformed_' + source_file_name )
    file_path = os.path.join(tempdir, file_name)

    with gz.open(file_path, 'wb') as gzfile:
        gzfile.write(output_json)
        print('Uploading ' + file_path + ' to ' + s3_key_prefix + file_name)

        # delete temporary files and directory from local disk
        gzfile.close()

    # Upload file in s3
    s3.meta.client.upload_file(file_path, s3_bucket, s3_key_prefix + file_name)

    # Remove temp directory
    shutil.rmtree(tempdir)

    # Check completion of upload
    bucket = s3.Bucket(s3_bucket)
    key = s3_key_prefix + file_name
    objects = list(bucket.objects.filter(Prefix=key))
    if len(objects) > 0 and objects[0].key == key:
        return True,'Complete upload'
    else:
        return False,'Incomplete upload'







