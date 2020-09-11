BEGIN;

CREATE TABLE grid (id INTEGER PRIMARY KEY AUTOINCREMENT);

SELECT AddGeometryColumn('grid', 'geometry', 3857, 'MULTIPOLYGON', 'XY');

INSERT INTO grid (geometry) 
	SELECT SquareGrid(Extent(geometry), 1000) FROM frames;



CREATE TABLE grid1 (id INTEGER PRIMARY KEY AUTOINCREMENT);

SELECT AddGeometryColumn('grid1', 'geometry', 3857, 'POLYGON', 'XY');

INSERT INTO grid1 (geometry) 
	SELECT geometry 
	FROM ElementaryGeometries 
	WHERE f_table_name = 'grid' 
		AND origin_rowid=1;


CREATE TABLE mean_damage_index (id INTEGER PRIMARY KEY AUTOINCREMENT, mean_damage_index DOUBLE);

SELECT AddGeometryColumn('mean_damage_index', 'geometry', 3857, 'POLYGON', 'XY');

INSERT INTO mean_damage_index (mean_damage_index, geometry)
	SELECT AVG(damage_index), grid1.geometry 
	FROM trees_view, grid1
	WHERE Contains(grid1.geometry, trees_view.geometry)
	GROUP BY grid1.id;

--Clean up

DROP TABLE grid;

DROP TABLE grid1;

COMMIT;
