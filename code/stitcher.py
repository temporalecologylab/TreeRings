from ashlar import filepattern, reg 
import os
from datetime import datetime

class Stitcher:
    def __init__(self):
        pass

    def run(self, path, pattern, overlap, pixel_size):
        reader = filepattern.FilePatternReader(path, pattern, overlap, pixel_size)
        edge_aligner = reg.EdgeAligner(reader,verbose=True)
        mosaics = []
        mosaic_args = {}
        mosaic_args['verbose'] = True

        edge_aligner.run()
        mosaics.append(reg.Mosaic(edge_aligner, edge_aligner.mosaic_shape, **mosaic_args))

        writer_class = reg.PyramidWriter
        time = datetime.now().strftime('%H_%M_%S')
        writer = writer_class(mosaics, "out_{}.tiff".format(time), verbose=True)
        writer.run()


    
if __name__ == "__main__":
    
    stitch = Stitcher()

    stitch.run("C:\\Users\\chloe\\wolkovich_s24\\TreeRings\\code\\image_stitch_testing\\ashlar\\20per_zoomout_correctdims", "frame_{row:01}_{col:01}_1.jpg", 0.20, 0.78)
