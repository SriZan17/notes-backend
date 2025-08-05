from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
import os
import random
from typing import Optional, List, Dict, Any
import math
import dotenv

dotenv.load_dotenv()

app = FastAPI(title="Notes API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://srizan17.github.io", 
        "http://localhost:3000",
        "https://srijanbasnet.com",
        "https://srijanbasnet.com.np",
        "https://www.srijanbasnet.com.np",  # Your main website
        "https://api.srijanbasnet.com.np",  # Your new HTTPS API
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
client = MongoClient(MONGODB_CONNECTION_STRING)
db = client["notes"]
notes_collection = db["quotes"] 

# Helper function to convert ObjectId to string
def serialize_doc(doc):
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc

def serialize_docs(docs):
    return [serialize_doc(doc.copy()) for doc in docs]

@app.get("/")
async def root():
    return {"message": "Notes API is running"}

@app.get("/notes/")
async def get_notes(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=100)):
    """Get paginated notes"""
    try:
        skip = (page - 1) * limit
        
        # Get total count
        total_count = notes_collection.count_documents({})
        
        # Get notes with pagination
        notes = list(notes_collection.find({}).skip(skip).limit(limit))
        
        # Calculate pagination URLs
        total_pages = math.ceil(total_count / limit)
        next_url = f"/notes/?page={page + 1}&limit={limit}" if page < total_pages else None
        prev_url = f"/notes/?page={page - 1}&limit={limit}" if page > 1 else None
        
        return {
            "results": serialize_docs(notes),
            "count": total_count,
            "next": next_url,
            "previous": prev_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notes/search/")
async def search_notes(q: str = Query(..., min_length=1), folder: Optional[str] = None):
    """Search notes by title or body content"""
    try:
        # Build search query - search in both title and body
        search_conditions = [
            {"title": {"$regex": q, "$options": "i"}},
            {"body": {"$regex": q, "$options": "i"}}
        ]
        
        search_query = {"$or": search_conditions}
        
        # Add folder filter if specified
        if folder:
            search_query["folder"] = folder
        
        # Find matching notes
        notes = list(notes_collection.find(search_query))
        
        return {"data": serialize_docs(notes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notes/random/")
async def get_random_note():
    """Get a random note"""
    try:
        # Get random note using MongoDB aggregation
        pipeline = [{"$sample": {"size": 1}}]
        notes = list(notes_collection.aggregate(pipeline))
        
        if not notes:
            raise HTTPException(status_code=404, detail="No notes found")
        
        note = notes[0]
        return {"data": serialize_doc(note)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/folders/")
async def get_folders():
    """Get all unique folders with note counts"""
    try:
        # Get folders with note counts using aggregation
        pipeline = [
            {"$group": {
                "_id": "$folder",
                "note_count": {"$sum": 1}
            }},
            {"$sort": {"note_count": -1}},
            {"$project": {
                "name": "$_id",
                "note_count": 1,
                "_id": 0
            }}
        ]
        
        folders = list(notes_collection.aggregate(pipeline))
        return {"data": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/folders/search/")
async def search_folders(q: str = Query(..., min_length=1)):
    """Search folders by name"""
    try:
        # Get unique folders that match the search query
        pipeline = [
            {"$group": {"_id": "$folder"}},
            {"$match": {"_id": {"$regex": q, "$options": "i"}}},
            {"$project": {"name": "$_id", "_id": 0}},
            {"$sort": {"name": 1}}
        ]
        
        folders = list(notes_collection.aggregate(pipeline))
        return {"data": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/folders/{folder_name}")
async def get_folder_with_notes(folder_name: str):
    """Get all notes in a specific folder"""
    try:
        # Get notes in this folder
        notes = list(notes_collection.find({"folder": folder_name}))
        
        if not notes:
            raise HTTPException(status_code=404, detail="Folder not found or no notes in folder")
        
        return {
            "data": {
                "folder_name": folder_name,
                "note_count": len(notes),
                "notes": serialize_docs(notes)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notes/by-folder/{folder_name}")
async def get_notes_by_folder(folder_name: str, page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=100)):
    """Get paginated notes from a specific folder"""
    try:
        skip = (page - 1) * limit
        
        # Get total count for this folder
        total_count = notes_collection.count_documents({"folder": folder_name})
        
        if total_count == 0:
            raise HTTPException(status_code=404, detail="Folder not found or no notes in folder")
        
        # Get notes with pagination
        notes = list(notes_collection.find({"folder": folder_name}).skip(skip).limit(limit))
        
        # Calculate pagination URLs
        total_pages = math.ceil(total_count / limit)
        next_url = f"/notes/by-folder/{folder_name}?page={page + 1}&limit={limit}" if page < total_pages else None
        prev_url = f"/notes/by-folder/{folder_name}?page={page - 1}&limit={limit}" if page > 1 else None
        
        return {
            "results": serialize_docs(notes),
            "count": total_count,
            "folder": folder_name,
            "next": next_url,
            "previous": prev_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)