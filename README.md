
# RAG App 

A Retrieval-Augmented Generation (RAG) web application.  
Upload PDFs, ask questions, and get context-aware answers using Pinecone and Google Gemini.
---
Application is highly scalable and can leverage paid hosting and storage plans to adapt to higher traffic.

## Features

- **PDF Upload:** Upload up to 20 PDFs at once.
- **RAG Backend:** Uses Pinecone for vector search and Google Gemini for answer generation.
- **Dockerized:** Easy to run anywhere.

---

## Quick Start

### 1. Clone & Install

```sh
git clone https://github.com/avichhitwal/rag_app
cd rag_app
python -m venv myenv
.\myenv\Scripts\activate.ps1  # On Windows
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file (see below):

```
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=your_index_name
GEMINI=your_gemini_api_key
```

### 3. Run Locally

```sh
python app.py
```

Visit [http://localhost:5000](http://localhost:5000) for the API  
Open `index.html` in your browser for the frontend.

---

## Docker

### Build & Run

```sh
docker build -t rag_app:v8 .
docker run -p 5000:5000 rag_app:v8
```

---

## Usage

- **Ask a Question:**  
  Type your question and get a Markdown-formatted answer.

- **Upload PDFs:**  
  Upload up to 20 PDF files. Their content will be chunked and indexed for retrieval.

---

## File Structure

```
rag_app/
│
├── app.py              # Flask app entrypoint
├── controllers.py      # All API endpoints and logic
├── index.html          
├── requirements.txt
├── Dockerfile
├── .env
├── .dockerignore
├── .gitignore
```

---

## API Endpoints

- `GET /` — Health check
- `POST /upload-pdfs` — Upload up to 20 PDFs
- `POST /rag` — Ask a question (JSON: `{ "prompt": "..." }`)
- `POST /query` — Direct vector DB query (JSON: `{ "query": "..." }`)

---

## Credits

- [Flask](https://flask.palletsprojects.com/)
- [Pinecone](https://www.pinecone.io/)
- [Google Gemini](https://ai.google.dev/)
- [Marked.js](https://marked.js.org/)
- [DOMPurify](https://github.com/cure53/DOMPurify)

---
