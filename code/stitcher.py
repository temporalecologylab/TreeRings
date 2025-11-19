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
import logging as log
import sample
# from memory_profiler import profile
import sys 
import time
import utils
import math

log.basicConfig(format='%(process)d-%(levelname)s-%(message)s', level=log.INFO)

class MaxFileSizeException(Exception):
    "Raised when a file is created that is over the maximum file size"
    def __init__(self, size):
        self.size = size 
        message = "File over {} MB created"
        super().__init__(message)

class Stitcher:
    def __init__(self, sample: sample.Sample):
        config = utils.load_config()
        self.sample = sample
        self._memmaps = []
        self._tiles = []
        self._mosaic = None
        self._frame_dir = sample.directory
        self._metadata = None
        self._max_file_size = config["stitcher"]["MAX_FILE_SIZE_GB"] * 1000 # GBs

        self.load_metadata()
        
    # @profile
    def write_dats(self, dats_path, resize = None):
        # Create dats directory 
        if not os.path.exists(dats_path):
            os.makedirs(dats_path)

        i = 0
        tile_paths = self.get_frames()
        self._memmap_paths = []
        first = True
        for tile_path in tile_paths:
            with rasterio.open(os.path.join(self._frame_dir, tile_path)) as dataset:
                data = np.transpose(dataset.read(), (1, 2, 0))
                if resize is not None and resize > 0 and resize < 1.0:
                    data = imutils.resize(data, width = int(resize * data.shape[1]))

                self._memmap_shape = (data.shape[0], data.shape[1], data.shape[2])

                # create a placeholder dat 
                if first:
                    memmap_path = os.path.join(dats_path, "placeholder_memmap_array.dat")
                    memmap_array = np.memmap(memmap_path, dtype = dataset.dtypes[0], mode='w+', shape=(data.shape[0], data.shape[1], data.shape[2]))
                    data = np.full((data.shape[0], data.shape[1], data.shape[2]), 0, dataset.dtypes[0])
                    memmap_array[:] = data[:]
                    memmap_array.flush()
                    del memmap_array
                    first = False

                memmap_path = os.path.join(dats_path, "{}_".format(i) + "memmap_array.dat")
                self._memmap_paths.append(memmap_path)
                self._memmap_dtype = dataset.dtypes[0]
                memmap_array = np.memmap(memmap_path, dtype=dataset.dtypes[0], mode='w+', shape=(data.shape[0], data.shape[1], data.shape[2]))
                i+=1
                memmap_array[:] = data[:]
                memmap_array.flush()

                
                # memmap_read_only = np.memmap(os.path.join(dats_path, "{}_".format(i) + "memmap_array.dat"), dtype=dataset.dtypes[0], mode='r', shape=(data.shape[0], data.shape[1], data.shape[2]))
                # self._memmaps.append(memmap_array)

                # flush to save the array
                del memmap_array
                del dataset
                del data
        
        # print(sys.getsizeof(self._memmaps))
        gc.collect()
        log.info("Wrote dats")
        return self._memmap_shape

    # @profile
    def read_dats(self):
        del self._memmaps

        self._memmaps = []

        for path in self._memmap_paths:
            memmap_array = np.memmap(path, dtype=self._memmap_dtype, mode='r', shape=(self._memmap_shape[0], self._memmap_shape[1], self._memmap_shape[2]))
            self._memmaps.append(memmap_array)

    def create_tiles(self):
        for path in self._memmap_paths:
            self._tiles.append(tile_memmap.MemmapOpenCVTile(path, self._memmap_shape))
        log.info("Created tiles")

    def create_mosaic(self):
        self._mosaic = mosaic_memmap.MemmapStructuredMosaic(self._tiles, dim=self._metadata["cols"])
        log.info("Created mosaic")

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

    def memmap_to_tiff(self, memmap, path_tif):
        if memmap is not None:
            tifffile.imwrite(
                path_tif,
                memmap,
                photometric='rgb',
                compression='LZW'
            )

    # def get_frames(self):
    #     # Create a regex pattern to match the filenames and extract row and column numbers
    #     pattern = re.compile(r'frame_(-?\d+)_(-?\d+)')

    #     # List all files in the directory
    #     files = os.listdir(self._frame_dir)

    #     # Filter and sort the files based on the row and column numbers
    #     sorted_paths = sorted(
    #         (f for f in files if pattern.match(f)),
    #         key=lambda f: (int(pattern.match(f).group(1)), int(pattern.match(f).group(2)))
    #         )
        
    #     log.info(sorted_paths)
    #     return sorted_paths
    def get_frames(self):
        pattern = re.compile(r'^frame_(-?\d+)_(-?\d+)\.tif$')

        files = os.listdir(self._frame_dir)

        matches = []
        for f in files:
            m = pattern.match(f)
            if m:
                row = int(m.group(1))
                col = int(m.group(2))
                matches.append((row, col, f))

        # Sort by row, then column
        matches.sort(key=lambda t: (t[0], t[1]))

        # return only filenames in order
        filenames = [t[2] for t in matches]
        log.info(filenames)

        return filenames
     
    # @profile
    def stitch(self, resize=None):
        start_time = time.time()
        self.sample.set_start_time_stitching(start_time)
        if resize is not None and resize < 1.0 and resize > 0:
            path = os.path.join(self._frame_dir, "{}per".format(int(resize * 100)))
            mosaic_dat_path = os.path.join(path, "mosaic_{}per.dat".format(int(resize *100)))
        else:
            path = os.path.join(self._frame_dir, "100per")
            mosaic_dat_path = os.path.join(path, "mosaic_100per.dat")
        
        self.dats_path = os.path.join(path, "dats")
        log.info("Writing dats with resize {}".format(resize))
        memmap_shape = self.write_dats(self.dats_path, resize = resize)
        log.info("Creating Tiles")
        # self.read_dats()
        # log.info("Reading dats")
        self.create_tiles()
        log.info("Creating Mosaic")
        self.create_mosaic()
        log.info("Aligning")
        self._mosaic.align()
        # self._mosaic.smooth_seams()

        if not os.path.exists(path):
            os.mkdir(path)

        shape = self._mosaic.save(mosaic_dat_path)

        end_time = time.time()
        self.sample.set_end_time_stitching(end_time)
        self.sample.set_stitch_height_pixels(shape[0])
        self.sample.set_stitch_width_pixels(shape[1])
        self.sample.set_stitch_depth(shape[2])

        self.sample.to_json(path)

        # no need in writing a normal tiff if it's going to be greater than the maximum tiff filesize
        if (shape[0] * shape[1] * shape[2]) / 1e6  < 3500:
            stitch = np.memmap(mosaic_dat_path, dtype='uint8', mode='r', shape=(shape[0], shape[1], shape[2]))

            try:
                self.memmap_to_tiff(stitch, str.replace(mosaic_dat_path, ".dat", ".tif"))
                del stitch
                # get rid of dat if there's a tiff 
                os.remove(mosaic_dat_path)

            except OSError:
                log.info("Not enough memory to create large tiff file")
            
        elif (shape[0] * shape[1] * shape[2]) / 1e6 > self._max_file_size: 
            raise MaxFileSizeException(self._max_file_size)


if __name__ == "__main__":
    def stitch_multiple_sizes(path, sizes):
        for size in sizes:
            st = Stitcher(path)
            try:
                st.stitch(resize = size)
            except MaxFileSizeException:
                print("Max file size met, no longer trying to stitch")
                break
            except Exception as e:
                print(e)
                print("Cannot align with this resize value.")
            finally:
                st.delete_dats()

                del st

    # sizes = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    sizes = [0.3]
    tile_path = "C:\\Users\\honey\\OneDrive\\Desktop\\TOSTITCH"
    stitch_multiple_sizes(tile_path, sizes)
    # tile_path = "C:\\Users\\honey\\Downloads\\BETPOP_WM8_P16_22_55_11_good"



    # stitch.run("C:\\Users\\chloe\\wolkovich_s24\\TreeRings\\code\\image_stitch_testing\\ashlar\\20per_zoomout_correctdims", "frame_{row:01}_{col:01}_1.jpg", 0.20, 0.78)
