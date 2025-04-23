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