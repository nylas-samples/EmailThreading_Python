# Load your env variables
from dotenv import load_dotenv
load_dotenv()

# Import your dependencies
from flask import Flask,render_template,request,redirect,url_for
import re
import os
from nylas import APIClient
from bs4 import BeautifulSoup
import datetime
from datetime import date

# Create the app
app = Flask(__name__)

# Initialize your Nylas API client
nylas = APIClient(
    os.environ.get("CLIENT_ID"),
    os.environ.get("CLIENT_SECRET"),
    os.environ.get("ACCESS_TOKEN")
)

# Get the contact associated to the email address
def get_contact(nylas, email):
	contact =  nylas.contacts.where(email= email)
	if contact[0] != None:
		return contact[0]

# Download the contact picture if it's not stored already
def download_contact_picture(nylas, id):
	if id != None:
		contact = nylas.contacts.get(id)
		picture = contact.get_picture()
		file_name = "static/" +  id + ".png"
		file_ = open(file_name, 'wb')
		file_.write(picture.read())
		file_.close()

# This the landing page
@app.route("/", methods=['GET','POST'])
def index():
# We're using a GET, display landing page
	if request.method == 'GET':
		 return render_template('main.html')
# Get parameters from form
	else:
		search = request.form["search"]
	    
	    # Search all threads related to the email address
		threads = nylas.threads.where(from_= search, in_= 'inbox')
		
		_threads = []
		
		# Loop through all the threads
		for thread in threads:
			_thread = []
			_messages = []
			_pictures = []
			_names = []
			# Look for threads with more than 1 message
			if len(thread.message_ids) > 1:
				# Get the subject of the first email
				_thread.append(thread["subject"])
				# Loop through all messages contained in the thread
				for message in thread["message_ids"]:
					# Get information from the message
					message = nylas.messages.get(message)
					# Try to get the contact information	
					contact = get_contact(nylas, message["from"][0]["email"])
					if contact != None and contact != "":
						# If the contact is available, downloads its profile picture
						download_contact_picture(nylas, contact.id)
					# Remove extra information from the message like appended 
					#  message, email and phone number
					soup = BeautifulSoup(message["body"],features="html.parser")
					regex = r"(\bOn.*\b)(?!.*\1)"
					result = re.sub(regex, "", str(soup), 0, re.MULTILINE)
					regex = r"[a-z0-9._-]+@[a-z0-9._-]+\.[a-z]{2,3}\b"
					result = re.sub(regex, "", result, 0, re.MULTILINE)
					regex = r"(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}"
					result = re.sub(regex, "", result, 0, re.MULTILINE)
					regex = r"twitter:.+"
					result = re.sub(regex, "", result, 0, re.MULTILINE)
					soup = BeautifulSoup(result, "html.parser")
					for data in soup(['style', 'script']):
						# Remove tags
						data.decompose()
					result = '<br>'.join(soup.stripped_strings)	
					_messages.append(result)
					# Convert date to something readable
					date = datetime.datetime.fromtimestamp(message["date"]).strftime('%Y-%m-%d')
					time = datetime.datetime.fromtimestamp(message["date"]).strftime('%H:%M:%S')
					if contact == None or contact == "":
						_pictures.append("NotFound.png")
						_names.append("Not Found" + " on " + date + " at " + time)
					else:
						# If there's a contact, pass picture information, 
						# name and date and time of message
						_pictures.append(contact["id"] + ".png")
						_names.append(contact["given_name"] + 
									     " " + contact["surname"] + " on " + date + 
                                         " at " + time)
				_thread.append(_messages)
				_thread.append(_pictures)
				_thread.append(_names)
				_threads.append(_thread)
		return render_template('main.html', threads = _threads)

# Run our application  
if __name__ == "__main__":
  app.run()
