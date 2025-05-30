import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models.entity_association import EntityAssociation, Base
from core.repositories.entity_association_repository import EntityAssociationHelper
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
    helper = EntityAssociationHelper()
    return EntityAssociationService(helper=helper)

def test_associate_and_get_related_entities(service, session):
    service.associate(session, 'action_log', 1, 'calendar', 2, 'related_to')
    related = service.get_related_entities(session, 'action_log', 1)
    assert ('calendar', 2) in related

def test_duplicate_association_raises(service, session):
    service.associate(session, 'action_log', 1, 'calendar', 2, 'related_to')
    with pytest.raises(ValueError):
        service.associate(session, 'action_log', 1, 'calendar', 2, 'related_to')

def test_dissociate(service, session):
    service.associate(session, 'action_log', 1, 'calendar', 2, 'related_to')
    service.dissociate(session, 'action_log', 1, 'calendar', 2, 'related_to')
    related = service.get_related_entities(session, 'action_log', 1)
    assert ('calendar', 2) not in related

def test_list_by_source_and_target(service, session):
    service.associate(session, 'action_log', 1, 'calendar', 2, 'related_to')
    service.associate(session, 'action_log', 1, 'appointment', 3, 'related_to')
    by_source = service.list_by_source(session, 'action_log', 1)
    by_target = service.list_by_target(session, 'calendar', 2)
    assert len(by_source) == 2
    assert by_target[0].source_id == 1

def test_get_related_entities_with_association_type(service, session):
    service.associate(session, 'action_log', 1, 'calendar', 2, 'related_to')
    service.associate(session, 'action_log', 1, 'appointment', 3, 'overlap')
    related = service.get_related_entities(session, 'action_log', 1, association_type='overlap')
    assert ('appointment', 3) in related
    assert ('calendar', 2) not in related

def test_dissociate_nonexistent(service, session):
    # Should not raise
    service.dissociate(session, 'action_log', 1, 'calendar', 2, 'related_to')

def test_circular_association(service, session):
    service.associate(session, 'calendar', 2, 'action_log', 1, 'related_to')
    related = service.get_related_entities(session, 'calendar', 2)
    assert ('action_log', 1) in related 