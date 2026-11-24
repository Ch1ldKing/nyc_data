import numpy as np
import pandas as pd
from urban_flooding.build import cell_index, CELL


def test_cell_index_floors_to_500m_grid():
    ids = cell_index(np.array([583499.9, 583500.0]), np.array([4500000.0, 4500499.0]))
    assert list(ids) == [f"{583499 // CELL}_{4500000 // CELL}", f"{583500 // CELL}_{4500499 // CELL}"]


def test_urban_mask_requires_land_roads_and_people():
    from urban_flooding.figs.strat import urban_mask
    d = pd.DataFrame({"land_frac": [0.9, 0.9, 0.3, 0.9], "road_frac": [0.1, 0.01, 0.1, 0.1], "pop": [500, 500, 500, 50]})
    assert urban_mask(d).tolist() == [True, False, False, False]
