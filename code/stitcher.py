from ashlar import filepattern, reg 
import os
import time

class Stitcher:
    def __init__(self, path, pattern, overlap, pixel_size):
        # self.metadata = FilePatternMetadata(path, pattern, overlap, pixel_size) #dont need bc reader defines its own metadata object?
        self.reader = filepattern.FilePatternReader(path, pattern, overlap, pixel_size) #in ashlar/filepattern.py pix_sz =1??
        self.edge_aligner = reg.EdgeAligner(self.reader,verbose=True)
        self.mosaics = []

    def run(self):
        mosaic_args = {}
        mosaic_args['channels'] = range(3)
        mosaic_args['verbose'] = True

        self.edge_aligner.run()
        self.mosaics.append(reg.Mosaic(self.edge_aligner, self.edge_aligner.mosaic_shape, **mosaic_args))

        writer_class = reg.PyramidWriter
        writer = writer_class(self.mosaics, "out_tiff_chan.ome.tiff", verbose=True)
        writer.run()


    
if __name__ == "__main__":
    
    stitch = Stitcher("C:\\Users\\chloe\\wolkovich_s24\\TreeRings\\code\\tiff_test", "frame_{row:01}_{col:01}_1.tiff", 0.20, 1.55)

    stitch.run()
