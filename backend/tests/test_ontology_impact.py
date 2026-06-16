import pytest

from app.services.ontology_impact import (
    compute_breaking_changes,
    find_affected_agents,
    find_affected_scenes,
)


class TestComputeBreakingChanges:
    def test_deleted_entity(self):
        old_entities = [
            {"source_entity_id": "e1", "name": "Customer"},
            {"source_entity_id": "e2", "name": "Contract"},
        ]
        new_entities = [
            {"source_entity_id": "e1", "name": "Customer"},
        ]
        changes = compute_breaking_changes(old_entities, new_entities)
        assert len(changes) == 1
        assert changes[0]["entity_name"] == "Contract"
        assert changes[0]["change_type"] == "deleted"
        assert changes[0]["source_entity_id"] == "e2"

    def test_renamed_entity(self):
        old_entities = [
            {"source_entity_id": "e1", "name": "OldCustomer"},
        ]
        new_entities = [
            {"source_entity_id": "e1", "name": "Customer"},
        ]
        changes = compute_breaking_changes(old_entities, new_entities)
        assert len(changes) == 1
        assert changes[0]["change_type"] == "renamed"
        assert changes[0]["entity_name"] == "OldCustomer"
        assert changes[0]["new_name"] == "Customer"

    def test_no_changes(self):
        old_entities = [
            {"source_entity_id": "e1", "name": "Customer"},
        ]
        new_entities = [
            {"source_entity_id": "e1", "name": "Customer"},
        ]
        changes = compute_breaking_changes(old_entities, new_entities)
        assert changes == []

    def test_first_publish_no_old_version(self):
        changes = compute_breaking_changes([], [
            {"source_entity_id": "e1", "name": "Customer"},
        ])
        assert changes == []


class TestFindAffectedScenes:
    def test_scene_with_deleted_entity_binding(self):
        scenes = [
            {"id": "s1", "ontology_bindings": ["Customer", "Contract"]},
            {"id": "s2", "ontology_bindings": ["Order"]},
        ]
        changes = [{"entity_name": "Contract", "change_type": "deleted", "source_entity_id": "e2"}]
        affected = find_affected_scenes(scenes, changes)
        assert affected == ["s1"]

    def test_scene_with_renamed_entity_binding(self):
        scenes = [
            {"id": "s1", "ontology_bindings": ["OldCustomer"]},
        ]
        changes = [{"entity_name": "OldCustomer", "change_type": "renamed", "new_name": "Customer", "source_entity_id": "e1"}]
        affected = find_affected_scenes(scenes, changes)
        assert affected == ["s1"]

    def test_no_affected_scenes(self):
        scenes = [
            {"id": "s1", "ontology_bindings": ["Order"]},
        ]
        changes = [{"entity_name": "Contract", "change_type": "deleted", "source_entity_id": "e2"}]
        affected = find_affected_scenes(scenes, changes)
        assert affected == []


class TestFindAffectedAgents:
    def test_agent_with_deleted_entity_id(self):
        agents = [
            {"id": "a1", "entity_ids": ["e1", "e2"]},
            {"id": "a2", "entity_ids": ["e3"]},
        ]
        changes = [{"entity_name": "Contract", "change_type": "deleted", "source_entity_id": "e2"}]
        affected = find_affected_agents(agents, changes)
        assert affected == ["a1"]

    def test_agent_with_empty_entity_ids(self):
        agents = [
            {"id": "a1", "entity_ids": None},
            {"id": "a2", "entity_ids": []},
        ]
        changes = [{"entity_name": "Contract", "change_type": "deleted", "source_entity_id": "e2"}]
        affected = find_affected_agents(agents, changes)
        assert affected == []
