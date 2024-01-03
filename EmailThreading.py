# Import your dependencies
from flask import Flask,render_template,request
import re
import os
from nylas import Client
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from nylas.models.threads import ListThreadsQueryParams
from dataclasses import dataclass
import urllib.request

# Load your env variables
load_dotenv()

@dataclass
class main_thread():
    thread: str
    message: int
    picture: float
    names: str

data_threads = []
all_threads = []

# Create the app
app = Flask(__name__)

# Initialize an instance of the Nylas SDK using the client credentials
nylas = Client(
    api_key = os.environ.get("V3_TOKEN")
)

# Get the contact associated to the email address
def get_contact(nylas, email):
    query_params = {
        'email': email
    }   
    
    contacts, _, _ =  nylas.contacts.list(os.environ.get("GRANT_ID"), query_params)
    for contact in contacts:
        return contact

# Download the contact picture if it's not stored already
def download_contact_picture(contact):
    full_path = f'static/{contact.given_name}_{contact.surname}.png'
    urllib.request.urlretrieve(contact.picture_url, full_path)  

# This the landing page
@app.route("/", methods=['GET','POST'])
def index():
# We're using a GET, display landing page
    if request.method == 'GET':
         return render_template('main.html')
# Get parameters from form
    else:
        search = request.form["search"]
        
        query_params = ListThreadsQueryParams(
            {'search_query_native': f'from: #{search}'}
        )
        
        # Search all threads related to the email address
        threads, _, _ = nylas.threads.list(os.environ.get("GRANT_ID"), query_params)
        
        all_threads = []
        
        # Loop through all the threads
        for thread in threads:
            # Look for threads with more than 1 message
            if len(thread.message_ids) > 1:
                # Get the subject of the first email
                subject = thread.subject
                # Loop through all messages contained in the thread
                for message in thread.message_ids:
                    # Get information from the message
                    message, _ = nylas.messages.find(os.environ.get("GRANT_ID"), message)
                    # Try to get the contact information    
                    contact = get_contact(nylas, message.from_[0]["email"])
                    if contact is not None and contact != "":
                        # If the contact is available, downloads its profile picture
                        download_contact_picture(contact)
                    # Remove extra information from the message like appended 
                    #  message, email and phone number
                    soup = BeautifulSoup(message.body, "html.parser")
                    for data in soup(['style', 'script']):
                        # Remove tags
                        data.decompose()
                    result = '<br>'.join(soup.stripped_strings) 
                    regex = r"(\bOn.*\b)(?!.*\1)"
                    result = re.sub(regex, "", result, 0, re.MULTILINE)
                    regex = r"[a-zA-z0-9._-]+@[a-zA-z0-9._-]+\.[a-z]{2,3}\b"
                    result = re.sub(regex, "", result, 0, re.MULTILINE)
                    regex = r"(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}"
                    result = re.sub(regex, "", result, 0, re.MULTILINE)
                    regex = r"(T|t)witter:.+"
                    result = re.sub(regex, "", result, 0, re.MULTILINE)
                    body = result
                    # Convert date to something readable
                    date = message.date.strftime('%Y-%m-%d')
                    time = message.date.strftime('%H:%M:%S')
                    if contact is None or contact == "":
                        picture = "NotFound.png"
                        names = "Not Found" + " on " + date + " at " + time
                    else:
                        # If there's a contact, pass picture information, 
                        # name and date and time of message
                        picture = contact.given_name + "_" + contact.surname + ".png"
                        names  = contact.given_name + " " + contact.surname + " on " + date + " at " + time
                    new_thread = main_thread(subject, body, picture, names)
                    data_threads.append(new_thread)
                all_threads.append(data_threads.copy())
                data_threads.clear()
        return render_template('main.html', threads = all_threads)

# Run our application  
if __name__ == "__main__":
  app.run()
