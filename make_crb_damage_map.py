def load_guam_osm():
    canvas = iface.mapCanvas()
    url = 'type=xyz&url=https://a.tile.openstreetmap.org/{z}/{x}/{y}.png&crs=EPSG3857'
    rlayer = QgsRasterLayer(url, 'Guam', 'wms')
    QgsProject.instance().addMapLayer(rlayer)
    rect = QgsRectangle(16098000.0, 1486000.0, 16137000.0, 1535000.0)
    canvas.setExtent(rect)
    canvas.update()


def load_layer_from_db(table_name):
    uri = QgsDataSourceUri()
    uri.setDatabase('/home/aubrey/Documents/populate_spatialite/videosurvey.db')
    schema = ''
    table = table_name
    geom_column = 'geometry'
    uri.setDataSource(schema, table, geom_column)
    display_name = table_name
    vlayer = QgsVectorLayer(uri.uri(), display_name, 'spatialite')
    QgsProject.instance().addMapLayer(vlayer)


def style_mean_damage_index():
    join_layer = QgsProject.instance().mapLayersByName(
        'mean_damage_index')[0]
    target_field = 'mean_damage_index'
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

    
# MAIN

load_guam_osm()
load_layer_from_db('tracks')
load_layer_from_db('frames')
load_layer_from_db('trees_view')
load_layer_from_db('vcuts_view')
load_layer_from_db('mean_damage_index')
style_mean_damage_index()


