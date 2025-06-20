from typing import List

from fastapi import APIRouter

from agno.os.connectors.knowledge.schemas import DocumentRequestSchema, DocumentResponseSchema
from agno.knowledge.knowledge import Knowledge, Document


def attach_routes(router: APIRouter, knowledge: Knowledge) -> APIRouter:
    @router.post("/documents", response_model=DocumentRequestSchema, status_code=201)
    async def add_document(document: DocumentRequestSchema) -> DocumentRequestSchema:
        knowledge.add_document(
            document=Document(
                name=document.name,
                content=document.content,
                # TODO
            )
        )

        return document

    @router.get("/documents", response_model=List[DocumentResponseSchema], status_code=200)
    async def get_documents() -> List[DocumentResponseSchema]:
        documents = knowledge.get_all_documents()

        return [
            DocumentResponseSchema(
                name=document.name,
                content=document.content,
                # TODO
            )
            for document in documents
        ]

    @router.get("/documents/{document_id}", response_model=DocumentResponseSchema, status_code=200)
    async def get_document_by_id(document_id: str) -> DocumentResponseSchema:
        document = knowledge.get_document_by_id(document_id=document_id)

        return DocumentResponseSchema(
            name=document.name,
            content=document.content,
            # TODO
        )
    
    @router.delete("/documents/{document_id}", response_model=DocumentResponseSchema, status_code=200)
    async def delete_document_by_id(document_id: str) -> DocumentResponseSchema:
        deleted_document = knowledge.delete_document(document_id=document_id)

        return DocumentResponseSchema(
            name=deleted_document.name,
            content=deleted_document.content,
            # TODO
        )

    @router.delete("/documents/", status_code=200)
    async def delete_all_documents():
        knowledge.delete_all_documents()

        return

    return router
