import requests
import webbrowser
import json
import sys
import os
import time
import math as maths
import HTMLParser

def get_width():
    global width
    width = os.popen('stty size', 'r').read().split()[1]
    width = int(width)
    return width

def spacer():
    get_width()
    print ('-'*width)

def loading_bar(n,i):
    get_width()
    factor=(n/(width-2.0))
    n=int(maths.floor((n)/factor))
    s=int(maths.floor(n/factor))
    i=int(maths.floor((i-1)/factor))
    sys.stdout.write('['+'='*(n-i)+' '*(i)+']')
    sys.stdout.flush()
    sys.stdout.write('\r')
    sys.stdout.flush()

def get_auth():
    try:
        token=open(os.path.dirname(__file__) + '../authtoken.txt','r').read()
    except IOError:
        print ('No authentication file found.')
        auth_true=input("Do you want to get your authentication token? You have to do this to use the program (Y/n) ").lower()
        
        if (auth_true != 'n'):
            savout = os.dup(1)
            os.close(1)
            os.open(os.devnull, os.O_RDWR)
            try:
                webbrowser.open("https://stackexchange.com/oauth/dialog?client_id=4921&scope=write_access&redirect_uri=http://timtjtim.github.io")
            finally:
                os.dup2(savout, 1)
            token=input('Please enter your SE authentication token here: ')
    if len(token) != 24:
        print ('Invalid token. Retying')
        open('../../authtoken.txt','w').write()
        get_auth()
    else:
        print ('Got token')
        open(os.path.dirname(__file__) + '../authtoken.txt','w').write(token)
        return token

def backoff(response_JSON):
    try:
        backoff = response_JSON['items'][0]['backoff']
        print ('Told to backoff, waiting for '+str(backoff)+' seconds.')
        for i in range (backoff, 0,-1):
            loading_bar(backoff,i)
            time.sleep(1)
        spacer()
    except KeyError:
        pass
    

def get_from_search(site,tag,key,token):
    response = requests.get("https://api.stackexchange.com/2.2/search",
          data={'tagged': tag,
                'site': site,
                'key': key,
                }
            )
    response_JSON = response.json()
    quota_remaining = response_JSON['quota_remaining']
    print (str(quota_remaining)+' requests left. Used '+str(10000-quota_remaining)+' today.')
    backoff(response_JSON)
    return response_JSON[u'items']

def get_ids_from_items(items):
    ids = []
    for question in items:
        ids += [question[u'question_id']]
    return ids

def get_tags_from_ids(question_IDs,key,token):
    all_data=[]
    n=len(question_IDs)-1
    i=n
    for q_id in question_IDs:
        response = requests.get('https://api.stackexchange.com/2.2/questions/'+str(q_id),
              data={'site': site,
                    'access_token': token,
                    'key': key,
                    'filter': '!9YdnSIoKx',
                    }
                )
        response_JSON = response.json()
        backoff(response_JSON)
        all_data+=[response_JSON]
        quota_remaining = response_JSON['quota_remaining']
        loading_bar(n,i)
        i-=1
    print (' '*(n+4))
    return all_data

def change_tag(q_tags,tag_id,tag,replacement_tags,site):
    try:
        tag_id=int(tag_id)-1
        new_tag=replacement_tags[tag_id]
        q_tags[q_tags.index(tag)]=new_tag
        print ('Tagging with ' + ' '.join(q_tags)+'\n')
        if site == 'askubuntu':
            site = 'ubuntu'
        print ('If you made a mistake please visit http://'+site+'.stackexchange.com/users/current?tab=activity&sort=revisions')

    except ValueError:
        tag_id=0
        print ('Skipping')
    return q_tags

def print_tags(replacement_tags):
    print_text='\nWhat should happen to this? Press enter to skip, press '
    for i in range(len(replacement_tags)-1):
        print_text+=str(i+1)+' for '+replacement_tags[i]+', '
    print_text+='or '+str(i+2)+' for '+replacement_tags[-1]+'.'
    print (print_text)

def show_tags(all_data,tag,replacement_tags,site):
    formed_data=[]
    for q_response in all_data:
        q_tags = q_response['items'][0]['tags']
        spacer()
        print (', '.join(q_tags))
        spacer()
        print_tags(replacement_tags)
        user_input = input()
        if not user_input:
            spacer()
            print (str(q_response['items'][0]['question_id'])+' : '+HTMLParser.HTMLParser().unescape(q_response['items'][0]['title'])+'\n')
            print (HTMLParser.HTMLParser().unescape(q_response['items'][0]['body_markdown']))
            spacer()
            print_tags(replacement_tags)
            user_input=input()
        new_tags = change_tag(q_tags,user_input,tag,replacement_tags,site)
        q_response['items'][0]['tags'] = new_tags
        formed_data+=[q_response]
    return formed_data

def send_edits(formed_data,key,token,site,tag):
    for question_data in formed_data:
        question_ID   = int(question_data['items'][0]['question_id'])
        body_markdown = str(HTMLParser.HTMLParser().unescape(question_data['items'][0]['body_markdown']))
        title         = str(HTMLParser.HTMLParser().unescape(question_data['items'][0]['title']))
        tags          = question_data['items'][0]['tags']

        response = requests.post('https://api.stackexchange.com/2.2/questions/'+str(question_ID)+'/edit',
              data={'body': body_markdown,
                    'comment': 'removed '+tag+' tag',
                    'tags': ' '.join(tags),
                    'title': title,
                    'access_token': token,
                    'site': site,
                    'key': key
                    }
                )
        response_JSON=response.json()
        backoff(response_JSON)

try:
    input = raw_input
except NameError:
    input = input

if len(sys.argv) < 2:
    site=input('Site: ').lower()
else:
    site = sys.argv[1]

if len(sys.argv) < 3:
    tag=input('Tag: ').lower()
else:
    tag = sys.argv[2]

if len(sys.argv) < 4:
    replacement_tags=input('Tag alternatives: ').lower().split()
else:
    replacement_tags = sys.argv[3:]
    #print (replacement_tags)
#print (replacement_tags)
if not replacement_tags:
    print ('Invalid replacement tags. Exiting')
    quit()

token = get_auth()
key = 'hDZI3p7wr3JAf1t)ccIIHA(('
items = get_from_search(site,tag,key,token)
question_IDs = get_ids_from_items(items)
print ("Got IDs, fetching data")
all_data = get_tags_from_ids(question_IDs,key,token)
formed_data=show_tags(all_data,tag,replacement_tags,site)
print ('Finished tagging, sending edit data. Please wait')
send_edits(formed_data,key,token,site,tag)
