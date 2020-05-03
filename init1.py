#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect, send_file
import pymysql.cursors
import hashlib
import os
import time
from functools import wraps
IMAGES_DIR = os.path.join(os.getcwd(), "photos")

#Initialize the app from Flask
app = Flask(__name__)

#Define salt for the password
SALT = "cs3083"

#Configure MySQL
conn = pymysql.connect(host='localhost',
					   port = 8889,
					   user='root',
					   password='root',
					   db='finstagram',
					   charset='utf8mb4',
					   cursorclass=pymysql.cursors.DictCursor)

#--------Define a route to hello function
@app.route('/')
def hello():
	return render_template("index.html")

#---------Make sure user is logged in
def login_required(func):
	@wraps(func)
	def dec(*args, **kwargs):
		if not 'username' in session:
			return redirect(url_for("login"))
		return func(*args, **kwargs)
	return dec

#--------------Define route for login
@app.route('/login')
def login():
	return render_template('login.html')

#-------------Define route for register
@app.route('/register')
def register():
	return render_template('register.html')

#-------------Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
	#grabs information from the forms
	username = request.form['username']
	password = request.form['password'] + SALT
	hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
	
	#cursor used to send queries
	cursor = conn.cursor()
	#executes query
	query = 'SELECT * FROM Person WHERE username = %s and password = %s'
	cursor.execute(query, (username, hashed_password))
	#stores the results in a variable
	data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row
	cursor.close()
	error = None
	if(data):
		#creates a session for the the user
		#session is a built in
		session['username'] = username
		return redirect(url_for('home'))
	else:
		#returns an error message to the html page
		error = 'Invalid login or username'
		return render_template('login.html', error=error)

#----------Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
	#grabs information from the forms
	username = request.form['username']
	password = request.form['password'] + SALT 
	hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
	firstName = request.form['firstname']
	lastName = request.form['lastname']
	email = request.form['email']
	#cursor used to send queries
	cursor = conn.cursor()
	#executes query
	query = 'SELECT * FROM Person WHERE username = %s'
	cursor.execute(query, (username))
	#stores the results in a variable
	data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row
	error = None
	if(data):
		#If the previous query returns data, then user exists
		error = "This user already exists"
		return render_template('register.html', error = error)
	else:
		ins = "INSERT INTO person (username, password, firstname, lastname, email) VALUES (%s, %s, %s, %s, %s)"
		cursor.execute(ins, (username, hashed_password, firstName, lastName, email))
		conn.commit()
		cursor.close()
		return render_template('index.html')


@app.route('/home')
@login_required
def home():
	return render_template('home.html', username=session["username"])

#----Required feature 1 - View Visible Photos
@app.route("/photos", methods = ["GET"])
@login_required
def photos(): 
	user = session["username"]
	cursor = conn.cursor()
	query = "SELECT pID, poster FROM Photo ORDER BY postingDate DESC"
	cursor.execute(query)
	photos = cursor.fetchall()
	cursor.close()
	return render_template("photos.html", photos = photos)

#-----------Required feature 2 - More Info 
@app.route("/viewPhotos/<int:pID>", methods=["GET", "POST"])
@login_required
def viewPhotos(pID):
	user = session["username"]
	
	#query for pID, filePath, postingDate
	cursor = conn.cursor()
	query = "SELECT pID, postingDate, filePath FROM Photo WHERE pID = %s"
	cursor.execute(query, (pID))
	data = cursor.fetchall()

	#first and last name of the poster 
	query2 = "SELECT firstName, lastName FROM Person WHERE username = %s"
	cursor = conn.cursor()
	cursor.execute(query2, (user))
	name = cursor.fetchall()

	#query to get usernames, firstName and lastName of taggedPeople 
	query3 = "SELECT username, firstName, lastName FROM Person NATURAL JOIN Tag WHERE pID = %s AND tagStatus = 1"
	cursor = conn.cursor()
	cursor.execute(query3, (pID))
	tag = cursor.fetchall()

	#username of people who ReactedTo the photo
	query4 = "SELECT username, comment FROM ReactTo WHERE pID = %s "
	cursor = conn.cursor()
	cursor.execute(query4, (pID))
	comment = cursor.fetchall()

	return render_template("viewPhotos.html", photos = data, names = name, tags = tag, comments = comment)

@app.route("/photo/<image_name>", methods=["GET"])
def image(image_name):
	image_location = os.path.join(IMAGES_DIR, image_name)
	if os.path.isfile(image_location):
		return send_file(image_location, mimetype="image/jpg")

