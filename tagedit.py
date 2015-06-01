# Version 1.1.0

import webbrowser
import json
import sys
import os
import time
import math as maths    # I'm English.

def kill_code(reason=''):
    """
    Take a message (default "No Message") and exits with that message
    """
    sys.exit(reason)

try:
    input = raw_input   # Python 2
except NameError:
    pass                # Python 3

try:
    import HTMLParser   # Python 2
except ImportError:
    import html.parser  # Python 3
    HTMLParser=html.parser
try:
    import requests     #Python 2
except ImportError:
    print ('You need to install python requests for this script with this command:')    # Python 3
    print ('    pip install requests')
    print ('Visit https://pypi.python.org/pypi/requests for more info')
    kill_code()

def term_width():
    """
    uses os.popen to update the global variable
    "width" with the terminal size.
    If this is unsupported, width is set to 50 and height to 25.
    """
    global width
    global height
        # Get the dimensions as a list of height,width
    size=os.popen('stty size').read().split()
        # Try to split apart the list. If not possible set variable to False
    try:
        height = int(size[0])
        width = int(size[1])        
        size_valid=True
    except (IndexError, ValueError):
        size_valid=False

        # Triggers if size_valid is False or height or width is 0
    if (not size_valid) or (not width) or (not height):
        width = 50
        height = 25


def spacer(before=''):
    """
    Prints out a spacer like ---------- the width of the console.
    If width is not supported, it will be 50 wide.
    """
    term_width()
    print (before+'-'*width)


