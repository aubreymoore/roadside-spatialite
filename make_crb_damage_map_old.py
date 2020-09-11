"""

make_crb_damage_map

Aubrey Moore 2020-08-26

This Python script uses QGIS 3.4 to generate a CRB damage map from roadside 
video survey data stored in a MySQL database (mysql.guaminsects.net/videosurvey). 

Data extracted from videos specified in VIDEOLIST will be included in the map.

Launch QGIS and run this script using this command line:
qgis --nologo --code make_crb_damage_map.py

Download the most recent version of this script using this command line:
wget https://github.com/aubreymoore/roadside/raw/master/jupyter-notebooks/videosurveydb/make_crb_damage_map.py

NOTES

1. It will take a few minutes for the map to be generated. When the processing is finished,
richt-click on the mean_damage_index and zoom to layer extent. (I haven't figured out the code
to automate this last bit).

2. To generate a web map (Hopefully, this will be integrated into the script in the near future.):

* web | qgis2web | Create web map
* Select Leaflet in the radio buttons at bottom of dialog
* Appearance | Appearance | Add layers list: expanded
* template: full screen
* do not include the trees layer. This layer contains a large amount of data and it will
make the web map unresponsive.
* generate the map. On my machine, the web map ends up in a directory named something like
/tmp/qgis2web/qgis2web_2020_08_26-13_28_55_114206, which contains all the code for displaying
the map in a browser. Copy this directory to a more useful location and rename it, to "webmap" for
example. You can then see the map in a web browser by opening webmap/index.html.
* Have a look at aubreymoore.github.io/roadside/webmap to see an example web map.

"""

from glob import glob
import processing
from qgis.utils import iface
from qgis.core import *
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt, QRectF
from PyQt5.QtGui import *
from sqlalchemy import create_engine
import pandas as pd
import os
import yaml


######################################################################
# Utility functions
######################################################################


def get_parameters_from_yaml():
    with open('make_crb_damage_map.yaml') as f:
        parameters = yaml.load(f)
    return parameters
    

def remove_layer(layer_name):
    to_be_deleted = project.mapLayersByName(layer_name)[0]
    project.removeMapLayer(to_be_deleted.id())


def rename_layer(original_name, new_name):
    to_be_renamed = project.mapLayersByName(original_name)[0]
    to_be_renamed.setName(new_name)


def video_list_string():
    return ','.join("'{}'".format(v) for v in parameters['VIDEOLIST'])


def connect_to_db():
    connection_string = 'mysql+pymysql://{}:{}@{}'.format(
        parameters['DBUSERNAME'], parameters['DBPASSWORD'], parameters['DBURL'])
    print(connection_string)
    engine = create_engine(connection_string)
    connection = engine.connect()
    return connection


######################################################################
# Get data from the database and write to files
######################################################################


def write_geojson_files():
    """
    Writes all geojson strings from the videos database table to text files named like 20200630_131814.geojson
    Input parameter is a date sting in the form '20200630'
    """
    sql = """
    SELECT video_id, gps_track_json
    FROM videos
    WHERE video_id IN ({});
    """.format(video_list_string())
    df = pd.read_sql_query(sql, conn)
    for index, row in df.iterrows():
        filename = row.video_id.replace('.mp4', '.geojson')
        print('writing {}'.format(filename))
        with open(filename, 'w') as f:
            f.write(row.gps_track_json)


def write_trees_csv():
    """
    Writes tree data to a CSV
    """
    sql = """SELECT frames.frame_id, lat, lon, damage
             FROM videos, frames, trees
             WHERE
             videos.video_id=frames.video_id
             AND frames.frame_id=trees.frame_id
             AND videos.video_id IN ({});
          """.format(video_list_string())
    df = pd.read_sql_query(sql, conn)
    df.to_csv('trees.csv', index=False)