#------------Required Feature 3: Post a photo
@app.route("/upload")
@login_required
def upload():
	query = "SELECT groupName, groupCreator FROM BelongTo WHERE username = %s"
	with conn.cursor() as cursor:
		cursor.execute(query, (session["username"]))
	data = cursor.fetchall()
	return render_template("upload.html", groups = data)


@app.route("/uploadPhoto", methods=["GET", "POST"])
@login_required
def uploadPhoto():
	if request.files:
		image_file = request.files.get("imageToUpload", "")
		image_name = image_file.filename
		filePath = os.path.join(IMAGES_DIR, image_name)
		image_file.save(filePath) 

		userName = session["username"]
		caption = request.form.get('caption')
		display = request.form.get('display')

		#Post to all followers
		if display == "All Followers":
			allFollowers = "1"
			query = "INSERT INTO Photo (postingDate, filePath, allFollowers, caption, poster) " \
					"VALUES (%s, %s, %s, %s, %s)"
			with conn.cursor() as cursor:
				cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, allFollowers, caption, userName))
				conn.commit()
				cursor.close()
       
		else:
			allFollowers = "0"
			query = "INSERT INTO Photo (postingDate, filePath, allFollowers, caption, poster)" \
					" VALUES (%s, %s, %s, %s, %s)"
			with conn.cursor() as cursor:
				cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, allFollowers, caption, userName))
				conn.commit()
				cursor.close()

		message = "photo successfully uploaded."
		return render_template("upload.html", message=message)

	else:
		message = "Failed to upload photo"
		return render_template("upload.html", message=message)

#------------Required 4 Manage Follows
@app.route('/follow', methods = ["GET", "POST"])
@login_required
def follow(): 

	cursor = conn.cursor()

	if(request.form): 
		user = session["username"]
		followee = request.form["followee"]	
		
		query = "INSERT INTO Follow(follower, followee, followStatus) VALUES (%s, %s, %s)"
		cursor = conn.cursor()
		cursor.execute(query, (user, followee, 0))
		cursor.close()
		return render_template("home.html")

	return render_template("follow.html")

@app.route('/manageFollowRequests', methods = ["GET", "POST"])
def manageFollowRequests():
	
	user = session['username']
	cursor = conn.cursor()
	query = 'SELECT * FROM Follow WHERE followee = %s AND followStatus= 0'
	cursor.execute(query, (user))	
	data = cursor.fetchall()
	cursor.close()
	return render_template('manageFollowRequests.html', pending = data)

@app.route('/acceptFollower/<string:follower>', methods = ['GET', 'POST'])
def acceptFollower(follower):
	user = session['username']
	cursor = conn.cursor();
	query = 'UPDATE Follow SET followStatus = 1 WHERE followee = %s AND follower = %s'
	cursor.execute(query, (user, follower))
	conn.commit()
	cursor.close()
	return manageFollowRequests()

@app.route('/rejectFollower/<string:follower>', methods = ['GET', 'POST'])
def rejectFollower(follower):
	user = session['username']
	cursor = conn.cursor();
	query = 'DELETE FROM Follow WHERE followee = %s AND follower = %s'
	cursor.execute(query, (user, follower))
	conn.commit()
	cursor.close()

	return manageFollowRequests()

#----Required Feature 5: Define route for FriendGroup
@app.route("/create_friendgroup")
@login_required
def create_friendgroup():
    return render_template("FriendGroup.html")


@app.route("/saveFriendGroupToDatabase",methods=['GET', 'POST'])
@login_required
def saveFriendGroupToDatabase():
    #check if group exists
    user = session['username']
    description = request.form['description']
    groupname = request.form['groupname']
    
    #cursor used to send queries
    cursor = conn.cursor()

    #executes query
    query1 = 'SELECT * FROM FriendGroup WHERE groupCreator = %s AND groupName = %s'
    cursor.execute(query1, (user, groupname))

    #stores the results in a variable
    data = cursor.fetchone()
    
    error = None
    if(data):
        #If the previous query returns data, then group exists
        error = "This group already exists"
        cursor.close()
        return render_template('FriendGroup.html', error = error)
    
    else:
        ins = "INSERT INTO FriendGroup (groupName, groupCreator, description) VALUES (%s, %s, %s)"
        cursor.execute(ins, (groupname, user, description))
        conn.commit()
        cursor.close()
        error = "Group created successfully"
        return render_template('FriendGroup.html', error = error)
    