def clear_term():
    """
    Clears the terminal / screen
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def loading_bar(n,i,ta=''):
    """
    Creates a loading bar like [========     ] the width of the console.
    Updates with get_width() each time it's called, so there is dynamic resizing.
    
    """
    term_width()
    n=float(n)
    i=float(i)
    factor=(n/(float(width)-2-len(str(ta))))
    n=int(maths.floor((n)/factor))
    i=int(maths.floor((i-1)/factor))
    sys.stdout.write('['+'='*(n-i)+' '*(i)+']'+str(ta)+'\r')
    sys.stdout.flush()

#
def check_for_error(response_JSON):
    """
    Takes the JSON response from the server,
    and checks to see if there is an error.
    """
    try:
        error_name=response_JSON['error_name']
        print (error_name)
        error_message=response_JSON['error_message']
        if error_name=='access_denied':
            get_auth(True)
            kill_code('Code will now exit, please restart')
        elif error_name=='write_failed':
            return False
        else:
            kill_code('Got error message: '+response_JSON['error_message'])
    except KeyError:
        return False

def backoff(response_JSON):
    """
    Accoring to the API rules, if there is the key "backoff"
    then the code must wauit for that time. This function checks for the key
    and if it exits it waits, with a loading bar.
    """
    try:
        backoff = int(response_JSON['items'][0]['backoff'])
        print ('Told to backoff, waiting for '+str(backoff)+' seconds.')
        for i in range (backoff, 0,-1):
            loading_bar(backoff,i,' '+str(i))
            time.sleep(1)
        spacer()
    except (KeyError, IndexError):
        pass

def site_format(site):
    """
    Take the site name and format it into the correct URL format for SE
    """
    special_sites=['askubuntu','stackoverflow','superuser','serverfault','stackapps']
    if site not in special_sites:
        site=site+'.stackexchange'
    return site

# 
def get_from_search(site,batch,tag,key,token):
    """
    Take the site name, number to get and the tag to search for
    Use the API search to get the list of questions.
    The max from the API is 100, hence the maximum set on the batch input
    """
    response = requests.get("https://api.stackexchange.com/2.2/search",
          data={'tagged': tag,
                'site': site,
                'key': key,
                'pagesize': batch,
                }
            )
    response_JSON = response.json()
    try:
        quota_remaining = response_JSON['quota_remaining']
    except KeyError as error:
        kill_code('Bad site name')
    print (str(quota_remaining)+' requests left. Used '+str(10000-quota_remaining)+' today.')
    try:
        items=response_JSON['items']
        if not items:
            kill_code('Got no questions with the tag "'+tag+'"')
    except KeyError:
            kill_code('Got no items')
    backoff(response_JSON)
    check_for_error(response_JSON)
    try:
        items = response_JSON[u'items'] 
    except KeyError as error:
        kill_code()
    return items

def get_ids_from_items(items):
    """
    Takes in the question data and loops through it.
    Returns a list of the question IDs.
    """
    ids = []
    for question in items:
        ids += [question[u'question_id']]
    return ids

def get_tags_from_ids(question_IDs,key,token,batch):
    """
    Uses the list of IDs and the API to get the data from the questions.
    This includes the tags, the 
    """
    all_data=[]
    str_question_IDs=[str(id) for id in question_IDs]
    response = requests.get('https://api.stackexchange.com/2.2/questions/'+';'.join(str_question_IDs),
            data={'site': site,
                  'access_token': token,
                  'key': key,
                  'filter': '!9YdnSIoKx',
                 }
            )
    response_JSON = response.json()
    backoff(response_JSON)
    check_for_error(response_JSON)
    quota_remaining = response_JSON['quota_remaining']
    all_data=response_JSON
    term_width()
    print (' '*(width+2))
    return all_data['items']

#
def change_tag(q_tags,tag_id,tag,replacement_tags,site):
    try:
        tag_id=int(tag_id)-1
        new_tag = replacement_tags[tag_id]
        q_tags[q_tags.index(tag)]=new_tag
        site=site_format(site)
        return q_tags
    except (ValueError, IndexError) as error:
        tag_id=0
        print ('Skipping\n')
        return False


def print_tag_numbers(replacement_tags,enter_command):
    print_text='\nWhat should happen to this? Press enter to '+enter_command+'. Press '
    for i in range(len(replacement_tags)-1):
        print_text+=str(i+1)+' for '+replacement_tags[i]+', '
    try:
        print_text+='or '+str(i+2)+' for '+replacement_tags[-1]+'.'
    except UnboundLocalError:
        print_text+='1 for '+replacement_tags[0]+'.'
    print (print_text)


def show_tags(q_response,count='',total=''):
    q_tags = q_response['tags']
    if count and total:
        print ('This is question '+str(count)+' out of '+str(total)+'.')
    spacer()
    to_print_l1=', '.join(q_tags)
    to_print_l2=str(q_response['question_id'])+' : '+HTMLParser.HTMLParser().unescape(q_response['title'])
    if len(to_print_l2) > width:
        print (to_print_l1+'\n'+to_print_l2[:width-3]+'...')
    else:
        print (to_print_l1+'\n'+to_print_l2)
    spacer()
    return q_tags

def show_question(replacement_tags,q_response,count,total):
    clear_term()
    show_tags(q_response,count,total)
    body_markdown = q_response['body_markdown']
    term_width()
    lines=body_markdown.split('\r\n')
    lines_cut=[]
    for line in lines:
        lines_cut+=[line[i:i+width-6] for i in range(0, len(line), width-6)]
    displayed = 0
    while lines:
        if displayed < (height -9):
            displayed += 1
            print (HTMLParser.HTMLParser().unescape(lines[0]))
            lines.pop(0)
        else:            
            user_input = input('Reached term height limit. Want to view more? (Y/n) ').lower()
            if user_input != 'n':
                displayed = 0
            else:
                break
    spacer('\n')
    print_tag_numbers(replacement_tags,'skip')
    user_input=input()
    return user_input


def show_data(all_data,tag,replacement_tags,site):
    formed_data=[]
    total = len(all_data)
    count = 1
    for q_response in all_data:
        clear_term()
        q_tags=show_tags(q_response,count,total)
        print_tag_numbers(replacement_tags,'view question content')
        user_input = input()
        print ('')
        if not user_input:
            show_question(replacement_tags,q_response,count,total)
        new_tags = change_tag(q_tags,user_input,tag,replacement_tags,site)
        if new_tags:
            q_response['tags'] = new_tags
            formed_data+=[q_response]
        count+=1
    return formed_data


def send_edits(formed_data,key,token,site,tag):    
    """
    Goes through the submitted edits and sends them to the site.
    Because edits appear on front page, there is a time limit.
    At a minimunm, it sends NO MORE than 1 per minute, and defaults to 1 minute 30 seconds.
    This is not user customisable via input. IT HAS TO BE CHANGED HERE.
    Think carefully before you change the value. No not change the 60 second limiter.
    """
    wait = 60
    print ('\nFinished tagging, sending edit data. Please wait '+str(max(60,wait))+' seconds between each edit.\n')
    failed = []
    titles = []
    errors = []
    n=len(formed_data)
    i=n
    for question_data in formed_data:
        q_id = int(question_data['question_id'])
        try:
            body_markdown = str(HTMLParser.HTMLParser().unescape(question_data['body_markdown']))
            title = str(HTMLParser.HTMLParser().unescape(question_data['title']))
            send = True
        except (UnicodeEncodeError,UnicodeDecodeError) as error:
            send = False
        tags = question_data['tags']

        if send:
            response = requests.post('https://api.stackexchange.com/2.2/questions/'+str(q_id)+'/edit',
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
            check_for_error(response_JSON)

            real_wait=max(60,wait) #DO NOT MODIFY THE NUMBER 60.
            
            for s in range(real_wait):
                loading_bar(n*real_wait,i*real_wait-s,' '+str(i*real_wait-s)+', '+str(i)+' left.')
                if i > 1:
                    time.sleep(1)
        else:
            failed += [q_id]
            titles += [question_data['items'][0]['title']]
            errors += [error]
        i-=1
    return [failed,titles,errors]


def get_auth(remove_file=False):
    """
    Retrieves auth token from authtoken.txt, or get's user input.
    The user is redirected to http://stackexchange.com then my site in the default webbrowser to get this token.
    The token is 24 chars long, and validated as that.
    """
    if remove_file:
        os.remove('authtoken.txt')#open('authtoken.txt','w').write('')
    try:
        token=open('authtoken.txt','r').read()
        token[1]
    except (IOError, IndexError):
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
        open('authtoken.txt','w').write('')
        get_auth(False)
    else:
        print ('Got token')
        open('authtoken.txt','w').write(token)
        return token

def display_failed(failed,titles,errors,site):
    print ('')
    if failed:
        display_list = input('Sent edits. '+str(len(failed))+' edits failed. Do you want to see a list? (y/N) ').lower()
        site=site_format(site)
        if display_list == 'y':
            for q_id,title,error in zip(failed,titles,errors):
                spacer()
                print ('"'+str(title)+'" was not edited sucsessfully. Error:'+str(error))
                print ('You may wish to edit it yourself, the url is http://'+site+'.com/questions/'+str(q_id))
                spacer()
            open_all=input('Do you wish to open all these questions for manual retagging? (y/N) ').lower()
            if open_all == 'y':
                for q_id in failed:
                    savout = os.dup(1)
                    os.close(1)
                    os.open(os.devnull, os.O_RDWR)
                    try:
                        webbrowser.open('http://'+site+'.com/questions/'+str(q_id))
                    finally:
                        os.dup2(savout, 1)
    kill_code('Finished Sending data. Exiting')

if len(sys.argv) < 2:
    site=input('Site: ').lower()
else:
    site = sys.argv[1]

if not site:
    kill_code('Invalid site name')

if len(sys.argv) < 3:
    """
    Get the tag to remove from questions
    """
    tag=input('Tag: ').lower()
else:
    tag = sys.argv[2]

if not tag:
    kill_code('Invalid tag name')


if len(sys.argv) < 4:
    """
    Get the number of questions to edit in batch. Max 100
    """
    try:
        batch=min(100, int(input('Number to edit at once: ')))
    except ValueError:
        print ('Invalid input. Setting to 10')
        batch=10
else:
    try:
        batch=min(100, int(sys.argv[3]))
    except ValueError:
        print ('Invalid input. Setting to 10')
        batch=10

if batch < 1:
    batch = 10

if len(sys.argv) < 5:
    replacement_tags=input('Tag alternatives: ').lower().split()
else:
    replacement_tags = sys.argv[4:]

if not replacement_tags:
    kill_code('Invalid replacement tags')

token = get_auth()
key = 'hDZI3p7wr3JAf1t)ccIIHA(('
items = get_from_search(site,batch,tag,key,token)
question_IDs = get_ids_from_items(items)
print ("Got IDs, fetching data")
all_data = get_tags_from_ids(question_IDs,key,token,batch)
formed_data=show_data(all_data,tag,replacement_tags,site)
results=send_edits(formed_data,key,token,site,tag)
failed=results[0]
titles=results[1]
errors=results[2]
display_failed(failed,titles,errors,site)
