from __future__ import annotations

from app.models.shared_ref import OntologySharedRef
from app.repositories.base import BaseRepository


class SharedRefRepository(BaseRepository[OntologySharedRef]):
    model = OntologySharedRef

    def list_by_target(self, target_ontology_id: str) -> list[OntologySharedRef]:
        return self.db.query(OntologySharedRef).filter(
            OntologySharedRef.target_ontology_id == target_ontology_id
        ).all()

    def list_by_source(self, source_ontology_id: str) -> list[OntologySharedRef]:
        return self.db.query(OntologySharedRef).filter(
            OntologySharedRef.source_ontology_id == source_ontology_id
        ).all()

    def find_ref(self, target_ontology_id: str, entity_id: str) -> OntologySharedRef | None:
        return self.db.query(OntologySharedRef).filter(
            OntologySharedRef.target_ontology_id == target_ontology_id,
            OntologySharedRef.entity_id == entity_id,
        ).first()
