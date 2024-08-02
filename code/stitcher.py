import tile as tile_memmap
import mosaic as mosaic_memmap
import rasterio
import tifffile
import numpy as np
import json
import re
import os
from datetime import datetime
import glob
import gc
import imutils

class Stitcher:
    def __init__(self, frame_dir):
        self._memmaps = []
        self._tiles = []
        self._mosaic = None
        self._sizes = [1.0, 0.4, 0.3, 0.2, 0.1, 0.05, 0.01] # percentage of full resolution
        self._full_resolution = round(3840 * 2160 / 1e6, 2)
        self._frame_dir = frame_dir
        self._resolution = round(3840 * 2160 / 1e6, 2)        
        self._metadata = None

        self.load_metadata()
        
        
    def write_dats(self, dats_path, resize = None):
        # Create dats directory 
        if not os.path.exists(dats_path):
            os.mkdir(dats_path)

        i = 0
        tile_paths = self.get_frames()
        for tile_path in tile_paths:
            with rasterio.open(os.path.join(self._frame_dir, tile_path)) as dataset:
                data = np.transpose(dataset.read(), (1, 2, 0))
                if resize is not None and resize > 0 and resize < 1.0:
                    data = imutils.resize(data, width = int(resize * data.shape[1]))
                memmap_array = np.memmap(os.path.join(dats_path, "{}_".format(i) + "memmap_array.dat"), dtype=dataset.dtypes[0], mode='w+', shape=(data.shape[0], data.shape[1], data.shape[2]))
                i+=1
                memmap_array[:] = data
                self._memmaps.append(memmap_array)
                memmap_array.flush()
                del memmap_array
                del dataset
        
        print("Wrote dats")
    def create_tiles(self):
        for memmap in self._memmaps:
            self._tiles.append(tile_memmap.MemmapOpenCVTile(memmap))
        print("Created tiles")
    def create_mosaic(self):
        self._mosaic = mosaic_memmap.MemmapStructuredMosaic(self._tiles, dim=self._metadata["cols"])
        print("Created mosaic")

    def delete_dats(self):
        # make sure files close after being done stitching
        del self._tiles
        del self._memmaps
        del self._mosaic

        gc.collect()

        if os.path.exists(self.dats_path):
            files = glob.glob(os.path.join(self.dats_path, "*"))

            for file in files:
                os.remove(file)

            os.rmdir(self.dats_path)


    def load_metadata(self):
        metadata_path = os.path.join(self._frame_dir, "metadata.json")
        with open(metadata_path) as f:
            j = json.load(f)
            self._metadata = j
            f.close()

    def write_metadata(self, new_dir, shape):
        new_metadata = {}
        new_metadata["species"]=self._metadata["species"]
        new_metadata["id1"]=self._metadata["id1"]
        new_metadata["id2"]=self._metadata["id2"]
        new_metadata["notes"]=self._metadata["notes"]
        new_metadata["camera_pixels"]=self._metadata["camera_pixels"]
        new_metadata["DPI"] = round(shape[0] / self._metadata["cookie_height_mm"] * 25.4, 2)
        new_metadata["cookie_height_mm"] = self._metadata["cookie_height_mm"]
        new_metadata["cookie_width_mm"] = self._metadata["cookie_width_mm"]
        new_metadata["pixels_h"] = shape[0]
        new_metadata["pixels_w"] = shape[1]
        new_metadata["depth"] = shape[2]

        with open(os.path.join(new_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(new_metadata, f, ensure_ascii=False, indent=4)

    def memmap_to_tiff(self, memmap, path_tif):
        if memmap is not None:
            tifffile.imwrite(
                path_tif,
                memmap,
                photometric='rgb',
                compression='LZW'
            )

    def get_frames(self):
        # Create a regex pattern to match the filenames and extract row and column numbers
        pattern = re.compile(r'frame_(\d+)_(\d+)')

        # List all files in the directory
        files = os.listdir(self._frame_dir)

        # Filter and sort the files based on the row and column numbers
        sorted_paths = sorted(
            (f for f in files if pattern.match(f)),
            key=lambda f: (int(pattern.match(f).group(1)), int(pattern.match(f).group(2)))
            )
        
        return sorted_paths

    def stitch(self, resize=None):
        if resize is not None and resize < 1.0 and resize > 0:
            path = os.path.join(self._frame_dir, "{}per".format(int(resize * 100)))
            mosaic_dat_path = os.path.join(path, "mosaic_{}per.dat".format(int(resize *100)))
        else:
            path = os.path.join(self._frame_dir, "100per")
            mosaic_dat_path = os.path.join(path, "mosaic_full_res.dat")
        
        self.dats_path = os.path.join(path, "dats")
        print("Writing dats with resize {}".format(resize))
        self.write_dats(self.dats_path, resize = resize)
        print("Creating Tiles")
        self.create_tiles()
        print("Creating Mosaic")
        self.create_mosaic()
        print("Aligning")
        self._mosaic.align()
        # self._mosaic.smooth_seams()

        if not os.path.exists(path):
            os.mkdir(path)

        shape = self._mosaic.save(mosaic_dat_path)

        self.write_metadata(path, shape)

        # no need in writing a normal tiff if it's going to be greater than the maximum tiff filesize
        if (shape[0] * shape[1] * shape[2]) / 1e6  < 3500:
            stitch = np.memmap(mosaic_dat_path, dtype='uint8', mode='r', shape=(shape[0], shape[1], shape[2]))
            self.memmap_to_tiff(stitch, str.replace(mosaic_dat_path, ".dat", ".tif"))


if __name__ == "__main__":
    def stitch_multiple_sizes(path, sizes):
        for size in sizes:
            stitcher = Stitcher(path)
            try:
                stitcher.stitch(resize = size)
            except:
                print("Cannot align with this resize value.")
            stitcher.delete_dats()

            del stitcher

    sizes = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    tile_path = "C:\\Users\\honey\\Downloads\\BETPOP_WM8_P16"
    stitch_multiple_sizes(tile_path, sizes)
    # tile_path = "C:\\Users\\honey\\Downloads\\BETPOP_WM8_P16_22_55_11_good"



    # stitch.run("C:\\Users\\chloe\\wolkovich_s24\\TreeRings\\code\\image_stitch_testing\\ashlar\\20per_zoomout_correctdims", "frame_{row:01}_{col:01}_1.jpg", 0.20, 0.78)
