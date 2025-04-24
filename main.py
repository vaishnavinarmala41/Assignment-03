from fastapi import FastAPI, Request , Form, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel,Field
from google.cloud import firestore , storage
from uuid import uuid4
from typing import List, Optional
from fastapi import HTTPException , status ,APIRouter
from fastapi.responses import JSONResponse, RedirectResponse
from google.auth.transport import requests
import google.oauth2.id_token
import time
import starlette.status as status
import local_constants
import uuid
from datetime import datetime

app = FastAPI()

# Serve static files like CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set template directory
templates = Jinja2Templates(directory="pages")

connectDB = firestore.Client()
firebase_request_adapter = requests.Request()


class Follower(BaseModel):
    username: str

class Following(BaseModel):
    username: str

class Comment(BaseModel):
    username: str
    comment: str
    time: str 

class Post(BaseModel):
    post_id: str
    Username: str             
    Date: str                 
    filename: str
    likes: int
    description: str
    comments: Optional[List[Comment]] = []

class User(BaseModel):
    name: str
    Username: str
    followers: Optional[List[Follower]] = []
    following: Optional[List[Following]] = []
    posts: Optional[List[str]] = []  
    joinedDate:str


class EmailRequest(BaseModel):
    email:str
 
 
class UserRequest(BaseModel):
    username: str

class UsernameRequest(BaseModel):
    username: str
    name:str
    email:str

class FollowRequest(BaseModel):
    username: str  # the user to be followed/unfollowed
    action: str  # either "follow" or "unfollow"
    currentUserName: str 


class ProfileUpdate(BaseModel):
    profileName: str
    username: str
    bio: str  # Assuming you plan to add this field
    email: str  # Used to identify the user
 
class CommentRequest(BaseModel):
    post_id: str
    comment: str
    username: str



def getuserfromemail(email):
    user_ref = connectDB.collection('NewUser').where('email_address', '==', email).limit(1).get()
    user_data = {
            'name':'John Doe'
        }
    if not user_ref:
        return user_data
    else:
        user_data = user_ref[0].to_dict()
        return user_data


def getUserPosts(username):
    posts = []
    posts_ref = connectDB.collection('NewPost')
    query = posts_ref.where('Username', '==', username).stream()
    for post in query:
        posts.append(post.to_dict())

    return posts

def createPost(filename, user, postdescription):
    post_id = str(uuid.uuid4())  # generate unique post ID
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # format current time
    connectDB.collection('NewPost').add(
            {
    "id": post_id,
    "Username": user['Username'],
    "author_email": user['email_address'],
    "Date": current_time,
    "media_file": filename,
    "like_count": 0,
    "caption": postdescription,
    "user_comments": []
})  
    print("created ")


def addDirectory(directory_name):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(directory_name)
    blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')

def addFile(file, user, postdescription):
    print("inside add file")
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)

    blob = bucket.blob(file.filename)  # Correct way to get a blob
    blob.upload_from_file(file.file, content_type=file.content_type)  # Pass file-like object
    createPost(file.filename, user, postdescription)

def blobList(prefix):
    print("local_constants.PROJECT_NAME ",local_constants.PROJECT_NAME)
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    return storage_client.list_blobs(local_constants.PROJECT_STORAGE_BUCKET, prefix=prefix)

def downloadBlob(filename):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.get_blob(filename)
    return blob.download_as_bytes()
    


def validateFirebaseToken(id_token):
    if not id_token:
        return None
    user_token = None 
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
    except ValueError as e:
        print(str(e))

    return user_token

def getuser(user_token):
    print("inside get user function")
    user = connectDB.collection('NewUser').document(user_token['user_id'])
    if not user.get().exists:
        user_data = {
            'name':'John Doe'
        }
        connectDB.collection('NewUser').document(user_token['user_id']).set(user_data)

    return user

@app.get("/myprofile", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("myprofile.html", {"request": request})

@app.get("/home", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    id_token = request.cookies.get('token')
    error_message = "No error here"
    user_token = None
    user = None

    print("inside get")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse("login.html",{'request':request, 'user_token':None , 'error_message':None , 'user_info':None})
    
    print("user validated")
    file_list = []
    directory_list = []

    blobs = blobList(None)
    print("after blobs")
    for blob in blobs:
        if blob.name[-1] == "/":
            directory_list.append(blob)
        else:
            file_list.append(blob)
    print("after blob") 
    user = getuser(user_token).get()
    return templates.TemplateResponse("login.html", {"request": request, 'user_token':user_token , 'error_message':error_message , 'user_info':user, 'file_list':file_list,'directory_list':directory_list})



@app.get("/api/detailsofuser/{userEmail}")
async def fetch_details_of_user(userEmail:str , response_class=JSONResponse):
    print("getting usrr ",userEmail)
    user_ref = connectDB.collection('NewUser').where('email_address', '==', userEmail).limit(1).get()
    if not user_ref:
        return JSONResponse(content={"error": "User not found"}, status_code=404)
    else:
        user_data = user_ref[0].to_dict()
        return JSONResponse(content={"user": user_data}, status_code=200)
    

    

@app.get("/api/user/{username}")
async def fetch_details_of_user(username: str , response_class=JSONResponse):
    print("getting usrr")
    user_ref = connectDB.collection('NewUser').where('Username', '==', username).limit(1).get()
    if not user_ref:
        return JSONResponse(content={"error": "User not found"}, status_code=404)
    else:
        user_data = user_ref[0].to_dict()
        return JSONResponse(content={"user": user_data}, status_code=200)
    
@app.post("/updateUsername")
async def update_username(profile: ProfileUpdate):
    users_ref = connectDB.collection('NewUser')
    print("email ",profile.email)
    query = users_ref.where('email_address', '==', profile.email).stream()

    user_doc = None
    for doc in query:
        user_doc = doc
        break

    if user_doc is None:
        return {"success": False, "message": "User not found"}

    update_data = {
        "name": profile.profileName,
        "Username": profile.username,
        "bio": profile.bio
    }

    users_ref.document(user_doc.id).update(update_data)
    return {"success": True, "message": "Profile updated"}


@app.post("/api/initializeuser")
async def initializeuser(data: EmailRequest):
    # print("check user ", data)
    user_ref = connectDB.collection('NewUser').where('email_address', '==', data.email).limit(1).get()
    if not user_ref:
        connectDB.collection('NewUser').add({
                "name": "",
                "email_address": data.email,
                "Username": "",
                "followers_list": [],
                "following_list": []
            })
        print("user created")
    else:
        print("user already exist")
        pass
    return 0