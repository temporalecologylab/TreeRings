import tile as tile_memmap
import mosaic as mosaic_memmap
import rasterio
import tifffile
import numpy as np
import json
import re
import os
from datetime import datetime

class Stitcher:
    def __init__(self, cookie_height_mm, cookie_width_mm):
        self._cookie_height_mm = cookie_height_mm
        self._cookie_width_mm = cookie_width_mm
        self._memmaps = []
        self._tiles = []
        self._mosaic = None
        self._sizes = [0.4, 0.3, 0.2, 0.1, 0.05, 0.01] # percentage of full resolution
        self._full_resolution = round(3840 * 2160 / 1e6, 2)
        self._resolutions = [self._full_resolution * size for size in self._sizes]

    def set_frame_path(self, frame_dir):
        self._frame_dir = frame_dir
        self._resolution = round(3840 * 2160 / 1e6, 2)

    def write_dats(self, frame_paths):
        # Create dats directory 
        dats_path = os.path.join(self._frame_dir, "dats")
        if not os.path.exists(dats_path):
            os.mkdir(dats_path)

        for path in frame_paths:
            compressed_path = os.path.join(dir, path)
            with rasterio.open(compressed_path) as dataset:
                memmap_array = np.memmap(os.path.join(dats_path, "{}_".format(i) + "memmap_array.dat"), dtype=dataset.dtypes[0], mode='w+', shape=(dataset.height, dataset.width, dataset.count))
                i+=1
                inter = dataset.read()
                memmap_array[:] = np.transpose(inter, (1, 2, 0))
                self._memmaps.append(memmap_array)

            del dataset
            del memmap_array
        
    def create_tiles(self):
        for memmap in self._memmaps:
            self._tiles.append(tile_memmap.MemmapOpenCVTile(memmap))

    def create_mosaic(self):
        with open(os.path.join(self._frame_dir + "metadata.json")) as f:
            cols = json.load(f)["cols"]
            f.close()

        self._mosaic = mosaic_memmap.MemmapStructuredMosaic(self._tiles, dim=cols)

    def delete_dats(self):
        pass

    def write_metadata(self, new_dir, shape):
        metadata_path = os.path.join(self._frame_dir, "metadata.json")
        with open() as f:
            j = json.load(f)
            f.close()

        new_metadata = {}
        new_metadata["species"]=j["species"]
        new_metadata["id1"]=j["id1"]
        new_metadata["id2"]=j["id2"]
        new_metadata["notes"]=j["notes"]
        new_metadata["camera_pixels"]=j["camera_pixels"]
        new_metadata["DPI"] = round(shape[0] / self._cookie_height_mm / 25.4, 2)
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

    def stitch(self, frame_dir):
        self.set_frame_path(frame_dir)
        paths = self.get_frames()
        self.write_dats(paths)
        self.create_tiles()
        self._mosaic.align()
        self._mosaic.smooth_seams()

        path = os.path.join(self._frame_dir, "100per")

        if not os.path.exists(path):
            os.mkdir(path)

        dat_path = os.path.join(path, "mosaic_full_res.dat")
        shape = self._mosaic.save(dat_path)

        self.write_metadata(path, shape)

        # no need in writing a normal tiff if it's going to be greater than the maximum tiff filesize
        if (shape[0] * shape[1] * shape[2]) / 1e6  < 3500:
            stitch = np.memmap(dat_path, dtype='uint8', mode='r', shape=(shape[0], shape[1], shape[2]))
            self.memmap_to_tiff(stitch, os.path.join(path, "mosaic_full_res.tif"))

    def stitch_multiple_sizes(self):
        for res, size in zip(self._resolutions, self._sizes):
            self._mosaic.resize(res)
            self._mosaic.align()
            self._mosaic.smooth_seams()

            path = os.path.join(self._frame_dir, "{}per".format(size * 100))

            if not os.path.exists(path):
                os.mkdir(path)

            dat_path = os.path.join(path, "mosaic_{}per.dat".format(size * 100))
            shape = self._mosaic.save(dat_path)
            self.write_metadata(path, shape)

            # no need in writing a normal tiff if it's going to be greater than the maximum tiff filesize
            if (shape[0] * shape[1] * shape[2]) / 1e6  < 3500:
                stitch = np.memmap(dat_path, dtype='uint8', mode='r', shape=(shape[0], shape[1], shape[2]))
                self.memmap_to_tiff(stitch, os.path.join(path, "mosaic_{}per.tif".format(size * 100)))

if __name__ == "__main__":
    
    stitch = Stitcher()

    stitch.run("C:\\Users\\chloe\\wolkovich_s24\\TreeRings\\code\\image_stitch_testing\\ashlar\\20per_zoomout_correctdims", "frame_{row:01}_{col:01}_1.jpg", 0.20, 0.78)
