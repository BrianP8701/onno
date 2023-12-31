from google.cloud import storage
from llama_index.node_parser import HierarchicalNodeParser
from llama_index import VectorStoreIndex, load_index_from_storage, StorageContext
from llama_index.schema import NodeWithScore
import gcsfs
import json
import os

'''
We want a llamaindex manager with these :
Attributes:
- username
- library name

Methods:
- update index (Add unadded documents into index)
- retrieve index object from GCS in cloud function
- save index back to GCS
- get k similar
'''


class CloudLLAMA_Index_Manager:
    '''
    This class manages a llama-index object stored in a JSON file on the cloud.
    Documents are added to the index and context is retrieved directly on the cloud without
    downloading the index to the local file system.
    
    retrieve_context(messages) -> str
    '''
    def __init__(self, project_name, bucket_name, llama_index_gcs_path):
        self.client = storage.Client(project=project_name)
        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name
        self.node_parser = HierarchicalNodeParser.from_defaults()
        self.llama_index_gcs_path = llama_index_gcs_path
        self.gcs = gcsfs.GCSFileSystem(project=project_name, token='secrets/onno-404216-b073f407c6eb.json')
        self.index = self.retrieve_or_create_index()
        
    def retrieve_or_create_index(self):
        if self.check_folder_exists(self.llama_index_gcs_path):
            return self.retrieve_index_from_gcs()
        else:
            return self.create_new_index()

    def create_new_index(self):
        index = VectorStoreIndex([]) 
        index.set_index_id(os.path.basename(self.llama_index_gcs_path))
        self.save_index_to_gcs(index)
        return index

    def retrieve_index_from_gcs(self):
        sc = StorageContext.from_defaults(persist_dir=self.bucket_name+'/'+self.llama_index_gcs_path, fs=self.gcs)
        return load_index_from_storage(sc, os.path.basename(self.llama_index_gcs_path))
    
    def save_index_to_gcs(self, index):
        index.storage_context.persist(self.bucket_name + '/' + self.llama_index_gcs_path, fs=self.gcs)

    def check_folder_exists(self, folder_prefix):
        blobs = self.bucket.list_blobs(prefix=folder_prefix)
        return any(True for _ in blobs)  # Folder exists if there are objects with the specified prefix

    def add_documents_to_index(self, documents_gcs_paths):
        for gcs_path in documents_gcs_paths:
            # Assuming documents are JSON files and we can use the JSON content as documents
            data = self.gcs.open(gcs_path, 'r').read()
            document = json.loads(data)
            self.index.insert(document)
        # Save the updated index back to GCS
        self.save_index_to_gcs(self.index)

# Cloud function handler
def process_documents_and_update_index(data, context):
    """
    This function is triggered by an event that provides JSON payload with 'data' and 'index_path'.
    """

    documents_gcs_paths = data['onno/users/b/libraries/avalon/text/DL_MIT.pdf']
    

    manager = CloudLLAMA_Index_Manager('onno-404216', 'onno', 'Briansvectoryyyy')
    manager.create_new_index()
    manager.add_documents_to_index(documents_gcs_paths)
    print(f"Updated index with documents from {documents_gcs_paths}")
from google.cloud import storage
from llama_index.node_parser import HierarchicalNodeParser
from llama_index import VectorStoreIndex, load_index_from_storage, StorageContext
from llama_index.schema import NodeWithScore
import functions_framework
import gcsfs
import os

@functions_framework.http
def llama_index_handler(request):
    """
    This function processes the HTTP request to interact with a llama index stored on Google Cloud Storage.
    It dispatches the request to various handlers based on the function name specified in the request JSON.

    Functions:
    - "create_new_index": Creates a new empty index and saves it to the specified GCS path.
    - "retrieve_context": Retrieves context based on the given messages from the request JSON.
    
    Args:
        request (flask.Request): The request object. Expected JSON structure:
            {
                "project_name": str,            # GCP project name.
                "bucket_name": str,             # GCS bucket name.
                "llama_index_gcs_path": str,    # GCS path to the llama index folder.
                ...                             # Other fields depending on the function_name.
            }

    Returns:
        flask.Response: A response object with the result of the dispatched function call, or an error message.
    """
    request_json = request.get_json(silent=False)
    project_name = request_json['project_name']
    bucket_name = request_json['bucket_name']
    llama_index_gcs_path = request_json['llama_index_gcs_path']
    
    handler = LLAMA_Index_Retriever(project_name, bucket_name, llama_index_gcs_path)
    try:
        result = handler.retrieve_context(request_json['messages'])
        return result, 200
    except Exception as e:
        return f"Invalid Input: {e}", 500

class LLAMA_Index_Retriever:
    def __init__(self, project_name, bucket_name, llama_index_gcs_path):
        self.client = storage.Client(project_name)
        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name
        self.node_parser = HierarchicalNodeParser.from_defaults()
        self.llama_index_gcs_path = llama_index_gcs_path
        self.gcs = gcsfs.GCSFileSystem()
        if self.check_folder_exists(llama_index_gcs_path):
            self.index = self.retrieve_index_from_gcs()    
            self.retriever = self.index.as_retriever()
        else:
            self.create_new_index()

    def dispatch(self, function_name, *args, **kwargs):
        function_map = {
            'retrieve_context': self.retrieve_context
        }
        if function_name not in function_map:
            raise ValueError(f"Function {function_name} not found.")
        return function_map[function_name](*args, **kwargs)
    
    def create_new_index(self):
        self.index = VectorStoreIndex([])
        self.index.set_index_id(os.path.basename(self.llama_index_gcs_path))
        self.save_index_to_gcs()
        self.retriever = self.index.as_retriever()
        return "Created new index successfully."
            
    def retrieve_context(self, messages):
        retriever = self.retriever
        retrieved_nodes: list[NodeWithScore] = retriever.retrieve(messages[-1]['message'])
        return ' '.join([node.text.replace('\n', ' ') for node in retrieved_nodes])
    
    def save_index_to_gcs(self):
        self.index.storage_context.persist(self.bucket_name + '/' + self.llama_index_gcs_path, fs=self.gcs)
        self.index = self.retrieve_index_from_gcs()
        return "Saved index successfully."

    def check_folder_exists(self, folder_prefix):
        blobs = self.bucket.list_blobs(prefix=folder_prefix)
        for blob in blobs:
            return True  # Folder exists as there are objects with the specified prefix
        return False  # Folder doesn't exist or is empty
    
    def retrieve_index_from_gcs(self):
        sc = StorageContext.from_defaults(persist_dir=self.bucket_name+'/'+self.llama_index_gcs_path, fs=self.gcs)
        return load_index_from_storage(sc, os.path.basename(self.llama_index_gcs_path))