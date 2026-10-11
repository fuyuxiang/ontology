"""Regression coverage for drafts created from a selected ontology."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.ontology_publish import (
    AddEntitiesRequest,
    CreateVersionRequest,
    add_entities,
    create_version,
    list_published_ontologies,
)
from app.database import Base
from app.models import OntologyEntity, ScenarioDict
from app.models.user import User
from app.models.version import OntologyVersion, OntologyVersionEntity


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_created_draft_stays_in_selected_ontology_and_numbers_independently(db):
    first = ScenarioDict(code="draft-first", name="第一本体")
    second = ScenarioDict(code="draft-second", name="第二本体")
    db.add_all([first, second])
    db.commit()
    user = User(id="draft-reviewer", username="draft-reviewer", name="评审", password_hash="x")

    one = create_version(CreateVersionRequest(name=" 草稿一 ", ontology_id=first.id), db, user)
    two = create_version(CreateVersionRequest(name="草稿二", ontology_id=first.id), db, user)
    other = create_version(CreateVersionRequest(name="其他草稿", ontology_id=second.id), db, user)

    assert (one["version_number"], two["version_number"], other["version_number"]) == (1, 2, 1)
    assert one["name"] == "草稿一"
    db.expire_all()
    assert db.get(OntologyVersion, one["id"]).ontology_id == first.id
    cards = {card["ontology_id"]: card for card in list_published_ontologies(db)}
    assert cards[first.id]["total_versions"] == 2
    assert {item["id"] for item in cards[first.id]["versions"]} == {one["id"], two["id"]}


def test_draft_rejects_missing_ontology_and_blank_name(db):
    user = User(id="draft-reviewer", username="draft-reviewer", name="评审", password_hash="x")
    with pytest.raises(HTTPException) as missing:
        create_version(CreateVersionRequest(name="草稿", ontology_id="missing"), db, user)
    assert missing.value.status_code == 404
    with pytest.raises(HTTPException) as blank:
        create_version(CreateVersionRequest(name="  "), db, user)
    assert blank.value.status_code == 422
    assert db.query(OntologyVersion).count() == 0


def test_cross_ontology_addition_is_rejected_before_partial_write(db):
    first = ScenarioDict(code="add-first", name="第一本体")
    second = ScenarioDict(code="add-second", name="第二本体")
    db.add_all([first, second])
    db.flush()
    own = OntologyEntity(name="own", name_cn="本体对象", tier=1, ontology_id=first.id)
    foreign = OntologyEntity(name="foreign", name_cn="其他对象", tier=1, ontology_id=second.id)
    draft = OntologyVersion(name="草稿", ontology_id=first.id, version_number=1, status="draft")
    db.add_all([own, foreign, draft])
    db.commit()

    with pytest.raises(HTTPException) as rejected:
        add_entities(draft.id, AddEntitiesRequest(entity_ids=[own.id, foreign.id]), db)
    assert rejected.value.status_code == 400
    assert db.query(OntologyVersionEntity).count() == 0

    add_entities(draft.id, AddEntitiesRequest(entity_ids=[own.id]), db)
    assert db.query(OntologyVersionEntity).one().source_entity_id == own.id