def write_vcuts_csv():
    """
    Writes vcut data to a CSV
    """
    sql = """SELECT frames.frame_id, lat, lon
             FROM videos, frames, vcuts
             WHERE
             videos.video_id=frames.video_id
             AND frames.frame_id=vcuts.frame_id
             AND videos.video_id IN ({});
          """.format(video_list_string())
    df = pd.read_sql_query(sql, conn)
    df.to_csv('vcuts.csv', index=False)


def get_data_from_db():
    write_geojson_files()
    write_trees_csv()
    write_vcuts_csv()


######################################################################
# Load layers
######################################################################


def load_guam_osm():
    canvas = iface.mapCanvas()
    url = 'type=xyz&url=https://a.tile.openstreetmap.org/{z}/{x}/{y}.png&crs=EPSG3857'
    rlayer = QgsRasterLayer(url, 'Guam', 'wms')
    QgsProject.instance().addMapLayer(rlayer)
    rect = QgsRectangle(16098000.0, 1486000.0, 16137000.0, 1535000.0)
    canvas.setExtent(rect)
    canvas.update()


def load_tracks_layers():
    geojsonlist = [s.replace('.mp4', '.geojson') for s in parameters['VIDEOLIST']]
    for f in geojsonlist:
        print('Reading {}'.format(f))
        vlayer = QgsVectorLayer(f, f, 'ogr')
        project.addMapLayer(vlayer, True)


def load_trees_layer():
    uri = "file://{}/trees.csv?type=csv&detectTypes=yes&xField=lon&yField=lat&crs=EPSG:4326&spatialIndex=no&subsetIndex=no&watchFile=no".format(os.getcwd())  
    vlayer = QgsVectorLayer(uri, 'trees', 'delimitedtext')
    project.addMapLayer(vlayer)
    processing.runAndLoadResults("native:reprojectlayer",
                                 {'INPUT': 'trees',
                                  'TARGET_CRS': 'EPSG:3857',
#                                  'OUTPUT': 'trees3857'})
                                  'OUTPUT': 'trees'})
    remove_layer('trees')
#    rename_layer('Reprojected', 'trees')


def load_vcuts_layer():
    uri = "file://{}/vcuts.csv?type=csv&detectTypes=yes&xField=lon&yField=lat&crs=EPSG:4326&spatialIndex=no&subsetIndex=no&watchFile=no".format(os.getcwd())  
    vlayer = QgsVectorLayer(uri, 'vcuts', 'delimitedtext')
    QgsProject.instance().addMapLayer(vlayer)


######################################################################
# Other stuff
######################################################################


def set_layer_visibility(layer_name, true_or_false):
    prj = QgsProject.instance()
    layer = prj.mapLayersByName(layer_name)[0]
    prj.layerTreeRoot().findLayer(
        layer.id()).setItemVisibilityChecked(true_or_false)


def create_grid():
    result = processing.run("qgis:creategrid",
                            {'TYPE': 2,
                             'EXTENT': '16098000,16137000,1486000,1535000',
                             'HSPACING': 1000.0,
                             'VSPACING': 1000.0,
                             'CRS': 'EPSG:3857',
                             'OUTPUT': 'memory:grid'})
    QgsProject.instance().addMapLayer(result['OUTPUT'])


def create_join():
    # processing.algorithmHelp("qgis:joinbylocationsummary")
    parameters = {
        'INPUT': 'grid',
        'JOIN': 'trees',
        'PREDICATE': 0,  # intersects
        'JOIN_FIELDS': 'damage',
        'SUMMARIES': 6,  # mean
        'DISCARD_NONMATCHING': True,
        'OUTPUT': 'mean_damage_index'
    }
    processing.runAndLoadResults(
        "qgis:joinbylocationsummary", parameters)
#    rename_layer('Joined layer', 'mean_damage_index')


