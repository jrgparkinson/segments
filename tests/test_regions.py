
def test_save(regions_db):
    regions_db.init_region([(0, 1), (2, 3)])
    regions_db.save()

    assert regions_db.display() == [{'bounds': [(0, 1), (2, 3)], 'explored': False}]

