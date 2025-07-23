import os
import orchestrator.core_loop as cl
import orchestrator.crud as crud


def test_project_memory_is_isolated(tmp_path):
    os.environ['ORCH_DB_URL'] = str(tmp_path / 'test.db')
    crud.init_db()
    p1 = crud.create_project(crud.ProjectCreate(name='A'))
    p2 = crud.create_project(crud.ProjectCreate(name='B'))

    mem_a = cl.Memory(project_id=p1.id)
    mem_b = cl.Memory(project_id=p2.id)

    mem_a.add('role', 'contentA')
    mem_b.add('role', 'contentB')

    items_a = mem_a.fetch()
    assert all('contentA' in c for _, c in items_a)
    assert not any('contentB' in c for _, c in items_a)