def style_mean_damage_index():
    join_layer = QgsProject.instance().mapLayersByName(
        'mean_damage_index')[0]
    target_field = 'damage_mean'
    legend = [
        {'low': 0.0, 'high': 0.0, 'color': '#008000', 'label': 'No damage'},
        {'low': 0.0, 'high': 0.5, 'color': '#00ff00', 'label': '0.0 - 0.5'},
        {'low': 0.5, 'high': 1.5, 'color': '#ffff00', 'label': '0.5 - 1.5'},
        {'low': 1.5, 'high': 2.5, 'color': '#ffa500', 'label': '1.5 - 2.5'},
        {'low': 2.5, 'high': 3.5, 'color': '#ff6400', 'label': '2.5 - 3.5'},
        {'low': 3.5, 'high': 4.0, 'color': '#ff0000', 'label': '3.5 - 4.0'},
    ]
    myRangeList = []
    for i in legend:
        symbol = QgsSymbol.defaultSymbol(join_layer.geometryType())
        symbol.setColor(QColor(i['color']))
        myRangeList.append(QgsRendererRange(
            i['low'], i['high'], symbol, i['label'], True))
    myRenderer = QgsGraduatedSymbolRenderer(target_field, myRangeList)
    myRenderer.setMode(QgsGraduatedSymbolRenderer.Custom)
    join_layer.setRenderer(myRenderer)


def merge_tracks():
    project = QgsProject.instance()
    layers_to_be_included = []
    layerList = project.layerTreeRoot().findLayers()
    for layer in layerList:
        name = layer.name()
        if name.endswith('.geojson'):
            layers_to_be_included.append(name)
    processing.runAndLoadResults("native:mergevectorlayers",
                                 {'LAYERS': layers_to_be_included,
                                  'CRS': QgsCoordinateReferenceSystem('EPSG:3857'),
                                  'OUTPUT': 'memory:'})
    processing.runAndLoadResults('native:simplifygeometries',
                                 {'INPUT': 'Merged',
                                  'METHOD': 0,
                                  'TOLERANCE': 10,
                                  'OUTPUT': 'tracks'})
#    to_be_renamed = project.mapLayersByName('Simplified')[0]
#    to_be_renamed.setName('tracks')

    layer = project.mapLayersByName('tracks')[0]
    layer.renderer().symbol().setWidth(1)
    layer.renderer().symbol().setColor(QColor('#ff0000'))
    layer.triggerRepaint()


def zoom_to_guam():
    rect = QgsRectangle(16098000.0, 1486000.0, 16137000.0, 1535000.0)
    canvas = iface.mapCanvas()
    canvas.setExtent(rect)
    canvas.refresh()


def get_video_list():
    return pd.read_sql_query(
        "SELECT video_id FROM videos ORDER BY video_id;", conn)


def cleanup():

    # zoom to mean_damage_index layer - NOT WORKING
    layer = project.mapLayersByName('mean_damage_index')[0]
    canvas = qgis.utils.iface.mapCanvas()
    canvas.setExtent(layer.extent())

    # delete grid layer
    to_be_deleted = project.mapLayersByName('grid')[0]
    project.removeMapLayer(to_be_deleted.id())

    # delete Merged layer
    to_be_deleted = project.mapLayersByName('Merged')[0]
    project.removeMapLayer(to_be_deleted.id())

    # Delete individual tracks (*.geojson)
    for id, layer in project.mapLayers().items():
        if layer.name().endswith('.geojson'):
            project.removeMapLayer(id)


    # style trees layer; set color to #00ff00
    layer = project.mapLayersByName('trees')[0]
    layer.renderer().symbol().setColor(QColor(0, 255, 0))
    layer.triggerRepaint()

    # style vcuts; set color to #ff00ff
    layer = project.mapLayersByName('vcuts')[0]
    layer.renderer().symbol().setColor(QColor(255, 0, 255))
    layer.triggerRepaint()


######################################################################
# MAIN
######################################################################

parameters = get_parameters_from_yaml()
print(parameters)
project = QgsProject.instance()
conn = connect_to_db()
get_data_from_db()
load_guam_osm()
load_tracks_layers()
merge_tracks()
load_trees_layer()
create_grid()
create_join()
style_mean_damage_index()
load_vcuts_layer()
cleanup()

print("FINISHED")
