from flask import Flask
from dotenv import load_dotenv
import os
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)
app.app_context().push()

# Set a single namespace for the entire application
# If not set in environment, use a default value
app.config['PINECONE_NAMESPACE'] = os.environ.get('PINECONE_NAMESPACE', 'rag_documents')

from controllers import *

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)