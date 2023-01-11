import random

layer =  iface.activeLayer()
fni = layer.dataProvider().fieldNameIndex('faixa_img')
unique_values = layer.uniqueValues(fni)

# fill categories
categories = []
for unique_value in unique_values:
    # initialize the default symbol for this geometry type
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    #symbol.setWidth(2)
    # configure a symbol layer
    layer_style = {}
    layer_style['color'] = '%d, %d, %d' % (random.randrange(0, 256), random.randrange(0, 256), random.randrange(0, 256))
    layer_style['outline'] = '#000000'
    symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
    # replace default symbol layer with the configured one
    if symbol_layer is not None:
        symbol.changeSymbolLayer(0, symbol_layer)

    # create renderer object
    category = QgsRendererCategory(unique_value, symbol, str(unique_value))
    # entry for the list of category items
    categories.append(category)

# create renderer object
renderer = QgsCategorizedSymbolRenderer('faixa_img', categories)

# assign the created renderer to the layer
if renderer is not None:
    layer.setRenderer(renderer)

layer.triggerRepaint()


#uri = "file:///E:/URUGUAIANA/STRUCT-10_41_29_09_2022.csv?type='csv&maxFields=10000&detectTypes=yes&xField=long_img&yField=lat_img&crs=EPSG:4326&spatialIndex=no&subsetIndex=no&watchFile=no'"
#l = QgsVectorLayer(uri, 'teste', 'delimitedtext')
#QgsProject().instance().addMapLayer(l)