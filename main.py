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



@app.get("/search", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/user/{username}", response_class=HTMLResponse)
async def renderuserprofile(request: Request, username:str):
    print("username ",username)
    return templates.TemplateResponse("friendProfile.html", {"request": request, 'username':username})

@app.get("/followers", response_class=HTMLResponse)
async def renderfollowers(request: Request):
    id_token = request.cookies.get('token')
    error_message = "No error here"
    user_token = None
    user = None

    print("inside get")
    user_token = validateFirebaseToken(id_token)
    print("inside user toekn ",user_token)

    if not user_token:
        return templates.TemplateResponse("main-page.html",{'request':request, 'user_token':None , 'error_message':None , 'user_info':None})
    
    return templates.TemplateResponse("followers.html", {"request": request , 'user_email':user_token['email']})

@app.get("/following", response_class=HTMLResponse)
async def renderfollowing(request: Request):
    id_token = request.cookies.get('token')
    error_message = "No error here"
    user_token = None
    user = None

    user_token = validateFirebaseToken(id_token)

    print("inside user toekn ",user_token)
    if not user_token:
        return templates.TemplateResponse("main-page.html",{'request':request, 'user_token':None , 'error_message':None , 'user_info':None})
    
    return templates.TemplateResponse("following.html", {"request": request , 'user_email':user_token['email']})




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


@app.post("/add-directory", response_class=RedirectResponse)
async def addDirectoryHandler(request: Request):
    id_token = request.cookies.get("token")
    user_token= validateFirebaseToken(id_token)
    if not user_token:
      return RedirectResponse('/')
    form = await request.form()
    dir_name = form['dir_name']
    if dir_name == '' or dir_name[-1] != '/':
        return RedirectResponse('/')
    addDirectory(dir_name)
    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

@app.post("/download-file", response_class=Response)
async def downloadFileHandler(request: Request):
    id_token= request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    form = await request.form()
    filename = form['filename']
    return Response (downloadBlob(filename))



@app.post("/api/posts/create", response_class=RedirectResponse)
async def uploadFileHandler(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')

    form = await request.form()
    image = form['image']
    description = form['description']

    # Check if a file was actually uploaded
    if image.filename == '':
        return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

    user = getuserfromemail(user_token['email'])
    print("user ",user_token)
    addFile(image, user, description)  # Assuming image is an UploadFile
    print(".filename = ", image.filename) 
    return JSONResponse(content={"sucess":True })


@app.post("/api/comment")
async def add_comment(data: CommentRequest, request: Request):
    try:
        post_ref = connectDB.collection('NewPost').where('id', '==', data.post_id).limit(1).stream()
        post = next(post_ref, None)

        if post is None:
            raise HTTPException(status_code=404, detail="Post not found")

        post_doc = connectDB.collection('NewPost').document(post.id)

        # New comment structure
        new_comment = {
            "username": data.username,
            "comment": data.comment,
            "Date": datetime.utcnow().isoformat()
        }

        # Append the comment to the existing array using Firestore arrayUnion
        post_doc.update({
            "user_comments": firestore.ArrayUnion([new_comment])
        })

        return {"message": "Comment added successfully", "comment": new_comment}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/api/commentAPost", response_class=JSONResponse)
async def addCommentToPost(request: Request):
    data = await request.json() 
    new_comment_data = data.get("comment")
    print("Received comment:", new_comment_data) 
    if not new_comment_data:
        return JSONResponse(content={"error": "No comment provided"}, status_code=400)

    post_id_field = new_comment_data.get("activePostId")
    if not post_id_field:
        return JSONResponse(content={"error": "No post ID provided"}, status_code=400)

    # Search by post.id field
    posts_ref = connectDB.collection("NewPost")
    query = posts_ref.where("id", "==", post_id_field).limit(1).get()

    if not query:
        return JSONResponse(content={"error": "Post not found"}, status_code=404)

    doc = query[0]
    post_doc = doc.to_dict()
    post_doc_id = doc.id

    print("post_doc_id:", post_doc_id)
    print("post_doc:", post_doc)
    print("new_comment_data ", new_comment_data)

    new_comment = {
        "username": new_comment_data["email"],
        "comment": new_comment_data["text"],
        "time": new_comment_data["timestamp"],
    }
    print("new comment ", new_comment)

    comments = post_doc.get("user_comments", [])
    comments.append(new_comment)

    # Update in the original NewPost collection
    doc.reference.update({
        "user_comments": comments
    })

    return JSONResponse(content={"message": "Comment added successfully", "new_comment": new_comment})