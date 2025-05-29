import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models.entity_association import EntityAssociation, Base
from core.repositories.entity_association_repository import EntityAssociationRepository
from core.services.entity_association_service import EntityAssociationService

@pytest.fixture(scope="function")
def session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()
    engine.dispose()

@pytest.fixture(scope="function")
def service(session):
    repo = EntityAssociationRepository(session=session)
    return EntityAssociationService(repository=repo)

def test_associate_and_get_related_entities(service):
    service.associate('action_log', 1, 'calendar', 2, 'related_to')
    related = service.get_related_entities('action_log', 1)
    assert ('calendar', 2) in related

def test_duplicate_association_raises(service):
    service.associate('action_log', 1, 'calendar', 2, 'related_to')
    with pytest.raises(ValueError):
        service.associate('action_log', 1, 'calendar', 2, 'related_to')

def test_dissociate(service):
    service.associate('action_log', 1, 'calendar', 2, 'related_to')
    service.dissociate('action_log', 1, 'calendar', 2, 'related_to')
    related = service.get_related_entities('action_log', 1)
    assert ('calendar', 2) not in related

def test_list_by_source_and_target(service):
    service.associate('action_log', 1, 'calendar', 2, 'related_to')
    service.associate('action_log', 1, 'appointment', 3, 'related_to')
    by_source = service.list_by_source('action_log', 1)
    by_target = service.list_by_target('calendar', 2)
    assert len(by_source) == 2
    assert by_target[0].source_id == 1

def test_get_related_entities_with_association_type(service):
    service.associate('action_log', 1, 'calendar', 2, 'related_to')
    service.associate('action_log', 1, 'appointment', 3, 'overlap')
    related = service.get_related_entities('action_log', 1, association_type='overlap')
    assert ('appointment', 3) in related
    assert ('calendar', 2) not in related

def test_dissociate_nonexistent(service):
    # Should not raise
    service.dissociate('action_log', 1, 'calendar', 2, 'related_to')

def test_circular_association(service):
    service.associate('calendar', 2, 'action_log', 1, 'related_to')
    related = service.get_related_entities('calendar', 2)
    assert ('action_log', 1) in related 