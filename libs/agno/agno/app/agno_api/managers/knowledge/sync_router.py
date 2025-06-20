from typing import List

from fastapi import APIRouter, Form, File, UploadFile

from agno.knowledge.knowledge import Knowledge
from agno.app.agno_api.schemas.knowledge.schemas import DocumentResponseSchema
from agno.utils.log import log_info
import uuid
from agno.document.document_v2 import DocumentV2, DocumentContent
import json
def attach_sync_routes(router: APIRouter, knowledge: Knowledge) -> APIRouter:



    @router.post("/documents")
    async def upload_documents(
        names: List[str] = Form(...),
        descriptions: List[str] = Form(...),
        urls: List[str] = Form(...),        # JSON stringified lists
        metadata: List[str] = Form(...),   # JSON stringified dicts
        contents: List[UploadFile] = File(...),
        type: List[str] = Form(...)
    ):
        for i in range(len(contents)):
            # Read the content once and store it
            content_bytes = await contents[i].read()

            # Parse URLs with proper error handling
            parsed_urls = None
            if urls[i] and urls[i].strip():
                try:
                    parsed_urls = json.loads(urls[i])
                except json.JSONDecodeError:
                    # If it's not valid JSON, treat as a single URL string
                    parsed_urls = [urls[i]] if urls[i] != "string" else None

            # Parse metadata with proper error handling
            parsed_metadata = None
            if metadata[i] and metadata[i].strip():
                try:
                    parsed_metadata = json.loads(metadata[i])
                except json.JSONDecodeError:
                    # If it's not valid JSON, treat as a simple key-value pair
                    parsed_metadata = {"value": metadata[i]} if metadata[i] != "string" else None

            document = DocumentV2(
                name=names[i],
                description=descriptions[i],
                urls=parsed_urls,
                metadata=parsed_metadata,
                content=DocumentContent(
                    content=content_bytes,
                    type=type[i]
                )
            )
            knowledge.add_document(document)

        return {"documents": "success"}
    

    @router.get("/documents", response_model=List[DocumentResponseSchema], status_code=200)
    def get_documents() -> List[DocumentResponseSchema]:
        documents = knowledge.get_documents()
        result = []
        for document in documents:
            # Convert DocumentV2 to DocumentResponseSchema
            response_doc = DocumentResponseSchema(
                id=document.id,  # Generate a unique ID
                name=document.name,
                description=document.description,
                type=document.content.type if document.content else None,
                size=str(len(document.content.content)) if document.content else "0",
                linked_to=knowledge.name,
                metadata=document.metadata,
                access_count=0
            )
            result.append(response_doc)
        return result
       
    @router.get("/documents/{document_id}", response_model=DocumentResponseSchema, status_code=200)
    def get_document_by_id(document_id: str) -> DocumentResponseSchema:
        document = knowledge.get_document(document_id=document_id)

        log_info(f"Getting document by id: {document_id}")

        document_1 = DocumentResponseSchema(
            id=document_id,
            name="Document 1",
            description="Description 1",
            type="pdf",
            size="100",
            linked_to="1",
            metadata={"user_tag": "User 1"},
        )

        return document_1

    @router.delete("/documents/{document_id}", response_model=DocumentResponseSchema, status_code=200)
    def delete_document_by_id(document_id: str) -> DocumentResponseSchema:
        knowledge.remove_document(document_id=document_id)
        log_info(f"Deleting document by id: {document_id}")

        return DocumentResponseSchema(
            id=document_id,
        )
    
    @router.delete("/documents/", status_code=200)
    def delete_all_documents():
        # knowledge.delete_all_documents()
        log_info(f"Deleting all documents")
        return [
            DocumentResponseSchema(
                id=str(uuid.uuid4()),
                name="Document 1",
            ),
            DocumentResponseSchema(
                id=str(uuid.uuid4()),
                name="Document 2",
            ),
            DocumentResponseSchema(
                id=str(uuid.uuid4()),
                name="Document 3",
            ),
        ]

    return router