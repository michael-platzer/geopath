
# digital elevation model of Austria (ZIP archive with GeoTIFF image)
# https://www.data.gv.at/katalog/dataset/d88a1246-9684-480b-a480-ff63286b35b7
AUSTRIA_DEM_ZIP = ogd-10m-at.zip
AUSTRIA_DEM_TIF = ogd-10m-at/dhm_at_lamb_10m_2018.tif

# vector tile protobuf parser
VECTOR_TILE_PB = vector_tile_pb2.py

all: $(AUSTRIA_DEM_TIF) $(VECTOR_TILE_PB)

$(AUSTRIA_DEM_TIF): $(AUSTRIA_DEM_ZIP)
	unzip $< -d $(dir $(AUSTRIA_DEM_TIF))

$(AUSTRIA_DEM_ZIP):
	wget https://gis.ktn.gv.at/OGD/Geographie_Planung/ogd-10m-at.zip

%_pb2.py: %.proto
	protoc --python_out=$(dir $@) $<

clean:
	rm -rf $(VECTOR_TILE_PB) $(dir $(AUSTRIA_DEM_TIF)) *.npy *.png *.svg
