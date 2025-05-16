from flask import Flask, request, jsonify
from flask import current_app as app
import os
import fitz  # PyMuPDF
import pinecone
from pinecone import Pinecone, ServerlessSpec
import uuid
from werkzeug.utils import secure_filename
import time
import json
from google import genai
import re

def init_pinecone():
    api_key = os.environ.get('PINECONE_API_KEY')
    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable not set")
    
    pc = Pinecone(api_key=api_key)
    return pc

def extract_text_from_pdf(file_path):
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def chunk_text(text, max_tokens=512, overlap=200):
    chars_per_token = 4
    max_chars = max_tokens * chars_per_token
    overlap_chars = overlap * chars_per_token
    
    chunks = []
    
    paragraphs = text.split('\n\n')
    
    current_chunk = ""
    current_length = 0
    
    for para in paragraphs:
        para = para.strip() + "\n\n"
        para_length = len(para)
        
        if current_length + para_length > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            if para_length > max_chars:
                sentences = para.replace('\n', ' ').split('. ')
                sentences = [s + '. ' for s in sentences if s]
                
                current_chunk = ""
                current_length = 0
                
                for sentence in sentences:
                    sentence_length = len(sentence)
                    
                    if sentence_length > max_chars:
                        words = sentence.split()
                        temp_chunk = ""
                        
                        for word in words:
                            if len(temp_chunk) + len(word) + 1 <= max_chars:
                                temp_chunk += word + " "
                            else:
                                chunks.append(temp_chunk.strip())
                                overlap_text = " ".join(temp_chunk.split()[-overlap:]) if overlap > 0 else ""
                                temp_chunk = overlap_text + " " + word + " "
                        
                        if temp_chunk.strip():
                            current_chunk = temp_chunk
                            current_length = len(temp_chunk)
                    
                    elif current_length + sentence_length <= max_chars:
                        current_chunk += sentence
                        current_length += sentence_length
                    
                    else:
                        chunks.append(current_chunk.strip())
                        overlap_text = " ".join(current_chunk.split()[-overlap:]) if overlap > 0 else ""
                        current_chunk = overlap_text + " " + sentence
                        current_length = len(current_chunk)
            
            else:
                if chunks and overlap > 0:
                    words = current_chunk.split()
                    if len(words) > overlap:
                        overlap_text = " ".join(words[-overlap:])
                        current_chunk = overlap_text + " " + para
                    else:
                        current_chunk = para
                else:
                    current_chunk = para
                
                current_length = len(current_chunk)
        
        else:
            current_chunk += para
            current_length += para_length
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

@app.route('/',methods=['GET'])
def home():
    return "api is running"

@app.route('/upload-pdfs', methods=['POST'])
def upload_pdfs():
    # 1) Validate files
    if 'files' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    files = request.files.getlist('files')
    if len(files) > 20:
        return jsonify({"error": "Maximum 20 files allowed"}), 400

    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_pdfs')
    os.makedirs(temp_dir, exist_ok=True)

    all_records = []
    total_pages = 0

    # 2) Extract & chunk each PDF
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": f"Invalid file: {file.filename}"}), 400

        filename = secure_filename(file.filename)
        tmp_path = os.path.join(temp_dir, filename)
        file.save(tmp_path)

        doc = fitz.open(tmp_path)
        page_count = len(doc)
        total_pages += page_count
        doc.close()

        if total_pages > 1000:
            return jsonify({"error": "Maximum 1000 pages allowed in total"}), 400

        full_text = extract_text_from_pdf(tmp_path)
        chunks    = chunk_text(full_text)

        for chunk in chunks:
            all_records.append({
                "_id":         str(uuid.uuid4()),    # record ID
                "text":  chunk,               # MUST match your index’s field_map
                "filename":    filename
            })

        os.remove(tmp_path)

    # 3) Upsert via upsert_records
    pc         = init_pinecone()
    idx        = pc.Index(os.environ['PINECONE_INDEX_NAME'])
    namespace  = app.config['PINECONE_NAMESPACE']
    BATCH_SIZE = 50

    for i in range(0, len(all_records), BATCH_SIZE):
        batch = all_records[i:i + BATCH_SIZE]
        idx.upsert_records(
            namespace=namespace,
            records=batch
        )

    return jsonify({
        "success":         True,
        "chunks_indexed":  len(all_records),
        "pages_processed": total_pages,
        "namespace":       namespace
    })

def perform_query(query_text):
    if not query_text:
        raise ValueError("Query text is required")
    
    namespace = app.config['PINECONE_NAMESPACE']
    
    pc = init_pinecone()
    index_name = os.environ.get('PINECONE_INDEX_NAME')
    
    if not index_name:
        raise ValueError("PINECONE_INDEX_NAME environment variable not set")
    
    index = pc.Index(index_name)
    
    results = index.search(
        namespace=namespace,
        query={
            "inputs": {"text": query_text},
            "top_k": 3
        },
        fields=["text", "filename"]
    )
    
    return results

@app.route('/query', methods=['POST'])
def query_docs():
    data = request.get_json(force=True)
    query_text = data.get('query')
    if not query_text:
        return jsonify({"error": "Missing `query` in request body"}), 400
    try:
        response_body = perform_query(query_text)
        response_body=response_body.to_dict()        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(response_body), 200

@app.route('/rag',methods=['POST'])
def RAG():
    data=request.get_json(force=True)
    prompt=data.get('prompt')
    client = genai.Client(api_key=os.environ.get("GEMINI"))
    system_prompt = (
    "Write an appropriate query for the given prompt to query a vector DB "
    "for a RAG application. Query should be of 3-5 sentences with all keywords relevant to the information present in the db. Dont include anything else, just return the query. Return the output in this exact JSON format: "
    "{\"query\": \"...\"}"
)

    full_prompt = f"{system_prompt}\n\nPrompt: {prompt}"
    response = client.models.generate_content(
    model="gemini-2.0-flash", contents=full_prompt
)
    response=response.to_json_dict()
    response=response['candidates'][0]['content']['parts'][0]['text']
    cleaned_text = re.sub(r"^```json\n|```$", "", response.strip(), flags=re.MULTILINE)
    query_obj = json.loads(cleaned_text)
    query_text = query_obj["query"]
    context=perform_query(query_text=query_text)
    context=context.to_dict()
    hits = context.get("result", {}).get("hits", [])
    all_texts = [hit["fields"]["text"] for hit in hits if "fields" in hit and "text" in hit["fields"]]

    combined_text = "\n\n".join(all_texts)
    system_prompt2 = (
    f"answer the the question {prompt} based on the context given below, try to answer from the given informatin only and not from outside of it. : {combined_text}"
)
    response = client.models.generate_content(
    model="gemini-2.5-flash-preview-04-17", contents=system_prompt2
)
    response=response.to_json_dict()
    response=response['candidates'][0]['content']['parts'][0]['text']
    return jsonify(response)