#--------Extra Feature #6 - Manage Tags
#----Define route for tag
@app.route("/tag", methods=["GET"])
@login_required
def tag():
    user = session["username"]
    
    #query for pID, filePath, postingDate
    cursor = conn.cursor()
    query = "SELECT pID, filePath, postingDate FROM Photo WHERE poster = %s ORDER BY postingDate DESC"
    cursor.execute(query, (user))
    data = cursor.fetchall()
    

    #first and last name of the poster 
    query2 = "SELECT firstName, lastName FROM Person WHERE username = %s"
    cursor = conn.cursor()
    cursor.execute(query2, (user))
    name = cursor.fetchall()

    #query to get usernames, firstName and lastName of taggedPeople 
    query3 = "SELECT username, firstName, lastName FROM Person NATURAL JOIN Tag WHERE pID = %s AND tagStatus = 1"
    cursor = conn.cursor()
    cursor.execute(query3, (user))
    tag = cursor.fetchall()

    #username of people who ReactedTo the photo
    query4 = "SELECT username, comment, emoji FROM ReactTo WHERE pID = %s "
    cursor = conn.cursor()
    cursor.execute(query4, (user))
    comment = cursor.fetchall()

    return render_template("tag.html", photos = data, names = name, tags = tag, comments = comment)



@app.route("/savetags",methods=['GET', 'POST'])
@login_required
def savetags():
    #cursor used to send queries
    cursor = conn.cursor()
    
    user = session['username']
    taggeduser = request.form['taggedperson']
    pictureid = request.form['pictureid']
    
    #case 1 self tag
    if (user == taggeduser):
        #Finstagram adds a row to the Tag table: (x, photoID, true)
        #username, tagStatus, pID
        ins = "INSERT INTO Tag (username, tagStatus, pID) VALUES (%s, %s, %s)"
        cursor.execute(ins, (user, 1, pictureid))
        conn.commit()
        cursor.close()
        error = "Successfully tagged yourself!"
        return render_template('tag.html', error = error)


    #executes query
    #query1 = 'SELECT * FROM FriendGroup WHERE groupCreator = %s AND groupName = %s'
    
    query1 = 'select followStatus from photo ph, follow fo where ph.poster = fo.followee and ph.allFollowers = true and poster=%s and pid = %s and follower  = %s' 
    


    cursor.execute(query1, (user, pictureid, taggeduser))
    #stores the results in a variable
    data = cursor.fetchone()
    if data == None:
        error = "Invalid user specified"
        return render_template('tag.html', error = error)
    
    error = None
    if(data['followStatus'] == 1):
        #If the previous query returns data, then follower exists
        ins = "INSERT INTO Tag (username, tagStatus, pID) VALUES (%s, %s, %s)"
        cursor.execute(ins, (user, 0, pictureid))
        cursor.close()
        conn.commit()
        
        error = "User successfully tagged"
        return render_template('tag.html', error = error)
    
    else:
        error = "Tag failed"
        return render_template('tag.html', error = error)


#--------Extra Feature #7 - React to a photo
@app.route("/comment/<pID>", methods=["GET", "POST"])
@login_required
def comment(pID):
	cursor = conn.cursor()

	if(request.form): 	
		user = session["username"]
		comment = request.form["comment"]
	
		query = "INSERT INTO ReactTo (username, pID, reactionTime, comment) VALUES (%s, %s, %s, %s)"
		cursor.execute(query, (user, pID, time.strftime('%Y-%m-%d %H:%M:%S'), comment))	
		return redirect(url_for('viewPhotos', pID = pID))
		
	
	cursor.close()
	return redirect(url_for('home'))

#------Extra Feature #9 - Search By Tag
@app.route("/searchByTag", methods=["POST"])
@login_required
def searchByTag():
	user = session["username"]
	if(request.form):
		tagged = request.form.get("tagged")
		cursor = conn.cursor()
	
		query = "SELECT pID FROM Photo WHERE pID IN (SELECT pID FROM SharedWith WHERE groupName IN (SELECT groupName FROM BelongTo WHERE groupCreator = %s OR username = %s)) ORDER BY postingDate DESC"
		query2 = "SELECT pID FROM Tag WHERE username = %s AND tagStatus = 1"
		cursor.execute(query, (user, user))
		cursor.execute(query2, (tagged))
		photos = cursor.fetchall()
	
	return render_template("searchByTag.html", tagged = tagged , photos = photos)

#------------Log Out
@app.route('/logout')
def logout():
	session.pop('username')
	return redirect('/')
		
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)
